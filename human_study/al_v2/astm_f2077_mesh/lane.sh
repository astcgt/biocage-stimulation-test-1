#!/bin/bash
# 2026-11-21 feasibility criterion F2 (mesh sensitivity) of the ASTM-style bench: p062 with the 0.1 mm thickness mesh (source
# numconv_hz01/p062, 43,010 cage hex vs 21,505), elastic (D 0.6) and hard-phase elastoplastic (WE 0.02, D 1.0); compare with
# astm_f2077/p062 and astm_f2077_plastic_hard/p062 (e11).
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
A=human_study/al_v2/astm_f2077_mesh; H=scripts/3_cage_case/h55_astm_f2077.py
for d in p062_hz01 p062_hz01_plastic; do for t in compression shear45 torsion; do
  [ -f $A/$d/$t/resources.json ] && continue
  until python $H run $A/$d $t 4 > $A/$d/$t.run.log 2>&1; [ $? -ne 3 ]; do sleep 300; done
done; (cd ../biocage-evo && python methods/e11_astm.py $PWD/../biocage_simulation_test_oct2026/$A/$d $PWD/../biocage_simulation_test_oct2026/$A/$d/astm_result.json > /dev/null 2>&1); echo "$(date +%H:%M) $d done"; done
echo "ASTM MESH LANE DONE"
