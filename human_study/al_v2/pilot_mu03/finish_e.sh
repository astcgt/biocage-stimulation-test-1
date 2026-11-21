#!/bin/bash
# 2026-11-21: when the three mu 0.3 'e' lanes are done, rerun the verdict pipeline (fric_compare -> e07_batch -> replicate_agreement ->
# collect_split -> mu_req_field -> shortcut_consistency -> obs01_batch); log ../biocage-evo/results/method/fric/pipeline_e.log
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
L=human_study/al_v2/pilot_mu03
until [ "$(cat $L/drive_e_fric.log $L/drive_e_G1.log $L/drive_e_G3.log 2>/dev/null | grep -c 'MU03R_E')" -ge 3 ]; do sleep 300; done
cd ../biocage-evo; LOG=results/method/fric/pipeline_e.log
cp results/method/fric/verdicts.json results/method/fric/verdicts_before_batch_e.json
python ops/fric_compare.py 3 > $LOG 2>&1 && python ops/e07_batch.py 3 >> $LOG 2>&1 && python ops/replicate_agreement.py physio_fric5r physio_relGr pilot_mu03r pilot_mu03Gr >> $LOG 2>&1 && \
python ops/collect_split.py 3 >> $LOG 2>&1 && python ops/mu_req_field.py >> $LOG 2>&1 && python ops/shortcut_consistency.py >> $LOG 2>&1 && python ops/obs01_batch.py 2 >> $LOG 2>&1
echo "$(date '+%m-%d %H:%M') PIPELINE_E DONE rc=$?" >> $LOG
