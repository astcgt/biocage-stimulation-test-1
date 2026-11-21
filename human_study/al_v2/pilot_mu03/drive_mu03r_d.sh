#!/bin/bash
# PI 2026-11-20 decision 9 (mu 0.3 official) follow-up, 授權自行決定: the 28 designs that verdicts.json flags mu03_not_run (their mu 0.35 read-out
# + the largest observed 0.35 -> 0.3 shift, 0.118 mm, could reach a line) + p128 (replicate of p095, so the deck group is judged at one mu).
# Same recipe as drive_mu03r_b/_c.sh (fric: scheduler insertion of pilot_mu03/<p> = physio_fric3 params + mu 0.3, then h51 generic route-E windows
# into pilot_mu03r) and drive_mu03G.sh (process G: h18 with cbuild_fric + STICK_MEMORY 1 into pilot_mu03G, then h51 into pilot_mu03Gr).
# usage: [GPUS=0,3,4] drive_mu03r_d.sh fric | G <gpu_a> <gpu_b>
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
A=human_study/al_v2
KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001'
if [ "$1" = fric ]; then
  export H51_SRC=pilot_mu03 H51_DST=pilot_mu03r H51_KEYS="$KEYS"
  IDS="p002 p014 p026 p038 p060 p065 p072 p076 p078 p079 p081 p092 p102 p112 p113 p117 p125 p132 p133 p135 p143 p148"
else
  export H51_SRC=pilot_mu03G H51_DST=pilot_mu03Gr H51_KEYS="$KEYS"
  IDS="p052 p083 p095 p104 p120 p129 p128"
  lane() { for p in "$@"; do
      until BIOCAGE_FEBIO=$PWD/third_party/FEBio/cbuild_fric/bin/febio4 BIOCAGE_STICK_MEMORY=1 python scripts/5_compute/h18_run_gpu_case.py $G0 $A/pilot_mu03G/$p 6; [ $? -ne 3 ]; do echo "$p no idle cores, retry in 10 min"; sleep 600; done
      echo "$(date +%H:%M) $p G insertion done"; done; }
  G0=$2 lane p052 p095 p120 p128 > $A/pilot_mu03/drive_d_G0.log 2>&1 &
  G0=$3 lane p083 p104 p129 > $A/pilot_mu03/drive_d_G1.log 2>&1 &
fi
N=$(echo $IDS | wc -w); built=""; i=0
while true; do                      # build the route-E windows of each design as soon as its insertion ended normally
  for p in $IDS; do
    case " $built " in *" $p "*) continue;; esac
    for d in $A/$H51_SRC/${p}_gpu* $A/$H51_SRC/${p}; do
      if [ -f $d/case.dmp ] && grep -q "N O R M A L" $d/case.log 2>/dev/null && ls -d $d/w_* >/dev/null 2>&1 && { [ -f $d/resources.json ] || [ -f $d/windows_skipped.json ] || [ -f $d/split_check.json ]; }; then
        built="$built $p"
        if python scripts/5_compute/h51_relG_fallback.py build $p; then   # windows start right away (h51 waits for the 32-core quota / GPU memory itself)
          i=$((i + 1)); g=$(echo ${GPUS:-0,3,4} | cut -d, -f$(( (i % $(echo ${GPUS:-0,3,4} | tr ',' ' ' | wc -w)) + 1 )))
          python scripts/5_compute/h51_relG_fallback.py run 1 $g 6 $p:flexion $p:extension > $A/pilot_mu03/drive_d_win_$p.log 2>&1 &
          echo "$(date +%H:%M) built $p, windows queued on GPU $g"
        fi; break
      elif grep -q "E R R O R" $d/case.log 2>/dev/null; then echo "$(date +%H:%M) $p insertion ERROR in $d"; built="$built $p"; break; fi
    done
  done
  [ $(echo $built | wc -w) -ge $N ] && break; sleep 300
done
echo "built: $built"; wait
echo "MU03R_D $1 DONE"
