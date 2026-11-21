#!/bin/bash
# PI 2026-11-19 item 7 = 甲′: p061 (verdict source physio_relGr) at mu 0.3: process-G insertion with the physio_relG convention
# (h18 with BIOCAGE_FEBIO cbuild_fric + BIOCAGE_STICK_MEMORY 1), then route-E windows pilot_mu03Gr via h51 generic mode.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
G=${1:-4}
until BIOCAGE_FEBIO=$PWD/third_party/FEBio/cbuild_fric/bin/febio4 BIOCAGE_STICK_MEMORY=1 python scripts/5_compute/h18_run_gpu_case.py $G human_study/al_v2/pilot_mu03G/p061 6; [ $? -ne 3 ]; do echo "no idle cores, retry in 10 min"; sleep 600; done
export H51_SRC=pilot_mu03G H51_DST=pilot_mu03Gr H51_KEYS='restart_env={"BIOCAGE_STICK_MEMORY": "1"}|window_drive_mode="rigid_relative"|window_min_residual=0.0001'
python scripts/5_compute/h51_relG_fallback.py build p061 && python scripts/5_compute/h51_relG_fallback.py run 2 $G 6 p061:flexion p061:extension
echo MU03G DONE
