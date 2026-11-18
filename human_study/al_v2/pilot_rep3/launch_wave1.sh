#!/bin/bash
# pilot_rep3 (2026-11-18 11:3x, PI 「依照建議」 C2 option 乙): third replicate of the two deck groups whose two production replicates (physio_fric5r) disagree by > 0.005 mm:
# p093 / p145 extension (spread 0.0124 mm, both at the ROM state, straddling the 0.55 mm posterior limit) and p051 / p075 flexion (0.0068 mm).
# Same settings as physio_fric5r (route E, stick memory, min_residual 1e-4), same physio_fric3 insertion dumps; p093/p145 GPU 1, p051/p075 GPU 4, 5 cores each.
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
R="python scripts/5_compute/h47_restart_pilot.py run"
$R human_study/al_v2/pilot_rep3/p093 1 5 extension & sleep 5
$R human_study/al_v2/pilot_rep3/p145 1 5 extension & sleep 5
$R human_study/al_v2/pilot_rep3/p051 4 5 flexion & sleep 5
$R human_study/al_v2/pilot_rep3/p075 4 5 flexion & sleep 5
wait; echo "REP3 DONE $(date -Is)"
