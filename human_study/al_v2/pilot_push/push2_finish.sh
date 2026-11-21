#!/bin/bash
# 2026-11-21: when the six carried-push lanes are done, retry every design that pushed less than 0.5 mm (push2_retry.sh skips the others)
# and write the summary. One design at a time, 4 cores, quota-aware.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
L=human_study/al_v2/pilot_push
until [ "$(cat $L/push2_lane*.log 2>/dev/null | grep -c 'PUSH2 LANE')" -ge 6 ]; do sleep 300; done
ALL=$(ls -d human_study/al_v2/pilot_push/p??? human_study/al_v2/pilot_pushG/p??? | xargs -n1 basename | sort -u | tr '\n' ' ')
bash $L/push2_retry.sh 0 4 $ALL >> $L/push2_retry.log 2>&1
(cd ../biocage-evo && python ops/push2_summary.py > results/method/e09/push2_summary.log 2>&1)
echo "$(date '+%m-%d %H:%M') PUSH2 FINISH DONE" >> $L/push2_retry.log
