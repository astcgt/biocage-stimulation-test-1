#!/bin/bash
# PI 2026-11-20 decision 8 = 乙, extended from the p062 trial to every design of the elastic ASTM batch (授權自行決定): hard phase elastoplastic
# (h55 WE 0.02 SCOPE hard, D 1.0 mm), same source case as human_study/al_v2/astm_f2077/<p>/astm.json; one design at a time, 4 cores per test
# (the account CPU quota is 32 cores, shared with the mu 0.3 reruns and the 3-cycle numerical check). p062 bound: WE 0 (perfectly plastic).
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
A=human_study/al_v2; H=scripts/3_cage_case/h55_astm_f2077.py
one() {  # <out> <src> <WE>
  [ -f $1/torsion/resources.json ] && return
  [ -f $1/astm.json ] || python $H build $1 $2 1.0 10 $3 hard || return
  for t in compression shear45 torsion; do
    [ -f $1/$t/resources.json ] && continue
    until python $H run $1 $t 4 > $1/$t.run.log 2>&1; [ $? -ne 3 ]; do sleep 300; done
  done
  (cd ../biocage-evo && python methods/e11_astm.py $PWD/../biocage_simulation_test_oct2026/$1 $PWD/../biocage_simulation_test_oct2026/$1/astm_result.json > /dev/null 2>&1)
  echo "$(date +%H:%M) $1 done"
}
one $A/astm_f2077_plastic_perfect/p062 $A/physio_fric5r/p062 0
for d in $A/astm_f2077/p*/; do
  p=$(basename $d); src=$(python3 -c "import json;print(json.load(open('$d/astm.json'))['source'])" 2>/dev/null) || continue
  one $A/astm_f2077_plastic_hard/$p $src 0.02
done
echo "ASTM PLASTIC LANE DONE"
