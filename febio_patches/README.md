# FEBio 4.13 source patches used in the BIOCAGE human C3-C4 study

Base: FEBio v4.13 (commit 32ae206, "Prepared version 4.13 release"). Apply with
`git -C third_party/FEBio apply febio_patches/febio-4.13-biocage.patch`, then rebuild.

1. `FECore/PointCurve.cpp` - `binarySearch` throws `NANInSolutionDetected` on a NaN argument (was an out-of-bounds read /
   segfault when a spring length became NaN in a diverging line search); FEBio then retries the step.
2. `FEBioMech/FESolidSolver2.cpp` - a zero line-search step no longer rejects an iteration whose residual has dropped by
   >= 1e6 (frictional contact: converged states were discarded until the iteration limit).
3. `FEBioMech/FETiedElasticInterface.*` - new tied-elastic parameter `init_time`: the tie is formed at that time in the
   current configuration (default -1 = original behaviour).

Verification (human_study/DECISIONS.md): refined C3-C4 FSU (6 directions) identical to the unpatched build (<= 5e-8 mm);
Herron C0-C7 flexion identical at the final state within 2e-5; extension completes 100 % instead of stopping at 99.9 %.
