# Data & asset provenance / 데이터·자산 사용 고지

**Research data.** All reported OHT movements, FOUP requests, 48-node directed network structure, 600 evaluation runs and 360 fleet/guard sensitivity trials are synthetic outputs of the research Python simulation code. No Samsung Electronics internal files, real fab floorplans, MES logs, identifiable employees, or measured wafer-production data are included.

**Scientific figures.** SVG charts (`assets/figures/01_policy_comparison.svg`, `02_paired_effects.svg`, `03_cycle_guard_ablation.svg`) were generated from the model's recorded synthetic means and paired inference. The directed network and pipeline SVGs are explanatory technical schematics. Their role is to help readers interpret simulated data; they are not photographs of a real factory.

**Interactive website.** https://fabflow-oht-phase3-deadlock.vercel.app/ is an explanatory public prototype. Its OHT animation is a stylized SVG scene, not a sensor-synchronized digital twin and not a replay of every Python experiment.

**PDF publications.** The repository PDF versions `docs/FABFLOW_Conference_Poster_A2.pdf` and `docs/FABFLOW_GitHub_Research_Brief_KO_EN.pdf` are created deterministically by GitHub Actions from `scripts/build_publications.py`. They are separate editions from the earlier offline A2 poster and 12-page research editorial report distributed in ChatGPT.

**Seminar context.** https://www.instagram.com/p/De6u9tXj2_h/ is a public announcement of the Learners × YPICS joint logistics seminar scheduled for **2026-10-31 at 14:00**. This repository does not assert that the presentation has already been delivered or awarded.

**Safety.** Simulated non-overlapping reservations and wait-for-cycle risk suppression are not equipment safety certifications. Vehicle physics, PLC interlocks, stop distances, actual human safety procedures and site engineering have not been validated.

**AI assistance.** Coding assistance, editorial work and chart/PDF preparation were AI-assisted. All empirical-looking values are explicitly labeled as simulation outputs. The public repository includes models, assumptions, scripts, checks and analyses rather than claiming real laboratory measurements.
