# FAB FLOW — Semiconductor OHT Routing & Resource-Control Research

**A synthetic semiconductor FAB simulation study on deadlock-aware segment reservation, network optimization, and tabular reinforcement learning.**

**Context:** [Learners × YPICS Joint Logistics/SCM Academic Exchange — October 31, 2026, 14:00 (scheduled)](https://www.instagram.com/p/De6u9tXj2_h/) · Presentation material in preparation, not a claim of a completed conference presentation.

**Resources:** [Live research web](https://fabflow-oht-phase3-deadlock.vercel.app/) · [A2 research poster](docs/FABFLOW_Conference_Poster_A2.pdf) · [12-page bilingual report](docs/FABFLOW_GitHub_Research_Brief_KO_EN.pdf) · [Korean README](README.md) · [Reproducibility notes](docs/REPRODUCIBILITY.md)

![Directed 48-node network](assets/figures/05_directed_network.svg)

## 1. The question that started the project

A semiconductor fabrication facility is not just a collection of fast processing machines. Wafers must repeatedly move among manufacturing steps, and automated material handling is essential to maintaining their operational sequence. I was interested in a deceptively simple question: **does selecting the shortest route for every vehicle necessarily maximize the amount of material transported by the entire system?**

I designed FAB FLOW as a controlled, reproducible study rather than a depiction of a real Samsung fabrication plant. The prototype provides a directed rail network, simulated FOUP transport requests, nine vehicles, resource conflicts, path-search policies, a cycle-risk guard, and an experimental evaluation protocol.

The core distinction is between **route choice** and **resource-control architecture**. Good shortest-path estimates can still coexist with poor throughput if a vehicle reserves an excessively large part of the network before traveling.

## 2. What is OHT, AMHS, and FOUP?

- **OHT (Overhead Hoist Transport):** a ceiling-mounted vehicle transporting a wafer container along a rail network.
- **FOUP (Front Opening Unified Pod):** an enclosed container holding wafers during transport and storage.
- **AMHS (Automated Material Handling System):** the broader set of equipment, tracking, and control functions that coordinate material movement among processes.
- **Deadlock:** a situation where mutually dependent resource waits prevent progress. A detected *wait-for cycle* is a warning signal, but it must not automatically be equated with a confirmed permanent deadlock.

## 3. Model assumptions

The Phase 3 model contains a 6×8 **synthetic directional network** with 48 nodes and 82 directed links. The benchmark horizon is 1,500 seconds, the initial fleet comprises nine OHTs, and transport requests follow a synthetic Poisson process at a baseline rate of 68 jobs per hour. Each algorithm is evaluated under normal operation, a 1.5× demand surge, and a blocked central rail link.

A one-second scheduling clock models vehicle movements, reservations, pick-up service, and drop-off service. Node ownership, edge ownership, and target reservations are checked before grants. This is an operational abstraction, not a calibrated electromechanical system.

## 4. Five policy variants

1. **Full-route atomic reservation + dynamic routing:** reserve the entire intended route before departure. This reference is conservative and reduces certain forms of waiting while holding a large portion of the network.
2. **Partial segment reservation + shortest-path routing:** only the immediately needed segment is reserved, while path choice favors the shortest remaining travel time.
3. **Partial segment reservation + congestion-aware routing:** select a feasible path using candidate costs and occupancy constraints.
4. **Partial segment reservation + untrained Q policy:** preserve the same policy structure as the trained agent but without learning-based Q values.
5. **Partial segment reservation + trained Q policy:** introduce values learned through 120 Q-learning training episodes. Feasible actions are restricted by the same protection logic and a route detour shield.

### Why compare trained and untrained Q separately?

A different policy may be more effective because of its candidate routes, its safety constraints, or its reservation architecture even if the agent has not learned a useful strategy. Therefore, the study treats the trained-versus-untrained contrast as the most direct check of the **incremental effect of learning**.

## 5. Q-learning: the actual implementation

The tabular update rule is:

```text
Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') − Q(s,a)]
```

The simulator uses a learning rate of **0.22** and a discount factor of **0.87**. State encoding includes the current node, discretized target zone, scenario, and coarse active-vehicle density. An action corresponds to a feasible next-node choice from candidate routes. The segment reward is the **negative time spent traveling the chosen segment**. Exploration is used during training with probability **0.20**.

A safety/action shield limits considered detours to **130% of the shortest feasible route cost**, with a bounded Q contribution to prevent extreme routing decisions. The reported method is consequently **tabular Q-learning as a residual component of a constrained routing heuristic**. It is not PPO, deep reinforcement learning, multi-agent PPO, or agentic LLM control.

Training comprises **120 episodes, 18,447 Q-value updates, and 3,358 state-action entries**. The held-out evaluation seeds are separated from the training seed range.

## 6. Deadlock risk protection

The model tracks which vehicles own track nodes or reservations. When a vehicle cannot move because another vehicle holds the required resource, a vehicle-to-vehicle wait dependency is recorded. A Wait-for Graph summarizes these dependencies; cycle detection identifies potential circular waiting.

A **local admission guard** rejects certain moves predicted to saturate a short directed loop. It maintains an occupancy invariant and prevents unsafe grants in the simulated model. This does not constitute proof of freedom from every possible industrial deadlock configuration.

## 7. Experimental protocol

- **600 main runs:** 3 scenarios × 5 policies × 40 *paired* evaluation seeds.
- **360 guard sensitivity runs:** 3 scenarios × 3 fleet sizes (6, 9, 12) × guard on/off × 20 seeds.
- **960 synthetic runs overall.**
- **Primary measure:** transport jobs completed within the fixed 25-minute horizon.
- **Additional measures:** unfinished requests, waiting/denied events, detected wait cycles, node reservation invariant violations, and lead times of completed jobs.
- **Uncertainty:** paired-seed bootstrap confidence intervals, two-sided sign tests, and Holm correction across nine preselected contrasts.

The same seed controls request generation across policies. Comparing the resulting within-seed differences reduces between-run demand variability. Mean travel time among *completed* jobs can be biased when different policies complete different subsets of requests; throughput is therefore emphasized.

## 8. Results

![Mean completed jobs across 3 scenarios and 5 policies](assets/figures/01_policy_comparison.svg)

| Scenario | Full route | Partial shortest | Partial dynamic | Untrained Q | Trained Q |
|---|---:|---:|---:|---:|---:|
| Normal | 18.925 | 24.600 | 24.450 | 24.450 | 24.300 |
| Demand surge | 20.900 | 36.150 | 34.325 | 34.325 | 34.900 |
| Link closure | 18.600 | 24.550 | 24.475 | 24.475 | 24.500 |

The partial-reservation dynamic policy improved mean completed jobs over the full-route reference by **+5.525** (normal), **+13.425** (demand surge), and **+5.875** (closure). All three paired 95% confidence intervals excluded zero. These are **simulated policy differences**, not measured improvements at an operating semiconductor fab. Since the comparison changes the resource-control architecture, the entire difference cannot be attributed to routing intelligence alone.

![Paired bootstrap effects](assets/figures/02_paired_effects.svg)

The incremental effect of trained versus untrained Q-learning was **−0.150** jobs in normal operation, **+0.575** during a demand surge, and **+0.025** with a rail closure. Only demand surge produced a confidence interval excluding zero **[+0.200,+1.000]**, with a Holm-adjusted sign-test p value of **0.0369**.

An important counterexample is that the **partial shortest-path policy performed better than partial congestion-aware routing during demand surge** in this test. More complicated algorithms do not automatically dominate well-designed simpler references.

## 9. Wait-for Graph ablation

![Potential wait-for cycle signal changes](assets/figures/03_cycle_guard_ablation.svg)

In a 12-vehicle demand-surge condition, potential wait-cycle signal accumulation dropped from a mean of **9.45 seconds per run** with the guard disabled to **0 seconds** with the guard enabled. The metric is a model-defined risk signal; it is not a count of permanent physical deadlocks. In some conditions a guard can also reduce throughput by withholding otherwise feasible moves.

## 10. Demonstration and source provenance

**[Live interactive research web](https://fabflow-oht-phase3-deadlock.vercel.app/)**

[Early research interface concept — live web visualization](https://fabflow-oht-phase3-deadlock.vercel.app/)

*The screenshot above illustrates an earlier FAB FLOW interface version, not the exact Phase 3 evaluation replay. The deployed research page contains synthetic summary statistics and a conceptual FAB animation. The CSV and Python files, not the moving illustration, are the source of experimental metrics.*

The source archive includes `src/phase3.py`, `src/phase2_reference.py`, `run_phase3.py`, `run_ablation.py`, CSVs, saved Q values, tests, chart images, research poster, and full research dossier.

### Reproduce the results

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q tests
python run_phase3.py
python run_ablation.py
```

## 11. Scientific boundaries and future work

The graph geometry, demand process, one-second scheduling and resource-control rules are synthetic abstractions. No real FAB telemetry, MES, PLC, factory 3D CAD data, or physical safety instrumentation is connected. The reported study does not establish industrial collision safety or universal deadlock freedom. Results should be re-evaluated under alternative network geometries, switch behavior, braking constraints, throughput levels, equipment workflows, and stronger RL baselines before making broad operational claims.

My main conclusion is that **resource reservation design had a larger observed effect on aggregate performance than incremental Q-learning** in this particular simulated system. The most transferable lesson is methodological: strong claims require realistic operating constraints, credible baselines, matched experiments, and transparent limitations.

---

**Project:** Industrial engineering independent research, synthetic FAB AMHS.  
**Seminar:** Learners × YPICS joint exchange, presentation material in preparation (scheduled October 31, 2026, 14:00).  
**Technical provenance:** AI-assisted research prototyping and documentation; source code, synthetic datasets, statistical outputs, and scope limitations are provided to support independent inspection.  
**Status:** Research prototype, not field-validated industrial software.