#!/bin/bash
# full-Newton test (restart Control max_ups 0) on the two windows that no friction law / drive could compute (p048 extension, p115 flexion; process-G dumps, physio_relGr settings)
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_rep3G/p048 4 6 extension & sleep 5
$R human_study/al_v2/pilot_rep3G/p115 4 6 flexion & sleep 5
wait; echo "FN DONE $(date -Is)"
