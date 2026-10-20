# Human C3-C4 BIOCAGE study: design decisions log

Decisions agreed with the PI during the review sessions. Anything not listed is still **open** and must not be assumed.

## Reference paper
- Herron et al. 2020 J Biomech (pre-proof PDF supplied by PI). Validation = full C0-C7, C7 fixed, 1.5 N m pure moment at C0, nucleus 0.1 MPa pre-pressure;
  ROM vs Panjabi 2001 / Leahy 2007 (C3-C7 lumped, no single C3-C4 ROM); facet force C3-4 vs Patel 2017; IDP vs Kretzer 2012.
- 26 y.o. model = idealised, left-right symmetric (from Osth 2016, 167 cm / 59 kg); C3-C4 disc height 5.00 mm (pop. 3.56 +/- 1.06, Lu 1999), mid-disc area 168 mm2 (59/64 y.o.: 275/253 mm2).

## Geometry source
- Bone: FEBio cervical spine model, 26 y.o. female, `C34.feb` (Herron MR, Brockmeyer DL, Dailey AT, Ellis BJ, J Biomech 2020; simtk.org/projects/febiocervical).
  Raw zip: `human bone/26y.o.FModel-latest.zip`. Extracted STLs: `human bone/stl/` (script `scripts/h01_extract_febio.py`).
- Bone STLs keep only the outer shell (Herron cortex/trabecular meshes have duplicated interface nodes -> inner shell removed).
- Pig model and `C3.SLDPRT` / `C4.SLDPRT` are no longer used (SLDPRT deleted 2026-10-20).
- Measured native C3-C4 disc: AP 13.2 x LR 14.2 mm; mid-sagittal height posterior 4.1 / mid 5.4-5.5 / anterior 2.7 mm; sagittal endplate wedge ~7 deg, coronal 0 deg.

## Surgery
- ACDR (arthroplasty, motion preserving). Bony endplates preserved.
- Removed: ALL, anterior annulus, nucleus, cartilage endplates, **PLL (resected)**.
- Kept: lateral/posterior annulus remnants, facet capsules, posterior ligaments (as in FEBio model).
- Disc remnant (PI 2026-10-20): all disc tissue inside the cage footprint removed; outer ~1 mm annulus rim kept laterally and posteriorly;
  anterior rim removed over a **120 deg sector** (+/-60 deg about anterior, from the disc centre) = annulotomy / ALL side.
- Insertion (PI 2026-10-20), 3 FE steps: (1) distract C3 pot by d along disc-normal Z, no cage contact; (2) cage built to the distracted gap
  (zero gap / zero overlap), contacts activated; (3) C3 pot released -> clamp force from facets, annulus remnant, ligaments.

## Cage geometry
- Outline: endplate outline inset **1 mm**.
- Central window for biodisc: **60 %** of footprint area (mandatory).
- Lordosis: follow this model's native endplate angle (no separate value).
- Total construct height = native local gap + distraction **d**, d = **0.5 / 1.0 / 1.5 mm** (uniform offset).
  Insertion modelled as: distract C3 by d, insert, release -> clamp force.
  If construct proves too soft, may increase base height, up to 2-3 extra iterations.
  "Too soft" (at mid materials, mid mu) = (a) load capacity < **1164 N** (Moroney 1988 JOR, max C4-5 compression) OR (b) height loss > **d/2** at 150 N.
  Note: extra height mainly raises clamp force; if (a) fails, remedy must be discussed with PI (height may not help).
- No lattice for now.
- Two designs compared:
  - **A**: cage surfaces contour-matched to bony endplates, **no pad**.
  - **B**: simple wedge cage + **flat soft pad** that conforms under load.
    Refined (PI 2026-10-20, Q37): B is a **generic planar cage placed between the uncinate processes**: footprint = A footprint
    clipped to |Y| <= 3.5 mm (68 % of A's area), window 60 % of B's own footprint, planar faces parallel to the least-squares
    endplate planes and touching (no penetration); remaining gaps (bottom mean 0.5 / max 0.9 mm, top 0.4 / 0.6 mm) close by pad deformation.
    Reason: C4 uncinate processes; a full-width plane would rest only on them (gap 1.4 / 2.1 mm).
  - Future option (not in this study): planar cage + **CT-customised variable-thickness pad** filling the gap (same footprint as A).

## Materials
- Hard: PLCL 85:15 (Corbion PURASORB PLC 8516). E low/mid/high = **250 / 400 / 900 MPa** (37 C wet lit. 379 +/- 132 MPa with filler, PMC9697335; prior 1100 MPa considered an overestimate).
- Soft: PLCL 50:50 elastomer. E low/mid/high = **1.5 / 4 / 12 MPa** (lit. 1.3-12 MPa; PMC8070679, Duan 2021 PMC8296602).
- Pad = soft material (same family -> no inner adhesive, per Michael).
- Sensitivity: full **3 x 3** hard x soft combinations (9 sets).
- Blend modulus vs hard fraction: **Duan 2021-shaped sigmoid** (soft-dominated below threshold, jump at threshold), end members scaled to our moduli; threshold = **20 / 30 / 40 %** hard fraction (sensitivity). Report must state this is an estimate from an analogous system and needs coupon validation (coupons planned, no data yet).
- Gradient direction: test all three: (i) axial (soft at endplate faces -> hard mid-height), (ii) radial (hard outer -> soft toward window), (iii) both. Must respect print resolution (0.4 mm nozzle, 0.2 mm layer).
- Fabrication undecided -> simulate **both**: (1) mixing nozzle = true blend, Duan sigmoid; (2) dual-nozzle interleave = discrete hard/soft lines, homogenised / explicitly resolved.
- Bone and other tissues: **FEBio original model values**.
- Bones **deformable**: C3/C4 cut from `C0C7.feb` (cortical orthotropic 8/8/12 GPa + trabecular neo-Hookean 100 MPa), not the rigid bodies of `C34.feb`.

- Thicknesses (fixed, no sensitivity): design-B pad **0.6 mm** per face (3 layers); axial transition **0.6 mm** per face (3 steps), rest 100 % hard (shrink transition where hard core too thin);
  radial transition **3 lines x 0.4 mm**: outer 100 % / middle 50 % / inner 0 % hard.
- Biodisc in window: **E = 0.03 MPa, nu = 0.45** (Lintz 2021 ch.2, as before).

## Validation result (PASSED, PI 2026-10-20)
- FEBio 4 conversion fix: sliding-elastic search_radius is relative in FEBio <= 3 and absolute in FEBio 4 -> 0.01 x 145.71 mm = 1.457 mm (else facets never engage).
  With it, Herron's C34.feb reproduces his log exactly (25 identical step times).
- C0-C7 vs Herron 26 y.o. (digitised, +/-2 deg): 18/22 within 10 %; C3-4 facet force ext/LB/AR 56.4/27.5/45.0 N vs 57/27/45 (<= 2 %);
  FE all within 2.2 %. Exceptions: LB C0-C1 +21 % (1.3 deg), AR C0-C1 -14 %, C1-C2 -11 %, C3-C7 +12 % (38.1 vs 34 deg; total C0-C7 AR -7 %;
  within the experimental spread of Herron Fig 4). flex/ext extension case stopped at 99.9 % load (1.497 N m); last converged state used.
  Full-model C3-C4 total ROM at 1.5 N m: FE 13.2, LB 7.8, AR 10.4 deg. Results: human_study/validation/results/.

## Model scope
- Validation first: full C0-C7 per Herron (C7 fixed, 1.5 N m at C0, NP 0.1 MPa); compare 26 y.o. moment-rotation (Fig 3), C3-C7 ROM (Fig 4), C3-4 facet force (Fig 5); pass = within **10 %** of Herron 26 y.o. (digitised, ~+/-1 deg reading error). (Proposed; PI did not object.)
- Implant simulations on **C3-C4 single segment with deformable bone**, after checking single segment vs full C0-C7 on one case.
- Generalisability: final best A and B re-run on **59 y.o. and 64 y.o.** models (PI to download zips).

- Dual-nozzle interleave modelling: **explicit lines** (0.2 mm mesh, 2 elements per 0.4 mm line); raster **0/90 deg alternating** per layer;
  hard/soft lines **perfectly bonded**; axial transition hard fraction from pad to core **25 % -> 50 % -> 75 % -> 100 %** (mixing nozzle: blend ratio; interleave: fraction of hard lines).

- Mesh (agreed): cage/pad hex **0.2 mm**; bone endplate locally refined to **0.5 mm** near cage, Herron mesh elsewhere;
  convergence study on one case: cage 0.4/0.2/0.1 mm x endplate 1.0/0.5/0.25 mm, accept if capacity and slip change < 5 %.
- Compression test: C4 base fixed, C3 top **displacement-controlled** quasi-static until an endpoint triggers (PI did not object).

- FSU check (intact, deformable bone, 5 mm potting, 1.5 N m pure moment) vs C3-C4 inside validated C0-C7: total ROM FE 13.0 vs 13.2 (-1.3 %),
  LB 8.2 vs 7.8 (+4.7 %), AR 10.35 vs 10.39 (-0.5 %); C3-4 facet force ext 59 vs 56 N (+5 %), LB 35.5 vs 27.5 N (+29 %), AR 40.6 vs 45 N (-10 %).
  File: human_study/fsu/fsu_vs_full.json. FSU runtime ~40-90 s per case (16 cores).
- Cage model (design A, ~218k equations), same run: CPU Pardiso 16 cores 41.6 min (solver 34.4) vs GPU cuDSS A100 + 16 cores 18.7 min (solver 12.9); identical results -> cage cases go to GPUs first.
- Thread scaling, FSU AR case (identical 188 iterations): 16 cores 54.4 s, 8 cores 59.1 s, 4 cores 75.9 s.

- Modelling details proposed by the analyst, PI did not object (2026-10-20): gradient 'both' = min(axial, radial) (softer wins);
  radial bands measured from the window edge (<0.4 mm 0 %, 0.4-0.8 mm 50 %, beyond 100 %); Poisson's ratio hard 0.35 / soft 0.45,
  linear in blend fraction; all cage materials neo-Hookean.
- Q38 (PI 2026-10-20): run the radial / both gradients as defined and let the results decide; respect real nozzle precision:
  wall = whole 0.4 mm perimeters (60 % window rounded to nearest count: A 3 perimeters = 1.2 mm, window ~60 %; B 2 perimeters = 0.8 mm,
  window ~66 %); radial bands = whole perimeters (innermost 0 %, next 50 %, rest 100 %); axial steps = whole 0.2 mm layers;
  interleave = contour-following perimeters, each all-hard/all-soft per layer, hard if (perimeter+layer) mod 4 < 4*phi.
- Cage damage: **post-processing only** (element counted damaged when its stress exceeds the local strength); no softening in the FE run (PI).

- Q39 (PI 2026-10-20): no cage-wall / annulus-remnant contact (remnant = disc hexes whose centroid is outside the footprint and
  outside the anterior 120 deg sector). Rim resistance to lateral/posterior cage motion ignored -> conservative for slip.
- Insertion implemented as: distract (t 0-1) -> insert + seat 0.1 mm with a statically determinate cage pin (t 1-2) -> release with
  all C3-pot reactions ramped to zero, cage in-plane hold (t 2-3) -> test (t 3-). Distraction of 1.0 mm needs ~1.1 kN (design A run).

## Interfaces
- Peripheral adhesive: **not modelled; friction only** (worst case).
- Friction mu: **uncertain parameter 0.2-0.5** (6th uncertain dim in active learning), one shared mu for hard cage and soft pad vs bone.

## Tests
- Load-bearing: slow quasi-static vertical compression applied through C3/C4, find max load.
  Monitor all four; capacity = first reached, report failure mode:
  (a) cage damaged volume > **15 %** (also report 10 % / 20 %);
  (b) endplate / bone failure (subsidence onset): strain-based (Morgan & Keaveny 2001): trabecular element yields if min principal strain < **-0.75 %** or max principal > **+0.70 %**;
      subsidence onset = yielded volume > **10 %** of trabecular bone within **3 mm** below the cage footprint (both C3 and C4);
  (c) construct height loss > **d** (distraction lost);
  (d) peak of force-displacement curve.
  Q40 (PI 2026-10-20): if the run stops (solver failure, typically soft layers squashed) before any endpoint, capacity is recorded as a
  LOWER BOUND (force at the last converged state) and annotated as **functional failure** with its state and time: time, displacement,
  force, height loss, peak compressive strain in the cage and the material group where it occurs. No extra numerical treatment.
  Strength (von Mises failure): hard PLCL 85:15 low/mid/high = **15 / 25 / 40 MPa** (no direct 37 C data; bracketed from PLLA 54.4 MPa, PLLA/PLCL75:25 44.2 MPa, prior 35 MPa est.);
  FDM inter-layer tensile = 0.8 x hard strength; soft PLCL 50:50 = **3 / 15 / 30 MPa**;
  blend strength = **linear** in hard fraction (Duan 2021: strength ~flat while modulus jumps);
  strength level is an **independent sensitivity dimension** (x3), not tied to modulus level.
- Slip test protocol:
  1. Insertion: distract C3 by d, insert, release -> record clamp force.
  2. **ISO 18192-1:2011** cervical motion as main test (verified against the standard text, Cornell-licensed copy supplied by PI; do NOT copy the PDF or its tables into the repo/report, cite parameters only):
     FE = 7.5 sin(2 pi t) deg; LB = 6 cos(2 pi t) deg (90 deg ahead of FE); AR = -4 cos(2 pi t) deg (180 deg out of phase with LB);
     axial load = 100 + 50 sin(2 pi t) N (in phase with FE); 1 Hz; moving frame, Euler sequence LB -> FE -> AR; cervical NOT inclined.
     Origin = **physiological C3-C4 instantaneous centre of rotation** (PI choice), used for all three rotations (sagittal ICR, on the midline; simplification to be stated in report).
     Location: **Anderst et al. 2013** (Spine 38:E594, Table 2, n=20 asymptomatic): +1.5 mm superior, 1.8 mm posterior of the C4 anatomic origin
     (mean of ant/post points of C4 sup/inf endplates), unscaled. Cross-check Amevo et al. 1991 (Clin Biomech 6:111; X 0.32, Y 0.52 normalised): differs 1.2 mm AP / 1.0 mm SI.
     On the 26 y.o. model: ICR = (23.19, 0, 75.02) mm (C34.feb frame); C4 body depth 13.0 mm, height 9.7 mm. Script `scripts/h03_icr.py`, figure `human_study/icr_c3c4.png`.
     C3-C4 is tilted ~17 deg forward (sagittal) in the CT frame.
- **Loading frame (PI: most physiological AND protocol-compliant)** = disc mid-plane frame: Z = normal to the bisector of C3 inferior and C4 superior endplates (superior),
  X = anterior in that plane, Y = left (ISO), origin = ICR. Compression along Z (= follower-load direction, Patwardhan 2000 Spine PMID 10851105;
  = device axis per ASTM F2077 for a wedge cage; = ISO Z, cervical not inclined). ISO rotations about X/Y/Z of this frame through the ICR.
  Values: X = (0.9527, 0, -0.3038), Z = (0.3038, 0, 0.9527); C3 inf endplate -20.7 deg, C4 sup -14.7 deg, wedge 6.1 deg, mid-plane -17.7 deg (CT frame).
  Script `scripts/h04_frame.py`, output `human_study/frame_c3c4.json`. Model is L/R symmetric, so the Y sign (anatomical left) does not change results. Annex A.3 recommends extra max-load / migration tests (supports x3 escalation).
  3. Upper limit: scale amplitudes x1.00, 1.25, 1.50 ... up to **x3.0** (step 0.25), stop at slip.
  4. Push-out (ASTM draft F04.25.02.02 style): 100 N preload, push cage to 3 mm / failure in **both directions**: posterior->anterior (standard, anterior opening) and anterior->posterior (safety, PLL resected, toward cord); compare Mobi-C 142+/-18 N, MOVE-C 202+/-8 N (100 N preload), Prodisc-C 304+/-30 N (45 N preload).
  - Slip threshold: **2 mm** (motion test), **3 mm** (push-out).
  - **3 full cycles** per level; cycle 1 settles contact, cycles 2-3 check ratcheting; if ratcheting, extrapolate per-cycle increment.
- Ranking: exclude configs with motion-test slip > 2 mm, then rank by load capacity.
- Test-matrix strategy: **active learning / surrogate-guided**.
  - Design variables: design A/B, gradient dir (3), fabrication (2), d. Uncertain params: E_hard, E_soft, strengths, blend threshold.
  - Objective: **robust** = must not slip over the whole material range, then maximise worst-material-case load capacity; also report material-averaged capacity.
  - Numeric params **continuous**: d 0.5-1.5 mm; E_hard 250-900 MPa, E_soft 1.5-12 MPa (log-scale sampling); strengths hard 15-40, soft 3-30 MPa; threshold 20-40 %.
  - Initial batch **48** (Sobol; 12 categorical combos x 4). Next batch size = **idle GPUs + cases the idle CPU cores can host** (PI 2026-10-20), hourly rescan.
  - Stop when any: **150** total points; best feasible capacity improves < 2 % for 3 consecutive batches; surrogate predictive uncertainty at best design < 5 %.
  - Every point runs **both** tests (slip = constraint, capacity = objective).
  - Surrogate: **Gaussian process** (BoTorch, mixed categorical kernel; constrained batch qEI).

## Visualisation (agreed)
- Per case: force-displacement curves, final state, interactive 3D HTML, internal stress slices, stress-evolution GIF, insertion clamp-pressure map,
  slip trajectory over ISO cycles (3-cycle accumulation), 3D yielded-bone (subsidence) map, push-out curve with Mobi-C / MOVE-C / Prodisc-C reference lines.
- Study level: validation vs Herron, active-learning progress, GP surrogate slices with CIs, final comparison (A vs B, gradients, fabrication, 26/59/64 y.o.).
- Summary report as a shareable web page.

## Compute
- Solver: **FEBio 4.13** (built from source, MIT) + custom **cuDSS GPU linear-solver plugin**. Hybrid scheduler: one case per idle GPU (cuDSS) and one case per 16 idle CPU cores (Pardiso), one shared queue.
  Benchmark (3D elasticity, 201,720 DOF): Pardiso 16 thr 7.9 s vs cuDSS A100 2.1 s (3.7x).
- CPU policy: rescan hourly; use only idle cores; **16 cores pinned per case**; always leave **>= 32 cores** for others.
  Update (PI, 2026-10-20): FEBio used only ~5.3 of 16 pinned cores on average. After the current validation batch, if no case's
  PEAK usage exceeds 8 cores -> switch to **8 cores per case**; then choose cores/case dynamically for maximum throughput
  (benchmark the real FSU/cage model at 4/8/16 threads; scheduler re-evaluates at each hourly rescan).
  Decision (PI, 2026-10-20, after FSU benchmark 16c 54 s / 8c 59 s / 4c 76 s): **dynamic cores per case = the option (4/8/16) that minimises
  the batch completion time** for the current number of cases and idle cores, ties -> fewer cores; re-benchmark on the cage model.
- Herron C34.feb converted to FEBio 4 format diverges at t = 1.93/2.0 (negative Jacobians) -> must reproduce the published intact-model results before adding the cage (first modelling step).
- Use any idle GPU on the node (as many as available).
- During runs, **re-scan every 1 h** for newly idle GPUs and add workers on them (current gpu_pool.py only checks at start -> must be extended). Idle = 1-min samples, **30-min mean util < 10 %** AND free memory >= **1.5 x single-case peak** (measure peak on one GPU first). **No yielding**: keep using a GPU even if others start on it (PI decision).

- Compute policy update (PI 2026-10-20): **grab every idle GPU and CPU resource, no reserve** ("盡量搶佔，不用保留，利用任何一分資源").
  Replaces the 32-free-core reserve and the 30-min GPU idle wait: CPU = any core <10 % busy and not pinned to my runs;
  GPU = any GPU with enough free memory. Runs go in tmux; errors are debugged/relaunched without waiting (PI: "模擬程序不要停，有錯就除錯").
  GPU copies of a case race the CPU run (dir suffix _gpu<N>); first to finish is used.
- **VOID (bug): the comparison below used a refined mesh in which ~half of the endplate/disc-attachment nodes were mapped to
  isolated gmsh size-field points (not connected to bone). h16 fixed 2026-10-20; old files in human_study/fsu/buggy_v1; re-run and re-ask PI.**
- Refined endplate bone (PI 2026-10-20, based on the buggy run): refined mesh + tied-elastic disc-to-endplate contact (h16/h17, C34_fsu_refined.feb).
  Intact C3-C4 total ROM at 1.5 N m, original FSU | refined+tie | refined no-tie | full C0-C7:
  FE 13.04 | 12.07 | 14.11 | 13.21 deg; LB 8.18 | 7.78 | 8.71 | 7.82; AR 10.35 | 10.17 | 10.78 | 10.39. Facet forces within 7 N.
  Refined+tie within 10 % of the full model in all modes (FE -8.6 %, extension alone -10.4 %); no-tie LB +11.4 % fails.
  Files: human_study/fsu/fsu_refined_vs_full.json, fsu_refined_notie_vs_full.json.
- Refined endplate bone, re-decided after the h16 bug fix (PI 2026-10-20): **tied-elastic disc-to-endplate** (physiological:
  the disc is bonded to the endplate over its whole surface). Validation of the fixed mesh (tie / no-tie) still running.
- Decision fallback rule (PI 2026-10-20): the analyst still asks the PI, but if the PI does not reply within a reasonable time
  (default 30 min), the analyst decides by priority: 1 matches reality / human physiology, 2 credible (literature/standard),
  3 the analyst's literature- or reasoning-based recommendation, 4 time-saving without losing much accuracy.
  Simulations are never paused waiting for an answer; every such decision is logged here, marked "auto (no reply)".
- Fixed refined FSU validated (2026-10-20): total ROM original | refined+tie | refined no-tie | full: FE 13.04 | 13.07 | 13.07 | 13.21;
  LB 8.18 | 8.19 | 8.19 | 7.82; AR 10.35 | 10.36 | 10.36 | 10.39 deg; facet forces within 0.3 N of the original FSU.
  -> refined+tie used for all cage models. Files: human_study/fsu/fsu_refined_vs_full.json, fsu_refined_notie_vs_full.json.
- Mesh convergence design — auto (no reply, asked 13:40, decided 14:10 by rule 4 "time-saving without much accuracy loss"):
  one-at-a-time, 5 cases: cage 0.4 / 0.2 / 0.1 mm at endplate 0.5 mm, and endplate 1.0 / 0.5 / 0.25 mm at cage 0.2 mm
  (the 4 extra full-grid cases all pair the 0.1 mm cage, ~1.5 M equations, CPU-only, hours each). Accept if capacity and
  slip change < 5 %. Cases: human_study/meshconv/. PI may overrule.
- Compute constraint found 2026-10-20: this account's processes share a **64 GiB cgroup memory limit**
  (system.slice/jupyter-alz.ee09.service memory.max) although the node has 1 TB; one OOM kill (0.1 mm cage case).
  CPU cage runs need ~6-8 GB host RAM, GPU runs ~3.3 GB -> GPUs preferred; scheduler checks memory headroom; CPU race copies
  are dropped when memory is short. The 0.1 mm cage case (~1.5 M equations) does not fit next to other runs.
- FEBio patch (2026-10-20): FECore/PointCurve.cpp binarySearch throws NANInSolutionDetected on a NaN argument (was a
  segfault: NaN spring length in a diverging line search -> size_t wrap-around). FEBio then retries the step with a smaller
  increment (its built-in path for NaN). Old library kept as cbuild/lib/libfecore.so.pre_nanpatch. Found on the 0.25 mm
  endplate mesh-convergence case (crashed 3x at t = 0.9 in the distraction step).
- Design A baseline on refined bone (2026-10-20): compression capacity lower bound 130 N (functional failure: 25 %-hard surface
  layer at -38 % strain, solver stop at 0.37 mm height loss; stiffness 503 N/mm); clamp 78 N, retained distraction 0.575 mm,
  slip after insertion 0.13 mm, posterior push-out peak 13.8 N at 0.27 mm then expulsion. ISO (penalty 1) stops at t~3.4 by
  inversion of the same soft surface layer. Testing contact penalty 0.3 / 0.1 for compression and ISO.
- Design A refined bone, anterior push-out (load on the anterior face, cage driven posteriorly): force rises slowly to 24.8 N at
  1.41 mm, then drops (21.8 N at 1.52 mm; run stalled in stick-slip and was stopped by h20). Posterior push-out: 13.8 N peak
  at 0.27 mm, then expulsion. Mesh-convergence cage 0.4 mm case stalled at release start (t 2.0, zero line step loop); re-run
  with line search off (lstol 0; changes the iteration path only, not the converged solution).
- Mesh convergence, cage level 0.4 mm proposed for removal (analyst, 14:50; asked PI, default after 30 min): the gradient steps are
  0.2 mm thick, so a 0.4 mm element cannot represent them (it changes the design, not only the discretisation); it also fails
  at the start of release (seat contact pressure peaks 15 MPa vs 1.6 MPa at 0.2 mm). Cage convergence judged on 0.2 vs 0.1 mm
  (0.1 mm runs on GPU 4: does not fit the 64 GiB host-RAM cap on CPU).
- ISO debugging (2026-10-20): penalty 1 -> soft surface layer inverts at t~3.39 (strain -40 % / +165 %); penalty 0.3 -> no
  inversion (strain -31 % / +26 %) but stick-slip zero-line-step loop at t 3.35. Next: penalty 0.3 + seg_up 3 (limits contact
  segment updates per step, standard remedy for frictional chatter); penalty 0.1 run still going (CPU).
- 0.1 mm cage (1.55 M equations) cannot run here: CPU and GPU+cuDSS-hybrid both exceed the 64 GiB account RAM cap (OOM kill),
  GPU-only cuDSS runs out of device memory. Replacement (analyst, auto by rule 4 unless PI objects): through-thickness refinement
  only, cage 0.2 mm in-plane x 0.1 mm in Z (51 layers, 117,861 hex) - Z is the direction of the 0.2 mm gradient steps and of the
  soft surface layer that governs capacity and ISO failure. Full 0.1 mm remains possible if the RAM cap is raised by the admin.
- seg_up 3 made ISO worse (fails at t 2.98 in release, negative Jacobians) -> dropped. Next: penalty 0.3 + augmented Lagrangian
  (laugon 1, tolerance 0.2, maxaug 10). Mesh convergence, endplate 1.0 vs 0.5 mm: capacity lower bound 127.4 vs 129.6 N (-1.7 %),
  clamp +0.6 %, retained distraction -0.2 %, stiffness +1.2 % (distraction force at 1 mm +13 %, not an endpoint).
- Contact penalty 0.1 is too soft (compression case): clamp 23.9 N (vs 78 N at penalty 1), retained distraction 0.27 mm (vs 0.575),
  stall at 20.5 N -> excessive cage-bone interpenetration, rejected; ISO penalty 0.1 run stopped. Penalty 0.3 pending; any penalty
  used must keep clamp / retained distraction within 5 % of penalty 1.
- Contact penalty sensitivity (compression, design A): penalty 1 -> clamp 78.1 N, retained 0.575 mm; penalty 0.3 -> 45.2 N,
  0.449 mm (-42 % / -22 %). Results are penalty-dependent -> running penalty 3 and augmented Lagrangian (penalty 0.3, aug tol 0.2)
  to find a penalty-independent answer before any design run.
- Mesh convergence, cage Z 0.1 mm (penalty 1): clamp 97.7 N (+25 % vs 0.2 mm), retained 0.614 mm (+7 %), stalls at 67 N.
  Consistent with auto-penalty scaling ~E/h (thinner elements -> stiffer contact) -> mesh convergence is confounded by the
  contact penalty; re-running Z 0.1 mm with augmented Lagrangian (penalty 0.3, tol 0.2) to separate the two.
- Penalty sweep (compression, design A, refined bone): clamp 23.9 / 45.2 / 78.1 / 115.0 N and retained distraction
  0.27 / 0.45 / 0.575 / 0.64 mm at penalty 0.1 / 0.3 / 1 / 3 -> not converged in penalty (interpenetration ~ same size as the
  real deformation of the soft surface layer). Penalty-independent answer needed: augmented Lagrangian (penalty 0.3 and 1, aug tol 0.2).
- Stiff penalties (10/30/100) failed at contact activation (t 1.0): the cage, sized for the nominal distraction d, overlaps the
  endplates because they separate by less than d under the ~1 kN distraction force (physical press fit). Fix (h21): ramp the
  seat-step contact penalty 1e-3 -> 1 x target over t 1-2 and seat lowering 0.02 mm (h14 'seat_mm'); runs now pass seating.
- Endplate mesh convergence (penalty 1, cage 0.2 mm) - 1.0 / 0.5 / 0.25 mm: clamp 78.6 / 78.1 / 77.3 N, retained distraction
  0.574 / 0.575 / 0.576 mm, stiffness 509 / 503 / 492 N/mm, max force at solver stop 127.4 / 129.6 / 134.1 N -> all < 5 % between
  0.5 and 0.25 mm => endplate 0.5 mm accepted (distraction force at 1 mm 1083 / 957 / 795 N is mesh-sensitive, not an endpoint).
- Stiff-penalty seating stalled (stick-slip: line search returns zero step; the tiny energy/displacement norms are an artefact
  of s = 0). Fix: frictionless seating (cage pinned in X-Y during seating), friction 0.35 from release on (h21).
- Penalty 10 (ramped, frictionless seating, seat 0.02 mm): clamp 150.1 N, retained distraction 0.678 mm; mean cage-endplate
  interpenetration at end of seating 0.001-0.0015 mm (max 0.02) vs 0.02 mm mean at penalty 1. Clamp is hypersensitive to retained
  distraction because the ligaments are very stiff at 0.6-0.7 mm (~1 kN/mm). Penalty 100 fails at release start. Convergence
  check pending: penalty 30 with identical seating (accept penalty 10 if clamp / retained distraction differ < 5 %).
- Per-step cage contacts (re-created at every step) made stiff-penalty runs jump at each step start (penalty 10 compression
  failed at t 3.0005, residual 9e6; penalty 30 failed in release). h14 now defaults to ONE persistent global cage contact:
  penalty x lc (0 during distraction, log ramp 1e-3 -> 1 during seating, 1 after), friction x lc (0 until t 2, mu from 2.05),
  seat 0.02 mm, penalty 10 default ('contact_mode': 'per_step' reproduces old cases). Penalty check: global 5 / 10 / 20.
- Global contact, penalty 5 / 10: clamp 132.5 / 150.3 N, retained distraction 0.661 / 0.679 mm (penalty-10 per-step gave 150.1 N:
  consistent). Assuming error ~ 1/penalty, extrapolated zero-penetration values: clamp ~168 N, retained ~0.697 mm (penalty 10 is
  ~11 % low on clamp). Penalty 5 compression reached 294 N before stopping (vs 130 N at penalty 1) -> capacity is also strongly
  penalty-dependent. Penalty 20 failed at friction onset (mu 0 -> 0.35 within t 2.00-2.05); now mu ramped over t 2.0-2.3
  ('mu_ramp'), re-running penalty 10 / 20 and the Z-0.1 mm cage with global contact.
- Global penalty 10 (old 0.05 friction ramp) failed at compression onset (t 3.029, 0.086 mm): the 25 %-hard surface layer is
  already at -41 % strain from the ~150 N clamp alone; stick-slip loop follows. Design-level observation for the PI: with
  near-non-penetrating contact the insertion clamp almost crushes the soft surface layer (E ~5.7 MPa).
- Penalty 20 fails in release even with the 0.3 friction ramp; global penalty-10 push_post fails at test start: in every
  stiff-contact run the solver stalls when the 25 %-hard surface layer reaches ~ -40 % strain (stick-slip, zero line step).
  Numerical remedy under test: cage materials as uncoupled neo-Hookean (Mooney-Rivlin c1 = mu/2, c2 = 0, k = K; same moduli)
  so FEBio uses the three-field hex formulation (h14 'cage_mat': 'uncoupled'); disc materials are coupled -> unaffected.
  If runs still stop, Q40 applies to every test (record lower bound + functional-failure state/time).
- FEBio patch 2 (2026-10-20, FEBioMech/FESolidSolver2.cpp): a zero line-search step no longer rejects an iteration whose
  residual has dropped >= 1e6 x (penalty-10 runs stalled at t 2.334 with residual 26 -> 2e-7 because s = 0 forced "not
  converged"). Old library kept as cbuild/lib/libfebiomech.so.pre_lspatch.
- With patch 2 + uncoupled (three-field) cage material + global contact penalty 10, design A runs past the test start:
  clamp 148.9 N (coupled material 150.3 N, -0.9 % -> material switch is equivalent), retained distraction 0.678 mm,
  slip after insertion 0.216 mm; compression already at 319 N (t 3.106) and continuing (was 130 N at penalty 1).
- 0.1 mm cage: PI emailed the server admin about raising the 64 GiB cap (2026-10-20); on hold until the reply.
  Meanwhile mesh convergence is re-run with the final contact settings (global penalty 10, uncoupled cage, FEBio patch 2):
  cage Z 0.1 mm, endplate 1.0 and 0.25 mm (queued in h19).
- Q41 capacity definition (PI 2026-10-20, "看軟層壓扁程度"): new compression endpoint (e) = >= 50 % of the cage elements touching
  the endplates (first / last element layer, biodisc excluded) at minimum principal strain < -30 %; read from the load curve,
  first-reached with (a)-(d); solver stop before any endpoint -> Q40 lower bound. Implemented in h15
  ('e_contact_layer_crush_50pct', 'contact_layer_crush_after_release'). Thresholds adjustable; all cases re-post-processable.
- Design A (refined bone, global penalty 10, uncoupled cage): capacity 217 N, mode (b) trabecular yield > 10 % at 0.19 mm;
  (a) cage damage 15 % at 358 N; (e) not reached (48 % at 319 N); contact-layer crush already 20 % after release (clamp 149 N).
  Penalty 5: no endpoint before solver stop -> lower bound 168 N.
- CORRECTION (2026-10-20, push direction labels): h14 'push_ant' prescribes the POSTERIOR wall nodes +X, i.e. drives the cage
  ANTERIORLY (toward the open, rim-free side); 'push_post' drives the cage POSTERIORLY (toward the canal; remnant rim present
  but not in contact per Q39 -> resistance underestimated, conservative). Earlier notes that called push_ant "cage driven
  posteriorly" are wrong: penalty-1 results = anterior push 24.8 N (rising, stalled at 1.5 mm), posterior push 13.8 N then
  expulsion at ~1.2 mm.
- Design A anterior push-out (global penalty 10, uncoupled cage): force still rising, 63.3 N at 0.48 mm when the solver stopped
  (Q40 lower bound >= 63 N, no expulsion yet; penalty 1 had given 24.8 N). Re-running with a 4x smaller push-step size.
- ISO with final settings (global penalty 10, uncoupled cage, patches): stops at t 3.25 (25 % of the ramp to the ISO start pose,
  LB ~1.5 deg / AR ~ -1 deg) by slow convergence (107 x max BFGS updates, 2 neg. Jacobians); clamp 149 N, slip 0.216 mm so far.
  Re-run with full Newton in the ISO step (max_ups 0, max_refs 50).
- Verification of the two FEBio source patches (2026-10-20, human_study/verify_patch): re-ran previously validated models with the
  patched build and compared with the original-build results.
  * Refined C3-C4 FSU, all 6 directions: identical step sequence (25 steps), final displacements differ <= 5e-8 mm (round-off);
    both builds terminate normally -> patches inactive when the original build converges.
  * Herron C0-C7 flexion: final state (t = 2.0) identical within 2e-5 relative (solver tolerance); the patched build skips a
    few step cut-backs, so intermediate time points differ.
  * Herron C0-C7 extension: original build stopped at 99.9 % load (accepted earlier); patched build completes 100 %. At the
    original's last time (t 1.9978) C0 rotation differs by 0.0013 rad (0.12 %).
  Conclusion: the patches do not change converged results; they only let runs continue where the original build stalled or
  crashed. To be disclosed in the report (FEBio 4.13 + 2 patches, rationale, this verification).
- Mesh convergence with final settings, endplate 1.0 vs 0.5 mm: clamp +1.6 %, retained -0.4 %, (a) cage damage -1.1 %, but
  (b) trabecular-yield endpoint 270.6 vs 217.4 N (+24 %) -> the bone-yield capacity is mesh-sensitive; 0.25 mm decides
  (if 0.5 vs 0.25 differ > 5 %, use 0.25 mm). Penalty 20 (uncoupled) and posterior push with 4x smaller steps stalled in
  zero-line-step loops -> stopped; penalty convergence to be judged from penalty 5 vs 10.
- DESIGN A baseline summary (refined bone, global penalty 10, uncoupled cage, FEBio patches; 2026-10-21):
  distraction force at 1 mm 957 N; clamp after release 149 N; retained distraction 0.678 mm; slip after insertion 0.216 mm;
  contact layer already 20 % crushed (< -30 %) after release. Compression capacity 217 N (b, trabecular yield; endplate-mesh
  sensitive, 0.25 mm check pending). Slip tests all stop by crushing of the 25 %-hard contact layer (Q40 annotation in h15
  'functional_failure_slip'): ISO at 25 % of the ramp to the start pose (LB ~1.5 deg, AR ~ -1 deg), slip 0.216 mm, layer min
  stretch 0.395; posterior push during the 100 N preload; anterior push >= 63 N at 0.48 mm. Design-level finding: the
  sub-threshold surface layer (phi 0.25 < theta 0.3 -> E ~5.7 MPa) is the weak point in every test.
- Q42 (PI 2026-10-21): soft PLCL 50:50 Poisson's ratio 0.49 (was 0.45); blend nu(phi) linear 0.35 -> 0.49 per hard fraction;
  biodisc unchanged (0.45). Basis: PLCL 50:50 is an elastomer (elongation at break 388-1974 %, Soft Matter 2020); real elastomers
  nu ~0.4995 at small strain; 0.49 avoids the near-0.5 instability, used with the three-field (mixed) hex formulation already
  adopted. No PLCL-specific measured nu found. All design-A / mesh-convergence / design-B runs with nu 0.45 are superseded.
- Q43 (PI 2026-10-21): keep neo-Hookean for both PLCLs (uncoupled form for the three-field formulation); report limitation:
  no material test data, large-compression stiffening may be underestimated (conservative); recalibrate and re-run the best
  designs if coupon compression data become available.
- PI 2026-10-21: before re-running everything with nu 0.49, compare ONE case (design A compression, nu 0.49 vs 0.45: clamp,
  retained distraction, contact-layer crush after release, capacity, max soft-layer strain). If all differ < 5 %, keep the
  nu-0.45 mesh-convergence conclusions and only use 0.49 for new runs; otherwise report the differences and decide re-runs.
- Q44 (PI 2026-10-21): soft-material Poisson's ratio back to 0.45. Comparison at the same state (t ~2.979, end of release),
  design A compression: retained distraction 0.6910 (nu 0.45) vs 0.6921 mm (nu 0.49), +0.16 %; C3 axial force 20.5 vs 18.0 N
  (still ramping). nu 0.49 did not reduce soft-layer crushing (min stretch 0.509, max 1.626: local squeeze + lateral bulge at
  endplate-edge contact) and all four nu-0.49 runs stopped at t 2.979 (release), whereas nu 0.45 runs pass release. -> soft-layer
  crushing is geometric (edge contact), not a compressibility artefact. nu-0.45 results (design A, mesh convergence) stand;
  report: nu 0.45 vs 0.49 changes results < 1 %.
- Q45 (PI 2026-10-21, screening simplification proposed by PI): cage PLCL materials (all phi) use the Gent model (uncoupled,
  three-field): G = E/(2(1+nu)), k = E/(3(1-2nu)), Jm = 0.7 -> same small-strain response as neo-Hookean, locks near ~40 %
  uniaxial compression (stiffness ~2x at 30 %), so the soft layers cannot be squashed into element inversion. Biodisc unchanged
  (uncoupled neo-Hookean). h14 default cage_mat = 'gent'. The contact-layer crush endpoint (50 % beyond -30 %) remains reachable.
- Endplate mesh convergence, final settings (penalty 10, uncoupled cage, nu 0.45) 1.0 / 0.5 / 0.25 mm: clamp 151.3 / 148.9 /
  146.9 N (-1.3 %), retained 0.675 / 0.678 / 0.686 mm (+1.2 %), (a) cage damage 15 % 353.6 / 357.7 / 352.5 N (-1.5 %) -> converged;
  (b) trabecular-yield 10 % 270.6 / 217.4 / 162.0 N -> NOT converged (contact-edge stress concentration sharpens with mesh).
  Q46 (PI 2026-10-21): screening (active learning) uses the 0.5 mm endplate mesh for all designs (fair relative comparison,
  bone-yield capacity absolute values mesh-dependent / high); the final best designs are re-run at 0.25 mm; report states it.
- Gent soft layers (Q45) stop the inversion, but every design-A Gent run stalls near the end of release (t ~2.95-2.96) in a
  frictional stick-slip loop (residual 0.58 -> 0.50, zero line step); line search off (lstol 0) fails earlier (t 2.31).
  Design B Gent: global instability at t 2.19 (10k negative Jacobians at once; suspected tipping of the narrow cage about its
  long axis once friction ramps) - deferred. Testing regularised friction: contact 'sliding-node-on-facet' with tangential
  stick penalty fric_penalty 1 / 10 / 100 (h14 contact_type 'node').
- FEBio patch 3 (2026-10-21, FEBioMech/FETiedElasticInterface.*): new tied-elastic parameter 'init_time' - the tie is formed
  at that time in the current configuration (default -1 = at activation, original behaviour). Verified: refined FSU flex_pos_y
  with the tied disc identical to the original build (26 records, max |diff| 5e-8). Old library kept (libfebiomech.so.pre_tiepatch).
- Screening interface option (h14 contact_type 'tied'): cage top <-> C3 bony endplate and cage bottom <-> C4 bony endplate,
  normal contact frictionless during distraction/seating, bonded (tied-elastic, init_time 2.0 = start of release) afterwards;
  slip risk then from friction demand |tau|/p vs mu in post-processing (pending PI choice A/B/C, default C).
- Q47 (PI 2026-10-21): screening uses the bonded cage-endplate interface (contact_type 'tied', from the start of release) and
  judges slip by FRICTION DEMAND: at each contact-layer point, required friction = |shear traction| / compressive normal
  traction; slip where demand > mu (and where the interface would be in tension = would separate); outputs slip-area fraction
  and global anti-slip safety factor SF = mu * sum(normal force) / |sum(shear force)| per face. PI: "only judging whether / how
  easily it slips (not mm) is good". Limitation accepted for now and to be written in Limitations + Future work: the bonded
  interface cannot separate, so in large ISO bending the side that would lift off is held -> cage stability somewhat
  overestimated; future option: separable contact and/or full frictional-contact verification of the final best designs.
- PI 2026-10-21: the main failure in the earlier physical tests was CAGE DISLOCATION (direction unknown; possibly rotation /
  tipping). -> dislocation is a primary simulation question: friction demand (slip) plus a TIPPING indicator in h15 for the
  bonded interface: tension (would-separate) area fraction and centre-of-pressure eccentricity per face (CoP offset / face
  half-extent; >= 1 means the net normal force acts at or beyond the edge -> rotation / lift-off). Design B's earlier global
  instability at release (narrow cage, suspected tipping) may reflect this physically; re-run B with the bonded interface.
- Q48 (PI 2026-10-21): active-learning objective = ANTI-DISLOCATION first, load capacity as a constraint. Dislocation metrics
  over the ISO protocol (bonded interface): minimum anti-slip safety factor, max slip-area fraction, tipping indicators
  (max centre-of-pressure eccentricity, max tension area fraction).
- Q49 (PI 2026-10-21, corrected - first answer was a mis-click): capacity constraint >= 150 N (ISO max axial load: the device must
  survive its own test load without failure). Design A baseline (0.5 mm endplate mesh) 217 N (bone-yield endpoint) -> passes.
- Q50 (PI 2026-10-21): three-stage dislocation study. (1) Screening with the bonded model; slip likelihood and INTENSITY from
  theory: safety factor SF = mu N / |T| (< 1 slips), excess shear |T| - mu N [N] (driving force beyond friction), slip-time
  fraction (share of the test with SF < 1), slip-area fraction, tipping (tension area, CoP eccentricity). (2) Feature analysis
  on the surrogate (importance + trend plots: which traits prevent dislocation). (3) Validate representative designs (best,
  worst, contrasts of key traits) with the full frictional sliding model (ranking check + slip in mm).
- Q51 (PI 2026-10-21, "even small dislocation is trouble in the cervical spine"): screening criterion = NO slip at any time of
  the ISO protocol (SF > 1 throughout, slip-time fraction 0, no tipping: CoP inside the face); passing designs ranked by the
  minimum SF margin (higher = further from slipping). Validation (full sliding model) dislocation threshold lowered from
  2 mm (Q13) to 1 mm relative cage-bone slip (well above the ~0.2 mm post-insertion settling).
- First bonded-interface ISO numbers (design A, Gent cage, t ~3.1 = 10 % of the ramp to the ISO start pose): per face normal
  185 / 184 N, net shear 14.2 / 7.0 N (bottom / top) -> SF 4.55 / 9.25, excess shear -50 / -58 N, no tension, CoP eccentricity
  0.21 / 0.17; local slip-area fraction 35 / 20 % (likely radial bulging of the soft layer, shear largely self-cancelling) ->
  dislocation judged on the global SF; local slip area reported as auxiliary. Clamp 199 N (bonded) vs 149 N (sliding).
  Bonded compression stopped at t 3.0055 (inversions) -> testing frictionless contact for the capacity test.
- Bonded-interface ISO, first A vs B comparison (Gent cage, 2026-10-21 03:45): A stops at 9 % of the ramp to the start pose
  (soft 25 % layer at the Gent lock, min stretch 0.559 -> functional failure = layer crushed, Q40/Q41), clamp 199 N, retained
  0.713 mm, min SF 4.44, no tension. B (0.6 mm 0 % pad, narrow) runs on (32 % of the ramp): clamp 48 N, retained 0.474 mm,
  min SF 2.53, tension (lift-off) area appearing (3 %), CoP eccentricity 0.18, no crush. Trade-off visible: softer/thicker
  surface layer -> no crushing but low clamp -> lower slip margin and onset of tipping.
- Screening model pieces confirmed (2026-10-21 04:30): bonded interface + Gent cage for BOTH tests. Design A: compression
  stops after only 32.8 N added beyond the 199 N clamp (soft 25 % layer at the Gent lock) -> capacity lower bound 33 N < 150 N;
  ISO completes 9 % of the ramp. Design B ISO stops at 34 % (0 % pad at the lock, min stretch 0.571); moments at the stop are
  physiological (A ~0.8-1.0 N m, B ~0.5 N m) -> soft surface layers crush under everyday loads (design weakness, not an
  over-severe protocol). For active learning, failures are scored continuously: ISO completion fraction before functional
  failure + min SF / tipping before failure. Frictionless compression abandoned (in-plane drift, no convergence).
  Cage mesh convergence (Z 0.1 mm) re-run with the screening model.
- Q52 (PI 2026-10-21): screening ISO (bonded, history-free hyperelastic model) runs ONE cycle per level, all 9 levels x1.00..x3.00
  (h14 'iso_cycles': 1); cycles 2-3 would repeat cycle 1 exactly in the bonded model. Validation (full sliding model) keeps
  3 cycles per level.
- 2026-10-21 ~04:24 the Jupyter service was stopped (restarted 04:48): every process incl. tmux died (z-mesh convergence runs lost
  after 2 min). PI: write checkpoints so interrupted runs need not restart from zero.
- Checkpointing (2026-10-21): runners (h06 CPU, h18 GPU) call FEBio with -dump=1 -dump_stride=5 (restart file <case>.dmp every
  5 converged time steps) and, if a case dir holds a .dmp and its log has no termination line, resume with 'febio4 -r <case>.dmp';
  the scheduler (h19) re-queues interrupted jobs on start. FEBio patch 4 (FEBioMech/FERigidSolidDomain.cpp +
  FEBioMechPlot.cpp): rigid domains now save/restore their material pointer on restart (it was null -> segfault when plotting
  stress after 'febio4 -r'), plus a null guard in the stress plot. Verified: refined FSU flex_pos_y killed (SIGKILL) mid-run and
  resumed -> final state identical to the uninterrupted run within 4e-7 (direct) / 7e-10 (via h06), plot complete (26 states).
- Cage mesh convergence with the screening model (design A, bonded, Gent; cage 0.2 mm vs Z 0.1 mm): clamp 198.9 / 205.7 N (+3.4 %),
  retained 0.713 / 0.717 mm (+0.6 %), ISO min SF 4.44 / 4.22 (-4.9 %), bottom SF 4.55 / 4.22 (-7.3 %); crush-timing metrics earlier
  with the finer mesh (crush after release 10 / 13 %, ISO completion 9 / 4 %, capacity lower bound 32.8 / 27.8 N). Design A fails
  the screening criteria with both meshes.
  Q53 (PI 2026-10-21): screening uses the 0.2 mm cage mesh (fair relative comparison, absolute SF ~5-10 % optimistic, crushing
  slightly late); the final best designs are re-run with Z 0.1 mm (together with the 0.25 mm endplate, Q46).
- Mesh convergence study complete for screening purposes -> next: active-learning setup.
- ACTIVE LEARNING started 2026-10-21 07:29 (scripts/6_active_learning/h22_active_learning.py; state human_study/al/points.json):
  * design: A/B x axial/radial/both x mix/interleave (12 combos) x d 0.5-1.5 mm; material inputs E_hard 250-900, E_soft 1.5-12 MPa
    (log), theta 0.20-0.40; post-processing worst cases: mu = 0.2 (range 0.2-0.5), strengths hard 15 / soft 3 MPa.
  * each point: ISO (bonded, Gent, 9 levels x1.00-x3.00, one cycle each = t 3 -> 13) + compression; meshes 0.2 mm cage / 0.5 mm
    endplate (Q46, Q53).
  * dislocation score y = ISO completion fraction before the first of: SF(mu 0.2) < 1, CoP eccentricity >= 1 (tipping),
    functional failure (solver stop / soft layer crushed); completing designs get y = 1 + 0.5 tanh(minSF - 1).
    capacity C = first compression endpoint force, else Q40 lower bound. Constraint C >= 150 N (Q49).
  * surrogates: two MixedSingleTaskGP (y, log C); candidates 12 combos x 21 d values; robust score = min over 64 Sobol material
    samples of (mean + 1 std) (optimistic-robust), feasibility by the same rule on log C; chosen designs simulated at their
    worst predicted material sample (max-min robust search); batch = (idle GPUs + 16-core CPU slots within memory) / 2 points.
  * initial 48 Sobol points (4 per combo); stop at 150 points or < 2 % change of the best robust feasible score over 3 batches.
  * Synthetic test: GP fit ~6 min per batch; recovers the planted trends and worst material corner.
