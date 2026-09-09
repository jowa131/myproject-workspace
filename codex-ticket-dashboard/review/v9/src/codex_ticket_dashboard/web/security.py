"""Loopback request checks and uniform local security response headers."""

from dataclasses import dataclass
from typing import Final, Literal

from fastapi import Request
from starlette.datastructures import MutableHeaders

_FORWARDED_HEADERS: Final = frozenset(
    {"forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"}
)
_SECURITY_HEADERS: Final = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    """Configure the exact loopback port accepted by this one process."""

    port: int

    def allowed_hosts(self) -> frozenset[str]:
        """Return the only accepted Host header values."""
        return frozenset({f"127.0.0.1:{self.port}", f"localhost:{self.port}"})


def request_rejection_code(
    request: Request, config: SecurityConfig
) -> Literal["HOST_NOT_ALLOWED", "FORWARDED_HEADERS_FORBIDDEN"] | None:
    """Reject forwarded spoofing and any host outside the exact loopback allowlist."""
    if any(header in request.headers for header in _FORWARDED_HEADERS):
        return "FORWARDED_HEADERS_FORBIDDEN"
    if request.headers.get("host") not in config.allowed_hosts():
        return "HOST_NOT_ALLOWED"
    return None


def apply_security_headers(headers: MutableHeaders) -> None:
    """Apply the mandatory local-only response protections in one place."""
    headers.update(_SECURITY_HEADERS)
