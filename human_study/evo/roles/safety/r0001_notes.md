# Safety guard r0001 - working notes (hand calculations, evidence)

Python execution was not permitted for this role in r0001; `s01_geometry.py` (same folder) is prepared to recompute the
geometry numbers below from the FSU mesh and should be run by the verifier / integrator. Until then the geometry numbers
are READ FROM THE FIGURE `human_study/fsu/endplates_footprint.png` (reading error ~ +/-0.2 mm) or taken from DECISIONS.md.

## G1 Geometry (disc mid-plane frame, X anterior, Y left)
- disc outline: X -6.4 .. 5.0, Y +/-6.7 (figure). DECISIONS.md:15 native disc AP 13.2 x LR 14.2 mm (different measure).
- footprint (inset 1 mm, red line): X -5.5 .. 4.0, Y +/-5.7 (figure).
- native gap: posterior 4.1 / mid 5.4-5.5 / anterior 2.7 mm (DECISIONS.md:15); inside the footprint: anterior edge ~3.0,
  posterior-central ~5.5 (figure, right panel).
- posterior footprint edge is 1.0 mm anterior of the posterior disc outline (= posterior vertebral wall, front of the canal);
  PLL resected (DECISIONS.md:19) -> only 1 mm of bone-free margin between cage and dura.
- anterior opening (120 deg annulotomy sector, DECISIONS.md:22): chord estimated from the figure ~11 mm (+/-0.5) vs max
  footprint width 11.4 mm -> the "Y width <= anterior opening" rule is close to non-binding; unverified until s01 runs.

## G2 S2 insertion from anterior - required height reduction
The part must pass the narrowest (anterior) gap while its tallest section matches the posterior-central gap:
ratio = (h_ant + d) / (h_max + d), DECISIONS.md:15 heights (2.7, 5.5):
- d 0.5: 3.2 / 6.0 = 0.53 ; d 1.0: 3.7 / 6.5 = 0.57 ; d 1.5: 4.2 / 7.0 = 0.60
- with the footprint values (3.0, 5.5): 0.58 / 0.62 / 0.64
=> a full-height contour-matched part needs 36-47 % height reduction, not 20 % (shrink 0.8), unless the surgeon distracts
   further during insertion (insertion distraction d_ins > d) or the anterior lip is removed.
Material limit (elastic strain ~ strength / modulus, DECISIONS.md:46,115): hard PLCL 15/900 = 1.7 %, 25/400 = 6.3 %,
40/250 = 16 %. 20 % compression of hard regions exceeds the elastic limit in every material set -> permanent deformation /
cracking. Only the soft 50:50 elastomer can recover 20 %.
Model check: h14 'expand' insertion (scripts/3_cage_case/h14_build_case.py:41,47,355-358) shrinks the cage's NATURAL shape
through a load-curve ramp (stress-free shape change), then lets it grow back; the sliding path and the insertion strain are
not simulated -> S2 is currently not measured by any simulation.

## G3 S6 / S8 endplate strength
- Schroder et al. 2006 Cent Eur Neurosurg 67:188: endplate failure 1084 +/- 314 N (340-1550) over 97.79 mm2 cage -> 10.47 MPa mean.
- Cheng et al. 2007 Spine (10.1097/BRS.0b013e31811ece5a), 3 mm flat indenter (area pi*1.5^2 = 7.07 mm2):
  intact 106 N -> 15.0 MPa; mean - 1 SD (20 N) -> 2.8 MPa; burred 1 mm 59 N -> 8.3 MPa; posterior stronger than anterior.
- 1164 N (S6) > mean endplate failure 1084 N -> at the S6 load the bone itself is at its limit; the v2 compression runs
  ended by bone yield at 230-277 N (DECISIONS.md:584-586). => S6 must be judged on CAGE failure; bone is S8.
- recommended S8 default: peak 1 mm2-averaged pressure <= 5 MPa at the physiological states (~ half of 10.5 MPa,
  ~ burred-endplate 8.3 MPa / 1.7), range 3-10 MPa; plus the FEBio strain criterion (DECISIONS.md:108-109) at L2.

## G4 Loads
- Moroney, Schultz, Miller 1988 J Orthop Res 6:713 (Analysis and measurement of neck loads): C4-5 compression up to 1164 N,
  AP shear up to 135 N, lateral shear up to 125 N (mean, max voluntary efforts). Shear / compression = 135 / 1164 = 0.12.
- NOT Moroney 1988 J Biomech 21:769 (load-displacement, compression only to 73.6 N) - the citation in PLAN.md S6 should
  name the J Orthop Res paper (DECISIONS.md:33 does say JOR -> consistent).
- Push-out with 100 N preload, friction only, two faces: 2 * mu * 100 = 40 N (mu 0.2) / 70 N (mu 0.35) + clamp share,
  vs clinical comparators Mobi-C 142 N / MOVE-C 202 N (DECISIONS.md:135, keeled / toothed devices).

## G5 Ratcheting
Neck motion cycles over a maturation period are many (count unverified; PI to give period). 3 simulated cycles
(DECISIONS.md:729) can only show the per-cycle increment; e.g. 1 um / cycle x 1e5 cycles = 100 mm -> the increment must be
extrapolated over the maturation period, not judged after 3 cycles.

## G6 Implementation
No `constraints.py` exists in the repository (glob **/constraints.py outside third_party: none, 2026-10-26); GOVERNANCE.md:23
assigns it to the safety guard, who may not write code outside roles/safety -> integrator must create it from the spec.
