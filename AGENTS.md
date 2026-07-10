# C:\MyProject Working Agreement

## Evidence-first answers

Do not answer from guesswork for project, account, trading, deployment, code,
data, or operational facts.

- Verify names, identifiers, mappings, statuses, prices, dates, command
  results, file contents, API responses, and account-specific facts from the
  current workspace, Wiki, logs, command output, or an allowed external source
  before presenting them as true.
- If a fact is not verified, say so clearly instead of making a plausible
  statement. Prefer "확인된 정보가 아닙니다" or "현재 근거로는 단정할 수 없습니다".
- If verification is possible with available tools, perform the verification
  before answering.
- If a previous answer was based on an unchecked assumption, correct it
  explicitly and update the Wiki when the lesson is reusable.

## KST time standard

Unless the user explicitly names another timezone, treat every user command,
automation, schedule, trigger window, deadline, log summary, report timestamp,
and follow-up time under `C:\MyProject` as Asia/Seoul time (KST, UTC+09:00).

- Before creating, updating, validating, or reporting an automation, convert
  any scheduler-native time representation back to KST and state the KST
  execution window.
- If a tool stores cron or RRULE hours in UTC, calculate the UTC fields from
  the intended KST time first, then verify the stored schedule by converting it
  back to KST before reporting success.
- When current time affects safety, trading, deployment, or data decisions,
  check the current local KST time with a tool and use exact dates and times.
- If the user says "today", "tomorrow", "morning", "noon", "close", or
  similar relative time words, resolve them in KST unless the user explicitly
  says otherwise.
- Record reusable timezone findings in the Wiki without secrets.

## User-approved automation semantics

For any automation, monitor, reminder, follow-up, scheduler, heartbeat, cron,
background thread, or other recurring/token-consuming behavior under
`C:\MyProject`, never invent or silently choose the execution cadence.

- Explicit user approval is required before creating or changing any schedule,
  polling interval, recurrence frequency, trigger window, retry/backoff policy,
  catch-up/backfill behavior, target thread fan-out, or token-consuming
  monitor loop.
- "Make it automatic", "monitor it", "catch up", "late start", or similar
  intent is not approval for a concrete interval such as 5 minutes, 10 minutes,
  hourly, daily, or continuous polling. If the cadence was not specified, ask
  for the cadence or propose options without saving an active automation.
- Do not create an ACTIVE recurring automation from an inferred schedule. Use a
  draft/suggested automation or a documented plan until the user explicitly
  approves the exact cadence and execution window.
- Before enabling a recurring automation, report the exact KST schedule,
  expected token/work cost driver, stop condition, duplicate-send guard, and
  target thread/workspace. Record the approval and verification result in the
  Wiki without secrets.
- If an unapproved or ambiguous recurring automation is discovered, pause it
  first when it is safe to do so, verify the paused state, record the incident,
  and wait for explicit user-approved semantics before re-enabling it.

## Wiki-first workflow

The official knowledge base is `C:\MyProject\wiki`.

1. Read the relevant Wiki documents before starting work.
2. Perform and verify the requested work.
3. Update the Wiki before considering the task complete.

Every Codex work unit must leave a Wiki record by default. This includes
project work, projectless/general Codex chats, investigations, planning,
failed-but-instructive attempts, automation changes, subagent handoffs, and
operational decisions. Keep the entry concise and centered on the core outcome,
meaningful decisions, evidence, current status, unresolved issues, and next
steps. Do not omit a work item merely because the record may later feel noisy.
Noise reduction is a separate cleanup/review job for a designated agent or
thread; the current worker records first, then pruning can happen later.

When any goal, instruction, task, investigation, fix, plan, automation change,
or delegated work unit is finished, the final report must include both the
completed outcome and the next step. If no meaningful next action remains,
state that no next step is currently required. The report should stay concise
and evidence-based: what was done, how it was verified, unresolved issues if
any, and the recommended next step.

Wiki-first does not mean raw transcript dumping. Never write secrets, access
tokens, full private logs, or unnecessary raw command output. Summarize the
meaningful part and point to local evidence paths when needed.

For Codex threads, automations, and follow-up jobs that work on a subproject
under `C:\MyProject`, include `C:\MyProject` itself as a workspace root or
writable root, not only the subproject directory. The Wiki is a sibling of most
project repositories, so a workspace limited to `C:\MyProject\<project>` can
read project code but fail the required Wiki update with a sandbox access
denial.

Preferred root policy: start Codex for subproject work with `C:\MyProject` as
the primary working root, then name the target subproject in the prompt or add
it as an additional writable directory. For Codex CLI, the verified pattern is
`codex -C C:\MyProject` or `codex -C C:\MyProject --add-dir
C:\MyProject\<project>`. If a thread starts inside a subproject and cannot read
or write `C:\MyProject\wiki`, stop and restart or re-open it with
`C:\MyProject` included rather than continuing without the Wiki update.

Root access is not a mandate to read the whole vault. For subproject work, read
only the relevant project Wiki entry, the current-status section needed for the
handoff, and shared `knowledge` or `decisions` documents that directly affect
the task. Do not spend context on unrelated sibling project Wiki files unless
the task crosses that boundary or the user explicitly asks for a cross-project
review.

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

### Review subagent timeout rule

Review subagents are gate helpers, not blockers for unbounded exploration.

- Spawn only review subagents whose verdict is necessary for the current gate.
- Give each reviewer one narrow responsibility, fixed files, fixed evidence, and no broad repository exploration unless explicitly requested.
- Require reviewers to return `APPROVE`, `REVISE`, or `INCONCLUSIVE`.
- Default wait policy: wait 120 seconds, send one nudge asking for a verdict from the checked scope only, then wait 60 seconds.
- If no final verdict arrives after that, record the reviewer as `INCONCLUSIVE` and continue with direct evidence or completed required gates.
- Never count a silent, running, closed, or interrupted reviewer as approval.

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

## IBS Care release notes

For IBS Care, any user-installable code change must bump both
`versionName` and `versionCode` before producing APK/ZIP artifacts. Do not
replace hashes under the same app version for a changed installable build.
When handing an installable IBS Care build to the user, present the ZIP artifact
first, not the raw APK path; the APK path may be included only as supporting
detail.

When `C:\MyProject\ibscare-android` produces a new app version, versionCode, or
phone-test APK/ZIP artifact, updating the local-only release note is required
before the work is considered done.

- Update `C:\MyProject\yulchive-astro\src\data\ibsCareReleases.mjs` and the
  local-only release note pages under
  `C:\MyProject\yulchive-astro\src\pages\ibs-care*` with the new version,
  verification date, artifact names, SHA256 hashes, and key verified behavior.
- Keep `/ibs-care` and `/ibs-care/*` local-only, excluded from public sitemap
  and RSS exposure, and verify that the page remains accessible only from the
  current PC/local loopback path.
- Record the release note update and verification result in both
  `C:\MyProject\wiki\projects\ibscare-android.md` and
  `C:\MyProject\wiki\projects\yulchive-astro.md`.

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
