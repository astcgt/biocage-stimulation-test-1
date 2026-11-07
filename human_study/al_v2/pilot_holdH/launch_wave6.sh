#!/bin/bash
# wave 6 (2026-11-08): flexion hold, smR arms (stick memory + window min_residual 1e-4) - p139_sm flexion hit the stationary
# displacement-criterion trap at t 4.228 (residual 7e-7, energy met, displacement 3.4e-10 vs 2.5e-12 required); p062_smR as the pair.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
H=scripts/5_compute/h47_restart_pilot.py; A=human_study/al_v2/pilot_holdH
python3 $H run $A/p139_smR 4 5 flexion > $A/p139_smR/run_flexion.out 2>&1 &
sleep 5
python3 $H run $A/p062_smR 3 5 flexion > $A/p062_smR/run_flexion.out 2>&1 &
wait
echo "WAVE6 DONE $(date -Is)"
