# C:\MyProject Working Agreement

## Wiki-first workflow

The official knowledge base is `C:\MyProject\wiki`.

1. Read the relevant Wiki documents before starting work.
2. Perform and verify the requested work.
3. Update the Wiki before considering the task complete.

## Common vibe-coding agent harness

All development work under `C:\MyProject` should use the common agent harness
defined in `C:\MyProject\wiki\knowledge\01 토큰 효율 에이전트 하네스.md`.

Use these roles as the default workflow for feature work, fixes,
investigations, deployment work, and handoffs:

1. Planning agent
2. Architect agent
3. Code development agent
4. UI development agent
5. Unit test agent
6. E2E test agent
7. Security agent
8. Deployment/Git agent
9. Documentation agent

For small tasks, one Codex thread may perform several roles sequentially, but
the role contracts must still be respected: input, editable scope, output,
verification command, completion criteria, and handoff.

For each non-trivial task, create or identify a task packet that states:

- goal
- non-goals
- files allowed
- acceptance criteria
- verification commands
- handoff expectations

Use `C:\MyProject\docs\task-packet-template.md` as the default task packet
shape, and `C:\MyProject\docs\verification-gates.md` to label checks as
required, advisory, blocked-by-external, or not-applicable.

Do not treat the harness as extra ceremony. Its purpose is to keep work scoped,
testable, secure, and easy for the next thread to continue.

Record requirements, decisions and reasons, environment details, implementation
changes, verification results, errors and resolutions, current status,
unresolved issues, and next steps.

Use `C:\MyProject\wiki\knowledge` for reusable technical knowledge and general
vibe-coding practices. Keep project-specific details in project-specific Wiki
documents.

Use separate threads for independent topics or project tasks. Before switching
threads, write a concise handoff to the Wiki.

Never write secrets to the Wiki. Graphify output is generated reference
material and does not override approved Wiki records.

## Workspace state and generated artifacts

Before non-trivial work, record whether the relevant repositories are dirty and
whether dirty files are source, docs, generated artifacts, or unrelated local
state. `scripts\myproject-status.ps1` provides a quick overview.

Generated or local runtime artifacts should not be used as broad search or
review input unless the task is specifically about them. Follow
`C:\MyProject\docs\generated-artifacts.md` and add project-specific generated
paths to the closest `.gitignore`.

For browser-facing or published content changes, use
`C:\MyProject\docs\ui-content-regression-checklist.md` and report desktop and
mobile coverage for affected routes.

For Yulchive feature projects, keep ownership boundaries aligned with
`C:\MyProject\docs\yulchive-integration-boundary.md`: feature projects own
source and tests, while `yulchive-astro` is the public integration point.

## Token and log hygiene

Wiki-first does not mean dumping whole Wiki files into the model context. Before
reading large Korean Markdown files, search for the relevant section with `rg`
or `Select-String`, then read only the necessary lines. Avoid full-document
`Get-Content` on long Wiki or session files unless the user explicitly needs the
whole file.

For Korean Wiki text on Windows PowerShell, prefer the safe reader:

```powershell
scripts\wiki-read.ps1 -Path <path> -StartLine <n> -First <n>
scripts\wiki-read.ps1 -Path <path> -Pattern <regex>
```

To verify that the Wiki files themselves are valid UTF-8, run:

```powershell
scripts\wiki-encoding-check.ps1
```

If direct PowerShell reads are unavoidable, set UTF-8 output for short reads:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -LiteralPath <path> -Encoding UTF8 | Select-Object -First <n>
```

If Korean output looks garbled, silently retry with the safe reader or the UTF-8
direct-read form before continuing. Do not tell the user that the Wiki is
garbled or has an encoding problem unless `scripts\wiki-encoding-check.ps1`
actually fails. Do not feed garbled full-document output back into the
conversation.

When investigating Codex usage, use `scripts\codex-token-usage.ps1` or parse
only `token_count` events from `%USERPROFILE%\.codex\sessions\...\rollout-*.jsonl`.
Do not print full session metadata, full JSONL logs, or unrelated tool schemas.

If the Windows sandbox reports helper launch errors, do not repeat the same
sandboxed command. Check `.codex\.sandbox\sandbox.<date>.log` and verify that
`codex-windows-sandbox-setup.exe` and `codex-command-runner.exe` exist next to
the active `codex.exe` on PATH. After a repair, verify with one short sandboxed
command before resuming broader exploration.
