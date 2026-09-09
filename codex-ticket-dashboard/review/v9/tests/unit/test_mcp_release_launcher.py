import importlib.machinery
import runpy
import sys
from pathlib import Path

import pytest


def test_launcher_selects_new_protected_source_and_preserves_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Path(__file__).parents[2] / "scripts" / "launch-mcp.py"
    product = tmp_path / "product-20260909-v12"
    package = product / "src" / "codex_ticket_dashboard"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    launcher = product / "launch-mcp.py"
    launcher.write_bytes(source.read_bytes())
    entry = runpy.run_path(str(launcher))["main"]
    arguments = [str(launcher), "--config", "approved.toml", "--data-root", "private-data"]
    calls: list[str] = []

    def run_server(name: str, *, run_name: str, alter_sys: bool) -> dict[str, object]:
        specification = importlib.machinery.PathFinder.find_spec("codex_ticket_dashboard", sys.path)
        assert specification is not None
        assert specification.origin == str(package / "__init__.py")
        assert str(tmp_path / "old-product" / "src") not in sys.path
        assert "untrusted-search-path" not in sys.path
        assert sys.argv == arguments
        assert run_name == "__main__"
        assert alter_sys is True
        calls.append(name)
        return {}

    monkeypatch.setattr(runpy, "run_module", run_server)
    monkeypatch.setattr(
        sys, "path", [str(tmp_path / "old-product" / "src"), "untrusted-search-path"]
    )
    monkeypatch.setattr(sys, "argv", arguments.copy())
    entry()
    assert calls == ["codex_ticket_dashboard.mcp.server"]
