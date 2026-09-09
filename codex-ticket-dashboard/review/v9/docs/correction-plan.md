# codex-auto-projection-correction-20260907 - Work Plan

> 최신 사용자 지시 반영 (2026-09-08): 현재 자동 수집·대시보드 목표의 구현, 집중 검증, 오류 수정, 대상 범위 내 되돌릴 수 있는 적용과 문서 정리는 단계별 재승인 없이 진행합니다. 내부 단계 구분은 추가 승인 사유가 아닙니다. PC 재부팅/기존 작업 중단 시점, 도구로 처리할 수 없는 필수 본인 입력, 해결 불가한 필수 정보, 최종 사용자 수락만 별도로 다룹니다. 병렬 소유권 분리와 Astra medium/high 방침을 유지합니다. 근거: `.omo/evidence/correction-autonomous-scope-20260908/decision.json`.


> 현재 실행 상태 갱신 (2026-09-08): X1은 이미 사용자 승인되어 문서 교정과 합성 검증·정리를 완료했습니다. 판정 `X1_SYNTHETIC_COMPATIBILITY_VERIFIED_WITH_CONSTRAINTS`, 제품 `PRODUCT-GOAL-INCOMPLETE`. 아래 최초 초안의 미승인/미착수 설명은 역사이며, 현재 승인 경계 표와 최종 결과를 우선합니다. X2–X4는 별도입니다. 근거: `.omo/evidence/correction-x1-remaining-20260908/outcome.json`; 다음 패킷: `.omo/drafts/correction-x2-handoff-20260908.md`.


> 2026-09-07 사용자 승인 모델 방침: 이 교정 작업의 신규 개발 담당은 모두 `gpt-6-astra`로 통일합니다. 일반 구현·고정 시험은 `medium`, 복잡한 원인 분석·설계 판단은 `high`입니다. 아래 과거 Sol/Terra/Luna 배정은 당시 계획 기록이며 새 생성에는 이 승인 방침을 우선합니다. 같은 성공 시험의 반복·중복 조사는 줄이고 실제 결함에 필요한 검증만 수행합니다.

## TL;DR (For humans)
**목적:** 일반 Codex 작업만 해도 신규·재개·하위 작업과 진행·차단·검토·명시적 수락이 대시보드에 이어지고, 누락도 보이도록 교정합니다.

**방안:** 기존 저장·수집·화면 기반을 재사용합니다. 활동 발생을 확실하게 기록하는 경로와 현재 작업 모델이 의미를 정리하는 경로를 분리합니다. 현재 컴퓨터에서 실제 발화가 입증된 뒤에만 병렬 개발을 시작합니다.

**완료 기준:** 실제 Desktop·CLI 일반 작업으로 15개 수락 시나리오를 검증하고 사용자가 그 범위를 명시적으로 수락해야 합니다. 기반 시험만으로 제품 완료를 판단하지 않습니다.

**규모와 위험:** 큰 교정 작업입니다. 예상 실행 토큰은 55–96k이며 실측이 아닙니다. 개인정보·사용자 결정 권한·Windows 생명주기와 재시작이 주요 위험입니다.

**승인할 결정:** 우선 정확한 합성 호환성 시험 변경·복구안을 검토합니다. 자동 시작·전역 적용·과거 백필은 묶어서 승인하지 않습니다. 현 문서는 계획이며 구현은 시작하지 않았습니다.

---

> TL;DR (machine): LARGE / HIGH-RISK / 8 tasks + 4 final checks / EXECUTION-NOT-AUTHORIZED

## Scope
### Must have

- 작성일: 2026-09-07 KST. 상태: `CORRECTION-PLAN-DRAFT / EXECUTION-NOT-AUTHORIZED`.
- 사용자 승인 범위: 교정 작업 패킷·병렬 조직·토큰 효율 설계 작성. 제품 코드, Hook, 사용자 설정, 플러그인, App Server, 자동 시작, 기존 Wiki·Git 변경은 이번 작성에 포함하지 않는다.
- 불변 목적: **여러 Codex Desktop·CLI 신규·재개 작업을 별도 등록이나 대시보드 지시 없이 자동으로 관찰하여 프로젝트·티켓·Task·Subtask의 진행, 대기, 차단, 검토, 명시적 사용자 결정을 읽기 전용 화면에서 확인한다. 기록 누락도 드러나야 한다.**
- 구현 수단의 실패는 목표 삭제의 근거가 아니다. 필수 기능 미지원이면 `BLOCKED` 또는 `PARTIAL`, 미검증이면 `UNVERIFIED`로 남기며 제품 완료를 선언하지 않는다.
- 현 제품 상태: `FOUNDATION-COMPLETE / AUTO-PROJECTION-INCOMPLETE / PRODUCT-GOAL-INCOMPLETE / CORRECTION-PLAN-NOT-YET-APPROVED`.
- 기존 수락·99개 시험·Phase 0 판정은 해당 시점·기반 후보의 역사로 보존한다. 현재 파일 해시·실제 실행·자동 투영·사용자 수락을 각각 구분한다.

### 권위와 근거

작업 기준 경로는 `C:/MyProject/codex-ticket-dashboard`이며 상위 저장소는 `C:/MyProject`다.

| 근거 | 적용 범위 |
| --- | --- |
| `docs/handoff-original-goal-gap-and-correction-20260907.md` §2–3, §8–10 | 교정 목적과 실제 수락 12개; SHA-256 `88c13dc757196ab14d40da430409fc7f374519ab5da1faefe899c01a4e5c3c21` |
| `../docs/design-codex-ticket-dashboard-prototype-v1-20260901.md:52` | 무개입 신규 수집부터 개인정보 비저장까지 원래 성공 기준 |
| 같은 설계 `:335`, `:508`, `:885`, `:1409` | Hook·하위 에이전트, 사용자 결정, Stop 필수 집합, 전체 완료 기준 |
| `../docs/task-packet-codex-ticket-dashboard-phase-1-mcp-desktop-prototype-20260905.md:11` | MCP 중심 기반의 좁은 과거 실행 범위; 자동 관찰 완료 근거 아님 |
| `../wiki/knowledge/14 Codex 작업 티켓 추적 도구 선택.md:948`, `:967` | 역사적 후보 수락·운영 활성화; 현행 실시간 상태 근거 아님 |
| 이전 작업 `01a058c2-1d39-7fb2-8d4e-dedd62677fc9`의 2026-09-07 교정·인계 응답 | 원래 목표를 비목표로 이동하고 좁은 완료 판정을 확대했다는 오류 확인. 대화 원문은 산출물에 복제하지 않음 |
| `../docs/verification-gates.md`, `../wiki/knowledge/01 토큰 효율 에이전트 하네스.md` | 변경면 기반 검증과 작은 인수인계 |

### 목표 추적표

| ID | 독립적으로 증명할 결과 | 담당 작업 | 필수 수락 |
| --- | --- | --- | --- |
| G1 | Desktop·CLI 신규·재개·압축 뒤 활동이 자동 기록됨 | 2, 3, 4, 8 | A1, A4, A9, A13 |
| G2 | 프로젝트/티켓/Task/부모·자식 연결; 실패도 미분류로 노출 | 3, 4, 5 | A2, A3, A14 |
| G3 | 대기·차단·검토·명시적 사용자 결정과 Git/Wiki 근거 | 5, 6 | A5, A6, A10 |
| G4 | 누락·중복·역순·중단·재시작이 성공으로 위장되지 않음 | 4, 6, 8 | A7, A8, A9, A15 |
| G5 | 원문 비저장·권한 분리·관찰 대상 비차단·읽기 전용 웹 | 3–8 | A7, A10, A11, A12 |
| G6 | 사용자가 실제 로컬 화면에서 관찰 결과와 한계를 확인함 | 7, 8, F1–F4 | 전체 추적표와 별도 사용자 수락 |

### Must NOT have (guardrails, anti-slop, scope boundaries)

- 원래 자동 투영 목표를 비목표로 이동하거나 `mcp_tool` 등록 자체를 제품 완료로 판단하지 않는다.
- 웹 변경 API, Codex 역제어, 외부 SaaS·배포, 자동 commit/push, Hook·수집기의 Wiki 쓰기를 만들지 않는다.
- 실제 prompt·assistant message·transcript·Hook/도구 입출력 원문이나 발췌를 DB/spool/archive/진단/로그/웹/검증 산출물에 저장하지 않는다. 예외 로그·임시 파일도 포함한다.
- 과거 전체 작업 백필·전역 프로젝트 registry 자동 확대·무한 재시도·주기 polling·heartbeat·자동 시작을 추가하지 않는다.
- 모바일·200% 확대·full v1.3의 기존 보류를 통과로 바꾸지 않는다. 자동 투영 수락과 full v1.3 수락 상태를 별도로 표시한다.
- 사용자 소유 dirty 파일을 정리·덮어쓰기·stage·commit하지 않는다. 현재 소스 상당수가 상위 저장소 미추적이므로 HEAD 기반 빈 worktree를 현재 구현이라고 취급하지 않는다.

### 제안 아키텍처와 분기 규칙

```text
Desktop·CLI 실제 생명주기
  -> 짧은 로컬 command Hook: 허용 metadata만 정규화
  -> 관찰 사건 전용 admission + 기존 보호 spool writer
  -> 단일 collector -> lifecycle/업무 투영 -> 로컬 조회 웹

현재 작업 모델: 승인된 최소 통합 지침
  -> 기존 일곱 MCP 도구 -> 업무 사건 spool

Stop: DB + incoming + identity/dependency pending의 같은 회차 집합 검사
  -> 정상 종료 또는 최대 1회 보정 요청
  -> 미해결/귀속 불명은 명시적 불완전 기록
```

1. **관찰과 의미 판단 분리:** Hook은 실제 활동 발생·부모 관계만 증명한다. 티켓 분류·결과·사용자 결정은 현재 작업 모델의 기존 MCP 경로를 사용한다. 관찰 adapter는 `CODEX_RESULT`/`USER_EXPLICIT`를 생성하지 않는다. 미분류 활동은 티켓 연결 전에도 조회 가능해야 한다.
2. **준비 시점 독립:** 시작·종료 관찰은 MCP 연결 준비나 HTTP/collector 가동에 의존하지 않는 command Hook으로 고정한다. 기존 spool의 ACL·containment·원자 기록을 재사용한다. MCP 전용 admission을 호출해 관찰 사건을 `MCP_TOOL` 또는 `RESOLVED`로 위장하지 않는다.
3. **MCP tool Hook은 필수 경로가 아님:** 현재 공식 문서에는 연결된 MCP 도구를 직접 호출하는 `mcp_tool`이 있다. 하지만 연결 전 시작과 종료의 제약 때문에 이를 단일 수집 경로로 선택하지 않는다. 현재 일곱 도구에 생명주기 payload를 억지로 넣거나 원문을 전달하지 않는다. [공식 Hooks 문서](https://learn.chatgpt.com/docs/hooks)
4. **최소 통합 지침:** Hook은 정상 경로에서 모델 문맥을 출력하지 않는다. 기존 MCP 서버의 초기화 `instructions`에 서버 도구 간 기록 계약을 담는 방안을 선택한다. 첫 512자는 자체 완결되게 만든다. task 2는 합성 MCP 서버의 일반적 지침 전달 능력만 확인하며, 실제 문안은 task 5에서 작성하고 task 8에서 그 최종 문안·서버 hash의 Host 수신을 검증한다. 이는 모델 안내이며 발화 보장이 아니다. 지침 유실·MCP 부재는 Stop과 관측 범위 검사에서 미완료로 남긴다. 전역 AGENTS 수정이나 매 도구 추가 문맥은 사용하지 않는다. [공식 MCP instructions 계약](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
5. **Stop 회차 연결:** 보정이 새 turn을 만들면 원본→보정 관계를 명시적으로 기록한다. `(session, original_turn, ordinal=1)`의 단일 소비권으로 재시작·동시 Hook·압축에도 2회 보정을 막는다. 원본과 보정 turn을 같은 문자열로 덮어쓰지 않는다. 판단은 DB·spool·pending의 합집합이며 async 영수증은 필수 집합에서 제외한다.
6. **비차단:** 정상 관찰의 출력은 빈 성공 또는 안전한 구조화 진단이다. 도구 입력 변경·도구 차단·`continue:false`를 관찰자가 사용하지 않는다. Stop은 승인된 1회 보정만 요청하고 실패 후 종료를 허용한다. 다른 Hook이 continuation을 막으면 요청과 최종 결과를 분리한다. 결과를 관측할 수 없으면 `UNKNOWN`이다.
7. **정직한 관측 한계:** Hook 전체 비활성/미신뢰와 저장소 전면 실패 때 독립 관측원 없이 모든 미발화 사건을 복원할 수 없다. 다음 정상 사건 또는 명시적 시작 점검에서 coverage를 `UNVERIFIED`/`GAP_DETECTED`로 표시한다. 즉시 전수 누락 감지가 필수인데 Host 근거가 없으면 제품 게이트를 차단하고 다른 수단의 승인을 구한다. 무승인 polling·App Server·원문 파싱으로 메우지 않는다.
8. **식별·권한:** registry 무일치 `UNCLASSIFIED`, 복수 `CONFLICT`; thread/turn/parent 연결은 공식 식별자만 쓴다. subagent Hook의 parent session+turn+agent_id를 보존하며 agent_id를 child session_id로 가정하지 않는다. 실제 자식 session 대응이 없으면 그 관계는 미확인으로 남긴다. 제목·시간·같은 cwd로 합치지 않는다. 결정 사건은 연결된 사용자 turn과 현재 ticket·전이·미소비 조건을 함께 검증한다. ‘Stop 발생’, ‘좋아 보임’, 도구 성공을 수락으로 취급하지 않는다.
9. **재시작:** 자동 시작과 데이터 복구는 별개다. 이번 교정 기본 검증은 재부팅 뒤 사용자가 승인한 수동 시작 절차에서 새 사건 연결까지 확인한다. 무인 가용성은 자동 시작 방식의 별도 승인 전 미충족으로 남긴다.
10. **지원 실패:** Desktop/CLI/부모·자식 필수 계약 중 하나라도 불충족이면 task 2에서 구현 확산을 멈춘다. 원래 목표를 유지한 차단 보고와 대안 계약을 제출한다. App Server는 실험적 진단 후보이며 자동 대체 수단이 아니다.

## Verification strategy

자동 검증은 에이전트가 수행하되 Hook trust·운영 활성화 승인·사용자 최종 수락은 검증기가 대행할 수 없다.

- 이번 계획 작성: 문서 구조·근거 링크·의존성·보호 파일 해시 검사만. 제품 시험 0, 빌드 0, 브라우저 QA 0.
- 실행 시: 보안·권한·복구는 먼저 실패하는 집중 시험을 추가하는 TDD + pytest. UI는 해당 route 실제 화면·기능 확인. 개별 worker는 자기 변경 검증만 한다.
- 각 실행 전 `Change class / Observed change surface / Risk boundary / Expected decision value / Estimated cost / Escalation trigger` 기록. 100개 이상 또는 전체 시험은 집중 시험 뒤 남은 공유 회귀 위험을 문서화한 경우만 실행한다.
- 증거 root `E=.omo/evidence/codex-auto-projection-execution-<승인일>/`; 작업마다 입력 manifest hash, 변경 파일 hash, 실제 명령·종료 코드·assertion 수·실패 ID를 저장한다. 원문 로그 대신 합성 ID와 구조화 결과를 사용한다.
- 새 아래 파일/명령은 **계획상 생성 대상**이며 현재 존재·실행·통과한 것으로 해석하지 않는다. `uv run --locked pytest -q <해당 파일>`; `uv run --locked ruff check <변경 파일>`; `uv run --locked basedpyright <변경 Python 파일>`을 사용한다. 잠금 변경이 불필요하면 의존성을 추가하지 않는다.

### 실제 수락 행렬

| ID | 실제 시나리오 | 통과 증거 / 실패 판정 |
| --- | --- | --- |
| A1 | 새 Desktop 작업과 새 CLI 작업에 일반 합성 요청만 전달 | 대시보드 도구 언급 없이 thread/turn 활동 생성; 한 Host 누락도 전체 PASS 금지 |
| A2 | 합성 파일 변경 작업 | 자동 preflight→ticket→Task 연결, 실제 결과와 변경 범위 일치 |
| A3 | 설명·상태 질문 | `DISCUSSION_LOG` 또는 명시적 미분류 활동; 조용한 유실 없음 |
| A4 | 기존 작업 재개 | 기존 식별 유지, 새 활동만 추가, 기존 사건 중복 투영 없음 |
| A5 | 사용자 답변 대기와 작업 차단 | `WAITING_USER`/`BLOCKED`와 실제 행동·사유·다음 단계 일치 |
| A6 | 일반 최종 응답 | 해당 Task·Git·Wiki·summary·status 인과 집합 충족; 부적용 gate는 근거 표시 |
| A7 | 기록 1개 생략, 보정 실패, competitor Hook 충돌 | 최대 1회 요청·최종 귀속 분리, 재누락 후 종료·불완전 표시 |
| A8 | collector 중지 중 기록, 역순/중복, apply/archive crash | spool 보존, 재시작 뒤 동일 사건 1회 투영, 손상은 이름 있는 오류 |
| A9 | Codex 종료·PC 재부팅 후 수동 런타임 시작 | DB·archive 유지와 신규·재개 활동 연결; 자동 시작 PASS로 표현 금지 |
| A10 | 명시 수락 없음/수락/취소/재개·오래된 결정 재사용 | 수락 전 `COMPLETED` 0; 일치한 최신 명시 결정만 원자 소비 |
| A11 | 합성 원문 canary·민감키를 입력/오류에 포함 | 모든 저장·실패·로그·웹에 원문·발췌·비밀값 0 |
| A12 | 웹 변경 요청·외부 Host·cache 검사 | 변경/역제어 거부, query-only, no-store·loopback 유지 |
| A13 | 세션 압축·동시 turn·보정 turn | 식별 관계 유지, 재등록·보정 예산 초기화 없음 |
| A14 | 부모 작업에서 하위 에이전트 시작/종료, 결과 역순 | 실제 parent/child 연결·별도 Task 결과, 부모/자식 완료 자동 추론 금지 |
| A15 | Hook 미신뢰/비활성, MCP 미준비, data-root 쓰기 실패 | 본 작업 지속, 관측 범위 불명/불완전 표시; 전수 감지 보장 불가를 숨기지 않음 |

실제 Codex Host와 브라우저를 사용한다. 수동 MCP 호출이나 DB 직접 삽입으로 A1–A6/A9/A14를 대체하지 않는다. 합성 fixture 시험은 실패 경계 증거이며 실제 무개입 사용 증거와 별도다.

## Execution strategy
### Parallel execution waves

1. **승인·호환성 단계:** 1a의 비활성 변경·복구 패킷 작성→X1 승인→1b 문서 교정→2→3 순차. 현재 Host와 공통 계약이 확정되기 전에 구현 worker를 늘리지 않는다.
2. **분리 구현 단계:** 4와 5 병렬. 다른 디렉터리·시험·합성 data root 사용. 6은 둘의 결과가 결속된 후 진행한다.
3. **표시·실제 사용 단계:** 7→8 순차. 상태 계약을 먼저 검증한 뒤 실제 Host·브라우저·재시작을 확인한다.
4. **최종 검증 단계:** F1–F4. 읽기 전용 감사는 병렬 가능하며 Host·포트·DB·파일을 바꾸는 QA는 항상 단독 실행한다.

단계별 작업 수를 채우기 위한 인위적 분할은 하지 않는다. 동시 실행 수는 고정하지 않으며, 실행 가능한 독립 Task와 공유 자원·조정 비용으로 결정한다. 동일 실제 Host/설정/SQLite를 변경하는 작업은 단일 소유자가 순차 실행한다.

### 사용자 확정 운영 원칙 — 2026-09-07 추가 반영

이 절은 아래 조직표·모델 예시·작업별 배정·의존성 표보다 우선한다. 목적은 개발·구현·테스트 중 서로 영향을 주지 않는 작업을 병렬로 수행해 시간을 줄이고, Task마다 충분한 성능의 모델을 골라 토큰을 절약하는 것이다. 병렬 조직 자체나 인원 확대는 목적이 아니다.

- **Task 단위 독립성:** 실행 전 선행 산출물, 읽기/쓰기 파일, schema/API 계약 버전, DB/data root, port/process, 사용자 설정과 검증 데이터를 대조한다. 미충족 의존성이 없고 다른 작업의 결과를 무효화하지 않는 Task만 동시에 실행한다.
- **개발·테스트 동시 진행:** 계약이 확정된 모듈 구현과 별도 시험 파일/합성 데이터의 준비, 완료된 모듈의 집중 시험과 다른 독립 모듈 구현은 병렬 가능하다. 시험 중 같은 소스를 수정하거나 같은 DB·포트·Host를 재설정하지 않는다. 시험 증거를 해당 source hash에 결속하고 변경 후에는 영향 시험만 다시 실행한다.
- **유동적인 배정:** 아래 단계와 의존성 표는 초기 배정안이다. 총괄이 실제 의존성·소유권·자원 격리와 기대 시간 절감 근거를 기록하면 Task를 분할·통합·재배치할 수 있다. 필수 선행 계약·보안 게이트·수락 조건은 제거하지 않는다. 추가 인원의 문맥 전달·중복 조사 비용이 절감 효과보다 크면 순차 실행하거나 기존 에이전트를 재사용한다.
- **Task별 모델 선택:** 담당자 A–E에 모델을 고정하지 않는다. 단순 문서·반복적인 확인은 `gpt-5.6-luna medium`, 기존 구조의 일반 구현·집중 시험은 `gpt-5.6-terra high`, 실제 Windows 생명주기·동시성·개인정보·상태 권한·복구 판단은 `gpt-5.6-sol high`를 출발점으로 삼는다. 시험도 난이도·위험에 따라 선택하며 역할명만으로 큰 모델을 배정하지 않는다.
- **모델 조정:** 생성/재배정 시 가용 모델, Task 위험, 추론 수준, 예상 시험·토큰·시간과 선택 이유를 기록하고 명시적으로 설정한다. 승인된 목표·예산·권한 내에서 필요한 조정은 총괄이 판단한다. 상위 모델 전환은 현재 접근의 한계와 기대 해결 가치를 기록한 뒤 시행한다. 사용자 지정 모델이 아닌 추천 모델의 미가용은 동등 위험을 감당하는 대안으로 조정하고 알린다. 명시 지정 모델·예산을 바꿔야 하면 사용자에게 묻는다. `xhigh/max/ultra`·불필요한 추가 검토는 기본 선택하지 않는다.

### 개발 중 자율 판단과 질문 기준

- 구현 오류·테스트 실패·호환성 차이·통합 충돌은 총괄이 증거를 확인하고 원인 가설→최소 재현→해결안 선택→수정→영향 검증으로 처리한다. 단순 실패, 첫 접근의 실패, 합리적인 내부 구현 선택 때문에 사용자에게 해결을 떠넘기지 않는다.
- 수정 범위·Task 순서·병렬 구성·모델·집중 시험을 승인 범위 안에서 자율 조정한다. 차단된 Task만 보류하고 독립적으로 유효한 작업은 계속한다. 같은 실패를 근거 없이 반복하거나 실패 시험을 약화·삭제하지 않는다.
- 필수 Host 기능 실패는 의존 구현과 완료 판정을 차단한다. 허용된 범위의 원인 조사·대안 비교·집중 재검증은 스스로 수행하며, 기능을 비목표로 옮기거나 검증되지 않은 성공으로 대체하지 않는다. 새로운 운영 권한이 필요한 대안은 적용하지 않고 검토 가능한 변경안까지 준비한다.
- **질문하는 경우:** 사용자의 목적·제품 선택을 바꿔야 하는 경우, 미승인 권한·비용 상한·범위를 확대해야 하는 경우, 사용자만 제공할 수 있는 정보·접근 권한이 필요한 경우, 되돌리기 어려운 조치, 또는 실행 가능한 해결 경로를 검토해도 해소되지 않는 문제에 한한다. 질문에는 확인한 사실, 시도와 실패 이유, 가능한 선택지, 권장안과 영향을 간결히 포함한다.
- 진행 중 필요한 판단은 짧은 증거 기록과 상태 보고로 남기며 승인 요청으로 바꾸지 않는다. 사용자가 이미 승인한 행동을 다시 승인받지 않는다. 이 자율 판단 승인은 제품 구현·설정 적용·자동화·최종 사용자 수락에 대한 아직 없는 권한을 생성하지 않는다.
- **정지·재시도 경계:** 개발 문제 해결은 고정 횟수만으로 포기하지 않되, 새로운 정보 없는 반복·무제한 탐색·자동 비용 증가는 하지 않는다. 다음 시도의 판단 가치가 없거나 필요한 권한/정보가 없을 때만 그 Task를 차단한다. 제품의 Stop 보정 최대 1회 계약은 개발 중 문제 해결 재시도와 별개이며 그대로 유지한다.

### 조직·모델·비용 제안

아래 시간·토큰과 모델은 **초기 실행 추정·배정 예시**이며 실측·과금 견적·담당자별 고정 모델이 아니다. 토큰은 읽기+출력 총량의 계획값이며 캐시·추론·도구 schema 비용에 따라 달라질 수 있다. Task가 구체화되면 실제 난이도와 독립성을 반영해 갱신한다. 사용자 승인 예산 상한은 임의로 늘리지 않는다.

| 책임과 소유권 | 모델 / 추론 | 작업 | 예상 집중 사례 | 예상 시간 / 토큰 |
| --- | --- | --- | --- | --- |
| 총괄: 목표·권한·공통 계약 승인·통합·Wiki 교정 승인안 | 현재 주 작업; 별도 총괄 생성 없음 | 1, F1, F4 | 문서/계약 대조 | 25–55분 / 6–12k |
| A: 공통 schema·Windows Hook·식별·Stop·Host 호환성 | `gpt-5.6-sol high` | 2, 3, 4, 6 | 단계별 8–16 | 105–175분 / 20–32k |
| B: lifecycle 투영·기존 MCP 의미 연결 | `gpt-5.6-sol high` | 5 | 12–18 | 50–90분 / 10–18k |
| C: 수집 문제·관측 범위 조회 표시 | `gpt-5.6-terra high` | 7 | 4–6 + 화면 | 30–50분 / 5–9k |
| D: 실제 Host 수락 실행; 구현자와 독립 | `gpt-5.6-sol high` | 8, F3 | 행렬 15개, Host별 확장 | 60–120분 / 10–18k |
| E: 개인정보·상태 권한 변경분 검토 | `gpt-5.6-sol high` | F2 | 코드+기존 증거만 | 25–45분 / 4–7k |

- 전체 초기 추정 55–96k 토큰, 직렬 환산 5–9시간이며 보장치나 승인된 지출 상한이 아니다. 병렬 4/5는 첫 기회일 뿐이고 개발·구현·테스트의 추가 독립 Task도 위 기준으로 병렬화한다. 실제 경과 시간은 승인 대기·PC 재부팅·Host 지원·자원 격리에 좌우된다. task 2 차단 시 의존 구현을 시작하지 않으며, 허용된 진단과 독립 작업만 가치·비용을 판단해 진행한다.
- A/B는 각각 단일 책임·기존 에이전트 재사용. 같은 schema/migration 파일이 필요하면 B/A가 직접 수정하지 않고 총괄에 변경 요청을 보내 3의 계약 변경으로 직렬 처리한다.
- 추가 검토자 E의 독립 가치는 비밀값 비저장과 사용자 결정 권한 검증이며 Host 실행 D와 중복하지 않는다. F1/F4는 총괄이 합쳐 수행한다.
- 실제 생성 직전 모델 가용성을 확인하고 `model`, `reasoning`을 명시한다. 변경 이유와 새 배정을 보고하되, 사용자 결정이 필요하지 않은 내부 배정은 위 자율 판단 원칙으로 처리한다.

### 토큰 사용 규칙

- 새 하위 에이전트는 `fork_turns=none`; 입력은 목표 G1–G6, 소유 파일, 필수 계약 발췌, 수락 ID, 금지사항, 참조 hash만 1–2k 토큰으로 전달한다. 전체 대화·전체 Wiki·99개 시험 로그를 복제하지 않는다.
- 공통 source map과 계약표 1개를 재사용한다. 같은 조사를 중복 위임하거나 recursive 하위 에이전트를 생성하지 않는다.
- 반환은 상태, 변경 파일/hash, 실제 명령·assertion 수, 증거 경로, 미해결, 다음 담당자로 구성하고 800단어 이내를 권장한다. 장문 로그는 파일로 남기며 비밀값 원문은 파일에도 저장하지 않는다.
- 상태 확인용 모델 턴·주기 polling을 만들지 않는다. 결과 push와 필요한 단일 대기만 사용한다. 자동 보정 예산은 root original turn당 1회이며 하위 에이전트마다 보정 모델을 증식시키지 않는다.
- 제품 운영 시 별도 요약 LLM/API 호출은 0. 정상 Hook은 모델 호출 0·모델 문맥 출력 0. 업무 MCP 기록은 기존 작업 모델이 필요 사건만 생성하고 변경 없는 Task/gate 재전송을 줄인다. API batch를 새로 추가하지 않는다.
- 실제 input/output/cached 토큰을 가능한 제공 계측으로 기록하되 수집 불가면 `UNVERIFIED`다. 각 원래 turn의 보정 횟수와 지연 분포도 측정한다. 비용 절감 때문에 필수 사건·수락 시험을 생략하지 않는다.
- 하나의 저장소를 공유하되 파일 소유권을 분리한다. worktree가 필요하면 현재 미추적 구현을 포함하는 승인된 manifest 기반 복사/작업 트리 방식을 먼저 정한다. 자동 commit으로 격리를 만들지 않는다.

### 승인 경계

| 게이트 | 구체적으로 승인할 내용 | 현재 |
| --- | --- | --- |
| P | 이 계획·조직 설계 작성 | 사용자 승인, 이번 작업 |
| X1 | task 1b 문서 교정과 task 2의 합성 Host 시험 범위·정확한 Hook/trust 변경·복구안 | 사용자 승인됨; 2026-09-08 조건·한계를 명시한 검증과 정리 완료 |
| X2 | task 3–7 제품 구현과 고정된 사건 schema·통합 지침 | 반복된 사용자 자율 진행 지시 적용; 일반 구현·검증의 단계별 재승인 불필요 |
| X3 | 실제 registry 범위·사용자 설정 설치·기존 업무 영향·task 8 실사용/재부팅 검증 | 현재 대상 내 되돌릴 수 있는 적용·검증은 변경/복구안 준비 후 자율 진행. 새 범위·기존 작업 중단·PC 재부팅 시점과 필수 직접 입력은 별도 |
| X4 | 실제 화면·필수 행렬에 대한 사용자 제품 수락 | 시험과 별개인 명시 결정 |

모든 게이트는 범위 승인 1회로 후속 동일 범위 행동을 포함한다. 동일 승인 재질문은 하지 않는다. 자동 시작·App Server 진단·전역 정책·Git 게시·백필은 위 게이트에 묶지 않는다.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | 1a=P, 1b=X1 | 2 | 없음 |
| 2 | 1 | 3–8 | 없음; Host 변경 직렬 |
| 3 | 2 PASS, X2 | 4,5 | 없음; 공통 계약 직렬 |
| 4 | 3 | 6 | 5 |
| 5 | 3 | 6 | 4 |
| 6 | 4,5 | 7 | 없음 |
| 7 | 6 | 8 | 없음 |
| 8 | 7, X3 | F1–F4 | 없음 |
| F1–F4 | 8 | X4 | F1/F2/F4 읽기만 병렬; F3 재실행은 단독 |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. 비활성 변경·복구 패킷 제시 후 승인된 목표·상태 정정
  - 소유: 총괄. **1a는 P 범위**: 실제 설정을 읽기 전용으로 필요한 필드만 확인하고, 합성 Host 시험의 exact diff·trust 검토 대상·복구 패킷을 `.omo/`에 작성해 제시한다. 적용·trust 승인·실행은 하지 않는다. **그 패킷에 X1 승인을 받은 뒤 1b**: 기존 문서를 소급 개작하지 않는 후속 교정 기록 작성. 대상 `AGENTS.md`, `README.md`, `docs/operator-guide.md`, `../wiki/knowledge/14 Codex 작업 티켓 추적 도구 선택.md`의 현재 상태 후속 절과 별도 실행 증거. 정식 설계의 과거 판정은 보존한다.
  - 참조: 위 권위 표, 인계서 §8, 정식 설계 :52/:335/:1434. 현행 제품 상태와 과거 기반 수락을 별도 필드로 표시한다.
  - 호환성 패킷에는 실행 파일/Hook 정의 hash, exact trust 변경·원상복구 대상, 고정 합성 작업 allowlist, 승인된 port/data root, 금지 경로를 담는다. 기존 실제 설정을 새 템플릿으로 덮어쓰지 않는다.
  - 수락: 원래 G1–G6가 전부 유지되고 같은 상태 문구가 기록됨. Wiki 쓰기 전 Company Memory Guardian 사전/사후/완료 검증을 적용한다. 이는 기존 코드 검증 통과를 뜻하지 않는다.
  - QA 정상: `git diff --check -- <이번 소유 문서>`와 UTF-8/상태 표식 대조 결과를 `E/task-1/`에 저장. 실패: 교정 전 보호 파일 hash 불일치·기존 변경 충돌 시 중단하고 소유권 보고; 원상복구로 남의 변경을 지우지 않는다.
  - 의존: 1a=P, 1b=X1. 다음: 2는 1b 뒤. 계획 자체는 활성화 patch가 아니므로 이를 X1의 승인 자료로 대신 사용하지 않는다. Commit: N, 별도 Git 승인 필요.

- [x] 2. 실제 Desktop·CLI Hook 발화·식별·trust 호환성 판정
  - 소유 A; 신설 `phase0/correction/` 합성 검사 도구와 `E/task-2/`만. 실사용 Hook 설치는 X3 전 금지. 임시 Host 설정 변경도 task 1에 고정된 X1 범위만 적용한다.
  - 참조: 정식 설계 :335–397, 인계서 §10 단계2, 공식 Hooks 문서, `phase0/` 역사 증거는 참고만. 새로운 manifest 생성.
  - Desktop/CLI 별 버전·실행 파일 hash, SessionStart startup/resume/compact, UserPromptSubmit, Stop, SubagentStart/Stop, 선택적 SessionEnd를 검사한다. thread/turn/parent ID, MCP 준비 전, 동시 Hook과 `continue:false` competitor, continuation의 새 turn 관계를 기록한다. 실제 원문 수집·transcript 읽기 금지.
  - 하위 에이전트 Hook의 `(parent session_id, parent turn_id, agent_id)`와 자식의 MCP 사건을 결합할 **공식 상관 키**를 합성 자식 작업에서 검증한다. 정확한 대응 근거 없이 agent_id=child session_id로 가정하지 않는다. 키가 없거나 불안정하면 G2/A14=`BLOCKED`; 후속 구현 3–8을 진행하지 않는다. 별도 trace 파싱으로 우회하지 않는다.
  - MCP `instructions` 시험은 고정 합성 서버·안전한 짧은 지침을 사용해 Host 전달 기능만 확인한다. 최종 제품 문안 수신 시험은 task 5/8의 책임이다.
  - 수락: 필수 Host×사건 행마다 `PASS/BLOCKED/UNVERIFIED`와 증거. 하나라도 필수 미지원이면 후속 구현 차단. SessionEnd 선택 미발화는 진단 한계로 명시하되 완료 사건으로 대체하지 않는다. trust 우회 플래그 금지.
  - QA 정상: 생성할 `phase0/correction/verify-host.ps1 -Manifest <합성 manifest> -Output <E/task-2/result.json>`로 승인된 단발 시나리오 실행; actual dispatch와 spool 관측 hash 대조. 실패: 미신뢰·MCP 미준비·역순·경합을 각각 고정 입력으로 유발하고 본 작업 지속/불완전 표시 가능성을 관측. 설정 복구 전후 hash 보존. 주기 재시험 없음.
  - 예상 8–12개 합성 실행 그룹, assertion은 필수 행별 별도 기록. 의존 1, 차단 3–8. Commit: N.

- [x] 3. 관찰 payload·회차 관계·투영 schema와 인터페이스 고정
  - 단일 코드 소유자 A (`gpt-5.6-sol high`) 재사용; 총괄은 계약 승인·대조만 수행한다. 이 구간에는 B 실행 금지. 신설 `lifecycle/contracts.py`, `domain/events.py`의 필요한 확장, `ingest/payload_models.py`, `ingest/payloads.py`, 신규 additive migration 및 `tests/unit/test_lifecycle_contracts.py`만.
  - 참조: `src/codex_ticket_dashboard/` 기준 `domain/events.py:47`, `:201`; `mcp/__init__.py:121`; `ingest/payloads.py:89`; `ingest/payload_models.py:231`; `storage/migrations/001_initial.sql:328`. 기존 initial migration을 편집하지 않는다.
  - 결정: 업무 ticket 이전의 `observed activity` projection을 독립 추가한다. `THREAD_OBSERVED` 등을 strict typed metadata로 확장하고 `(source host, session, turn, event identity)` 중복·인과 계약을 고정한다. 비어 있는 ticket을 꾸며 만들지 않는다. 식별 실패 활동은 pending의 제한 metadata 조회로 노출하고 원본 envelope는 불변이다.
  - 새 lifecycle payload는 actor `OBSERVER`, origin `HOOK`, 시스템 관찰 권한만 허용한다. `USER`·`USER_EXPLICIT`는 생성하지 않는다. 기존 historical AuthorityOnly payload 읽기 호환을 유지하며 timestamp를 idempotency 키의 변동 요인으로 쓰지 않는다.
  - task 2의 공식 parent/child/MCP 상관 키를 typed 관계 계약과 fixture에 고정한다. 관계 미확인을 성공으로 처리하는 nullable 우회는 금지하며, 해당 키 없이는 G2/A14를 통과할 수 없다.
  - command admission은 기존 `SpoolWriter.write(EventEnvelope)`와 안전 data-root 초기화를 재사용한다. 기존 MCP 도구·도구 수는 유지한다. durable Stop budget은 DB writer를 늘리지 않는 spool 원자 claim으로 소비하고 collector가 Hook 상태 표에 투영하도록 인터페이스를 고정한다.
  - 수락: old/new payload 파싱·replay, 원문 차단, 같은 turn 중복·다른 payload 충돌, root/child ID 충돌 검증. 공통 계약 hash를 A/B 입력에 고정한다.
  - QA 정상/실패: `uv run --locked pytest -q tests/unit/test_lifecycle_contracts.py tests/unit/test_events.py`; old fixture 통과, forged USER authority·raw canary·누락 ID 거부를 명시 assert. `E/task-3/`. 예상 새 8–12개 사례. 의존 2 PASS+X2. 다음 4/5. Commit: N.

- [ ] 4. deterministic command 관찰과 보호 spool 연결
  - 소유 A. `src/codex_ticket_dashboard/lifecycle/{command,admission,identity,normalization}.py`, repo-owned `hooks/correction-hooks.example.json`, `tests/unit/test_lifecycle_admission.py`, `tests/integration/test_lifecycle_spool.py`. 3의 공통 파일 수정은 총괄에 반환한다.
  - 참조: `storage/spool.py:140`, `domain/events.py:201`, `ingest/identity.py:71`; task 2 Host manifest/task 3 계약 hash. Python·Windows 지침 적용.
  - Hook stdin은 메모리에서 allowlist 정규화하고 raw input·stdout·stderr·예외 stack에 값을 남기지 않는다. session 시작·사용자 turn·subagent·종료를 MCP 준비와 무관하게 기록한다. 정상 경로 추가 모델 문맥 없음. 업무 요약/수락 추론 없음.
  - 수락: data-root ACL/final-path와 registry identity 유지, 같은 관찰 1회 기록, MCP/collector 부재에도 spool 유지, unsupported metadata는 불완전/미분류 처리. 파싱 실패는 redacted code만 반환한다.
  - QA 정상: `uv run --locked pytest -q tests/unit/test_lifecycle_admission.py tests/integration/test_lifecycle_spool.py`; 실제 NTFS 합성 root에서 writer 사용. 실패: 원문 canary, invalid path/reparse, disk write 실패, MCP 미준비, 동일 event 역순/중복. 저장 불가 시 성공 receipt 금지와 Codex 비차단을 분리 assert. `E/task-4/`, 예상 10–16개. 의존 3; 5와 병렬. Commit: N.

- [ ] 5. 활동 투영·업무 연결과 최소 모델 기록 계약
  - 소유 B. 신설 `ingest/lifecycle_projection.py`, 필요한 최소 dispatch 연결 `ingest/collector.py`, `storage/lifecycle_queries.py`, `mcp/server.py`의 initialization instructions만, `tests/integration/test_lifecycle_projection.py`, `docs/correction-recording-contract.md` 초안. schema/migration·기존 user-decision 로직을 병렬 편집하지 않는다.
  - 참조 `ingest/collector.py:98`, `ingest/payloads.py:89`, `mcp/tools.py:25`, `domain/status.py:121`, `ingest/review_invalidation.py:58`, 정식 설계 :508/:529. A의 구현 대신 고정 계약 synthetic EventEnvelope로 개발한다.
  - 수락: 자동 활동이 ticket 미연결이어도 조회됨; 기존 MCP preflight가 같은 session/turn에 도착하면 인과 관계로 연결. 미분류/충돌 표시, late identity resolve와 restart에서 activity 중복 없음. child 연결은 명시 ID만 사용. generic actor/authority를 허용하는 우회 경로 없음.
  - 모델 기록 계약은 preflight·변경 Task·최종 summary/required gates/status·명시 결정 기록을 현재 작업 모델에 요청하며 별도 요약 모델 없음. MCP initialize 응답에 지침을 결속하고 실제 handshake에서 읽히는지 검증한다. 무변경 gate의 부적용 근거와 정책 snapshot을 유지한다. X3에는 변경된 서버 hash와 정확한 문안·예상 토큰을 제출한다. 같은 작업을 새 티켓으로 재등록하지 않는다.
  - QA 정상: `uv run --locked pytest -q tests/integration/test_lifecycle_projection.py`; lifecycle→MCP→조회 연결, DISCUSSION, parent-child. 실패: registry conflict, orphan child, late identity, stale 결정/summary 미충족을 거부하고 보존. 기존 `test_state_authority.py`·`test_user_decisions.py`는 연결 코드가 그 경계를 바꿀 때만 집중 추가 실행. `E/task-5/`, 예상 12–18개. 의존 3; 4와 병렬. Commit: N.

- [ ] 6. Stop 기록 대조·한 차례 보정·관측 범위 진단
  - 소유 A 재사용. 신설 `lifecycle/{completeness,continuation,coverage}.py`, `tests/integration/test_stop_completeness.py`, 필요한 4 command의 Stop 분기. B 결과 hash를 받아 순차 통합한다.
  - 참조 정식 설계 :359/:898/:986, task 2 실제 turn 관계, task 3 claim 계약. DB는 query-only, incoming+pending과 함께 읽는다. collector만 DB를 쓴다.
  - 수락: pending을 missing으로 잘못 재생성하지 않음; 원래 turn당 durable claim 1개; Stop 재시작·중복·동시 실행·compact 뒤에도 횟수 유지. observer 요청과 Host aggregate 결과 분리. 부정확한 연관은 `UNKNOWN`으로 남김. claim 후 process crash는 보정 실행 여부 불명으로 기록하고 자동 재요청하지 않는다.
  - QA 정상: `uv run --locked pytest -q tests/integration/test_stop_completeness.py`; 완전 집합 0 continuation, 실제 누락 1 continuation. 실패: claim crash, 양쪽 누락, pending race, competitor 차단, 2회 Stop, hook disabled coverage 검사. 불완전 상태가 화면 조회 데이터로 전달되는지 검증. `E/task-6/`, 예상 10–16개. 의존 4+5. 다음 7. Commit: N.

- [ ] 7. 관측 범위·미분류 활동·기록 불완전 화면 연결
  - 소유 C. `src/codex_ticket_dashboard/web/`의 기존 수집 문제·프로젝트/티켓 화면에 필요한 조회/template만, 신설 `tests/e2e/test_lifecycle_display.py`. 기존 GET/HEAD·query-only·Host·no-store 경계 유지. 새 화면 체계 재설계 금지.
  - 참조 `web/pages.py`, `web/queries.py`, `web/page_models.py`, `web/templates/screen.html`, `web/static/dashboard.css` (`src/codex_ticket_dashboard/` 기준); task 5 query 계약과 task 6 coverage codes를 입력으로 받는다. frontend·visual-qa 지침을 변경면에 적용한다.
  - 수락: 미관측을 0활동/정상으로 표시하지 않음. pending/UNCLASSIFIED/CONFLICT/누락과 새로고침 시각·검증된 Host 범위를 사용자가 구분함. 원문 없이 원인·다음 단계 표시.
  - QA 정상: `uv run --locked pytest -q tests/e2e/test_lifecycle_display.py`; 승인된 작업 전용 local port의 실제 Chrome 화면 1280×800·1440×900, 영향 route만. 실패: 빈 registry·pending·stale coverage·긴 한국어 사유·금지 POST/Host 검사. `E/task-7/`, 예상 4–6개. 변경 화면의 모바일 회귀 확인은 실시 여부/제약을 분리하며 기존 모바일 제품 수락으로 확대하지 않는다. 의존 6. 다음 8. Commit: N.

- [ ] 8. 통합 설치안과 실제 무개입 종단 간 수락 행렬 실행
  - 소유 D, 구현자와 독립. 정확한 설치 diff/승인된 registry/Hook trust/통합 지침/rollback을 `E/task-8/activation-packet.md`에 먼저 고정하고 X3 승인 후 실행한다. 사용자 실제 비밀 데이터 대신 고정 합성 작업만 사용한다.
  - 원래 작업과 수정된 작업의 영향 범위·정상 Hook model context 토큰·MCP 호출 수·보정 횟수·지연을 기록한다. 별도 로컬 데이터 root에서 시작하고 실운영 설치는 별도 승인 범위 그대로 적용한다.
  - 수락: 위 A1–A15 전체. 증거는 `E/task-8/acceptance-matrix.json`에 Host/source version, synthetic session/turn refs, expected/actual, observed_at KST, artifact hashes를 담는다. 실제 ‘명시 수락’ 실험은 합성 티켓에 한정하며 이번 제품에 대한 사용자 수락을 만들어 내지 않는다.
  - QA 정상: 승인된 Codex App 생성/메시지 도구 또는 실제 Desktop UI와 CLI로 일반 작업을 만들고 로컬 Chrome에서 사건을 확인한다. 신규 fixture 문구에는 대시보드·MCP 호출 지시를 넣지 않는다. 생성 도구·CLI 명령·UI 행동은 task 2 확인값을 그대로 쓴다.
  - QA 실패: 수집기 중단·재시작, 누락, competitor Hook, 취소/재개와 결정 재사용, 미신뢰 Hook를 합성 범위에서 실행. PC 재부팅은 사용자의 편리한 시점과 중단 범위가 승인되기 전 실행하지 않는다. 미실행 A9는 `BLOCKED-BY-USER-WINDOW`로 남기며 제품 완료 금지.
  - 시험 후 자기 임시 runtime만 정리하고 archive는 보존한다. 사용자 기존 설정·프로세스와 증거를 지우지 않는다. 의존 7+X3. 다음 F1–F4. Commit: N.

## Final verification wave
아래 네 책임은 네 개의 새 agent를 뜻하지 않는다. 총괄 F1/F4, 독립 보안 검토 E의 F2, 실제 수락 실행 D의 F3으로 제한한다. 통과한 Host 시험을 형식상 재실행하지 않는다. 각 보고는 최종 변경 manifest SHA-256에 결속하며 소스 변경 시 영향 증거만 갱신한다.

- [ ] F1. 목표 대조: 총괄이 G1–G6→A1–A15→현행 증거를 대조한다. 누락·미지원·검증하지 않은 Host가 있으면 `REVISE` 또는 `INCONCLUSIVE`; 전체 PASS 금지. `E/final/goal-audit.md`.
- [ ] F2. 개인정보·권한·코드 변경 검토: `gpt-5.6-sol high` 1명이 lifecycle admission, shared payload/migration, continuation claim과 사용자 결정 경계의 diff+증거만 읽는다. 원문 저장·자동 USER 권한·두 번째 writer·무제한 continuation 여부 검토. 실행자의 자기 보고만으로 APPROVE 금지. `E/final/security-authority.md`.
- [ ] F3. 실제 사용 증거 판정: D의 실제 Host→spool→DB→브라우저 A1–A15를 대조하고 합성 API 주입이 실제 무개입 작업을 대체하지 않았음을 확인한다. 새 실패·소스 drift가 있을 때만 해당 시나리오 재실행. `E/final/host-acceptance.md`.
- [ ] F4. 범위·비용·인계: 총괄이 보호 hash, 실제 토큰/호출/보정 수, 승인 범위, 새 Wiki 후속 상태, 기존 dirty 보존과 unresolved 목록을 확인한다. `E/final/scope-cost-handoff.md`. 도구가 계측을 제공하지 않으면 사용량을 0으로 쓰지 않는다.

검토자는 `APPROVE/REVISE/INCONCLUSIVE`로 반환한다. 120초 후 1회 범위 제한 안내, 60초 추가 대기 후 미응답은 INCONCLUSIVE로 기록한다. 침묵은 승인이 아니다. 필수 안전 검토가 INCONCLUSIVE이면 제품 수락 후보를 통과시키지 않는다.

## Commit strategy

이번 계획·후속 기본 실행은 자동 commit·push·branch 변경을 포함하지 않는다. 기존 dirty를 hash로 보존하고 소유 파일만 인계한다. Git 게이트는 실제 권한 상한을 반영하고 commit 미승인을 숨기거나 강제 commit하지 않는다. 사용자가 별도 승인한 경우에만 `omo:git-master`로 원자 commit을 설계한다.

## Success criteria

- 계획 작성 완료: 목표 추적표, 8개 실행 작업, 4개 최종 책임, 소유권/의존성/모델·비용, 승인 경계와 실패 시 정지 조건이 있으며 참조·형식·보호 hash 확인을 통과한다.
- 실행 결과의 최대 자동 판정: 모든 필수 증거가 충족될 때 `AUTO-PROJECTION-CANDIDATE-IN_REVIEW`. 이는 사용자 제품 수락이 아니다.
- 제품 수락: 실제 신규·재개 Desktop·CLI 활동, 하위 에이전트, 결과·명시 결정, 누락·복구가 검증되고 사용자가 그 범위·화면·한계를 명시적으로 수락해야 한다. 하나라도 필수 미완료면 `PRODUCT-GOAL-INCOMPLETE` 유지.
- full v1.3·모바일·자동 시작·전역 범위의 보류는 별도 표기한다. 자동 투영 교정의 성공으로 해당 범위를 완료 처리하지 않는다.

### 제안 Wiki 후속 기록 문안 — 현재 미적용

사용자 추가 지시에 따라 조직은 Task 독립성과 공유 자원 충돌을 기준으로 구성하고, 개발·구현·테스트를 안전하게 병렬 실행한다. 모델은 Task별 난이도·위험·비용으로 선택하며 동시 2명 또는 담당자별 모델을 고정하지 않는다. 개발 오류·시험 실패는 승인 범위 안에서 스스로 해결하고 목적 변경·미승인 권한·필수 사용자 정보·해소 불가능한 문제에 한해 의견을 구한다.

2026-09-07 교정 계획은 신규·재개 Codex 작업의 무개입 자동 투영을 원래 목표로 고정했다. 기존 MCP 기반 후보 수락은 역사로 보존하며 현재 제품은 `PRODUCT-GOAL-INCOMPLETE`다. 계획 위치는 `codex-ticket-dashboard/.omo/plans/codex-auto-projection-correction-20260907.md`. Hook command 관찰과 기존 MCP 업무 기록을 분리하고 실제 Host 호환성 게이트 뒤에만 병렬 구현한다. 이번에는 계획과 읽기 전용 조사만 수행했으며 Wiki·제품·운영 설정 변경은 없다. 다음은 정확한 합성 Host 시험 변경·복구 패킷 승인이다.

## 2026-09-08 X1 종료 및 X2 입력

Task1–2는 완료했습니다. 실제 Host 근거와 G0–G11의 적용 범위·한계는 최종 outcome을 참조하며, 이전 문서의 parent turn 가정은 실제 확인한 자식 turn 상관 키로 교정합니다. Tasks3–7은 제품 구현 권한을 포함하는 X2 패킷을 승인받은 뒤 시작하고, 공통 계약을 직렬 고정한 다음 command 관찰과 collector를 병렬 구현합니다. 자동 시작·실운영 설정·제품 수락은 포함하지 않습니다.

## 자율 진행 해석 갱신

최신 사용자 지시를 우선합니다. 최초 초안과 과거 결과의 미승인 표식은 당시 범위 기록이며 현재 자율 진행의 일반 단계 전환을 차단하지 않습니다. 기술 검사와 개인정보·권한 요건은 그대로 통과해야 합니다. 정확한 적용 변경과 복구안은 여전히 작성·검증하되 준비 문서의 존재를 추가 사용자 승인 사유로 삼지 않습니다. 필요한 사용자 입력은 해당 부분만 분리하고 독립 작업을 계속합니다.
