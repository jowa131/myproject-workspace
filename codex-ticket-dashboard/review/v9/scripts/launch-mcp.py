#!/usr/bin/env python3
"""Install beside src/ and select the pinned runtime before MCP imports."""

import runpy
import sys
from pathlib import Path


def main() -> None:
    """Discard inherited source paths before starting the protected MCP server."""
    product_root = Path(__file__).resolve().parent
    dependencies = product_root.parent / "deps-20260909-v11"
    sys.path[:] = [
        str(dependencies / relative)
        for relative in (
            "", "Lib", "DLLs", "site-packages", "site-packages/win32",
            "site-packages/win32/lib", "site-packages/pythonwin",
        )
    ] + [str(product_root / "src")]
    _ = runpy.run_module("codex_ticket_dashboard.mcp.server", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
