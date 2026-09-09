"""Opaque, unsigned, context-bound pagination cursor codec."""

import base64
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,2048}$")


class InvalidCursorError(ValueError):
    """Reject malformed or out-of-contract cursors."""

    code: Literal["INVALID_CURSOR"] = "INVALID_CURSOR"


class CursorContextMismatchError(ValueError):
    """Reject a cursor reused outside its original list context."""

    code: Literal["CURSOR_CONTEXT_MISMATCH"] = "CURSOR_CONTEXT_MISMATCH"


@dataclass(frozen=True, slots=True)
class CursorContext:
    """Bind an opaque cursor to one route, filter, and sort direction."""

    route_id: str
    filter_digest: str
    direction: Literal["asc"] = "asc"


class _CursorPayload(BaseModel):
    """Validate the compact public cursor representation at its boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = Field(alias="v")
    route_id: str = Field(alias="r", min_length=1, max_length=80)
    filter_digest: str = Field(alias="f", pattern=r"^[0-9a-f]{64}$")
    direction: Literal["asc"] = Field(alias="d")
    snapshot_high_watermark: int = Field(alias="h", ge=0)
    last_sequence: int = Field(alias="s", gt=0)
    last_stable_id: str = Field(alias="i", min_length=1, max_length=160)


@dataclass(frozen=True, slots=True)
class CursorPosition:
    """Represent the immutable key after which a page resumes."""

    sequence: int
    stable_id: str
    snapshot_high_watermark: int


def filter_digest(values: tuple[tuple[str, str], ...]) -> str:
    """Hash a normalized filter set without carrying values in the cursor."""
    canonical = "&".join(f"{key}={value}" for key, value in values)
    return sha256(canonical.encode("utf-8")).hexdigest()


def encode_cursor(context: CursorContext, position: CursorPosition) -> str:
    """Encode one public, unsigned cursor with no SQL or request text."""
    payload = _CursorPayload(
        v=1,
        r=context.route_id,
        f=context.filter_digest,
        d=context.direction,
        h=position.snapshot_high_watermark,
        s=position.sequence,
        i=position.stable_id,
    )
    return (
        base64.urlsafe_b64encode(payload.model_dump_json(by_alias=True).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )


def decode_cursor(token: str, context: CursorContext) -> CursorPosition:
    """Decode and verify a cursor's bounded syntax and exact list context."""
    if _TOKEN_PATTERN.fullmatch(token) is None:
        raise InvalidCursorError
    padding = "=" * (-len(token) % 4)
    try:
        source = base64.urlsafe_b64decode(token + padding)
        payload = _CursorPayload.model_validate_json(source)
    except (UnicodeError, ValidationError, ValueError) as error:
        raise InvalidCursorError from error
    if (
        payload.route_id != context.route_id
        or payload.filter_digest != context.filter_digest
        or payload.direction != context.direction
    ):
        raise CursorContextMismatchError
    return CursorPosition(
        sequence=payload.last_sequence,
        stable_id=payload.last_stable_id,
        snapshot_high_watermark=payload.snapshot_high_watermark,
    )
