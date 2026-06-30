# QCI별 RB 할당과 네트워크 슬라이싱 비교 메모

## 핵심 구분

| 항목 | QCI/5QI 기반 RB 또는 PRB 자원 배분 | 네트워크 슬라이싱 |
|---|---|---|
| 주된 범위 | RAN scheduler/RRM/QoS 처리 | RAN, transport, core, policy, orchestration, assurance |
| 식별 단위 | bearer, QoS Flow, traffic class | slice, service, customer, tenant, S-NSSAI |
| 주요 목적 | packet forwarding behavior 차등 처리 | 특정 서비스 목표를 end-to-end 운영 단위로 제공 |
| 구현 예 | priority, weight, GBR, admission control, PRB reservation/cap | slice selection, per-slice RAN policy, transport path/QoS, UPF/SMF/PCF policy, lifecycle/assurance |
| 관계 | RAN slice 구현에 사용될 수 있는 수단 | QCI/5QI를 내부 QoS 도구로 사용할 수 있는 상위 운영 모델 |

## 칼럼에서 쓸 문장

QCI별 RB 할당은 "무선 자원을 어떻게 나눠 줄 것인가"에 대한 scheduler/RRM 관점의 답에 가깝다. 네트워크 슬라이싱은 "어떤 서비스 또는 고객에게 어떤 논리 네트워크 경험을 제공하고, 그 경험을 여러 domain에서 어떻게 유지할 것인가"에 대한 운영 관점의 답이다.

## 주의할 표현

- "QCI별 RB 할당은 slicing이 아니다"라고 단정하지 않는다.
- 더 안전한 표현: "QCI별 RB 할당은 RAN slice를 구현하는 수단이 될 수 있지만, 그것만으로 end-to-end network slicing은 아니다."
- RAN slicing이 곧 hard isolation이라고 쓰지 않는다.
- Transport slicing은 MPLS/SRv6/FlexE/TSN 중 하나로 고정하지 않는다.
