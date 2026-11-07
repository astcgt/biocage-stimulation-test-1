#!/bin/bash
# wave 7 (2026-11-08): half-step arms for the hold criterion clause 2 (production dt 0.05 vs 0.025): stick memory + min_residual 1e-4 + window_dt 0.025, extension window.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
H=scripts/5_compute/h47_restart_pilot.py; A=human_study/al_v2/pilot_holdH
python3 $H run $A/p062_smRh 3 5 > $A/p062_smRh/run.out 2>&1 &
sleep 5
python3 $H run $A/p139_smRh 4 5 > $A/p139_smRh/run.out 2>&1 &
wait
echo "WAVE7 DONE $(date -Is)"
