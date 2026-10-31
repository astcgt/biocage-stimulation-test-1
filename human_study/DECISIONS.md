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
- 2026-10-21 08:40: the admin raised the account memory cap from 64 to 128 GiB (online, no restart; all runs survived). CPU cores
  are now the binding resource. The full 0.1 mm cage mesh-convergence case (screening model, compression, ~1.5 M equations,
  CPU-only) is queued last (after the active-learning batch) as an in-plane resolution check complementing Q53.
- 2026-10-22 00:10: memory (not cores) was binding: 15 runs used ~108 of 128 GiB, 43 GB of it the 0.1 mm meshconv case (stuck
  retrying t=1.68 for 2.5 h). Paused it (checkpoint 10-21 20:20) and requeued it behind AL batch 0, as planned above. FEBio runs
  average ~2.5 busy cores, so AL jobs now pin 8 cores instead of 16 (h22 JOB_CORES) to fit more runs at once.
- 2026-10-22 (PI: "implement" async AL, memory-aware scheduling, multi-fidelity):
  * Async AL (h22, after Alvi et al. 2019 PLAyBOOK): no waiting for a whole batch; when < 2 AL jobs wait in the queue the loop
    proposes points for the free slots, keeping proposals away (same combo, |d_u| < 0.15) from points still running. Stop rule
    unchanged in spirit: < 2 % change of the best robust feasible score over 3 checkpoints taken every 8 new results.
  * Scheduler (h19): first-fit backfill (a later job may start when the oldest does not fit; a head job waiting > 12 h gets a
    reservation); up to 3 of my jobs per GPU while it averages < 50 % utilisation (GPU runs need ~3.3 GB host RAM vs 5-8 GB on
    CPU); GPU launches also require idle cores; jobs that survive a scheduler restart are archived when their FEBio ends.
  * Multi-fidelity (PI choice): low fidelity = endplate 1.0 mm (convergence: clamp / retention / cage damage within ~1-2 % of
    0.5 mm; bone-yield capacity not converged -> C may be biased, the multi-fidelity GP learns the offset). High fidelity = the
    current screening model. Pilot first: points 37, 41, 10 re-run at 1.0 mm (human_study/al/mf_pilot) to measure the time saved
    and the y / C offset before the multi-fidelity GP and cost-aware acquisition are switched on.
  * Noted: all 15 finished points end in ERROR termination; 11 stop at the start of ISO (t 3.0-3.6, soft-layer crush, as
    agreed = functional failure), but 4 (p011, p031, p035, p036) stop during insertion/release (t 1.0-1.6) and score y = 0,
    C = 0 without the test having started -> to discuss with the PI.
- 2026-10-22 02:50 insertion failures explained: during distraction the stretched annulus / ligaments pull the C4 endplate up
  into the cage space (max rise 0.005 mm at d 0.5, 0.10-0.14 at d 1.0-1.1, 0.20-0.31 at d 1.24-1.48; C3 side not logged).
  h12 builds the cage on the undeformed endplates + d, so at contact activation (t = 1) the cage overlaps the bone by up to
  ~0.3 mm -> inversions (p011, p031, p035, p036 fail at t 1.0-1.6; p000, p003, p004, p015 crawl). Smaller d also carries a
  hidden press fit (<= 0.14 mm) that grows with d.
  PI proposal: shrink the cage, insert, let it spring back. h14 insert_mode 'expand': natural cage height ramps to 0.8 x design
  during distraction (prestrain gradient, stress-free, pinned on its mid plane) and back to 1.0 during seating; full contact
  penalty from t = 1 (no overlap), seat lowering 0. Final state = cage at design height pressed into the real gap (same as
  compress-then-release for this history-free model, without passing through a crushed state).
  FEBio patch 5 (FEPreStrainUncoupledElastic): the stock uncoupled prestrain wrapper applied Fp to the deviatoric part only, so
  volume could not change (single-hex test: target z 0.80 gave z 0.862 and x, y +7.7 %; the first expand runs bulged
  sideways into the endplate rims and failed at t 1.009). Patched U/UJ/UJJ to use J*Jp -> hex test z 0.800, x = y = 1.000.
  Identical to the stock build whenever no prestrain is used. Old lib kept as libfebiomech.so.pre_prestrainpatch.
- Multi-fidelity pilot (endplate 1.0 vs 0.5 mm, same points): p037 y 0.013 -> 0.017, C 272 -> 328 N (bone-yield endpoint,
  +21 %, as in the convergence study), clamp 63.6 -> 64.0 N; p010 y 0.062 -> 0.056, C 71 -> 72 N (cage damage), clamp 29.1 ->
  29.1 N. Wall time ~1-3x shorter (iso 0.6-1.2 h vs 3.8-5.1 h, but the old runs shared busier CPUs). p041 pending.
- 2026-10-22 03:45 expand test, run 2 (patched lib): p037 (d 0.59) passes distraction and is into seating (t 1.41) with no
  failed step; p036 (d 1.48) blew up during distraction (t 0.66, up to 2909 inverted elements, no contact active). Cause: the
  3 seating pins (+-1 mm from the footprint centre) all lie in the window, i.e. in the 0.03 MPa biodisc, so the free,
  shrinking cage was held only by jelly. Expand-mode pins moved to cage-wall nodes (left / right / front, mid plane); p036
  rebuilt and restarted 03:47 (p037 left running for comparison).
  NOTE for the PI: the old (overlap) mode uses the same centre-based picks for the seating pins and the release in-plane hold
  ('cage_hold'), so in all AL runs these constraints act on biodisc nodes, not on the cage; the bonded (tied) interface holds
  the cage from release on, so the effect is probably small, but it should be fixed in the re-run.
- 2026-10-22 04:30 expand test p037 (run 2, old centre pins) failed at t 1.82: FEBio -output_negative_jacobians -> all 240
  inverted elements are biodisc (window filler) elements, i.e. the jelly-pin problem again; rebuilt with the wall pins and
  restarted. p036 with wall pins passes its old blow-up point (t 0.66). Third test added: p011 ISO (design B, d 1.43, failed
  at t 1.27 with the old insertion).
- Stuck old-mode cases (p000, p003, p004, p015, p038; t 1.3-1.9, dt 5e-4-3e-3, 14-31 failed steps, inversions): soft contact
  layers are NOT crushed at their last converged state (min principal Lagrange strain -0.04 to -0.13; p000 -0.30 at the
  crush threshold) -> not the agreed physical functional failure but a numerical stall from the insertion overlap.
  Plan (PI 2026-10-22): debug expand until the test cases pass all stages, then switch every case to expand.
- 2026-10-22 04:50 PREFLIGHT (PI: check model and run conditions before simulating): scripts/5_compute/h24_preflight.py +
  human_study/current_settings.json. A case may run only if a rebuild with the current h14 is byte-identical, its params match
  the current settings for its class, pins / prestrain / curves are as intended, FEBio passes the patch-5 one-hex test, and
  any checkpoint comes from the same case.feb (launched_feb.sha256 written by h06 / h18 at a fresh start). h19 launches only
  preflight-valid jobs; daemon in tmux biocage_preflight (watchdog-managed); failures -> queue/failed/, log preflight.log.
- Error census (55 terminated AL runs, ALL ended in ERROR, none NORMAL): 38 at the very start of the test step (t 3.00-3.6),
  17 during insertion (overlap, see above). Replays from checkpoints with -output_negative_jacobians: p021_compress (B): all
  119 inverted elements are biodisc (0.03 MPa window filler sharing nodes with the cage wall); p041_iso (A): 31 soft (0 %)
  interleave lines + 9 hard elements, mostly inner layers (material distortion, closer to the agreed functional failure).
  p039, p042 replays pending. Biodisc handling put to the PI: (a) one ring smaller + contact, (b) drop from screening
  (load share < ~1 N vs 30-300 N clamp, identical for all designs), (c) keep.
- FEBio patch 5b: the uncoupled prestrain volumetric term took Jp from the previous stress evaluation (one increment late at
  each step start -> pressure mismatch ~K ln(1.025) in the hard core; p036, E_hard/E_soft 380x, failed in distraction even
  with wall pins). FEConstPrestrainGradient::CurrentJp() now gives the current det for a constant F0. One-hex test still
  z 0.800, x = y = 1.000. Expand tests p036, p037, p011 restarted 05:05 on 5b via the preflight-gated launcher.
- 2026-10-22 05:20 PI: screening model WITHOUT the biodisc (h14 'biodisc': False; its nodes fixed, its faces removed from the
  contact surfaces); applied to the expand tests now (settings class expand_test), to the AL with the full switch.
- Solver-work census (all AL logs, stiffness factorizations): distraction 5 %, insertion 56 % (33 % on failed attempts),
  release 18 %, test 21 %; ~80 % of wall time is the linear solver. PI-approved order, each tested alone against p037
  (expand, no biodisc) and adopted only if the results barely change, then the full switch and re-run:
    1. release step max dt 0.02 -> 0.1 (h14 'release_dtmax'; path-independent screening model, only the end state matters)
    2. symmetric contact stiffness (h14 'contact_symmetric': 1; frictionless normal contact in the tied screening model)
    3. dtol 0.001 -> 0.005 (h14 'dtol')
  Options added with defaults = current settings (rebuilds of AL and expand cases byte-identical).
- 2026-10-22 ~05:17-11:33 every process (incl. tmux, watchdog, the 50-min report schedule) was killed again (Jupyter service stop; host not rebooted). Recovered 11:33: watchdog restarted all daemons, interrupted AL jobs requeued to resume from checkpoints (after preflight), expand tests restarted fresh. ~6 h lost.
- 2026-10-22 12:30 expand tests (patch 5b, wall pins, no biodisc), all three ended in ERROR:
  * p037 (A axial interleave, d 0.59) passed distraction, insertion and release for the first time and stopped early in
    compression (t 3.10, as most old runs). Old vs expand: distraction force 81.4 / 81.5 N, clamp after release 63.6 / 103.0 N
    (+62 %), retained 0.53 / 0.61 mm, capacity (bone yield) 272 / 251 N. The clamp change must be explained before any switch;
    variant p037 expand WITH biodisc running (human_study/al/expand_variants/p037bio_compress) to separate the biodisc effect.
  * Inverted elements (FEBio -output_negative_jacobians): p037 70 % soft (0 %) interleave lines + 24 % hard, mostly inner
    layers; p011 ISO (B, d 1.43) failed at t 1.98 (end of the spring-back, i.e. when the press fit builds) with 82 % soft lines.
    -> with the biodisc gone, the dominant error is the explicit soft interleave lines.
  * p036 (d 1.48) failed in distraction (t 0.57-0.66): inverted elements are C3 cortical bone across the whole vertebra +
    disc/facet near the cage edge, not the cage; forces equal to the old run up to t 0.47; the old run also had distraction
    failures at t 0.47 / 0.82 but recovered -> large-d distraction is fragile in itself. h14 'distract_dt' option (default
    0.1, unchanged); p036 relaunched with 0.025.
  Open PI questions: cage height definition (nominal gap + d, so the press fit grows with d, vs. the real distracted gap) and
  how to treat soft-interleave-line inversion.
- 2026-10-22 13:25 human_study/al/HOLD_PROPOSALS: the async AL loop collects results but proposes no new points until the new screening model is validated (they would be built with the old model and re-run); batch 0 continues.
- 2026-10-22 14:20 speed-option variants of p037 (expand, no biodisc) started side by side, each one change vs the baseline expand_test/p037_compress: p037rel01 (release dtmax 0.1), p037sym (symmetric contact stiffness), p037dtol005 (dtol 0.005); human_study/al/expand_variants/. Batch 0 queue empty (30/48 done, 22 running).
- 2026-10-22 15:15 speed options vs baseline p037 (expand, no biodisc), up to the end of release (t 3):
  * clamp after release: base 102.998795 N; release_dtmax 0.1: 102.998795; symmetric contact: 102.998796; dtol 0.005:
    102.998797 (all within 1e-8 relative); capacity (bone yield) 250.527 / 250.529 / 250.522 N -> results unchanged.
  * stiffness factorizations to t 3: base 88 (release 53 steps); release_dtmax 0.1: 50 (release 15 steps, -43 %); symmetric:
    88 (benefit, if any, is time per factorization: pending wall-time comparison on equal load); dtol 0.005: 82.
  * expand_test/p036 (d 1.48, fine distraction) passed distraction but has been stuck at t 1.929 (end of the spring-back,
    press fit building, as p011) for ~1 h; p037bio (expand WITH biodisc) in release at t 2.75, no failed step, slower.
- 2026-10-22 16:10 p037 clamp decomposition: old (overlap insertion, biodisc) 63.6 N; expand + biodisc 103.03 N; expand without
  biodisc 103.00 N -> biodisc effect 0.03 %; the +62 % comes entirely from the insertion method. Suspected cause (not verified:
  the plotted 'contact gap' is 0 everywhere, i.e. positive gaps only): the old seating ran with a 1e-3..1e-1 penalty, so the
  cage could sink into the endplates before the tie formed at t 2, effectively shortening the cage.
- Speed options, wall time: all three variants ended in the usual early-compression ERROR, so total times are not comparable
  (ran under different load); symmetric contact and dtol 0.005 show no clear gain -> not adopted (simpler to keep defaults);
  release_dtmax 0.1 (-43 % factorizations to t 3, identical results) proposed for adoption.
- expand_test/p036 (d 1.48) stuck at t 1.93 (end of the spring-back) for 2.5 h; p011 failed at the same point -> large d means a
  large press fit with the nominal cage height (open PI question).
- 2026-10-22 17:10 AUTO (no reply since 12:35; PI fallback rule: physiological first): cage height = the REAL gap after
  distraction (surgeons size the cage with trial spacers after distracting), not the undeformed gap + d (press fit grows with
  d; p011 and p036 failed / stuck exactly when the press fit builds; old clamp also suspect). Implementation: gap library
  (scripts/3_cage_case/h25_gap_library.py) = distraction-only runs at d 0.5-1.5 step 0.1 (cage fixed, out of contact,
  distract_dt 0.025) recording the C3 / C4 endplate node displacements at t 1; h12 optional arg gaplib.npz builds the faces on
  the deformed endplates (linear in d; Endplates(disp=...)). Interleave soft-line inversion: option (c) (re-assess after the
  gap fix). release_dtmax 0.1: adopted for the new model (identical results, -43 % work); symmetric contact / dtol 0.005 not.
  Preflight now regenerates the cage mesh with the current h12 and compares the arrays (was: mtime rule).
- 2026-10-22 18:10 gap library done (11 distraction-only runs, all NORMAL, no failed step): gap loss (C3 drop + C4 rise, max)
  0.006 / 0.15 / 0.53 mm at d 0.5 / 1.0 / 1.5 (C3 and C4 deform about equally) = the old oversize of the nominal cage.
  New screening model under test (human_study/al/gap_test, settings class gap_test): cage on the real distracted gap (h12 +
  gaplib), expand insertion (shrink 0.8), no biodisc, wall pins, release_dtmax 0.1, distract_dt 0.025; tests p037 compress,
  p036 compress (d 1.48), p011 ISO (B, d 1.43). Old expand p036 (stuck 5.5 h at t 1.93) stopped.
- 2026-10-22 19:05 gap-model tests: p037 passes all preparation stages, clamp 102.8 N (expand 103.0; gap loss at d 0.59 only
  0.006 mm), capacity 249.6 N (bone yield), stops early in compression like before (1294 inverted: soft 0 % + hard lines).
  p036 (d 1.48) passes distraction + insertion + release for the first time (< 1 h), clamp after release 1135 N, cage damage
  15 % already reached -> physical overload, not a numerical artefact. p011 ISO (B, d 1.43) passes insertion, crushes its soft
  interleave lines in release (6018 inverted soft elements) under the large clamp.
  PLAUSIBILITY FLAG for the PI: distraction force at the end of distraction rises steeply with d: 55 / 81 / 484 / 898 / 1454 /
  4277 N at d 0.51 / 0.59 / 0.87 / 0.99 / 1.10 / 1.48 mm. The upper values look far above intraoperative distraction forces
  (to be checked against the literature) -> either the d range (Q?, 0.5-1.5 mm) is too large for this FSU or its tensile
  soft-tissue response is too stiff (ALL/PLL already removed). Needs a PI decision before the AL re-run.
- 2026-10-22 19:55 LITERATURE CHECK of the distraction stiffness (critical): cadaver C3-C4 axial distraction (intact disc)
  1.7 mm @ 44 N, 2.7 mm @ 89 N (Frank et al. 1996, intraoperative retractor technique); 12 cadavers ~2.1-2.4 mm @ 89 N
  (Neurosurgery 1996); disc-unit tensile failure ~569 N. This model (after discectomy, ALL/PLL removed, i.e. it should be
  SOFTER) needs 484 N for 0.87 mm and 4277 N for 1.48 mm -> ~50-100x too stiff in axial distraction. The large-d clamp /
  cage overload is therefore very likely a model artefact. The validation (step 1, Herron C0-C7) covered moments, not axial
  tension. Candidates: C3-pot kinematics (x, y and rotations fixed during distraction), facet capsules / contact, the tied
  disc remnant, ligament springs. Gap-model tests p036 / p011 ended in ERROR after the overload (expected given the above).
  -> AL re-run on hold until the PI decides; non-destructive diagnosis of the load path started.
- 2026-10-22 20:50 correction + diagnosis: distraction force at t 1 (Fz, column 10 of C3pot.txt): 53 / 321 / 957 / 2037 / 4447 N
  at d 0.5 / 0.8 / 1.0 / 1.2 / 1.5 (gap library, fixed C3-pot kinematics); an interim reading of column 11 (Mx) as Fz was
  wrong. Free C3-pot kinematics at d 1.0 (only z prescribed): 282 N (C3 tilts 4.6 deg, shifts 0.6 mm) -> the fixed kinematics
  stiffen ~3.4x, but even free the model is far stiffer than cadaver data (1.7 mm @ 44 N). Component-removal runs at d 1.0
  (h14 'diag_drop', gaplib_diag/): no FCC springs, no flavum, no interspinous, no facet contact, no annulus remnant (+ ties).
- 2026-10-22 21:35 LOAD-PATH DIAGNOSIS (d 1.0, fixed C3-pot kinematics, distraction force at t 0.5 / 0.75 / 1.0):
  base 53 / 230 / 957 N; no FCC springs 45 / 212 / 922; no flavum 52 / 229 / 956; no interspinous 52 / 228 / 955;
  no facet contact 53 / 230 / 957; NO ANNULUS REMNANT (+ its endplate ties) 9 / 20 / 39 N; free C3-pot kinematics 19 / 55 / 282.
  -> ~96 % of the distraction force is carried by the annulus remnant (posterolateral ring left by the ACDR discectomy,
  Herron fibre-reinforced solid mixtures, tied to the endplates). Without it the segment needs 39 N for 1 mm, the order of
  the cadaver data (1.7 mm @ 44 N, intact disc). The Herron annulus was validated in bending, not axial tension.
  Options for the PI: (a) calibrate the remnant's tensile response to axial-distraction data, (b) treat the remnant as
  released / resected in the surgery model (no annulus), (c) restrict d to the low-force range, (d) free the C3-pot rotations
  during distraction (3.4x softer, but the segment tilts 4.6 deg). AL re-run waits for this decision.
- 2026-10-22 22:05 PI DECISION (supersedes "Kept: lateral/posterior annulus remnants", 2026-10-20): in the surgery model the
  posterolateral annulus remnant is treated as released / resected (h14 'annulus_remnant': False -> remnant hexes and their
  endplate ties removed, nodes left unconnected fixed; facet cartilage, facet contact, capsules, flavum, interspinous kept).
  Verified identical (up to node-set order) to the diagnostic 'noAnnulus' model (39 N for 1 mm distraction, cadaver order).
  Gap library rebuilt for this surgery model (human_study/gaplib_noann). Consequences: all earlier clamp / capacity / AL
  numbers (with remnant) are superseded; the d range is to be reviewed against the new distraction forces.
- 2026-10-22 22:35 annulus-released gap library (gaplib_noann, 11 runs NORMAL): distraction force at t 1 = 9 / 12 / 17 / 23 /
  30 / 39 / 48 / 57 / 68 / 81 / 95 N for d 0.5-1.5 (was 53 ... 4447 N); cadaver order (1.7 mm @ 44 N intact; ours still has
  the C3-pot rotations fixed). The endplates no longer deform during distraction (gap loss 0.000 mm at every d; the remnant
  was what pulled them in) -> real gap = nominal gap + d, so the screening model v2 builds the cage on the nominal gap (no
  gap library needed). v2 = annulus released + expand insertion + no biodisc + wall pins + release_dtmax 0.1 (settings class
  human_study/al/v2_test); tests p037 / p036 / p011-ISO started 22:35.
- 2026-10-23 04:20 v2 tests: p037 compress: distraction 12 N, clamp 18.4 N, retained 0.68 mm, C 277 N (bone yield, endpoint
  reached); p036 compress (d 1.48): distraction 93 N, clamp 115 N, retained 1.57 mm, C 230 N (bone yield) -> the compression
  test now works over the whole d range. p011 ISO (B, d 1.43): passes insertion and release (clamp 21 N) but fails at the very
  start of ISO (t 3.00; inverted: 1835 C3 cortical tets + 1617 soft-line hexes) -> ISO-start failure still to be diagnosed.
  (The tests had ended ~23:00; the 23:19 report did not run and the machine idled until 04:15 - a monitoring lapse.)
- 2026-10-23 04:20 PI ("use the resources, the tuning looks good"): FULL SWITCH to the v2 screening model. h22 now writes
  to human_study/al_v2 (v1 kept in human_study/al), job prefix al_v2p, cases built with V2 = expand insertion (shrink 0.8),
  no biodisc, wall pins, release_dtmax 0.1, annulus remnant released; meshes shared (nominal gap). Same 48 Sobol points
  re-initialised (96 cases queued); settings class human_study/al_v2/cases/. Build workers 16, preflight daemon 12 threads.
- 2026-10-23 04:45 PI: analyse the ISO-start failure automatically once enough v2 ISO runs end. Runners (h06/h18) now pass
  -output_negative_jacobians=50 (inverted element ids in every case.log from now on); scripts/4_postprocess/
  h26_iso_failure_analysis.py summarises stop phase / time, clamp, rotations, inverted tissues, soft-layer compression and
  design factors into human_study/al_v2/iso_analysis/report.md. First run started (17 ISO runs already ended); automatic
  re-runs at 24 and 48 ended ISO runs (session cron). Scheduler fixes: nvidia-smi timeouts (a hung call froze launching),
  up to 8 CPU launches per pass.
- 2026-10-23 05:10 first ISO-stop analysis (19 v2 ISO runs, human_study/al_v2/iso_analysis/report.md):
  * 7 runs (and their compression twins) stop at the LAST INSERTION STEP (t 1.909, d 1.11-1.38; p036 at 1.48 passed): replay
    of p000 with element output -> all 580 inverted elements are the outermost 25 % cage layer (top 375 / bottom 205), i.e. the
    soft contact layer is crushed when the springing-back cage first meets the faceted endplate (0.2 mm cage grid vs 0.5 mm
    endplate triangles) -> numerical. AL: points that stop before the test (t < 3) are now 'invalid' (kept out of the GP;
    p000, p003, p012, p020, p031 corrected). Fix under test: h14 'insert_dt' 0.01 (p000, p012 in al_v2/diag).
  * 12 runs stop early in ISO (t 3.00-4.05, completion <= 10 %, C3 rotation 0.5-5.7 deg at the stop) with the soft contact
    layer at min principal strain -0.25 ... -0.35 (crush threshold -0.30, Gent lock ~-0.4) and clamp 9-32 N vs ISO axial
    100-150 N -> consistent with the agreed functional failure (soft surface layers crushed under the ISO load), as seen on
    2026-10-21; element-level confirmation pending (runs started after 04:40 log inverted ids).
- 2026-10-23 05:40 ISO-stop analysis #2 (34 v2 ISO runs, auto-trigger at 24): 7 stop at the last insertion step (numerical,
  fix under test); 27 stop early in ISO (completion median 3.7 %, max 20.7 %, C3 rotation 0.5-6.5 deg at the stop). Inverted
  elements (runs with ids): cage soft 12661 (87 %), cage hard/mix 1370, C3 cortical 530, C4 cortical 16. Contact-layer min
  principal strain -0.19 ... -0.39 but only 0-2 % of contact elements beyond -0.30 -> not a whole-layer crush: the ISO moment
  tilts the load onto the cage edge and a few soft edge elements invert, which ends the run. Factor signal: gradient radial
  (soft inside, hard edge) lasts longest (mean t_end 3.40) vs both 3.22 vs axial 2.86; the three furthest runs are A radial
  mix; design, fabrication, E_soft, clamp ~no correlation. So y currently measures "first soft edge element inverts", not
  slip / tipping. Options put to the PI (no setting changed): (a) keep, (b) strain-fraction criterion, (c) let ISO run further
  (finer soft-layer mesh or lower Gent Jm, Q45), (d) review the ISO load start (100 N + moments vs clamp 7-100 N).
- 2026-10-23 06:00 PI: the BIOCAGE's purpose is TEMPORARY SUPPORT AND FIXATION while the biodisc matures in vivo (not a
  permanent motion-preserving disc, not a fusion device). Note: the screening ISO step is ISO 18192-1 (motion-preserving disc
  wear test), displacement-controlled - C3 is driven to LB 6 deg / AR -4 deg + 100 N in a 1 s ramp, then FE 7.5 / LB 6 / AR 4
  deg x levels 1-3; all ISO stops so far occur inside that 1 s ramp (typically ~1.8 deg LB, ~30 N). Test protocol / AL
  objective to be revisited with the PI in the light of the device purpose.
- 2026-10-23 06:35 insertion fix confirmed: with h14 'insert_dt' 0.01 (fine steps for the final spring-back contact) p012 and
  p000 pass the step where they failed at t 1.909 (p012 into compression, p000 into release). Adopted into v2 (h22 V2 +
  settings class al_v2/cases); the 7 invalid points (0, 3, 12, 16, 20, 24, 31) rebuilt and requeued (old run dirs kept as
  *_invalid_<HHMM>). AL loop restarted so its proposals use the new settings (the running proposal had the old state).
- 2026-10-23 07:52 AL proposal took > 67 min (262 torch threads = one per core, fighting ~200 cores of FEBio runs); h22 now caps torch at AL_THREADS = 8 (env, default 8); loop restarted (37 threads).
- 2026-10-23 08:20 ISO-stop analysis #3 (43 valid v2 ISO runs; the 7 re-run points now pass insertion -> 0 insertion stops):
  all 43 stop early in ISO (completion median 3.7 %, max 20.8 %; 7 within the first 2 %). Inverted elements: cage soft 82010
  (82 %), cage hard/mix 12278 (12 %), C3 cortical 5573 (6 %). Mean stop time: design A 3.72 vs B 3.33; gradient radial 3.75 >
  axial 3.45 > both 3.34; fabrication mix 3.66 > interleave 3.37; corr with E_hard +0.30, clamp +0.35, E_soft +0.02, d +0.01.
  Furthest runs (t ~4-5.1, i.e. into the first ISO cycle): A radial mix (p38, p14, p2, p26), A axial mix d 1.48 (p36, clamp
  115 N). Same mechanism as #2 (a few soft edge elements invert under the imposed rotation); the ranking (A, radial, mix, stiffer
  hard phase, higher clamp) is physically consistent. Options to the PI unchanged; protocol question (purpose = temporary
  fixation) pending.
- 2026-10-23 11:34 Jupyter stopped again (~09:13-11:34, all processes killed); watchdog restored. 7 batch-0 cases built before insert_dt was adopted could not resume (preflight: settings mismatch, correct) -> rebuilt with the current v2 settings and restarted fresh (p011c, p015c, p032c, p038c, p038i, p043i, p044c; old dirs in al_v2/cases_invalid). Scheduler: a job file moved by preflight during a pass aborted the whole pass -> first_fit now skips vanished files.
- 2026-10-23 12:00 PI DECISION: replace the ISO 18192-1 screening test by a test closer to the patient's daily life during
  recovery (device purpose = temporary support and fixation while the biodisc matures). Default values proposed and used
  (PI gave none): 'physio' test (h14) = follower load 100 N (fixed-direction axial force through the ICR, ramp t 3-3.5, held)
  + pure moments 1.5 N m one direction at a time (flexion, extension, right LB, left LB, left AR, right AR; 0.5 s up / 0.5 s
  down each, t 3.5-9.5); C3 pot free in rotation and in-plane translation (moment control). h15 reports per direction: ROM
  at the peak moment, max cage slip, min anti-slip SF, max CoP eccentricity, completion. ISO kept for the final best designs.
  Test version on p037, p014, p011 (al_v2/physio_test, preflight OK) running; AL switch after the PI has seen it.
- 2026-10-23 12:45 PI: "no idle resources". Measured: FEBio runs use ~2.6 GB RAM and ~2.5 busy cores each (load 28 with 240
  cores pinned) -> memory (128 GB cap) is the real limit. New AL jobs pin 4 cores (h22 JOB_CORES 8 -> 4); up to 5 of my jobs
  per GPU (h19 MAX_PER_GPU 3 -> 5, share util < 60 %). The new 'physio' test is pre-run for all 44 done points (speculative,
  uses otherwise idle capacity; usable as soon as the PI approves the test switch): jobs al_v2pXXX_physio, 4 cores, 4 GB.
- 2026-10-23 12:55 h06.claimed_cores: only FEBio runs younger than 5 min claim their pinned cores (older runs are judged by measured load); with 8-core pins but ~2.5 busy cores per run, idle-unclaimed cores were 4 at load 21 / 256 -> 65 after the change.
- 2026-10-23 13:15 memory over-packed after the claim change: 51 runs, 5 GB free, 4 OOM kills (cgroup oom_kill 2 -> 6; killed runs resume from checkpoints via the watchdog). h19 now keeps MEM_HEADROOM = 16 GB free (was 4) before launching.
- 2026-10-23 14:20 physio test status: p014 (A radial mix) passes follower load + flexion (1.53 deg at 1.5 N m), stalls near
  the extension peak (t 4.91) with inverted FACET CARTILAGE elements (6, mat 5) - facets loaded in extension, numerical.
  p037 (A axial interleave) reaches peak flexion (2.75 deg) and stalls at t 4.04-4.08 with 1135 inverted soft interleave
  lines + 154 hard -> the interleave soft lines fail already at 1.5 N m flexion (same edge mechanism as in ISO, now under a
  physiological moment). p011 (B both interleave) stalls at the start (t 3.01-3.03, follower ramp + freed C3 rotations) with
  956 inverted soft lines. -> interleave soft lines are the weak point; facet cartilage inversion in extension needs a fix.
- 2026-10-23 15:07 AL stalled at 47 done for ~2 h: compression runs past their capacity endpoint crawl in auto-stepper retry loops (e.g. p062 at t 3.419, p063 3.410, p052 3.326 unchanged for > 15 min) holding memory slots, and 26 of 39 slots were physio pre-runs. h23 watchdog: a run whose simulated time advances < 0.005 within 45 min is stopped and its log closed with an ERROR TERMINATION line (equivalent to FEBio giving up after max retries; result truncated there; stops before t 3 -> 'invalid'). physio test p011 (B both interleave) ended in ERROR at the follower-load start (soft lines).
- 2026-10-23 17:22 AL jobs now declare mem_gb 4 (was 8; measured ~2.6 GB per run) so the 16 GB headroom rule does not leave ~20 GB idle.
- 2026-10-23 17:45 AL proposal blocked ('every candidate is near a running point', 30 min cooldown) while ~35 GB were free: h22 retries with a 0.07 d-separation when 0.15 leaves no candidate, cooldown 10 min. physio pre-runs queued for the 18 newly done points.
- 2026-10-23 18:45 physio summary (h27, 42 ended runs): NO run passes the 2nd window (extension); 14 complete flexion only,
  all design B complete 0 windows (stop at the follower-load start). Flexion at 1.5 N m: C3 rotation 0.4-3.3 deg, min anti-slip
  SF at mu 0.2 = 0.56-0.91 (< 1 -> slip predicted in flexion for every A design that got there). The extension stop is the
  facet-cartilage inversion seen in p014 -> blocks the protocol for every design; numerical, design-independent. Testing facet
  contact variants on p014 (h14 'facet_contact' overrides, default unchanged): pure penalty (laugon 0) and single pass
  (two_pass 0), queued first (al_v2/facet_test).
- 2026-10-23 18:45 cgroup oom_kill 6 -> 8 at ~18:35: not FEBio runs (no requeue) but my h27 physio summary running 8 h15 post-processings in parallel next to ~40 runs; h27 now uses 2 workers. FEBio peak RSS up to ~5 GB per run.
- 2026-10-23 21:00 AUTO (no reply since 14:20; PI fallback rule): (b) interleave soft lines failing under the physiological
  1.5 N m moment COUNT as functional failure (consistent with the agreed soft-layer-crush definition); (c) friction worst case
  stays mu = 0.2 (existing decision, not changed). (a) extension stall at ~-1.2 N m: not decided yet - test p014 with the
  extension moment capped at 1.0 N m (h14 'physio_scale', default unchanged; al_v2/facet_test/p014_ext1) to see whether the
  remaining four directions (LB, AR) complete. Facet variants (pure penalty, single pass) removed the inversions but also
  stall at -1.2 N m (C3 rotation linear, -2.1 deg; numerical, not instability).
- 2026-10-25 12:05 Jupyter service was down 10-24 ~11:06 -> 10-25 11:48 (~25 h; no runs lost, the queue was empty except the
  items below); daemons restarted by the watchdog at 11:51. AL v2 (ISO screening) reached the 150-point budget on 10-24 01:29;
  144 done, best robust feasible y 0.0096. Leftovers found and fixed: points 64 / 65 had status 'new' and truncated compress
  case.feb files (build killed by the 10-23 outage; preflight crashed on the XML) -> rebuilt and queued; p070_iso and
  p071_compress were killed at 10-23 18:33 (the cgroup OOM kills) but the wrapper reported exit 0, so the watchdog never
  requeued them -> requeued; h23 now also requeues v2 jobs with exit 0 and no FEBio termination line. Points 54 / 59 stay
  invalid (stop before the test even with insert_dt 0.01). All 76 physio pre-runs have ended.
- 2026-10-25 12:05 physio results (h27, 76 runs): windows completed 0: 35, 1: 39, 3: 2; design B 0 windows in every run (stops
  at the follower-load start); A 0.87. p062 and p063 (A axial mix, d 0.50 / 0.65) pass extension at the full 1.5 N m (-2.1 /
  -2.3 deg) and right LB (+1.2 / +1.1 deg) -> the extension stall is not universal. p014_ext1 (extension capped at 1.0 N m)
  also completes flexion, extension (-1.76 deg) and right LB (+1.23 deg). All three then stall in LEFT LB (t 6.68-7.03, i.e.
  after the moment reverses from right to left LB; zero line-search steps, p062 / p014_ext1 without inverted elements ->
  numerical contact convergence, not a material failure). Min anti-slip SF at mu 0.2 in every completed window < 1 (0.38-0.91).
- 2026-10-25 12:25 PI: (1) YES, the AL is re-run with the physio test (replaces ISO screening); (2) YES, numerical fixes for
  the left-LB stall may be tried (test conditions unchanged). h14 new optional params 'physio_dt' (default 0.05) and
  'physio_ctrl' (Control / time_stepper overrides for the physio step); default build byte-identical (checked on p062).
  Left-LB variants, one change each vs base, on p062 (full 1.5 N m) and p014_ext1 (al_v2/lb_test, jobs diag_lb_*):
  dt01 (dt 0.01), newton (max_ups 0 = full Newton), nols (lstol 0 = no line search), laug0 (facet laugon 0), combo
  (dt 0.02 + full Newton + facet laugon 0). The physio AL starts after this test, otherwise every point would stop at left LB
  and be re-run.
- 2026-10-25 12:25 slip, quantified (76 physio runs; contact is tied in screening, slip judged by the whole-face friction demand
  |T| / N at the peak moment, so 'max slip mm' in tied runs is not a real slip): friction coefficient needed to hold, mu_req =
  0.35 / SF_sim: flexion (41 runs) 0.21-0.37, median 0.26 (0 hold at mu 0.2, 38 hold at 0.35); extension 0.47-0.49 and right LB
  0.51-0.53 (only the 3 runs that got there, incl. p014_ext1). -> with friction alone at mu 0.2 every design slips in every
  direction tested. Consequence for the AL objective: the ISO score (completion until the first SF < 1 at mu 0.2) stopped all
  150 v2 points at the first slip (y 0.004-0.017), i.e. the ISO AL could only rank designs by how early they slip; the
  physio AL needs an objective that stays informative when every design slips at mu 0.2 (proposal to the PI: maximise the
  minimum SF over the 6 directions = minimise mu_req).

## Free-form evolutionary design (evo), PI 2026-10-25
Goal (PI): PLCL-only BIOCAGE, shape and material grown freely (evolution-like) to go beyond human-imagined designs; minimum
constraints = surgery-compatible + no nerve / bone harm; maximum freedom otherwise. Plan: `human_study/evo/PLAN.md`.
- Roles: four adversarial AI roles (Claude, headless) + a computational engine (evolution + simulation):
  designer (free ideation / mutation), verifier (reliability + reproducibility of the evaluation pipeline),
  safety guard (minimum purpose + nerve / bone safety), red team (finds and amplifies holes in all others, reports options).
- Space: STRICTLY inside the disc space (inset footprint, between the endplates); no bone penetration (no teeth / keels / screws),
  nothing protruding out of the disc space. Fixation must come from shape + friction.
- Material: every voxel = void or any PLCL 85:15 / 50:50 blend fraction phi in [0, 1] (Duan 2021 sigmoid as in the AL),
  print resolution 0.4 mm line / 0.2 mm layer.
- Biodisc space: the 60 % central-window rule is dropped for evo; replaced by (a) a low floor on the biodisc (void) volume and
  (b) the void must connect both endplates; volume is an objective -> trade-off chart (biodisc space vs fixation) for the PI.
- Insertion: one piece, from anterior, may be compressed during insertion and spring back (as the 'expand' insertion, shrink 0.8).
- Fixation score: minimise the friction coefficient needed to hold, worst of the 6 physiological directions (mu_req = max over
  flexion / extension / left-right LB / left-right AR); no hard pass mark.
- Compute: about half of CPU / GPU for evo, half for the physio AL.
- 2026-10-25 PI: avoid CPU-bound simulation where a credible GPU method close to reality exists; main goal = no slip-out,
  checked smartly; compare methods first (human_study/evo/METHODS_COMPARISON.md). New e02 (scripts/7_evo/e02_friction_limit.py):
  friction limit with twist (linear program) on tied runs. p062: force ratio 0.35-0.52 vs friction limit 0.75-2.15 (twist up to
  ~1 N m on the glued face in lateral bending, coupled axial rotation) -> the current force ratio is optimistic, the limit
  pessimistic; real friction simulation needed to decide. Proposal: own GPU explicit solver (TLED) on the same FEBio mesh,
  verified against FEBio in 5 gates. Batch on all 76 physio runs: tmux biocage_evo_e02 -> human_study/evo/method/.
- 2026-10-25 PI: evo slip-out failure = cage centre translation relative to the bone > 1 mm (as the earlier 1 mm relative-slip limit); also record ratcheting over cycles.
- 2026-10-26 PI asked how the four roles are managed (independent, cooperating, supervising, no data mixing): proposal human_study/evo/GOVERNANCE.md (IV&V, separation of duties, blackboard, structured JSON hand-overs, blinding, provenance, enforced per-role tool permissions). Pending PI comments.
- 2026-10-26 PI answers (evo):
  (1) solver core accepted: GPU Newton (cuDSS) + explicit friction return mapping (pure explicit DR too slow for bone vs nucleus);
  (2) three-tier evaluation accepted (fast screen < 1 min, full GPU 10-30 min for the front runners, FEBio for finalists);
  (3) friction coefficient PLCL-bone for the real-friction check: from literature (analyst to search and propose);
  (4) 6 directions x 3 cycles for ratcheting: enough;
  (5) S1-S9 values: PI asked for a plainer explanation (pending);
  (6) twist in flexion / extension (I-001): define precisely, search literature, analyse, propose fixes before using the numbers;
  (7) AL objective: wait for the real-friction GPU results before changing it;
  (8) start verifier, safety guard, red team now (designer later);
  (9) all roles on claude-opus-5-5, observe for one day.
- 2026-10-26 BUG FOUND (I-001, while analysing the 'twist in flexion'): h14 physio moment curves lacked the window-start
  point (ts, 0), so each moment ramped from t 3.5 instead of starting at its own window: at the flexion peak C3 also carried
  Rx 299 / Rz 166 N mm, at the right-LB peak Rz 833 N mm (p062 C3pot.txt). Every physio run so far (76 AL pre-runs,
  physio_test, facet_test, lb_test) had COMBINED loading instead of the agreed one-direction pure moments (Wilke 1998 /
  Panjabi testing convention). Fixed in h14 (pts += (ts, 0)); other tests unchanged. Consequences: physio ROM, stalls
  (extension / left LB), slip safety factors and the e02 twist numbers are invalid and must be re-run; the physio AL had not
  started (queue empty), no compute lost. Cage-mesh / model symmetry checked: surfaces mirror within 0.01 mm, bone tet meshes
  not mirrored (node offsets 0.04-0.6 mm) - only a small numerical asymmetry expected.
- 2026-10-26 physio reruns with the fixed curves queued: human_study/al_v2/physio_fix/{p062,p063,p014} (settings class = physio_test, preflight OK) to quantify the bug's effect before the physio AL.
- 2026-10-26 PI (evo constraints):
  friction coefficient for the real-friction check: mu = 0.3 main (smooth polymer, wet), sensitivity 0.2 / 0.45; every
  design also reports the mu needed to hold (no PLCL-bone measurement in the literature; coupon test recommended);
  S4 biodisc space floor = 50 % of the disc-space volume (was proposed 30 %); S5 printability: keep 0.4 mm / 45 deg overhang;
  S9 replaced: the test goal is NO slip-out in ANY direction (cage-centre translation > 1 mm relative to C3 or C4 = fail,
  6 directions x 3 cycles, ratcheting recorded); posterior migration (toward the cord) is absolutely unacceptable
  (reported separately; any posterior net translation is flagged even below 1 mm).
- 2026-10-26 red-team F-0002: pre-fix physio results marked INVALID (al_v2/PHYSIO_INVALID_2026-10-26.md, copies in physio_analysis/ and evo/method/; METHODS_COMPARISON.md section A and ISSUES.md I-002 flagged).
- 2026-10-26 PI (evo): (a) posterior limit 0.5 mm net migration toward the cord and minimum posterior push-out 135 N (safety guard
  proposal, Moroney 1988 max cervical AP shear) accepted; (b) biodisc maturation / support period: from the lab's previous work
  (Lintz 2021 dissertation, human_study/evo/PRIOR_FAILURES_Lintz2021.md): >= 16 weeks main, 26 weeks sensitivity; (c) no
  radiographic marker for now, imaging follow-up assumed possible (out of scope); (d) insertion: any feasible insertion method
  may be considered (oblique, staged, ...); the 53-60 % compression needed for a front slide-in and the permanent-set risk of
  hard PLCL must be faced: analyst to research surgical distraction / endplate preparation practice; (e) commit the work
  (author austonliuyi only, no Claude attribution).
- 2026-10-26 insertion feasibility (analyst, for PI): native C3-C4 gap in the footprint 2.95-5.30 mm (concave endplates, tallest
  in the middle). A contour-matched cage (design A, all AL designs) slid in from anterior WITHOUT compression needs an extra
  transient parallel distraction of 2.35 mm beyond the final distraction d (total 2.85-3.85 mm over native for d 0.5-1.5);
  without it the tallest column must be compressed 35-41 %. Hard PLCL 85:15 yield strain ~5 % (25 MPa / ~400 MPa, no direct
  data) -> the 'expand' insertion (natural height 0.8 x) is not physically possible for the hard core; it is a numerical
  convenience. Literature: surgeons distract with Caspar pins / trial spacers until a snug fit; final disc-height gain >= 2 mm
  (over-distraction) raises adjacent-segment ossification and subsidence (Sci Rep 2023, s41598-023-44998-4; Frontiers 2023 FE);
  ACDR practice removes osteophytes and checks parallel endplates (PMC5435629). Open PI / surgeon questions: maximum TRANSIENT
  intraoperative distraction for insertion; whether endplate preparation (anterior lip / osteophyte removal, flattening the
  concavity with curettes) is part of the procedure. Insertion options for evo (PI: any feasible method): (1) transient extra
  distraction, (2) endplate preparation, (3) hard core inside the insertable envelope + compliant PLCL 50:50 parts that compress
  elastically and refill the concavity, (4) rotate-in / oblique paths. Note: the concavity that blocks insertion also blocks
  expulsion (geometric interlock) - a fixation mechanism worth keeping.
- 2026-10-26 The free-form evolution study (evo) moved to its own repository biocage-evo
  (/raid/jupyter-alz.ee09/projects/claude-work/biocage-evo, private GitHub astcgt/biocage-evo); its decisions continue in
  biocage-evo/docs/DECISIONS.md. Removed here: scripts/7_evo/, human_study/evo/ (history kept in both repos).
- 2026-10-26 physio reruns with the FIXED load curves (al_v2/physio_fix, GPU copies *_gpuN, ~14 min each): p062 and p063 (A axial
  mix) complete ALL six directions (the left-LB stall was caused by the combined-loading bug); ROM flexion 1.71 / 1.57, extension
  -2.30 / -2.36, LB +-1.35 / +-1.31 (left-right symmetric, confirms the fix), AR +-1.80 / +-1.84 deg. Anti-slip SF at mu 0.35:
  flexion 1.84 / 1.67, extension 2.07 / 2.08, AR 1.87-2.04, LB 0.67-0.70 -> lateral bending is the slip direction
  (mu_req ~0.5). p014 (A radial mix) ERROR TERMINATION in extension (t 4.95). The physio AL has not been started.
- 2026-10-26 PI: use the idle resources. physio_v3 = physio test with the fixed curves for all 148 finished v2 AL points (scripts/6_active_learning/h28_physio_prerun.py, re-runnable, settings class = physio_test); data needed whatever AL objective is chosen. The AL loop itself is not restarted with a new objective (PI: wait for real-friction results).
- 2026-10-28 PI (via evo): physio windows under rotation control (h14 test 'physio_rot': follower step, then one step per
  window with the main C3 rotation prescribed relative to the step start, 0 -> intact ROM at 1.5 N m -> 0, other dofs free);
  post-processing takes the state where the reaction moment reaches 1.5 N m. Reason: 135 / 148 physio_v3 (moment control)
  stalled at facet contact onset, mostly in extension. Cases human_study/al_v2/physio_rot/ (jobs physrot_*), built by
  h28 (now parametrised: test / out dir / job prefix / ids); watchdog re-queues physrot_*.
- 10-28 22:43 physrot_* (rigid-prescribed version, rejected by FEBio: mixed prescribed/free rotations) unqueued / killed and moved to queue/failed; rebuilt with a generic rigid joint
- 2026-10-28 23:15 physio_rot fixes: (1) rotation amplitude per design = 1.15 x the rotation it reached at the moment-control
  peak in physio_v3 (else 1.4 x median cage / intact ratio x intact ROM): driving to the intact ROM overshot 1.5 N m ~3x
  (cage ROM 0.25-0.71 x intact) and inverted cage elements (p001 at t 3.80); (2) FEBio patch (output only):
  FEGenericRigidJoint records the force / moment it applies to body B (m_F, m_M were never set), logged as drive.txt
  (rigid_connector_data); e03 takes the state where the driving moment reaches 1.5 N m. Pilots p062, p001, p005.
- 2026-10-29 06:40 physio_rot pilots (p062, p001: extension t 4.87 / 4.83; p005: follower step t 3.39) failed with "Max nr of
  reformations". FEBio warned "Rigid connectors require non-symmetric stiffness matrix": the global stiffness was stored
  symmetric (solver default), dropping the non-symmetric terms of the Lagrange-multiplier joint and the sliding-elastic
  facet / cage contacts. h14 physio_rot now writes symmetric_stiffness 0 in the follower and window steps (param
  physio_rot_symmetric, default 0; insertion steps unchanged, so insertion = physio_v3). Checked on a small model: the tag
  is accepted, the warning is gone, cuDSS solves the general matrix. Old pilots -> al_v2/physio_rot_invalid_symstiff/.
  drive.txt (rigid_connector_data) still logs literal 0 in the full model although it works on small test models; the
  joint moment is in case.log ("=== rigid connector #k ... Lagrange m."; p062 flexion: 376 / 1026 / 1746 N mm at
  t 3.6 / 3.8 / 4.0, so the 1.15 x amplitude passes 1.5 N m as intended). Post-processing must read case.log until fixed.
  Relaunched: p062, p001, p005, p002, p003, p004, p006, p007 (8 x 4 cores = the 32-core cgroup quota).
- 2026-10-29 h19 scheduler caps launches at the cgroup CPU quota (cpu.max = 32 cores; the host has 256): free cores =
  min(idle host cores, quota - cores of my running jobs). Before, it counted idle host cores and could oversubscribe.
- 2026-10-29 07:30 symmetric_stiffness 0 fixed the extension stall: p062, p001, p002 ran all 6 windows (t 9.5). e04 on these
  (biocage-evo results/method/e04_rot): mu_squeeze <= 0.136 (lateral bending), one-face slip bound <= 0.25 mm. p001 reached
  1.5 N m only in flexion (fallback amplitudes too small for a stiff design). p005 / p006 / p007 (E_soft 2.4-4.6 MPa or
  design B) inverted at the start of flexion (t 3.54-3.62): cage soft layers (p005, p006), C3 cortical bone (p007).
  Queued: all remaining designs (physrot_, 105 jobs); second pass h28 'physio_rot al_v2/physio_rot_r2 physrot2_ all
  al_v2/physio_rot' for windows below the target (tangent extrapolation x 1.15, capped 2.5 x), p001 first; facet
  sensitivity (PI: can the facets be isolated for slip-out?) on p062, p002: no facet contact (physrotF0_, amplitude x 1.3),
  facet cartilage E 30 instead of 10 MPa (physrotF3_). Run the second pass for all designs when the first pass ends.
  Anterior muscle springs and the reduced (equivalent-spring) model: agreed with the PI, after the facet result.
- 2026-10-30 PI: (1) designs with > 30 % local soft compression (worst element) at the last converged state are
  unacceptable: 48 designs. (2) slow dynamic analysis for the rest: h14 param physio_dynamic {density 1e-6 t/mm^3 (all
  materials, ~1000 x tissue), rhoi 0 (generalized-alpha, maximal high-frequency damping)}, follower + window steps only.
  Validation vs static (e04): p062 / p002 mu_squeeze within 0.002, slip bound within 0.02 mm; p093 / p100 (static failed in
  flexion) completed. Queued 61 designs (physrotD_, al_v2/physio_rot_dyn, amplitudes from pass 1 / pass 2);
  h29_rot_chain.py queues the next dynamic pass (physrotD2_, al_v2/physio_rot_dyn2) for windows below the target when
  the pass ends (no idle queue between passes; in resume_all.sh).
- 2026-10-30 user: the top priority is the simulation environment and procedure validation (feasibility of every protocol test).
  Diagnosis of the 2 failed physio_rot_dyn runs: p023 (B both interleave, E_soft 1.50, E_hard 263) and p053 (A both interleave,
  d 1.50, E_soft 1.57) stop in insertion (t 1.99 / 3.00) in every physio version -> design failures before the test (p023: cage
  inversions through the whole height + C4 cortical; p053: 88 % in the top 4 layers against C3 + C3 cortical, at the end of
  release); with p054 / p059 these are the only 4 of 150 points that stop before t 3 (E_soft median 1.57 vs 5.2) -> invalid.
  Validation pilots on p062 / p002 (the two designs that pass all 6 physio_rot windows), human_study/proc_val/, jobs val_*
  (queued first; watchdog re-queues val_): h14 new optional params 'nonsym' ('test' | 'all': symmetric_stiffness 0 in those
  steps) and 'test_dynamic' (= physio_dynamic for any test); defaults byte-identical (checked on physio_rot_dyn, physio_rot,
  physio_v3, cases iso / compress). (1) ISO 18192-1, 1 level x 3 cycles, tied: iso_ns (nonsym test), iso_nsdyn (+ slow
  dynamic). (2) push-out with REAL friction (sliding-elastic, mu 0.35, nonsym all, dynamic test): push_ant, push_post; push_post
  static (nonsym all) on p062. (3) physio_rot dynamic with real friction (mu 0.35, nonsym all) on p062, p002.
- 2026-10-31 01:40 validation pilots (proc_val, 11 runs) ended. ISO 1 level x 3 cycles: p002 COMPLETES (t 7.0) both static
  nonsym and dynamic -> first ISO cycles ever completed; p062 stops (static t 3.04, no inverted elements = convergence;
  dynamic t 4.95, inverted C3 cortical 879 + cage mix_0.25 251). Push-out with real friction (mu 0.35): p062 push_post
  dynamic COMPLETES 3 mm: peak 93 N at 1.10 mm, 80 N at 3 mm (< 135 N posterior guard; rim not in contact, conservative);
  p062 push_post static stops t 3.26 (no inversion -> dynamic needed); push_ant p062 t 3.42 (no inversion), p002 t 3.21
  (soft cage 476 inverted); push_post p002 t 3.37 (soft cage 109). physio_rot dynamic with real friction: p062 COMPLETES
  all 6 windows (t 9.5); p002 stops in LB_left (t 6.76; C3 cortical 1571 + soft cage 511 inverted). Analysis pending
  (e04 on friction run vs tied, push curves).
- 2026-10-31 PI: soft-PLCL compression rule replaces "worst element <= 30 %": sustained (after insertion + release + 100 N
  follower, t 3.5) <= 15 %, peak (windows, up to the state where the driving moment reaches 1.5 N m) <= 25 %, measured as
  the worst 1 % (99th percentile) of 1 - minimum principal stretch over the cage elements containing soft PLCL
  (biocage-evo methods/e05_compression.py). Interim: no compression-set data for bulk PLCL in the literature (rubber-spring
  / elastomeric-bearing practice, PLCL 70:30 stress relaxation ~30 %, Peerlinck 2023); to be replaced by bench data
  (stepwise 10-40 % compression in PBS 37 C, residual strain at 1 h / 24 h, after 4 / 8 weeks aging). Height loss and
  posterior bulge are the safety agent's checks. All designs are re-judged with this rule (the 58 "> 30 %" verdicts lapse).
- 2026-10-31 PI: windows run independently: h14 param physio_split -> h30 writes the insertion run (case.feb, step-end plot
  states, -dump=2) + w_<window>/restart.feb (FEBio restart 2.0: archive ../case.dmp + one window step, rotation curve at
  t 3.5-4.5); h06 / h18 run h31_split_run.py (insertion, then each window restart; needs the same -cnf; the window dir gets
  a copy of case.xplt). Test p062 flexion: mu_squeeze 0.0259 vs 0.0261 sequential, slip bound 0.1155 vs 0.1154 mm.
- 2026-10-31 user: equivalent contact-skin prototype started; NO homogenisation of the cage interior (the evo agents need the
  material layout resolved). Design: replace only the outermost cage element layer (0.2 mm) by a per-node law (parameters
  from the material under each node, so the in-plane material map and the surface geometry stay); interior unchanged.
  Failure diagnosis of the 6 failed proc_val pilots (scratch where.py / first.py): terminal cause = cage inversion in 2
  (p062 ISO dyn, p002 push_ant; layers 0-1 from the surface), contact convergence without inversion in 4; the C3 cortical
  inversions in p062 ISO / p002 friction physio lie 10-13 mm from the cage (facet region), recovered by step cuts, not terminal.
  Step 1, patch calibration (scripts/3_cage_case/h32_eqlaw_patch.py, human_study/eqlaw/patch_soft (E 3.67, G 1.27, k 12.2,
  Jm 0.7) and patch_mix025 (G 106, k 671)): bonded plane-strain strip t 0.2 mm, w 0.4 / 1.2 / 3.0 mm, all reach 40 %
  compression without inversion. Apparent modulus at small strain (soft) 7.2 / 11.1 / 12.9 MPa = 2.0 / 3.0 / 3.5 E, tending to
  the confined modulus K + 4G/3 = 13.9 MPa. Tilted platen (0 -> 40 % over 3 mm): the LOCAL (Winkler) law from the strip interior
  reproduces the FE base pressure within 1-4 % except within ~1-2 t of the free edges (+12 % at the low end, -8 / -10 % at
  40 %); total force within 2 %. -> at t 0.2 mm the response is local; a Pasternak (neighbour-coupling) term is not needed
  (corrects the earlier estimate); edge effects are confined to ~0.2-0.4 mm. Bonded corners give singular edge pressure
  (2x centre). Next: facet-like indentation patch (0.5 mm faceted rigid surface) to reproduce the inversion mechanism, then
  the FEBio implementation (normal + diagonal springs for shear, contact on a skin surface; the 'expand' shrink of the
  removed 0.2 mm moved into the core prestrain so the cage height history is unchanged).
- 2026-10-31 06:30 split runs, BUG + fix: the restart LoadData redefinition of each window's rotation curve did not act (FEBio
  restart redefines curves by load-controller index, not by file id): in every window except flexion (curve already at
  3.5-4.5) the joint moment stayed constant (p062 split test: LB_left Mx 1.7 N mm throughout, extension My -80 N mm), so the
  rotation was never applied; the "split = sequential" check had covered flexion only. The physrotS_ / physio_rot_split
  results (40 designs) are INVALID except their insertion state (sustained compression) and flexion. Fix (h30): every window
  curve is moved to t 3.5-4.0-4.5 in the insertion run itself, so the dump holds it; restart.feb has no LoadData. Windows stop
  at the peak (t 4.0, half the steps): the unload tail is not used and its near-zero-load end failed the relative energy norm.
  h31: a dynamic window failing before its first converged step gets one static retry (restart_static.feb). Rebuilt as
  al_v2/physio_rot_split2 (prefix physrotT_, 38 designs; p049 / p141 left out: sustained compression 40 %, fail). p062 first
  (all 6 windows compared with sequential before the results are used). Disk: /raid reached 0 MB at 05:54 (4 runs lost);
  .dmp checkpoints of terminated runs deleted (252 GB; not in physio_rot_split*), launches restored.
- 2026-10-31 disk full (99 %): user approved deleting .xplt/.dmp (201 files, 177 GB) in the invalid dirs al_v2/physio_rot_invalid_*, cases_invalid, physio_test, facet_test, lb_test, cases/*physio*; feb/log/txt kept (al_v2/INVALID_OUTPUTS_PURGED_2026-10-31.md). Also removed 204 GB of stale git tmp_pack_* garbage (10-20/21). Folder rename to biocage_stimulation_test_oct2026 scheduled after the physrotT (split2) batch ends and the daemons are stopped, no symlink.
- 2026-10-31 user approved: deleted .xplt in early test / pilot dirs (cage_test, gaplib [superseded by gaplib_noann], al_v2/diag, al_v2/physio_rot_split_test, al_v2/physio_rot_r2_p001try); feb/log/txt/json kept.
- 2026-10-31 user approved: deleted .dmp restart files of finished runs (all of human_study except al_v2/physio_rot_split*, proc_val and running / queued jobs).
- 2026-10-31 watchdog_retries.json had been truncated to 0 bytes by the full disk (watchdog crashed every cycle since ~05:54: no requeue / stall checks); restored from HEAD -> the watchdog then requeued 7 superseded physrotS_ (bad-curve split v1) jobs and physrot2_p001; unqueued to queue/cancelled_stale_requeue/, retry counts set to MAX.
- 2026-10-31 08:30 split2 validation, p062 (CPU, all 6 windows vs the sequential run; mu_squeeze / slip bound mm / M at
  target): flexion 0.0259/0.1155/1558 vs 0.0261/0.1154/1557, LB_right 0.1355/0.0744 vs 0.1361/0.0745, LB_left 0.1355/0.0741 vs
  0.1361/0.0742 (within 1 %); extension 0.0117/0.1464/1693 vs 0.0134/0.1339/1552, AR_left 0.0742/0.2090/1580 vs
  0.0743/0.2006/1502, AR_right 0.0736/0.2134/1634 vs 0.0742/0.2017/1506: the slip-bound ratio equals the moment ratio at the
  target-crossing step (1.09 / 1.05 / 1.08), i.e. sampling of the first step past the target, not a different response; the
  split windows start from the neutral implanted state (no previous-window history). Accepted; split results replace the
  sequential ones. 12 designs (p009 p011 p021 p023 p033 p035 p045 p047 p053 p055 p057 p058) fail the insertion run at the
  same point as in every earlier version (static physio_rot, physio_rot_dyn, first split): negative Jacobians in the
  follower-load step t 3.0-3.4 (p023 / p053 at t 2.0, insertion): not computable in any mode, stay "open" (verdict rule to
  be decided: inversion under the 100 N follower load = compression failure?). h31 static retry: 6 of 7 first-step dynamic
  failures completed (p027 AR_right failed both). Post-processing: biocage-evo ops/collect_split.py (e04 + e05 per window,
  merged verdicts in results/method/split/).
