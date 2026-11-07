#!/bin/bash
# wave 5 (2026-11-08 04:xx): FLEXION hold windows from the holdA checkpoints (coarse hold): stick memory vs control (holdA flexion drifted -0.118 / -0.183 under the production law).
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_holdH/p062_sm 3 5 flexion & sleep 5
$R human_study/al_v2/pilot_holdH/p062_ctl 3 5 flexion & sleep 5
$R human_study/al_v2/pilot_holdH/p139_sm 4 5 flexion & sleep 5
$R human_study/al_v2/pilot_holdH/p139_ctl 4 5 flexion & sleep 5
wait; echo "WAVE5 DONE $(date -Is)"
