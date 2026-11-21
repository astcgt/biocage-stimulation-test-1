#!/bin/bash
# PI 2026-11-19 item 5: S9 3 cycles at the verdict amplitude (window_cycles scale 0.8 = intact ROM) on the 10 PASS designs with
# the smallest friction posterior read-out + p062 reference. One lane per GPU, designs in sequence.
#  fric designs (pilot_cyc3v): h18 insertion with the production binary (h31 skips the windows: restart_env), then h47 build
#    pilot_cyc3vr/<p> from that checkpoint and h47 run of the cycle window with the stick-memory law (route E).
#  relG designs (pilot_cyc3vG): h18 with BIOCAGE_FEBIO = cbuild_fric + BIOCAGE_STICK_MEMORY = 1 (physio_relG convention:
#    insertion + window with stick memory), windows run inside h31.
# usage: lanes.sh <gpu> <cores> p036 p121 ...
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
G=$1; C=$2; shift 2; A=human_study/al_v2
for p in "$@"; do
  if [ -d $A/pilot_cyc3vG/$p ]; then
    until BIOCAGE_FEBIO=$PWD/third_party/FEBio/cbuild_fric/bin/febio4 BIOCAGE_STICK_MEMORY=1 python scripts/5_compute/h18_run_gpu_case.py $G $A/pilot_cyc3vG/$p $C; [ $? -ne 3 ]; do echo "$p no idle cores, retry in 10 min"; sleep 600; done
    echo "$(date +%H:%M) $p relG done"
  else
    until python scripts/5_compute/h18_run_gpu_case.py $G $A/pilot_cyc3v/$p $C; [ $? -ne 3 ]; do echo "$p no idle cores, retry in 10 min"; sleep 600; done
    if grep -q "N O R M A L" $A/pilot_cyc3v/${p}_gpu$G/case.log; then
      python scripts/5_compute/h47_restart_pilot.py build $A/pilot_cyc3vr/$p $A/pilot_cyc3v/${p}_gpu$G && \
      for i in $(seq 36); do python scripts/5_compute/h47_restart_pilot.py run $A/pilot_cyc3vr/$p $G $C flexion; [ -f $A/pilot_cyc3vr/$p/resources_flexion.json ] && break; echo "$p window not started (cores?), retry in 10 min"; sleep 600; done
      echo "$(date +%H:%M) $p route-E cycle window done"
    else echo "$(date +%H:%M) $p insertion not normal"; fi
  fi
done
echo "LANE $G DONE"
