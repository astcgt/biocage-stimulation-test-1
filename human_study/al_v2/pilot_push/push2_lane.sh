#!/bin/bash
# 2026-11-21 carried push (h53 add2: both wall node sets prescribed -X, window w_push_post2) on EXISTING pilot_push / pilot_pushG cases.
# Per design: h24 check in place (settings changed since the build; the check rebuilds the deck and compares, results untouched),
# add the window, run it (h47, route-E keys / stick-memory law as the one-wall push), read e09 -> ../biocage-evo/results/method/e09/<p>_push_post2.json
# usage: push2_lane.sh <gpu> <cores> p062 p051 ...
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
G=$1; C=$2; shift 2; A=human_study/al_v2; EV=../biocage-evo
for p in "$@"; do
  d=$A/pilot_push/$p; [ -d $A/pilot_pushG/$p ] && d=$A/pilot_pushG/$p
  [ -f $d/done_push_post2 ] && { echo "$p already done"; continue; }
  python3 -c "
import sys; sys.path.insert(0, 'scripts/5_compute'); import h24_preflight
r = h24_preflight.check('$d'); print('$p h24', r['ok'], r['errors']); sys.exit(0 if r['ok'] else 4)" || { echo "$p NOT LAUNCHED (h24)"; continue; }
  [ -f $d/w_push_post2/restart.feb ] || python scripts/5_compute/h53_push_restart.py add2 $d
  bash scripts/5_compute/wait_quota.sh $C
  for i in $(seq 36); do python scripts/5_compute/h47_restart_pilot.py run $d $G $C push_post2; [ -f $d/resources_push_post2.json ] && break; echo "$p not started (cores?), retry in 10 min"; sleep 600; done
  (cd $EV && python methods/e09_pushout.py $PWD/../biocage_simulation_test_oct2026/$d/w_push_post2 results/method/e09/${p}_push_post2.json 2>&1 | tail -1 | sed "s/^/$(date +%H:%M) $p /")
done
echo "PUSH2 LANE $G DONE"
