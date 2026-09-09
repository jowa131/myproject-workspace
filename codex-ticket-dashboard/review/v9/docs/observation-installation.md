# 자동 관찰 설치와 복구

현재 문서는 설치 준비 절차입니다. `scripts/install-observation.ps1`과
`scripts/uninstall-observation.ps1`의 존재는 운영 적용이나 실제 Host 검증을
뜻하지 않습니다. 실행 증거는 `.omo/evidence/auto-projection-product-20260908/activation/`
아래의 활성화 패킷과 최종 적용 영수증을 따릅니다.

현재 시험 환경에는 보호 버전8 MCP·수집기·Hook이 설치돼 있습니다.
실행 종류의 정상 기본값 `unknown`을 보완 대상에서 제외한 두 조건을 수정한 뒤
34.429초에 정상 기동했고, 기존 기록과 보호 파일 보존을 확인했습니다.
일반 파일 작업에서 최초 보완 요청1개가 실제 생성됐지만 업무 기록은0건입니다.
보완 안내의 stdout 전달과 Codex의 후속 실행은 미확인입니다. 근거는
`activation/first-preflight-recovery/source-kind-fix/actual-ordinary/final-ordinary-result.json`과
`activation/first-preflight-recovery/source-kind-fix/review.json`입니다.
설치·기동·기존 기록 보존은
`activation/first-preflight-recovery/source-kind-fix/install-drafts/actual-install-result.json`에
있습니다. 이전 버전4의 설치·신뢰·시작 순서는
`activation/version4-sequence-summary.json`에서 확인하십시오. 실제
읽기 전용 HTTP 확인은 `activation/actual-v4-http-readonly.json`, 수집기 중단 중
생성된 종료 기록 한 건의 보존·재시작 후 단일 반영은
`activation/lifecycle-backlog/result.json`에 있습니다. 이 근거는 운영 환경 전환이나
일반 업무의 모든 기록·마무리가 성공했다는 뜻이 아닙니다.

보호 버전5와 프로젝트별 기록 도구 승인을 적용했던 일반 재개 작업에서는
업무 기록 일곱 건이 적용됐고 기존 티켓이 진행 중으로 바뀌었습니다. 완료 증거의
입력 형식 거절 두 건과 Wiki 근거 누락이 남아 검토 상태에는 도달하지 못했습니다.
근거는 `activation/recording-diagnosis/scoped-tool-approval/result.json`입니다.
버전6에서 새 일반 파일 작업은 결과 파일을 만들었지만 업무 기록은 0건이었습니다.
결과는 `activation/recording-diagnosis/input-hints/actual-ordinary/result.json`을
따릅니다. 첫 MCP 기록이 없으면 기존 Stop 보완의 티켓·증거 선행 조건도 충족하지
못하는 공백을 확인했고, 별도 최초 사전 기록 요청을 구현·집중 검증·독립 검토한 뒤
설치했습니다. 과거의 명확히 다른 작업 실패만 현재 판정에서 분리하고, 같은 턴의
실패·식별 불명·불안정 읽기는 계속 차단합니다. 기존 실패 자료와 보완 횟수는
보존합니다. 버전8에서는 첫 사전 기록 누락의 감지와1회 요청을 확인했으며,
후속 자동 기록과 마무리는 아직 미완료입니다. 이전 재개
작업의 업무 기록 0건과 호출 미확인 판정도 별도 역사로 유지합니다.
남은 실제 조건은 `acceptance/remaining-actual-checks.md`를 따릅니다.
공식 여섯 Hook 신뢰 등록 뒤 전역 설정 해시는 바뀝니다. 버전8 적용에서는 정확한
여섯 신뢰 값만 메모리에서 이전 값으로 되돌린 전체 해시를 대조해 나머지 바이트
보존을 확인했습니다. 전역 파일을 직접 복원하지 않았습니다. 버전7 당시의 미확인
판정은 `security-review/v7-trust-boundary.json`에 별도 역사로 유지합니다.
프로젝트 지침 파일을 바꾼 뒤 이전 대화를 재개했다는 사실만으로 새 지침 전달을
확인하지 마십시오. 고정 Codex 소스의 재개 경로와 실제 증거는
`activation/recording-diagnosis/resume-guidance-source-conclusion.json`에 구분했습니다.

원래 운영 등록과 주 프로젝트 연결은 아직 전환하지 않았습니다. 시험용 프로젝트
설정 복구와 해당 시험 서비스 종료 후에만 운영 등록과 주 프로젝트 연결을
순서대로 적용합니다. 실제 설치에 사용한 버전별 명세·해시·복구 영수증을 사용하며,
과거 `activation/final-draft/` 준비 파일을 최신 설치 사실로 대신하지 않습니다.

## 범위와 실행 전제

- 기존 `prj_codex_ticket_dashboard`, 등록 루트 하나와 빈 `worktree_roots`를
  유지합니다. 전역 Codex 설정, 다른 프로젝트, 주기 작업, 자동 시작은 변경하지 않습니다.
- 총괄의 소스 준비 판정 후에만 버전별 설치 명세를 `SOURCE_READY`로 고정합니다.
  같은 승인 대상에 대한 재승인 단계가 아니라 코드·검증 결과의 기술적 선행 조건입니다.
- 설치 명세 전체 SHA256을 명시적으로 전달합니다. 설치기는 원본 파일과 변경 전
  대상의 해시가 명세와 다르면 중단합니다. 기본 모드는 쓰기가 없는 `Preflight`입니다.
- 보호 실행 파일, 의존성, 제품 코드와 설정은 기존 보호 폴더
  `.omo/probes/correction-runtime-20260908`의 새 버전 하위 폴더에 고정합니다.
  폴더와 파일은 현재 사용자 전용 ACL과 상속 차단을 유지합니다.
- 실행 환경은 개발 `.venv`로 돌아가는 편집 가능 설치를 사용하지 않습니다.
  `.pth`는 설치 대상에서 거부합니다. 필요한 운영 의존성만 복사하고 복사 전에
  파일 수·바이트 수를 기록합니다. 테스트·브라우저·개발 패키지는 관성적으로 복사하지 않습니다.
- 실제 실행 파일, 표준 라이브러리, DLL, 제품 모듈의 import 경로와 환경변수·사용자
  site 경로 차단은 별도의 보호 실행 검증으로 확인합니다. 파일 해시 대조만으로
  실행 경로 전체가 보호되었다고 판정하지 않습니다.

## 설치 명세

명세에는 `schema_version: 1`, `status: SOURCE_READY`, 기존 `project_id`,
정규 절대 `project_root`, 보호된 새 `runtime_root`, 순서가 고정된 `files`를 둡니다.
`purpose`는 `IMMUTABLE_RUNTIME`, `PRODUCT_ACTIVATION`, `INSTALLER_SELF_CHECK`
중 하나입니다. 마지막 값은 정확히 보호된 `installer-check-20260908/synthetic/`
안의 `existing.txt`·`new.txt` 두 시험 파일만 허용하며 다른 경로는 거부합니다.
각 파일에는 `source`, `target`, `sha256`, `before_sha256`, `acl`, `rollback`을 둡니다.
변경 전 파일이 없으면 `before_sha256`은 `ABSENT`입니다.

`acl`은 새 보호 파일의 `owner-only` 또는 기존 외부 파일의 `preserve`입니다.
`rollback`은 기존 설정·Hook을 되돌리는 `restore` 또는 새 버전 코드·등록 문서를
보존하는 `retain`입니다. 코드·의존성·설정 사본을 먼저 놓고, 실제 Host가 읽는
Hook/MCP 설정은 맨 마지막에 놓습니다. 준비 중인 빈 명세나 미정 해시는 실행할 수 없습니다.

설치기는 현재 프로젝트 `config.toml`, 버전이 명명된 등록 문서, 프로젝트 및 기존
합성 S의 `.codex/config.toml`·`.codex/hooks.json`, 지정된 보호 실행 폴더 안의
파일만 허용합니다. 이것은 경로 상한이며 모든 경로를 실제로 변경한다는 뜻은 아닙니다.
최종 명세는 해당 회차에서 필요한 정확한 파일만 담아야 합니다. 새 외부 부모 폴더는
설치기가 만들지 않으므로 그 폴더의 소유권과 생성 작업도 사전에 명세화해야 합니다.

```powershell
$release = '<실제로 동결한 설치 명세 절대 경로>'
$digest = '<검토한 명세의 SHA256>'
& .\scripts\install-observation.ps1 -Manifest $release -ManifestSha256 $digest
& .\scripts\install-observation.ps1 -Manifest $release -ManifestSha256 $digest -Mode Apply -ExclusiveWritersConfirmed
```

위 명령은 해당 PowerShell 환경의 실행 정책을 그대로 따릅니다. 실행 정책이 스크립트를
허용하지 않으면 정책 변경이나 우회 플래그를 추가하지 않습니다. 실제 적용자는
검증된 공식 실행 경로와 적용 영수증을 패킷에 고정해야 합니다.

실제 적용과 복구 전에는 해당 설정을 쓰는 Host·편집기·다른 작업자를 중단하거나
그 쓰기 범위를 배제한 근거를 확인하고 `-ExclusiveWritersConfirmed`를 전달합니다.
이 값은 사용자 재승인 요청이 아니라 실행자가 확인하는 필수 운영 전제입니다.
설치기는 실제 부모 디렉터리의 최종 경로·reparse 여부를 handle로 검증하고 삭제
공유 없이 작업 끝까지 유지합니다. 보호된 operation.lock은 이를 따르는 설치기끼리
배타적으로 실행합니다. 복사 중 대상 파일의 읽기 handle도 다른 쓰기를 허용하지
않습니다. 파일 교체 직전의 짧은 간격까지 비협력적인 동일 사용자 writer를 막는
무조건적 compare-exchange는 제공하지 않으므로 위 쓰기 배제 전제가 필요합니다.

## 등록 근거와 현행 정책

`authority_source_ref`와 `authority_source_sha256` 두 필드만 검토된 불변 등록
문서로 바꿉니다. 등록 문서는 원본 초안과 바이트가 같아야 하며 설치된 실제 파일의
해시를 다시 읽어 비교합니다. 과거 사건·정책 스냅샷·차단된 티켓은 다시 쓰지 않습니다.

불변 등록 문서는 프로젝트 식별과 Wiki 경로의 근거입니다. 현행 전역·프로젝트
AGENTS와 실제 권한의 변경을 고정하거나 면제하지 않습니다. 정책 근거는 그때의
실제 파일 바이트를 별도로 읽어 수집해야 합니다. 상수를 전달하거나 오래된 Wiki
해시를 현재 관측이라고 부르지 않습니다. 중앙 Wiki 권위도 이전하지 않습니다.

## Hook 신뢰와 실제 사용

설치기는 Hook 신뢰 DB를 변경하거나 프로세스를 시작·종료하지 않습니다.
현재 공식 경로는 CLI의 `/hooks`에서 실제 정의를 개별 검토하고 신뢰하는 것입니다.
새 정의와 변경된 정의는 신뢰 전 실행되지 않습니다.
[공식 Hook 문서](https://learn.chatgpt.com/docs/hooks)

신뢰 검토 전에는 최종 `.cmd` 실행기와 Hook 정의, 보호된 Python, 설정, 코드의
해시를 확인합니다. 시험은 승인된 합성 범위에 한정하며 기존 신뢰 레코드를
직접 쓰거나 일괄 우회하지 않습니다. 일반 작업의 원문·도구 입출력·환경 전체를
설치 영수증이나 시험 로그에 저장하지 않습니다.

## 복구

먼저 확인된 소유 프로세스의 실제 실행 파일·시작 시각·설정 경로·포트를 확인한 후
그 프로세스만 종료합니다. 오래된 PID나 포트 점유만으로 종료하지 않습니다.
그다음 같은 명세와 해시로 복구합니다.

```powershell
& .\scripts\uninstall-observation.ps1 -Manifest $protectedManifest -ManifestSha256 $digest -ExclusiveWritersConfirmed
```

`$protectedManifest`는 해당 버전의 `installation/manifest.json`입니다. 설치기는
명세를 한 번 읽은 동일 바이트의 해시를 검증·파싱하고, 실제 파일 적용 전에 그
바이트를 보호된 원자 사본으로 보존합니다. 원래 작업 폴더의 명세가 없어져도 이
사본과 외부에서 고정한 SHA256으로 복구할 수 있습니다.

복구는 적용 순서의 역순으로 `restore` 파일만 되돌립니다. 설치 후 다른 사람이
바꾼 파일은 해시 불일치로 보존하고 중단합니다. 원래 있던 파일은 보호된 백업의
바이트와 ACL로 복구합니다. 이 설치가 새로 만든 설정 파일만 정확한 경로로
삭제할 수 있으며 재귀 삭제는 없습니다. 보호 실행 폴더, 불변 등록 문서, DB,
spool, archive, 적용·복구 증거는 보존합니다. 신뢰 레코드 제거도 자동으로 하지 않습니다.

ACL 복구는 감사 권한을 요청하지 않는 .NET의 Access·Owner·Group 전용 API를
사용합니다. 실제 Windows 파일 교체가 추가하는 `DiscretionaryAclAutoInherited`
표시만 대조에서 제외하고 소유자·그룹·DACL·상속 차단의 차이는 모두 거부합니다.
이 표시는 권한 허용 ACE의 추가가 아닙니다. PowerShell의 빈 문자열 변환을
피하도록 파일 교체의 미사용 백업 인수에는 명시적인 CLR null을 전달합니다.

중간 실패 시 자동 전체 되돌림을 시도하지 않습니다. 이미 쓰인 파일·백업·적용
표식을 보존하고 같은 명세로 복구합니다. 복구 준비 파일은 시도마다 고유한 이름을
사용하므로 이전 중단으로 남은 완전·부분 `.restore` 파일이 다음 복구를 막지 않으며
그 잔여 파일도 자동 삭제하지 않습니다. 원본 소스가 이후 변경되어도 복구는
설치 당시의 명세와 백업 해시에 의존합니다. 다음 활성화는 새 버전 폴더와 새 명세를 사용합니다.


## 요청별 안내와 접수 진단

고정 기록 안내의 단일 원본은 `recording_guidance.py`입니다. 현재 등록 경로에서
성공적으로 접수된 `UserPromptSubmit`만 이 안내를 공식 JSON 응답으로 반환합니다.
기존 MCP 안내도 보존합니다. 설치 시에는 이 작업이 추가한 중복 프로젝트 지침만
명세와 해시로 제거하며, 기존 사용자 설정은 보존합니다. 안내를 반환했다는 사실은
모델이 업무 기록을 작성했거나 업무가 완료됐다는 증거가 아닙니다.

접수 전 진단은 보호된 `logs` 안의 인스턴스별 횟수와 허용된 오류 코드만 저장합니다.
인수·응답 본문·원문·사용자/작업 식별값은 저장하지 않습니다. 진단 기록 실패는 기존
업무 결과나 예외를 바꾸지 않으며 진단의 신뢰성만 무효화합니다.

호출 0회를 판정하려면 같은 프로세스 번호와 인스턴스 nonce에 대해 이번 SDK 시작
뒤의 열린 기준 기록과 그보다 큰 revision의 종료 기록을 모두 확인해야 합니다.
종료 기록은 `closed=true`, `reliable=true`, `lifespan_entries=1`, `write_failures=0`,
`in_flight=0`, `entered=0`이어야 합니다. 없거나 오래되거나 불완전한 기록은 미확인입니다.
이 판정도 해당 서버의 도구 진입점에 도달한 호출만 다루며 다른 서버나 전송 시도는
판정하지 않습니다. 응답 횟수는 수집기의 업무 적용 결과와 별개입니다.

소스·집중 검증과 독립 검토는 `activation/source-ready-v5-release.json` 및
`security-review/turn-guidance-diagnostics-review.json`에 결속했습니다. 실제 설치와
일반 업무 연결 여부는 이후 별도 실행 영수증을 확인하십시오.

## 프로젝트별 기록 도구 승인

Codex의 전역 승인 정책이 `never`인 환경에서는 승인이 필요한 도구가 서버에
도달하기 전에 거절될 수 있습니다. 전역 정책을 변경하는 대신, 승인된 대상
프로젝트의 `[mcp_servers.codex_ticket_dashboard.tools.<tool>]`에
`approval_mode = "approve"`를 명시하는 공식 설정을 사용했습니다.

적용 범위는 `ticket_preflight_record`, `task_upsert`, `ticket_status_update`,
`ticket_turn_summary`, `git_gate_report`, `wiki_update_record` 여섯 도구입니다.
사용자 완료·취소·재개 결정을 기록하는 `ticket_user_decision_record`는 제외합니다.
이 설정은 도구 입력·권한·정책 검사나 Codex의 엄격한 자동 검토를 해제하지 않습니다.

현재 시험용 설정은 사용자 원본188바이트와 여섯 도구 승인 의미를 보존합니다.
소유 추가 구간의 줄바꿈 정규화 때문에 과거674바이트 전체의 동일성을 주장하지 않습니다.
적용·복구는 `activation/recording-diagnosis/scoped-tool-approval/`의 실제 명세와
현재 해시를 대조한 뒤 수행합니다. 이 승인이 다른 프로젝트나 운영 환경에도
적용됐다고 가정하지 마십시오.

## 입력 형식 오류의 복구 안내

버전6은 알려진 요청 모델의 오류에 공개 도구·필드 이름과 고정 오류 코드만
최대 세 개 반환합니다. 잘못된 입력은 계속 거절하며 동적 경로·사전 키·입력값·
예외 원문을 반환하거나 진단에 저장하지 않습니다. 내부 모델에서 발생한 오류는
기존 일반 오류로 유지하므로 이를 모델의 입력 실수라고 단정하지 마십시오.

Wiki 근거의 경로 객체를 사건 문자열로 변환하는 결함은 같은 버전에서 수정했습니다.
검증된 변경 전후 해시와 실제 상대 경로를 신고해야 하며, 빈 경로나 만들어 낸
근거로 검토 상태를 통과시키지 않습니다. 이 집중 검증의 성공은 일반 작업 전체의
자동 기록 성공과 구분합니다.
