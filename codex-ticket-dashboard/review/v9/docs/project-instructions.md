# Codex 작업 티켓 대시보드 프로젝트 지침

- 생성일: 2026-09-01 KST
- 초기화 모드: 업데이트, 최대 깊이 3
- 적용 범위: `C:\MyProject\codex-ticket-dashboard`
- 상위 지침: `C:\MyProject\AGENTS.md`
- Git 맥락: 상위 저장소 `C:\MyProject`; 이 디렉터리는 독립 Git 루트가 아님

## 개요 (OVERVIEW)

- 목적: Codex Desktop·CLI 작업을 관찰해 로컬 대시보드의 프로젝트·티켓 상태로 투영한다.
- 제품 방향: Codex -> 원자 spool -> 수집기 -> SQLite WAL -> 로컬 읽기 전용 웹.
- 현재 상태: 역사적 Phase 0 v1.1 `FAIL-BLOCKED`와 v1.2 비침습 재평가 `LIMITED`는 불변입니다. `phase1_authorized=true`는 2026-09-05 승인된 좁은 `MCP-FIRST-DESKTOP-CANDIDATE` 프로필에만 적용하며, 현재 데스크톱 후보는 2026-09-06 사용자의 명시적 수락으로 `MCP-FIRST-DESKTOP-CANDIDATE-USER-ACCEPTED / DESKTOP-SCOPE-COMPLETED`입니다.
- 승인된 데스크톱 후보의 소스·패키지 명세·실행 스크립트·테스트·운영 문서가 현재 존재하며 데스크톱 범위의 사용자 수락이 확인됐습니다. 이는 모바일·Chrome 200% 확대·배포·full v1.3 완료를 의미하지 않습니다.
- 계획 아키텍처 또는 과거 Phase 0 기록만으로 실행·수락·배포 사실을 주장하지 않습니다.

## 권위 원본 (AUTHORITATIVE REFERENCES)

| 우선순위 | 경로 | 용도 |
| --- | --- | --- |
| 1 | `..\docs\design-codex-ticket-dashboard-prototype-v1-20260901.md` | 승인된 v1.3 정식 구현 계약 |
| 2 | `..\docs\task-packet-codex-ticket-dashboard-phase-1-mcp-desktop-prototype-20260905.md` | 2026-09-05 승인된 MCP 중심 데스크톱 실행 범위·게이트 |
| 3 | `..\docs\design-codex-ticket-dashboard-prototype-v1.2-amendment-20260901.md` | 역사적으로 승인·통합된 v1.2 결정 이유 |
| 4 | `..\docs\task-packet-codex-ticket-dashboard-phase-0-compatibility-20260901.md` | Phase 0 v1.1 범위·승인 게이트·합성 시나리오·복구 |
| 5 | `..\wiki\knowledge\14 Codex 작업 티켓 추적 도구 선택.md` | 지속 프로젝트 상태와 인계 |
| 6 | `..\docs\verification-gates.md` | 변경 인지형 검증 단계 |

- 이 파일의 요약과 정식 설계가 다르면 정식 설계를 따른다.
- 이 프로젝트는 승인된 이관 프로젝트가 아니므로 중앙 Wiki가 권위 원본이다.
- 생성된 Wiki 투영을 직접 편집하거나 이곳에 프로젝트 로컬 Wiki 권위를 만들지 않는다.

## 현재 구조 (STRUCTURE)

```text
codex-ticket-dashboard/
├── AGENTS.md
├── README.md · DESIGN.md · config.example.toml · pyproject.toml · uv.lock
├── docs/operator-guide.md
├── scripts/{start-local,stop-local,verify-local}.ps1
├── src/codex_ticket_dashboard/{domain,ingest,mcp,storage,compliance,web}/
├── tests/{unit,integration,e2e,fixtures/synthetic-events}/
└── .omo/evidence/codex-ticket-dashboard-phase-1-mcp-desktop-prototype/
```

## 찾아볼 곳 (WHERE TO LOOK)

| 필요한 정보 | 먼저 읽을 곳 |
| --- | --- |
| 제품 범위와 권한 | 정식 설계 3-5절 |
| Hook·호환성 계약 | 정식 설계 11절 |
| MCP 도구·상태 권한 | 정식 설계 12절·15절 |
| 사건 순서·복구 | 정식 설계 13절·21절과 수정안 5-6절 |
| Git·Wiki 준수 | 정식 설계 19-20절 |
| API·웹 제약 | 정식 설계 23-25절 |
| Phase 0 실행 경계 | Phase 0 패킷 2-9절 |
| 최신 승인 상태 | 중앙 Wiki의 마지막 Codex 대시보드 관련 절 |

## 아키텍처 계약 (ARCHITECTURE CONTRACT)

- 웹은 로컬 관찰자이며 Codex를 제어하거나 티켓을 수정하지 않는다.
- 변경 API의 스텁, 빈 변경 처리기, 역제어 자리 표시자도 만들지 않는다.
- `project_id`는 논리 Codex 프로젝트 ID이고 `repo_key`는 Git common dir ID다. 추정으로 합치지 않는다.
- 미해결 식별은 `UNCLASSIFIED` 또는 `CONFLICT`로 유지하며 상위 Git root를 대체값으로 선택하지 않는다.
- 사건 투영 순서는 파일 감시기의 발견 순서나 파일명 순서가 아니라 명시적 의존성을 따른다.
- MCP 원자 spool 사건이 권위 원본이며 비동기 `PostToolUse` 영수증은 진단용일 뿐이다.
- App Server adapter는 실험적 로컬 프로토타입 전용이다. `thread/list`는 `useStateDbOnly=true`와 명시적 `sourceKinds=["cli","vscode","unknown"]`를 사용하고, `thread/read`는 기본 `includeTurns=false`다. turn 포함 읽기는 고정 합성 allowlist의 단일 thread에만 제한한다. 공식 app-server 명령과 WebSocket이 실험 단계·프로덕션 비지원이라는 성숙도 경계를 Phase 0 로컬 호환성으로 덮어쓰지 않는다.
- 활성 Hook layer는 공존하며 실행 순서를 가정하지 않는다. 동기 Stop 제어에서 observer `decision:block`과 competitor `continue:false`가 함께 있으면 공식 우선순위에 따라 aggregate는 `NOT_CONTINUED`다. 별도 async 정보성 Hook은 원 작업을 제어할 수 없으며 역순 완료에도 snapshot·projection이 불변이어야 한다.
- 저장 내용은 구조화 summary와 제한된 source metadata뿐이다. 사용자 prompt·assistant message·transcript·Hook 출력의 원문 또는 발췌를 DB·spool·진단·성공 archive에 저장하지 않는다.
- 누적 목록은 변경 불가 `created_seq`·`ingest_seq`와 첫 page `snapshot_high_watermark`로 membership·순서를 고정한다. mutable 시각을 cursor 순서에 사용하지 않는다.
- 로컬 데이터는 현재 사용자 전용 `owner-only` Windows ACL과 상속 차단을 요구한다. reparse point·UNC·device path를 거부하고, `127.0.0.1` bind·엄격한 `Host` allowlist·모든 응답의 `Cache-Control: no-store`를 적용하며 별도 인증 token은 만들지 않는다.
- `IN_REVIEW`의 active work-item set은 상태 transaction의 ticket projection as-of 값으로 계산한다. 요청의 `affected_work_item_ids`와 dependency 배열은 비교 claim일 뿐이며 누락·추가로 필수 결과·gate를 우회할 수 없다.
- 새 정책·준수 drift가 기존 `IN_REVIEW`를 무효화하면 collector만 `actor_type=SYSTEM`, `authority=SYSTEM_DERIVED`와 정확한 causation으로 `BLOCKED`에 내린다. 해결 뒤에는 ready-for-review-retry만 표시하고 자동 복원하지 않으며, 현재 as-of 집합·gate를 담은 새 `CODEX_RESULT` 요청이 필요하다.
- Codex는 티켓을 `IN_REVIEW`까지만 전환할 수 있다. 완료·취소·재개는 명시적 사용자 결정만 허용한다.
- `PROJECT_IDENTITY_RESOLVED`의 `project_id=null`은 실제 identity pending 관측과 검증된 registry snapshot을 한 transaction에서 연결하는 bootstrap 예외뿐이다. 임의 resolver와 순환 generic pending은 거부한다.
- `REJECTED`·`DEPENDENCY_FAILED`는 자손에 결정적 순서로 전파하고 dependency graph는 비순환이어야 한다. cycle은 `DEPENDENCY_CYCLE` terminal failure이며 무한 pending을 허용하지 않는다.
- spool 적용은 `APPLIED+archive_state=PENDING` commit, 원자 archive 이동, `ARCHIVED` commit의 두 단계다. 재시작에서 archive hash 불일치·양쪽 부재·중복은 이름 있는 실패로 남기고 성공을 만들거나 중복을 자동 삭제하지 않는다.
- 레지스트리, 정책 스냅샷, Git 권한, Wiki 권한의 불일치·변경 편차는 실패 시 차단(fail closed)한다.

## 권한 게이트 (AUTHORITY GATES)

- 역사적 v1.1 `FAIL-BLOCKED` 판정은 불변이며, `OWNED-RESIDUE-CLEAN` 복구 영수증은 그 판정을 PASS로 바꾸지 않는다.
- v1.2 비침습 재평가 판정은 `LIMITED`이며 당시 `phase1_authorized=false`였다는 역사 기록을 유지한다. 새 모델 턴·Hook/플러그인/config/App Server/Git 재시험 결과로 바꾸지 않는다.
- 2026-09-05 사용자 승인에 따라 `phase1_authorized=true`는 `MCP-FIRST-DESKTOP-CANDIDATE` 프로필에만 적용한다. Phase 1 사건·DB·MCP와 Phase 2 조회 웹의 데스크톱 범위를 결합하며 모바일 구현·QA·수락과 full v1.3 완료는 후속 승인이다.
- 프로젝트 식별은 dashboard `config.toml`의 사용자 승인 registry-only이며 Host project id를 사용하지 않는다. dashboard config 구현은 포함하지만 Codex Hook/plugin/config/App Server 변경·호출·재시험은 제외한다.
- 성공 spool은 `%LOCALAPPDATA%\CodexTicketDashboard\spool\archive\`에 owner-only로 보관하고 자동 삭제하지 않으며 사용자 명시 수동 정리만 허용한다.
- 웹 시작은 명시 `-Port`를 요구한다. 목록 limit은 기본 50·최대 200이고, 한 로컬 프로세스에서 collector만 DB writer이며 HTTP는 query-only다.
- Git mutation, 외부 배포, 예약 작업, 실제 사용자 원문 접근·저장은 금지한다.
- 이전 `init-deep`와 Phase 0 승인 게이트는 역사 기록으로 유지한다. 현재 구현 권한 원본은 2026-09-05 Phase 1 MCP 중심 데스크톱 작업 패킷이며, 새 Hook·plugin·trust·App Server·합성 Git 재시험 권한으로 확대하지 않는다.
- 이번 별도 실행 승인은 역사적 Phase 0을 통과로 재분류하지 않는다. 구현은 새 작업 패킷의 독립 게이트를 따른다.
- 모바일, P2/P3 편집, 외부 SaaS, 예약 실행, heartbeat(주기 상태 확인), 고정 polling, 배포, 광범위한 과거 이관은 이번 프로필 범위 밖이다.

## 관례 (CONVENTIONS)

- 실행 환경: Python 3.12, FastAPI, Jinja2, Uvicorn, Pydantic v2, SQLite WAL.
- UI: 최소 JavaScript를 사용한 서버 렌더링 HTML, `127.0.0.1`의 데스크톱 우선 로컬 접속.
- 테스트: `pytest`와 FastAPI test client, 단위·통합·E2E·합성 픽스처 분리.
- 경로와 명령은 현재 디스크 존재와 해당 작업 증거를 대조한 뒤에만 실행·통과 사실으로 보고한다.
- 설계의 기계 식별자, 사건 이름, 권한 열거값, 경로, 상태 값은 정확히 보존한다.
- 원문 prompt·transcript·assistant message·도구 입출력의 원문 또는 발췌, 자격증명·무제한 환경 정보는 산출물에 넣지 않는다.
- 승인된 호환성 시험에서는 고정 합성 표식만 사용한다.

## 금지 패턴 (ANTI-PATTERNS)

- Phase 0 증거 전에는 Hook 필드, Desktop 동작, App Server 공유, `commandWindows`, Stop continuation을 호스트 검증 완료로 말하지 않는다.
- 합성 시험 중 예상 밖 실제 사용자 스레드나 transcript를 읽지 않는다.
- Hook·수집기·웹이 프로젝트 레지스트리를 자동 생성·수정하지 않는다.
- 의존성 누락 복구에 무제한 재시도, 주기 polling, 시간 순서를 사용하지 않는다.
- 정상 작업 회차 종료, `Stop`, `SessionEnd`, 프로세스 종료를 사용자 수락으로 해석하지 않는다.
- 관찰자가 관찰 대상 작업의 Git commit·push 또는 Wiki 쓰기를 대신하지 않는다.
- 상위 저장소의 관련 없는 변경을 stage·commit·push·clean·reset·revert하지 않는다.
- 새 승인 범위 없이 클라우드 호스팅, GitHub, Slack, Jira, Linear, Trello, Notion, 클라우드 DB를 도입하지 않는다.

## 명령 (COMMANDS)

- 현재 프로젝트에는 `uv sync --locked`, `uv run ruff check .`, `uv run basedpyright src tests`, `uv run pytest -q`와 `scripts/{start-local,stop-local,verify-local}.ps1` 실행 경로가 있다.
- 로컬 웹 시작은 명시 `-Port`를 요구하며, 운영 절차·수락 경계는 `README.md`와 `docs/operator-guide.md`를 따른다.
- 명령 존재, 과거 통과, 현재 실행, 사용자 수락은 각각 별도 사실로 기록한다.
- Phase 0 v1.1의 12개 합성 실행 그룹은 정식 설계 §28.1의 16개 필수 검증 assertion을 포괄했으며 역사적 종합 판정은 `FAIL-BLOCKED`다. 이후 `OWNED-RESIDUE-CLEAN` 복구와 v1.2 비침습 재평가는 새 합성 시험을 실행하지 않은 `LIMITED` 관측이다. 종합 `PASS`는 모든 required surface·scenario가 새로 `PASS`일 때만 가능하며, required `LIMITED`나 실행 전 제외된 required branch는 비활성 capability를 열거한 종합 `LIMITED`, 하나라도 `FAIL-BLOCKED`면 전체 `FAIL-BLOCKED`다. `conditional NOT-RUN`은 실행 전의 명시적 optional/fallback branch에만 허용한다.

## 참고 (NOTES)

- 현재 모듈 경계는 `src/`·`tests/`·`scripts/`·`docs/`에 있다. 독립 소유권·관례가 생길 때에만 하위 `AGENTS.md`를 추가하거나 `init-deep` 재실행을 검토한다.
- 현재 Codegraph 로컬 색인이 없다. 상위 색인은 관련 없는 형제 프로젝트 심볼을 반환할 수 있으므로 이 프로젝트의 근거로 사용하지 않는다.
- LSP 설치·설정은 별도 필요가 확인될 때만 수행하며, 문서 상태 교정만을 위해 추가하지 않는다.
- 완료 보고는 설계 완료, Phase 0 완료, 구현 완료, 검토 완료, 사용자 수락을 구분한다.
- 현재 확정 상태는 `DETAILED-DESIGN-V1.3-USER-ACCEPTED / PHASE-0-V1.1-HISTORICAL-FAIL-BLOCKED / RECOVERY-OWNED-RESIDUE-CLEAN / PHASE-0-V1.2-REASSESSMENT-LIMITED / MCP-FIRST-DESKTOP-EXECUTION-AUTHORIZED / phase1_authorized=true / MCP-FIRST-DESKTOP-CANDIDATE-USER-ACCEPTED / DESKTOP-SCOPE-COMPLETED / FULL-V1.3-NOT-COMPLETED`입니다. 현재 데스크톱 범위에 필요한 다음 개발 단계는 없으며, Chrome 200% 확대는 `DEFERRED_BY_USER_NOT_PASSED`, 모바일·배포·full v1.3 완료는 별도 승인 범위입니다.

## 2026-09-07 원래 목표 교정과 X1 현재 상태

- 현재 제품 판정은 `FOUNDATION-COMPLETE / AUTO-PROJECTION-INCOMPLETE / PRODUCT-GOAL-INCOMPLETE`입니다. 기존 후보 수락·검증과 역사적 Phase 0 판정은 보존합니다.
- `X1 SYNTHETIC-COMPATIBILITY-AUTHORIZED`는 승인되었으나 합성 호환성 probe는 실행 전입니다. `X2`, `X3`은 승인되지 않았습니다.
- 문서 교정은 `gpt-5.6-luna / medium`, probe 구현·privacy/claim 자체검증은 `gpt-5.6-sol / high`, 계약 자료 준비는 `gpt-5.6-luna / medium`으로 Task별 선택합니다. 같은 Host·config·trust·데이터는 순차 처리하고 독립 문서와 probe 준비만 병렬화합니다. 승인 범위의 일반 오류는 원인·영향이 고정된 경우 자율적으로 수정·재검증합니다.


## 2026-09-07 X1 최종 G0 결과 인계

- 원래 목표는 별도 지시 없이 Desktop·CLI 신규·재개·하위 작업을 자동 관찰·투영하는 것입니다. 제품 상태는 `FOUNDATION-COMPLETE / AUTO-PROJECTION-INCOMPLETE / PRODUCT-GOAL-INCOMPLETE`이며 과거 후보 수락은 보존합니다.
- X1 승인에 따라 합성 probe 집중 시험 19개와 소스 8개 해시 대조를 마쳤습니다. CLI 공식 화면에서 정확한 합성 Hook 7개를 개별 신뢰했으나 실제 Host 발화는 미검증입니다. Desktop의 정확한 합성 폴더가 프로젝트 목록에 없고 현재 도구로 열 수 없어 G0은 `BLOCKED`, G1–G11은 `NOT_RUN`입니다.
- 합성 설정 2개를 제거했고 manifest는 `ready=false`입니다. 공식 CLI에서 시험 Hook 활성 0개, 기존 Hook 활성 수 복원과 검증용 프로세스 exit 0을 확인했습니다. 비활성 신뢰 기록 7개는 보존했습니다. 비교 기준 이후 config 26개 구역 중 hooks만 변경됐고 25개는 동일합니다. 그 이전 전체 해시 변동 원인은 미확인이며 전체 설정을 복원하지 않았습니다.
- CLI 조작 중 기존 OMO `create_goal` Hook을 잠시 비활성화했다가 즉시 복구했습니다. 그 사이 모델 턴은 없었습니다. 자체검증을 실제 자동 투영 성공으로 간주하지 않습니다.
- 다음 단계: 사용자가 `C:/MyProject/codex-ticket-dashboard/.omo/probes/correction-host-20260907`를 Desktop 프로젝트로 연 뒤 정확한 등록 경로를 확인합니다. 같은 X1 승인으로 설정·소스 해시·ACL·공식 신뢰를 다시 확인하고 G0부터 재개합니다. X2–X4는 미승인입니다.
- 증거: `C:/MyProject/codex-ticket-dashboard/.omo/evidence/correction-x1-20260907/outcome.md`, `cleanup-root-verification.json`, `probe/cleanup.json`, `probe/verification.json`, `docs-final/root-postflight.json`. 문서 중복 삽입은 총괄이 기존 전체 해시와 일치하는 원본을 복원한 뒤 이 절 하나만 추가하여 수정했습니다.

## 2026-09-08 자동 관찰 제품의 현재 범위

- 현재 목표는 일반 Codex Desktop·CLI 신규·재개·하위 작업의 활동을 별도 기록 지시 없이 수집하고 기존 업무 기록과 연결하여 읽기 전용 화면에 표시하는 것입니다. 미분류·누락·관측 미확인과 사용자 명시 결정은 구분합니다.
- 최신 사용자 지시에 따라 현재 승인 대상의 구현·집중 검증·오류 수정·되돌릴 수 있는 적용은 내부 단계별 재승인 없이 진행합니다. 위의 과거 미승인·미실행 문구는 당시 기록이며 현재 진행 범위를 제한하는 새 승인 절차로 사용하지 않습니다.
- 과거 데스크톱 후보 수락과 역사적 판정은 보존합니다. 이 절의 추가는 새 자동 관찰 제품의 설치 완료, 실제 Codex 작업 검증 통과, 제품 완료 또는 사용자 수락을 뜻하지 않습니다. 구현·검토·설치·실사용 결과는 아래 실행 증거와 인계 기록을 각각 확인하십시오.
- 기존 프로젝트 하나·등록 루트 하나·빈 worktree_roots 범위를 유지합니다. 전역 Hook·설정, 새 프로젝트, 주기 실행·자동 시작·백필·외부 배포는 추가하지 않습니다. PC 재부팅이나 기존 작업 중단 시점과 필수 본인 입력, 최종 사용자 수락은 대신 결정하지 않습니다.
- 모바일 확인은 자동 승인 검토에서 거절되어 BLOCKED_BY_AUTO_REVIEW이며 재시도하거나 통과로 보고하지 않습니다. Chrome 200% 확대의 기존 보류도 유지합니다.
- 기존 수동 시작 명령은 과거 후보의 운영 절차입니다. 보호된 자동 관찰 환경의 실제 적용에는 별도 설치 명세·소스 해시·공식 신뢰 확인과 적용 영수증이 필요합니다. 문서의 포트 48723은 실행 중이라는 증거가 아닙니다.
- 현재 확인 경로: [실행 증거](.omo/evidence/auto-projection-product-20260908/), [실사용 수락 조건과 인계](.omo/evidence/auto-projection-product-20260908/acceptance-and-handoff.md), [자동 관찰 설치와 복구](docs/observation-installation.md). 다음 단계는 고정된 소스와 해당 단계의 실제 증거를 대조하여 적용·실사용 검증을 마치는 것입니다.

## 2026-09-09 비용 통제와 반복 진단 재발 방지

- 사용자의 포괄적 진행 권한은 불확실한 유료 실험이나 무제한 검증의 허가가 아닙니다. 원래 자동 추적 목표를 유지하면서 아래 제한을 우선 적용합니다.
- 진단은 코드·입력/출력 계약 검토부터 시작합니다. 가설, 구분할 증거, 수정할 후보 위치, 성공/실패 뒤 결정이 없는 실험은 실행하지 않습니다.
- 진단 작업의 기본 전체 시간 한도는 10분입니다. 준비, 문서 읽기, 담당 전달, 도구 승인 대기, 결과 정리를 포함합니다. 단계 전환·담당 교체·새 사용자 진행 지시·문맥 압축만으로 한도를 다시 세지 않습니다. 새로 확인한 원인에 대한 구현은 별도 범위와 완료 조건으로 기록합니다.
- 수정이나 새 관측 수단이 없는 같은 입력/설정/기동/명령 재시험은 금지합니다. 실패한 실험을 작은 변형으로 이어 붙이지 않습니다. 한도를 소진하면 해당 접근을 종료하고 확인된 사실·미확인 원인·수행 가능한 다음 결정을 간결히 보고합니다.
- 시험용 Desktop/CLI 모델 요청과 보조 작업자는 기본 0개입니다. 새로 필요한 경우 정확한 코드 변경 또는 새 관측 수단, 그 실행으로 판별할 항목, 기존 근거로 대체할 수 없는 이유, 횟수 상한을 먼저 기록합니다. 관측 결과를 얻을 수 없는 상태에서 메모 파일 읽기 같은 모델 요청을 반복하지 않습니다.
- Astra Ultra 및 추가 검토자를 관성적으로 사용하지 않습니다. 새 작업자의 모델/추론은 상위 비용 라우팅 규칙에 따라 최소 적정 수준을 명시하고, 고비용 선택의 구체적 판단 가치를 기록합니다. 현재 모델을 전환하지 않았으면 전환했다고 보고하지 않습니다.
- 재현 도구의 실행 파일, argv, 셸, cwd, 환경은 실제 실행 계약과 구분합니다. 시험 도구 오류로 판명된 근거는 제품 결함 근거에서 제외합니다. 원인과 연결되지 않은 제품 변경은 정확히 원복하고 그 근거를 재사용하지 않습니다.
- 구성요소 성공, 실제 Host 연결 성공, 제품 완료, 사용자 수락을 구분합니다. 파일/설정 존재나 직접 호출 성공을 실제 자동 기록 성공으로 바꾸어 보고하지 않습니다.
- 검증 모음은 변경 범위의 가장 가까운 경우만 실행합니다. 이미 통과한 무변경 범위의 전체 시험/빌드/화면 검증/추가 리뷰를 붙이지 않습니다. 코드가 바뀌지 않은 문서·설계 판단에는 런타임 시험을 실행하지 않습니다.
- 원인 미확정 상태에서 관찰자에게 업무 완료·의미 있는 티켓 생성 권한을 넘기거나 식별·권한 검사를 완화하지 않습니다. 새 전송 경로/주기 수집/대규모 진단기는 별도 설계 판단 없이 추가하지 않습니다.
