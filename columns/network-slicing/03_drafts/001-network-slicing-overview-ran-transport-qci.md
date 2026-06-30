---
title: "네트워크 슬라이싱 첫 번째 이야기: QCI 기반 자원 배분과 무엇이 다른가"
series: "네트워크 슬라이싱의 실제"
episode: 1
status: draft
updated: 2026-06-26
target: "yulchive-astro 편입 전 초안"
postTemplate: articleFeature
---

# 네트워크 슬라이싱 첫 번째 이야기: QCI 기반 자원 배분과 무엇이 다른가

## 한 줄 메시지

네트워크 슬라이싱은 QCI나 5QI 기반 우선순위를 더 정교하게 주는 기능이 아니라, RAN, transport, core, policy, assurance를 하나의 서비스 단위로 묶어 운영하려는 모델이다.

## 도입: 네트워크 슬라이싱을 다시 봐야 하는 이유

통신망을 다뤄본 사람에게 "트래픽을 다르게 처리한다"는 말은 새롭지 않다. LTE에서는 QCI를 기준으로 bearer의 forwarding behavior를 구분했고, 장비 구현에 따라 QCI별 scheduling weight, GBR 처리, admission control, RB 또는 PRB 자원 배분 정책을 조정해 왔다. 5G에서도 5QI, QFI, QoS Flow, ARP, GBR 같은 용어가 등장하지만, 결국 현장에서 먼저 보이는 것은 "어떤 트래픽이 더 우선 처리되는가"라는 문제다.

그래서 네트워크 슬라이싱을 처음 시험하면 자연스럽게 이런 질문이 나온다.

> 지금 하고 있는 QCI별 RB 할당과 네트워크 슬라이싱은 무엇이 다른가?

이 질문은 중요하다. 슬라이싱을 단순히 "특정 QCI에 RB를 더 주는 기능"으로 이해하면, 실제 시험 결과를 해석할 때 계속 엇갈린다. 반대로 QCI/5QI 기반 자원 배분을 무시하고 슬라이싱을 완전히 별개의 가상망처럼만 설명해도 현장감이 떨어진다. 둘은 연결될 수 있지만 같은 것은 아니다.

이 글은 연재의 첫 번째 글로, 네트워크 슬라이싱을 전체 그림에서 다시 본다. 자세한 3GPP 절차와 메시지는 다음 글에서 다루고, 여기서는 RAN 슬라이싱, transport 슬라이싱, core/policy 연결, 그리고 QCI별 RB 할당과의 차이를 먼저 정리한다.

## 네트워크 슬라이싱의 핵심 개념

네트워크 슬라이싱은 특정 서비스, 고객, 업무, 단말 그룹에 맞는 논리적 네트워크를 만드는 개념이다. 3GPP 관점에서는 `S-NSSAI`와 `NSSAI`가 slice 식별과 선택의 중요한 언어가 되고, 관리 관점에서는 slice lifecycle, SLA/SLS, 성능 측정, fault, assurance가 함께 따라온다.

하지만 `S-NSSAI`가 붙었다고 해서 그 순간 완성된 slice가 생기는 것은 아니다. `S-NSSAI`는 "이 트래픽 또는 PDU Session이 어떤 slice와 관련되는가"를 표현하는 식별자에 가깝다. 실제 서비스 품질은 그 뒤에 붙는 여러 계층의 구현에 의해 결정된다.

- UE는 어떤 slice를 요청하거나 허용받는가
- 앱 트래픽은 어떤 URSP 정책을 통해 어떤 PDU Session으로 가는가
- Core는 어떤 AMF, SMF, UPF, PCF 정책을 선택하는가
- RAN은 slice별로 어떤 scheduler/RRM 정책을 적용하는가
- Transport는 slice별 경로, 대역폭, 지연, 격리를 어떻게 제공하는가
- OAM/Orchestration은 slice별 상태와 SLA를 어떻게 감시하고 수정하는가

따라서 네트워크 슬라이싱은 단일 기능이라기보다 multi-domain 운영 단위에 가깝다. RAN만 slice-aware여도 부족하고, core에 `S-NSSAI`가 보여도 transport가 동일 best-effort로 동작하면 end-to-end 보장은 약해진다.

## QCI별 RB 할당과 네트워크 슬라이싱의 차이

QCI 또는 5QI 기반 처리는 QoS 차등 처리의 핵심 수단이다. LTE의 QCI는 bearer 또는 service data flow가 기대하는 packet forwarding behavior를 가리키는 값으로 쓰였고, packet delay budget, packet error loss rate, priority 같은 QoS 특성과 연결된다. 5G에서는 5QI와 QoS Flow가 이 역할을 이어받는다.

현장에서 말하는 "QCI별 RB 할당"은 대체로 RAN scheduler 또는 RRM 정책의 영역이다. 예를 들어 특정 QCI에 더 높은 scheduling priority를 주거나, GBR bearer를 admission control로 보호하거나, 혼잡 상황에서 특정 traffic class의 PRB 사용 기회를 더 보장하는 방식이다. 이것은 매우 중요하다. 무선 구간이 병목이면 어떤 slice도 체감 품질을 보장하기 어렵기 때문이다.

다만 이것만으로 네트워크 슬라이싱이라고 부르기는 어렵다. 이유는 네 가지다.

첫째, QCI/5QI는 flow 또는 bearer 수준의 QoS 처리에 가깝다. 반면 slice는 가입자/서비스/고객 단위의 논리 네트워크와 lifecycle을 포함한다.

둘째, QCI별 RB 할당은 주로 RAN 내부 scheduler 정책으로 관찰된다. 반면 slicing은 RAN뿐 아니라 transport, core, policy, charging, assurance까지 이어져야 한다.

셋째, QCI/5QI는 같은 slice 안에서도 여러 개가 공존할 수 있다. 예를 들어 하나의 enterprise slice 안에 음성, 영상, 제어, 일반 데이터가 각각 다른 5QI로 흐를 수 있다.

넷째, slicing은 "누가 어떤 slice를 사용할 수 있는가"라는 선택과 권한의 문제를 포함한다. 이 지점에서 `S-NSSAI`, subscription, NSSF, PCF, URSP, NSSAA 같은 기능이 등장한다. QCI별 RB 할당만으로는 이런 slice 선택과 lifecycle 관리를 설명할 수 없다.

정리하면, QCI별 RB 할당은 RAN slice를 구현하는 하나의 도구가 될 수 있다. 그러나 QCI별 RB 할당 자체가 end-to-end network slicing은 아니다.

## RAN 슬라이싱: 무선 구간에서 실제로 나뉘는 것

RAN 슬라이싱은 슬라이싱에서 가장 눈에 잘 보이지만, 동시에 가장 어려운 영역이다. Core에서 slice가 선택되고 PDU Session이 만들어져도, UE가 실제로 체감하는 throughput, latency, jitter는 결국 air interface에서 크게 흔들린다.

RAN 슬라이싱에서 논의되는 구현 요소는 대략 다음과 같다.

- slice별 RRM policy
- scheduler priority 또는 weight
- PRB reservation 또는 PRB cap
- GBR/Non-GBR admission control
- slice-aware QoS Flow handling
- congestion 상황에서의 자원 보호
- slice별 RAN counter와 KPI
- O-RAN/RIC 기반 동적 제어

여기서 중요한 점은 RAN slicing이 항상 hard isolation을 의미하지 않는다는 것이다. 어떤 구현은 PRB를 정적으로 예약할 수 있고, 어떤 구현은 혼잡 시 우선순위를 높이는 방식일 수 있다. 또 어떤 구현은 최소 보장과 최대 제한을 함께 쓰고, 평상시에는 남는 자원을 공유하게 만들 수 있다.

즉 RAN slicing의 핵심은 "무선 자원을 완전히 쪼갠다"가 아니라, 특정 slice의 서비스 목표에 맞춰 RAN 자원 정책을 slice-aware하게 적용하고 측정할 수 있느냐에 있다.

## Transport 슬라이싱: RAN과 Core 사이를 잇는 보장 구조

Transport 슬라이싱은 종종 core나 RAN보다 덜 주목받지만, end-to-end slicing에서는 빠지면 안 되는 영역이다. RAN에서 특정 slice를 보호하고 core에서 별도 UPF나 policy를 적용해도, fronthaul, midhaul, backhaul, IP/MPLS 망이 모두 같은 best-effort 경로와 큐를 공유하면 서비스 보장은 쉽게 흐려진다.

Transport slicing의 목적은 slice별 트래픽이 전송망에서 필요한 대역폭, 지연, jitter, 가용성, 격리 수준을 얻도록 만드는 것이다. 구현 방식은 사업자망과 벤더에 따라 다를 수 있다.

- VLAN, VRF, QoS queue, traffic engineering
- MPLS 또는 SRv6 기반 경로 제어
- FlexE 기반 물리/논리 채널 격리
- TSN 또는 deterministic networking 계열의 시간 민감 트래픽 처리
- slice별 OAM, telemetry, SLA monitoring

여기서도 특정 기술 하나가 곧 transport slicing이라고 단정하면 안 된다. 중요한 것은 RAN과 Core 사이에서 slice intent가 전송망 정책으로 번역되고, 그 결과를 측정할 수 있느냐이다.

Huawei가 transport slicing과 deterministic networking을 강하게 강조하고, Ericsson/Nokia/Samsung이 RAN/Core/Transport/Orchestration을 함께 묶어 설명하는 이유도 여기에 있다. end-to-end slice는 weakest link의 영향을 받는다. Transport가 slice-aware하지 않으면, RAN slicing과 core slicing은 서로 따로 노는 설정처럼 보일 수 있다.

## Core 및 정책 제어와의 연결

Core 영역에서는 slice 선택과 session 구성이 중요하다. UE는 registration 과정에서 `Requested NSSAI`를 전달할 수 있고, 네트워크는 subscription과 policy를 바탕으로 `Allowed NSSAI`를 제공한다. 이후 PDU Session Establishment에서 `S-NSSAI`, DNN, SMF/UPF 선택, QoS Rule, 5QI, PCF 정책이 결합된다.

하지만 Core에서 `Allowed NSSAI`가 내려왔다고 해서 앱 트래픽이 자동으로 원하는 slice로 흘러가는 것은 아니다. 앱 또는 traffic descriptor가 어떤 PDU Session을 사용할지는 URSP와 단말 구현의 영향을 받는다. 이 때문에 consumer slicing이나 app-based slicing에서는 단말/OS/modem/SIM support가 실제 상용화의 병목이 될 수 있다.

Core slicing은 slice를 식별하고 선택하는 중심축이지만, 혼자서 체감 품질을 보장하지는 않는다. Core는 "어떤 slice로 보낼 것인가"를 결정하고, RAN과 Transport는 "그 slice를 실제 자원 위에서 어떻게 대우할 것인가"를 구현한다.

## 현장 관점: 슬라이싱이라고 부르기 전 확인할 질문

시험이나 벤더 설명을 볼 때는 "slice 지원"이라는 문장을 바로 받아들이기보다 아래 질문을 던지는 편이 좋다.

1. 이 기능은 `S-NSSAI` 기반 slice selection을 포함하는가?
2. UE subscription, NSSF, AMF/SMF/UPF, PCF 정책이 slice-aware하게 연결되는가?
3. RAN에서 slice별 scheduler/RRM 정책이 실제로 달라지는가?
4. Transport에서 slice별 경로, 큐, 대역폭, 지연 관리가 되는가?
5. 같은 slice 안에서 5QI/QoS Flow가 어떻게 매핑되는가?
6. 혼잡 상황에서 slice별 보호 또는 제한이 관찰되는가?
7. slice별 KPI, fault, SLA/SLS monitoring이 가능한가?
8. 이 기능은 lab demo, live-network trial, commercial service 중 어디에 해당하는가?

이 질문에 답하지 못하면, 그것은 network slicing이라기보다 slice-ready capability, QoS tuning, 또는 특정 domain의 부분 구현일 수 있다.

## 마무리: QoS의 확장이 아니라 운영 단위의 확장

네트워크 슬라이싱을 QCI별 RB 할당과 비교하는 것은 좋은 출발점이다. 실제 무선망에서 자원 배분을 어떻게 하느냐가 slice 품질을 좌우하기 때문이다. 그러나 거기서 멈추면 슬라이싱의 절반만 보게 된다.

QCI/5QI 기반 처리는 packet 또는 flow를 어떻게 대우할지 정하는 QoS 언어다. RAN slicing은 그 QoS와 slice intent를 무선 자원 정책으로 구현하는 영역이다. Transport slicing은 그 의도를 전송망 경로와 큐, 대역폭, 지연 관리로 이어주는 영역이다. Core와 policy는 어떤 단말과 앱이 어떤 slice를 사용할 수 있는지 선택하고 제어한다. Orchestration과 assurance는 이 모든 것을 서비스 lifecycle로 묶는다.

그래서 네트워크 슬라이싱은 "더 좋은 QCI"가 아니다. "예약된 RB"만도 아니다. 여러 domain이 같은 서비스 목표를 바라보도록 만드는 운영 모델이다. 그리고 실제 시험에서 가장 중요한 질문은 이것이다.

> 지금 내가 보고 있는 것은 QoS 차등 처리인가, RAN slice인가, 아니면 end-to-end slice인가?

이 질문을 분리해서 봐야 슬라이싱 시험 결과도, 벤더 구현 차이도, 상용화 발표도 제대로 읽을 수 있다.

## 참고자료

- 3GPP TS 23.501, System architecture for the 5G System: https://www.3gpp.org/DynaReport/23501.htm
- 3GPP TS 23.502, Procedures for the 5G System: https://www.3gpp.org/DynaReport/23502.htm
- 3GPP TS 23.503, Policy and charging control framework: https://www.3gpp.org/dynareport/23503.htm
- 3GPP TS 28.530, Management and orchestration of network slicing: https://www.3gpp.org/DynaReport/28530.htm
- ETSI TS 123 203, Policy and charging control architecture, QCI definition: https://www.etsi.org/deliver/etsi_ts/123200_123299/123203/15.03.00_60/ts_123203v150300p.pdf
- Ericsson RAN Slicing: https://www.ericsson.com/en/network-slicing/ran-slicing
- Nokia 4G/5G Network Slicing: https://www.nokia.com/mobile-networks/monetization/network-slicing/
- Samsung Network Slicing: https://www.samsung.com/global/business/networks/solutions/network-slicing/
- Huawei 5G Network Slicing Router: https://www.huawei.com/en/news/2017/2/industry-first-5g-network-slicing-router
