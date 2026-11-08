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

6. `FEBioMech/FESlidingElasticInterface.*` (2026-11-06, separate file `febio-4.13-biocage-patch6-stick-memory.patch`, built into
   `third_party/FEBio/cbuild_fric/`, NOT in the production binary `cbuild/`): new sliding-elastic parameter `stick_memory` (default 0 =
   original behaviour). With 1: (a) an integration point that ended the last converged increment in stick keeps its stick point
   (original FEBio copied the fresh projection at every increment start, so a sticking point lost its elastic tangential offset each
   increment and the body crept by ~ t_s / eps per increment under constant load: cage drift proportional to the increment count at a
   fixed angle, 0.05-0.46 mm; block 0.015 mm per increment at E 10 MPa); (b) a point that slipped is re-anchored on the friction cone
   (return mapping); (c) the slip direction is the trial tangential traction direction instead of the incremental kinematic direction
   (which is noise when nothing moves); (d) the stiffness of a return-mapped slipping point is the elastoplastic Coulomb tangent.
   Block test (gpufe/verify/v17f_block_patch.py, results/gpufe_verify/v2/v17f_block_patch.json): hold creep <= 5e-7 mm in every
   converged case (production binary 0.0019-0.603 mm, proportional to increments); at 0.9 of the friction limit three fixed-step
   cases with a coarse load ramp do not converge (the deck has no auto stepper), one does.

7. `FEBioMech/FESlidingElasticInterface.*`, `FECore/CompactUnSymmMatrix.cpp` (2026-11-07/08, in the same patch file as 6, built into
   `cbuild_fric/` only): (a) `stick_memory` is no longer an input-file parameter - FEBio refuses a restart dump whose parameter count
   differs from the binary's (`FEParamContainer::Serialize`), so the sliding-elastic list is kept identical to 4.13 and production
   checkpoints (t 3.5 states of the friction runs) load in the patched build; the pilot options come from the environment, frictional
   interfaces only, applied in `Init()` and on dump loading: `BIOCAGE_STICK_MEMORY=1`, `BIOCAGE_CAGE_LAUGON=<tol>[,<maxaug>]`
   (augmented Lagrangian, minaug 1). (b) With stick memory the frozen-status branch of `ContactTraction` no longer replaces the
   current secondary element by the anchor element (that wrote the contact stiffness outside the sparse profile), and
   `BuildMatrixProfile` also adds the anchor element's couplings. (c) `CRSSparseMatrix::add` reports a column that is absent from the
   row's profile on stderr and drops it instead of bisecting for ever (FEBio 4.13 hangs there; n0 = k, n1 = k + 1). Verification:
   control restart (options off) reproduces the production hold drift (p062 +0.057 vs +0.059 mm; p139 0.0030 vs 0.0025 mm per
   increment); stick memory: coarse hold drift 0.005-0.010 mm (controls 0.057-0.125), DECISIONS 2026-11-08 01:40.
   (d) 2026-11-09 patch 7b (logging only, same patch file): `Init()` / `Serialize()` run before FEBio opens the `-o` log, so the
   patch-7 lines never appeared in a restart window's `case.log`; the frictional interface now writes the env settings in effect
   once more at its first `Update()` (flag `m_benvlogged`): `BIOCAGE patch 7: interface '<name>': stick_memory = 1, laugon = 0,
   atol = ... (env settings in effect, logged at the first update)`. h37 R15 requires this line in every physio_fric5 window log and
   pins the library hash (libfebiomech.so sha256 be7b357f..., built 2026-11-09 06:13).
