#!/bin/bash
# PI 2026-11-22 (pending item 12): full Newton becomes the official window solver setting; 5 designs that already PASS at mu 0.3 with the
# quasi-Newton windows are recomputed with full Newton from the same checkpoints (both windows) to confirm that the read-outs do not move
# (criterion: posterior / in-plane translation at the evaluation point within 0.005 mm). 4 production-inserted + 1 process-G design.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001|window_max_ups=0'
( export H51_SRC=pilot_mu03 H51_DST=pilot_mu03rN H51_KEYS="$KEYS"
  python scripts/5_compute/h51_relG_fallback.py build p105 p110 p131 p038
  python scripts/5_compute/h51_relG_fallback.py run 2 1,3 6 p105:flexion p105:extension p110:flexion p110:extension p131:flexion p131:extension p038:flexion p038:extension ) > human_study/al_v2/pilot_mu03/drive_NC_fric.log 2>&1 &
( export H51_SRC=pilot_mu03G H51_DST=pilot_mu03GrN H51_KEYS="$KEYS"
  python scripts/5_compute/h51_relG_fallback.py build p052
  python scripts/5_compute/h51_relG_fallback.py run 1 4 6 p052:flexion p052:extension ) > human_study/al_v2/pilot_mu03/drive_NC_G.log 2>&1 &
wait; echo "NEWTON_CONFIRM DONE $(date '+%m-%d %H:%M')" >> human_study/al_v2/pilot_mu03/drive_NC_fric.log
