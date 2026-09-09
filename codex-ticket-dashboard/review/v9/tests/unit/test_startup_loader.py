import json
import subprocess
import sys
from pathlib import Path

import pytest

from codex_ticket_dashboard.config import ConfigLoadError, load_dashboard_config
from codex_ticket_dashboard.storage.path_security import initialize_data_root


def _config_text(data_root: Path, workspace: Path) -> str:
    return "\n".join(
        (
            "schema_version=1",
            "data_root=" + json.dumps(str(data_root)),
            "[[projects]]",
            "schema_version=1",
            'project_id="prj_synthetic"',
            'label="Synthetic"',
            "roots=[" + json.dumps(str(workspace)) + "]",
            'wiki_authority="CENTRAL_WIKI"',
            'authority_source_ref="synthetic.md"',
            'authority_source_sha256="' + "a" * 64 + '"',
        )
    )


def _module_command(module: str, *arguments: str) -> list[str]:
    return [sys.executable, "-m", module, *arguments]


def test_startup_modules_do_not_eagerly_import_typer_or_settings() -> None:
    probe = "\n".join(
        (
            "import sys",
            "import codex_ticket_dashboard.config",
            "import codex_ticket_dashboard.lifecycle.command",
            "raise SystemExit(any(name in sys.modules for name in ('typer', 'pydantic_settings')))",
        )
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", probe], capture_output=True, check=False
    )

    assert result.returncode == 0


def test_config_reads_only_explicit_toml_and_is_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config_path = tmp_path / "dashboard.toml"
    _ = config_path.write_text(_config_text(tmp_path / "runtime", workspace), encoding="utf-8")
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "environment-canary"))

    config = load_dashboard_config(config_path)

    assert config.data_root == tmp_path / "runtime"
    assert config.model_config.get("frozen") is True


@pytest.mark.parametrize(
    "content",
    (
        "schema_version=[",
        'schema_version=1\ndata_root="C:\\\\Synthetic"\napi_key="PRIVATE_CANARY"',
        'schema_version=1\n[[projects]]\nschema_version=1',
    ),
)
def test_config_rejects_invalid_missing_or_extra_toml_without_leaking_content(
    tmp_path: Path, content: str
) -> None:
    config_path = tmp_path / "invalid.toml"
    _ = config_path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigLoadError) as raised:
        _ = load_dashboard_config(config_path)

    assert raised.value.code == "CONFIG_INVALID"
    assert "PRIVATE_CANARY" not in str(raised.value)


def test_config_cli_success_and_redacted_error(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    valid = tmp_path / "dashboard.toml"
    _ = valid.write_text(_config_text(tmp_path / "runtime", workspace), encoding="utf-8")
    invalid = tmp_path / "invalid.toml"
    _ = invalid.write_text('schema_version=1\ndata_root="PRIVATE_CANARY"', encoding="utf-8")

    success = subprocess.run(  # noqa: S603
        _module_command("codex_ticket_dashboard.config", "--check", str(valid)),
        capture_output=True, check=False, text=True
    )
    failure = subprocess.run(  # noqa: S603
        _module_command("codex_ticket_dashboard.config", "--check", str(invalid)),
        capture_output=True, check=False, text=True
    )

    assert success.returncode == 0
    assert json.loads(success.stdout)["status"] == "READY"
    assert failure.returncode == 2
    assert failure.stdout == ""
    assert "CONFIG_INVALID" in failure.stderr
    assert "PRIVATE_CANARY" not in failure.stderr


def test_hook_cli_rejects_invalid_recognized_source_kind_with_redacted_exit_one(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    paths = initialize_data_root(tmp_path / "runtime")
    config_path = tmp_path / "dashboard.toml"
    _ = config_path.write_text(_config_text(paths.root, workspace), encoding="utf-8")

    result = subprocess.run(  # noqa: S603
        _module_command(
            "codex_ticket_dashboard.lifecycle.command", "--config", str(config_path),
            "--source-host", "host_synthetic", "--source-kind", "not-a-source-kind"
        ),
        input=b'{"prompt":"PRIVATE_RAW_CANARY"}', capture_output=True, check=False
    )

    assert result.returncode == 1
    assert result.stdout == b""
    assert json.loads(result.stderr) == {"code": "ADMISSION_UNVERIFIED", "recording": "UNVERIFIED"}
    assert b"PRIVATE_RAW_CANARY" not in result.stderr


def test_hook_cli_rejects_unknown_argument_with_redacted_exit_one() -> None:
    result = subprocess.run(  # noqa: S603
        _module_command(
            "codex_ticket_dashboard.lifecycle.command",
            "--private-unknown-option",
            "PRIVATE_ARGUMENT_CANARY",
        ),
        input=b'{"prompt":"PRIVATE_RAW_CANARY"}',
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == b""
    assert json.loads(result.stderr) == {"code": "INPUT_INVALID", "recording": "UNVERIFIED"}
    assert b"PRIVATE_ARGUMENT_CANARY" not in result.stderr
    assert b"PRIVATE_RAW_CANARY" not in result.stderr


def test_hook_cli_accepts_user_prompt_without_echoing_raw_input(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    paths = initialize_data_root(tmp_path / "runtime")
    config_path = tmp_path / "dashboard.toml"
    _ = config_path.write_text(_config_text(paths.root, workspace), encoding="utf-8")
    raw = json.dumps(
        {
            "session_id": "synthetic",
            "turn_id": "own_turn",
            "cwd": str(workspace),
            "hook_event_name": "UserPromptSubmit",
            "prompt": "PRIVATE_RAW_CANARY",
        }
    ).encode()

    result = subprocess.run(  # noqa: S603
        _module_command(
            "codex_ticket_dashboard.lifecycle.command", "--config", str(config_path),
            "--source-host", "host_synthetic", "--source-kind", "cli"
        ),
        input=raw, capture_output=True, check=False
    )

    assert result.returncode == 0
    assert result.stderr == b""
    assert json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert b"PRIVATE_RAW_CANARY" not in result.stdout
