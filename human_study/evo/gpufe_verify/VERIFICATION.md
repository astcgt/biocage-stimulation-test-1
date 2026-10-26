# GPU explicit solver (scripts/7_evo/gpufe) - credibility record

Gate plan: human_study/evo/METHODS_COMPARISON.md. Each gate script writes its JSON report next to this file.
Formulas were transcribed from the FEBio 4 source in third_party/FEBio (FEOrthoElastic, FENeoHookean, FEHolmesMow,
FEFiberExpPow, FEGentMaterial, FEPreStrainUncoupledElastic + FEConstPrestrainGradient, FE3FieldElasticSolidDomain,
FENonlinearSpring, PointCurve SMOOTH, FEContactInterface::AutoPenalty, FESlidingElasticInterface::ContactTraction).

| Gate | What | Result (2026-10-26) |
|---|---|---|
| 1 patch | homogeneous general F on every node, element Cauchy stress + nodal reactions vs FEBio 4, same input | PASS: neo hex / neo tet / orthotropic cortex tet / Holmes-Mow + 2 fibers hex / uncoupled prestrain Gent hex (three-field, ramped F0) all < 5e-12; nonlinear spring with smooth ligament curve 5e-8 |
| 1b equilibrium | clamped bar with prescribed lift, every node displacement + reaction vs FEBio Newton | PASS: neo 2.8e-8, Gent prestrain 1.5e-7, orthotropic tets 1.5e-6 (275-1225 DR iterations per increment, 0.4-2 s) |
| 1c friction | block pressed then dragged on a block, Fx / Fz while sliding vs Coulomb | PASS: mu 0.2 -> 0.198-0.200 (1.1 %), mu 0.5 -> 0.496-0.499 (0.8 %); stick below the limit; normal force within ~2 % of FEBio. FEBio itself reached only 0.457 at mu 0.5 and skipped output times (auto step cuts) |
| 2 intact FSU | ROM 6 directions + facet force vs FEBio refined FSU runs | running |
| 3 cage case | p062 tied physio vs FEBio | pending |
| 4 friction cases | real-friction cage runs | pending |
| 5 quasi-static | KE / loading-rate checks | pending |

Sign convention: FEBio node reactions = minus the internal force (checked in gate 1).
