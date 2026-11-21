#!/bin/bash
# PI 2026-11-20 decision 10: numerical check of the 3-cycle posterior accumulation. Same insertion checkpoint as pilot_cyc3vr,
# window only changed: pilot_cyc3vdt = window time step halved (0.025), pilot_cyc3vpen = cage contact penalty x2 from t 3.5-3.6
# (restart-file redefinition of load curve 16). usage: run_one.sh <class dir> <design> <gpu> <cores>
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
D=human_study/al_v2/$1/$2
bash scripts/5_compute/wait_quota.sh $4
for i in $(seq 36); do python scripts/5_compute/h47_restart_pilot.py run $D $3 $4 flexion; [ -f $D/resources_flexion.json ] && break; echo "$2 not started (cores?), retry in 10 min"; sleep 600; done
echo "$(date +%H:%M) $1 $2 done $(cat $D/resources_flexion.json | head -c 120)"
