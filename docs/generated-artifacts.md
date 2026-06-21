# Generated And Local Artifacts

Generated files and local runtime data should not drive design decisions, code
search, or review unless the task is specifically about those artifacts.

## Default Exclusions

Exclude these from broad searches and code review by default:

- `node_modules/`
- `.next/`
- `dist/`
- `.astro/`
- `.cache/`
- `coverage/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `*.pyc`
- `logs/`
- `runs/`
- `tokens/`
- `secrets/`
- `graphify-out/`

## Search Guidance

Prefer `rg` with explicit excludes for broad scans:

```powershell
rg --glob '!node_modules/**' --glob '!.next/**' --glob '!dist/**' --glob '!__pycache__/**' --glob '!.venv/**' <pattern> C:\MyProject
```

## Git Rules

- Add generated outputs to the closest repository `.gitignore`.
- If an artifact is intentionally tracked, document why in the project README
  or AGENTS file.
- Before starting non-trivial work, record whether dirty files are source,
  docs, generated artifacts, or unrelated local state.

