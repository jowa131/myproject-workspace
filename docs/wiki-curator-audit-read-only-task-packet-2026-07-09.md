# Wiki Curator Audit Read-Only Task Packet - 2026-07-09

Task:
Run the first `wiki-curator-audit` as a read-only audit over a deliberately small Wiki document set. The audit may produce an audit report and a proposed cleanup task packet, but it must not perform cleanup.

Owner project:
`C:\MyProject` / official Wiki `C:\MyProject\wiki`.

Goal:
Identify duplicate, misplaced, stale, oversized, or under-indexed Wiki records only within the approved first audit corpus, then present safe cleanup candidates for user approval.

Non-goals:
- Do not create `wiki-curator.toml`.
- Do not run Wiki cleanup.
- Do not modify, delete, move, rename, or compress existing Wiki pages.
- Do not edit Graphify output, Obsidian settings, project code, generated files, or unrelated project Wiki records.
- Do not read the full vault or broaden into unrelated sibling projects.
- Do not record secrets, tokens, full private logs, or full conversation transcripts.

User-visible behavior:
The user receives a concise read-only audit result with candidate cleanup rows, risk labels, hold items, and explicit approval points before any future cleanup worker runs.

Files allowed:
- Read only:
  - `C:\MyProject\wiki\03 현재 상태.md`
  - `C:\MyProject\wiki\knowledge\00 전역 기술 지식.md`
  - `C:\MyProject\wiki\knowledge\05 무선통신과 이동통신 규격 지식.md`
  - `C:\MyProject\wiki\knowledge\06 Wiki 정리 전담 에이전트 검토.md`
  - `C:\MyProject\wiki\decisions\ADR-0001 지식 관리 도구.md`
  - `C:\MyProject\wiki\history\2026-07-09 Wiki 기록 원칙과 curator 인계.md`
- Write only if the user explicitly starts this audit task:
  - `C:\MyProject\wiki\history\2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md`
  - An optional follow-up cleanup task packet under `C:\MyProject\docs\`, if and only if it is only a proposal and contains no executed cleanup.

Files excluded:
- All other files under `C:\MyProject\wiki`, including unrelated `projects/*`, `history/*`, `knowledge/*`, and `.obsidian/*`.
- Any `graphify-out`, Graphify cache, generated reference output, Codex session JSONL, SQLite state, raw logs, screenshots, build artifacts, API responses, or credential-bearing files.
- Any file outside `C:\MyProject` unless the user grants a new explicit scope.

Required context:
- `C:\MyProject\AGENTS.md` applies as the workspace working agreement.
- `C:\MyProject\docs\task-packet-template.md` is the packet shape.
- `C:\MyProject\docs\verification-gates.md` supplies verification gate labels.
- The read-only audit role contract is in `C:\MyProject\wiki\knowledge\06 Wiki 정리 전담 에이전트 검토.md`.

읽을 문서:
| Purpose | Exact path | Read method |
| --- | --- | --- |
| Current status and latest curator handoff | `C:\MyProject\wiki\03 현재 상태.md` | Search first for `Wiki`, `curator`, `정리 전담`, `audit`, then read only relevant line ranges with `scripts\wiki-read.ps1`. |
| Knowledge index | `C:\MyProject\wiki\knowledge\00 전역 기술 지식.md` | Read full file with `scripts\wiki-read.ps1`; it is small. |
| Wireless/telecom classification sample | `C:\MyProject\wiki\knowledge\05 무선통신과 이동통신 규격 지식.md` | Read full file with `scripts\wiki-read.ps1`; it is small. |
| Curator role contract | `C:\MyProject\wiki\knowledge\06 Wiki 정리 전담 에이전트 검토.md` | Read full file with `scripts\wiki-read.ps1`; it defines output and prohibitions. |
| Knowledge management decision | `C:\MyProject\wiki\decisions\ADR-0001 지식 관리 도구.md` | Read full file with `scripts\wiki-read.ps1`; it is small. |
| Handoff for this curator work | `C:\MyProject\wiki\history\2026-07-09 Wiki 기록 원칙과 curator 인계.md` | Read full file with `scripts\wiki-read.ps1`; it limits scope and next action. |

읽지 않을 문서:
- Do not scan the whole vault with broad `Get-Content`, full recursive readers, or broad semantic summarizers.
- Do not read unrelated project pages such as `projects/yulchive-astro.md`, `projects/auto-trading.md`, `projects/ibscare-android.md`, or other sibling project records unless the user later approves a new audit scope.
- Do not read Codex raw sessions, app state databases, Graphify output, generated artifacts, Obsidian workspace files, or private logs.

금지 작업:
- `wiki-curator.toml 생성 금지`.
- `Wiki cleanup 실행 금지`.
- `Graphify 수정 금지`.
- No deletion, move, rename, compression, content rewrite, link rewrite, index rewrite, or metadata normalization.
- No "noise" removal by judgment alone.
- No secret, token, full transcript, or raw log capture.
- No user approval inference from this packet. The audit may recommend; it may not execute.

산출물 표 형식:
Cleanup candidate table:
| Candidate ID | Original location | Proposed location/action | Core content to preserve | Duplicate or placement evidence | Risk | User approval needed | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

Index candidate table:
| Candidate ID | Missing or stale index/link | Current evidence | Proposed index/link change | Risk | User approval needed |
| --- | --- | --- | --- | --- | --- |

Classification proposal table:
| Candidate ID | Current document | Suggested class (`knowledge`/`projects`/`history`/`decisions`/draft) | Reason | Risk |
| --- | --- | --- | --- | --- |

Hold list:
| Item | Reason to hold | Missing evidence | Needed user decision |
| --- | --- | --- | --- |

Approval request table:
| Approval point | Candidate IDs | Exact future files | Future worker allowed actions | Verification required before completion |
| --- | --- | --- | --- | --- |

Acceptance criteria:
- Required: The audit result references only the approved corpus and does not introduce facts from excluded files.
- Required: Every cleanup candidate has exact path evidence, preservation notes, risk, and a user approval requirement.
- Required: The audit result includes a hold list for anything that lacks evidence or may alter meaning.
- Required: No cleanup, TOML creation, Graphify edit, deletion, move, rename, or content rewrite is performed.
- Advisory: The audit may suggest a later cleanup task packet, but only as a proposal awaiting user approval.

Verification commands:
```powershell
git -C C:\MyProject\wiki status --short
scripts\wiki-read.ps1 -Path 'wiki\history\2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md' -Pattern 'Candidate ID|Approval point|Hold list|wiki-curator.toml 생성 금지|Wiki cleanup 실행 금지|Graphify 수정 금지'
scripts\wiki-encoding-check.ps1
git -C C:\MyProject\wiki diff --stat
```

Verification gates:
Gate:
Level: required
Command or check: `git -C C:\MyProject\wiki status --short` before and after the audit.
Result: Must show no unexpected existing Wiki page mutation beyond the explicitly allowed audit report path.
Evidence: Paste a concise status summary, not raw unrelated logs.
Notes: Existing dirty files must not be reverted.

Gate:
Level: required
Command or check: `scripts\wiki-read.ps1` on the audit report markers.
Result: Must find candidate, hold, approval, and prohibition markers.
Evidence: Marker output.
Notes: If no cleanup candidates exist, the report must say so and still include the hold and approval sections.

Gate:
Level: required
Command or check: `scripts\wiki-encoding-check.ps1`.
Result: Must pass after writing the audit report.
Evidence: Command exit 0.
Notes: Report encoding problems only if this script fails.

Gate:
Level: advisory
Command or check: `git -C C:\MyProject\wiki diff --stat`.
Result: Used to confirm the audit did not mutate unrelated files.
Evidence: Diff stat.
Notes: Dirty files that existed before the audit are not audit failures unless changed by the audit worker.

Security/privacy notes:
- Do not include passwords, tokens, account identifiers, API keys, credential files, private raw logs, full session transcripts, or unnecessary local metadata.
- Summarize evidence by path and line range. Do not paste large raw document bodies.
- Treat Graphify as generated reference only; approved Wiki records take precedence.

Generated artifacts:
- This packet is a planning artifact.
- The future audit report is allowed only when the user starts the audit task.
- No TOML, cleanup patch, generated graph, raw log export, or vault-wide index is generated by this packet.

Git dirty-state note:
The Wiki repository was dirty before this packet was prepared. Existing modified and untracked files must be treated as pre-existing user/agent work and must not be reverted or normalized by the audit.

사용자 승인 지점:
1. Before any audit scope expands beyond the six approved corpus documents.
2. Before any cleanup worker modifies, moves, deletes, renames, compresses, or rewrites Wiki content.
3. Before generating or installing `wiki-curator.toml`.
4. Before treating Graphify output as anything more than generated reference material.
5. Before merging multiple candidate rows into one broad cleanup task.

Handoff location:
- This packet: `C:\MyProject\docs\wiki-curator-audit-read-only-task-packet-2026-07-09.md`
- Current handoff source: `C:\MyProject\wiki\history\2026-07-09 Wiki 기록 원칙과 curator 인계.md`
- Future audit report, only after user starts the audit: `C:\MyProject\wiki\history\2026-07-09 wiki-curator-audit 1차 읽기 전용 감사.md`
