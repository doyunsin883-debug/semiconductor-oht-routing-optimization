# FAB FLOW | Semiconductor OHT Routing & Deadlock-Aware Optimization

### 반도체 FAB의 OHT 운행을 수리모형·강화학습·교착 위험 제어로 비교한 시뮬레이션 연구

> **Learners × YPICS Joint Logistics Seminar — Presentation Preparation (October 31, 2026, 14:00)**  
> 대학생 물류·SCM 학술교류를 위한 연구 발표 자료. **예정된 세미나의 준비 자료**이며, 발표 완료 또는 수상 실적을 의미하지 않습니다.  
> [Official seminar announcement / 공식 안내](https://www.instagram.com/p/De6u9tXj2_h/) · [Live Research Web / 연구 페이지](https://fabflow-oht-phase3-deadlock.vercel.app/) · [Conference Poster / 발표 포스터](docs/CONFERENCE_POSTER.md) · [Detailed Methodology / 연구 해설](docs/TECHNICAL_EXPLANATION.md) · [English README](README_EN.md)

![Research diagram: directed semiconductor OHT rail network](assets/figures/05_directed_network.svg)

<sub>**Figure 1.** 제가 연구에 사용한 48-node / 82-directed-link 가상 레일 네트워크. 실제 반도체 공장 내부도면이나 삼성전자 제공 데이터가 아닙니다.</sub>

## Repository publication / 공개 현황

> **GitHub publication note (2026-10-26).** This GitHub version currently includes bilingual research text, seminar notes, synthetic benchmark mean results, paired inference and SVG scientific figures. The original full simulator source files, detailed per-run datasets and binary A2/12-page PDF downloads are not yet uploaded through this connection. The full prepared 39-file source/PDF archive remains separately available as a downloadable project artifact in the corresponding ChatGPT conversation. Do not treat this GitHub checkout alone as an end-to-end reproduction of all 960 simulations.
>
> 공개 사이트의 3D 운행 화면은 설명용 SVG 개념 시각화이며 실제 FAB 데이터와 연동한 디지털트윈이 아닙니다.

[Conference poster and research figures](docs/CONFERENCE_POSTER.md) · [Detailed technical explanation](docs/TECHNICAL_EXPLANATION.md) · [Experiment summary CSV](results/summary_600.csv) · [Paired inference CSV](results/paired_inference.csv)

## Research at a glance / 연구 개요

반도체 제조공장(FAB)의 물류를 공부하면서 가장 궁금했던 건 단순했습니다. **차량 한 대가 가장 짧은 길로 가는 것과, 여러 차량이 동시에 잘 움직이는 것은 왜 다를까?**

FAB에서는 웨이퍼가 여러 공정을 오가고, 천장 레일을 따라 움직이는 OHT(Overhead Hoist Transport)가 FOUP(Front Opening Unified Pod)을 운반합니다. 개별 OHT가 항상 가장 짧은 이동경로를 선택하더라도, 여러 차량이 같은 교차로에 집중되면 운송 작업 전체는 오히려 지연될 수 있습니다. 이 문제를 산업공학의 **경영과학(Operations Research), 생산운영관리, 네트워크 최적화, 이산적 시간 기반 시뮬레이션**으로 이해해 보고 싶었습니다.

그래서 가상의 FAB 네트워크를 직접 모델링하고, 배차와 경로 선택 및 레일 점유를 프로그램으로 구현했습니다. 이후 알고리즘을 추가해 보는 데 그치지 않고, **왜 결과가 달라졌는지**까지 확인하려고 기준 정책, 학습 전/후 대조실험, 통계검정을 함께 구성했습니다.

**English overview.** I modelled a synthetic semiconductor FAB transport network and compared full-route locking, next-segment reservations, congestion-aware routing, and tabular Q-learning. The objective was to understand whether differences in completed transport jobs are driven by routing intelligence or by the underlying resource-control mechanism. The study includes 600 matched-seed evaluation runs, 360 safety-sensitivity runs, an interactive explanatory interface, and a bilingual research report.

> **Scope note.** FAB FLOW is a **simulation-based research prototype** using synthetic network and demand data. It is **not** a sensor-synchronized digital twin of any operating factory, not affiliated with Samsung Electronics, and not industrial safety certified. The 3D-style web animation is a schematic visualization, **not a frame-by-frame replay of all evaluation runs**.

---

## 01 | 문제의식: 왜 '최단경로'만으로는 부족할까?

물류 업무를 택배나 트럭의 배송 경로 문제로만 생각하면 '최단거리'가 곧 '좋은 경로'처럼 보일 수 있습니다. 하지만 반도체 FAB는 조금 다릅니다. 장비 사이의 운반로를 다수의 OHT가 공유하고, 실제 출입 가능한 구간과 차량 점유 제약이 있으며, 목적지에 도착한 차량을 언제 하역할지도 중요합니다.

예를 들어 두 OHT가 동시에 같은 교차로에 진입하려고 하면, 한 차량은 대기해야 합니다. 한쪽이 출발 전에 지나갈 경로 전체를 예약하는 설계라면, 아직 수분 뒤에 사용할 구간까지 다른 차량이 쓰지 못할 수 있습니다. 안전을 위해 예약을 지나치게 보수적으로 만들면 운송 처리량이 낮아질 수 있다는 뜻입니다.

이번 연구에서 확인하고 싶었던 질문은 다음 세 가지였습니다.

1. **Reservation policy:** 전체 경로를 사전에 예약하는 방식보다 다음 구간만 예약하는 방식이 가상 FAB의 운송 처리량을 개선하는가?
2. **Deadlock control:** 부분 예약에서 생길 수 있는 순환대기 위험을 Wait-for Graph 기반 판단으로 줄일 수 있는가?
3. **Reinforcement learning:** Q-learning의 정책 구조 때문이 아니라 **학습 자체로 추가 개선**이 발생하는 조건이 있는가?

### 일상적인 비유로 설명하면

- **Full-route reservation:** 복도 끝까지 걸어갈 사람 한 명이 복도 전체를 자기 차례가 끝날 때까지 예약하는 방식.
- **Partial reservation:** 다음 문 앞 공간이 비어 있는지 확인하고, 지나간 공간은 뒤 사람에게 돌려주는 방식.
- **Wait-for Graph:** A가 B를 기다리고, B가 C를 기다리고, C가 A를 기다리는 관계가 생겼는지를 검사하는 방식.
- **Q-learning:** 지금 상황에서 어느 선택이 결과적으로 덜 기다리는지 반복 경험하면서 평가값을 조정하는 방식.

---

## 02 | System Architecture / 시스템 설계

![Pipeline of synthetic FAB research, from graph to paired inference](assets/figures/04_system_pipeline.svg)

실제 연구 흐름을 한 방향으로 고정했습니다. **FAB 네트워크 생성 → 운송 요청 → 배차와 경로 선택 → 자원 점유/반환 → 시간에 따른 상태 변화 → 평가 데이터 저장 → 통계 분석** 순서입니다.

| 구성요소 / Component | 구현 / Implementation | 산업공학적 의미 |
|---|---|---|
| FAB network | 6×8 directed graph, 48 nodes / 82 links | 네트워크 모델링, 대체 경로, 교차로 구조 |
| FOUP requests | Synthetic Poisson arrivals | 운송 수요 발생과 대기행렬적 관점 |
| Fleet | 9 OHTs (base evaluation) | 다차량의 동시 자원 사용 |
| Dispatch | Idle-vehicle assignment | 운송 작업 및 차량 할당 |
| Routing | Dijkstra, dynamic path selection, Q-learning | 경로탐색과 상태기반 의사결정 |
| Resource control | Full-route atomic vs next-segment reservation | 공유 레일 자원 관리 |
| Cycle guard | Wait-for dependencies and short-loop lookahead | 교착 위험 신호 탐지 및 진입 회피 |
| Benchmarking | Matched random seeds, bootstrap CIs, Holm correction | 공정한 비교와 불확실성 정량화 |
| Frontend | HTML/CSS/JavaScript/SVG | 이해를 돕는 입체형 FAB 시각화 |

### 모델 범위 / Assumptions

- 48개 노드와 82개 단방향 링크로 구성한 **합성 방향성 네트워크**를 사용했습니다.
- 기본 평가는 OHT 9대, 관찰시간 1,500초(25분), 기본 요청률 68건/시간으로 구성했습니다.
- 수요 급증 시나리오는 운송 요청률을 1.5배로 조정했고, 차단 시나리오는 특정 링크를 통행 불가로 변경했습니다.
- 센서 통신이나 PLC와 실시간 연결하지 않았으며, 이동/정차/공정 반입·하역을 단순화했습니다.
- **SimPy, PPO, Stable-Baselines3를 실제 Phase 3 평가 코드에서 사용했다고 주장하지 않습니다.** Phase 3은 직접 작성한 시간 단계형 시뮬레이터와 **tabular Q-learning** 기반입니다.

---

## 03 | 경로탐색과 레일 예약 / Routing & Locking

### A. Dijkstra's shortest path

기본 알고리즘은 현재 출발지와 목적지를 연결하는 비용 최소 경로를 찾습니다. 링크의 길이나 이동에 필요한 시간을 비용으로 두면 해당 차량 입장에서는 효율적인 선택이 됩니다. 하지만 다른 차량이 이미 점유한 구간을 충분히 반영하지 않으면 합리적인 개별 선택이 전체 혼잡을 키울 수 있습니다.

### B. Congestion-aware routing

차량이 진입할 수 있는 후보 경로를 구성할 때 다음 구간의 점유와 예약 상태를 확인합니다. 이동 경로는 물리적으로 가능한 링크에서만 선택하며, 같은 노드에 다른 차량이 중복 예약하지 못하도록 제약을 적용했습니다.

### C. Full-route atomic reservation

출발 전에 목적지까지의 경로 전체를 확보합니다. 한 번 확보한 자원을 기다리면서 추가로 확보하지 않아도 되기 때문에 특정 자원교착 형태를 억제할 수 있습니다. 대신 다른 차량이 사용할 수 있는 레일을 넓게 잠그는 문제가 발생합니다.

### D. Partial next-segment reservation

차량이 당장 진입해야 할 **다음 레일/노드**가 비어 있는지 확인한 뒤 이동을 허용합니다. 목적지 진입이 완료되면 이전 구간의 점유를 해제합니다. 모든 차량이 동시에 움직일 수 있는 기회를 넓히지만, 잘못 구현하면 교착이나 중복 점유 문제가 발생할 수 있으므로 별도 제어가 필요합니다.

### E. Wait-for Graph / 교착 위험 신호

차량 `i`가 차량 `j`가 점유 중인 자원 때문에 이동하지 못한다면 대기 그래프에 `i → j`라는 간선을 추가합니다. 이러한 대기 관계가 순환될 경우 교착 위험을 의심할 수 있습니다. 구현에서는 다음 구간 예약 시 노드/링크 점유를 검증하고, 일부 짧은 방향성 폐회로가 모두 점유되는 것을 사전에 막으며, 대기 그래프의 순환 관계를 모니터링했습니다.

```text
Grant(i, u, v)
    = Free(destination node v)
    AND Free(directed edge u → v)
    AND NOT predicted short-loop / wait-for cycle risk
```

실험 로그에서 노드 중복 점유 위반이 0건이라는 사실은 **코드에 정의된 점유 불변식을 통과했다**는 뜻입니다. 실제 산업 현장 모든 조건에서 물리적 충돌이나 교착이 발생하지 않는다는 인증을 받은 것은 아닙니다.

---

## 04 | Reinforcement Learning: 어떻게 학습시켰는가?

### 강화학습을 적용한 이유

혼잡 환경에서는 출발지와 목적지뿐 아니라 주변 차량의 점유 상태, 대기 상황, 새로운 운송 수요가 계속 바뀝니다. 따라서 상황에 따라 경로 선택을 달리하는 정책을 시험해 보고 싶었습니다.

이번 연구에서는 **Q-learning**으로 특정 상태에서 다음 이동을 선택했을 때의 평가값을 누적하도록 했습니다. CNN이나 LLM이 차량을 직접 조종하는 방식이 아닙니다.

```text
Q(s,a) ← Q(s,a) + α · [r + γ max_a' Q(s',a') − Q(s,a)]

s  : current node / destination zone / scenario / activity level
 a : feasible next-node choice
 r : negative travel time for the completed segment
 α : learning rate = 0.22
 γ : discount factor = 0.87
```

**State / 상태.** 현재 노드 번호, 목적지의 구역 정보, 정상·수요 증가·차단 여부, 동시에 활동 중인 차량 수를 구간화한 정보를 반영합니다. 차량이 바라보는 주변 상황을 숫자로 요약한 것입니다.

**Action / 행동.** 단방향 링크를 따라 연결되고 예약 제약을 충족하는 후보 경로 중 다음 이동을 선택합니다. 정책은 최단 이동시간을 기본적으로 선호하며 학습한 Q값을 보조 신호로 사용합니다.

**Reward / 보상.** Phase 3 실제 구현에서는 다음 이동 구간을 완료했을 때 소요된 이동시간의 음수(`-travel_seconds`)를 보상으로 사용합니다. 시간이 오래 걸릴수록 낮은 보상을 받는 구조입니다.

**Exploration / 탐색.** 학습 중에는 확률 0.20으로 가능한 후보 가운데 탐색하고, 나머지는 현재 정책의 선택을 사용합니다. 평가 단계에서는 학습을 중단하고 고정된 Q값으로 비교합니다.

**Action shield / 안전한 탐색 범위.** 학습 정책이 지나치게 먼 우회로를 선택하는 현상을 관찰했기 때문에, 가장 짧은 실행 가능 후보보다 경로비용이 30%를 초과하는 후보는 제거했습니다. 학습 Q값의 가중치에도 제한을 두었습니다. 따라서 본 실험의 Q-learning은 순수 RL 단독 제어가 아니라 **휴리스틱+학습 보정+행동 제한의 결합 정책**입니다.

### 학습 전과 후를 왜 따로 비교했나?

새로운 AI 정책이 기존 Dijkstra보다 높은 수치를 보였다고 해서 그 차이를 모두 '학습 효과'로 부르면 정확하지 않습니다. 후보 경로, 안전 차폐, 자원 예약 방식이 함께 달라졌을 수 있기 때문입니다. 이 문제를 피하기 위해, 같은 정책 구조에서 **학습한 Q값을 넣은 버전과 넣지 않은 버전**을 독립적으로 비교했습니다.

**Training** 120 episodes, 18,447 Q updates, 3,358 state-action entries. **Held-out evaluation** uses seeds 40001–40040, separated from training seeds 1500–1619.

---

## 05 | Experimental Design / 비교실험 조건

| 항목 | 설계 |
|---|---|
| Main evaluation | 3 scenarios × 5 routing/control policies × 40 matched seeds = **600 runs** |
| Guard sensitivity | 3 scenarios × 3 fleet sizes (6/9/12) × 2 guard states × 20 seeds = **360 runs** |
| Total | **960 synthetic evaluations** |
| Time horizon | 1,500 s (=25 min) per main run |
| Controlled randomness | 공통 난수 시드로 같은 요청 패턴을 다른 정책에 입력 |
| Primary outcome | 관찰시간 내 완료된 운송 작업 수 |
| Secondary outcomes | 미완료, 대기시간, 노드 점유 위반, WFG cycle signals |
| Inference | Seed-paired bootstrap 95% confidence intervals / sign tests / Holm adjustment |

완료 작업만의 평균 리드타임은 분석할 때 조심해야 합니다. 관찰시간 안에 완료하지 못한 요청은 평균에 포함되지 않으므로, 처리량이 낮은 정책이 상대적으로 '빨리 끝난 작업만' 평균에 남기는 **선택 편향**이 생길 수 있기 때문입니다. 따라서 처리량과 미완료 작업을 먼저 보고, 리드타임은 보조적으로 해석했습니다.

---

## 06 | Results: Full-route vs Partial Reservations

![Policy comparison from 600 simulation runs](assets/figures/01_policy_comparison.svg)

<sub>**Figure 2.** 각 시나리오에서 40개 matched evaluation seeds의 평균 완료 작업 수. 이 그래프는 `results/summary_600.csv`를 다시 시각화했습니다.</sub>

| Scenario | Full-route atomic | Partial shortest | Partial dynamic | Untrained Q | Trained Q |
|:--|--:|--:|--:|--:|--:|
| Normal / 정상 | 18.925 | 24.600 | 24.450 | 24.450 | 24.300 |
| Demand surge / 수요 급증 | 20.900 | 36.150 | 34.325 | 34.325 | 34.900 |
| Rail closure / 링크 차단 | 18.600 | 24.550 | 24.475 | 24.475 | 24.500 |

### 결과를 어떻게 해석했는가?

**부분 예약(혼잡 대응) − 전체 예약** 기준으로 정상 +5.525건, 수요 급증 +13.425건, 링크 차단 +5.875건을 더 완료했습니다. 전체 예약을 기준으로 각각 약 **29.2%, 64.2%, 31.6%**의 상대적인 증가입니다. 모든 시나리오에서 두 정책의 완료 작업 수 차이에 대한 95% 대응 신뢰구간은 0을 제외했습니다.

이 결과는 'AI를 쓰면 64% 좋아진다'는 뜻이 아닙니다. **기준 모델은 출발 전에 경로 전체를 묶어두는 방식이고, 비교 모델은 다음 구간만 예약하기 때문에 기본 자원 운영 구조부터 다릅니다.** 또한 실험이 합성 네트워크에서 이루어졌으므로 실제 공장 처리량의 증가율로 해석하면 안 됩니다.

한 가지 흥미로운 점은 **수요 급증 환경에서 부분예약 최단경로(36.15건)가 부분예약 혼잡 대응(34.325건)보다 높았다**는 사실입니다. 복잡한 알고리즘이 언제나 높은 처리량을 보장하지 않는다는 점도 이번 연구에서 그대로 확인할 수 있습니다.

---

## 07 | Q-learning: Did learning itself help?

![Matched-seed bootstrap effects and confidence intervals](assets/figures/02_paired_effects.svg)

<sub>**Figure 3.** 95% seed-paired bootstrap confidence intervals. 좌측은 자원 예약 제어 구조 차이, 우측은 Q 학습 전후 차이.</sub>

| Scenario | Trained − Untrained Q | Bootstrap 95% CI | Holm-adjusted p (sign test) |
|---|---:|---:|---:|
| Normal | −0.150 jobs | [−0.350, +0.025] | 0.9053 |
| Demand surge | **+0.575 jobs** | **[+0.200, +1.000]** | **0.0369** |
| Rail closure | +0.025 jobs | [−0.050, +0.125] | 1.0000 |

결론은 생각보다 단순하지 않았습니다. 정상과 차단 조건에서는 학습한 Q 정책의 추가 개선을 통계적으로 확인하지 못했습니다. 수요 급증 조건에서는 평균 **+0.575건**의 작지만 양의 효과를 얻었습니다. 이것 역시 특정 합성 네트워크와 학습 조건에서만 확인된 결과입니다.

제가 이 결과에서 중요하게 본 것은 높은 숫자를 만드는 것보다 **정책이 왜 좋아졌는지를 분리해서 설명할 수 있어야 한다**는 점입니다.

---

## 08 | Guard Ablation: Wait-for Graph가 줄인 것은?

![Wait-for cycle detection before and after guard](assets/figures/03_cycle_guard_ablation.svg)

<sub>**Figure 4.** 12대, 수요 급증 환경의 평균 순환대기 신호. `results/guard_ablation_360.csv` 기반.</sub>

OHT 12대와 수요 급증을 조합한 환경에서 보호장치를 적용하지 않으면 WFG 순환대기 위험 신호가 평균 **9.45초/회**, 보호장치를 적용한 모델에서는 **0초/회** 기록됐습니다.

하지만 이 결과를 '실제 교착이 9.45초 발생했다'고 소개하지는 않습니다. 프로그램에서 관찰한 것은 **잠재적인 방향성 대기 사이클 신호**이지, 산업 현장에서의 영구 교착을 인증된 방식으로 측정한 결과가 아니기 때문입니다. 일부 조건에서는 보호장치가 처리량을 제한하는 trade-off도 있었습니다.

---

## 09 | Interface / 구현 화면

**[Open the live research website](https://fabflow-oht-phase3-deadlock.vercel.app/)**

[Earlier FAB FLOW 3D presentation interface (v2), not the Phase 3 trace](https://fabflow-oht-phase3-deadlock.vercel.app/)

<sub>**Interface reference.** FAB FLOW의 초기 3D 프런트엔드 화면. 본 연구의 **Phase 3 Python 로그를 그대로 재생한 이미지가 아니라**, 가상 FAB/차량/정책 비교를 설명하기 위한 **이전 UI 단계 스크린샷**입니다. 현재 Phase 3 결과 확인은 위의 공식 배포 링크를 사용하세요.</sub>

- 외부인이 복잡한 코드를 설치하지 않아도 FAB, 레일, 차량, 혼잡과 우회라는 개념을 파악할 수 있도록 인터페이스를 구성했습니다.
- Python 실험에서 도출한 수치와 순수 설명용 애니메이션은 명확하게 구분했습니다.
- 발표 자료를 봤을 때 '물류 운송 알고리즘의 개선'과 '화면이 움직이는 효과'가 혼동되지 않도록 노력했습니다.

---

## 10 | Technologies & Implementation Details

| Technology | 실제 역할 | 이번 연구에서 하지 않은 것 |
|---|---|---|
| Python | 시뮬레이터, 차량 상태 및 수리실험 전체 실행 | 실제 설비 PLC 제어 |
| NetworkX | 방향성 그래프, 단방향 후보 경로, 사이클 분석 | 실제 FAB CAD 기반 물류 지도 |
| NumPy | Poisson 요청 생성, 수치 연산 | 실제 제조사 수요 데이터 학습 |
| pandas | 600+360 runs 집계, 정책별 결과 비교 | 실시간 MES 스트리밍 |
| SciPy | 통계 검정 및 표본 기반 계산 | 산업용 제어 안정성 검증 |
| Matplotlib | 공개 그래프 및 학회용 Figure 출력 | 그래프를 근거 없이 생성하지 않음 |
| ReportLab | 편집 가능한 코드 기반 PDF 산출 | CAD 기반 물리 시뮬레이션 |
| HTML / CSS / JS / SVG | 반응형 웹, 개념 애니메이션, 정보 전달 | 실제 3D CAD 및 동기화 digital twin |
| pytest | 방향성 링크, 점유 불변식, cycle guard 등의 자동 검사 | 인증기관의 설비 안전성 시험 |

### 무엇이 실제 코드로 구현됐는가?

- `src/phase2_reference.py` : 전체 경로 예약 기준 시뮬레이터.
- `src/phase3.py` : 부분 예약, WFG 순환대기 감지, QPolicy, 학습 갱신, 차량 배차/운송/하역, 로그 및 평가.
- `run_phase3.py` : 학습, 600회 held-out evaluation, paired inference, CSV/그래프/Q table 기록.
- `run_ablation.py` : 차량대수와 보호장치를 변화시킨 360회 민감도 실험.
- `tests/test_phase3.py` : 연결·점유·제어 논리의 자동 검증.
- `docs/FABFLOW_Conference_Poster_A2.pdf` : 포스터형 연구 요약.
- `docs/FABFLOW_Research_Editorial_Report_KO_EN.pdf` : 연구 동기, 모델, 통계, 한계가 포함된 12페이지 국영문 연구 자료.

### 재현 방법 / Run it yourself

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate

python -m pip install -r requirements.txt
python -m pytest tests/ -q
python run_phase3.py
python run_ablation.py
```

원본 `results/` 폴더에는 분석에 사용한 자료를 보관했습니다. `run_phase3.py`를 재실행하면 학습과 600회 평가가 다시 수행되며 결과 CSV와 수치 도표가 갱신됩니다. 다만 난수, 실행 라이브러리 버전과 플랫폼 차이를 통제할 필요가 있습니다.

---

## 11 | Academic Exchange / Learners × YPICS

이번 연구는 **물류를 단순한 운송 경로 문제가 아니라 생산설비와 연결된 시스템 운영 문제로 설명하고 싶다**는 생각에서 출발했습니다. 이런 관점은 반도체뿐 아니라 자동창고, 스마트물류센터, 공장 내 AGV·AMR 운영에서도 중요하다고 봅니다.

공식 인스타그램 공지에 따르면 **Learners × YPICS(와이픽스) 학술교류는 2026년 10월 31일 토요일 오후 2시 예정**입니다. 이 프로젝트를 바탕으로 **세미나 발표를 준비**하면서, 비전공자도 이해할 수 있도록 OHT, FOUP, 병목, 예약, 교착 방지, 강화학습을 하나씩 설명하는 구성을 만들었습니다.

> **Seminar context (planned):** Learners × YPICS Joint Logistics/SCM Academic Exchange — *research presentation preparation*  
> **Official organizer announcement:** [Instagram / YPICS × Learners](https://www.instagram.com/p/De6u9tXj2_h/)  

제가 발표에서 가장 전달하고 싶은 문장은 다음과 같습니다.

> 여러 차량이 함께 움직이는 시스템에서는 한 차량의 최단경로보다, **공유 자원을 언제 누구에게 허용하는지**가 전체 운영 성능을 더 크게 바꿀 수 있습니다. 그리고 AI의 효과는 정책 구조의 효과와 분리해 검증해야 합니다.

---

## 12 | Limitations & Next Steps / 연구 한계와 개선 방향

1. **Synthetic geometry** — 실제 반도체 FAB의 내부 레일/스위치 구조를 그대로 재현하지 않았습니다.
2. **Control simplification** — 1초 시간 단계, 노드 점유, 측선 동작 등은 모델링을 위한 추상화입니다. 실제 가감속, 제동거리, 스위칭 지연을 충분히 검증하지 않았습니다.
3. **No plant integration** — PLC/MES/FOUP 센서 정보와 연결하지 않았으므로 엄밀한 의미의 실시간 현장 디지털트윈은 아닙니다.
4. **Deadlock guarantee** — WFG 관련 위험 신호 감소를 확인했으나 모든 운영 조건의 교착 방지 증명은 아닙니다.
5. **RL limitations** — 120 에피소드 기반 tabular Q-learning 한 가지에 대한 실험 결과입니다. 정책 전체의 우월성이나 다른 강화학습 알고리즘 성능을 일반화할 수 없습니다.
6. **Evaluation generalization** — 네트워크 구조, 수요율, 차량 수, 보상 설계, 예약 정책을 넓혀 추가 실험이 필요합니다.
7. **Censoring & significance** — 완료 작업만의 운송시간 평균에는 우측 검열 문제가 있고, 우연 개선을 통제하기 위해 미리 정의한 비교 및 Holm 보정을 사용했습니다.

**Next steps.** 방향성 레일 구조 다양화 → 교차로별 실제 스위칭 제약 → 운송 작업과 장비 가동상태 통합 → 안전 제약을 만족하는 강건한 정책 학습 → 다중 FAB 구조에서의 외적 검증 순서로 확장할 계획입니다.

## Research files / 자료 보기

| Resource | Link |
|---|---|
| Live research website | [Open FAB FLOW](https://fabflow-oht-phase3-deadlock.vercel.app/) |
| A2 conference-style poster | [PDF](docs/CONFERENCE_POSTER.md) |
| 12-page bilingual research dossier | [PDF](docs/TECHNICAL_EXPLANATION.md) |
| English research overview | [README_EN.md](README_EN.md) |
| Simulation assumptions & reproducibility | [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) |
| Raw results | [`results/`](results/) |
| Actual source code | [`src/`](src/) |
| Seminar announcement | [Learners × YPICS Instagram](https://www.instagram.com/p/De6u9tXj2_h/) |

---

**Project type:** Independent research prototype / 산업공학 개인연구  
**Domain:** Semiconductor FAB logistics · AMHS · OHT · OR · Reinforcement Learning · Deadlock Awareness  
**Status:** Synthetic simulation verified at code level, publication-grade external validation pending.  
**Ownership / provenance:** 연구 내용의 재현 가능성을 위해 원본 코드와 synthetic CSV를 제공하며, 연구 기획·코드 작성·문서 정리 과정에서 AI 보조 도구를 사용했습니다. 실제 산업 데이터나 장비 접근 없이 생성된 결과를 현장 실측처럼 표현하지 않습니다.