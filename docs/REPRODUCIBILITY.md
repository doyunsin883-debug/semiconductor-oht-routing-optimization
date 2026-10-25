# Reproducibility / 재현 안내

This repository presents results of a synthetic semiconductor OHT simulation experiment and the related analytic visualizations.

## Experimental design

- Network: 48 nodes, 82 directed rail links; synthetic layout, not a real FAB floorplan.
- Fleet: 9 OHT vehicles for the main experiment.
- Task arrival rate: baseline 68 requests/hour, demand-surge factor 1.5.
- Horizon: 1,500 seconds (25 minutes).
- Main experiments: 3 scenarios × 5 policies × 40 matching evaluation seeds = **600**.
- Safety/fleet sensitivity: 3 scenarios × 3 fleet sizes × 2 guard conditions × 20 seeds = **360**.
- Policy training: separate simulation seeds, tabular Q-learning with learning rate 0.22 and discount factor 0.87.
- Paired statistical comparisons: seed-level differences, 95% bootstrap confidence intervals and exact sign tests with Holm correction.

## Distinguish the claims

1. **Reservation architecture:** Comparing partial-segment reservation with atomic full-route reservation estimates the total impact of two different implemented control policies, not a causal effect of ML.
2. **Learning contribution:** Comparing the trained Q policy with the identical untrained policy isolates additional learning effects under shared safety constraints.
3. **Wait-for cycles:** WFG cycles are risk indicators, not proof of a permanent physical deadlock. Zero recorded ownership violations within test scope is not a safety certification.
4. **3D visuals:** The public web view is an explanatory SVG projection, not a synchronized replay of all simulation runs.

## Repository release status

The complete Phase 3 experiment code, 600-run raw evaluation CSV, 360-run guard ablation CSV, tabular Q model, representative 800-second trace, PNG figures, summary tables and paired inference are now committed to GitHub. The A2 PDF and bilingual research brief are generated from committed data by `scripts/build_publications.py` and committed by GitHub Actions. The original separate 12-page editorial report remains in the offline ChatGPT delivery archive. Do not confuse it with the GitHub-generated research brief.

## Quick calculations

To examine the current CSV summary using Python without additional dependencies:

```python
import csv
with open("results/summary_600.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
for scenario in ("normal", "surge", "closure"):
    r = {row["policy"]: float(row["completed_mean"]) for row in rows if row["scenario"] == scenario}
    gain = r["partial_dynamic"] - r["full_atomic_dynamic"]
    learned = r["partial_rl_trained"] - r["partial_rl_untrained"]
    print(scenario, round(gain, 3), round(learned, 3))
```

This calculation verifies published means, not the full seed-level statistical inference. To reproduce confidence intervals and p-values exactly, use the per-run records and the complete Python simulation archive.


## Verified GitHub Actions

- [Unit tests](../.github/workflows/tests.yml) — Python 3.12, tests must pass.
- [600 + 360 benchmark reproduction](../.github/workflows/benchmark.yml) — reruns experiments and checks all policy/scenario completion means against the saved CSV (maximum tolerance 0.001).
- [GitHub PDF generation](../.github/workflows/publications.yml) — builds the A2 PDF poster and bilingual research brief with ReportLab and Korean fonts.

**Data download:** [600 evaluation rows](../results/heldout_600_runs.csv) · [360 sensitivity rows](../results/guard_ablation_360.csv) · [Q-learning state-action table](../results/model_q.json).
