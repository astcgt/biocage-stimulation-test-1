#!/bin/bash
# pilot_holdQR wave 1 (2026-11-18 05:4x): TRUE half-step hold (deck dtmax curve 0.025 over the hold, dtmax_windows [[3.9,3.91,0.05],[4.4,4.5,0.025]])
# restarted from the pilot_holdQ t 3.5 checkpoints under ROUTE E (relative C3-pot drive) with stick memory + window_min_residual 1e-4
# -> NUM-13 clause 2 (step / half-step hold-end difference <= 0.005 mm) under the route-E window configuration; compare with pilot_holdR (dtmax 0.05).
# p062 GPU 1, p139 GPU 4, 5 cores per window.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_holdQR/p062 1 5 extension & sleep 5
$R human_study/al_v2/pilot_holdQR/p062 1 5 flexion & sleep 5
$R human_study/al_v2/pilot_holdQR/p139 4 5 extension & sleep 5
$R human_study/al_v2/pilot_holdQR/p139 4 5 flexion & sleep 5
wait; echo "WAVE1QR DONE $(date -Is)"
