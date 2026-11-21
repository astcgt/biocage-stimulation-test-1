#!/bin/bash
# PI 2026-11-20 (rough-surface upper bound): p062 re-inserted at mu 0.6 on the whole cage faces (pilot_mu06, production recipe via
# the h19 scheduler), then route-E windows (pilot_mu06r) via h51 generic mode - same recipe as pilot_mu03/drive_mu03r.sh.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
export H51_SRC=pilot_mu06 H51_DST=pilot_mu06r H51_KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001'
p=p062
while true; do
  for d in human_study/al_v2/pilot_mu06/${p}_gpu* human_study/al_v2/pilot_mu06/${p}; do
    if [ -f $d/case.dmp ] && grep -q "N O R M A L" $d/case.log 2>/dev/null; then
      python scripts/5_compute/h51_relG_fallback.py build $p && built=1; break
    elif grep -q "E R R O R" $d/case.log 2>/dev/null; then echo "$p insertion ERROR in $d"; exit 1; fi
  done
  [ -n "$built" ] && break; sleep 300
done
python scripts/5_compute/h51_relG_fallback.py run 1 4 6 $p:flexion $p:extension
echo MU06R DONE
