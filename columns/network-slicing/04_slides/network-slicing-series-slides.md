# 네트워크 슬라이싱 컬럼 연재 구성

통신 실무자가 보는 규격, 시험, 벤더 구현, 상용화의 거리

---

## Skill 조합 판단

| 목적 | LazyCodex Skill |
|---|---|
| 표준/벤더/상용 사례 심층 조사 | `omo:ultraresearch` |
| 3GPP, GSMA, 벤더 PDF 분석 | `pdf:pdf` |
| 원고 초안/문서화 | 기본 Codex, 필요 시 `documents:documents` |
| 구조도/동작 흐름 시각화 | Mermaid, 필요 시 `imagegen` |
| 최신 발표 검증 | Web browsing |

---

## 전체 연재의 중심 질문

네트워크 슬라이싱은 정말 상용화되었는가?

- 표준은 무엇을 정의했는가
- 실제 시험에서는 무엇이 다르게 보이는가
- 벤더들은 무엇을 다르게 구현했는가
- 상용 사례는 어디까지 믿을 수 있는가

---

## 추천 연재 흐름

1. QCI/RB와 슬라이싱 차이
2. 규격 기반 동작 원리
3. 시험 경험 기반 해석
4. RAN/Transport slicing 심화
5. 벤더별 구현 차이
6. 상용화 사례 판별법
7. URSP와 단말
8. 5G-A와 다음 단계

---

## 1편

# QCI 기반 자원 배분과 네트워크 슬라이싱은 무엇이 다른가

핵심 메시지:

> QCI/5QI 기반 RB/PRB 할당은 RAN slice 구현 수단이 될 수 있지만 end-to-end slicing 자체는 아니다.

다룰 내용:

- QCI/5QI는 QoS 처리의 언어다
- RB/PRB 배분은 주로 RAN scheduler/RRM 영역이다
- slicing은 RAN, transport, core, policy, assurance를 묶는 운영 모델이다

---

## 2편

# 3GPP 규격으로 보는 동작 원리

핵심 메시지:

> 표준은 슬라이스를 선택하고 관리하는 공통 언어를 제공한다.

다룰 규격:

- `TS 23.501`: 5GS architecture
- `TS 23.502`: procedures
- `TS 23.503`: policy, URSP
- `TS 28.530` 계열: management/orchestration
- `TS 29.531`: NSSF
- GSMA GST/NEST

---

## 2편 핵심 용어

- `S-NSSAI`
- `Configured NSSAI`
- `Requested NSSAI`
- `Allowed NSSAI`
- `NSSF`
- `URSP`
- `NSSAA`
- `NSI / NSSI`

---

## 3편

# 실제 시험에서 본 슬라이스

핵심 메시지:

> 설정은 됐는데 체감이 안 달라질 수 있다.

다룰 내용:

- Allowed NSSAI와 실제 트래픽 경로는 다르다
- URSP, DNN, PDU Session을 같이 봐야 한다
- QoS rule, 5QI, RAN policy가 체감 품질을 좌우한다
- NAS/Core/RAN 로그를 함께 봐야 한다

---

## 4편

# RAN slicing과 transport slicing은 어디서 보장되는가

핵심 메시지:

> 무선과 전송망이 slice-aware하지 않으면 end-to-end 보장은 약해진다.

다룰 내용:

- RAN scheduler/RRM과 PRB 정책
- slice-aware QoS Flow handling
- transport path, queue, bandwidth, latency 관리
- hard isolation과 statistical isolation의 차이
- RAN/Core/Transport가 어긋날 때 생기는 시험 결과

---

## 5편

# 벤더별 구현 철학

핵심 메시지:

> 같은 표준을 구현해도 벤더가 먼저 푸는 문제가 다르다.

비교 축:

- Huawei: deterministic networking, transport, vertical
- Samsung: E2E slicing, orchestration, RIC/SLA assurance
- Ericsson: RAN slicing, automation, differentiated connectivity
- Nokia: FWA, edge slicing, on-demand, AI/intent

---

## 6편

# 상용화 사례를 제대로 읽는 법

핵심 메시지:

> Commercial, live trial, PoC, product capability는 다르다.

분류 기준:

- Product capability
- Lab demo / PoC
- Live-network trial
- Commercial service

---

## 6편 사례 후보

- Ericsson / Singtel
- Ericsson / Telstra
- Nokia / Telia Finland
- Samsung / KDDI
- Huawei / China power grid
- Airtel postpaid slicing
- Deutsche Telekom 5G+ Gaming

---

## 7편

# URSP와 단말

핵심 메시지:

> 앱 기반 slicing은 단말 정책 없이는 완성되지 않는다.

다룰 내용:

- URSP가 앱 트래픽을 PDU Session으로 연결하는 방식
- Android/iOS, modem, SIM, operator policy 영향
- compatible device의 중요성
- consumer slicing의 현실적 병목

---

## 8편

# 5G-A와 slicing의 다음 단계

핵심 메시지:

> 다음 전장은 automation, exposure, intent, AI다.

다룰 내용:

- Rel-18 이후 slice exposure
- enterprise self-service
- closed-loop assurance
- intent-driven management
- AI/agentic slicing

---

## 연재 전체 톤

기술 소개보다 실전 해석 중심

- 표준은 기준선으로 사용
- 시험 경험은 현실감을 주는 장치
- 벤더 비교는 우열보다 구현 철학 중심
- 상용화 사례는 표현 강도를 엄격히 구분

---

## 추천 제목

# 네트워크 슬라이싱의 실제

규격, 시험, 벤더 구현, 그리고 상용화의 거리

---

## 다음 작업

1. 2편 규격 근거 표 정리
2. 시험 경험 메모를 3편 구조로 정리
3. RAN/Transport slicing 심화 자료 정리
4. 벤더별 구현 철학과 상용화 사례 분류표 정리
