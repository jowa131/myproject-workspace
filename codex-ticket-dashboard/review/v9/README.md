# Codex 작업 티켓 대시보드 v9 교차검증 소스

사용자가 지정한 설치 v9를 Claude Code가 교차검증하도록 공유합니다. **제품 미완료**이며 마지막 실제 요청에서 UPS/Stop3초 시간 초과, Stop관측1건, 업무사건0건이 확인됐습니다. 읽기 전용 분석과 해결안 작성부터 진행하십시오.

## 읽기 순서

1. `docs/handoff.md`: 목표, 실패 경과, 지침, 코드 위치, 질문, 잔여 TASK.
2. `docs/design-v1.3.md`, `docs/correction-plan.md`: 원래 목표와 승인 계약. 후속 구현과 다른 부분은 승인 근거를 확인합니다.
3. `src/codex_ticket_dashboard/lifecycle/command.py`, `config.py`, `recording_guidance.py`, `mcp/official_context.py`, `lifecycle/initial_preflight.py`.
4. `evidence/`의 해당 회차 결과. 과거 부분 검사 통과를 전체 자동 등록 성공으로 보지 마십시오.

## 소스 범위와 식별

- `src/`97개 파일은 설치 v9 source-manifest와 바이트/해시가 일치하도록 복사했습니다. `source-manifest.json`의 해시는 제품 기능 성공을 보장하지 않습니다.
- v9의 Typer/pydantic-settings 구현이 기준입니다. 작업 폴더의 argparse/tomllib 경량화 후보는 포함하지 않습니다.
- 적용 Hook 명령은 `evidence/hook-trust-approval-20260909/hooks-host-powershell-v9.json`에 있습니다. PowerShell이 제공하는 본문에서 `src/observe.cmd`를 호출합니다. cmd/bash Host 검증으로 대체하지 마십시오.
- `pyproject.toml`, `uv.lock`, `config.example.toml`은 공유 시점의 프로젝트 보조 자료입니다. `installed-dependencies.json`은 실제v9 설치 메타데이터입니다. 의존성을 새로 설치하거나 실행한 것은 아닙니다.
- 설치 v9에는 시험 소스가 포함되지 않았습니다. 미검증 수정이 섞인 현재 tests를 v9 시험으로 복사하지 않았습니다. 과거 시험 결과와 범위는 evidence와 handoff에 있습니다.
- 실제 config, Python/라이브러리 바이너리, DB/spool/archive, 사용자 대화/세션 원문, 자격증명은 포함하지 않습니다. 별도 운영 설치·자동 실행을 뜻하지 않습니다.

## 경로 대응

| 원래 자료 | 공유본 |
|---|---|
| design-codex-ticket-dashboard-prototype-v1-20260901.md | docs/design-v1.3.md |
| codex-auto-projection-correction-20260907.md | docs/correction-plan.md |
| auto-projection-product-execution-20260908.md | docs/execution-plan.md |
| 프로젝트 AGENTS.md | docs/project-instructions.md |
| handoff-original-goal-gap-and-correction-20260907.md | docs/original-goal-handoff.md |
| automatic-recording-static-review-20260909.md | docs/static-review.md |
| automatic-recording-root-cause-analysis-20260909.md | docs/failure-analysis.md |
| execution-process-root-cause-20260909.md | docs/process-audit.md |
| release-remaining-tasks-20260908.md | docs/remaining-tasks.md |
| .omo/evidence/goal-alignment-audit-20260908/ 아래 선택 근거 | evidence/ 아래 같은 폴더명 |

기존 문서는 출처 보존을 위해 복사했으므로 과거 경로/완료/승인 문구가 남습니다. 원래 메타데이터를 현재 실행 사실로 확대하지 마십시오. 추가 자료가 없으면 추측하지 말고 그 한계를 적으십시오.

## Claude Code 요청

이 폴더의 v9 소스와 설계/실패 근거를 읽기 전용으로 교차검증하고 최소 해결안을 작성해 주세요. 현재 작업 폴더나 v10 대신 이 src를 기준으로 하세요. 원인·증상·시험 오류를 구분하고, 현재 접근을 유지할 가치와 수정 대상 파일, 최소 확인 계획, 실패 시 종료 조건을 제시해 주세요. 추가 구현·테스트·설치·Hook 변경·모델 요청·화면 조작은 시작하지 마세요.
