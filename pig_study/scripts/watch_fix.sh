#!/bin/bash
# wait until both Test-1 summaries exist, then patch F_fail_N (runs before phase 2 starts)
while [ ! -f results/test1_static/A_smooth/summary.json ] || [ ! -f results/test1_static/B_tread/summary.json ]; do
  python3 scripts/fix_ffail.py; sleep 20
done
python3 scripts/fix_ffail.py
