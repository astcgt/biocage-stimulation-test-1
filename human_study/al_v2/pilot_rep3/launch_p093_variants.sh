#!/bin/bash
# p093 extension reproducer (fails 2 of 3 times from the same dump): n = full Newton (restart Control max_ups 0), d = window dt 0.005 (step_size / plain dtmax; the hold curve is unaffected)
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_rep3/p093n 4 6 extension & sleep 5
$R human_study/al_v2/pilot_rep3/p093d 4 6 extension & sleep 5
wait; echo "P093VAR DONE $(date -Is)"
