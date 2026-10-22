# FEBio 4.13 source patches used in the BIOCAGE human C3-C4 study (5 patches)

Base: FEBio v4.13 (commit 32ae206, "Prepared version 4.13 release"). Apply with
`git -C third_party/FEBio apply febio_patches/febio-4.13-biocage.patch`, then rebuild.

1. `FECore/PointCurve.cpp` - `binarySearch` throws `NANInSolutionDetected` on a NaN argument (was an out-of-bounds read /
   segfault when a spring length became NaN in a diverging line search); FEBio then retries the step.
2. `FEBioMech/FESolidSolver2.cpp` - a zero line-search step no longer rejects an iteration whose residual has dropped by
   >= 1e6 (frictional contact: converged states were discarded until the iteration limit).
3. `FEBioMech/FETiedElasticInterface.*` - new tied-elastic parameter `init_time`: the tie is formed at that time in the
   current configuration (default -1 = original behaviour).

4. `FEBioMech/FERigidSolidDomain.cpp`, `FEBioMech/FEBioMechPlot.cpp` - rigid domains save / restore their material pointer in
   restart files (was null after `febio4 -r` -> segfault when plotting stress); null guard in the stress plot. Needed for the
   checkpoint / resume used by the runners (`-dump=1 -dump_stride=5`, `febio4 -r case.dmp`).

5. `FEBioMech/FEPreStrainUncoupledElastic.*`, `FEBioMech/FEConstPrestrain.h` - the uncoupled prestrain wrapper applied the
   prestrain to the deviatoric part only, so a prestrain with det != 1 could change shape but never volume (target z 0.80
   gave z 0.862 and x, y +7.7 % on one hex). U / UJ / UJJ now use J * Jp, with Jp taken from the gradient's current ramp
   (5b; it was one evaluation late). Used by the 'expand' cage insertion (h14); no effect without prestrain.

Verification (human_study/DECISIONS.md): refined C3-C4 FSU (6 directions) identical to the unpatched build (<= 5e-8 mm);
Herron C0-C7 flexion identical at the final state within 2e-5; extension completes 100 % instead of stopping at 99.9 %. Patch 3 (default off) leaves the
tied disc unchanged (5e-8). Patch 4: an FSU run killed mid-way and resumed from its checkpoint ends identical to the
uninterrupted run (<= 4e-7). Patch 5: one-hex test z 0.800, x = y = 1.000 (also run by the preflight check, h24).
