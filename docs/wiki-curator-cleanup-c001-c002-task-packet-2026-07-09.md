# wiki-curator cleanup C001/C002 task packet proposal — 2026-07-09

Task:
Prepare a user-reviewable cleanup task packet for audit candidates C001 and C002. This packet does not authorize execution by itself.

Owner project:
`C:\MyProject\wiki`

Goal:
Define a limited future cleanup worker scope for C001 and C002 so the user can approve or reject the exact work before any Wiki cleanup happens.

Non-goals:
- No cleanup execution.
- No deletion, move, rename, compression, link rewrite, index rewrite, or metadata normalization.
- No `wiki-curator.toml` or other agent/TOML generation.
- No Graphify modification or promotion to official record.
- No full Vault scan.
- No secrets, tokens, raw Codex transcripts, or full session logs.
- No C003 scope expansion.

User-visible behavior:
After user approval, a future cleanup worker would make only the approved edits listed here and then report exact changed files, verification results, unresolved risks, and the next step. Until then, this packet is proposal-only.

Files allowed:
- `C:\MyProject\wiki\03 현재 상태.md`
- `C:\MyProject\wiki\history\2026-07-09 Wiki 기록 원칙과 curator 인계.md`
- `C:\MyProject\wiki\history\2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md`
- `C:\MyProject\wiki\knowledge\06 Wiki 정리 전담 에이전트 검토.md`
- `C:\MyProject\wiki\knowledge\07 온톨로지와 Codex 작업 적용.md`

Files excluded:
- `C:\MyProject\wiki\.obsidian\*`
- `C:\MyProject\wiki\projects\*`
- Graphify generated outputs
- Raw Codex session logs or transcripts
- Any file outside `Files allowed`

Required context:
- `C:\MyProject\docs\task-packet-template.md`
- `C:\MyProject\docs\verification-gates.md`
- `C:\MyProject\docs\wiki-curator-audit-read-only-task-packet-2026-07-09.md`
- `C:\MyProject\wiki\knowledge\06 Wiki 정리 전담 에이전트 검토.md`
- `C:\MyProject\wiki\knowledge\07 온톨로지와 Codex 작업 적용.md`
- `C:\MyProject\wiki\history\2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md`

## Candidate scope

| Candidate ID | Proposed future action | Allowed edit type | Approval required before execution | Stop condition |
| --- | --- | --- | --- | --- |
| C001 | Keep `03 현재 상태.md` as short current status and link long-lived Wiki curator principles to `knowledge/06` or the handoff/audit record if duplicated | Add or adjust a short cross-reference only; do not remove meaning without explicit line-level approval | Yes | Stop if the section contains operational current-state information that would be lost by shortening |
| C002 | Preserve the handoff document as chronological transfer evidence and keep canonical role contract wording in `knowledge/06` | Add or adjust a short cross-reference only; do not move or delete handoff content without explicit line-level approval | Yes | Stop if the handoff wording is needed to reconstruct thread context |

## Output tables

A future cleanup worker must return these tables after execution.

### Change table

| File | Candidate ID | Lines changed | Change summary | Preserved meaning | Verification |
| --- | --- | --- | --- | --- | --- |
| TBD | C001 or C002 | TBD | TBD | TBD | TBD |

### Risk table

| Risk | Candidate ID | Mitigation | Status |
| --- | --- | --- | --- |
| Current status loses useful live context | C001 | Keep status concise but retain current next step and link to deeper record | Must be checked before edit |
| Handoff loses chronological evidence | C002 | Preserve handoff content unless user approves exact deletion | Must be checked before edit |

### Hold table

| Item | Reason held | Release condition |
| --- | --- | --- |
| C003 | Requires scope expansion outside current corpus | User approves a separate wireless/telecom cleanup audit |
| `wiki-curator.toml` | Requires repeated safe audits and explicit approval | User approves agent/TOML creation after 2-3 safe runs |
| Graphify changes | Generated reference cannot override official Wiki | User approves a separate Graphify usage task |

Acceptance criteria:
- Packet contains C001 and C002 only.
- Packet states `No cleanup execution`.
- Packet lists exact allowed files and excluded files.
- Packet includes prohibited actions and user approval points.
- Packet includes output tables for future worker reporting.
- Packet includes required/advisory/not-applicable verification gates.
- Packet preserves the rule that cleanup, TOML generation, and Graphify modification remain blocked until user approval.

Verification commands:

```powershell
$p = 'docs\wiki-curator-cleanup-c001-c002-task-packet-2026-07-09.md'
$markers = @(
  'Task:',
  'Goal:',
  'Non-goals:',
  'Files allowed:',
  'Files excluded:',
  'Acceptance criteria:',
  'Verification commands:',
  'Verification gates:',
  'Output tables:',
  'User approval points:',
  'C001',
  'C002',
  'No cleanup execution'
)
$text = Get-Content -LiteralPath $p -Encoding UTF8 -Raw
$missing = @($markers | Where-Object { $text -notlike "*$_*" })
if ($missing.Count -gt 0) { throw "missing packet markers: $($missing -join ', ')" }
```

```powershell
scripts\wiki-encoding-check.ps1
```

```powershell
git -C C:\MyProject -c core.quotepath=false status --short -- `
  docs/wiki-curator-cleanup-c001-c002-task-packet-2026-07-09.md `
  wiki/history/2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md `
  wiki/knowledge/07 온톨로지와 Codex 작업 적용.md
```

Verification gates:

| Gate | Level | Command or check | Result expectation | Evidence |
| --- | --- | --- | --- | --- |
| Packet marker check | required | Marker validator in `Verification commands` | All markers present | Command output |
| Wiki encoding | required | `scripts\wiki-encoding-check.ps1` | Exit 0 | Command output |
| Scope status | required | `git status --short -- <allowed paths>` | Only intended proposal/Wiki files changed by this task | Command output |
| Cleanup execution | not-applicable | Direct cleanup command | Must not run | This packet is proposal-only |
| TOML generation | not-applicable | Agent/TOML file creation | Must not run | Explicit non-goal |
| Graphify mutation | not-applicable | Graphify edit command | Must not run | Explicit non-goal |

Security/privacy notes:
- Do not record secrets, tokens, raw session logs, or full private transcripts.
- If evidence is needed, record only concise command results and file paths.
- Do not inspect unrelated project files or the full Vault.

Generated artifacts:
- This proposal document only.
- No generated Graphify artifacts.
- No generated TOML agent files.

Git dirty-state note:
Before execution, the future worker must run `git -C C:\MyProject\wiki -c core.quotepath=false status --short` and record whether changed files are pre-existing, proposal-related, or unrelated. Existing user/agent changes must not be reverted.

User approval points:
- Approve or reject C001.
- Approve or reject C002.
- If approved, choose whether the future cleanup worker may edit only cross-links or also shorten duplicated prose.
- Confirm that C003 remains out of scope.
- Confirm that `wiki-curator.toml`, cleanup execution beyond exact approved lines, and Graphify modification remain blocked.

Handoff location:
If the user approves execution, the cleanup worker must record results in:
- `C:\MyProject\wiki\history\2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md`
- `C:\MyProject\wiki\knowledge\07 온톨로지와 Codex 작업 적용.md`

Next step:
Wait for user approval of C001 and/or C002 before executing any cleanup.

## 2026-07-10 execution result

User approval:
`본문 삭제 없이 cross-link만 허용`.

| Candidate ID | Execution status | Edit type | Evidence | Constraint after execution |
| --- | --- | --- | --- | --- |
| C001 | C001 execution completed | Added one cross-link line to `C:\MyProject\wiki\03 현재 상태.md` | `GREEN: C001 cross-link marker present`; `DIFFCHECK: current additions=1 deletions=0` | No further cleanup without explicit approval |
| C002 | C002 execution completed | Added one cross-link line to `C:\MyProject\wiki\history\2026-07-09 Wiki 기록 원칙과 curator 인계.md` | `GREEN: C002 cross-link marker present`; `DIFFCHECK: handoff additions=1 deletions=0` | No further cleanup without explicit approval |

Result:
cross-link-only execution completed. No body deletion, move, rename, TOML generation, Graphify mutation, or full Vault scan was performed. `deletions=0`.
