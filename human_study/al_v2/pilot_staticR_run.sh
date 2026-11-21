#!/bin/bash
# 2026-11-21 NUM-08 FRIC (never run): p062 route-E windows with a STATIC window step (h14 key window_static; same physio_fric3 t 3.5
# checkpoint, stick-memory law, relative drive) vs the slow-dynamic production windows physio_fric5r/p062. usage: pilot_staticR_run.sh <gpu> <cores> <window>
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
D=human_study/al_v2/pilot_staticR/p062
for i in $(seq 36); do python scripts/5_compute/h47_restart_pilot.py run $D $1 $2 $3; [ -f $D/resources_$3.json ] || [ -f $D/resources.json -a "$3" = extension ] && break; echo "not started, retry in 10 min"; sleep 600; done
echo "$(date +%H:%M) staticR p062 $3 done"
