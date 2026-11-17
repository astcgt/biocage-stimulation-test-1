#!/bin/bash
# pilot_holdR wave 1 (2026-11-18): hold windows (holdA checkpoints, ramp to 0.8 x amplitude then hold 0.5 s) under ROUTE E (relative C3-pot drive) with stick memory + window_min_residual 1e-4
# -> NUM-13 hold-segment evidence for the route-E window configuration (PI 2026-11-18 「數值項可以補」). p062 GPU 1, p139 GPU 4, 5 cores per window.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_holdR/p062 1 5 extension & sleep 5
$R human_study/al_v2/pilot_holdR/p062 1 5 flexion & sleep 5
$R human_study/al_v2/pilot_holdR/p139 4 5 extension & sleep 5
$R human_study/al_v2/pilot_holdR/p139 4 5 flexion & sleep 5
wait; echo "WAVE1 DONE $(date -Is)"
