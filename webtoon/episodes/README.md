# 에피소드 로그 저장 형식

## 기본 결정

에피소드는 Markdown 파일 하나를 하나의 기획 로그로 관리합니다. 파일 상단에는 YAML front matter를 두고, 본문에는 인스타용 4컷 웹툰 기획안을 씁니다.

이 저장소에는 실제 사람, 회사, 고객, 프로젝트, 날짜, 금액, 내부 자료, 비밀정보를 원문 그대로 저장하지 않습니다. 공개 가능한 각색 구조와 감정만 남깁니다.

## 파일 이름

권장 형식:

```text
episodes/YYYY-MM-short-slug.md
```

- `YYYY-MM`은 작성 월 또는 가상의 시즌 구분입니다. 실제 사건 발생일을 뜻하지 않습니다.
- `short-slug`에는 실제 회사, 고객, 프로젝트명을 쓰지 않습니다.
- 예: `2026-06-meeting-loop.md`, `2026-06-deadline-mirror.md`

## YAML front matter

```yaml
---
id: 2026-06-example
status: draft
visibility: private-draft
source_sensitivity: high
theme: communication
core_emotion: awkward
panel_count: 4
cast:
  - role: requester
    alias: "급한 요청자"
  - role: resolver
    alias: "침착한 정리자"
safety:
  real_names_removed: false
  company_names_removed: false
  customer_names_removed: false
  project_names_removed: false
  dates_and_amounts_blurred: false
  secrets_removed: false
  public_ready: false
---
```

## 본문 구조

```markdown
# 에피소드 제목

## 한 줄 로그라인

## 각색된 배경

## 캐릭터

## 4컷 구성

| 컷 | 장면 | 대사/텍스트 | 코미디 포인트 | 안전 메모 |
| --- | --- | --- | --- | --- |
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |

## 공개 전 수정 메모

## 보류 사유
```

## 상태 값

- `draft`: 작성 중
- `needs-anonymization`: 식별 단서 제거 필요
- `needs-review`: 공개 전 체크 필요
- `public-candidate`: 공개 후보
- `hold`: 민감도 때문에 보류

## 공개 범위 값

- `private-draft`: 비공개 초안
- `internal-candidate`: 내부 공유 후보
- `public-candidate`: 공개 후보

## 운영 규칙

- 원본 사건 전문을 붙여 넣지 않습니다.
- 식별 가능한 사실은 `공개 전 수정 메모`에 "흐려야 함"처럼 처리 과제로만 적습니다.
- 안전 체크가 하나라도 `false`이면 `public_ready`도 `false`로 둡니다.
- 공개 후보가 된 파일도 업로드 전 `docs/anonymization-and-publication-checklist.md`를 다시 통과해야 합니다.
