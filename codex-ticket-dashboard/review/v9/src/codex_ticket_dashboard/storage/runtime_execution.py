"""Digest-bound protected runtime validation, separate from the legacy project-venv route."""

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from codex_ticket_dashboard.compliance.runtime_authority import read_pinned_source
from codex_ticket_dashboard.compliance.runtime_authority_models import (
    ClosedModel,
    Digest,
    FilePin,
    RuntimeAuthorityError,
)
from codex_ticket_dashboard.storage.path_security import validate_secure_path


class ExecutionApproval(ClosedModel):
    """Externally pinned execution contract over installed bytes and import locations."""

    schema_version: Literal[1]
    protected_root: Path
    interpreter: FilePin
    source_root: Path
    config: FilePin
    task_authority: FilePin
    dependency_manifest: FilePin
    source_manifest: FilePin
    import_paths: tuple[Path, ...]
    metadata_files: tuple[FilePin, ...] = ()


class InstalledFile(BaseModel):
    """Only installed targets are authoritative; mutable build sources are ignored."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    target: Path
    sha256: Digest
    size: int = Field(ge=0)


class InstalledManifest(BaseModel):
    """Manifest closure rooted at one approved installed tree."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    schema_version: Literal[1]
    runtime_root: Path
    files: tuple[InstalledFile, ...] = Field(min_length=1)


def _contained(path: Path, root: Path) -> None:
    if not path.is_absolute() or not path.is_relative_to(root):
        raise RuntimeAuthorityError(code="EXECUTION_PATH_OUTSIDE_APPROVAL")


def _protected_pin(pin: FilePin, root: Path) -> bytes:
    _contained(pin.path, root)
    _ = validate_secure_path(pin.path, root)
    return read_pinned_source(pin)


def _installed_tree(
    pin: FilePin,
    protected_root: Path,
    metadata: tuple[FilePin, ...],
) -> tuple[Path, frozenset[Path]]:
    manifest = InstalledManifest.model_validate_json(_protected_pin(pin, protected_root))
    root = manifest.runtime_root
    _contained(root, protected_root)
    _ = validate_secure_path(root, protected_root)
    targets = frozenset(item.target for item in manifest.files)
    if len(targets) != len(manifest.files):
        raise RuntimeAuthorityError(code="EXECUTION_MANIFEST_DUPLICATE")
    for item in manifest.files:
        _contained(item.target, root)
        content = _protected_pin(
            FilePin(
                path=item.target,
                reference=item.target.name,
                sha256=item.sha256,
            ),
            protected_root,
        )
        if len(content) != item.size:
            raise RuntimeAuthorityError(code="EXECUTION_SIZE_MISMATCH")
    allowed = targets | {item.path for item in metadata} | {pin.path}
    for path in root.rglob("*"):
        _ = validate_secure_path(path, protected_root)
        if path.is_file() and path not in allowed:
            raise RuntimeAuthorityError(code="EXECUTION_UNMANIFESTED_FILE")
    return root, targets


def verify_protected_execution(  # noqa: PLR0913 -- complete independently observed startup identity.
    approval_path: Path,
    approval_sha256: str,
    *,
    config_path: Path,
    task_authority_path: Path,
    task_authority_sha256: str,
    running_executable: Path,
    runtime_module: Path,
    import_paths: tuple[Path, ...],
    bytecode_disabled: bool,
    isolation_verified: bool,
) -> Path:
    """Reject substituted interpreter, source, imports, or declarations before runtime creation."""
    try:
        pin = FilePin(path=approval_path, reference=approval_path.name, sha256=approval_sha256)
        approval = ExecutionApproval.model_validate_json(read_pinned_source(pin))
        root = approval.protected_root
        _ = validate_secure_path(root, root)
        _ = _protected_pin(pin, root)
        if (
            not bytecode_disabled
            or not isolation_verified
            or approval.config.path != config_path
            or approval.task_authority.path != task_authority_path
            or approval.task_authority.sha256 != task_authority_sha256
            or approval.interpreter.path != running_executable
            or runtime_module != approval.source_root / "codex_ticket_dashboard/runtime.py"
            or import_paths != approval.import_paths
        ):
            raise RuntimeAuthorityError(code="EXECUTION_IDENTITY_MISMATCH")
        for item in (
            approval.interpreter,
            approval.config,
            approval.task_authority,
            *approval.metadata_files,
        ):
            _ = _protected_pin(item, root)
        dependency_root, dependency_targets = _installed_tree(
            approval.dependency_manifest,
            root,
            approval.metadata_files,
        )
        source_root, source_targets = _installed_tree(
            approval.source_manifest, root, approval.metadata_files
        )
        if (
            source_root != approval.source_root
            or running_executable not in dependency_targets
            or runtime_module not in source_targets
            or not any(path.name == "python312._pth" for path in dependency_targets)
        ):
            raise RuntimeAuthorityError(code="EXECUTION_MANIFEST_IDENTITY_MISMATCH")
        for directory in import_paths:
            if not directory.is_relative_to(dependency_root) and not directory.is_relative_to(
                source_root
            ):
                raise RuntimeAuthorityError(code="EXECUTION_IMPORT_OUTSIDE_APPROVAL")
            _ = validate_secure_path(directory, root)
    except (OSError, ValidationError):
        raise RuntimeAuthorityError(code="EXECUTION_APPROVAL_INVALID") from None
    return running_executable
