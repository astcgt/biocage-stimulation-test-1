#!/bin/bash
date +%T; grep -c "done\|FAILED" logs/run_all.log | sed 's/^/jobs finished: /'; grep FAILED logs/run_all.log | head -3
for f in results/*/*/log.txt; do d=$(dirname $f); [ -f $d/summary.json ] && s=DONE || s=run; echo "$s $(basename $d): $(tail -1 $f | cut -c1-120)"; done
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader -i 3,4,7 | tr '\n' ' '; echo
