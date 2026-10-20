# 6_active_learning/

`h22_active_learning.py` - active-learning screening of BIOCAGE designs (rules: `human_study/DECISIONS.md`, "ACTIVE LEARNING").

| Command | What it does |
|---|---|
| `init` | 48 Sobol design points -> cage meshes (h12, cached) + ISO and compression cases (h14) -> scheduler queue |
| `collect` | post-process finished points (h15) and compute the dislocation score `y` and capacity `C` |
| `next` | fit the two GP surrogates, choose and queue the next batch (robust max-min over material uncertainty) |
| `loop` | `collect` + `next` every 5 min until the stop criterion (run in tmux: session `biocage_al_loop`) |
| `status` | counts and the current best points |

Outputs: `human_study/al/points.json` (all points, inputs, scores), `al.log`, `cases/pNNN_{iso,compress}`, `meshes/`.
