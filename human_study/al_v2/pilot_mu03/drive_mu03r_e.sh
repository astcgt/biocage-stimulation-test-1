#!/bin/bash
# 2026-11-21 (授權自行決定): the designs still judged at mu 0.35 only, rerun at mu 0.3 (decks: pilot_mu03/build_e.py). One lane = designs
# in sequence on one GPU: insertion by h18 (production binary for pilot_mu03; cbuild_fric + STICK_MEMORY 1 for pilot_mu03G = the
# physio_relG convention), then the route-E windows from that checkpoint (h51 generic: build + run flexion, extension; h51 waits for
# the 32-core quota itself). usage: drive_mu03r_e.sh <fric|G> <gpu> p036 p066 ...
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
KIND=$1; G0=$2; shift 2; A=human_study/al_v2
KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001'
if [ $KIND = G ]; then SRC=pilot_mu03G; DST=pilot_mu03Gr; else SRC=pilot_mu03; DST=pilot_mu03r; fi
for p in "$@"; do
  if ! ls -d $A/$SRC/${p}_gpu* >/dev/null 2>&1; then
    bash scripts/5_compute/wait_quota.sh 6
    if [ $KIND = G ]; then
      until BIOCAGE_FEBIO=$PWD/third_party/FEBio/cbuild_fric/bin/febio4 BIOCAGE_STICK_MEMORY=1 python scripts/5_compute/h18_run_gpu_case.py $G0 $A/$SRC/$p 6; [ $? -ne 3 ]; do echo "$p no idle cores, retry in 10 min"; sleep 600; done
    else
      until python scripts/5_compute/h18_run_gpu_case.py $G0 $A/$SRC/$p 6; [ $? -ne 3 ]; do echo "$p no idle cores, retry in 10 min"; sleep 600; done
    fi
  fi
  d=$(ls -d $A/$SRC/${p}_gpu* 2>/dev/null | head -1)
  if [ -n "$d" ] && [ -f $d/case.dmp ] && grep -q "N O R M A L" $d/case.log 2>/dev/null; then
    H51_SRC=$SRC H51_DST=$DST H51_KEYS="$KEYS" python scripts/5_compute/h51_relG_fallback.py build $p && \
    H51_SRC=$SRC H51_DST=$DST H51_KEYS="$KEYS" python scripts/5_compute/h51_relG_fallback.py run 2 $G0 6 $p:flexion $p:extension
    echo "$(date +%H:%M) $p windows done"
  else echo "$(date +%H:%M) $p insertion not normal"; fi
done
echo "MU03R_E $KIND lane $G0 DONE"
