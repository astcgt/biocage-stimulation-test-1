#!/bin/bash
# PI 2026-11-22 (pending item 14, option C): 8 flexion-extension cycles at the intact-ROM amplitude (window_cycles n 8, scale 0.8) to see whether
# the posterior translation reaches a steady state or keeps growing. Full-Newton windows (PI item 12). One design per call.
#  fric designs: h18 insertion of pilot_cyc8v/<p> (production binary; h31 skips the window: restart_env), then h47 build pilot_cyc8vrN/<p>
#                (+ window_max_ups 0) from that checkpoint and h47 run of the cycle window (route E, stick-memory law).
#  process-G design: h18 of pilot_cyc8vGN/<p> with BIOCAGE_FEBIO = cbuild_fric + BIOCAGE_STICK_MEMORY = 1 (insertion + window in one run).
# usage: lanes8.sh <gpu> <cores> <design>
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
G=$1; C=$2; p=$3; A=human_study/al_v2
bash scripts/5_compute/wait_quota.sh $C
if [ -d $A/pilot_cyc8vGN/$p ]; then
  until BIOCAGE_FEBIO=$PWD/third_party/FEBio/cbuild_fric/bin/febio4 BIOCAGE_STICK_MEMORY=1 python scripts/5_compute/h18_run_gpu_case.py $G $A/pilot_cyc8vGN/$p $C; [ $? -ne 3 ]; do sleep 600; done
  echo "$(date '+%m-%d %H:%M') $p process-G 8-cycle run ended"
else
  until python scripts/5_compute/h18_run_gpu_case.py $G $A/pilot_cyc8v/$p $C; [ $? -ne 3 ]; do sleep 600; done
  if grep -q "N O R M A L" $A/pilot_cyc8v/${p}_gpu$G/case.log; then
    python scripts/5_compute/h47_restart_pilot.py build $A/pilot_cyc8vrN/$p $A/pilot_cyc8v/${p}_gpu$G 'window_max_ups=0' && \
    for i in $(seq 36); do bash scripts/5_compute/wait_quota.sh $C; python scripts/5_compute/h47_restart_pilot.py run $A/pilot_cyc8vrN/$p $G $C flexion; [ -f $A/pilot_cyc8vrN/$p/resources_flexion.json ] && break; sleep 600; done
    echo "$(date '+%m-%d %H:%M') $p 8-cycle window ended"
  else echo "$(date '+%m-%d %H:%M') $p insertion not normal"; fi
fi
