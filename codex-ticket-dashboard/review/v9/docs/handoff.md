# Claude Code 교차검증용 인계 자료 — v9 기준

작성 기준: 2026-09-09 11:28 KST 최초 작성, 11:38 KST 이후 Git/설치 v9 정보 확인 및 사용자 지정 기준 반영. 작성자: 이 프로젝트를 진행한 Codex 총괄.

## 0. Git 공유본의 v9 기준

이 공유본의 `src/`는 설치된 v9의97개 파일을 원래 바이트대로 복사한 것입니다. `source-manifest.json`에서 상대 경로와 SHA256을 확인할 수 있습니다. 작업 폴더의 후속 수정본/v10을 포함하지 않습니다. 제품은 실제 Hook 시간 초과와 업무 등록 실패가 남은 미완료 상태입니다.

- 저장소: https://github.com/jowa131/myproject-workspace
- 공유 브랜치: `review/codex-ticket-dashboard-v9`
- 검토 폴더: `codex-ticket-dashboard/review/v9`
- `V9_ROOT`: 이 검토 폴더, `V9_SOURCE`: `src/codex_ticket_dashboard`, `V9_WRAPPER`: `src/observe.cmd`.
- 실제 적용 Hook 정의: `evidence/hook-trust-approval-20260909/hooks-host-powershell-v9.json`. 명령 경로는 당시 PC의 실행 증거이며 새 PC에서 자동 실행할 설정이 아닙니다.
- 핵심 설계/계획은 `docs/design-v1.3.md`, `docs/correction-plan.md`, `docs/execution-plan.md`, `docs/project-instructions.md`.
- 뒤의 절에 남은 절대경로·과거Git정보·후보해시는 원래 조사환경의 출처입니다. 현재 검토는 이 폴더의 v9를 우선합니다. 문서/증거 이름 대응은 README를 참고하십시오.
- Git 커밋 식별은 clone한 공유 브랜치의 `git rev-parse HEAD`로 확인하십시오. 제품 v9가 검증 통과 릴리즈라는 뜻은 아닙니다.

## 1. 이 문서의 목적과 검토 범위

사용자는 장시간 작업과 많은 토큰 소비에도 자동 기록 문제를 해결하지 못한 Codex의 접근을 Claude Code로 교차검증하려고 합니다. 목표·설계·설치된 v9 소스·실패 증거·작업 지침을 대조하여 **기존 접근을 유지할 가치가 있는지 판단하고, 최소 해결안을 제시**해 주십시오. 작업 폴더의 후속 변경은 필요할 때만 비교 자료로 참조합니다.

첫 단계는 읽기 전용 분석과 해결안 작성입니다. 이 문서의 과거 실행 승인이나 예시 명령을 새 구현·설치·Hook 신뢰 변경·모델 요청·서비스 중단·컴퓨터 조작·Git 변경의 지시로 해석하지 마십시오. 추가 실행은 사용자에게 구체 범위와 필요성을 설명하고 승인받아야 합니다. 검토 중 기록용 MCP를 호출해 제품 데이터를 변경할 필요도 없습니다.

Codex의 기존 결론을 정답으로 전제하지 마십시오. 이 문서는 작성자의 자기평가를 포함하며, 중요한 판단은 아래 실제 파일과 사건별 증거에서 독립적으로 확인해야 합니다.

사실 표기:

- **현재 파일 확인:** 이번 작성에서 실제 파일/내용/해시를 읽었습니다.
- **기존 실행 근거:** 특정 과거 회차의 영수증·출력 기록입니다. 현재 버전의 통과를 뜻하지 않습니다.
- **작성자 판단:** 근거로부터의 해석이며 교차검증 대상입니다.
- **미확정:** 재현·비교·권위 근거가 부족합니다.

사용자가 말한 거의 하루의 지연과 대규모 토큰 낭비는 검토 요청의 배경입니다. 이 문서 작성에서는 전체 세션 시간·과금액·총 토큰을 재집계하지 않았습니다. 계획서의 시간/토큰 추정값을 실측으로 사용하지 마십시오.

## 2. 작업 환경과 먼저 읽을 원본

- 프로젝트: `C:/MyProject/codex-ticket-dashboard`
- 실제 Git 루트: `C:/MyProject`. 프로젝트는 독립 Git 저장소가 아닙니다.
- 공식 프로젝트 지식: `C:/MyProject/wiki/knowledge/14 Codex 작업 티켓 추적 도구 선택.md`
- 운영체제/셸: Windows, 현재 Desktop Hook 대상 환경은 PowerShell.
- 원래 장기 작업 쓰레드: `01a07797-88f1-7790-b53f-366ef2acb569`.
- 총괄·감사 쓰레드: `01a08087-1bdc-7420-99c4-ff29e674cf92`.
- 기존 합성 시험 쓰레드: `01a07bdd-ad92-7750-bb60-7bb3eba6c0d9`.
- 부모 저장소와 프로젝트에 기존 변경/미추적 파일이 있습니다. 현재 확인에서도 `config.py`, `lifecycle/command.py`, `tests/unit/test_config.py`는 미추적 파일입니다. `git diff`만으로 전체 구현이나 변경 유무를 판단하지 마십시오. reset/clean/일괄 stage/commit은 하지 마십시오.

| 읽기 순서 | 경로 | 읽을 내용과 주의 |
|---|---|---|
| 1 | `C:/MyProject/docs/design-codex-ticket-dashboard-prototype-v1-20260901.md` | 제목은 상세 설계 v1.3. §2–5 목표/권한, §10 식별, §11 Hook, §12 MCP, §13/15 사건·상태, §21 복구, §23–25 웹 계약 |
| 2 | `C:/MyProject/codex-ticket-dashboard/docs/handoff-original-goal-gap-and-correction-20260907.md` | 원래 제품 목표와 과거 기반 완료의 차이. 당시의 ‘관찰 계층 없음’은 역사적 상태이며 현재 소스 부재로 재사용하지 않음 |
| 3 | `C:/MyProject/codex-ticket-dashboard/.omo/plans/codex-auto-projection-correction-20260907.md` | 교정 계약, A1–A15 수락 조건, 통합 지침/모델 방침. 문서 내 시각별 갱신과 후속 변경 근거 대조 필요 |
| 4 | `C:/MyProject/codex-ticket-dashboard/.omo/plans/auto-projection-product-execution-20260908.md` | 실제 구현 단계와 남은 적용·수락 |
| 5 | `C:/MyProject/AGENTS.md`, 프로젝트 `AGENTS.md` | 적용 지침. 특히 비용 통제·변경 인지 검증·컴퓨터 제어권 반환 |
| 6 | 프로젝트 `docs/release-remaining-tasks-20260908.md` | R1–R6. 앞부분의 과거 원인 미확정/승인 대기 문구보다 마지막 2026-09-09 정정을 함께 읽음 |
| 7 | 프로젝트 `docs/automatic-recording-root-cause-analysis-20260909.md`, `docs/execution-process-root-cause-20260909.md` | 제품 오류 반환 결함과 실행/감독 실패를 구분. 최초 문구와 마지막 정정의 시점 차이 주의 |

설계서 §1의 ‘구현/설치 비목표’는 그 설계 문서 작성 작업의 범위입니다. 이후 승인된 구현 전체를 금지하는 제품 비목표로 오독하지 마십시오. 반대로 과거 좁은 기반 수락을 자동 추적 제품 전체의 수락으로 확대해서도 안 됩니다.

## 3. 원래 제품 목표와 지켜야 할 경계

사용자는 Codex Desktop·CLI에서 작업 지시·피드백·최종 수락을 합니다. 별도로 티켓 등록이나 기록을 지시하지 않아도 프로젝트·스레드·회차·티켓·Task/Subtask·상태·결과·검증·Git/Wiki 준수·누락 여부가 로컬 읽기 전용 웹에 연결돼야 합니다.

완료 기준의 핵심:

1. 신규·재개·하위 작업이 자동으로 관찰되고 적절한 업무와 연결됩니다.
2. 사용자 피드백과 결과가 동일 회차로 연결되며 부모·자식 관계를 보존합니다.
3. 불확실한 활동은 `UNCLASSIFIED`/불완전 상태로 보이고 사라지지 않습니다.
4. 수집기 중단 중 사건은 spool에 보존되고 재시작 뒤 중복 없이 반영됩니다.
5. 기록 기능이 실패해도 원래 Codex 작업은 계속할 수 있고 누락이 드러납니다.
6. Codex는 `IN_REVIEW`까지입니다. 완료·취소·재개는 정확한 최신 사용자 명시 결정만 허용합니다.

보존할 계약:

- `project_id`는 논리 프로젝트, `repo_key`는 Git 저장소 관계입니다. 상위 Git root로 프로젝트를 추정해 합치지 않습니다.
- 원자 spool → 수집기 → SQLite WAL → 읽기 전용 웹. 웹의 역제어/변경 API나 스텁도 만들지 않습니다.
- 저장은 구조화 요약과 제한 메타데이터만. 사용자 prompt/assistant message/transcript/Hook 출력의 원문·발췌와 비밀값을 제품 DB/spool/진단/archive에 저장하지 않습니다.
- Windows owner-only ACL·상속 차단, reparse/UNC/device path 차단, loopback/Host allowlist/no-store를 유지합니다.
- Hook은 다른 Hook의 공존·비동기 역순을 고려하고 원 작업을 임의 차단하지 않습니다. Stop 보완은 승인된 최대1회 조건을 지킵니다.
- 불안정한 transcript 파싱, 새 polling/자동 시작/백필/외부 서비스로 결함을 우회하지 않습니다.
- 현재 로컬 릴리즈에는 모바일·외부 배포·추가 화면 미화·다른 프로젝트 등록 확대를 붙이지 않습니다.

`UserPromptSubmit`은 사용자가 원하는 유즈 케이스 자체가 아니라 현재 설계의 수단입니다. 다만 정식 설계 §11.1에는 필수입니다. 대체가 필요하면 시작/진행 추적까지 동등하게 충족하는 변경 계약과 승인 필요성을 제시해야 합니다. Stop 때만 뒤늦게 생성하는 방식은 자동 시작/진행 추적과 동등하지 않습니다.

## 4. 현재 구현과 제품 상태

**판정: PRODUCT-GOAL-INCOMPLETE. 릴리즈 완료 아님.**

| 구간 | 현재 확인한 상태 | 보장하지 않는 것 |
|---|---|---|
| domain/storage/ingest/MCP/web | 구현 파일과 과거 구성요소 검증 기록 존재 | 실제 신규·재개 작업의 자동 등록 전체 성공 |
| lifecycle 관찰/문맥/보완 | 구현 존재, 직접 관측 접수 성공 근거 존재 | 실제 Host의 정상 종료와 후속 업무 기록 |
| 실패 반환·진단 | v9 수정과 당시 집중4사례 통과 보고 | 최신 미검증 후보의 통과 |
| Hook 설치·신뢰 | 09:49 기준 시험 프로젝트6개 활성·신뢰 영수증 | 6개 모두 실제 정상 동작 |
| 실제 대표 작업 | 09:50 회차 UPS/Stop3초 시간 초과, Stop관측1, 업무사건0 | 자동 티켓 생성·제품 완료 |
| 기동 경량화 후보 | 작업 소스에 변경 존재 | 기능 검증·실제 활성화 |
| 최종 운영 적용/수락 | 미완료 | 사용자 최종 수락 |

현재 시험 Hook 설정은 v9를 참조하고 v10 참조는 없습니다. v10 의존성 설치는 끝났지만 `product-20260909-v10` 디렉터리는 없습니다. 소스 변경과 설치된 런타임을 같은 것으로 취급하지 마십시오. 이번 인계 작성에서는 서비스 건강 상태·현재 DB 전체 건수·웹 실행 여부를 새로 조회하지 않았습니다.

## 5. 코드 경로와 중요한 연결 의존성

아래 표의 `src/codex_ticket_dashboard/...`는 **V9_ROOT 아래의 경로**로 읽습니다. 프로젝트 작업 폴더의 동명 파일로 대체하지 마십시오. 줄 번호는 v9에서 대조했습니다. Hook은 실제 ACTIVE_HOOKS와 V9_WRAPPER를 기준으로 읽습니다.

| 위치 | 책임/검토 지점 |
|---|---|
| `ACTIVE_HOOKS` | 적용된6개 Hook의 PowerShell 명령 본문, 타임아웃/동기·비동기 설정. 프로젝트 hooks 템플릿은 비교용 |
| `V9_WRAPPER:2` | Python `-I -B -m codex_ticket_dashboard.lifecycle.command`; 비정상 종료를1로 정규화 |
| `src/codex_ticket_dashboard/lifecycle/command.py:34` | 관측 접수; UPS 접수 후 `additionalContext=RECORDING_GUIDANCE` 반환 |
| `src/codex_ticket_dashboard/lifecycle/command.py:68` | stdin/설정/정규화/식별/접수/진단/종료 코드 |
| `src/codex_ticket_dashboard/config.py:126` | v9의 TomlConfigSettingsSource/BaseSettings 기반 설정 검증. argparse 경량화 후보와 구분 |
| `src/codex_ticket_dashboard/lifecycle/command_diagnostics.py` | 원문 없는 제한된 최신 처리 결과. 진단 부재만으로 미호출 단정 금지 |
| `src/codex_ticket_dashboard/lifecycle/normalization.py` | Hook 입력 정규화와 원문 저장 방지 |
| `src/codex_ticket_dashboard/lifecycle/admission.py` | 관찰 사건의 원자 spool 접수 |
| `src/codex_ticket_dashboard/recording_guidance.py:5` | 모델에게 preflight/task/summary/gate/status MCP 호출을 요구하는 고정 안내 |
| `src/codex_ticket_dashboard/mcp/official_context.py:145` | 같은 작업/회차의 관측 문맥이 없으면 `OBSERVER_CONTEXT_MISSING` |
| `src/codex_ticket_dashboard/lifecycle/initial_preflight.py:56` | 반영된 UPS 관측이 없으면 최초 기록 보완 대상에서 제외 |
| `src/codex_ticket_dashboard/lifecycle/stop_observer.py` | 종료 관측과 제한된 보완 판단 |
| `src/codex_ticket_dashboard/ingest/lifecycle_projection.py` | 관측 투영과 기존 업무 관계 연결. 관측만으로 의미 있는 업무 티켓을 생성하는 경로가 아님 |

현재 연결은 **Hook 관측 → 모델에 기록 안내 → 모델의 MCP 호출 → 접수/수집 → 업무 투영**입니다. Hook 관측 성공과 업무 등록 성공은 별개입니다. 시작 관측 누락 상태에서 안내 문구나 동일 요청만 반복해도 독립 복구가 되지 않는 의존성을 검토해야 합니다.

### 특히 교차검증할 설계 차이

정식 설계 §11.3과 교정 계획의 ‘최소 통합 지침’은 정상 Hook 경로에서 모델 문맥을 출력하지 않고 MCP 초기화 instructions를 쓰도록 합니다. 현재 `command.py:44–54`는 UPS에서 추가 문맥을 반환합니다. `docs/observation-installation.md:167` 이후에는 이 현 구현을 설명합니다.

**문서와 코드의 차이는 확인했습니다.** 현 구현이 승인된 후속 설계 변경인지, 단순 운영 문서 추가만으로 계약이 달라진 것인지는 이번 제한된 조회에서 확정하지 않았습니다. 후속 승인 근거를 확인하고, 없다면 필요한 계약 변경으로 명시하십시오. 즉시 코드를 삭제하거나 현 경로를 정당화하지 마십시오.

## 6. 실패 경과와 증거 해석

증거 기준 폴더:

`E = C:/MyProject/codex-ticket-dashboard/.omo/evidence/goal-alignment-audit-20260908/hook-trust-approval-20260909`

| 시점 | 실제 사실 | 해석 제한 | E 아래 근거 |
|---|---|---|---|
| 이전 조사 | 실패 시 cmd/Python이 성공 종료0으로 보이게 하는 계약 발견 | 과거 모든 누락의 최초 원인이 이 결함이라는 뜻은 아님 | 별도 `failure-contract-analysis-20260909` 폴더 |
| 09:02 | `send_message_to_thread` 요청은 `FunctionCallOutput` 경로, 관측/업무0 | 직접 사용자 입력의 UPS 실패 표본이 아님 | `input-route-correction.json` |
| 09:11 | 실제 Desktop 직접 입력에서 UPS/Stop `hook timed out after 3s` | 내부에서 시간을 소진한 정확 단계는 미확정 | `confirmed-native-timeout.json` |
| 09:22 전후 | 별도 빈 입력에서 전체 명령3.38초/직접Python1.73초; 초기 import 비용 관측 | 캐시·부하·호출 방식이 통제된 성능 비교 아님. 차이를 순수 개선 효과로 계산하지 않음 | `native-raw-command-startup.json`, `direct-python-import-profile.json` |
| 09:34 | 중간 직접 cmd 방식 적용 뒤 실제 Hook code1 | COMSPEC 시험을 PowerShell Host 검증으로 쓴 오류 | `direct-wrapper-native-result.json`, `hostshell-decision.json` |
| 09:49 | PowerShell 명령 본문 적용, 소유6개 활성·신뢰, 범위 밖 설정 보존 | 실제 처리 성공 아님 | `hostshell-activation-success.json` |
| 09:50 | UPS/Stop 시간 초과, Stop진단 SUCCEEDED/RECORDED, DB관측1, 업무사건0 | 저장 성공과 Host 정상 종료를 구분. 자동 등록 성공 아님 | `hostshell-native-result.json`, `loop-audit-result.json` |
| 10시 이후 | 기동 후보 시험이 새 테스트 SyntaxError로 수집 중단. 문법2곳만 수정·구문 확인 | 수정 후 기능시험 통과가 아님 | `cold-start-focused-tests.log`, `loop-audit-result.json` |

마지막 대표 회차: `01a083a5-6917-7980-a548-47de32498b7e`.

고정 공식 소스 참조: `openai/codex` commit `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`(기존 조사에서 codex-cli0.153.4 대응).

- `codex-rs/core/src/hook_runtime.rs`: 직접 `TurnInput::UserInput`과 내부 전달/도구 결과의 UPS 분기 차이. E의 `official-hook-runtime.rs` 사본 참고.
- `codex-rs/core/src/session/mod.rs:4453–4481`: `environment.shell`에서 Hook 셸을 구성.
- `codex-rs/hooks/src/engine/command_runner.rs`: 명시된 셸/인자 실행. COMSPEC fallback을 모든 Windows Host 실행과 동일시하면 안 됨. E의 `official-command-runner.rs` 사본 참고.

현재 명령 형태는 PowerShell 본문입니다:

```text
& '<protected>/observe.cmd' '<protected>/python.exe' '<approved>/dashboard.toml' 'local' 'unknown'; exit $LASTEXITCODE
```

경로를 채워 바로 실행하라는 명령이 아닙니다. 별도 PowerShell 실행 파일을 다시 중첩하지 않는다는 계약 설명입니다. cmd/bash Host 지원까지 검증된 것은 아닙니다.

### 잘못된 근거와 알려진 함정

- 내부 도구 전달 요청을 직접 UPS 표본으로 사용한 결과는 폐기해야 합니다.
- Python `subprocess` 인자 목록의 재이스케이프와 Rust `raw_arg`가 달랐던 로컬 측정은 무효입니다. E의 `local-empty-input-startup.json`은 성공 증거가 아닙니다.
- 긴 pytest 임시경로 때문에 spool 파일 경로가269자가 된 실패는 시험 환경 오류였습니다. 짧은 경로로 해당 사례만 통과했습니다. 실제 Hook 최초 실패와 합치지 마십시오.
- 오래된 로그/rollout에 Hook 행이 없는 것, UI 트리가 한 번 갱신되지 않은 것만으로 미발동을 단정하지 마십시오.
- `THREAD_RESUME`의 JSON-RPC `-32600`은 과거 보조 조사 경로의 미해결 결과입니다. 이를 해결하는 것이 제품 필수 납품물은 아닙니다. 원인을 busy/권한/DB writer로 추정하지 마십시오.
- 실제 Hook 결과는 Desktop 응답 아래 Hook 상세에서 확인했습니다. 반복적인 설정 조회·신뢰 갱신·메모 읽기 모델 요청으로 대신할 수 없습니다.

## 7. 비교 참고용 미검증 변경과 검사 통과 범위

이 절의 후속 후보는 **v9 일차 검토 기준에서 제외**합니다. v9 원인 분석 후 Codex의 후속 변경을 평가할 필요가 있을 때만 읽으십시오. 프로젝트 작업 폴더에 남은 기동 경량화 후보:

- `config.py`: BaseSettings/pydantic-settings 기반에서 명시 TOML 읽기+BaseModel 검증으로 변경, eager Typer 제거, argparse 기반 CLI.
- `lifecycle/command.py`: Typer 기반 CLI를 argparse로 바꾸고 고정 코드/종료1·안내 반환을 유지하려는 변경.
- 관련 시험은 CliRunner 호출을 직접 main 호출로 바꾸거나 실제 PowerShell 래퍼에 맞췄습니다. 이를 검증 대상 행위 자체를 약화한 변경으로 볼 여지가 없는지 독립 검토하십시오.
- 새 config 시험의 잘못된 문자열/바이트 리터럴은 구문 수준에서 수정됐습니다. 최신 기능 시험·정적 검사 전체 통과는 없습니다.

과거 검사 결과를 좁게 재사용해야 합니다:

1. `failure-contract-fix-20260909/worker-return-and-freeze.json`: 오류 반환 수정 당시 고유4사례, red4/green4/final-green4로 총12사례 실행. Ruff/basedpyright 통과는 작업자 보고이며 별도 명령 로그는 제공되지 않았다고 명시돼 있습니다.
2. E의 `hostshell-tests.log`: PowerShell 계약3사례 통과,1사례 제외,5.48초. 그 후 config/command를 변경했으므로 최신 후보의 통과가 아닙니다.
3. 최신 `cold-start-focused-tests.log`: 수집 단계 SyntaxError, 기능 사례 실행 전 중단. 구문 수정 이후 재실행하지 않았습니다.

비교용 작업 폴더 소스 SHA256(최초 작성에서 읽음, v9 해시 아님; v9 해시는0절):

| 파일 | SHA256 |
|---|---|
| `hooks/observe.cmd` | `3056f7d504d1176b580c1407dbc9af185b955f6a4674bd3857548f532b059522` |
| `hooks/correction-hooks.example.json` | `aa6fab3da9f8d13659c28a0d6e6cc76f35371ac3049fba8c31be2b782344d228` |
| `src/codex_ticket_dashboard/config.py` | `c797e4764fc37dc0629052822129db7ce7f826bd64f1dd50f26ba021ea09eedb` |
| `src/codex_ticket_dashboard/lifecycle/command.py` | `2baf1a32076def105a1c216624d6fd59e99169a38b06c50adca8b07de0bb6143` |
| `src/codex_ticket_dashboard/lifecycle/command_diagnostics.py` | `0e4e5957607a3d8e5c341d5001fd80895f1dcebed7c668cbeb79c0d4b3ebda6a` |
| `tests/unit/test_config.py` | `c1f6ab7e6cf6934cb8c2cd0a918b7496a9210775afa2aed4d9e7f83f5235ca3b` |
| `tests/integration/test_hook_failure_reporting.py` | `72379b52db0070ee4ba880d3d20f2588bc469544befc4a3093bc93d8b3c82701` |
| `tests/integration/test_lifecycle_spool.py` | `e58d190112e26a2c2658a776f95c19e6c34480703feaabc25108deabe5c20459` |

과거 검사 통과 소스와 해시가 다릅니다. 위 해시도 변경 식별용이며 정확성의 증명이 아닙니다.

## 8. 실행 환경 위치와 보존 사항

아래는 경로 안내이며 실행/복구 명령이 아닙니다.

| 대상 | 프로젝트 루트 기준 경로 |
|---|---|
| 시험 프로젝트 | `.omo/probes/correction-host-20260907` |
| 활성 Hook 정의 | 위 프로젝트의 `.codex/hooks.json` |
| 시험 MCP 설정 | 위 프로젝트의 `.codex/config.toml` |
| 활성 v9 의존성 | `.omo/probes/correction-runtime-20260908/deps-20260909-v9` |
| 활성 v9 제품 소스 | `.omo/probes/correction-runtime-20260908/product-20260909-v9/src` |
| 미완성 v10 의존성 | `.omo/probes/correction-runtime-20260908/deps-20260909-v10` |
| Hook 대상 dashboard 설정 | `.omo/probes/correction-runtime-20260908/qa-activation-20260908/dashboard.toml` |
| QA 데이터 | `.omo/probes/correction-runtime-20260908/product-20260908/qa-data` |
| QA DB | 위 데이터의 `data/dashboard.sqlite3` |
| 기존 설치 자료 | `docs/observation-installation.md`, `scripts/install-observation.ps1`, `scripts/uninstall-observation.ps1` |

v10 interpreter의 경로 설정은 아직 없는 product-v10을 향하므로 완성된 비교 실행 환경으로 취급하지 마십시오. 활성 v9를 직접 덮어쓰거나 기존 QA/운영 데이터, spool/archive, 다른 작업의 dirty 파일, 알 수 없는 프로세스를 정리하지 마십시오. 원래 장기 쓰레드/합성 쓰레드에 새 메시지를 보내지 마십시오.

## 9. Codex 동작 지침과 실제 어긴 점

사용자 지시와 로컬 작업 지침의 요약입니다. Claude Code의 동작은 Claude Code에 적용되는 지침과 사용자의 최신 요청에 따라 판단하십시오.

| 적용 지침 | 실제 문제와 교정 필요 |
|---|---|
| 지시한 범위와 직접 필요한 최소 조치만; 추가 작업은 사전 승인 | 조사·문서·검증을 묶어 범위를 넓힘. 현재 사용자 지시는 과거 포괄 승인보다 최신 |
| 확인된 사실만 보고, 완료/관측/승인 구분 | 구성요소 성공이나 관측 저장을 전체 진전으로 확대하기 쉬운 보고 반복 |
| 진단 전체 기본10분, 준비·전달·대기 포함; 새 근거 없는 재시험 금지 | 단계/담당/후보를 바꾸며 기존 접근을 계속함. 시간 상한을 실제 행동 제한으로 적용하지 못함 |
| 변경 범위의 최소 검사, 전체 시험/추가 검토자 기본 금지 | 검증 환경 자체 오류를 수리하며 추가 반복 발생 |
| 총괄이 목표·비용·접근 타당성을 판단, 독립 범위만 병렬화 | 동일 가설의 연장과 작업자 시간 초과를 제때 통제하지 못함 |
| 모델/추론을 작업 위험·비용에 맞게 명시 | 교정 계획에는 Astra medium/high 지정이 있고 실제 오류 반환 작업 영수증에는 Sol high가 있음. 후속 변경 승인·현재 라우팅 지침과의 관계를 확인할 필요가 있음 |
| KST·작업명 포함 진행 보고 | 처리/대기 중 긴 공백 발생. 기록한 상한 초과도 있음 |
| 컴퓨터 제어 전 앱/목적/항목/판정·종료 조건 출력, 중간 보고, 확인 직후 반환 | 확인 뒤 반환 통지가 불명확해 사용자 작업 방해. 현재 공통 AGENTS에 사전 고지·60초 보고·즉시 반환·분석/대기 중 점유 금지를 추가 |
| 사용자 작업·dirty 상태·데이터 보존, 무단 자동화 금지 | 후속 분석에서도 유지해야 하는 경계 |

일반적인 ‘완료까지 계속’ 방식으로 작은 실험을 이어 붙인 것이 적절했는지 검토하십시오. 구체적인 비용 제한과 실패 접근 종료 판단을 적용하지 못한 점이 작성자가 인정하는 핵심 감독 오류입니다. 지침을 더 쓰는 것만으로 실행을 물리적으로 차단하거나 재발을 보장할 수는 없습니다.

작성자의 최근 감사 자체도10:27:54 시작/10:37:54 상한 뒤11:08:17에 확인되어 초과했습니다. 검토자 생성 aborted, 장문 문서 저장 명령 잘림, Windows tzdata 미설치 사용으로 인한 자체 오류도 발생했습니다. 독립 승인이나 성공으로 세지 않았습니다. 이는 제품 결함과 별개인 실행 품질 문제입니다.

현재 사용자 요청은 **백데이터 문서 작성**입니다. 추가 조사/구현/검증을 무제한 승인한 요청이 아닙니다.

## 10. Claude Code에 요청하는 판단

다음 질문에 근거 파일/줄과 확실성을 붙여 답해 주십시오. 전체 저장소·세션을 먼저 훑지 말고 필요한 근거에서 시작하십시오.

1. 현재 실패의 확정 원인, 기여 요인, 아직 미확정인 구간은 무엇입니까? Codex가 원인·증상·시험 오류를 혼동한 결론을 정정해 주십시오.
2. 2–3초 Hook 안에 Python 기동·설정/모델 로딩·식별·보호 저장·Stop 처리를 두는 v9의 책임 배분은 적절합니까? v9 접근의 유지/최소 수정/일부 설계 변경 중 무엇을 권고합니까?
3. 관측이 성공해야 MCP 문맥/보완이 가능하고, 업무 기록은 모델 호출에 의존하는 연결이 원래 자동성·비차단·누락 표시를 충족합니까? 실패 시 독립적인 복구가 있는지 확인해 주십시오.
4. 추가 문맥 반환과 승인 설계의 차이, 모델 라우팅 지시와 실행의 차이는 승인된 변경입니까? 근거가 없으면 미확정으로 남겨 주십시오.
5. v9에 대한 독립 원인 판단을 먼저 내리십시오. 필요할 때만 미검증 config/CLI 후보가 그 원인에 대응하는 최소 수정인지 비교하고, 채택/보류할 부분을 제시하되 직접 원복하지 마십시오.
6. 실험을 반복하지 않고 의사결정을 내릴 수 있는 가장 작은 해결안은 무엇입니까? 해결 불가능한 Host 경계가 있다면 억지 대체 구현 대신 명시해 주십시오.

요청하는 결과물:

- `현재 접근 유지 / 최소 수정 / 일부 설계 변경 / 현재 조건에서 불가` 중 권고와 근거.
- 확인된 결함 목록: 근거, 영향, 기존 결론 정정 여부.
- 원래 목표와 권한/개인정보 경계를 유지하는 **한 개의 권고안**. 비교가 필요한 대안만 짧게 제시.
- 수정 파일과 구체 변경, 변경하지 않을 기반, 예상 위험, 되돌림 범위.
- 최소 확인 계획: 각 확인이 바꾸는 결정, 실행 환경, 최대 횟수/시간, 기존 증거 재사용, 실패 시 종료 조건. 지금 실행하지 말 것.
- 추가 승인/제품 판단이 필요한 항목과, 사용자에게 물을 필요 없이 분석으로 확정 가능한 항목 구분.
- 정확한 해결책을 확정할 근거가 없다면 `미확정`과 필요한 단 하나의 추가 증거를 제시. 통과 약속·완성 추정·새 반복 루프 금지.

## 11. 릴리즈까지 남은 작업

| 순서 | 남은 작업 | 범위 |
|---|---|---|
| R1 | 실제 자동 등록 연결 완성 | 현재 핵심 개발/연결 과제. 별도 기록 지시 없이 시작관측→MCP→티켓/작업/결과까지 연결 |
| R2 | 신규·재개·하위 작업/상태/화면 | 기존 구현의 미확인 통합 조건과 발견된 결함만 |
| R3 | 누락·중단·재시작 | 새 연결의 보존·한 번 반영·불완전 표시. 무변경 복구 로직 일괄 재시험 아님 |
| R4 | 사용자 결정·개인정보·읽기 전용 | 변경된 연결의 필수 경계만 기존 근거와 대조 |
| R5 | 승인된 실제 사용 환경 적용 | 최종 버전 고정·설치·복구·시험 설정 정리·운영 안내 |
| R6 | 실제 사용·사용자 수락 | 재부팅 후 수동 재시작 등 원래 조건과 명시 수락. 임의 재부팅 금지 |

6개 신규 기능이나6번의 모델 요청을 뜻하지 않습니다. R1이 미해결인 채 R2–R6 전체 검증을 펼치지 마십시오. 현재 신뢰할 완료율·소요 시간 추정은 없습니다.

## 12. 추가 근거 위치와 마지막 주의

- `.omo/evidence/goal-alignment-audit-20260908/failure-contract-fix-20260909/{final-result.json,worker-return-and-freeze.json}`: 과거 소스 동결/검사 범위.
- `.omo/evidence/auto-projection-product-20260908/{contracts,command,projection}/completion.json`, `ui-review/verdict.json`: 구현 기반의 과거 근거. 현재 버전에 자동 승계하지 않음.
- `.omo/evidence/auto-projection-product-20260908/acceptance-and-handoff.md`: 실제 수락 조건.
- `.omo/evidence/goal-alignment-audit-20260908/root-cause-process-audit-20260909/`: 최근 감독 실패·정책 기록.
- `docs/desktop-hook-dispatch-blocker-20260908.md`: 과거 막힌 조회/실험과 철회 이력. 최신 timeout 확인 이전 설명을 현재 상태로 재사용하지 않음.

이 문서 작성에서는 제품 코드·설정·서비스·다른 쓰레드에 손대지 않았고 기능 시험·새 모델 요청·컴퓨터 조작을 수행하지 않았습니다. 이 인계서의 존재는 제품 문제 해결이나 Claude Code의 승인/검토 완료를 의미하지 않습니다.
