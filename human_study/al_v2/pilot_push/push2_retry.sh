#!/bin/bash
# 2026-11-21: carried-push runs that died in their FIRST step (no converged state) are rerun with a small first increment (dt0 0.005)
# and full Newton (h53 add2 dt0= maxups=); the old log is kept as case_first_fail.log. usage: push2_retry.sh <gpu> <cores> p039 p064 ...
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
G=$1; C=$2; shift 2; A=human_study/al_v2; EV=../biocage-evo
for p in "$@"; do
  d=$A/pilot_push/$p; [ -d $A/pilot_pushG/$p ] && d=$A/pilot_pushG/$p; w=$d/w_push_post2
  [ -f $w/case.log ] || { echo "$p has no first attempt"; continue; }
  # retry when the first attempt pushed less than 0.5 mm (2026-11-21 20:5x: was 'no converged state'; p088 stopped after 2 steps)
  awk -v t="$(grep 'converged at time' $w/case.log | tail -1 | awk '{print $NF}')" 'BEGIN{exit !(t == "" || t < 3.5834)}' || { echo "$p pushed more than 0.5 mm in the first attempt"; continue; }
  [ -f $w/case_first_fail.log ] && { echo "$p already retried"; continue; }
  cp $w/case.log $w/case_first_fail.log
  python3 -c "
import sys; sys.path.insert(0, 'scripts/5_compute'); import h24_preflight
r = h24_preflight.check('$d'); sys.exit(0 if r['ok'] else 4)" || { echo "$p NOT LAUNCHED (h24)"; continue; }
  python scripts/5_compute/h53_push_restart.py add2 $d mm=3.0 dt0=0.005 maxups=0
  rm -f $d/resources_push_post2.json $d/done_push_post2
  bash scripts/5_compute/wait_quota.sh $C
  for i in $(seq 36); do python scripts/5_compute/h47_restart_pilot.py run $d $G $C push_post2; [ -f $d/resources_push_post2.json ] && break; sleep 600; done
  (cd $EV && python methods/e09_pushout.py $PWD/../biocage_simulation_test_oct2026/$w results/method/e09/${p}_push_post2.json 2>&1 | tail -1 | sed "s/^/$(date +%H:%M) $p retry /")
done
echo "PUSH2 RETRY $G DONE"
