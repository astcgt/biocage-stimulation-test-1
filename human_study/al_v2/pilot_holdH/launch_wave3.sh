#!/bin/bash
# wave 3 (2026-11-08): the six stick-memory arms on the fixed library (sha 3130d3e8; wave 2 ran on the unfixed one by mistake); GPU 3 = p062, GPU 4 = p139, 5 cores each.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
for v in sm smR; do $R human_study/al_v2/pilot_holdH/p062_$v 3 5 & sleep 5; done
$R human_study/al_v2/pilot_holdHf/p062_sm 3 5 & sleep 5
for v in sm smR; do $R human_study/al_v2/pilot_holdH/p139_$v 4 5 & sleep 5; done
$R human_study/al_v2/pilot_holdHf/p139_sm 4 5 & sleep 5
wait; echo "WAVE3 DONE $(date -Is)"
