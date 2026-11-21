#!/bin/bash
# 2026-11-21 (授權自行決定, pilot): the 11 mu 0.3 route-E windows that stopped before an evaluation point (quasi-Newton, max_ups 10), restarted from
# the SAME mu 0.3 checkpoints with full Newton in the window Control (window_max_ups 0; pilot_rep3 2026-11-18: 4 of 4 converged where BFGS
# converged 1 of 3, read-out within 0.004 mm). Evidence for the pending PI decision 'window solver -> full Newton'; not a verdict source until then.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001|window_max_ups=0'
( export H51_SRC=pilot_mu03 H51_DST=pilot_mu03rN H51_KEYS="$KEYS"
  python scripts/5_compute/h51_relG_fallback.py build p014 p026 p079 p086 p093 p117 p125
  python scripts/5_compute/h51_relG_fallback.py run 2 0,3 6 p014:extension p026:extension p079:extension p086:flexion p093:flexion p117:flexion p117:extension p125:flexion ) > human_study/al_v2/pilot_mu03/drive_N_fric.log 2>&1 &
( export H51_SRC=pilot_mu03G H51_DST=pilot_mu03GrN H51_KEYS="$KEYS"
  python scripts/5_compute/h51_relG_fallback.py build p095 p104 p128
  python scripts/5_compute/h51_relG_fallback.py run 1 5 6 p095:extension p104:extension p128:extension ) > human_study/al_v2/pilot_mu03/drive_N_G.log 2>&1 &
wait; echo "MU03RN DONE"
