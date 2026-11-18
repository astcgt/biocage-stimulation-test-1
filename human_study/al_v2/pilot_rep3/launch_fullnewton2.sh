#!/bin/bash
# full-Newton reproducibility: p093 extension twice more on other GPU / core counts (n2 GPU 1 5 cores, n3 GPU 3 6 cores) and p145 extension with full Newton (GPU 4, 6 cores) - fills the 2x2 and tests whether max_ups 0 converges every time
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_rep3/p093n2 1 5 extension & sleep 5
$R human_study/al_v2/pilot_rep3/p093n3 3 6 extension & sleep 5
$R human_study/al_v2/pilot_rep3/p145n 4 6 extension & sleep 5
wait; echo "FN2 DONE $(date -Is)"
