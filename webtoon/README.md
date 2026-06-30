# Webtoon

회사 에피소드를 웹툰형 콘텐츠로 각색하고 관리하는 프로젝트입니다.

## 현재 범위

- 실제 회사 경험을 바로 공개하지 않고, 인물과 조직을 특정할 수 없도록 각색합니다.
- 현재 산출물은 인스타용 4컷 웹툰 기획안, 캐릭터 설정, 에피소드 로그입니다.
- 공개 채널은 아직 정하지 않았습니다. 공개 전에는 개인정보, 회사 정책, 명예훼손 위험을 점검합니다.

## 문서

- `docs/company-episode-webtoon-workflow.md`: 회사 에피소드 웹툰화 제작 워크플로
- `docs/series-100-episode-roadmap.md`: 100화 시리즈 큰 흐름
- `docs/anonymized-career-story-spine.md`: 실제 경력 흐름을 익명화한 장기 서사 축
- `docs/episode-title-roadmap-100.md`: 1~100화 제목 전용 로드맵
- `docs/instagram-4cut-production-requirements.md`: 인스타 4컷 웹툰 제작 준비 목록
- `docs/anonymization-and-publication-checklist.md`: 캐릭터 익명화 규칙과 공개 전 점검표
- `episodes/README.md`: 에피소드 로그 저장 형식
- `templates/episode-input.md`: 첫 에피소드 입력 템플릿
- `templates/episode-001-interview.md`: 1화 시작 전 인터뷰 질문지

## 콘텐츠 저장 형식

초기 저장 형식은 Markdown episode log와 YAML front matter를 함께 사용합니다.

- `episodes/` 아래에 에피소드별 Markdown 파일을 둡니다.
- YAML front matter에는 상태, 공개 범위, 감정 축, 캐릭터 역할, 안전 점검 결과처럼 나중에 데이터로 변환하기 쉬운 항목만 둡니다.
- 본문에는 4컷 기획안, 대사 초안, 코미디 포인트, 공개 전 수정 메모를 씁니다.
- 원본 실명, 회사명, 고객명, 프로젝트명, 날짜, 금액, 내부 자료, 비밀정보는 에피소드 로그에 저장하지 않습니다.

## 작업 원칙

- 실명, 회사명, 고객명, 프로젝트명, 날짜, 금액, 내부 자료는 원문 그대로 기록하지 않습니다.
- 원본 사건은 비공개 메모에만 두고, 공개용 기획안에는 각색된 구조와 감정만 남깁니다.
- 비난보다 상황 코미디와 업무 공감을 우선합니다.
