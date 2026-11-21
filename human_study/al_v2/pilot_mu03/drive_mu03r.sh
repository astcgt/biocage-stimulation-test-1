#!/bin/bash
# PI 2026-11-19 (option 乙): 5 designs re-inserted at mu 0.3 (pilot_mu03, production recipe), then route-E windows (pilot_mu03r) via h51 generic mode
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
export H51_SRC=pilot_mu03 H51_DST=pilot_mu03r H51_KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001'
IDS="p062 p100 p063 p131 p110"; built=""
while true; do
  for p in $IDS; do
    case " $built " in *" $p "*) continue;; esac
    for d in human_study/al_v2/pilot_mu03/${p}_gpu* human_study/al_v2/pilot_mu03/${p}; do
      if [ -f $d/case.dmp ] && grep -q "N O R M A L" $d/case.log 2>/dev/null; then
        python scripts/5_compute/h51_relG_fallback.py build $p && built="$built $p"; break
      elif grep -q "E R R O R" $d/case.log 2>/dev/null; then echo "$p insertion ERROR in $d"; built="$built $p"; break; fi
    done
  done
  n=$(echo $built | wc -w); [ $n -ge 5 ] && break; sleep 300
done
echo "built: $built"
ONLY=""; for p in $built; do [ -d human_study/al_v2/pilot_mu03r/$p ] && ONLY="$ONLY $p:flexion $p:extension"; done
python scripts/5_compute/h51_relG_fallback.py run 3 2,3,4 6 $ONLY
echo MU03R DONE
