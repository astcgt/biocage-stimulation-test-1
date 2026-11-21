#!/bin/bash
# PI 2026-11-19 item 4 = 乙: posterior push-out (S9 direction) on the 43 PASS + GREY designs as a RANKING read-out.
# v2 (11:2x): build just before each run (a settings edit between build and run invalidated the h24 fingerprint and the h51
# orchestrator then rebuilt with ITS default keys - refused by h24, nothing ran). Per design: h53 build (h47 route-E rebuild of the
# verdict friction source + push windows, h24 inside) -> h47 run push_post (stick memory). Lanes: every n-th design per GPU.
# usage: push_batch.sh <gpu> <lane index> <n lanes>
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
G=$1; L=$2; N=$3; A=human_study/al_v2
python - <<'P' | awk -v L=$L -v N=$N 'NR % N == L' > /tmp/claude-1024/push_lane_$L.txt
import json
E='/raid/jupyter-alz.ee09/projects/claude-work/biocage-evo/'
cls=json.load(open(E+'results/method/split/verdict_classes_merged.json'))['classes']; fr=json.load(open(E+'results/method/fric/verdicts.json'))
for p in sorted(cls['PASS']+cls['GREY/friction-posterior-0.45-0.55']):
    w=fr[p]['windows']['flexion']; print(p, w['set'], w['case_dir'], 'pilot_pushG' if w['set']=='physio_relGr' else 'pilot_push')
P
while read p set cd dst; do
  d=$A/$dst/$p
  [ -f $d/done_push_post ] && grep -q "\"normal\": true" $d/resources_push_post.json 2>/dev/null && { echo "$p done"; continue; }
  python scripts/5_compute/h53_push_restart.py build $d $A/$set/$cd 2>&1 | tail -1
  for i in $(seq 36); do
    python scripts/5_compute/h47_restart_pilot.py run $d $G 6 push_post 2>&1 | tail -1
    [ -f $d/resources_push_post.json ] && break
    if ! python -c "import sys;sys.path.insert(0,'scripts/5_compute');import h24_preflight as h;sys.exit(0 if h.valid('$d') else 1)"; then
      python scripts/5_compute/h53_push_restart.py build $d $A/$set/$cd 2>&1 | tail -1; fi
    sleep 300
  done
  echo "$(date +%H:%M) $p push_post $(python -c "import json;print(json.load(open('$d/resources_push_post.json')).get('normal'))" 2>/dev/null)"
done < /tmp/claude-1024/push_lane_$L.txt
echo "PUSH LANE $L DONE"
