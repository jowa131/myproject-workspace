"""Closed official MCP transport provenance, never a model-supplied tool argument."""

from dataclasses import dataclass
from typing import Annotated, ClassVar, Self, override

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from codex_ticket_dashboard.domain.identifiers import SessionId, TurnId, parse_session_id


@dataclass(frozen=True, slots=True)
class McpContextError(ValueError):
    """Reject contradictory transport identity without retaining its content."""

    @override
    def __str__(self) -> str:
        return "MCP_CONTEXT_CONFLICT"


class McpContextWitness(BaseModel):
    """Exact transport context corroborating a business event and its logical parent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )
    source_host: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
    thread_id: Annotated[SessionId, AfterValidator(parse_session_id)]
    turn_id: Annotated[TurnId, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
    parent_thread_id: Annotated[SessionId, AfterValidator(parse_session_id)] | None = None

    @model_validator(mode="after")
    def validate_parent(self) -> Self:
        """A logical child cannot name itself as its transport parent."""
        if self.parent_thread_id == self.thread_id:
            raise McpContextError
        return self


def witness_is_absent(value: McpContextWitness | None) -> bool:
    """Keep witness-free historical envelope serialization byte-compatible."""
    return value is None
