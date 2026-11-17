#!/bin/bash
# pilot_holdQ (2026-11-18): hold insertion decks like pilot_holdA but with the hold dtmax halved (dtmax_windows [[3.9,3.91,0.05],[4.4,4.5,0.025]] -> 0.025 on (3.91, 4.4], holdE trick),
# production binary, joint-driven windows (production-law half-step controls). The t 3.5 checkpoints feed the route-E stick-memory restarts (h47, class pilot_holdQR) = NUM-13 clause 2 under route E.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
python scripts/5_compute/h18_run_gpu_case.py 1 human_study/al_v2/pilot_holdQ/p062 6 & sleep 10
python scripts/5_compute/h18_run_gpu_case.py 4 human_study/al_v2/pilot_holdQ/p139 6 & sleep 10
wait; echo "HOLDQ DONE $(date -Is)"
