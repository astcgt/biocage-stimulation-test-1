#!/bin/bash
# wave 4 (2026-11-08 02:xx): static window step (no inertia) from the holdE fine-hold checkpoints - discriminates slow-dynamic settling from friction creep.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_holdHf/p139_smS 4 5 & sleep 5
$R human_study/al_v2/pilot_holdHf/p139_ctlS 4 5 & sleep 5
$R human_study/al_v2/pilot_holdHf/p062_smS 3 5 & sleep 5
wait; echo "WAVE4 DONE $(date -Is)"
