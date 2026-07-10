# Ontology and Second-Brain Audit Task Packet - 2026-07-10

Task:
Audit whether the current Codex, Obsidian, and Wiki operating model supports complete work-unit capture, reliable classification, future AI retrieval, and a durable personal second brain.

Owner project:
`C:\MyProject` / official Wiki `C:\MyProject\wiki`.

Goal:
Produce an evidence-based fit assessment and a prioritized improvement direction without changing the existing knowledge structure or creating an agent definition.

Non-goals:
- Do not store full chat transcripts or raw Codex session logs in the Wiki.
- Do not run Wiki cleanup, deletion, move, rename, compression, or broad metadata normalization.
- Do not create `wiki-curator.toml`, `ontology-curator.toml`, or any recurring automation.
- Do not modify Obsidian settings or Graphify output.
- Do not scan unrelated project documents.

User-visible behavior:
The user receives a four-goal verdict, the gaps that prevent the goals from being guaranteed, the recommended target operating model, approval points, and the next implementation slice.

Files allowed:
- Read: the two named Codex sessions, selected Wiki operating/ontology/curator documents, `00 Home.md`, and `projects/00 Projects.md`.
- Write: this task packet and `C:\MyProject\wiki\knowledge\07 온톨로지와 Codex 작업 적용.md`.

Files excluded:
- Unrelated `projects/*`, raw session exports, secrets, tokens, private logs, `.obsidian/*`, Graphify output, and generated artifacts.

Required context:
- `C:\MyProject\AGENTS.md`
- `C:\MyProject\wiki\01 운영 원칙.md`
- `C:\MyProject\wiki\03 현재 상태.md` Wiki-related sections
- `C:\MyProject\wiki\knowledge\00 전역 기술 지식.md`
- `C:\MyProject\wiki\knowledge\06 Wiki 정리 전담 에이전트 검토.md`
- `C:\MyProject\wiki\knowledge\07 온톨로지와 Codex 작업 적용.md`
- `C:\MyProject\wiki\decisions\ADR-0001 지식 관리 도구.md`

Acceptance criteria:
- Each of the four user goals has a verdict grounded in current files or the two named Codex sessions.
- The assessment distinguishes complete semantic work-unit capture from prohibited raw transcript dumping.
- The proposed target model covers capture, canonical classification, ontology, retrieval, and user review.
- Agent responsibilities are separated into capture coverage, curation, ontology mapping, and context retrieval.
- No cleanup, TOML creation, Graphify edit, or recurring automation is performed.

Verification commands:
```powershell
scripts\wiki-read.ps1 -Path 'wiki\knowledge\07 온톨로지와 Codex 작업 적용.md' -Pattern '네 가지 목적 정합성|Work Unit Record|wiki-coverage-audit|context-retriever|사용자 승인 지점'
scripts\wiki-encoding-check.ps1
git -C C:\MyProject\wiki -c core.quotepath=false status --short
git -C C:\MyProject\wiki diff --check -- 'knowledge/07 온톨로지와 Codex 작업 적용.md'
```

Verification gates:
- `required`: Required audit markers exist in `knowledge/07`.
- `required`: Wiki UTF-8 validation exits successfully.
- `required`: No prohibited artifact or cleanup mutation is introduced.
- `advisory`: Diff check is clean for the edited knowledge document.

Security/privacy notes:
- Record only session identifiers, workspace relevance, decisions, and outcomes needed for the audit.
- Do not copy full prompts, private logs, encrypted reasoning, credentials, or token details into the Wiki.

Generated artifacts:
- This task packet and one reusable Wiki audit section only.

Git dirty-state note:
The Wiki repository was already dirty with modified and untracked user/agent files. Existing changes must be preserved and are not part of this audit.

Handoff location:
`C:\MyProject\wiki\knowledge\07 온톨로지와 Codex 작업 적용.md`.
