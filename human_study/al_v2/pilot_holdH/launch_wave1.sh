#!/bin/bash
# wave 1 (2026-11-07 13:20): restart hold pilots, extension window, from the holdA (coarse hold) / holdE (fine hold) t 3.5 checkpoints.
# GPU 3: p062 arms, GPU 4: p139 arms; 3 cores each (30 of the 32-core quota). Launched from tmux session holdH.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
for v in ctl sm smR al; do $R human_study/al_v2/pilot_holdH/p062_$v 3 3 & sleep 4; done
$R human_study/al_v2/pilot_holdHf/p062_sm 3 3 & sleep 4
for v in ctl sm smR al; do $R human_study/al_v2/pilot_holdH/p139_$v 4 3 & sleep 4; done
$R human_study/al_v2/pilot_holdHf/p139_sm 4 3 & sleep 4
wait
echo "WAVE1 DONE $(date -Is)"
