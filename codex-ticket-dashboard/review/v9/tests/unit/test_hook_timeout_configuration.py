import json
from pathlib import Path


def test_hook_templates_define_event_budgets_and_windows_parity() -> None:
    root = Path(__file__).parents[2]
    template_paths = (
        root / "hooks" / "correction-hooks.example.json",
    )
    expected_timeouts = {
        "SessionStart": 2,
        "UserPromptSubmit": 5,
        "Stop": 5,
        "SubagentStart": 3,
        "SubagentStop": 3,
        "SessionEnd": 3,
    }

    for template_path in template_paths:
        template = json.loads(template_path.read_text(encoding="utf-8"))
        hooks = template["hooks"]
        assert set(hooks) == set(expected_timeouts)
        for event, timeout in expected_timeouts.items():
            handler = hooks[event][0]["hooks"][0]
            assert handler["timeout"] == timeout
            assert handler["commandWindows"] == handler["command"]

        deployable_text = template_path.read_text(encoding="utf-8").lower()
        assert "diagnostic" not in deployable_text
        assert "command_diagnostics" not in deployable_text
