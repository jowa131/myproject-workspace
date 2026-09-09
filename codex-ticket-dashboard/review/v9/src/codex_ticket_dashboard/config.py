"""Typed dashboard registry configuration boundary and check command."""

from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path, PurePosixPath
from tomllib import TOMLDecodeError
from typing import Annotated, ClassVar, Literal, Self, override

import typer
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    SettingsError,
    TomlConfigSettingsSource,
)

from codex_ticket_dashboard.domain.identifiers import ProjectId, parse_project_id


@unique
class WikiAuthority(StrEnum):
    """Supported durable Wiki authority routes."""

    CENTRAL_WIKI = "CENTRAL_WIKI"
    PROJECT_LOCAL_WIKI = "PROJECT_LOCAL_WIKI"


@dataclass(frozen=True, slots=True)
class ConfigLoadError(Exception):
    """Describe a configuration failure without retaining source content."""

    code: Literal["CONFIG_INVALID"]
    field_path: str
    issue_count: int

    @override
    def __str__(self) -> str:
        """Return a stable, redacted configuration error."""
        return f"{self.code}: field={self.field_path} count={self.issue_count}"


class ProjectRegistryEntry(BaseModel):
    """One user-approved registry-only project mapping."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    project_id: ProjectId
    label: Annotated[str, Field(min_length=1, max_length=120)]
    roots: Annotated[tuple[Path, ...], Field(min_length=1, max_length=32)]
    worktree_roots: Annotated[tuple[Path, ...], Field(max_length=32)] = ()
    wiki_authority: WikiAuthority
    authority_source_ref: Annotated[str, Field(min_length=1, max_length=240)]
    authority_source_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @field_validator("project_id", mode="after")
    @classmethod
    def validate_project_id(cls, value: ProjectId) -> ProjectId:
        """Require the stable registry project prefix."""
        return parse_project_id(value)

    @field_validator("roots", "worktree_roots", mode="after")
    @classmethod
    def validate_absolute_roots(cls, values: tuple[Path, ...]) -> tuple[Path, ...]:
        """Reject relative registry roots at the file boundary."""
        if any(not value.is_absolute() for value in values):
            raise ConfigLoadError(code="CONFIG_INVALID", field_path="projects.roots", issue_count=1)
        return values

    @field_validator("authority_source_ref", mode="after")
    @classmethod
    def validate_relative_authority_ref(cls, value: str) -> str:
        """Keep authority references relative and traversal-free."""
        reference = PurePosixPath(value.replace("\\", "/"))
        if reference.is_absolute() or ".." in reference.parts:
            raise ConfigLoadError(
                code="CONFIG_INVALID",
                field_path="projects.authority_source_ref",
                issue_count=1,
            )
        return value


class DashboardConfig(BaseSettings):
    """Validated dashboard configuration loaded from an explicit TOML file."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    data_root: Path
    projects: Annotated[tuple[ProjectRegistryEntry, ...], Field(min_length=1, max_length=128)]

    @field_validator("data_root", mode="after")
    @classmethod
    def validate_absolute_data_root(cls, value: Path) -> Path:
        """Reject a relative dashboard data root."""
        if not value.is_absolute():
            raise ConfigLoadError(code="CONFIG_INVALID", field_path="data_root", issue_count=1)
        return value

    @model_validator(mode="after")
    def validate_unique_projects(self) -> Self:
        """Reject duplicate stable project identifiers."""
        project_ids = tuple(project.project_id for project in self.projects)
        if len(project_ids) != len(set(project_ids)):
            raise ConfigLoadError(
                code="CONFIG_INVALID",
                field_path="projects.project_id",
                issue_count=1,
            )
        return self


class ConfigCheckOutput(BaseModel):
    """Redacted metadata emitted by the configuration check command."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: Literal["READY"] = "READY"
    schema_version: Literal[1]
    project_count: int = Field(ge=1)
    project_ids: tuple[ProjectId, ...]


def load_dashboard_config(path: Path) -> DashboardConfig:
    """Load and validate an explicit dashboard TOML file."""
    try:
        source = TomlConfigSettingsSource(DashboardConfig, toml_file=path)
        return DashboardConfig.model_validate(source())
    except (OSError, SettingsError, TOMLDecodeError) as error:
        raise ConfigLoadError(code="CONFIG_INVALID", field_path="$", issue_count=1) from error
    except ValidationError as error:
        raise ConfigLoadError(
            code="CONFIG_INVALID",
            field_path="$",
            issue_count=error.error_count(),
        ) from error


def check_config(path: Path) -> ConfigCheckOutput:
    """Return only safe registry metadata for a validated configuration."""
    config = load_dashboard_config(path)
    return ConfigCheckOutput(
        schema_version=config.schema_version,
        project_count=len(config.projects),
        project_ids=tuple(project.project_id for project in config.projects),
    )


def main(check: Annotated[Path, typer.Option("--check")]) -> None:
    """Validate a dashboard configuration without creating runtime artifacts."""
    try:
        output = check_config(check)
    except ConfigLoadError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from None
    typer.echo(output.model_dump_json())


if __name__ == "__main__":
    typer.run(main)
