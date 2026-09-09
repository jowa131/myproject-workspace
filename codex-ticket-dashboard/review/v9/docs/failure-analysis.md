# 자동 기록 실패의 원인 분석과 수정 방안

2026-09-09 KST. 이번 범위는 분석 및 보고입니다. 제품/설정 변경, 새 모델 시험, 작업자, 앱 입력, 런타임 시험, 빌드는 모두 0입니다.

## 결론과 확실성

**확정한 결함은 실패를 정상 종료로 바꾸는 오류 반환 계약입니다. 최근 실제 요청의 최초 관측 누락 원인은 아직 미확정입니다.** 두 결론을 합쳐 오류 반환 결함이 과거 실패의 직접 원인이라고 주장하지 않습니다.

1. hooks/observe.cmd:2-3은 Python 실행 뒤 결과와 관계없이 `exit /b 0`을 반환합니다. 소스와 설치 v8 파일이 같습니다. SHA256: 9496d7a17889166659fe92403c79cbbe6771230e9bee7ad4667e12f15cb87047.
2. lifecycle/command.py:66-80은 입력/설정/저장 오류를 고정 코드로 stderr에 쓰지만 실패 종료 코드를 반환하지 않습니다. 설치본과 소스가 같습니다. SHA256: ad5c3d8ac5bbe04f7ffee54f8a8eb1e7189e9e364c11be37c58c04f0555be45f.
3. 공식 user_prompt_submit.rs:126-148은 상태를 Completed로 시작하며 exit0이면 stdout만 해석합니다. 빈 stdout은 상태를 바꾸지 않고 이 분기에서 stderr 오류를 해석하지 않습니다. 따라서 `수신 오류 → stderr만 출력/빈 stdout → exit0 → Hook Completed`라는 경로가 코드상 성립합니다. 실제 세 회차에서 그 경로가 발생했다는 뜻은 아닙니다.
4. tests/integration/test_lifecycle_spool.py:211-234는 입력 거부와 저장 실패에도 exit0을 기대하고 stderr만 검사합니다. 본 작업 비차단과 Host의 실패 구분을 혼동한 계약을 통과시킬 수 있습니다. 이번에 해당 시험을 실행한 것은 아닙니다.

## 실패 뒤 자동 등록이 회복되지 않는 이유

- command.py:34-48은 관측 접수가 끝난 뒤에야 모델에게 MCP 기록 안내를 반환합니다. Hook 자체가 의미 있는 티켓을 생성하지 않습니다.
- mcp/official_context.py:125-146은 같은 작업/회차 관측이 없으면 OBSERVER_CONTEXT_MISSING으로 거절합니다. 이것은 호출될 때의 조건이며 실제 세 회차에서 MCP가 그 오류를 반환했다고 단정하지 않습니다.
- lifecycle/initial_preflight.py:45-57은 반영된 UserPromptSubmit 관측이 없으면 최초 기록 보완 대상에서 제외합니다. 다른 Hook 관측만으로는 이 조건을 충족하지 않습니다.
- 따라서 시작 관측 누락 상태에서 같은 요청이나 안내 문구를 반복하는 방식은 독립적인 복구 경로가 아닙니다. 식별 보호를 삭제하거나 다른 작업의 ID를 가져오는 것은 해결안이 아닙니다.

## 아직 구분하지 못한 실제 원인

| 가능성 | 현재 판단 |
| --- | --- |
| Host가 대상 명령을 선택/호출하지 않음 | 실제 선택/시작 결과가 없어 미확정 |
| 수신 오류가 정상 종료로 가려짐 | 은폐 계약은 확정, 해당 회차 발생 여부는 미확정 |
| 3초 제한 초과 | Host timeout 결과가 없어 미확정. 임의 제한 확대 금지 |
| 티켓 등록 코드만 고장 | 선행 관측부터 없으므로 그 단계로 원인을 좁힐 근거 없음 |

공식 core/hook_runtime.rs:628-664는 UserInput에 대해서만 UPS를 호출하고 내부 통신/결과 입력은 건너뜁니다. 분기 존재만으로 실제 UI 요청이 내부 입력이었다고 추정하지 않습니다. command와 commandWindows의 Windows 선택 분기도 확인했지만 정적 명령 불일치는 찾지 못했습니다.

## 권고 수정 순서

**첫 수정 후보는 확정된 오류 반환 계약입니다.** 직전의 대체 경로 우선 검토 권고를 이 구체 결함 수정 우선으로 갱신합니다. 이것만으로 자동 티켓 등록이 복구된다고 보장하지 않습니다.

1. `lifecycle/command.py`, `hooks/observe.cmd`, `hooks/correction-hooks.example.json`과 관련 집중 시험에서 성공과 비차단 실패를 구분합니다. Python → cmd → PowerShell 전체가 오류를 무조건0으로 덮지 않아야 합니다.
2. 정상은 0, 일반 실패는 1로 정규화하는 안을 사용합니다. 공식 UPS에서 1은 Failed이며 should_stop=false이고, 2는 조건에 따라 사용자 요청을 차단합니다. 원래 종료 코드를 무조건 전달하는 수정은 안 됩니다. 공통 래퍼가 영향을 주는 6개 Hook의 오류 의미도 정적으로 대조하고 정상 Stop 보완의 기존 JSON 권한/횟수 계약을 보존합니다.
3. 고정 오류 코드를 원문 없는 최소 처리 결과로 구분해야 합니다. exit1만 바꾸면 공식 결과에는 일반 종료 코드만 표시될 수 있습니다. 기존 보호 경로에 회차/처리 단계/허용 오류 코드만 남기는 최소 기록을 설계합니다. 입력 파싱 전에는 회차를 추정하지 않고 원문 stdout/stderr를 저장하지 않습니다. 새 서버나 주기 수집기는 만들지 않습니다.
4. 구현 후 집중 검증은 정상 접수, 입력 거부, 저장 실패, Python 기동 실패 4사례로 제한합니다. 외부 명령까지 결과 전달, 본 작업 비차단, 원문 미노출이 기준입니다. 과거 잘못된 cmd 비교 도구의 결과를 재사용하지 않습니다.
5. 설치 명세와 소유 정의의 공식 신뢰를 맞추고 결과를 읽을 수 있는 수단을 먼저 확보한 뒤 실제 대표 요청 1회를 확인합니다. 진입 기록이 없다는 사실만으로 미호출을 확정하지 않고 Host 시작/명명된 오류와 대조합니다. 같은 요청을 반복하지 않습니다.
6. 얻은 정확한 오류에 따라 수신기 또는 Host 연결을 최소 수정합니다. 지원되는 진입 경로가 없다고 확인된 경우에만 같은 제품 목표를 충족하는 대체 설계로 전환합니다. 종료 기록만으로 시작/진행 추적을 대체하지 않습니다.

위 검증과 수정은 다음 구현 단계의 구체 범위이며 이번에 실행하지 않았습니다. 최초 누락의 직접 원인이 확정되지 않은 점은 미해결로 남깁니다.

## 근거

- 고정 버전 대응: `.omo/evidence/correction-x1-remaining-20260908/mcp-source/source-manifest.json`의 rust-v0.153.4와 commit 3d2ee51ca2d5db578f328aa75e20aa22c0197c9a.
- [공식 UPS 결과 처리](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/hooks/src/events/user_prompt_submit.rs#L126).
- [공식 사용자 입력 분기](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/hook_runtime.rs#L628).
- 기존 실제 실패/직접 접수: `.omo/evidence/goal-alignment-audit-20260908/r1-admission-storage/` 및 `r1-input-readiness/native-comparison.json`.
- 이번 소스 보존 근거: `.omo/evidence/goal-alignment-audit-20260908/failure-contract-analysis-20260909/`.

- 2026-09-09 구현 결과: 오류 반환 및 보호된 단계별 진단 수정 완료. 담당 최종 집중4사례/Ruff/basedpyright 통과 보고와 총괄 소스 동결 대조 완료. 새 v9 설치 뒤 사용자가 컴퓨터 조작을 중단하여 소유 Hook 정의는 v8로 복원했습니다. 실제 요청0, 서비스 재시작0, 활성 적용/자동 티켓 등록은 미검증입니다. 근거: `.omo/evidence/goal-alignment-audit-20260908/failure-contract-fix-20260909/final-result.json`.

- 2026-09-09 02시 재개 결과: 사용자 재개 승인 후 SessionStart1개 v9 신뢰 완료, 남은5개는 자동 승인 검토에서 거절되어 기존 v8 명령으로 안전 복원했습니다. 기존 데이터/다섯 신뢰/다른 설정 보존, 실제 요청0. 상태 BLOCKED_AUTO_APPROVAL_FIVE_HOOK_TRUST. 다음은 해당5개 샌드박스 밖 실행의 명시적 신뢰 승인입니다. 근거: `.omo/evidence/goal-alignment-audit-20260908/failure-contract-fix-20260909/resume-result.json`.

## 2026-09-09 실제 실행에서 확인한 정정

- 신뢰 승인은 해소되어 대상6개 정의가 적용됐습니다. 작업 전달 도구의 FunctionCallOutput은 UPS 직접 입력 표본이 아닙니다.
- 직접 Desktop 입력의 Hook 상세 결과에서3초 시간 초과를 확인했습니다. Hook 셸은 환경 셸을 따르므로 Desktop PowerShell 안에서 다시 PowerShell을 실행하던 계층을 제거하고 호출 연산자/오류코드 전달을 유지했습니다. COMSPEC 전용 시험을 Desktop 검증으로 보지 않습니다.
- 09:50 회차는 Stop 관측1건 저장에 성공했으나 Host의 UPS/Stop3초 시간 초과와 업무 사건0이 남습니다. 초기 기동 비용 수정 진행 중이며 자동 등록/제품 완료를 주장하지 않습니다.
- 근거: `.omo/evidence/goal-alignment-audit-20260908/hook-trust-approval-20260909/`. R1–R6의 조건과 기존 구현 재사용 원칙은 유지합니다.
