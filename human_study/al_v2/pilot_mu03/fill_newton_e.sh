#!/bin/bash
# 2026-11-22 (PI item 12: full Newton is the official window solver): batch-e mu 0.3 windows whose quasi-Newton run stopped before an
# evaluation point (no 1.5 N m state, intact ROM not reached) are recomputed with full Newton (window_max_ups 0) from the SAME checkpoint,
# so that 'not computable at mu 0.3' is counted under the official solver. Same recipe as drive_mu03rN.sh / drive_newton_confirm.sh.
# usage: fill_newton_e.sh <fric|G> <gpu> p050:extension p064:extension ...
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
KIND=$1; G=$2; shift 2
KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001|window_max_ups=0'
if [ $KIND = G ]; then export H51_SRC=pilot_mu03G H51_DST=pilot_mu03GrN; else export H51_SRC=pilot_mu03 H51_DST=pilot_mu03rN; fi
export H51_KEYS="$KEYS"
python scripts/5_compute/h51_relG_fallback.py build $(printf '%s\n' "$@" | cut -d: -f1 | sort -u | tr '\n' ' ')
python scripts/5_compute/h51_relG_fallback.py run 1 $G 6 "$@"
echo "FILL_NEWTON_E $KIND $* DONE $(date '+%m-%d %H:%M')"
