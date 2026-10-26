# Methodology comparison: simulator and slip-out check (evo), 2026-10-25

PI asks: (1) do we need CPU-bound FEBio? Find a GPU method that is credible and close to reality.
(2) Main goal = the cage must not slide out; find a smart check (e.g. hold it fixed, compute whether friction is enough).

## A. Slip-out check

| Method | What it does | Cost | Verdict |
|---|---|---|---|
| M1 real friction contact (FEBio sliding-elastic, mu 0.2 / 0.35) | simulates the actual sliding | hours; stick-slip stalls (DECISIONS 2026-10-21: why tied was adopted) | gold standard, too slow / fragile on CPU |
| M2 tied + force ratio (current, h15 Q47) | glue the cage, mu_force = sum shear / sum compression per face | free (post-processing) | **optimistic**: ignores the twist the face must also resist |
| M3 tied + friction limit (new, e02) | glue the cage, smallest mu for which a friction field with \|f_i\| <= mu P_i balances shear force AND twist (linear program; limit surface, Goyal 1991 / Lynch) | ~1 s per state | **pessimistic**: assumes all twist must be held by friction |

Check on solver: analytic cases (uniform disc, pure shear 0.300 / pure twist 0.302 vs exact 0.300).

**INVALID (2026-10-26): these runs had combined loading (h14 load-curve bug, al_v2/PHYSIO_INVALID_2026-10-26.md); the twist explanation below is wrong (it was the applied axial-rotation moment). To be redone on al_v2/physio_fix/.**

First results (tied FEBio physio runs, worst state per direction, worst of top / bottom face):

| case | flexion M2 / M3 | extension M2 / M3 | right LB M2 / M3 | left LB M2 / M3 |
|---|---|---|---|---|
| p062 (A axial mix d 0.50) | 0.35 / 0.75 | 0.49 / 1.27 | 0.52 / 1.79 | 0.48 / 2.15 |
| p063 (A axial mix d 0.65) | 0.32 / 0.70 | 0.46 / 1.24 | 0.50 / 1.83 | 0.44 / 1.97 |
| p000 (A axial mix d 1.20) | 0.23 / 0.23 | 0.16 / 0.27 | - | - |

Reading: the glued face carries up to ~1 N m of twist about the disc normal in lateral bending (cervical coupled axial
rotation driven by the facets). A glued cage must resist it; a real cage would partly spin. So:
- M3 <= mu  -> safe for sure (rigid-body sense); M2 > mu -> slips for sure; in between -> only a real friction simulation decides.
- Spinning lowers the resistance to translation (friction is shared between spin and slide), so a cage that spins in lateral
  bending / rotation may then walk out under the shear of flexion / extension (ratcheting over cycles). M2 alone cannot see this.
- Expulsion = net translation of the cage centre (agreed limit 1 mm relative slip), not spin.

=> M2 / M3 bracket is a cheap pre-filter. The deciding number must come from a real friction simulation, which is what the GPU solver below is for.

## B. Simulator

| Option | GPU | Credibility | Friction contact | Effort | Verdict |
|---|---|---|---|---|---|
| FEBio + cuDSS (current) | linear solve only (3.7x on solve, ~2.2x overall) | high (validated model, Herron 2020) | implicit, stalls | 0 | keep as reference (L2) |
| JAX-FEM (Xue 2023, Comput Phys Commun) | yes, differentiable | verified vs FEniCSx; no contact built in | must be added | high | not chosen: contact + facet + ligament all new |
| Commercial explicit (Abaqus/Explicit, LS-DYNA) | partly | very high | robust | licence | not available here |
| **Own GPU explicit solver (TLED) on the same FEBio mesh** | yes, whole model on GPU, many designs per GPU | method published + validated for soft tissue on GPU (Miller 2007 Commun Numer Meth Eng; Taylor 2008 IEEE TMI, NiftySim); credibility here by verification against FEBio, same mesh and materials | explicit penalty + Coulomb: no convergence failure, slip is computed directly | medium (~2-3 days) | **recommended** |

Why explicit: no global equation solve, every element / contact independent -> GPU friendly; frictional stick-slip
cannot "fail to converge" (the reason FEBio needed the tied shortcut); slow quasi-static loading + mass scaling + damping
is the standard way explicit codes do press-fit / push-out implant analyses.

The FSU model is small (27.8 k nodes, 114 k tets + ~3.6 k hexes, 5 ligament spring sets, 2 facet contacts); everything it
uses can be ported exactly: orthotropic linear (cortex), neo-Hookean (trabecular, facet cartilage), Holmes-Mow + fiber-exp-pow
(annulus), nonlinear springs with load curves (ligaments), frictionless facet contact.

### Credibility gates (ASME V&V 40 style; the GPU solver is used only after each passes)
1. Code checks: patch test, single-element material responses = FEBio to < 1 %; friction benchmarks (block on a plane: slips exactly at F = mu N; disc under twist).
2. Intact FSU: ROM under 1.5 N m in 6 directions vs FEBio FSU runs (< 5 %), facet force vs FEBio.
3. Cage case (p062, tied): ROM, cage axial force, face tractions, M2 / M3 vs the FEBio run (< 10 %).
4. Friction: a few real-friction cases in both codes (FEBio may stall; compare up to the stall) -> slip agreement.
5. Quasi-static check every run: kinetic energy < 1 % of strain energy; result unchanged when the loading is 2x slower (sampled).
Then: evo L1 = the GPU solver with real friction, the deciding number = cage centre translation (and mu sweep -> mu needed).
