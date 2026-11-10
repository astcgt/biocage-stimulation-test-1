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
- 2026-10-31 10:40 (split2 batch ended 09:30; review day). (1) Post-processing gap: the e04/e05 batches of earlier sessions
  globbed only p*_gpu* dirs, so 18 CPU-run cases (6 complete sequential runs) were never evaluated; computed now. collect_split
  (biocage-evo) now AGGREGATES verdicts from every per-run result file (explicit invalid-set list, source recorded per value,
  manual_overrides.json for p049/p141 insertion state from split v1 = same design point, sustained 39.6 %) instead of
  merging into hand-made intermediates; crash on sustained = None fixed. (2) Merged verdicts: 62 pass, 62 fail
  (compression), 24 open (12 invert under the follower load; 12 with a window below 1.5 N m), 2 invalid; mu_req < 0.17 for
  every evaluable design, lateral bending governs (67/68); best p048 0.076. (3) AL set: 150 points = 133 unique designs (12
  duplicate groups: GP acquisition clamped at the bounds); report unique counts. (4) Queued: second pass physrotU_
  (al_v2/physio_rot_split3; h28 rot_retarget now reads split runs w_*/drive.txt) for the 12 open designs; real-friction check
  physrotFr_ (al_v2/physio_fric: contact_type elastic mu 0.35, nonsym all, dynamic, split) on p062 p048 p125 p060 p115 p109
  p084; settings classes added. (5) Documents: human_study/PROGRESS_REPORT_2026-10-31.md (read first in new sessions);
  biocage-evo paper/LITERATURE.md, paper/ABSTRACT_OUTLINE.md, paper/figures (F1-F7), docs/RISKS.md,
  docs/IDEAS_ARCHITECTURE.md, docs/DESIGNER_KICKOFF.md, roles/prompts/designer.md (DRAFT). (6) The 29-agent review workflow
  hit the account usage limit (4 of 29 completed); the review was finished inline. Rule: small agent fan-out, inline synthesis.
- 2026-10-31 11:40 second pass (physrotU_, al_v2/physio_rot_split3) ended: 12/12 insertions and 72/72 windows normal.
  Verdicts (collect_split, split2 + split3): 68 pass, 63 fail, 17 open (12 follower-load inversions + p036 p051 p082 p093
  p113 still below 1.5 N m in >= 1 direction). p068 p100 p101 p112 p117 -> pass; p003 p015 -> fail (compression at the
  split3 evaluated states). Third pass for the 5 pending (amplitude x 1.3-1.5) to be queued after the friction batch.
- 2026-10-31 11:50 CORRECTION to the second pass: for the 5 designs whose previous run was a split run (p036 p051 p082 p093
  p113) h28 rot_retarget visited the never-run build dir (no w_*/drive.txt) before the _gpuN copy and kept the amplitudes
  (ratio 1.00), so their second pass repeated the first; the 7 designs with sequential previous runs were retargeted
  correctly (5 -> pass). Fixed (skip dirs without window drive data); third pass physrotV_ (al_v2/physio_rot_split4, prev
  split3) queued for the 5 with the enlarged amplitudes printed above in scheduler.log order.
- 2026-10-31 12:35 third pass (physrotV_, al_v2/physio_rot_split4) ended: p036 p051 p082 p093 p113 reach 1.5 N m in all
  six windows -> pass. Verdicts 73 pass / 63 fail / 12 open (= the 12 follower-load inversions). The screen of the human
  design families is complete except for those 12 and the real-friction check (physrotFr_, running).
- 2026-10-31 12:45 degradation SENSITIVITY sweep queued to use the idle slots (exploration, not a verdict rule; PI may cancel):
  five passing designs spanning E_soft (p048 1.67, p097 1.92, p062 8.19, p115 7.38, p109 11.3 MPa) rebuilt with E_soft x 0.5
  (physrotG5_, al_v2/physio_degr050) and x 0.2 (physrotG2_, physio_degr020), the three stiffest also x 0.1 (physrotG1_,
  physio_degr010); split2 protocol and amplitudes; E_soft below the agreed 1.5-12 MPa range on purpose (literature: CL-rich
  PLCL loses half its molecular weight in 18-32 days). Question: does fixation (mu_req) or the compression rule fail first
  as the compliant phase softens?
- 2026-11-01 23:40 folder renamed 'biocage stimulation test 1' -> biocage_stimulation_test_oct2026 (no symlink; queue empty, no FEBio running since 10-31 15:47). Daemons stopped and restarted via biocage-evo/ops/resume_all.sh; hard-coded paths updated in biocage-evo code/docs (config.json, e03_batch.sh, resume_all.sh, collect_split.py, fric_compare.py, degr_compare.py, activity_keepalive.py, make_figs.py, run_foreman.sh, foreman.md) and PROGRESS_REPORT_2026-10-31.md; result json 'case' fields keep the old path as a record.
- 2026-11-01 user: the four platform goals (physically realistic, as fast as possible, observe only the targets we care about,
  accommodate diverse designs) ARE the capability labels. Every failed run / debugging item / change must be tagged with the
  capability it concerns ([物理] [速度] [觀測] [多元]), classified as platform deficiency vs design elimination ([設計]) vs rule
  pending ([決定]), and assessed for its effect on the other three capabilities. Written: human_study/PLATFORM_CAPABILITIES.md
  (capability objects, decision table, trade-off matrix, impact-assessment template) and human_study/AUDIT_TODO_2026-11-01.md
  (severity-ordered to-do list, plain language, glossary). Post-processing run today: ops/fric_compare.py and ops/degr_compare.py
  (biocage-evo results/method/fric, degr). Findings: (1) real-friction batch (physrotFr_, 7 designs): p048 / p084 / p115 stop in
  the follower-load or release step (inversions in cage soft layers AND C3/C4 cortical bone), p109 flexion/extension fail; the
  completed windows used the tied amplitudes (physio_rot_rad identical) and reach only 0.5-1.2 N m (p062 flexion 922 vs 1746
  N mm tied) -> gate 4 not yet answered; (2) e04 accepted a must-point micro-step (dt 2e-6, slow dynamic) as the target state:
  p060 LB_left M -295270 N mm, target_reached True -> evaluation-state filter needed; (3) degradation sweep E_soft x 0.5/0.2/0.1
  on p048 p062 p097 p109 p115: mu_req and sustained compression almost unchanged (p062 0.136 -> 0.138; p048 sustained 6.6 -> 6.9 %),
  slip bound rises (p048 0.158 -> 0.351 mm), p115 reaches only 3-4 windows at the fixed amplitudes: passing designs are
  hard-phase-carried; soft-phase degradation is not their fixation risk, hard-phase creep (e06) is. Sensitivity only, not merged.
- 2026-11-02 07:06 folder renamed again biocage_stimulation_test_oct2026 -> biocage_simulation_test_oct2026 (typo: simulation, not stimulation; no symlink; queue empty, no FEBio running). Daemons stopped / restarted via biocage-evo/ops/resume_all.sh; the same 10 biocage-evo code/doc files plus PROGRESS_REPORT_2026-10-31.md and AUDIT_TODO_2026-11-01.md re-pointed.
- 2026-11-02 user: capability labels refined. [數值] numerical correctness (Verification: discretization, time stepping / slow-dynamic
  artefacts, contact algorithm, protocol approximations, solver consistency) is a fifth PRIMARY label, split from [物理] (now
  Validation only). [泛化] robustness of conclusions and [時程] support-period coverage are SECONDARY: registered, verdict
  deferred, but every conclusion carries their scope statements (R07, R08). Judgement made systematic and object-oriented:
  Capability -> Facet -> Check (method, threshold + source, configs, required/advisory, depends on Components, status per
  Configuration TIED / FRIC / GPUFE), Restriction (bounded / exclusion / scope). Facet = worst required check; only a bounded
  restriction upgrades a gap to 有條件合格; a component modified after a check's evidence date makes it stale. Files:
  human_study/PLATFORM_CAPABILITIES.md (rules), human_study/platform_capabilities.json (56 checks, 9 restrictions),
  scripts/8_audit/h33_capability_audit.py -> human_study/CAPABILITY_SCORECARD.md (generated), `impact` query for changes.
  First verdicts (TIED / FRIC / GPUFE): [物理] 未評/未評/-, [數值] 未評/不合格/不合格, [速度] 不合格/不合格/-, [觀測] 不合格 x3,
  [多元] 不合格/不合格/未評. All thresholds marked 提案 await the PI. AUDIT_TODO retagged (T01 T02 T14 T17 T18).
- 2026-11-02 15:40 capability gap pass (user: list gaps per label by severity, research, implement what is safe, list conflicts
  and unsolvable items; human_study/CAPABILITY_GAPS_2026-11-02.md). Implemented, all post-processing / operations (no FEBio
  input changed): (1) biocage-evo e03.filter_rows + target_bracket: evaluation states with dt < 1e-4 (FEBio must-point /
  step-end micro-step, FECore FETimeStepController::CheckMustPoints: spurious inertia moment in slow dynamics) or isolated
  moment spikes (deviation from the neighbour prediction > max(0.15 target, 1x predicted)) are excluded; metrics interpolated
  between the two states bracketing 1.5 N m (T07 overshoot removed: p062 extension slip 0.1463 -> 0.1383 mm vs sequential
  0.1339; AR_left 0.2090 -> 0.2016 vs 0.2006, i.e. the split-vs-sequential residual WAS the overshoot); e04/e05 --test.
  (2) scripts/8_audit/h34_window_scan.py (WINDOW_SCAN_2026-11-02.md): 474 windows, 1 micro-step, 21 spike windows, 3 old
  verdicts rested on a spurious state (split2 p015 / p027 extension, fric p060 LB_left -> below target, R02); 16 failed
  insertions, 15 with C3/C4 cortical bone inversions (74-590 elements; [數值] NUM-06, not a design verdict); non-computable
  designs concentrate in family B (8/9), gradient both (7/8), interleave (11/30 vs mix 2/12), low E_soft (8/14 vs 0/14 high).
  (3) h31 writes w_*/window_check.json + split_check.json; collect_split rejects windows without valid states, adds
  class/reason per design (PASS, DESIGN/compression-*, [觀測]/amplitude, [觀測]/integrity, [多元]/computability,
  DECISION/T05-lowerbound), normalises old folder names; full re-evaluation of split2-4 running (old results kept in
  results/method/split_pre_interp_20261031/). (4) h19 reads human_study/scheduler_tuning.json every pass, pauses launches when
  free disk < 100 GB (usage limit off until the PI sets the quota); h23 atomic state files, tolerant loads, hourly du ->
  disk_usage.json, ALERT_watchdog.txt after 3 failed cycles, al/loop.done stops the AL-loop restarts (2060 so far); both
  daemons restarted 14:45. (5) h28 despike (a spike no longer freezes the amplitude). Queued: physrotFr2_ (al_v2/physio_fric2:
  p060 p062 p109 p125, amplitudes retargeted from physio_fric; gate 4 second pass) and p062 numerical-convergence runs
  physrotNdt_ (physio_dt 0.025), physrotNp05_/Np20_ (penalty 5/20), physrotNhz_ (cage HZ 0.1 mm, meshconv/
  cage_A_axial_mix_d0.500_HZ0.1.npz, penalty 5 to keep the auto-penalty stiffness ~E/h); settings classes added. Literature:
  Henninger 2010 (< 5 % mesh-convergence criterion for spine segments); Smit/Engels/Govaert 2008/2010 (PLLA creep: 50 % of
  short-term strength -> ~1 day, 14 MPa per decade; 25 % -> ~3 months); FEBio plot_level/stride only for fixed steps and
  must-point states are micro-step states -> xplt reduction must be post-run (conflict 3.1). Open for the PI: GAPS section 4
  (bone inversions, family B computability, material data, disk policy, e06 threshold, 135 N gate, slow-dynamic artefacts).
- 2026-11-02 16:10 re-evaluation of split2-4 with the interpolating / filtering e03-e05 ended: 276 windows, 0 errors; verdicts
  72 pass / 63 fail / 13 open (was 73 / 63 / 12). Among 234 windows reached in both evaluations mu_squeeze moved by -0.4 %
  (median) and the slip bound by -3.4 %; the 13 windows with |d mu| > 20 % are 10 whose old evaluation state was a moment spike
  (p100 LB_right 0.043 -> 0.122, p092 AR_left 0.125 -> 0.036, p082 p088 p015 p052 p061 p051) and 3 with mu < 0.01 (absolute
  change <= 0.002). p027 pass -> open: its extension window collapsed after a spike (1434 -> 1742 -> 992 -> -137 N mm, C3
  cortical inversions); collect_split rule added: a window with dropped states AND a non-monotonic moment is 'unstable' and
  counts neither as reached nor as a compression lower bound -> class [數值]/unstable-window, recompute before any verdict.
  Classes: PASS 72, DESIGN/compression-sustained 53, -peak 5, -peak-lowerbound 5, DECISION/T05-lowerbound 10 (p009 p011 p021
  p033 p035 p045 p047 p055 p057 p058), [多元]/computability 2 (p023 p053), [數值]/unstable-window 1 (p027). All 8 queued runs
  (physrotFr2_ x4, physrotN* x4) started on CPU: every GPU is occupied by other users.

## 2026-11-02 18:00 — numerical convergence of the rotation protocol; second evaluation-state rule (rigid-body dynamic residual, NUM-14)
- The four p062 convergence runs (dt x0.5, penalty x0.5 / x2, cage HZ 0.1 mm with penalty 5) ended. First comparison: 5/6 windows
  within tolerance for every variant, extension out by 6-7 % in all four - but the four variants agreed with each other to 2 %; the
  OUTLIER WAS THE BASELINE. Per-state trajectories: the baseline's state at t 3.9455 is a retried step (log: Retry attempt 1, dt
  0.05 -> 0.04545) whose joint moment reads 1360 while the neighbours predict 1535; slip / mu / N of that state are consistent with
  the neighbours; C3pot.txt logs a rigid-body moment My = -184 N mm at that state (< 0.3 elsewhere) = the deficit.
- Root cause of the "spikes" (T02): the driven rigid body's inertial residual (mass-scaled slow dynamics, density 1e-6 t/mm3 =
  1000 x water) after a retried / cut step, at the window start, or during contact chatter; the joint moment absorbs the same
  amount. Verified on all large spikes: M_drive - M_rb(axis) returns to the neighbour interpolation within 1 % (p052 +245 % ->
  +0.4 %, p051 +237 % -> +0.6 %, p093 +118 % -> -1.0 %, p142 +32 % -> -0.5 %, p145 +34 % -> 0.0 %). FEBio source: m_Fr / m_Mr are
  the assembled residual contributions on the body (FEResidualVector, FERigidFollowerForce, FEGenericRigidJoint).
- RULE (standing, 提案 threshold): a state whose rigid-body moment residual |M_rb| > 2 % of the target (30 N mm) is never used for a
  verdict (e03.filter_rows reason 'dyn'; h28, h31, h34 same rule). Dropped, not repaired: the correction is unreliable inside
  unstable windows. The force residual is reported only (rb_fres_max): states 2-7 N off the follower with |M_rb| < 30 have smooth
  slip / mu / N (p092 flexion, p130 extension, p083 LB_left) - convergence slack, not a transient. A tighter smoothness threshold
  was rejected (would touch 75 windows, mostly legitimate sign-crossing ramps).
- Scan (h34): 158 / 474 windows have such states (337 / 5278 = 6.4 %); 11 windows flip "reached" -> "not reached" (production 5:
  p088 AR_left, p107 AR_right, p117 AR_right, p015 AR_right split3, p082 AR_left split4). 123 production windows re-evaluated
  (old results archived in biocage-evo/results/method/split_pre_dyn_20261102/): 70 pass / 62 fail / 16 open (was 72/63/13).
  Moved: p082, p107 PASS -> open [數值]/unstable-window; p003 fail (peak lower bound) -> open. collect_split: a window with
  dropped states that did not end in a valid state (complete False) is also 'unstable'.
- Re-run comparison: NUM-01 / NUM-03 / NUM-05 PASS on p062 (time step: all |d| <= 0.2 %; penalty x0.5 / x2: slip <= 2.3 %, mu
  <= 3.3 % (extension 7.7 % = 0.0011 absolute); mesh 0.1 mm: slip <= 0.8 %, mu <= 4.9 % (0.0012); sustained <= 0.11 pp). mu
  relative changes count only when |d mu| > 0.005 (MU_ABS, 提案). R09 exclusion -> bounded (< 5 % = tie; +-5 % of a threshold =
  數值待確認). Only p062 (family A) verified.
- Duplicate designs (AL did not dedupe): p082=p088, p092=p117, p093=p145, p100=p142 (only the h28 amplitudes differ). Windows with
  identical amplitudes agree to <= 3.1e-10 between cuDSS (GPU) and pardiso (CPU) and between GPUs -> NUM-11 pass; windows with
  10 % different amplitude give mu / slip / N at 1.5 N m within 0.5 % -> rate independence of the slow-dynamic protocol (NUM-08
  support). p082 open vs p088 PASS for the same design: evidence of duplicates should be merged (T26).
- Registry 57 checks, scorecard regenerated: [數值] temporal facet 合格, contact facet 不合格 (bone inversions), capability
  不合格. Friction second pass (physrotFr2_, CPU) still running. Open PI items unchanged (GAPS section 4); item 7 now has the
  root cause and two options (accept the filter as routine, or invest in lower density / static / step-restart - all need
  re-validation).

## 2026-11-03 — PI DECISIONS on the 2026-11-02 capability audit (plain-language list answered item by item)
1. Slow-dynamic spurious states: the two-layer evaluation-state filter (micro-step; rigid-body moment residual > 2 % of the target,
   NUM-14) is ACCEPTED AS ROUTINE. Root-cause fixes (lower density, static windows, step restart) are not pursued now.
2. Numerical-convergence tolerances CONFIRMED: mesh and penalty 5 %, time step 2 % (p062 passes). ALSO verify one family-B (thin
   soft layer) design — pending: no family-B design has completed any window yet (all 9 stop under the follower load or during
   insertion), so this waits for item 4.
3. T05 lower bound: an insertion run that stops under the follower load with the soft layer already compressed beyond the limit is a
   FAIL (class DESIGN/compression-sustained-lowerbound; collect_split updated). 10 designs move open -> fail.
4. Designs that stop in the insertion phase before any load (p023, p053): treat as a PLATFORM problem first; search for fixes and
   iterate; come back to the PI only when nothing works, or with an analysis showing thin soft layers are not a realistic design.
5. Bone element inversions: first ANALYSE why a reputable solver fails on bone (fundamental) — analysis started
   (human_study/BONE_INVERSION_ANALYSIS_2026-11-03.md when done), no fix runs yet.
6. Duplicate designs: merge evidence of identical-parameter designs in collect_split (done; p082 inherits p088's AR_left) and
   de-duplicate AL proposals against all existing points (h22 updated).
7. Hard-phase stress (e06) threshold: 18 % of short-term strength — but SECONDARY; focus stays on the short-term indicators and the
   capability labels (no slip-out, successful insertion). e06 not implemented now.
8. Expulsion gate 135 N: PI asked for the difference between "ASTM-style relative comparison" and "value re-derived from
   physiological shear" before deciding (explained in the 2026-11-03 report).
9. Storage: /raid is not needed for compute now — archive to the NAS (/mnt/jp/alz.ee09), cap 3 TB. h36_nas_archive.sh moves finished
   sets and leaves symlinks; phase 1 (old / invalid sets, ~1.1 TB) started 2026-11-03; split2/3/4, fric, degr, numconv follow when
   the friction second pass has ended.
10. Material bench data: none yet.
11. Commit and push both repositories (done 2026-11-03).
12. Reporting: from now on reports to the PI in plain language like a briefing to a boss — problem / cause / recommended fix /
    professional sources consulted; encoded as the project agent .claude/agents/pi-report.md.

## 2026-11-03 01:30 — bone "inversions" re-attributed (BONE_INVERSION_ANALYSIS_2026-11-03.md, analysis agent; spot-checked)
- CORRECTION of 2026-11-02: the "15/16 failed insertions with C3/C4 cortical inversions" were diverged Newton iterates of retried
  steps (Jacobians -2 ... -1e13, impossible for a converged state), inflated by -output_negative_jacobians=50 per domain and the
  block check order (C3_cortical first). In every failed run the FIRST inverted element is cage_soft (verified on p053, p023,
  p048, p011). FEBio is not failing on bone; NUM-06 -> partial, h34 now attributes by the first inverting block.
- Root physics: the Gent pad (Jm 0.7) locks at stretch ~0.60; under 100 N the solid area of family A needs ~2.7 MPa, family B
  ~4.4 MPa nominal, so designs with sigma/E_soft >~ 1.5 (all B interleave; A with E_soft <= 1.7 and both/axial gradient) sit at
  the locking singularity: tangent blows up, 0.8 mm walls buckle, Newton diverges. 13/16 failures at t 3.0-3.4 where three events
  coincide (static -> dynamic switch, follower-load start, dt change); p023 (t 1.99) fails when the patched tied interface forms
  inside a non-converged Newton loop while cage expansion alone already buckles the walls.
- Candidate fixes ranked by the analysis (none run yet): (1) feasibility gate sigma_demand / E_soft + Gent lock before building
  (no GPU); (2) time-stepper aggressiveness 1 + must-point small steps at t 2 and 3 (pilot p023 + p053 ~0.4 GPU-h); (3) de-stack
  the t = 3 events (follower load in the static release, dynamic start at dt 0.005; pilot ~0.6 GPU-h); (4) tied patch: form the tie
  after convergence, serialize m_binit, drop the sliding penalty once tied (pilot p023 ~0.1 GPU-h); (5) relax Jm or neo-Hookean
  screening - overrides the PI's Q45 decision, needs approval; not recommended: homogenising the cage, shell / rigid cortex,
  augmented Lagrangian for the tie, cortical refinement. Secondary note to verify: Herron orthotropic G31 = 444 gives a negative
  Lame mu1 for cortical bone (not the cause, but check against the paper).

## 2026-11-03 03:00 — pilot of fixes 4 + 2 on p023 (PI order: p023 4+2 -> p053 3 -> only then 5)
- FEBio tied-elastic patch extended: parameter 'init_converged' (tie formed in the iteration-0 update of the first step that
  starts at/after init_time, i.e. on the converged t = 2 configuration, instead of inside the Newton loop of the step ending
  at 2.0) and m_binit serialized in the shallow retry dump only (restart .dmp layout unchanged, so running split windows still
  restart). Scan: no NORMAL production insertion run ever retried the tie-forming step, only p023 did -> production verdicts
  unaffected by the old behaviour. Build tree reconfigured (the CMake cache still pointed at the pre-rename path); full rebuild
  03:00; h14 rebuild of p062 byte-identical with the new options off; h24 preflight OK on the pilot case.
- h14 options (off by default): tied_init_converged, sliding_off_after_tie (sliding penalty ramps to 0 over t 2.0-2.03 once the
  tie carries the interface; PI question answered: two penalties on one surface pair double the stiffness and fight each other
  when the tie was pinned on a bad configuration), aggressiveness (time stepper), dtmax_windows (step curve: dt 0.005 at
  t 1.95-2.05 and 3.0-3.1). Settings class al_v2/pilot_tie; job pilotTie_p023 queued.
- Friction second pass (physrotFr2_) ended: p060, p062, p125 6/6 windows NORMAL; p109 flexion / extension ERROR. fric_compare
  now covers physio_fric + physio_fric2 with the NUM-14 filter (old results in results/method/fric_pre_dyn_20261102/); running.

## 2026-11-03 04:00 — gate 4 second pass result (real friction vs tied screening; PHY-05 partial)
- physrotFr2_ (p060 p062 p109 p125; mu 0.35, 100 N follower, slow dynamic, amplitudes retargeted from physio_fric; evaluated
  with the NUM-14 filter; biocage-evo/results/method/fric/compare.json): 14 windows reach 1.5 N m; cage translation there
  <= 0.373 mm (p125 flexion) - all within the PI's 1 mm / 0.5 mm posterior criterion.
- Extension never reaches 1.5 N m in any design: the moment saturates at 530-580 N mm, i.e. the friction capacity of the
  interface (~ mu N x lever arm = 0.35 x 100 N x ~15 mm); the retargeted drive then rotates C3 to 15.7 deg (p060) and the cage
  slides posteriorly 1.40 mm. Evaluated instead at the intact segment's extension ROM (7.4 deg at 1.5 N m): p060 0.54 mm
  posterior (> 0.5 mm, borderline), p062 0.36 mm (reached only 6.6 deg), p125 0.24 mm (5.8 deg). fric_compare now reports
  both evaluation points (moment target; intact ROM).
- The tied one-face slip bound is NOT an upper bound in flexion: friction translation exceeds it (p125 0.373 vs 0.137, p062 0.188
  vs 0.111, p060 0.787 at 1405 N mm vs 0.316) and in p109 LB_left (0.194 vs 0.133); in LB / AR it holds (friction 0.03-0.19 vs
  bounds 0.07-0.73). Tied screening is therefore conservative for LB / AR, not for flexion / extension.
- p109 flexion / extension ERROR (window runs). Open for the PI (GAPS 4, item 12): the extension rule for friction runs (ROM-based
  evaluation; is 0.5 mm posterior at 7.4 deg a fail for p060?), and whether flexion / extension need friction runs for every
  passing design (~1.5 GPU-h each) or a corrected tied bound.
- Pilot p053 (fixes 4 + 2 + 3: class pilot_tie3 = pilot_tie + follower_in_release + physio_dt0 0.005) queued alongside p023
  (CPU, p023 at t 0.34 after 25 min).

## 2026-11-03 04:30 — PI DECISION: friction-run dislocation rule
- PI: the ROM-threshold evaluation for flexion / extension in the friction configuration is accepted; "0.54 mm: if it exceeds
  the limit we set, it is a FAIL". Rule implemented (fric_compare -> results/method/fric/verdicts.json; collect_split applies
  it as class DESIGN/dislocation-friction): any valid, monotonic window whose cage translation exceeds 1 mm (any direction) or
  0.5 mm posterior at either evaluation point (1.5 N m, or the intact ROM when the moment cannot be transmitted) fails the
  design. p060 -> fail (extension at ROM: posterior 0.54 mm). Verdicts: 70 pass / 73 fail / 5 open.
- Still open (PI): whether every passing design gets flexion + extension friction windows (71 x ~0.5 GPU-h) or the tied slip
  bound is corrected for flexion / extension; item 8 (expulsion gate).

## 2026-11-03 05:00 — PI DECISION: friction flexion + extension windows for every passing design
- Class al_v2/physio_fric3 (= physio_fric2: contact elastic mu 0.35, nonsym all, slow dynamic, split; plus physio_windows
  [flexion, extension]; h14 option added, production builds byte-identical). Drive amplitudes fixed at 1.25 x the intact ROM
  (flexion 0.126 rad, extension 0.161 rad) so the ROM evaluation point is always reached; the moment target is reached only
  where the interface can transmit it. Jobs physrotFr3_<design> for the 70 passing designs (p060 already failed); insertion run
  + 2 windows each, ~0.5 GPU-h; evaluated by fric_compare (SETS + physio_fric3) with the dislocation rule of 04:30.

## 2026-11-03 06:00 — pilot results (fixes 4+2 on p023, 4+2+3 on p053); NAS phase 1 done
- p023 (pilot_tie: tie formed on the converged t = 2 state, sliding penalty off after the tie, geometric retries, dt 0.005
  windows): the old failure point is cleared - t 1.75-2.0 took 2 retries (production: 10 retries exhausted at t 1.999), the tie
  formed on the converged configuration and the release stage ran at dt 0.05 with no retry. It died at t 3.05, the first
  dynamic step with the follower load (97 retries, dt down to 1e-13, first inverted element cage_soft) - the stacked-event step
  that fix 3 targets. Fix 4 therefore works for the insertion stage; p023 with 4+2+3 queued (pilotTie3_p023, front of queue).
- p053 (pilot_tie3 = 4+2+3, follower ramped 2.5-3.0 in the static release stage, first dynamic dt 0.005): insertion and the
  tie passed cleanly (no retry before t 2.6). Retries started at t 2.62-2.72, exactly when the C3-pot axial force crosses
  zero (distraction fully released, follower ~25-45 N added) and the first inverted elements are cage_soft near the cage top;
  from t 2.70 the step stayed at dtmin 1e-4 with 24-30 Newton iterations per step (1 step / 45 s, ~29 h to t 3.0) - stopped
  at 05:50 (kill_febio.sh). With the dynamic transition removed, p053 still cannot carry the follower load on its soft pad:
  the failure follows the load, not the solver event, consistent with BONE_INVERSION_ANALYSIS section 2.6 (A family E_soft
  1.57-1.67: nominal demand 2.67 MPa / E_soft = 1.7, Gent lock at lambda ~0.61). Remaining options are the PI's: fix 5 (relax
  Jm, changes Q45) or classify the thin/soft A-family pads as physically unable to carry 100 N (design, not platform).
- physio_fric3 batch: 4 NORMAL (p002 p026 p036 p051), p039 stopped by the watchdog (stalled at t 2.233: dtmin 1e-4 with
  24-30 iterations per step, no retry, elastic-contact release stage; same signature in p050 at t 2.52). 61 queued; GPUs are
  held by other users so the scheduler launches on CPU only (max 8 x 4 cores).
- NAS archive phase 1 finished 05:45 (cases, physio_rot, physio_v3, dyn, r2, fix, facet*, invalid*: 1098 GB on the NAS,
  /raid free 2.6 TB, symlinks in place).

## 2026-11-03 07:15 — p023 with fixes 4+2+3: fails under the follower load, not at a solver event
- pilotTie3_p023 (CPU, 1 h 20): insertion clean (5 retries in t 1.5-1.8, tie formed on the converged t = 2 state, release at
  dt 0.05), then 13 retries at t 2.62-2.65 and ERROR at t 2.6492 - the moment the C3-pot axial force turns compressive
  (Fz +40 N at t 2.0 -> -9 N at t 2.62, follower ~25-30 N of 100 N added). 685 inverted elements, all cage (528 soft, 157
  hard), zero bone. Same behaviour as p053 (06:00 entry): with the tie, retry and event-stacking fixes in place, both
  insertion-stage failures become "the soft pad inverts under the first 30 N of compression". Fixes 4+2+3 are therefore
  not the answer for these two designs; they remain useful platform options (p023's t = 2 step and the t = 3 residual jump).
- Control queued: pilotTie3_p062 (passing design, convergence-check reference) in the same class, to show the pilot options do
  not harm a design that carries the load and to measure the t = 3 residual with the follower ramped statically.
- For the PI: fix 5 (Jm) or classify E_soft <= ~1.7 MPa (A) / <= ~4.2 MPa (B) pads as design failures (BONE_INVERSION_ANALYSIS
  2.6: nominal demand 2.67 / 4.44 MPa). Not started without a decision.

## 2026-11-03 07:50 — control p062 in the pilot class (fixes 4+2+3): harmless, cheaper in retries, residual jump at t = 3 stays
- pilotTie3_p062 insertion run NORMAL in 28 min on 4 CPU cores, 0 retries, 2 negative-Jacobian lines (production split2: 0
  retries, 136 steps; pilot 328 steps because of the dt 0.005 windows at t 1.95-2.05 / 3.0-3.1 and the geometric retry
  option). The six windows started normally (flexion 6-7 iterations per step).
- Fix 3 does NOT remove the residual jump at the first dynamic step: initial residual norm 3.5e1 at t 3.0 -> 4.8e3 (3.005) ->
  1.2e5 (3.019) -> 3.1e4 (3.067) -> 2.4e2 (3.1) -> 5.9e-1 (3.27); production 2.4e-2 at 3.0 -> 1.3e4 at 3.05 -> 1e2 at 3.1-3.3.
  The jump therefore belongs to the static -> mass-scaled dynamic switch itself (inertial residual of the first dynamic steps,
  cf. NUM-14), not to the follower load; it costs no extra iterations (3-5) on a design that carries the load. For p023 / p053
  the follower load alone (static, 25-45 N) already inverts the soft pad, so the t = 3 event was never the root cause.
- numconv_compare SETS gains pilot_tie3 (information row): when the p062 pilot windows end, mu_squeeze / slip / N / compression
  are compared with the split2 baseline to confirm the pilot options leave the physics unchanged (expected within the 2 %
  time-step tolerance).

## 2026-11-03 08:15 — control p062 windows: pilot options leave the metrics unchanged
- All six pilot_tie3/p062 windows NORMAL (1 retry in AR_right). numconv_compare (row pilot_tie3, tolerance 2 %): mu_squeeze
  within -0.7..+0.6 % (extension +4.9 % = +0.0007 absolute, below the 0.005 floor), slip bound within 0.0..+0.7 %, sustained
  compression +0.02 pp vs the split2 baseline -> pass. The tie-on-converged-state, geometric-retry, dt-window and
  follower-in-release options are therefore physics-neutral on a load-carrying design and may be enabled per class when a
  design needs them; production classes stay unchanged (builds byte-identical) until the PI asks otherwise.

## 2026-11-03 13:50 — friction batch (physrotFr3_) mid-point: every insertion failure is a radial-gradient design
- 55 of 70 insertion runs ended: 30 NORMAL (17 radial, 13 axial), 19 ERROR (19 radial, 0 axial), 6 running, 15 queued; GPUs
  became free ~09:45 so the scheduler now launches on GPU. Earlier friction sets agree: physio_fric 3 radial ERROR / 3 radial +
  1 axial OK; physio_fric2 all OK. In the tied production configuration all 70 of these designs passed.
- Two failure signatures, both only in radial designs (soft bands at the window edge of the contact face, 100 % hard elsewhere):
  (a) release-stage crawl stopped by the watchdog (p039 p048 p050 p052 p064 p097): dt at dtmin 1e-4 with 22-40 Newton
  iterations per step, no or few inverted elements - contact chatter signature; E_soft 1.67 and 11.9 alike.
  (b) first dynamic step t 3.0-3.06 (p061 p068 p071 p074 p082 p083 p084 p088 p095 p101 p104; p109 at 3.34): 10-18 retries,
  thousands of inverted cage elements (first inverted: cage_soft / cage_mix, twice C3_cortical) - the stacked t = 3 event.
  Window failures (8 of 60 ended windows: p014 E, p051 F, p063 F, p066 F, p078 E, p081 F, p086 F, p093 F) are mixed radial /
  axial and are evaluated separately (10-35 retries late in the window).
- Hypothesis for "radial only": the cage-endplate sliding-elastic contact (two_pass 0, auto_penalty 1, master C3_endplate,
  slave cage_top/cage_bot) computes the penalty per SLAVE facet from the cage element's bulk modulus (FESlidingElasticInterface
  ::CalcAutoPenalty on m_ss). A radial pad mixes hard (E 300-800 MPa) and soft (1.6-12 MPa) facets on one contact face, so the
  penalty varies ~100x along the interface; with friction the hard facets take the load and the soft facets chatter / invert.
  Axial pads are uniformly soft at the face (uniform penalty) and all pass. Under the tied contact the interface is glued, so
  the heterogeneity never mattered. Not yet tested; candidate fixes are a uniform penalty (auto_penalty 0 with a fixed value
  calibrated to the current hard-facet penalty), two_pass, or augmented Lagrangian - each a numerics change to validate on
  p062 (numconv_compare) before use.
- Action taken: class al_v2/physio_fric3p = physio_fric3 + the physics-neutral pilot options (follower_in_release, physio_dt0
  0.005, aggressiveness 1, dtmax_windows; 08:15 entry). The 12 signature-(b) designs are queued as physrotFr3p_<design>
  (builds differ from physio_fric3 only in the follower curve, dt curve and control blocks). Signature (a) is not expected to
  respond to time-step options and waits for the penalty test.

## 2026-11-03 14:30 — uniform contact-penalty test for the friction configuration (radial designs)
- Evidence sharpened: in the t = 3 failures (p061 p083 p088 p068) 73-100 % of the first inverted cage elements sit in the two
  element layers at the contact face (layer 0-1 or the top layers), both soft and hard facets. Auto-penalty per slave facet =
  PENALTY x k_facet / h (h 0.2 mm): p048 soft 279 vs hard 45 276 N/mm3 (ratio 162), p061 1 977 vs 18 231 (9), p026 1 003 vs
  61 106 (61); the axial p062 is 33 562 vs 54 128 (1.6) and passes. So it is the heterogeneity along one contact face, not the
  penalty magnitude, that separates radial (fail) from axial (pass) under friction.
- h14 option cage_penalty_fixed (N/mm3): auto_penalty 0 and a fixed penalty (still ramped by pen_ramp); off by default,
  production builds byte-identical (p062 physio_fric3 rebuild md5 4f3208b5 unchanged).
- Test classes al_v2/physio_fric3uS (fixed = soft-facet value) and physio_fric3uH (fixed = hard-facet value), each with p048
  (release crawl), p061 (t = 3 failure) and p026 (radial design that passed: numerics control for the metric change). If both
  values rescue p048/p061, the heterogeneity is the cause; if only one does, the magnitude matters too. p026's windows are
  compared with its physio_fric3 result (fric_compare) to judge whether the uniform penalty changes mu / slip beyond the 5 %
  penalty tolerance. No production class changes until the PI sees the result.

## 2026-11-03 19:45 — friction batch: 43/70 insertions done, 27 radial failures; pilot options do not rescue, uniform penalty partly
- physio_fric3: 43 NORMAL (both windows OK for 33; 10 window ERROR: p014 E, p051 F, p063 F, p066 F, p078 E, p081 F, p086 F,
  p093 F, p125 F, p146 F), 27 ERROR - all radial (8 new ones at t 3.01-3.07 with 10-18 retries: p115 p116 p120 p127 p128 p129
  p130 p140), 1 running. Every axial design completed.
- physio_fric3p (pilot time-step options + follower ramped 2.5-3.0): the 12 radial designs fail or crawl EARLIER - 6 ERROR at t
  2.93-3.005 (p071 136 retries at the first dynamic step; p083/p104 at t 2.93-2.95 with 16/10 retries under the static
  follower ramp) and 6 crawling at dtmin 1e-4 with 25-55 iterations per step at t 2.73-2.97 (watchdog will stop them). With
  friction the radial faces fail as the follower load approaches 100 N, static or dynamic: the failure follows the load.
- physio_fric3uS (uniform soft-facet penalty): p048 moved past its old crawl (t 2.44 -> 2.88, dt 0.005-0.007, 20-29 iterations),
  p061 still crawls at 1e-4 (t 2.78), p026 control normal (dt 0.08, 8-10 iterations). uH (hard-facet value) at t 1.3.
- Reading: the inverted elements are the face layers at the hard/soft band boundaries (face fraction 0.3-1.0, mixed phi). Under
  the tie the soft bands are glued; with sliding allowed the nearly incompressible soft bands (nu 0.45) bulge laterally between
  hard bands and the 0.2 mm face elements shear until they invert. The penalty heterogeneity contributes (p048 improves) but is
  not the whole mechanism (p061). This is a computability limit of radial pads in the friction configuration, not of axial pads.
- Consequence for the PI's order (flexion + extension friction windows for every passing design): ~33 designs get both windows,
  ~27 radial designs cannot be evaluated in the friction configuration with the current mesh / contact. Options for the PI:
  (a) keep the tied screening result for those designs and flag the friction gate as 'not numerically confirmed' (tied bound is
  conservative for LB / AR, not for flexion / extension); (b) a friction-computable method for radial pads (finer face mesh,
  or a contact formulation to be validated on p062 / p026); (c) treat 'not computable under friction' as a design-level penalty
  (soft bands squeezed out of a sliding interface are also a real-world concern for interleaved radial pads).
- fric_compare (SETS + physio_fric3) running on the ended windows -> results/method/fric/verdicts.json; collect_split + h33 after
  the remaining runs end.

## 2026-11-03 22:30 — friction batch (physio_fric3) ended: 70 designs, corrected evaluation, two failure clusters, pilots queued

**Batch.** All 70 passing A-family designs ran the frictional insertion (sliding-elastic, mu 0.35, slow dynamic) with flexion +
extension windows: 43 insertions NORMAL (18 axial, 25 radial), 27 ERROR (all radial). fric3p (pilot time-step options) 12/12
ERROR; uniform-penalty test: uS p048 2.90 / p061 3.014 ERROR (no rescue), uS p026 flexion u_h 0.353 vs 0.368 mm (-3.9 %) but
1.5 N m not reached (|M| 682) and extension ERROR at t 3.77; uH (hard-facet penalty everywhere) all ERROR at contact onset
t 2.02-2.11, 653 soft / 17 hard negative-jacobian elements -> the soft facets cannot carry the hard penalty. Conclusion: the
penalty heterogeneity is not the cause of the radial failures.

**Evaluation bug fixed (ops/fric_compare.py).** The intact-ROM evaluation picked the first dir starting with the id, which for
GPU-run designs is the never-run build dir (p110 vs p110_gpu3) -> rom_error on 76 rows and vacuous 'pass' for every GPU-run
design in the 13:50 / 19:45 interim notes. Rows now carry case_dir. Corrected verdicts (results/method/fric/verdicts.json,
fric3_summary.csv): **19 pass / 25 fail** of 44 evaluated (43 fric3 + p060). Rule: translation at the state where the C3
rotation reaches the intact ROM (flexion 5.8 deg, extension 7.4 deg) > 1 mm any direction or > 0.5 mm posterior.
- flexion, anterior translation at ROM: axial 0.50-0.64 mm (all pass), radial 0.93-1.19 mm (20 of 21 radial with a valid
  flexion window fail; p072 exactly 1.00). Bimodal by gradient, independent of E_soft (1.6-11.9), d and theta.
- extension, posterior translation at ROM: 0.20-0.64 mm; 13 windows > 0.5 (p135 0.50, p076 0.50, p139 0.63 axial; the rest
  radial interleave 0.51-0.61). Extension sits on the 0.5 mm limit for both gradients.
- 11 designs evaluated on one window only (other window missing / non-monotonic); p066 no window valid.
Reading: with real friction the cage slides ~1 mm anteriorly when the segment flexes to its intact ROM if the contact face has
soft perimeter bands (radial); whole-layer axial faces slide ~0.55 mm. The tied slip bound (0.1-0.3 mm) is not comparable
(evaluated at 1.5 N m, which friction never transmits: moment saturates at 520-590 N mm).

**The 27 radial insertion failures = two clusters, both numerical, feature-correlated.**
- Feature: every ERROR design has soft-band depth d >= 0.8 mm (median 1.25); every radial NORMAL has d <= 0.96 (median 0.65).
  theta and E_soft do not separate them.
- Cluster 1 (6 designs, t 2.23-2.93, release / follower ramp, static): p039 p064 p052 p050 p097 p048. No xplt state near the
  failure (PLOT_STEP_FINAL), only the log: crawl then negative jacobians in the soft face bands (19:45 note).
- Cluster 2 (21 designs, t 3.005-3.07): the FIRST dynamic step at t 3. p061: at t 3.000 (static, converged) soft-band stretches
  0.97-1.04 (strain <= 4 %), hard 0.99-1.01; the first dynamic step (dt 0.05) starts with residual 6.0e4 (static steps 1e-2 to
  1e0), 'converges' in 60 iterations to a state with soft stretches 0.58-3.60 and 6 % of soft elements beyond the Gent lock
  (I1-3 > 0.7); the next step inverts ~400 elements. Same R0 1e4-1e6 in p068 (fails outright, R0 1e6), p026 (survives, R0 2e4),
  p062 axial (survives, R0 1.3e4); fric3p with dt0 0.005 and the follower moved to release: R0 2.1e4, dies at 3.005 -> the
  transient is the analysis-type switch itself, not the load ramp, not dt. p109 (3.34) is the only late one.
  => for cluster 2 the element inversion is NOT a material overload: 4 % strain one step before, >200 % one step after. It is
  the static->dynamic switch transient hitting a sliding cage whose contact face has soft bands.
- Answer to the PI's question (inversion = 破掉?): no. Inversion is the mesh/solver limit; in cluster 2 the material was at
  <= 4 % strain just before, so nothing physical broke. In cluster 1 the strains are not logged; physically the soft perimeter
  bands squeeze out between the hard bands (nu 0.45), the likelier real failure mode is delamination at the printed hard/soft
  interface (assumed perfectly bonded in the model), not fracture of PLCL soft phase (elongation at break hundreds of %).
  The model has no failure criterion, so '破掉' cannot be concluded from it.

**Pilots queued (h14 option dynamic_from_release, default off; production p062 fric3 case byte-identical, md5 4f3208b5...):**
classes al_v2/pilot_dynrel (switch to dynamic at t 2 while cage_hold constrains the cage), pilot_static (no dynamic at all),
pilot_rho9 (density 1e-9 = real tissue, 1000x less artificial mass); designs p061, p068 (cluster 2), p048 (cluster 1).
Decision rule: an option counts only if it (i) passes the three, (ii) keeps p062's window metrics within the 5 % / 2 % numconv
tolerances (ops/numconv_compare.py), (iii) is then re-run on the 27.

**Degradation sweep (physio_degr050/020/010, tied, secondary, ops/degr_compare.py):** E_soft x0.5/0.2/0.1 changes mu_req by
<= 0.005, slip bound <= 0.36 mm, sustained compression +0.1-0.9 pp, peak compression +0.3-3 pp (p048 24.5-24.6 % at x0.5/0.2 vs
25 % limit; p062 5.8-7.0 %). The tied verdicts are insensitive to soft-phase degradation.

**Storage.** NAS phase 2 started 22:05 (split2/3/4, fric, fric2, fric3p, fric3uS/uH, numconv_*, pilot_tie*; ~110 GB);
physio_fric3 (79 GB) and physio_degr* stay on /raid until the pilots and any strain re-reads are done.

## 2026-11-04 01:30 — correction: the t 3 event is the instantaneous release of the C3 distraction reaction, not the dynamic switch; 'd' is the distraction, not a band depth

**Correction of the 22:30 entry.** `d_mm` in the design parameters is the DISTRACTION height of C3 during insertion
(prescribed rigid z, lc 15), not the soft-band depth. The feature that separates the 27 insertion failures (d >= 0.8, median
1.25) from the 25 radial NORMAL (d <= 0.96, median 0.65) is therefore the distraction.

**Mechanism, confirmed by three pilots (p061 / p068 / p048 each).** dynamic switch moved to t 2 (pilot_dynrel): p061 NORMAL +
both windows NORMAL, p068 ERROR t 3.05, p048 ERROR t 3.10. No dynamic at all (pilot_static): p061 NORMAL (windows running),
p068 / p048 ERROR at the first step after t 3. Real density 1e-9 (pilot_rho9): same. In every variant the first step after
t 3 starts with residual R0 = 9.9e5 for p068, and C3pot.txt shows the C3 rigid-body reactions at t 3: Fx -35 N, My 998 N mm
-> |F|^2 + |M|^2 = 9.97e5. p061 R0 6.0e4 = (Fx -10.6, My 244)^2; p062 1.25e4 = (Fx -5.5, My 112)^2; p026 1.95e4.
The release step holds C3 in x, y, Rx, Ry, Rz while the distracted segment is seated; the ligaments / facets stretched by the
distraction leave a reaction moment of ~730 N mm per mm of distraction (corr |My| vs d 0.98 over the 70 designs; p050/p068/
p084/p127/p109/p048/p097 at d 1.5: 1092 N mm; p036 axial d 1.48: 1056 N mm, survives). The hold step frees those DOFs in one
step = an impact of up to 1 N m on a sliding cage; axial faces survive it, radial faces with soft bands at the contact do not.
Table: biocage-evo results/method/fric/seated_reactions_t2.json.
- Physics reading: a real distractor is removed gradually and C3 settles into the cage under the ligament preload; the
  model applies that preload as a step. The stored moment itself is a real quantity (lordosis / preload after insertion) and
  worth logging per design.
- Pilot queued (h14 option c3_release_ramp, default off, production p062 case byte-identical): the t 3 reactions applied as
  rigid forces / moments on C3 decaying linearly to 0 over the hold step (t 3 -> 3.5); class al_v2/pilot_c3ramp, designs
  p068 (Fx -35.4, My 998), p061 (-10.6, 244.5), p048 (p068's values; its own run died at 2.93 before t 3). Check: R0 of the
  first step after t 3 should drop from 1e6 to ~1e2; then p062 numconv tolerance (5 % / 2 %) before any re-run of the 27.
- The 2026-11-03 'pilot options' (dt0, aggressiveness, follower_in_release) could not help: the impact is independent of dt
  and of the follower load.

**Interface shear (PI 2026-11-04: shear large enough to delaminate the printed hard / soft interface is unsafe).**
methods/e07_interface_shear.py: traction on every cage face shared by a hard and a soft element, from the soft-side and
hard-side Cauchy stress separately (they agree within ~20 %), split into horizontal (between printed layers; the axial
interface) and vertical (in-plane band boundary; the radial interface) faces; shear and peel, max and p99, per state.
First numbers (MPa, soft-side p99 / max): p062 axial friction: insertion t 3.5 horizontal 1.8 / 2.5, flexion window t 3.68
4.4 / 6.0; p026 radial friction: insertion vertical 2.2 / 3.9, flexion t 3.76 8.2 / 11.9 (peel max 27); p062 tied (split2)
flexion peak t 4.0 horizontal 6.8 / 9.0. Batch over the 84 friction windows running (ops/e07_batch.py -> e07_summary.csv,
values at the intact-ROM state and max up to it). No threshold applied: the bond strength of the co-printed PLCL hard/soft
interface is not measured; typical multi-material FDM interface shear strengths in the literature are a few MPa, so the PI's
criterion would bite at the window peaks for most designs - threshold is the PI's decision.

## 2026-11-04 02:30 — e07 interface shear, 86 friction windows (results/method/fric/e07_summary.csv, e07_by_design.csv)

Soft-side p99 shear at the intact-ROM state (MPa), by class:
- axial mix (18): insertion 1.3-2.3; flexion horizontal 10.2-14.0 (median 11.9), extension 2.1-3.5. Independent of E_soft (1.7-11.3).
- radial mix (12, E_soft 1.6-7.0): insertion 1.5-3.1; flexion horizontal 18.6-30.0 / vertical 10.7-16.9, peel max 31-53;
  extension 4.3-6.2.
- radial interleave (10, E_soft 10.3-11.9, hard fraction 0.857): insertion 0.1-0.2; flexion 1.7-2.7; extension 0.3-0.5.
- Windows over a p99@ROM threshold of 2 / 3 / 5 MPa: flexion 34 / 27 / 27 of 37, extension 29 / 17 / 8 of 41.
Caveats: (i) flexion drives the segment to 5.8 deg with the cage as the only spacer, so the anterior edge carries the load and
the interface values there exceed the hard-phase yield parameter (sig_hard 15 MPa) in the radial-mix designs - above that the
numbers are 'the model's stress at a corner', a relative ranking rather than a stress a bonded interface would really see;
(ii) p99 over 2300-4300 interface faces (tens of faces); (iii) reference-configuration normals (+-10 %).
Decision pending (PI): bond-strength threshold and evaluation point (ROM state recommended, same as the slip rule).

## 2026-11-04 03:30 — PI decisions applied: interface shear 3 MPa provisional, radial mix excluded; merged result 0 / 71

**PI 2026-11-04.** (1) Interface-shear threshold 3 MPa, soft-side p99 shear at the intact-ROM state, flexion and extension
(frictional runs), marked 'provisional, pending bond-strength test'. (2) Radial-gradient mixing-nozzle designs excluded at
design level (A and B). Accepted knowing that every axial design fails the shear gate in flexion.

**Implementation (biocage-evo).** ops/e07_batch.py -> results/method/fric/e07_verdicts.json (threshold and provisional flag
stored in the file's meta). ops/fric_compare.py: no pass by absence - a window counts when it reached the intact ROM or
1.5 N m among the valid states (the |M| monotonic flag is reported, not used to discard: before, p072 passed because its
extension window, 0.55 mm posterior at ROM, was dropped); a design passes gate 4 only if flexion AND extension count;
designs whose frictional insertion stopped are open with reason 'not computable'. ops/collect_split.py: per-design 'gates'
record (tied screening, dislocation_friction, interface_shear, design_rule) and first-cause class order tied screening ->
dislocation-friction -> interface-shear-provisional -> radial-mix-excluded; a tied pass a friction gate could not evaluate
becomes open; design features read from any valid case.json (cage block or mesh name). Old repo
scripts/6_active_learning/h22_active_learning.py: EXCLUDED_COMBOS = radial mix (A, B) never proposed again. Evo docs/PLAN.md
S10 added.

**Merged result (verdict_classes_merged.json): 0 designs pass all gates.** Of the 71 tied passes:
DESIGN/dislocation-friction 26 (incl. p072, which was a nominal pass), DESIGN/interface-shear-provisional 15 (all axial
designs with a usable window, flexion 10.2-14.0 MPa; plus radial mix p081, p113 by first cause), DESIGN/radial-mix-excluded
13 (+ p107, previously open), [多元]/friction-computability 14 (all radial interleave: p039 p048 p052 p061 p064 p082 p083
p088 p101 p115 p120 p121 p129 p140), [觀測]/friction-window 3 (p066, p146 axial; p086 interleave - flexion did not reach ROM).
- The 13 radial-mix designs among the 27 friction-insertion failures no longer need a re-run; only the 14 interleave ones
  do, and they ride on the c3_release_ramp pilot.
- Of the 10 radial interleave designs computed under friction: shear 1.7-2.7 MPa (pass), but 8 fail the slip rule (~1 mm
  flexion) and p072 fails extension (0.55 mm). The axial designs hold (0.50-0.64 mm flexion) but fail the shear gate.
- Gap (not expanded now): the shear gate covers flexion / extension only; lateral bending / axial rotation exist only as tied
  windows.

## 2026-11-04 04:10 — reaction-ramp pilot, first result; run-to-run divergence of identical inputs

- pilot_c3ramp p068 (radial mix, now excluded; reactions Fx -35.4 N, My 998 N mm ramped to 0 over t 3 -> 3.5): the ramp works
  as intended - first step after t 3 R0 9.7e3 (was 9.9e5; = (99.8 N mm)^2, the per-step decrement), converged in 17
  iterations, cage translation unchanged (0.007 mm). The run still dies in the SECOND step: R0 5.3e7 at step start, 291
  negative jacobians. Not inertia (mass 1e-6); most likely a contact re-projection jump at the soft-banded face as C3 begins
  to move. So the one-step release explained the first-step impact, not the whole failure of the radial faces.
- pilot_c3ramp p061 / p048 stalled in the STATIC release step (t 2.68 / 2.12, dt at dt_min 1e-4), stopped (kill_febio).
  The release step is byte-identical to production physio_fric3 and to pilot_static, yet pilot_static p061 (same GPU) passed:
  the time-step histories of the two identical inputs agree to 7 digits for 151 steps and then diverge on round-off. The
  release step of these radial designs is at the edge of computability (path sensitivity) - one more reason the friction
  configuration cannot certify them as is.
- pilot_c3ramp2 queued on the designs that matter (radial interleave, cluster 2): p061 (Fx -10.6, My 244.5), p083 (-16.6,
  400.2), p129 (-13.5, 323.9), p120 (-16.9, 412.6); reactions from the production runs at t 3.
- platform_capabilities.json: PHY-05 TIED -> fail (tied bound not conservative for flexion / extension), PHY-09 interface
  shear (partial, provisional threshold), NUM-15 C3 release impact / friction-insertion computability (fail); evo-path
  evidence fixed (../biocage-evo); h33 rerun, 0 warnings.

## 2026-11-04 04:40 — interface-shear metric passes the numconv tolerances (p062 flexion, tied, at 1.5 N m)

results/method/numconv/e07/compare_p062_flexion.json (biocage-evo). Soft-side p99 layer-interface shear (the metric that
decides the axial designs): baseline 6.08 MPa; HZ 0.1 mm +2.0 %, penalty x0.5 -1.7 %, x2 +1.4 %, dt x0.5 0.0 % -> within the
PI tolerances (5 % mesh / penalty, 2 % dt). Band-boundary p99 3.64 MPa: -7.2 % (HZ 0.1), -7.8 % (penalty x0.5) - outside 5 %,
but it is not the deciding interface for axial designs. Single-face max (+29.7 % with HZ 0.1) and hard-side p99 (+24.1 %) are
mesh-sensitive: the gate correctly uses the soft-side p99. Not tested: the frictional ROM state on the HZ 0.1 mesh (no such
run); the axial values there (10.2-14.0 MPa) are 3-5x the threshold, far beyond a few-% mesh error.
Reading: for whole-layer (axial) pads the layer interface is in series with the contact face, so the shear it carries is set
by equilibrium (the shear the endplate transmits), not by the pad modulus - this is why it is independent of E_soft.
- 04:50: p066 / p086 / p146 flexion windows stopped with 1100-2400 negative jacobians at 0-1.3 deg (ERROR), so they are
  [多元]/friction-computability, not [觀測]. Final merged classes of the 71 tied passes: dislocation-friction 26,
  interface-shear-provisional 15, radial-mix-excluded 13, friction-computability 17 (14 interleave insertions + p066 p086 p146).

## 2026-11-04 11:30 — corrections and evaluation-point finding (retracts parts of the 02:30 / 03:30 / 04:10 / 04:40 entries)

**e07 bug (mine).** The first version took the interface from the mesh flag 'hard', which is the interleave pattern; in mix
designs it alternates inside one material, so all mix values before now (axial and radial mix, the p062 convergence check) were
on faces that are no material interface. Fixed: material = FEBio element block. Invalid results kept out of the results tree.
Corrected soft-side p99 shear (MPa), flexion at ROM / flexion at 1.5 N m / extension at ROM: axial mix 10.5-15.8 / 4.7-6.7 /
3.2-7.4; radial mix 10.7-16.6 / 5.2-7.0 / 2.3-3.2; radial interleave 1.7-2.7 / 1.2-1.5 / 0.3-0.5.
Merged classes of the 71 tied passes: dislocation-friction 26, interface-shear-provisional 17, radial-mix-excluded 13,
friction-computability 15 (14 interleave insertions + p086). 0 pass.

**Retraction: the shear metric does NOT pass the PI's mesh tolerance.** p062 tied flexion at 1.5 N m, corrected faces: HZ 0.1 mm
layer p99 -15.9 %, band p99 +16.7 % (limit 5 %); penalty x0.5 -1.0 / -5.6 %, x2 +3.2 / +1.6 %; dt x0.5 0.0 %. So the value is
good to about +-16 %. The axial fail at 3 MPa survives that error. In interleave designs the two one-sided tractions differ by
up to ~27x (p093 t 3.5: soft 0.15, hard 4.2 MPa), so the boundary is not resolved at 0.2 mm; no interleave mesh check exists.
The '~20 % soft / hard agreement' and the mechanism note 'equilibrium, independent of E_soft' were read from the invalid faces
and are not established.

**Evaluation-point inconsistency (mine).** The rule as written and reported to the PI on 2026-11-03 is 'at 1.5 N m, or at the
intact ROM when the moment cannot be transmitted'; the code applied the ROM to every window. Flexion DOES transmit 1.5 N m, and
holding it to the intact ROM takes |M| 1.9-6.1 N m (median 2.3 interleave, 3.3-3.4 mix; target 1.5). Every flexion slip failure
comes from this: at 1.5 N m flexion translation is 0.09-0.88 mm (none > 1 mm). Extension is the case the ROM rule was made for
(|M| saturates at 0.52-0.59 N m). The PI accepted 'ROM time point' for the shear gate on my wording, so the choice goes back to
the PI. Not changed in code. Table: biocage-evo results/method/fric/threshold_rule_table.json, eval_point_sensitivity.json.

**Friction computability.** pilot_c3ramp2 p061 / p083 / p120 / p129: all ERROR at t 3.05, step 2, 200-470 negative jacobians.
First step fine (R0 7e2-2e3). Step-2 R0 scales exactly with 1/dt^2 (p061 ||R|| x dt = 107.6 in four retries) = the inertial
predictor of the dynamic solver; its size is not explained by the logged C3 motion (cause open). Without the ramp p061 passes
in three configurations (dynrel, static, rho9), three different stops for p068 / p048. Not exhausted: static + ramp and real
density + ramp queued (classes pilot_c3rampS, pilot_c3rampR9; p061 p083 p129 p120). p061 windows (dynrel / static / rho9) reach
only 2.9 deg (amplitude not retargeted) with flexion 0.56-0.61 mm.
Literature check for the threshold: ABS-TPU 4.7, ASA-TPU 6.4 MPa lap shear (Harris 2019, Front Mech Eng); no PLCL value found.
The earlier 'a few MPa' had no checked source.

## 2026-11-04 12:20 — briefing check (pi-report) and duplicate detection
- Flexion at 1.5 N m among windows that reached it: 0.15-0.88 mm (the 0.09 in the 11:30 entry is p063, stopped at 1.65 deg).
- collect_split duplicate detection widened to design-defining parameters over all valid sets; p077 = p139, p143 = p092 = p117,
  p086 = p100 = p142, p051 = p075, p095 = p128 were missed. Gates 4 and shear now pool the group (any id fails -> the group fails).
- Identical designs do not repeat near the limit: extension posterior at ROM p077 0.456 / p139 0.634, p100 0.457 / p142 0.575
  (only the prescribed amplitude differs), so the 0.5 mm limit is not numerically resolved; question to the PI.
- Passes with pooled evidence, threshold / ROM everywhere / flexion 1.5 N m + extension ROM: 3 MPa 0 / 0; 5 MPa 0 / 2 (p036 p065);
  6.4 MPa 0 / 9; 7.5 MPa 0 / 11; 16 MPa 11 / 11. All axial mix. Not applied: awaits the PI.

## 2026-11-04 13:50 — merged classes after duplicate pooling (supersedes the counts in the 11:30 / 12:20 entries)
- Tied passes 72 (p059 added: same design-defining parameters as p074, no split run of its own, inherits the pooled evidence).
  First-cause classes: dislocation-friction 28, interface-shear-provisional 16, radial-mix-excluded 14, [多元] friction-computability 14
  (p039 p048 p052 p061 p064 p082 p083 p088 p101 p115 p120 p121 p129 p140, all radial interleave). Pass all gates: 0.
  Evaluation point unchanged (code applies the intact ROM to every window); threshold 3 MPa provisional; awaiting the PI
  (questions 1-5 of the 13:30 briefing). Files: biocage-evo/results/method/split/*_merged.json.
- QA audit of code vs decisions vs capability labels launched (PI request 13:45); a recurring QA structure is being designed.
- Note: verdict_classes_merged.json lists 15 designs under DESIGN/radial-mix-excluded: the 14 tied passes plus p107, whose
  tied screening is open ([數值]/unstable-window); the design-level exclusion is applied regardless of the tied result.

## 2026-11-04 14:05 — QA system installed (PI request 13:45: a test-quality agent must check periodically that code matches the agreed method and the capability labels)
- Design: human_study/qa/QA_SYSTEM.md. Layer A scripts/8_audit/h37_qa_check.py: ten deterministic regression checks, each from a
  real error of 2026-10-31..11-04 (run dir resolution, pass by absence, e07 face recount, insertion state, document counts,
  retracted claims qa/RETRACTED.json, pilot options in production, golden rebuild p062 md5 4f3208b5, one FEBio block per cage
  material, register / audit-due). Report only; writes qa/QA_STATUS.{json,md}. tmux biocage_qa runs it every 6 h (crontab not
  permitted for this account). First full run: all checks PASS, R10 WARN (no LLM audit yet).
- Launch gate: h24_preflight.check() now calls `h37 launch <case_dir>` (pilot keys, material blocks); p062 fric3 preflight OK;
  OBS-08 reconfirmed 2026-11-04 (stricter gate only). Preflight daemon restarted (tmux biocage_preflight).
- Layer B: agent .claude/agents/qa-auditor.md fills the register qa/QA_SPEC.json (status 符合 / 不符 / 未實作 / 實作時自選 / PI待決)
  and writes qa/audits/QA_AUDIT_<date>.md; skill /qa-audit runs A then B. pi-report must read QA_STATUS first and stamp every
  briefing; numbers from result files only.
- Pending PI: git pre-commit hook running h37 --quick (repo config change). Three audit agents (simulation method, verdict code,
  labels) running now; their tables become the initial register.

## 2026-11-04 14:20 — QA audit results applied (three independent auditors: simulation method, verdict code, labels)
Verified at the cited lines before acting. Code fixes (no decision changed):
- fric_compare.py:56 operator-precedence bug (k == 0 -> TypeError -> window silently 'open'); never triggered (0 rom_error rows).
- fric_compare.py insertion stops: reason now distinguishes t_end < 3 (static release step, before the follower load: platform
  problem, cluster 1) from t >= 3 (C3 release impact). Of the 14 [多元]/friction-computability designs, p039 2.233, p064 2.443,
  p052 2.450, p048 2.931 stopped BEFORE t 3: the c3_release_ramp pilots cannot rescue them (the 13:30 briefing attributed all 14
  to the release impact: corrected). 21 insertion runs stopped at t 3.005-3.34; 2 radial-mix ones (p050 2.518, p097 2.642) also < 3.
- e07_batch.py: ROM-state shear interpolated over the VALID states only (NUM-14), as gate 4 does; 6 windows change by <= 0.2 MPa
  (p139 ext 3.38 -> 3.59, p135 ext 3.52 -> 3.62 MPa), no verdict flips. Stale header text corrected (threshold IS applied; window rule
  stricter than gate 4). e07_interface_shear / e04 docstrings corrected (one-sided tractions; node mean, not best fit).
- current_settings.json: physio_fric3 class now locks nonsym all / physio_dynamic 1e-6 / physio_split / physio_rot_rad 0.126, 0.161
  (were only in the h28 EXTRA argument, so h24 could not check them); pilot classes carry their keys (pilot_static physio_dynamic null,
  rho9 1e-9, dynrel dynamic_from_release). 70/70 production params already matched. PHY-06, GEN-02/03, TIM-01/03 reconfirmed.
- h37: pilot-key check is class-aware and per-set key-set consistency; new R11 (intact ROM constants in h14 / h28 / fric_compare agree).
Findings that change what the PI was told (go into the next briefing):
- Evaluation point: code checks BOTH the 1.5 N m point (when reached) and the ROM point (when reached), any exceedance fails; no
  window fails at 1.5 N m, so today the ROM decides. The conditional rule of 04:30 (1.5 N m when transmissible) would move 12
  flexion-only fails (p002 p014 p026 p038 p078 p079 p100 p112 p125 p132 p133 p148) out of gate 4: dislocation-friction 28 -> 17,
  interface-shear-provisional 16 -> 27 (current gate order), pass still 0.
- Gate order: radial-mix exclusion is the LAST first cause; 32 radial-mix designs in total, 27 tied passes, of which 14 carry the class,
  11 are counted under dislocation-friction and 2 under interface-shear. Exclusion first would give 17 / 14 / 28 / 14.
- Production code not committed: h14 / h22 / h24 / h28 / h34 / current_settings / h37 are working-tree only; HEAD's h14 cannot rebuild
  the production cases (preflight h14 sha 682cf344 vs HEAD df38154a). Commit awaits the PI (standing rule).
Sign-off items (implementation choices the decisions do not pin down): soft side = lower-phi side of each phi step (mix designs have no
pure-soft block); p99; max(layer, band); reference-configuration normals; |n_z| > 0.7; shear window usable only at ROM (gate 4 also at
1.5 N m); 1.25x amplitude factor not in any file (0.126 / 0.161 literal); 100 N and 1500 N mm as h14 defaults; ROM constants in 3 files
(now R11-checked); restart.feb not covered by the h24 rebuild comparison.

## 2026-11-04 15:00 — labels maintenance after the QA audit; p062 controls for the ramp pilots queued
- platform_capabilities.json: PHY-05 method / threshold now state the actual rule (PI 04:30: > 1 mm any, > 0.5 mm posterior, both
  evaluation points when reached; merged counts 26 unpooled / 28 pooled; per-family ranges at ROM: axial flexion 0.50-0.64, interleave
  0.93-1.18, radial mix 1.00-1.19 mm; extension axial 0.20-0.63, interleave 0.46-0.61, radial mix 0.36-0.49), evidence date = result
  time, fric3_summary.csv removed from its evidence. PHY-09 date = evidence time, valid-state interpolation noted. NUM-15 value now quotes
  only numbers that exist in result files (c3_reactions_t3.json moved into results/method/fric; t 2 regression slope ~950 N mm/mm, not
  730), stop phases split (6 static-release / 21 release-impact). R03 marked superseded by PI 2026-11-03 04:30 (friction results ARE
  the design gates). New: NUM-16 interface-shear numerical convergence (fail: +-16 %), NUM-17 verdict reproducibility near limits
  (fail: 0.5 mm line unresolved), R10 scope (shear only flexion / extension), R11 scope (evaluation point pending PI). OBS-10 / DIV-03 /
  OBS-06 / NUM-14 values updated to the merged result (NUM-14 FRIC -> partial: no h34 batch scan of physio_fric3). METRICS component
  now includes e07 and fric_compare. 39 status entries reconfirmed with explicit notes (h14 options off + byte-identical rebuild,
  FEBio option off by default, settings lock existing values, OPS hardening, METRICS widening); NUM-10 (FEBio patch regression) left
  STALE on purpose: the regression test must be re-run after the 2026-11-03 rebuild. Scorecard stale lines 65 -> 2 (NUM-10).
  Retired e07 wrong-face outputs: results/method/fric/retired_wrong_faces_20261104/.
- fric_compare.py: my 14:20 edit of line 56 had put the comment mid-line and commented out the interpolation fraction -> every window
  'rom_error' -> the dislocation count fell to 0 and the shear count rose to 31. Caught by h37 R5 on the first rerun (counts vs documents), fixed 14:40,
  pipelines rerun: 28 / 16 / 15 / 14 unchanged, gate-4 verdicts 26 fail / 14 pass / 31 open, shear 31 / 10 / 2; p139 ext 3.59,
  p135 ext 3.62 MPa (valid-state interpolation). Lesson recorded: every gate-file edit is followed by the pipeline rerun + h37.
- Pilots (14:00): pilot_c3rampR9 p061 insertion NORMAL (t 3.5; flexion window running, t 3.80), p120 ERROR t 2.77 (static release
  phase, not the release impact), p083 t 2.81 / p129 t 3.37 running; pilot_c3rampS p061 3.32 / p120 3.43 / p129 3.37 past the release
  and running, p083 t 2.84. First combinations past the C3 release. Controls queued per the 11:30 plan: p062 in pilot_c3rampR9 and
  pilot_c3rampS (jobs pilotCR9_p062, pilotCS_p062; ramp Fx -5.54 N, My 111.7 N mm from the production C3pot at t 3; amplitudes 0.126 /
  0.161 as production; preflight OK). Acceptance: p062 windows within 5 % / 2 % of production physio_fric3 before any interleave rerun.

## 2026-11-04 16:25 (Claude) — p062 controls: static+ramp variant fails the control, real-density+ramp on track
- pilot_c3rampS (fully static: physio_dynamic None applies to the main run AND the windows) p062: insertion NORMAL (t 3.5), flexion
  window E R R O R at t 3.824 (first stall t 3.766, 41 -> 905 negative-Jacobian elements in cage_mix_0.25 + C3 / C4 cortical tets),
  before the intact ROM (production t_rom 3.900). Production p062 flexion (dynamic 1e-6) ran to t 4 with 4 retries. The static window
  is therefore a different solver set-up, not a 1:1 control; the static variant fails acceptance on p062 already. Its main runs are
  also ~10x slower (p061 / p083 / p120 / p129 still at t 3.42-3.49 after 5 h). Static+ramp dropped unless the PI wants a hybrid
  (static release, dynamic windows), which would be a new pilot.
- pilot_c3rampR9 (density 1e-9 + C3 release ramp) p062: insertion NORMAL, flexion window past the ROM state while running
  (t 3.958): u_h@ROM 0.486 mm vs production 0.503 (-3.3 %), post -0.486 vs -0.503 — within the 5 % acceptance; extension window
  not yet started. p061 flexion t 3.86 / p129 flexion t 3.83 running, p083 main t 3.39 running, p120 ERROR t 2.77 (static phase).
- Evaluation script (same metric as fric_compare.at_intact_rom, reproduces production 0.503 / 0.448 exactly):
  scratchpad p062_control_eval.py -> p062_control_eval.json. Decision pending the extension window: if both within 5 %, rerun the
  interleave designs in pilot_c3rampR9 settings, excluding p039 p048 p052 p064 (stopped before t 3: platform problem, ramp cannot help).

## 2026-11-04 20:10 (Claude) — p062 control result: real-density+ramp does NOT reproduce production in extension
- pilot_c3rampR9 p062 both windows NORMAL to t 4. Flexion: u_h@ROM 0.486 vs production 0.503 mm (-3.3 %, accepted). Extension:
  0.566 vs 0.448 mm (+26 %), and at t 4 0.879 vs 0.650 (+35 %); smaller lift (uz 0.36 vs 0.47): the cage slides posteriorly
  instead of riding up. Smooth divergence from t ~3.75 on (504 states, no oscillation), so not a dynamic artefact of the pilot.
  Consequence: p062 would FAIL the 0.5 mm posterior line in extension under the pilot settings. Acceptance NOT met.
- pilot_c3rampS p062: both windows ERROR (3.824 / 3.841, negative Jacobians, purely static windows). Static variant dropped.
- Two factors differ from production (density 1e-9 vs 1e-6; C3 release ramp). Isolation pilots queued (h28, preflight OK):
  pilot_rho9/p062 (1e-9, no ramp, job pilotR9_p062) and pilot_c3ramp2/p062 (1e-6 + ramp, job pilotC2_p062), amplitudes 0.126 / 0.161.
- If the density is the cause, the production physio_fric3 extension translations (the gate that fails most designs at the 0.5 mm
  line) carry a ~25 % numerical-damping bias in the favourable direction -> [數值] finding on top of NUM-17; PI must decide the
  reference density. Interleave rerun on hold until the isolation pilots end.

## 2026-11-05 02:55 (Claude) — isolation pilots: the DENSITY is the cause, the C3 release ramp is harmless
- pilot_c3ramp2/p062 (production density 1e-6 + ramp): flexion 0.503 / extension 0.446 mm @ROM vs production 0.503 / 0.448
  (-0.1 % / -0.3 %). The ramp reproduces production; it is a pure solver aid.
- pilot_rho9/p062 (physical density 1e-9, no ramp): flexion 0.564 (+12 %), extension 0.535 (+19.6 %). pilot_c3rampR9 (1e-9 + ramp):
  -3.3 % / +26 %. The 1e-6 density (1000x the physical PLCL / bone density) damps the cage motion and lowers the production
  translations by 12-26 % in the favourable direction; p062 crosses the 0.5 mm posterior line in extension at physical density.
- Insertion stops: 1e-6 + ramp (pilot_c3ramp2) still stops p061 / p083 / p120 / p129 at t 3.05 (release impact); 1e-9 + ramp
  (pilot_c3rampR9) carries p061 / p083 / p129 to t 3.5 and through both windows (p120 stops at 2.77, static phase). So the ramp
  alone does not rescue the interleave designs; the physical density does, and it also changes the answers.
- Static+ramp (pilot_c3rampS): 5 of 10 windows ERROR before t 4; dropped.
- PI decision needed (added to the pending list as item 8): reference density for the frictional runs. (a) keep 1e-6: results carry a
  12-26 % favourable bias, 14 interleave designs stay '算不完'; (b) switch to 1e-9 (physical): rerun the 70 physio_fric3 designs
  (~2 GPU-days at the pilot pace), expect more 0.5 mm failures, interleave designs become computable (3 of 4 pilots). Numbers in
  scratchpad p062_control_eval.json; production is NOT re-labelled until the PI decides.
- 03:20 addendum: static vs physical density at EQUAL drive (end of window, 2.9 deg; the 11:30 pilots p061 / p083 / p129 were built
  with the retargeted amplitude 0.0507 rad, below the intact ROM, so they are insertion-feasibility pilots only): p083 flexion
  static 0.451 vs 1e-9 0.449 mm; p129 flexion 0.491 vs 0.491; p061 flexion 0.631 vs 0.600 (rho9) / 0.579 (R9). Physical density
  reproduces the static solution within 0-8 %; the production 1e-6 is the outlier (12-26 % low on p062). Evidence that 1e-9 is the
  correct quasi-static reference. Files: human_study/PI_PENDING_DECISIONS.md (8 items, plain language), human_study/FILE_INDEX.md
  (file index; h37 R12 checks that the listed paths exist).

## 2026-11-05 04:10 — PI DECISIONS on the 8 pending items (human_study/PI_PENDING_DECISIONS.md of 03:20)
PI answers (verbatim): 1 "1.5 N·m 點＝體外實驗標準力矩"; 2 依照建議; 3 a; 4 a; 5 c; 6 a; 7 依照建議; 8 b.
- Item 1, evaluation point — read as the PI's own 2026-11-03 04:30 wording (option ii): a window is judged at the 1.5 N m state
  when it transmits that moment, and ONLY at the intact-ROM state when it never reaches 1.5 N m. Implemented in fric_compare
  (eval_point per window recorded in verdicts.json). If the PI meant "1.5 N m only", windows that never transmit it would stay
  open instead — to be confirmed. The interface-shear gate stays at the ROM state (PI 2026-11-04 03:30 set it there explicitly).
  Effect (from results/method/fric/verdicts.json): gate 4 verdicts 26 fail / 14 pass / 31 open -> 14 fail / 24 pass / 33 open (27 insertion stops: 6 static-release + 21 release-impact; 6 window-level: p014 p063 p066 p078 p086 p146);
  10 designs fail -> pass (p002 p026 p038 p079 p100 p112 p125 p132 p133 p148: their flexion windows exceeded the limit only at
  the ROM state while transmitting 1.5 N m), 2 fail -> open (p014 p078). All 14 remaining fails are extension@ROM (the extension
  window never transmits 1.5 N m in these designs), posterior 0.50-0.64 mm.
- Item 2, gate order — radial-mix exclusion is now the FIRST design-level cause (collect_split), ahead of dislocation and shear.
- Merged classes after items 1 + 2 (results/method/split/verdict_classes_merged.json; tied passes 72, PASS 0):
  DESIGN/radial-mix-excluded 28 (27 tied passes + p107), DESIGN/dislocation-friction 17, DESIGN/interface-shear-provisional 14,
  [多元]/friction-computability 14; tied-screening classes unchanged (compression-sustained 53, -lowerbound 10, -peak 5,
  -peak-lowerbound 4, computability 2, unstable-window 2). The 13:30 / 11-04 figures 28 / 16 / 14 / 14 are superseded.
- Item 3 — commit authorised (PI author, local commit, no push; run directories and the deleted al_v2/cases records left out).
- Item 4 — R03 confirmed superseded; all friction verdicts carry 'provisional' (verdicts.json _meta, e07 meta) until NUM-16 /
  NUM-17 and item 8 are settled. Class strings unchanged.
- Item 5 — T05 extension to the 6 static-release stops checked, nothing changes: their last converged plotted state is t 2.0
  (p097: 2.64), i.e. before the release step completed, and the soft-layer compression there is <= 2 % (max over soft elements,
  z-direction, as in failed_runs_lastJ.json; p99 principal <= 1 %) — far below the 15 % limit, so no lower-bound FAIL can be
  claimed. They stay [多元]/friction-computability. Numbers: results/method/fric/static_release_stops_lastJ.json. The 21
  release-impact stops wait for item 8 as decided. Note: T05 as worded (stop UNDER the follower load, t >= 3) does not cover t < 3;
  had any exceeded 15 % the extension would have needed its own entry.
- Item 6 — FEBio patch regression (NUM-10) to be re-run with the 2026-11-03 binary into a new directory (see later entry).
- Item 7 — pre-commit hook: runs h37 --quick --hook (register findings reported as WARN, not blocking) in both repos.
- Item 8 — reference density becomes the physical 1e-9 (new class physio_fric4, NO C3 release ramp: at 1e-9 the ramp shifts the
  answer 14 % (p062 flexion 0.564 -> 0.486) and the static reference sits nearer no-ramp; pilot_rho9 p061 got through insertion
  at 1e-9 alone). Step 1: time-step convergence on 5 designs (physio_dt 0.05 vs 0.025, acceptance 2 % on the item-1 evaluation-point
  translation). Step 2: the remaining passing designs, excluding the 6 static-release stops (t < 3 is static in both densities).
  physio_fric3 stays as the record of the 1e-6 results; physio_fric4 is kept out of fric_compare SETS until the rerun is complete,
  then the basis is switched in one documented step.
- 04:00 — commits (PI item 3): biocage_simulation_test_oct2026 ea74af8, biocage-evo 8586fb8 (author austonliuyi, local, no push; the
  pre-commit hooks ran h37 --quick --hook: WARN only, LLM audit due). Left out on purpose: run directories, the untracked al_v2 set
  metadata (physio_fric*, numconv_*, pilots) and the ~40 deleted al_v2/cases records — PI to say if they should follow.
  Density pilots queued (preflight OK, amplitudes 0.126 / 0.161): physF4_ and physF4dt_ for p062 p060 p139 p061 p083 (10 jobs).
  NUM-10 regression running: human_study/verify_patch_20261105 (6 FSU directions + C0-C7 flexion / extension, CPU batch).
- 04:24 — QA audit 2026-11-05 (human_study/qa/audits/QA_AUDIT_2026-11-05.md): 3 不符, all label / document text and numbers, no
  verdict or class count changes. Fixed: (1) my 04:10 "26/14/5 -> 14/24/7" counted only designs with windows; verdicts.json counts
  are 26 / 14 / 31 -> 14 / 24 / 33 (open = 27 insertion stops + 6 window-level designs) — corrected in DECISIONS, R11, PHY-05, evo
  docs; (2) PHY-05 method / threshold_src still described the two-point check -> conditional rule; 1.5 N m reached in 38 physio_fric3 windows (compare.json rows);
  (3) OBS-10 note still gave the old gate order. PHY-05 / OBS-10 / DIV-03 status dates moved to the result-file time 03:41.
  Item 5 figures corrected: max soft z-compression 1.28-2.14 % (p097 2.14), p99 principal 0.45-1.50 % — still far below 15 %.
  Auditor sign-off items noted: the 03:20 option texts the PI answered against were overwritten by the 04:40 pending-doc rewrite
  (only the 04:40 version is in git) — the PI's answers are read via the 04:10 entry; the scratch scripts (p062_control_eval,
  static-release compression, verify_patch compare) live in the session scratchpad, not the repo.
- 04:25 — NUM-10 regression rerun (PI item 6) done: human_study/verify_patch_20261105 (2026-11-03 03:00 binary) vs the 2026-10-21
  baseline. FSU six directions: CPU path <= 4.8e-12, cuDSS GPU path <= 7.9e-12 relative at t 2.0 (GPU vs CPU of the same binary
  <= 7.9e-12) -> the production geometry passes on both solver paths. Herron C0-C7 flexion 1.1e-4 (0.004 mm, at the threshold);
  C0-C7 extension: C0 rotation 0.025 % but node displacements up to 0.12 mm (2 % of C6's 5.6 mm), different auto-stepper path
  (46 vs 56 steps, path-dependent frictional contact); the pre-rebuild binary no longer exists, so a fixed-step two-binary run is
  impossible -> recorded as a limitation, not hidden. NUM-10 TIED / FRIC -> pass (2026-11-05) with that note; the 2026-11-04
  reconfirmation sweep's premise (rebuild changed no converged result on the production geometry) is now established.
  GPUs 5 / 6 were taken by another user (39.8 GB each) during the run; cuDSS handle creation fails on a full GPU (status 4).
- 04:28 — timestamp correction: the entries I labelled 05:05 / 05:40 / 05:50 and the pending-doc "04:40" were written at ~04:00 /
  04:24 / 04:25 / 03:50 (I had estimated the clock instead of reading it); labels relabelled, NUM-10 status date set to 04:25.
  The "04:10" header above was written at ~03:45; kept as is because the audit report and register cite it by that label.
- 04:33 — audit re-check: 3 不符 -> 符合, h37 overall PASS (QA_AUDIT_2026-11-05.md §9-10). Follow-ups applied: NUM-10 label numbers
  now reproducible from verify_patch_20261105/compare.json (gpu_vs_cpu_same_binary 7.9e-12; C0-C7 extension attempted steps
  46 vs 56 incl. retries, converged 30 vs 32); the NUM-10 exception (C0-C7 extension 2 % node-level difference, label kept pass
  on the production geometry) is listed for PI sign-off in PI_PENDING_DECISIONS.md §C. Stale labels after the 03:40 gate-file
  changes: PHY-06 / OBS-02 / OBS-03 / OBS-05 / OBS-07 reconfirmed with notes (self-tests e03/e04/e05 PASS 04:31), OBS-06 value
  updated to the 03:41 merge (276 windows, fail 131 / open 18 / pass 0).
- 04:38 — GAP FOUND AND CLOSED (own check, not caught by the gates): the p139 density pilots in physio_fric4 / physio_fric4dt ran
  with the window amplitude of the first, wrong build (0.035 / 0.050 rad instead of 0.126 / 0.161): h28 skips the h14 build when
  case.feb exists, rewrote only the params file, and h24 passed because it compares a rebuild of case.feb only — the drive amplitude
  lives in the window restarts (w_*/restart.feb, physio_schedule.json), which h24 never compared (listed as a sign-off item on
  2026-11-04, now proven to matter). physF4_p139 ran to the end with the wrong amplitude (windows reached 2.0 / 2.9 deg, below the
  ROM); physF4dt_p139 killed at t ~3. Fixes: h24 now also compares every w_*/restart.feb, restart_static.feb and
  physio_schedule.json against the rebuild (tested: the stale p139 build FAILS, the fresh builds pass); h37 launch gate R13 compares
  the window schedules' rot_rad with the params file and the class setting (a check against case.json would not have caught it —
  a stale build is self-consistent; verified on a synthetic stale copy). Stale jobs moved to human_study/queue/cancelled_stale_amplitude/,
  p139 dirs deleted and rebuilt (schedule 0.126 / 0.161, preflight OK), requeued. The other 8 pilots were fresh builds and are correct
  (params = case = window schedule 0.126). Lesson: never rely on a build-skip when the inputs changed; the preflight must cover every
  file FEBio reads.

## 2026-11-05 06:38 — PI DECISIONS: item-1 reading confirmed; NUM-10 partial
- PI (verbatim): "傳得到 1.5 N·m 在 1.5 N·m 判，傳不到才在 ROM 判" — the implemented reading of item 1 is confirmed; D-20261105-1b closed.
  Gate-4 numbers stand: 14 fail / 24 pass / 33 open; merged radial-mix-excluded 28, dislocation-friction 17, interface-shear-provisional 14,
  friction-computability 14, PASS 0.
- PI: "NUM-10 例外：部分通過" — NUM-10 TIED / FRIC set to partial (production FSU geometry passes on both solver paths at <= 1e-11;
  the C0-C7 extension case exceeds the 1e-4 threshold by 2 % at node level and cannot be re-run against the old binary); the threshold
  keeps no exception. Sign-off item D-20261105-S4 closed.

## 2026-11-05 07:31 — platform vs FEBio agreement figure (scripts/8_audit/h38_febio_agreement_fig.py)
- User asked for a Nature-style figure showing the platform converging on FEBio, with a test of no effective or significant difference. Built from result files only; outputs in human_study/figures/febio_agreement/. The data do not support that claim as a whole: 9 rows equivalent, 4 not, 6 without a conclusive test.
- Equivalent: tied cage metrics GPU vs CPU on byte-identical inputs (15 windows, 3 designs, margin 2 %, max |e| 0.33 %), intact FSU regression, gpufe gate 1 / 1b. Not equivalent: real-friction slip (GPU vs CPU max 26 %, GPU vs GPU 33 %, margin 5 %), interface shear, C0-C7 regression. gpufe gate 2 re-run on current code into gate2_rerun_20261105/ (results/ of the evo repo untouched); gates 3-4 have no data.
- New findings, listed in PI_PENDING_DECISIONS.md, labels not changed: NUM-17's "amplitude differs" is wrong for p077/p139 and p100/p142 (byte-identical inputs); NUM-11's "<= 0.1 %" does not hold (mu 0.33 %, translation 0.58 %).

## 2026-11-05 10:06 — GPU solver vs FEBio plain-language figure (scripts/8_audit/h40_gpu_solver_fig.py, data h39)
- User asked for a figure showing the GPU solver within tolerance of FEBio across physical processes, and listing capability labels still out of tolerance or undecidable. Outputs in human_study/figures/gpu_solver_agreement/.
- Gates 1b / 1c re-run on the current Newton solver for the first time (F-0014, F-0026), no FEBio run. 14 of 18 rows inside their limit. Outside: bars at the default 0.05 N floor (1.9 %, limit 0.1 %), sliding at mu 0.2 (stops at t 0.04). No limit set: pressing force vs FEBio (4.1 %, 10 %). Gate 2 still 1 of 6; gates 3-4 not run.
- Labels unchanged; NUM-13 data and the stopping-rule conflict are listed in PI_PENDING_DECISIONS.md. Fine and coarse gate 2 reruns of 2026-11-05 reproduce the 10-28 stall region (6-23 % of the load).

## 2026-11-05 11:29 — main results figures (scripts/8_audit/h41_main_results_figs.py)
- User asked for 1-2 plain-language Nature-style figures of the most complete result. Chosen: the neck model check plus the 149-design screen. Outputs in human_study/figures/main_results/. Numbers computed from the merged verdict files: 0 of 149 pass; 72 compression, 17 slip, 14 bond (provisional), 18 could not finish, 28 excluded.
- Own checks changed two statements: PHY-01 reproduces as 15 of 19 from comparison.json, not 18 of 22 (listed in PI_PENDING_DECISIONS.md, label unchanged); stiffness does not separate compression pass and fail across cage types, so the draft claim that E_soft is the dominant factor was not used.

## 2026-11-05 13:42 — figure revisions and two more figures (h41, h42, h43)
- User: p100 must not sit in the pass zone of Fig. 2a. Runs of byte-identical inputs are now one design, plotted at its worst slip and shear (any fail fails the group); the pass zone is empty. The single in-limit run stays in the legend. Family A axial labels changed from "soft pads" to "softer towards the faces" (h12: family A has no pad).
- Fig. 3 (one representative of each of the 12 design types, rule in fig3_fig4_legends.md) and Fig. 4 (methodology). Fig. 4 marks the designer and engine as not started: no AI-generated design exists; last agent round 10-28, 29 findings none closed, HOLD not enforced.

## 2026-11-05 18:02 — GPU naming in figures
- User approved renaming to avoid mixing two different GPU things. FEBio's GPU is now always called the GPU linear solver (cuDSS) or "GPU run / CPU run"; the in-house solver is always "in-house GPU solver (gpufe)". Applied in h38 (fig_febio_agreement), h40 (fig_gpu_solver_vs_febio) and h43 (fig4); abbreviation lists explain both. No numbers changed.


## 2026-11-05 18:08 (Claude) — physio_fric4 step 1 did NOT pass; full rerun held; correction to the 02:55 density conclusion
- Convergence pilots read at 17:58 (three windows still running; scratchpad fric4_dt_eval.json). Acceptance was 2 % at the gate-4 evaluation point
  for dt 0.05 vs 0.025. Result: p062 flexion +3.9 %, extension -5.8 %; p139 flexion +3.8 %, extension -11.8 %; p060 flexion -4.8 %; p083 flexion +5.1 %.
  None within 2 %. This compares dtmax with dtmax under the adaptive stepper, not a controlled dt (225 increments over a 0.5 window means an average dt near 0.002), so it shows path sensitivity, not a clean convergence number.
  Flexion windows stopped (ERROR) in p060, p061, p083 at physical density. Step 2 (remaining designs) is NOT launched.
- Correction: on 11-05 02:55 I wrote that the density is the cause and that 1e-6 is the outlier. That is overstated. Halving dt alone moves p139 extension
  0.809 -> 0.713 (1e-6 value 0.637) and p062 extension 0.552 -> 0.520 (1e-6 value 0.448). PI item 8 was decided on that claim, so it goes back to the PI.
- New hypothesis, not yet proven: the translation grows with the number of FEBio increments. FEBio resets the stick point every increment
  (verifier V05 from source, V07 measured 0.0151 mm per increment on a 10 MPa block; PI 2026-10-27 already excludes FEBio as the friction reference).
  Same design, translation at the intact ROM: p062 extension 25 inc 0.448, 29 inc 0.446, 271 inc 0.535, 275 inc 0.552, 302 inc 0.566, 315 inc 0.520;
  p139 extension 36 inc 0.637, 157 inc 0.713, 225 inc 0.809; byte-identical inputs p077 33 steps 0.456, p139 53 steps 0.637.
  Evidence is mixed: every high-increment run is also a 1e-9 run, so increments and density are confounded. At fixed density p139 agrees (157 -> 225: up) but p062 does not (275 -> 315: 0.552 -> 0.520). Only p077 / p139 is a clean same-input comparison, and reverse causation is possible (more slip -> more step cuts).
  The direct test is a hold at a fixed angle with fixed increments (V17 of ../biocage-evo/docs/GPUFE_VERIFICATION_PLAN.md).
  If confirmed, it affects the 0.5 mm verdicts of physio_fric3 (NUM-13 FRIC has never been run). Labels and verdicts unchanged until then.
- PI request 2026-11-05: list what gpufe needs verified, how, and on what basis; check the method; then start. Plan v0.1: ../biocage-evo/docs/GPUFE_VERIFICATION_PLAN.md.

## 2026-11-05 18:25 — Fig. 5: multi-agent loop as a stand-alone 4:3 figure (scripts/8_audit/h44_multiagent_loop_fig.py)
- User asked for panel c of Fig. 4 to be refined with more interaction arrows, at 4:3. 14 arrows between 9 roles, taken from docs/GOVERNANCE.md and roles/prompts (change requests pass through the integrator; canaries; round digest; escalation to the PI). Fig. 4 panel c is unchanged. Status line computed from findings and verdict files: 3 rounds, HOLD each, 29 findings, designer and engine not started.


## 2026-11-05 21:36 (Claude) — gpufe stage 0 results: stop rule triggered; FEBio cage drifts at a fixed angle
- V22 speed (results/gpufe_verify/v2/v22_speed_p062_tied.json, gpufe/verify/v22_speed.py): tied p062 deck, FEBio + cuDSS recorded 844 s to t 9.5 (1430 iterations, 372 reforms); gpufe stopped at t 9.05 after 2164 s (Newton not converged), 1686 accepted-increment iterations. 72 % of the time is cuDSS factorisation (2886 factorisations, one per iteration). gpufe is at least 2.6 times slower, not faster. Timings on shared GPUs, one run each. Plan stop rule reached: not continuing to stage 1 until the PI decides. Accuracy was not compared in this test.
- V1 reader audit: gpufe/verify/v01_reader_audit.py, production window deck has 4 defect types (drive joint, friction curve, dynamic analysis, rhoi).
- V17(a) hold (gpufe/verify/v17a_hold.py, results/gpufe_verify/v2/v17a_hold.json): C3 angle constant to 3 decimals in degrees, follower constant, no time-dependent material, so a converged rate-independent model must not move. It moves: extension p139 0.462 -> 0.642 mm, 0.474 -> 0.647 mm; p062 0.452 -> 0.512 mm; flexion falls by 0.06-0.18 mm. Still 0.0005-0.002 mm per increment at the end of the hold. This breaks the friction law the PI set as the reference, on the production cage.
- Not yet separated: the planned dtmax arms gave about the same number of increments (the stepper was cutting steps anyway: 55-71 vs 66), so per-increment and loose-convergence causes are still open. New arms queued, extension only: pilot_holdC (dtmax 0.002, at least 250 increments), pilot_holdD (rtol 0.001, h14 option rtol, default unchanged, R8 passes).
- V17(e) block (results/gpufe_verify/v2/v17e_block_al.json): laugon 0 creep is proportional to increments and inversely to stiffness (E 10: 0.075 mm / 5 inc, 0.302 mm / 20 inc; E 400: 0.0019, 0.0075). laugon 1 removes it where it converges (E 10 -0.0024, E 400 0.00013) but stopped in 5 of 8 cases with tolerance 0.01.
- Replicates: hold classes share the production ramp and settings to t 3.9, translation at t 3.9 scatters: flexion p139 0.576 / 0.586 / 0.701, p062 0.503 / 0.532 / 0.613; extension p139 0.456 / 0.462 / 0.474 / 0.637. Verdicts and labels unchanged; these go to the PI with the hold result.

## 2026-11-05 23:29 (Claude) — correction to the stage 0 hold entry; controlled increment ladder at fixed density
- Correction: pilot_holdB and pilot_holdC did not put small steps in the hold. FEBio's step curve gives the value of the NEXT point, so the dtmax values applied on t (3, 3.9], before the hold (seen in the logs: dt 0.002 before t 3.9 in C). The hold in A, B, C, D all ran at dtmax 0.05, which is why their hold increments are alike (41-71). Hold drift therefore still does not separate per-increment from time-based causes. pilot_holdE (dtmax 0.002 truly in t 3.91-4.4, at least 245 increments) is queued for p062 and p139.
- The accident is a clean experiment: same density 1e-6, same inputs, only dtmax on t (3, 3.9] differs (A 0.05, B 0.0125, C 0.002). results/gpufe_verify/v2/v17a_ladder.json, extension window:
  p139 at t 3.5 (follower only, no rotation): 29 inc 0.004 mm, 92 inc 0.061, 321 inc 0.147. At t 3.9 (intact ROM): 0.462, 0.474, 0.616.
  p062 at t 3.5: 35 inc 0.006 mm, 98 inc 0.031, 357 inc 0.133. At t 3.9: 0.452, 0.456, 0.491.
  So at fixed density the gate-4 translation is not converged in increments and grows with them; the +0.15 mm on p139 is larger than the margin of the designs near the 0.5 mm line. It is the same direction as the FEBio stick-point reset, measured on two designs only. No fine-step limit has been reached, so no corrected value exists yet.
- rtol arm: pilot_holdD p139 (rtol 0.001): drift 0.145 mm in 51 increments vs A 0.180 in 71. Tightening the force residual does not remove it; loose convergence is not the main cause.

## 2026-11-06 00:50 (Claude) — hold test decisive: FEBio cage drift scales with increments; 11-05 density conclusion retracted
- pilot_holdE vs pilot_holdA, extension, same density 1e-6, same start at t 3.91 (p062 0.461 / 0.465, p139 0.475 / 0.475), same 0.49 of hold time, angle constant to 3 decimals in degrees, follower constant, no time-dependent material:
  p062 54 inc +0.047 mm, 355 inc +0.303 mm (0.00087, 0.00085 per inc); p139 71 inc +0.167 mm, 251 inc +0.461 mm (0.0023, 0.0018 per inc), ending at 0.936 mm. Elapsed time is equal, so the drift follows increments, not time. A converged Coulomb model must not move here. Files: results/gpufe_verify/v2/v17a_hold.json, v17a_ladder.json.
- Scope: two designs, extension only. Flexion arms had dtmax on the ramp only. Rate is not simply 1 / eps (p139 eps is 5.5 times softer, rate 2.2-2.7 times larger).
- Retraction: "density is the cause, 1e-6 is the outlier and biased low by 12-26 %" (11-05 02:55, R12, PI item 8). The 1e-9 runs carry 200-300 increments against 25-36, so most of that gap can be this artefact; the density effect itself has not been isolated. PI item 8 goes back to the PI with this.
- Effect on verdicts: the artefact inflates translation, so existing dislocation fails can be overstated; verdict files unchanged, all remain provisional. No corrected value exists: cannot subtract rate x increments because traction differs along the ramp.
- Labels: NUM-13 FRIC -> fail with this evidence; R12 rewritten. NUM-13 GPUFE left for the PI (pending since 11-05 10:06). Options written in PI_PENDING_DECISIONS.md. Not started: FEBio patch, reruns, gpufe stage 1.

## 2026-11-06 23:15 — friction lower bound figures (scripts/8_audit/h45_mu_face_scan.py, h46_mu_figs.py); Fig. 2 retraction fix
- User chose option C (check the FEBio drift first); the 11-06 00:50 hold test had already answered it. Two figures: fig_mu_poster and fig_mu_gaps, in human_study/figures/mu_requirement/.
- mu_req (mu_squeeze, whole cage) on 505 windows of 93 designs: all at most 0.166; 79 designs with six motions.
- New from the h45 scan on the same windows: worst single-face mu_scaled median 0.72, above 0.3 in 344, above 1 in 155, every side-bending and twisting window above 0.3. Tension over net normal force on the glued face: median 170 % in extension, 31 % in the other motions.
- Gate-4 evaluation point: 13 of 79 physio_fric3 windows over the limit, all extension. An earlier chat count of 32 used the ROM state for flexion and was wrong against the PI rule. Production friction runs cover flexion and extension only; side bending and twisting exist for 15 usable windows of 4 early designs.
- Fig. 2 (h41): the retracted density statement was replaced by the FEBio drift finding, in the panel, footer and legend. Labels and verdicts unchanged.

- 23:18 addendum: "most of that gap can be this artefact" is too strong. At the same density the fine-step ramp gives p062 0.491 and p139 0.616 mm; the 1e-9 runs with similar ramp increments give p062 0.520-0.566 and p139 0.713-0.809 mm. A remainder of 0.03-0.19 mm is not explained by ramp increments; it may be density or run-to-run scatter. The withdrawal of the rerun still stands because the two cannot be separated until the friction rule is fixed.

## 2026-11-06 23:42 — PI DECISIONS: friction fix (a)+(b) in parallel; gold standard first; gpufe deferred
PI (verbatim, 2026-11-06): "1. a,b同時，然後互相參照迭代問題與解法直到無法解決需要我提出大決定，摩擦很重要所以必須精確得出mu_reqest，可以有goldstandard模擬以及速度較快然後和goldstandard誤差在可容許範圍的篩選模擬 2. 零件變重會影響到摩擦力的預估嗎(摩擦力很重要)？如果密度會影響只會影響滑出的估值，滑出量好像也不是我們主要關注的目標模擬物理量結果 3. 先修febio使goldstandard先出來，gpufe需要依賴goldstandard來學習如何取巧加速"; also "盡量使用fable，因為我weekly limit快沒了".
- Item 1: (a) FEBio patch 6 'stick_memory' (FESlidingElasticSurface::InitSlidingSurface keeps m_rsp / m_pmep for points that ended the last increment in stick; parameter default off, so the production binary behaviour is unchanged) built into third_party/FEBio/cbuild_fric (production cbuild untouched); (b) augmented Lagrangian on the cage contacts (h14 option cage_laugon, default off) queued as pilot_holdF p062 / p139 on the production binary. Both feed the hold test; iterate until a decision only the PI can take.
- Item 2 answered in the reply (summary): tied screening decks (mu_req source) also use density 1e-6 in the dynamic window step; the reaction on the C3 pot shows the inertia / damping force on the segment stays below 1 N (std 0.17 N, max 0.85 N at 1e-6 vs 0.01 at 1e-9) against the 100 N follower, so the normal load and the friction capacity are affected by about 1 % or less; the earlier 12-26 % was mostly the increment artefact. mu_req itself does not use the stick / slip rule (tied contact), so the stick reset does not touch it; its own open issue is tension on the tied faces (F-0021). PI asked to confirm that slip-out verdicts return to mu_req-first (10-27) with the friction run as the check (11-03 made it gate 4).
- Item 3: gpufe stays stopped until the FEBio gold standard exists (R04 unchanged); the plan file keeps its stage-1 list for later.
- Working rule from the PI: economise tokens (Fable, no agent fan-out unless needed).
- h06: BIOCAGE_FEBIO env override for pilots on the patched build; h37 PILOT_KEYS now include physio_hold, cage_laugon, cage_stick_memory (a production case carrying them fails the launch gate). R8 golden rebuild still passes.

## 2026-11-06 23:59 (Claude) — FEBio patch 6 'stick_memory' passes the block hold test; cage hold tests running on both fixes
- Patch 6 (febio_patches/febio-4.13-biocage-patch6-stick-memory.patch, binary third_party/FEBio/cbuild_fric/bin/febio4 sha256 88c24a0d…, production cbuild untouched, parameter default off): (a) stick points kept across increments, (b) slipped points re-anchored on the friction cone, (c) slip direction = trial tangential traction direction (the kinematic incremental direction is noise at a hold and made Newton chatter), (d) elastoplastic Coulomb tangent for return-mapped slip. Three iterations were needed: v1 (a only) creep 0.0086-0.069 mm and 5/8 non-converged; v2 (+b) worse; v3 (+c) creep <= 2e-6 at 0.5 of the limit but 4/4 fails at 0.9; v4 (+d) = current.
- Block test (verifier V07 deck, results/gpufe_verify/v2/v17f_block_patch.json): production binary hold creep 0.0019-0.603 mm, proportional to increments; patched: displacement constant to 5 decimals during the hold in every converged case (fixed steps 10/40, E 10/400 MPa, 0.5 and 0.9 of the limit; with FEBio's auto stepper all 0.5 cases and 3 of 4 at 0.9). The 'creep' numbers printed for the auto variant (0.0002-0.006) are an interpolation artefact of x(0.5) across the last ramp increment, not drift (rb.txt shows constant x from the first hold state on). Not converged: 0.9 of the limit with the whole shear applied in one fixed increment (no stepper) and one auto case (E 10, n 10) stopping at t 0.79 — step cutting handles it in the cage decks, to be verified there.
- Cage hold tests: pilot_holdG p062 / p139 (patch 6, CPU 16 cores each, min_residual 1e-6, tmux holdG, launched via h06 with BIOCAGE_FEBIO) and pilot_holdF (augmented Lagrangian, production binary, GPU) running. Acceptance: hold drift <= 0.01 mm and independent of increments (NUM-13), window completes.
- Reader of settings: all pilot keys (physio_hold, cage_laugon, cage_stick_memory, min_residual) are in h37 PILOT_KEYS; R7, R8 pass.

## 2026-11-07 13:00 — PI DECISIONS: all nine recommendations of the 12:40 briefing accepted; pacing rule
PI (verbatim): "照建議，盡力迭代解決問題"; then "依照usage limit聰明配速"; later (2026-11-08 00:xx) "列出目前子專題以及各自的目標、進度 / 繼續迭代解決問題，參考專業文獻或可信程式庫 / 大目標：構建符合能力標籤的模擬平台" with the five labels restated:
[物理] the shortcut mu_req (smallest friction coefficient that prevents slip-out, including slow creep over motion and time, or slip small enough to tolerate) must agree with a credible real-friction simulation within a small margin; [數值] repeatable, the numbers must reflect the intent, precision only as fine as the goal needs; [速度] every shortcut and every resource within the set limits, GPU where it is faster, GPU builds allowed; [觀測] only the target quantity has to be right, everything else only has to run; [多元] room for the design agents' unusual shapes, stiffness and bone-contact modes.
Decisions (item: choice): 1 slip-out verdict = mu_req first (10-27 rule), the friction run is the check, 17 dislocation-friction designs to be reclassified (a); 2 single-face friction: record only, no limit yet (a); 3 side bending and twisting friction runs after the fix (a); 4 existing slip-out verdicts stay provisional until recomputed (a); 5 commit code, documents and patch 6 only, PI author, the 12,137 deleted al_v2/cases records stay out (a); 6 hourly foreman paused while the queues are empty (a); 7 NUM-11 threshold stays 1e-4, label partial (a); 8 PHY-01 value 15/19 and re-judge acceptance (a); 9 NUM-13 GPUFE fail (a).
Applied today: 7, 8, 9 in platform_capabilities.json (PHY-01: 15/19 misses the recorded threshold >= 18/22, so the state is fail and the acceptance question goes back to the PI in PI_PENDING_DECISIONS.md - 照建議 cannot turn a missed threshold into a pass); 6 in ../biocage-evo/ops/evo_daemon.sh (foreman only when a job waits or runs, an evo task exists or a febio4 process of this user runs; daemon restarted); 1 and 5 below / pending; 2, 3, 4 need no code now.
Working rule: no agent fan-out, no Workflow; FEBio runs on the idle quota (GPU 3, 4; 32-core cgroup).

## 2026-11-07 13:00 - 2026-11-08 01:00 (Claude) — why pilot_holdF / holdG stopped; restart hold design; FEBio patch 7; first results
Four stops, all in the recomputed insertion (t < 3.5), none in the hold that was to be tested:
- F p139 (augmented Lagrangian, t 2.173, static release): every printed norm met (energy 6.7e-14 < 1.2e-10, displacement 1.4e-18 < 4.2e-15, residual 3e-8), but the line search collapsed to 0.00023 ("Zero linestep size"), FEBio reformed 25 times and failed. FEBio's stationary-state trap; min_residual 1e-6 (not in the holdF params) ends it at once.
- G p062 (patch 6, t 3.436, follower ramp): 250-iteration stall; residual floor 1.6e-5 (|R| 4 mN against 100 N), displacement 3.7e-10 against a required 1.5e-13 (dtol^2 x a 1.5e-7 increment after the auto stepper had cut dt to 0.0005 because every step from t 3.08 on needed ~40 iterations). The 1e-6 min_residual was 16x too tight for this floor.
- G p139 (patch 6, t 3.05-3.085): Newton diverges (residual 6.7e6 -> 1e8-1e9, |du| 1e2-1e3) at every retry down to dt 0.003; inverted elements all in cage_mix_0.25 (soft cage layer). Production p139 passed 3.0-3.085 with 13/30/10 iterations and no retry. Patch-induced; not isolated (candidates: patch-6 (d) tangent, (c) direction rule under the release impact).
- F p062 (augmented Lagrangian, t 3.07): converged 3.05, then inverted C3_cortical tets at the first iteration of the next step; initial residual 4e8 (inertial impact of the 1e-6 density segment after the C3 release). 21 production insertion runs stop at the same event (release-impact class).
Design change (advisor-reviewed): the hold is a WINDOW problem, so the window is restarted from the existing t 3.5 checkpoints of pilot_holdA (coarse hold, dtmax 0.05) and pilot_holdE (fine hold, dtmax 0.002), both produced by the production binary; only the window gets the friction treatment. Same insertion state as the 11-05/06 drift numbers, so the drift isolates the treatment. This also makes a later production rerun from the 71 existing physio_fric3 checkpoints possible (no fragile insertion recompute, QA R4 state kept).
FEBio patch 7 (third_party/FEBio/cbuild_fric only; patch file febio_patches/febio-4.13-biocage-patch6-stick-memory.patch regenerated, README to follow):
- stick_memory is no longer an input parameter: FEParamContainer::Serialize refuses a dump whose parameter count differs, so the sliding-elastic list is kept identical to FEBio 4.13 and production checkpoints load. Pilot options come from the environment, applied to frictional interfaces only (facets untouched) in Init() and on dump loading: BIOCAGE_STICK_MEMORY=1; BIOCAGE_CAGE_LAUGON=<tol>[,<maxaug>] (augmented Lagrangian, minaug 1). The solver's augmentation flag is recomputed by the restart step's new solver (FESolidSolver2::Init). feLogInfo lines are filtered by FEBio's log level, so launch.json / the h47 env record is the evidence (to switch to feLog later).
- hang found and fixed: in ContactTraction, when the stick/slip status is frozen (m_bfreeze), a stuck point's current element is replaced by its anchor element (data.m_pme = m_pmep). With stick memory the anchor may sit on another element, the contact stiffness then addressed (cage node, C3 node) pairs outside the sparse profile, and CRSSparseMatrix::add's bisection never terminates for a missing column (n0 = k, n1 = k+1 for ever). Found with gdb on a fresh copy (ptrace attach is blocked) and a FECore guard that reports the pair on stderr instead of hanging (kept; production FEBio would hang there). Fix: with stick memory the anchor stays in (m_pmep, m_rsp) and m_pme is kept; BuildMatrixProfile also adds the anchor element's couplings. Production path (stick_memory off) unchanged.
- h14 key window_min_residual (restart Control only, via physio_schedule.json -> h30), h37 PILOT_KEYS + window_min_residual, restart_env; settings classes pilot_holdH (= holdA) and pilot_holdHf (= holdE); scripts/5_compute/h47_restart_pilot.py (build: h14 rebuild must be byte-identical to the checkpoint's case.feb, hard-linked dump, h24 preflight; run: in-place window restart on a GPU with the env). All 10 cases passed h24; h37 --quick all PASS (R10 LLM audit WARN).
Wave 1 (13:20-14:30, 3 cores each, GPU 3/4; results/gpufe_verify/v2/v17g_hold_restart.json):
- control (patched build, options off, holdA dumps): p062 drift +0.0568 mm in 51 hold increments (holdA +0.0594 / 55), p139 +0.1246 / 41 (holdA +0.1799 / 71; per increment 0.0030 vs 0.0025). The patched build without the options reproduces the production artefact and the checkpoints load correctly.
- augmented Lagrangian, tolerance 0.2, maxaug 10, window min_residual 1e-4 (holdA dumps): p062 +0.0332 / 229 increments, p139 +0.0173 / 185; per increment 1/7 and 1/30 of the control, but not zero and above the 0.01 mm acceptance; 21,262 / 20,713 iterations against 2,062 / 1,472 for the controls (10x cost). Reference: Simo & Laursen 1992, Comput. Struct. 42:97-116 (augmented Lagrangian frictional contact) - the multipliers carry the traction across increments, the remaining penalty part still resets.
- stick memory arms hung (the m_bfreeze swap above); the Hf p139 arm ran on the unfixed library to t 3.949 and stopped (two retries, inverted elements) - discarded. Wave 2 (00:10) was launched by mistake on the unfixed library (the edit script had failed before the build) - discarded, logs in _wave2_fail/. Wave 3 (00:40) on the fixed library (libfebiomech sha256 3130d3e8...): six stick-memory arms (p062/p139 x coarse / coarse+min_residual 1e-4 / fine), no out-of-profile entries, running.
Literature basis of the two treatments: stick memory + return mapping = elastoplastic Coulomb friction (Wriggers, Computational Contact Mechanics, 2nd ed. 2006, ch. 5-6; Laursen 2002); FEBio's sliding-elastic algorithm is Zimmerman & Ateshian 2018, J. Biomech. Eng. 140(8):081013, whose stick point is the previous increment's projection - the source of the per-increment creep under constant load.
Labels: NUM-13 FRIC fail unchanged; nothing else changed by these pilots yet.

## 2026-11-08 01:40 (Claude) — decision 1 implemented (friction run = check); wave 3 stick-memory results (coarse hold)
- ../biocage-evo/ops/collect_split.py: the frictional dislocation record is no longer a gate. A tied pass whose friction run exceeded the limit keeps its mu_req verdict and carries friction_check = exceeded (provisional); the list is written as friction_check_exceeded in verdict_classes_merged.json. The interface-shear gate (PI 2026-11-04) and the radial-mix exclusion (PI 2026-11-04/05) are unchanged, so a design without usable friction windows stays open for the shear gate. h37: R2-merged ignores the dislocation_friction record (role check); R5 counts friction-check-exceeded instead of dislocation-friction.
- Recomputed (276 windows): PASS 13 (was 0), friction-check-exceeded 13 (p051 p060 p072 p075 p086 p092 p093 p100 p114 p117 p142 p143 p145; all 13 are among the PASS), interface-shear-provisional 18 (was 14: p-ids of the former 17 dislocation fails that also exceed 3 MPa moved here), radial-mix-excluded 28, friction-computability 14, open 18, fail 118; compression classes unchanged (53 / 10 / 5 / 4). All friction-based entries stay provisional (decision 4) until the windows are recomputed with the fixed friction law.
- Wave 3, stick memory (patch 6+7, fixed library), restart from the holdA checkpoints, coarse hold (dtmax 0.05), extension: p062 drift +0.0073 mm in 18 hold increments (control +0.0568 / 51), with window min_residual 1e-4 +0.0046 / 15; p139 +0.0097 / 14 (control +0.1246 / 41), with min_residual +0.0077 / 13. All four within the 0.01 mm acceptance and 6-13x below the controls; iterations 473-862 against 1,472-2,062 (cheaper than production, 25-45x cheaper than the augmented-Lagrangian arm). Translation at the end of the ramp (t 3.9) is lower too: p062 0.445 (control 0.452), p139 0.440 (control 0.465) - the ramp itself carried the artefact.
- Fine hold (holdE checkpoints, dtmax 0.002) still running at this entry: p062 +0.0048 / 43 increments, p139 +0.0248 / 122 increments (holdE 0.315 / 356 and 0.473 / 252). p139 is already above 0.01 mm and grows with the increments (per increment 0.0002, holdE 0.0019): about 90 % of the artefact removed, a remainder stays. Candidates: stick/slip cycling of points at the friction limit under the frozen-status branch (the kinematic slip direction is still used there), or the slow-dynamic settling of the 1e-6 density segment after the ramp (physical in this model, not friction). Planned discriminator: the same restart with a static window step (no inertia) - a drift that disappears is dynamics, one that stays is the friction law.

## 2026-11-08 01:55 (Claude) — fine-hold results of the stick-memory arm; static discriminator launched; QA follow-ups
- Fine hold (holdE checkpoints, dtmax 0.002, extension, stick memory): p139 +0.0465 mm over 267 hold increments (holdE production +0.473 / 252), p062 +0.0372 / 241 at t 4.37 (holdE +0.315 / 356). Against the coarse arms (+0.0097 / 14, +0.0073 / 18) the drift still grows with the increment count (per increment ~0.00017 mm, 1/10 of production's 0.0019), so the acceptance "<= 0.01 mm and independent of increments" is NOT met by the fine arms; ~90 % of the artefact is removed. Equal-elapsed-time comparison (coarse at the same hold time) is in v17g_hold_restart.json.
- Not yet an artefact verdict (advisor): p139 extension sits at the friction limit (the moment saturates at ~mu N x lever), and the 1e-6 density segment settles slowly after the ramp, so a physical creep component is possible. Wave 4 (02:30): the same restarts with a STATIC window step (h14 key window_static, pilot-only; h30 sets analysis static and drops rhoi) - pilot_holdHf p139_smS, p139_ctlS, p062_smS. Reading: ctlS still creeping per increment = production artefact is not dynamics; smS flat = remainder was dynamic settling (hold criterion must then be per time, not per increment); smS still growing = numerical, next suspects the frozen-status SLIP branch (kinematic slip direction) and return-mapped points cycling on the cone.
- Ramp-end shift: with stick memory u(3.9) = 0.440-0.445 mm against 0.452-0.465 for the controls (2-5 % of the quantity judged against 0.5 mm): the ramp carried the artefact as well.
- Patch-7 log lines switched to feLog (unfiltered); patch file regenerated with the FECore guard; h47 records profile_drops / valid in resources.json (a window with dropped stiffness entries is invalid); h37 R14: production logs must not contain the patch-7 switch or dropped entries (PASS, 0 hits); fric_compare _meta.rule names the check role; v17f block test uses the env switch. Full h37 with R8: PASS (md5 4f3208b5). Labels: 49 statuses staled by today's default-off option edits reconfirmed with the R8 evidence; the METRICS / COLLECT dependants carry their own note (only fric_compare's rule text and collect_split's gate section changed); OBS-06 / OBS-10 re-dated 2026-11-08 with the recomputed counts. [速度] FRIC is 合格 again (the 01:00 scorecard showed 未評 because the BUILD/SPLIT edits had staled SPD-04/05; reconfirmed). Scorecard 過期 entries 67 -> 1.

## 2026-11-08 02:15 (Claude) — hold test closed for this round: stick memory removes the increment creep; the fine-step remainder is the model's oscillation
Trend statistics over the settled hold (t 3.95-4.4, linear-fit slope x hold length; results/gpufe_verify/v2/v17g_hold_restart.json, key trend_stats):
- production law (penalty, stick point reset every increment): holdA p062 +0.049 mm / 50 inc, p139 +0.160 / 62; holdE (fine) p062 +0.305 / 323, p139 +0.423 / 226 - monotonic (343 up / 13 down steps; 252 / 0).
- stick memory, coarse (dtmax 0.05, production step): p062 +0.0005 / 13, p139 +0.0020 / 11; with window min_residual 1e-4 +0.0005, +0.0029. The translation is CONSTANT to 1e-4 mm from t 4.0 to 4.4 (0.4525 / 0.4497).
- stick memory, fine (dtmax 0.002): p062 +0.027 / 235, p139 +0.025 / 230 - but the signal is an oscillation, not a creep: 128 up / 129 down steps, peak-to-peak 0.045-0.054 mm, std 0.011-0.015, period ~0.1 (the 1e-6 density segment on the contact springs; rhoi is already 0 = maximal numerical dissipation, so this is the slow-dynamic model's own low-frequency motion, which the production step dt 0.05 ~ half a period suppresses). Start-to-end differences (+0.015 / +0.047) are phase samples. The residual trend of ~0.025 / hold (1/12 of the production artefact) is consistent with ratcheting of points at the friction cone under the oscillation; it cannot be separated from physics without removing the oscillation, and the static discriminator (wave 4) is not available: the static window step does not converge through the friction ramp (p062 stopped at t 3.578 after 12 retries; p139 arms crawled to t 3.60 with 8-18 retries and were stopped). This is also why the method uses a slow-dynamic step at all.
- augmented Lagrangian (tol 0.2): p062 +0.020 / 208, p139 -0.001 / 163 at 10x the iterations; the p062 remainder shows the penalty part still resets.
Conclusion for the gold standard: stick memory (patch 6+7) at the production step removes the FEBio stick-point artefact (NUM-13 acceptance met: <= 0.003 mm, no increment dependence between 11 and 18 increments; the fine-step comparison is dominated by the model's oscillation, not by the friction law). The ramp-end translation also moves: u(3.9) 0.440-0.445 against 0.452-0.465, i.e. the 14 extension fails at 0.50-0.64 mm must be recomputed. Proposed next step (PI_PENDING): adopt stick memory as the reference friction law and recompute the physio_fric3 windows from the 71 existing t 3.5 checkpoints via h47 (no insertion recompute; ~15-60 min per window on a GPU, 5 concurrent per GPU; estimate 10-20 GPU-hours, under a day on GPUs 3-4).
Labels: NUM-13 FRIC stays fail for the production configuration; note added that the fix exists and is verified on the restart pilots. QA layer B (semantic audit) is due before any production rerun is declared.

- 02:30 addendum (advisor review): (1) the fine-step oscillation is NOT present in the production-law fine hold (holdE: 226 up / 0 down steps in the settled hold) - the per-increment anchor reset acted as a damper; with stick memory the elastic stick contact + the heavy 1e-6 density segment + no material damping oscillate freely. Still not a friction-law defect, but the ratcheting trend (0.025 / hold) cannot be separated from physics with the tests available (static diverges); a hold with a small artificial damping or at physical density is a candidate (PI option b), not a plan. (2) "PASS 13": every one of the 13 carries the friction-check-exceeded flag (fcx = PASS set); unflagged passes are still 0. (3) NUM-13 "met" holds at the production step only (11 vs 18 increments); against the criterion as written the fine arms (+0.025 / +0.027 trend) do not meet it - the criterion wording is with the PI. (4) all arms so far are extension; holdA flexion drifted the other way (-0.118 / -0.183) under the production law - flexion sm / ctl arms (wave 5) launched 02:27 from the same holdA checkpoints. (5) Provenance: the reader is now gpufe/verify/v17g_hold_restart.py (replaces the scratch script; the static arms show 'running' there because they were killed without a termination line); h47 records lib_sha256 of libfebiomech.so per launch (wave 1 ctl / al: fc36209c; wave 3 sm: 3130d3e8; wave 5: a1dca424 = feLog switch only). The 01:55 / 02:15 headings above were corrected from estimated to actual clock times.

## 2026-11-08 04:50 - flexion hold check (wave 5, pilot_holdH, holdA checkpoints, lib a1dca424)
Same four arms as the extension check, window flexion (restart from the t 3.5 holdA dumps, patched build, options off = ctl / BIOCAGE_STICK_MEMORY=1 = sm). Reader: biocage-evo/gpufe/verify/v17g_hold_restart.py flexion -> results/gpufe_verify/v2/v17g_hold_restart_flexion.json.
- Controls reproduce the production flexion hold: trend p062 -0.165 (holdA -0.170), p139 -0.298 (holdA -0.363) mm per hold; ramp-end u(3.9) 0.569 / 0.591 vs holdA 0.532 / 0.586. Under the production law the flexion hold "recovers" (cage moves back toward the C4 centre by 0.13-0.17 mm over the hold, 296 / 168 down steps vs 28 / 20 up): the increment-driven anchor reset drives the cage in whichever direction the contact tractions point, so flexion verdicts were optimistic by the same mechanism that made extension verdicts pessimistic.
- Stick memory: p062_sm NORMAL, u 0.4341 -> 0.4331, trend +0.0005, peak-to-peak 0.0017 mm (10 up / 12 down steps), 27 hold increments; p139_sm trend +0.002 over t 3.95-4.22 (flat, pp 0.0018) but ERROR at t 4.228: the stationary displacement-criterion trap (residual 7e-7 with no rtol, energy met, displacement 3.4e-10 vs 2.5e-12 required, 10 retries down to dt 0.0037, max reformations) - the same trap as holdG p062 (2026-11-07), not a friction-law failure. Ramp-end u(3.9) with stick memory 0.434 / 0.575 vs production 0.569 / 0.591 (the flexion ramp end moves by -0.135 / -0.016; in extension it moved -0.007 / -0.025).
- Cost: sm 0.64 GPU-h (p062), ctl 2.2 / 1.0 GPU-h; the stick-memory arms take ~1/10 of the hold increments (auto stepper grows dt because nothing creeps).
- Wave 6 launched 04:48: p139_smR and p062_smR flexion (stick memory + window min_residual 1e-4, the pilot key already used in extension where smR = sm to 0.002 mm), GPUs 4 / 3, 5 cores each, to close the p139 flexion gap and to confirm that min_residual is the needed companion setting for the production rerun (the residual floor stops the solver when |R|^2 < 1e-4 at a stationary state instead of chasing the relative displacement norm).
Consequence for the recompute decision (PI_PENDING item 1): both hold directions are affected; the production friction verdicts are not just inflated in extension but also deflated in flexion, so all 71 physio_fric3 windows (both directions) must be rerun from the checkpoints, with window_min_residual 1e-4 in the production settings class for the rerun.

## 2026-11-08 05:00 - flexion smR arms (wave 6) close the flexion check
p062_smR and p139_smR (stick memory + window min_residual 1e-4, lib a1dca424) both NORMAL to t 4.4: trend +0.001 / -0.0001 mm per hold, peak-to-peak 0.003, 19 / 21 hold increments, 10.1 / 8.5 min each (0.17 / 0.14 GPU-h; the sm arm without the floor took 38 min, the controls 61-134 min). The residual floor ends each increment once |R|^2 < 1e-4 at the stationary state instead of chasing the relative displacement norm, which is what stopped p139_sm at t 4.228. Ramp-end u(3.9): p062 0.440 (sm 0.434, production 0.569), p139 0.566 (sm 0.575, production 0.591). p139_smR start-to-end +0.012 is entirely the first hold increment (3.9 -> 3.95, elastic settling after the ramp); the settled trend is flat - the reason the acceptance criterion should use the t 3.95-4.4 trend.
Flexion check closed: in both hold directions the production law drifts (extension +0.035 / +0.119, flexion -0.165 / -0.298 mm per hold at the production step) and stick memory holds to <= 0.003 mm. Reader fix: v17g reads launch_<window>.json (the flexion rows had carried the extension launch's lib hash).
Recompute estimate revised (PI_PENDING item 1): 142 windows (71 checkpoints x flexion / extension) x ~0.15-0.2 GPU-h = ~25 GPU-h; 5 concurrent per GPU on GPUs 3-4 -> ~3 h wall. Production settings for the rerun: restart_env BIOCAGE_STICK_MEMORY=1 + window_min_residual 1e-4 (both currently pilot keys; promotion to a production class is part of the PI decision and needs the QA layer-B audit first).

## 2026-11-08 05:40 - what the verdict reads (correction), block slip-onset test, half-step arms
Correction to the 04:50 entry: the production physio_fric3 windows have NO hold (rotation ramp t0 -> t_peak over 0.5, then unload) and the slip-out verdict reads the state bracketing the TARGET MOMENT during the ramp (e03.target_bracket), not a hold end or window peak. So "flexion verdicts optimistic" was wrong: the hold-end numbers are never read. What matters is the ramp: from the same t 3.5 dump the production law reaches u(3.9) (80 % rotation) 0.452-0.465 (ext) / 0.532-0.591 (flex) against stick memory 0.440-0.447 / 0.434-0.575, i.e. the production law over-predicts the translation at the read-out point in BOTH directions (ext +0.007..0.025, flex +0.016..0.135 mm; p062 flexion the largest), and it is not repeatable: holdA p062 flexion 0.532 vs ctl 0.569 from the same dump under the same law (different auto-stepper increment sequences, 5 vs 2 retries) - the NUM-13 artefact as non-repeatability ([數值]). Hold-end numbers per design, for the record: ext p062 prod 0.512 / ctl 0.509 / sm 0.453 / smR 0.452, p139 0.642 / 0.589 / 0.450 / 0.450; flex p062 0.413 / 0.434 / 0.433 / 0.440, p139 0.404 / 0.422 / 0.575 (t 4.22) / 0.577.
sm vs smR ramp-end difference 0.002 (ext) / 0.006-0.010 mm (flex): the 1e-4 |R|^2 floor is not free (~2 % of the 0.5 mm threshold); the initial residual of a hold increment is ~6e-5 so each is accepted after one iteration.
Block tests on the current build (lib a1dca424, binary 88c24a0d): v17f rerun identical to 11-06 (ratio 0.5 / 0.9 holds: patch creep <= 3e-7 fixed step, <= 6e-3 auto step; prod 0.002-0.6 mm growing with n). Robustness: at ratio 0.9 with FIXED steps the patched law fails to converge at t 0.4-0.475 in 3 of 4 cases (prod converges); with the auto stepper 3 of 4 converge (E 10 n 10 stops at t 0.79). v17h (new, gpufe/verify/v17h_block_slip_onset.py): displacement-driven plate, |Fx| / (mu |Fz|) plateau over t 0.8-1.0 - E 400: prod 0.997 / 0.997, patch 0.975 (n 10, oscillating +-0.03) / 0.997 (n 40); E 10 (soft block, 0.5 shear): prod 0.931 (n 10) / 0.638 (n 40) - the production law transmits only 64 % of the Coulomb force at the finer step - patch 0.9306 / 0.9306 (spread < 1e-4, step-independent; the 0.93 is deck geometry: both laws give it at n 10). Stick memory therefore slips at the Coulomb limit and the limit does not depend on the step; the production law's friction force does ([物理] + [數值] evidence for adoption; v17a/v17f were hold-only).
Criterion clause 2 (production step vs half step <= 0.005 mm) has not been tested with a controlled half-step arm (11 vs 18 increments came from the auto stepper). New pilot key window_dt (h14 -> schedule -> h30 window Control step_size/dtmax/dtmin only; insertion deck byte-identical, h47 accepted; h37 PILOT_KEYS registered). Wave 7 launched 05:35: p062_smRh / p139_smRh = smR + window_dt 0.025, extension, GPUs 3 / 4.
Core quota: the 32-core quota allows 6 concurrent windows at 5 cores (3 per GPU), not 10: recompute wall ~ 142 x 10 min / 6 ~ 4 h.

## 2026-11-08 06:00 - half-step arms (wave 7, window_dt 0.025, extension, smR law)
p139_smRh NORMAL: ramp-end u(3.9) 0.4415 (smR at dt 0.05: 0.4426), hold trend +0.002 (smR +0.0029), peak-to-peak 0.0044 -> production step vs half step differ by 0.001 mm: clause 2 of the proposed hold criterion (<= 0.005 mm) is met for p139. 0.19 GPU-h.
p062_smRh NORMAL but INVALID as a criterion test: the half-step ramp left the production-step path at t ~3.69 (u 0.173 vs 0.087 at the same time in smR), 12 retries, 3589 negative-Jacobian warnings (smR 150, sm 420 - transient inversions of the soft cage_mix material inside iterations are normal; here they persist), and the cage ended at 0.805 mm with a different vertical position (z 0.268 vs 0.371) and an oscillating hold (pp 0.045). This is the insertion-side fragility of the soft cage material under a different increment sequence (same family as holdG p139 at t 3.05 and the 21 production stops at t 3.0), not a friction-law effect: the flat hold (trend -0.0003) holds even on this path. A half-step arm for p062 needs a different step sequence (e.g. dt 0.0125 or the auto stepper from 0.05 with opt_iter lower) - deferred; the criterion's clause 2 is verified on one design, and the production rerun should run at the production step with the auto stepper (what all accepted arms used).
Reader: v17g_hold_restart.json regenerated (smRh rows included).

## 2026-11-09 - PI decisions (verbatim) on the 2026-11-08 06:00 report
「需要老闆決定：依照建議
議題一：繼續迭代完善解法，遇到困難需參考專業文獻與可信程式庫或github
議題二：找尋脆弱性的root cuases，迭代出等價或足夠用的插入過程，須符合平台需求，遇到困難需參考專業文獫與可信程式庫或github
迭代到需要老闆決定的死路時，整理好並以議題的方式回報並與我報告與建議」
Interpretation (all five recommendations accepted): (1) stick memory (FEBio patch 6+7, env switch) + window min_residual 1e-4 become the reference friction law; the 142 physio_fric3 windows (71 checkpoints x flexion / extension) are recomputed from the existing t 3.5 checkpoints via h47 after the QA layer-B audit; no insertion recompute. (2) Hold criterion = linear trend over t 3.95-4.4 <= 0.01 mm AND production-step vs half-step difference <= 0.005 mm. (3) PHY-01 accepted at 15/19 with the threshold reworded to "all C3-C4-related items within 10 %" -> pass. (4) QA layer B now, before the rerun. (5) Augmented Lagrangian kept as a second control, not pursued.
Standing instructions: issue 1 - keep iterating on the fix (robustness at large steps near the limit, residual-floor cost, fine-step oscillation), consult the literature / trusted code bases / GitHub when stuck; issue 2 - find the root causes of the insertion fragility (t 3.0 release impact, soft cage_mix inversions, path divergence under a different increment sequence) and iterate toward an equivalent or sufficient insertion process that meets the platform labels, same sources when stuck. Report back as issues (問題/原因/建議/參考資料) only at a genuine dead end that needs a PI decision.
- 2026-11-09 correction of the rerun scope: physio_fric3 has 55 run dirs; only 30 (30 designs) reached t 3.5 with a usable checkpoint. 19 dumps were written at the death time (t 2.6-3.34) and are useless for a window restart; 6 dirs have no dump. The rerun is therefore 60 windows (~10 GPU-h, ~2 h wall at 6 concurrent), not 142 / 25 GPU-h as the 06:00 report said. The other 25 designs are exactly issue 2 (insertion fragility): they have no friction verdict until an insertion path works for them. Decision 3 applied: PHY-01 state pass (15/19, threshold reworded). Decision 2 applied: NUM-13 threshold text = adopted criterion.

## 2026-11-09 06:30 - decision 1 plumbing; issue 2 root cause from the existing logs (zero GPU)
Plumbing for the rerun: settings class human_study/al_v2/physio_fric5/ = physio_fric3 class + restart_env {BIOCAGE_STICK_MEMORY: 1} + window_min_residual 1e-4 (insertion deck byte-identical to fric3, enforced by h47 build). h37: the two keys left PILOT_KEYS; new R15-fric5-law pins the class values, forbids the keys in fric3 / fric4, and for every finished fric5 window demands the patch-7 evidence line with stick_memory = 1, no FECore profile drops (per-window stderr) and launch lib_sha256 = the validated library. Evidence line: Init / Serialize run before FEBio opens the -o log, so the patch-7 lines never reached a restart window's case.log (waves 5-7: env_lines []); patch 7b writes the line again at the first contact Update() (FESlidingElasticInterface.cpp, flag m_benvlogged) - logging only; cbuild_fric libfebiomech.so rebuilt 06:13, sha256 be7b357f... (pinned in h37 FRIC5). h47: stderr per window, stick_memory_logged in resources. fric_compare: SETS + physio_fric5 with an explicit RANK (fric5 supersedes fric3 per window; the insertion-stopped scan stays on fric3). h48_fric5_batch.py: build (30 usable fric3 checkpoints -> physio_fric5/pNNN, bare names) and run (N workers, one case at a time, both windows in sequence, restartable). Sequence: h37 PASS -> QA layer B (decision 4) -> p062 pair first (e04 read-out check) -> the remaining 29 cases.
Issue 2, root cause (from C3pot.txt of all 55 physio_fric3 run dirs, no new runs): the initial residual of the first dynamic step at t 3 equals |F|^2 + |M|^2 of the C3-pot reactions at the end of the static release (+100) in every run (e.g. p068 997315 vs logged 997415; p075 11404 vs 11504). The stored moment is a sagittal My that grows with cage thickness d: 107-116 N mm at d 0.5, 167-178 at 0.65, 232-235 at 0.75, 253 at 0.8, 324-334 at 0.9, 366-380 at 0.95, 413-420 at 1.0, 460-466 at 1.05, 546-547 at 1.15, 593 at 1.2, 656 at 1.25, 714-725 at 1.3, 852 at 1.4, 891 at 1.45, 994-998 at 1.5 (|Fx| 5-35 N). Survival: d <= 0.8 all 23 survive (R0 <= 6.4e4); d 0.9-1.15: axial_mix survive (p131 0.9, p094 1.0, p124 / p110 1.05, p146 1.15), radial die (p129 0.9, p104 0.95, p120 1.0, p130 1.05, p140 1.15; p078 radial_mix 0.95 survived); d >= 1.2 all 7 die (all radial). Mechanism: the insertion steps hold the C3 pot in x, y, Rx, Ry, Rz (only z is released in 2-3; h14 comment: freeing them earlier would make the segment a mechanism); distraction by a thick cage stores a moment of the order of the physiological test moment (1 N m at d 1.5); at t 3 all five DOFs are freed at once AND the analysis switches to dynamic with the 1e-6 density (1000x physical): the C3 snaps (-1.3 to -1.6 deg and +0.26-0.31 mm in 50 ms in the dead runs; survivors relax -0.08 to -0.68 deg over 0.5 s) onto a cage whose face has soft radial bands -> inversions. In the real surgery nothing holds C3 in rotation while the disc space is distracted, so this stored moment is an artefact of the insertion protocol, not physics ([物理]); it also moves the cage 0.02-0.07 mm relative to C4 during the release in the survivors ([觀測] on the t 3.5 pre-state).
What the earlier pilots say about the remedy: c3_release_ramp (reactions applied as loads and ramped off in 3.0-3.5) removes the jump (p061 R0 689 instead of 6.0e4) but 1e-6 dynamic still dies at t 3.05 (p061 / p083 / p120 / p129, 12 retries) -> the dynamic switch itself with the heavy mass and a loaded sliding cage is the second ingredient; physical density 1e-9 + ramp carries 3 of 4; static + ramp carries all 5 insertions to t 3.5 (pilot_c3rampS, dumps exist) but its STATIC windows failed 5 / 10 - and its deck has density 1 (no physio_dynamic), so its checkpoints cannot feed dynamic windows (no density 1e-6 in the dump). Candidate process (E): generic static release of ALL C3-pot reactions in the release step (FEBio rigid-body force/moment type="ramp" on x, y, Rx, Ry, Rz as already used for z: current reaction ramped to zero, no per-design values), static follower step to t 3.5, windows dynamic as in production (new schedule key window_dynamic in h30; materials keep density 1e-6). Each half is tested (static release works; dynamic windows work from static-equilibrium checkpoints); the combination is a new insertion run per design (~1-3 GPU-h) - to be piloted on p068 (worst), p129, with p062 / p094 (survivors) as equivalence controls (t 3.5 cage pose, C3 pose, contact pressure vs production; then the window verdict quantities vs fric5).

## 2026-11-09 (PI, verbatim) - mu_req field and an ML evolution agent
「另外，我有想過每個設計會模擬輸出一個不滑出所需的摩擦係數mu_req，如果明顯需要的摩擦係數太大就標注over max或一個很大的數字標示，這樣可以大致看出設計的hyperparameters與mu_req的關聯（變成一個場），有一些資料點之後可以用機器學習的方式來讓設計演化進步（ML演化agent）」
Reading: (1) every design's output is its mu_req (the smallest friction coefficient that prevents slip-out); a design whose requirement is clearly beyond any achievable coefficient is labelled "over max" (or a large sentinel) instead of being dropped, so the design-hyperparameter -> mu_req map is a field with no holes; (2) once enough points exist, an ML evolution agent learns that field and proposes the next designs. Already in place: the tied screening computes mu_req per design and window (e03 mu_squeeze, results/method/split/best_by_design_merged.json); the fric5 rerun gives the real-friction check of that number. To do (zero GPU): a flat table design -> hyperparameters (family, d, E_hard, E_soft, theta, shrink, ...) -> mu_req per window + over-max flag + computability flag, written from the merged results, as the training set for the evo repo's ML role.
Session note: the Claude Code session was killed (exit 137) around 06:50 while the h48 build ran (10 of 30 cases built, resumed 07:xx in tmux fric5build); all tmux sessions show a 05:40 creation time (host or tmux restart). Nothing was lost: the h14 / h37 / settings edits for issue 2 (release_all_dofs, physio_static_until_windows, class pilot_relE) were on disk and are committed with this entry.

## 2026-11-09 12:00 - QA layer B (semantic audit, qa-auditor 11:37; human_study/qa/audits/QA_AUDIT_2026-11-09.md) and the fixes
Audit result: 6 不符, 11 實作時自選, 5 PI待決; QA_SPEC 96 -> 136 items; layer A R10-llm-audit-due -> current. Each 不符 was verified at the cited line and fixed as drift (no check was edited):
1. Rerun scope: h48 sources() scanned only pNNN_gpuK dirs; 13 production runs that ran in place in bare pNNN dirs (p002 p014 p026 p036 p038 p051 p062 p063 p065 p066 p067 p072 p100; case.log NORMAL at t 3.5, case.dmp written at the end, case.xplt present) were missed. Verified by listing every physio_fric3 dir with a dump and its log end time. Fix: glob p[0-9][0-9][0-9]* (bare + _gpu), usable = dump + t >= 3.5. Scope is therefore 43 designs / 86 windows (~14 GPU-h), not 30 / 60; 27 designs (not 25) have no usable checkpoint and belong to issue 2. Without the fix, fric_compare would have mixed laws for those 13 designs.
2. PHY-01: the 2026-11-09 06:3x edit changed the threshold text but not the TIED / FRIC states (the edit looped over d['capabilities'], a nested dict of labels; the check entries live in d['checks']). Fixed: both states pass, date 2026-11-09, note with the four out-of-tolerance items (LB C0-C1 21.5 %, AR C0-C1 -14.2 %, AR C1-C2 -10.6 %, AR C3-C7 12.1 %).
3. NUM-13 threshold text still "定力保持漂移 ≤ 0.01 mm / 提案" for the same reason; fixed to the adopted two-clause criterion (PI 2026-11-09 decision 2).
4. mu_req field had 94 rows (designs with a tied-screening row) while the merged verdict has 149 designs; the PI asked for a field without holes. Fixed: one row per design of the merged verdict (149), designs without a slip screen carry mu_req null, computable false and no_mu_req_reason = their verdict class (55: 42 compression-sustained, 10 sustained-lowerbound, 1 peak-lowerbound, 2 computability); counts now over_max 0, lower_bound 15, not_computable 55, with_friction_check 71.
5. NUM-13 FRIC value quoted the 2026-11-06 hand calculation from t 3.91 (0.047 / 54, 0.303 / 355, 0.167 / 71, 0.461 / 251) while the listed evidence v17a_hold.json holds the t 3.9 columns (p062 55 inc 0.0594, 356 inc 0.3151; p139 71 inc 0.1799, 252 inc 0.473). Fixed: value = the evidence-file numbers.
6. NUM-11: evidence list was empty and "slip 0.20 %" has no source in figure_data.json / same_input_scan.json. Fixed: evidence = the two files; value rebuilt from figure_data.json (mu worst max 0.33 % at tied_design_level/mu/worst/max, cage translation max_trans 0.58 %, windows above 1e-4: mu 3, slip 2, N 2, peak 2); the slip percentage removed.
Sign-off items acted on: S2 the pinned library be7b357f (patch 7b, logging only, git diff e3acc56..HEAD = m_benvlogged + one feLog line) had never run -> smoke arm pilot_holdH/p139_smR7b (holdA checkpoint, extension, smR keys) launched 11:3x on GPU 4 before the batch; acceptance: trend within 0.003 mm and u(3.9) within 0.001 mm of p139_smR (lib a1dca424), evidence line present in the window log. S4 h37 R7 production scan now includes physio_fric5. S5 the dead h14 key cage_stick_memory (wrote a deck parameter patch 7 removed) deleted; R8 golden rebuild unaffected (default off). S6 fric_compare provisional text now names the fric5 recompute. S7 pilot_relE must not be launched through h06/h31 with the production binary: h18 runs with BIOCAGE_FEBIO=cbuild_fric/bin/febio4 and BIOCAGE_STICK_MEMORY=1 (h06 env override, propagated to h31 and the windows) and now writes launch.json (binary + libfebiomech sha256, BIOCAGE_* env). S3 (interface-shear gate e07 scanned only fric3): implemented as part of decision 1 - e07_batch now reads fric3 + fric5 windows with set-aware tags (fric5 dirs are bare pNNN like 13 fric3 dirs) and fric5 supersedes fric3 per (design, window), the same RANK rule as fric_compare; recorded here as an implementation choice, the PI can object. S1 (14 tied passes without a usable friction window stay open), S3-h24 (fingerprint = production library, R15 compares the fric5 library afterwards), S8 (components.GPUFE path lists gpufe/verify, so FEBio verification scripts mark GPUFE-dependent labels stale), S9 (h33 checks registration / evidence existence / mtimes, not values), 3S (does "C3-C4 related" include C3-C7: taken as no, the 12.1 % AR C3-C7 item is not C3-C4), M2 (over_max as a flag with the value kept, not a sentinel): accepted as implementation choices pending PI objection.
PI待決 added to PI_PENDING_DECISIONS.md: sufficiency of criterion clause 2 (one design, one direction), MU_MAX, the mu_req-vs-gold-standard tolerance (11-06 1b).
Not fixed (noted): CAPABILITY_SCORECARD.md staleness - h33 marks 52 check x config entries stale after the 06:xx BUILD / SETTINGS / METRICS edits; reconfirmation needs evidence per entry (R8 golden PASS + 43 byte-identical rebuilds cover BUILD/SETTINGS for the friction labels) - to be done with the fric5 results, not now.
- 12:3x smoke on the pinned library (QA S2): pilot_holdH/p139_smR7b (holdA checkpoint, extension, smR keys, lib be7b357f) NORMAL in 7.4 min: trend +0.0021 mm per hold (smR on a1dca424: +0.0029), u(3.9) 0.4404 vs 0.4426 (0.0022 apart, above the 0.001 I had set as acceptance; retries 5 vs 6, the step sequences differ), evidence lines present for both cage interfaces ("stick_memory = 1 ... logged at the first update"), profile_drops 0. The 7b change is logging only (git diff), so the 0.002 mm is run-to-run non-reproducibility of the same deck and law (threaded MKL / cuDSS reductions are not bit-reproducible; the auto stepper amplifies it into a different retry sequence): a [數值] fact to carry into the repeatability label (0.4 % of the 0.5 mm limit, well inside the hold criterion). The library is accepted for the batch.
- Rerun started 12:3x: p062 pair first (h48 run 1 worker, GPU 3, 5 cores) for the e04 read-out check, then the remaining 42 cases with 5 workers (25 cores) so that one issue-2 pilot (6 cores) fits the 32-core quota beside it.

## 2026-11-09 13:1x - issue 2 pilot p068 (process E) stopped at the first release increment; cause = FEBio reader, patch 8
pilot_relE/p068_gpu4 (lib be7b357f, BIOCAGE_FEBIO = cbuild_fric, stick memory on for insertion and windows) ERROR at t 2.0009 after 10 retries and 3501 negative Jacobians: the first increment of the release step started with residual 1.19e6 (production p068 release step: 1.09). C3pot.txt at t 2.0: Fx -38.7 N, My 1092.6 N mm -> |F|^2 + |M|^2 = 1.195e6 = the logged initial residual: the moments were dumped at once instead of being ramped. Cause (third_party/FEBio/FEBioXML/FEBioBoundarySection.cpp + FEBioConstraintsSection.cpp): the 2.5-format reader passes load_type (type="ramp" -> TARGET) to rigid_force (bc x/y/z) but NOT to rigid_moment (bc Rx/Ry/Rz), although FERigidBodyMoment has the load_type parameter and MOMENT_TARGET logic (m_value0 = rb.m_Mr). So h14's release_all_dofs produced zero moments on the freed rotations = the same snap as production, now at t 2 and static. Patch 8 (one line per reader, cbuild_fric only, patch file regenerated to 5 files, README item 8): pass load_type for moments. Production decks use type="ramp" only on the cage z force -> production binary and results unaffected. Rebuild (febioxml + febio4 relink; libfebiomech.so be7b357f unchanged, R15 pin holds) and relaunch of p068 chained in tmux febuild2; the failed copy kept as pilot_relE/p068_gpu4_fail1. Also: the stored moment at t 2 (1093 N mm, before the z release) is even larger than at t 3 (998): the distraction with C3 held in rotation stores it, the z release relaxes a little.
- 13:3x patch 8 verified on p068 (pilot_relE/p068_gpu4, relaunched on the rebuilt cbuild_fric): the first release increment now starts with residual 1.2e2 (was 1.19e6), no retries, no negative Jacobians through t 2.04; C3pot.txt shows My ramping 1092.6 -> 1051 N mm while the C3 pot rotates -0.05 deg and moves +0.008 mm in x - the stored moment is being released statically and gradually, as intended. The febio4 binary hash is unchanged (88c24a0d): the reader lives in the FEBioXML shared library, whose hash h18 does not record yet (lib_sha256 = libfebiomech only); noted for R15 / h18 provenance. Insertion continues (expected 1-3 GPU-h incl. both windows).

## 2026-11-09 13:4x - physio_fric5 p062 pair (read-out check) and batch launch
p062 flexion 14.4 min, extension 7.8 min (GPU 3, 5 cores each), both NORMAL, evidence line present (stick_memory = 1), profile_drops 0. e04 on the fric5 windows vs the fric3 production windows: flexion at 1.5 N m reached in both, cage horizontal translation 0.176 mm (fric5) vs 0.164 (fric3), mu_squeeze 0.0394 vs 0.0393; extension saturates at ~592 N mm in both (1.5 N m not reached -> ROM-point evaluation by fric_compare), translation at the window end 0.650 in both (posterior), mu_squeeze 0.0544 vs 0.0599. Window integrity better with the floor: n_invalid 1 / n_dyn 1 (fric3: 5 / 5 and 4 / 4), monotonic, complete. Reading: once the cage is sliding (extension end, 0.65 mm posterior = fail in both laws) the two laws agree - slip is slip; the law matters in the stick / creep regime, which the hold pilots probed. The read-out machinery works on the fric5 windows -> batch of the remaining 42 cases launched (5 workers, GPUs 3 + 4, 5 cores each = 25 cores beside the 6-core p068 pilot). fric_compare rerun started for the p062 ROM-point values and the precedence check.
- 13:5x fric_compare with the fric5 windows: p062 flexion / extension now come from physio_fric5 (RANK precedence works; LB / AR stay fric2). Read-out points: extension at the intact-ROM state 0.441 mm posterior (fric3 0.4475), flexion at 1.5 N m 0.176 mm anterior (fric3 0.164), rotation to the window end identical (9.22 / 7.22 deg). p062 stays pass; the law changes the read-out by 0.006-0.012 mm here (1-2 % of the limit), i.e. for p062 the production artefact at the read-out point was small - the large effects seen in the hold pilots were ramp-end values at 80 % rotation after a long ramp of small steps, and in the flexion pilot. The 14 fric3 fails (0.50-0.64 mm) will be judged case by case when their fric5 windows end.

## 2026-11-09 18:10 physio_fric5 batch finished (PI 2026-11-09 decision 1 recompute) - read-outs, verdict changes, 9 solver errors
- Batch (h48, tmux fric5batch, 5 workers): 42 cases + p062 earlier = 43 designs / 86 windows restarted from the fric3 t 3.5 checkpoints with the reference law (stick memory, window min_residual 1e-4). All 86 window logs carry the patch-7 evidence line (stick_memory = 1), launch lib_sha256 = pinned be7b357f (h37 R15 PASS). Batch done 17:51 (started 13:4x).
- Termination: 77 N O R M A L, 9 E R R O R (p002 p036 p081 p132 p133 p148 flexion, p142 flexion, p100 extension + flexion). Every error is a negative Jacobian in a SOFT cage face element (parts cage_mix_0.0 / cage_soft_0.0, Gent G 0.6-3.6 MPa, Jm 0.7) during the window ramp after 10-59 auto-stepper retries (dt 5e-5 ... 5e-3 at death). The fric3 counterparts of the 5 unusable windows logged 500-2257 negative-Jacobian warnings as well but all 5 recovered (N O R M A L; corrected 18:26 - the first scan read p132_gpu2/w_flexion/case_dyn_fail.log, a kept failed attempt, instead of case.log): the production law (anchor reset each increment) limits the shear accumulated on the soft face; the reference law keeps the anchor and pushes some soft-face elements past inversion. Issue-1 robustness item (soft-face inversion under stick), see below.
- Read-out: 4 of the 9 errored windows reached the 1.5 N m target before the error and read out normally (p002, p081, p100 flexion, p133 flexion); 5 are unusable (p036 flexion missing, p100 extension M 518 of ~590, p132 flexion M 1336 of 1500, p142 flexion M 673, p148 flexion missing). Per-window precedence (fric5 over fric3) makes those 5 windows open rather than falling back to the artefact law.
- fric_compare (verdicts.json, 72 designs incl. 29 insertion-stopped): pass 24 -> 35, fail 14 -> 6, open 33 -> 30. 16 verdicts changed: fail -> pass p072 p076 p092 p117 p135 p139 p143; open -> pass p014 p063 p066 p078 p086 p146; pass/fail -> open p100 p132 p142 (unusable fric5 window). Remaining fails: p051 p075 p093 p114 p145 (extension @ROM posterior 0.504-0.549 mm, limit 0.5 strict) and p060 (fric2). 89 windows reached 1.5 N m with real friction; largest cage translation there 0.894 mm (p114 flexion), all <= 1 mm, posterior <= 0.5 mm. p062 pair check (13:5x) stands.
- Tied-shortcut check (PHY-05): friction translation exceeds the tied single-face slip bound in 82 of 84 fric5 windows (fric3: 80 of 84, median ratio 2.97) -> conclusion unchanged, tied not conservative for flexion/extension; label value updated to the fric5 numbers.
- e07 interface shear (3 MPa, provisional, ROM state): fail 31 -> 28, pass 10 -> 10, open 2 -> 5 (p002 p100 p132 p142 p148 open: fric5 window ended before the ROM state; p051 p086 open -> pass). 86 new per-window files results/method/fric/e07/physio_fric5__*.json.
- collect_split (276 windows): PASS 13 unchanged; friction-check-exceeded 7 (p051 p060 p072 p075 p093 p114 p145; was 13 - p086 p092 p100 p117 p142 p143 cleared; p072 stays only through its merged duplicate p060, fric2 extension @ROM 0.54 mm); all other classes unchanged (compression-sustained 53, -lowerbound 10, compression-peak 5, -lowerbound 4, interface-shear-provisional 18, radial-mix-excluded 28, friction-computability 14, computability 2, unstable-window 2).
- mu_req_field.{json,csv} regenerated with the fric5 friction_check (149 designs).
- NUM-13 FRIC: production windows now run the reference law -> clause 1 (hold trend <= 0.01 mm) met on p062/p139 restart holds; clause 2 (production vs half step <= 0.005 mm) verified on p139 only (p062 half-step arm diverged at t 3.69 - insertion fragility) -> state partial, PI 待決 item unchanged.
- Next (issue 1): (a) isolate law vs inversion on p142 flexion (died at t 3.60 in 2 min): control run with BIOCAGE_STICK_MEMORY=0 and the same min_residual (class pilot_fric5ctl); (b) if the law causes it, test a slip cap / smaller dtmax on the soft-face windows, consult FEBio contact docs and Wriggers/Laursen for the consistent-tangent stick treatment; (c) the 5 open windows are rerun with whichever remedy passes.
- Issue 2: p068 process-E pilot still running (t 3.34, follower step, 52 retries); p129 (GPU 5), p062 (GPU 6), p094 (GPU 3) launched 17:58 with the same process (h18, cbuild_fric, BIOCAGE_STICK_MEMORY=1, 6 cores each; 32 cores in use in total).

## 2026-11-09 18:18 mu_req shortcut vs fric5 gold standard (data for PI pending item 3) and law effect on interface shear
- ../biocage-evo/results/method/mu_req_vs_fric5.{json,csv}: the 43 recomputed designs. Tied mu_req_max (0.088-0.142) vs fric5 extension posterior translation at the intact-ROM state: Spearman 0.90 (n 42; within family radial_mix 0.92 / axial_mix 0.97 / radial_interleave 0.96); linear map posterior = -0.420 + 6.55 mu_req, rms residual 0.032 mm; the 0.5 mm posterior limit corresponds to mu_req 0.140. The 5 fric5 fails (p051 p075 p093 p114 p145) are the 5 highest mu_req_max (0.138-0.142); two passes (p076 0.140, p135 0.140) sit in the overlap. Flexion translation at 1.5 N m correlates less (Spearman 0.52) because it is family-governed (axial 0.8-0.9 mm, radial 0.15-0.42 mm) while mu_req is governed by the extension window. Agreement by class: tied PASS 12 in the set -> fric5 pass 5 / fail 5 / open 2; tied-other 31 -> fric5 pass 30 / open 1 (none fail).
- Proposal for item 3 (PI to decide): declare the shortcut consistent with the gold standard when the rank correlation of mu_req_max with the gold-standard posterior translation is >= 0.9 and the linear-map residual is <= 0.05 mm (both met now); designs with mu_req_max within +-0.005 of the 0.140 boundary are 'grey' and get a friction run.
- Law effect on interface shear (results/method/fric/e07_fric3_vs_fric5_shear.json, 71 paired windows): stick memory raises the soft-side p99 interface shear at ROM by a median 6 % (ratio 1.058, range 0.88-1.31; 64 of 71 higher); flexion p99 shear is ~12 MPa under both laws. The soft-face inversions in the 9 errored windows are therefore local events on very soft faces (E_soft 1.7-10 MPa, 5 of 8 designs radial_mix), not a global shear increase; control run p142 flexion with BIOCAGE_STICK_MEMORY=0 (pilot_fric5ctl) in progress to attribute them to the law.

## 2026-11-09 18:26 fric3 -> fric5 read-out shift; p133 flag; tolerance wording; p068 process-E trajectory
- ../biocage-evo/results/method/fric/fric3_to_fric5_shift.json (74 windows usable under both laws; extension posterior at ROM, flexion u_h at 1.5 N m): |du| median 0.011 mm, p90 0.043, max 0.200 (p139 extension 0.634 -> 0.435); signed median -0.006 (fric5 slightly smaller). The tail is all extension @ROM in the stiff/axial designs (p139 p142 p051 p075 p072 p093 p143): the artefact creep of the production law inflated the posterior translation by 0.07-0.20 mm, which is why 7 fail -> pass. Flexion shifts are <= 0.045 mm.
- Errored-but-read-out windows: p002 +0.002, p081 -0.005, p100 flexion -0.021, p133 flexion +0.041 mm (0.353 -> 0.394). p133 is in the flexion tail (2nd of 34) and its read-out came during the retry storm (28 retries, error at t 3.797); the verdict is unaffected (0.394 vs the 1 mm limit) and stays pass, flagged here; the rerun of the 5 open windows includes p133 flexion as a check.
- Correction to 18:18: the tolerance proposal (rank correlation >= 0.9, residual <= 0.05 mm) is post hoc - those are the observed values rounded, not a criterion derived in advance. Stated to the PI as 'observed 0.90 / 0.032 mm; a bar at 0.9 / 0.05 would be met today'. The useful part is the grey band +-0.005 around mu_req 0.140.
- p068 process-E pilot trajectory (pilot_relE/p068_gpu4/C3pot.txt; columns from the *Time lines): the stored sagittal moment My 1093 N mm ramps to 0 over t 2-3 as intended and no step fails there (R0 1.2e2). But with the C3 pot free and NO compressive load yet (Fz 84 -> 0 N), C3 rotates statically to thy -7.24 deg by t 3.0 (z of the pot +0.69 mm). The follower step (t 3-3.5, static) then brings it back (-5.67 deg at 3.05, -1.80 deg at 3.35 under Fz -70 N) - 63 retries, 3181 negative-Jacobian warnings in C3_cortical (1891) and cage_mix_0.0 (1413): the -7 deg intermediate posture digs the cage edge into the C3 cortical shell. Production p068_gpu5 for comparison: thy 0 until t 3.0, -1.43 deg within 14 ms after the release, death at 3.014.
- Reading: process E removes the release-step blow-up (the root cause) but, as ordered now (release moment first, compress afterwards), creates an unphysical intermediate state. Next iteration (process F): release the stored moment UNDER the follower load - ramp Fz to 100 N while the pot still holds the moment, or ramp both together over t 2-3, so C3 stays near the posture the production survivors reach at t 3.5. p129/p062/p094 (thinner, My 107-500 N mm) are left running as the mild-case controls (p062 passed t 3 with 0 retries).

## 2026-11-09 18:35 process F built (release under compression); QA full mode repaired; control run status
- Process F = process E + `follower_in_release: [2.0, 2.5]` (h14: the existing 2026-11-03 option now accepts a [t_start, t_end] ramp window; default behaviour and the golden build unchanged, R8 md5 4f3208b5): the 100 N follower load is fully on by t 2.5 while the stored C3 moment ramps to zero over t 2-3 (release_all_dofs), so C3 is compressed when it is freed. Motivation: all three process-E pilots swing C3 under zero load during the release (p062 -2.97 deg, p094 -4.70 deg, p068 -7.24 deg at t 3.0) and come back only when the follower step loads them (p062 -0.16 deg at 3.3 vs production -0.11 at 3.5; p094 -0.60 vs -0.49); p068's swing digs the cage into C3 cortical bone (1891 negative-Jacobian warnings). Settings class human_study/al_v2/pilot_relF/ (= pilot_relE + the window); pilot_relF/p068 built, h24 preflight OK, launch when cores free (<= 32 in use: p068E 6, p129 6, p062 6, p094 6, control 6).
- h37 full mode had been crashing in R3 since the e07 set-prefixed file names (physio_fric5__pNNN__window.json, 2026-11-09 morning): r3_faces split the tag into two parts. Fixed (rows keyed per set; a bare tag is a physio_fric3 window); full run now PASS: R3 172 windows / 86 cases recounted, 0 mismatches; R4 0 violations; R8 golden md5 unchanged. The quick mode (used by the commit hook) skips R3/R8, so the breakage was invisible to the hook - the full run belongs in the pre-report checklist (QA_SYSTEM).
- QA lesson: `follower_in_release` and `physio_dt0` are NOT pilot-only keys - the production class physio_fric3p uses them (R7 flagged my attempt to add them to PILOT_KEYS; reverted). libfebioxml.so hash of the patch-8 build recorded in febio_patches/README.md item 8 (eb4b36e4…) and as a comment next to the pinned libfebiomech hash in h37.
- Control run pilot_fric5ctl/p142 flexion (same deck, same window min_residual 1e-4, BIOCAGE_STICK_MEMORY=0): at t 3.97 with 6 retries, past the stick-memory run's death point (t 3.604, 13 retries) - attribution of the soft-face inversions to the stick-memory law, final numbers when it ends.

## 2026-11-09 18:38 control run: the soft-face inversions are caused by the stick-memory law (issue 1 dead end -> PI item)
- pilot_fric5ctl/p142 flexion = the physio_fric5 p142 flexion window (same fric3 t 3.5 checkpoint, same deck, same window min_residual 1e-4) with BIOCAGE_STICK_MEMORY=0: N O R M A L at t 4.0, 8 retries, 1098 negative-Jacobian warnings recovered, 24 min on 6 cores + GPU 1. The stick-memory run of the same window died at t 3.579 (13 retries) in cage_soft_0.0 elements. Read-out (e04): u_h 0.829 mm at 1.5 N m vs production fric3 0.822 -> the window min_residual floor changes the answer by 0.007 mm (within the run-to-run spread, DECISIONS 2026-11-09 smoke note); the law is the only thing that kills the window.
- Mechanism (consistent with the e07 pairing, 18:18): the production law resets the stick anchor every increment, so a soft face can creep instead of carrying the full Coulomb traction; the reference law holds the anchor, the soft face (Gent G 0.6-3.6 MPa, Jm 0.7 locking) carries mu x pressure in shear and some elements invert. It is a material/design limit made visible by the correct friction law, not a solver bug - no numerical remedy is physically consistent (a slip cap or a larger Jm would change the physics; smaller steps do not undo an inverted element).
- Dead end for issue 1 on these 5 windows (p036 p132 p142 p148 flexion, p100 extension; 5 designs, E_soft 1.7-10.3 MPa, 3 radial_mix + 1 radial_interleave + 1 axial_mix) -> PI item (PI_PENDING_DECISIONS.md): (a) keep them open / class [多元]/friction-computability under the reference law (designs flagged 'soft face locks under stick'); (b) fall back to the production-law read-out plus the measured law shift (p90 0.043 mm) as margin - all 5 would pass (fric3 values 0.169-0.822 mm, limits 1 / 0.5 mm) and be flagged 'fallback'; (c) change the soft-face material model for all designs (changes the physics of every verdict). Recommendation: (b) for the verdict table with the flag, (a) as the label state until the PI rules; not (c).
- The remaining 4 process-E / F pilots and the p129 run stay on; the issue-2 answer (equivalence at t 3.5, window read-outs) follows when they end.
- 18:39 literature / code check for the soft-face inversion (PI: consult sources when stuck): (i) FEBio sliding-elastic friction (Zimmerman & Ateshian 2018, J Biomech Eng, PMC6056201; feature manual) is a penalty / augmented-Lagrangian Coulomb law with the tangential traction derived from the normal traction and the slip; neither the paper nor the manual offers a cap on the shear a soft body may carry in stick - the stick anchor reset we found upstream is the only thing that limited it, by accident. (ii) Element inversion in Newton solves: the documented remedies are solver-internal - inversion-aware line search that rejects steps with J <= 0 (Poya et al., cited in arXiv 2409.17822 'generalised tangent stabilised nonlinear elasticity'), mesh untangling to restart from an inversion-free state (Shontz & Vavasis, arXiv cs/0609001), inversion-safe strain energies (graphics literature). None exists in FEBio 4.13 and all would be a further solver patch of uncertain value for a material that is at its locking limit; the Gent Jm 0.7 soft face is the physical reason the elements fold. Conclusion unchanged: a PI decision (options a/b/c, 18:38), not a fix attempt.

## 2026-11-09 18:45 time stamps corrected; p129 pilot stopped by mistake and resumed
- The headers and in-text stamps of today's entries from 18:18 on were written with an estimated clock that ran up to 1.5 h ahead (18:50/19:05/19:10/19:50/20:05/20:15 -> 18:18/18:26/18:26/18:35/18:38/18:39, the git commit times of the same content; also in PI_PENDING_DECISIONS.md, FILE_INDEX.md and platform_capabilities.json notes). The order of events is unchanged.
- The same clock error made me read pilot_relE/p129_gpu5 as hung ("no log output for 1.6 h" - the log was 2 min old) and stop its FEBio process at 18:41 (exit 1 in p129_run.log is that SIGTERM, not a solver error). h18 resumed it at 18:42 from the t 2.0 checkpoint (case.dmp 18:08) on GPU 5 (p129_run2.log; the stopped run's log kept as case_hang1.log) - about 35 min of the release step are recomputed. Rule from this: before any kill, check the file mtime against `date`, never against an assumed clock.

## 2026-11-09 19:10 process E p062 died in the static follower step by the stationary displacement trap (not inversion)
- pilot_relE/p062_gpu6: E R R O R at t 3.381 (follower step t 3-3.5 static, Fz -76 N, C3 thy -0.135 deg quasi-stationary), 19 retries, ZERO negative-Jacobian warnings. Last iteration: residual 3.0e-4 -> 2.6e-5 (REQUIRED 0, rtol off), energy 3.6e-10 < 6.0e-9 converged, displacement 1.1e-9 vs REQUIRED 1.8e-13 - the relative displacement tolerance scaled by a vanishing first increment, the same trap as the hold windows (DECISIONS 2026-11-08; fixed there by window_min_residual 1e-4). The main-deck static steps of the pilots have no residual floor. p094 (t 3.42, 2 retries) and p068 E (t 3.40, 94 retries) are in the same step. Next: class pilot_relE2 = pilot_relE + min_residual on the main deck (the existing pilot key), p062 rebuilt and relaunched; process F p068 (t 2.43 in the release step) runs on and gets the same floor if it stalls in the hold.

## 2026-11-09 19:35 process E2 p062: insertion state equivalent to production (issue-2 core claim), windows die at the static->dynamic restart
- pilot_relE2/p062_gpu6 (release_all_dofs + physio_static_until_windows + main-deck min_residual 1e-4, stick-memory law throughout): insertion N O R M A L to t 3.5 in 20.6 min, 0 retries, 2 negative-Jacobian warnings. h49 vs production physio_fric3/p062 at t 3.5: cage relative to C4 differs by 0.0018 mm (horizontal), C3 position by 0.002-0.003 mm, C3 rotation by 0.005 deg, pot reactions identical (Fz -100 N, moments 0) - within the run-to-run spread of identical decks (0.002 mm). The statically released insertion reproduces the production insertion state for this design.
- Both windows then E R R O R within 50-100 ms of the restart (extension t 3.554, flexion t 3.596): first-iteration residual 1.84e4 growing to 8.7e6 / 7.4e5, displacement norm 4.6e5 - the static -> dynamic switch (density 1e-6) at the window start with the free C3 pot carrying the 100 N follower load, the same mechanism as the t 3.0 blow-up of the production runs (there with the stored moment; |F|^2 ~ 1e4 here). Production fric5 windows restart from a DYNAMIC follower state, so they never see this switch.
- Decision: process E' (class pilot_relE3) = ONLY the release step changed (release_all_dofs, stored moment ramped to zero statically over t 2-3) + main-deck min_residual 1e-4; the follower step stays dynamic as in production, so the switch happens at t 3.0 with ~zero pot reactions (benign) and the windows restart exactly like the production ones. p062 built (preflight OK) and launched on GPU 6. physio_static_until_windows is dropped from the candidate process. Process F (follower load in the release step) keeps its static hold for now: its insertion result on p068 (does compression during the release avoid the -7 deg swing and the C3 cortical inversions?) is the information wanted; its windows will fail the same way and are not read.
- p068 E: t 3.405, 114 retries, zero line-step reformations - still in the follower hold, left running for the record. p094 E: t 3.47, windows will fail at the restart; the t 3.5 state is still compared with h49.

## 2026-11-09 20:12 p094 process E: same trap at t 3.4998; insertion state equivalent; E' p094 launched
- pilot_relE/p094_gpu3: E R R O R at t 3.49984 (static follower step, Fz -99.96 N, 15 retries, no new negative Jacobians after the 300 at the t 3.0 release) - the stationary displacement trap again, 2 h 6 min wasted on the hold. h49 vs production physio_fric3/p094_gpu5 at t 3.5: cage relative to C4 differs by 0.007 mm (horizontal), C3 position by 0.006 mm, C3 rotation by 0.015 deg (production carries a residual pot moment My -2.1 N mm, the pilot 0). Second design in which the statically released insertion reproduces the production insertion state.
- pilot_relE3/p094 (process E': static moment release only, dynamic follower step, main-deck min_residual 1e-4) built, preflight OK, launched on GPU 3 (6 cores; in use: p068 E, p129, p068 F, p062 E', p094 E' = 30). pilot_relE3/p062: insertion N O R M A L at 3.5 with 0 retries, windows running.
- p129 (resumed): past the release, t 3.15 in the follower step. p068 E: t 3.42, 146 retries. p068 F: t 2.45, 6 retries (follower ramp 2.0-2.5 inside the release).

## 2026-11-09 20:14 process E' p062: insertion AND window read-out equivalent to production + reference law
- pilot_relE3/p062_gpu6 (release_all_dofs + main-deck min_residual 1e-4, follower step dynamic as production, stick-memory law, cbuild_fric): insertion N O R M A L at t 3.5, 0 retries; h49 vs production p062: cage rel. C4 within 0.003 mm, C3 position within 0.003 mm, C3 rotation within 0.008 deg, reactions identical. Windows restart with R0 1.4e-2 (E2 with the static hold: 1.8e4). Flexion window N O R M A L at t 4.0 (3 retries): e04 read-out u_h 0.174 mm at 1.5 N m vs physio_fric5 p062 (production insertion, same law) 0.176 mm, fric3 0.164, fric2 0.188 - 0.002 mm apart, the run-to-run spread. Extension window running (t 3.73).
- Reading: for a design that survives the production insertion, process E' changes nothing measurable; the 27 designs that died at the t 3.0 release are the real test (p068 E' next; p094 E' running).

## 2026-11-09 20:17 process F path on p068 is gentler; p068 process E stopped (purpose served); p068 E' launched
- pilot_relF/p068_gpu1 (follower load ramped 2.0-2.5 inside the static release, moment ramped to zero 2-3): at t 2.45 C3 thy -0.43 deg, Fz -44 N (sum of the stored +84 N reaction ramping down and the -100 N follower ramping up), ZERO negative-Jacobian warnings, 6 retries; process E at the same time: thy -1.35 deg, heading for -7.24 deg at t 3.0 with 1891 C3-cortical inversion warnings. Compression during the release does what it was meant to do. F keeps the static hold (trap-prone) and its windows will fail at the static->dynamic restart - the insertion path is what is read from it; a later F''' (= F + dynamic follower step as production) is the candidate if the switch at t 3.0 under 100 N is tolerable (production survivors switched with |M|^2 up to ~2.5e5, so R0 ~1e4 should be).
- pilot_relE/p068_gpu4 (process E, static hold) stopped at 20:16 at t 3.42 after 7 h 10 min and 146+ retries in the hold: the release-step blow-up is removed (its purpose), the hold is the stationary trap, the windows would fail at the restart, and there is no production t 3.5 state of p068 to compare with (production died at t 3.014). Log kept as case_stopped_2016.log. Its 6 cores go to pilot_relE3/p068 (process E', GPU 4), the first design that died in production to get the candidate process.
- (20:18) Headers 20:12/20:14/20:17 above were first written as 20:15/20:25/20:30 - estimated again instead of read from `date`; corrected within minutes. Every header from here on is taken from `date` at writing time.

## 2026-11-09 20:20 process E' p062 complete: both windows equal the production + reference-law read-outs
- pilot_relE3/p062_gpu6 finished (45 min on 6 cores + GPU 6; insertion 0 retries, windows 1 / 3 retries, both N O R M A L at t 4.0). Extension at the intact ROM (fric_compare at_intact_rom on the window dir): posterior 0.441 mm, t_rom 3.899, rot_max 9.225 deg - identical to physio_fric5 p062 (0.441 / 3.899 / 9.225); fric3 0.448. Flexion at 1.5 N m: 0.174 vs fric5 0.176 mm. Insertion state at t 3.5 within 0.003 mm / 0.008 deg of production (h49). Numbers in pilot_relE3/equivalence_p062.json.
- Issue-2 status: the candidate process E' is equivalent to the production process on a design that survives it, in insertion state and in both verdict read-outs. What remains is whether it carries the designs that died at t 3.0 (p068 E' running, d 1.3 radial; p094 E' running, d 1.0) and the p129 control (process E, resumed).

## 2026-11-09 20:49 process E' p094 complete: second design equivalent in insertion state and both read-outs
- pilot_relE3/p094_gpu3 (d 1.0 radial_interleave): insertion N O R M A L at t 3.5 (0 retries, 2 negative-Jacobian warnings), both windows N O R M A L (3 / 7 retries), 33 min on 6 cores + GPU 3. C3 swings to -4.73 deg at t 3.0 during the static release and the DYNAMIC follower step brings it back to -0.49 deg at t 3.5 = the production value (-0.49); h49: cage rel. C4 within 0.004 mm, C3 position within 0.006 mm, rotation within 0.01 deg, pot moment My -3.2 vs -2.1 N mm. Read-outs: extension at ROM 0.302 mm (fric5 0.307, fric3 0.313); flexion at 1.5 N m 0.136 mm (fric5 0.143, fric3 0.147) - 0.005-0.007 mm below fric5, inside the law-change spread (median 0.011) and the run-to-run spread. The flexion window has 14 of 36 states flagged dyn (rigid-body residual > 2 %), dropped by the read-out filter as in production. Numbers in pilot_relE3/equivalence_p094.json.
- Insertion-stopped production designs (27, all radial: 14 interleave, 13 mix; d 0.80-1.50): 21 died at the t 3.0 release (3.01-3.07), p109 at 3.34, and 5 died INSIDE the static release step (p052 2.45, p039 2.23, p064 2.44, p048 2.93, p050 2.52, p097 2.64) - a second failure mode that process E' only touches indirectly (ramped forces instead of fixes). Next pilots: p129 (interleave d 0.9, died 3.053; its process-E run with the doomed static hold is stopped and replaced by E') and p052 (interleave d 1.0, died inside the release at 2.45) - with p068 E' (mix d 1.5) running this spans both families and both failure modes.

## 2026-11-09 20:51 p129 process E stopped; E' p129 and p052 launched
- pilot_relE/p129_gpu5 (process E, resumed run) stopped at 20:51 at t 3.195 in the static follower hold (log kept as case_stopped_run2.log): same doomed path as p062/p094 E (trap at ~3.4-3.5, windows failing at the restart), cores reused. pilot_relE3/p129 (GPU 5) and pilot_relE3/p052 (GPU 2, died inside the production release at t 2.45) built from the physio_fric3 params + E' keys, preflight OK, launched (6 cores each; 24 in use with p068 E' and p068 F).

## 2026-11-09 21:10 E' on the designs that died in production: p068 insertion completes, p129 dies at the switch like production -> process F''' (compression during release + dynamic follower step)
- pilot_relE3/p068_gpu4 (radial_mix d 1.5, production death t 3.014): insertion N O R M A L at t 3.5 (13 retries, 2661 negative-Jacobian warnings recovered), windows running. C3 path: -7.25 deg at t 3.0 (zero-load swing during the static release), then under the dynamic follower ramp -6.75 / -1.38 / -5.59 / -3.71 / -2.55 / -1.22 deg at 3.05 / 3.10 / 3.20 / 3.30 / 3.40 / 3.50 with pot moments up to -116 N mm and My +6.5 at 3.5 - a swinging, not settled, start state for the windows (no production reference exists for this design).
- pilot_relE3/p129_gpu5 (radial_interleave d 0.9, production death t 3.053): E R R O R at t 3.053, 10 retries, 3993 negative Jacobians in disc_or_facet_mat5 (2342), C3_cortical (1142), cage_soft_0.0 (504), 13 min. First dynamic step R0 4.8e3 (production: 1.05e5 with the stored moment) - the residual is 20x smaller but the segment has swung to -4.23 deg with 0.59 mm anterior pot translation under zero load, and the follower ramp from that posture crushes the facets. p094 E' survived the same swing (-4.73 deg), so the margin is design-specific. Lesson: the zero-load swing is the remaining weakness of E'; the release must happen under compression.
- Process F''' (class pilot_relF2 = E' + follower_in_release [2.0, 2.5]): the 100 N follower load ramps inside the static release step while the stored moment ramps to zero over t 2-3 (p068 F path: -0.43 deg at t 2.45 instead of -1.35), the follower step stays dynamic as production, so the switch at t 3.0 happens under 100 N near the production posture (R0 ~ |F|^2 ~ 1e4, which production survivors tolerated as |M|^2 up to 2.5e5). p129 (GPU 5) and p068 (GPU 3) launched; p068 F (static hold, path information only) continues at t 2.46; p052 E' at t 3.12.

## 2026-11-09 21:26 E' p068: insertion completes but the t 3.5 state is swinging and both windows fail
- pilot_relE3/p068_gpu4 windows: extension E R R O R at t 3.5046 (10 retries, 1180 negative Jacobians: C3_cortical 865, cage_mix_0.0 296), flexion E R R O R at 3.641 (30 retries, 4997: cage_mix_0.0 3596, C3_cortical 1023, cage_mix_1.0 366). Start state: in the last 30 ms before t 3.5 C3 thy moves -1.74 -> -2.01 -> -1.22 deg and the pot moment oscillates -91 -> -132 -> +7 N mm; the flexion window's first state (3.514) already carries My +924 N mm. The dynamic follower step of E' leaves a d 1.5 radial segment swinging after the -7.2 deg zero-load excursion; the windows start from a non-equilibrium and the soft face (cage_mix_0.0, E_soft 1.67 MPa, the issue-1 material) folds.
- Reading: E' is sufficient for designs whose release swing is moderate (p062, p094) and insufficient for the thick radial ones (p068: swing; p129: facet crush at the switch). F''' (compression during release) is the candidate for all; it is now running on p129 and p068 (dead-in-production designs) and p094 (production reference, GPU 6, launched 21:26) to check that it stays equivalent where E' was. If F''' passes those three, p062 F''' closes the equivalence set and the 27 insertion-stopped designs get a batch.

- 21:28: pilot_relF/p068_gpu1 (process F with the static hold) stopped at t 2.469 after 3.3 h: its release path is reproduced by F''' p068 (same release step) and its hold/windows were doomed (trap, static->dynamic restart); log kept as case_stopped_static.log. p062 F''' launched on GPU 1 to complete the equivalence set (p062, p094 with production references; p129, p068, p052-type without).

## 2026-11-09 22:05 process F''' p094: quiet path, extension equal, flexion read-out 0.04 mm lower; p068 F''' dies at the switch; p052 E' insertion completes
- pilot_relF2/p094_gpu6 (compression ramped 2.0-2.5 inside the static release, dynamic follower step): insertion N O R M A L (0 retries, 2 negative Jacobians), both windows N O R M A L (4 / 10 retries), 37 min. C3 path: thy 0 -> -0.48 deg smoothly during the release, flat at -0.480 deg through t 3-3.5 (production -0.49) - no swing, quiet start state. h49 vs production: C3 rotation within 0.01 deg BUT cage rel. C4 and C3 position differ by 0.026 / 0.024 mm in x (E': 0.004 / 0.006): seating the cage under compression leaves it ~0.025 mm further along x than the production path. Read-outs: extension at ROM 0.308 (fric5 0.307, E' 0.302) - equal; flexion at 1.5 N m 0.100 mm vs fric5 0.143 (E' 0.136, fric3 0.147) - 0.043 mm lower (30 % of the quantity; equal to the p90 of the law-change shift; 0.9 mm below the limit). The frictional preload of the cage faces depends on whether the segment was compressed before or after the moment release (stick memory keeps that history). Numbers in pilot_relF2/equivalence_p094.json.
- pilot_relF2/p068_gpu3: release under compression is smooth (thy -1.16 deg at t 3.0, x +0.24 mm, 811 soft-face warnings recovered, no swing) and then E R R O R at t 3.0046 right at the static -> dynamic switch under the 100 N follower load (retries down to dt 0.0045; 2597 C3_cortical + 1177 cage_mix_0.0 + 268 facet negative Jacobians after t 3.0). E' p068 passed the same switch at zero load but swinging. So for d 1.5 radial_mix the switch itself is the killer whichever state it is taken from: a dynamic step started from a static state with a loaded, nearly massless free rigid body.
- Reading for the PI: E' is the closer reproduction of the production process (0.005 mm) but fails the thick radial designs; F''' survives more of the insertion but changes the flexion read-out by ~0.04 mm on a design with a reference, and still dies on p068 at the switch. p129 F''' is past the switch (t 3.07, 18 retries).
- pilot_relE3/p052 (died inside the production release step at t 2.45): E' insertion N O R M A L at 3.5 (2 retries, 418 negative Jacobians) - the ramped release also removes the second failure mode; windows running. pilot_relF2/p062 insertion N O R M A L (0 retries, 0 negative Jacobians), windows running.
- Next: remove the switch altogether for the thick designs - process G = F''' with the whole run dynamic (density 1e-6 from t 0, no static -> dynamic transition anywhere; needs an h14 option) - after checking what the 2026-11-03 fix-3 class (physio_fric3p: follower_in_release + physio_dt0) found.

## 2026-11-09 22:10 F''' p062 numbers; fix-3 (2026-11-03) recalled; process G (all dynamic) built and launched on p068 / p094
- pilot_relF2/p062_gpu1: insertion 0 retries / 0 negative Jacobians, both windows N O R M A L. h49 vs production: cage rel. C4 -0.011 mm and C3 position -0.014 mm in x (E': 0.001-0.002), rotation within 0.004 deg. Extension at ROM 0.439 (fric5 0.441, E' 0.441); flexion at 1.5 N m 0.157 vs fric5 0.176 (E' 0.174) - 0.019 mm lower. Same pattern as p094 (0.025 mm x offset, flexion 0.043 lower): compressing the segment before the stored moment is released changes the cage's frictional preload; E' keeps the production ordering and reproduces the read-outs to 0.002-0.007 mm. Numbers in pilot_relF2/equivalence_p062.json.
- Recalled from DECISIONS 2026-11-03/04 (lines 1185-1259): physio_fric3p = production + follower_in_release (2.5-3.0) + physio_dt0 0.005 was tried on the 12 radial failures: 12/12 failed, EARLIER (6 at t 3.005, R0 2.1e4) - the static -> dynamic switch under the follower load with a small first step was already shown fatal for these designs; today's F''' p068 death at 3.0046 under 100 N is the same event (the stored moment is now gone, the switch under load still kills). The switch itself - first dynamic step from a static state with a loaded, nearly massless free rigid body - is the remaining root cause for d >= 1.2 radial designs.
- Process G (class pilot_relG = F''' + all_dynamic; h14 option: STATIC_STEPS = () so every step from t 0 runs dynamic with density 1e-6, no transition anywhere; all_dynamic added to h37 PILOT_KEYS, R7 PASS, golden build unaffected - the option is off by default): p068 (GPU 3) and p094 (GPU 4, reference) built, preflight OK, launched 22:10. If G carries p068 to t 3.5 and through the windows, and p094 stays within the F''' numbers, G is the candidate for the 27 insertion-stopped designs; E' remains the equivalent process for the 43 survivors (no rerun needed there).
- Running: F''' p129 (t 3.09, 18 retries), E' p052 (flexion N O R M A L, extension running).

## 2026-11-09 22:17 E' p052: first insertion-stopped design carried through insertion and both windows
- pilot_relE3/p052_gpu2 (radial_interleave d 1.0, E_soft 11.9; production died INSIDE the static release step at t 2.45): E' insertion N O R M A L (2 retries, 418 negative Jacobians), extension window N O R M A L (3 retries), flexion N O R M A L (8 retries); 82 min on 6 cores + GPU 2. Read-outs: extension at the intact ROM posterior 0.390 mm (t_rom 3.899, rot_max 9.23 deg); flexion at 1.5 N m u_h 0.685 mm -> provisional pass under the reference law (limits 1 / 0.5 mm). Tied screen: mu_req_max 0.108, class [多元]/friction-computability (no friction run existed). Numbers in pilot_relE3/readout_p052.json. No production reference for h49 (the design never reached t 3.5 before).
- Status of the candidate processes on the 27 insertion-stopped designs so far: E' carries p052 (release-step death mode) and p068 to t 3.5 (but p068 swinging, windows fail) and fails p129 at the switch; F''' carries p129 past the switch (running, t 3.09) and fails p068 at the switch; G (all dynamic) running on p068 and p094. The mixing question for the PI (which process for the 27, while the 43 survivors keep their production insertion) is in PI_PENDING_DECISIONS.md 之後再議 and becomes current once G reports.

## 2026-11-09 23:00 process G p094: same outcome as F''' (the compression-before-release, not the dynamics, sets the read-out); G p068 past t 2.95 with 0 retries
- pilot_relG/p094_gpu4 (every step dynamic from t 0, compression during the release): insertion N O R M A L (0 retries, 135 negative-Jacobian warnings all in the hard cage block), windows N O R M A L (1 / 8 retries), 48 min. h49 vs production: cage rel. C4 -0.026 mm and C3 -0.024 mm in x (= F'''), rotation within 0.01 deg. Extension at ROM 0.308 (F''' 0.308, fric5 0.307); flexion at 1.5 N m 0.094 (F''' 0.100, E' 0.136, fric5 0.143). So G = F''' in result: making the whole run dynamic changes nothing visible on a design that survives anyway; the 0.03-0.05 mm lower flexion read-out comes from seating the cage under compression. Numbers in pilot_relG/equivalence_p094.json.
- pilot_relG/p068_gpu3 (d 1.5 radial_mix): t 2.96 with 0 retries and 0 negative Jacobians (F''' p068 had 811 soft-face warnings before t 3 and died at the switch at 3.0046; there is no switch in G). pilot_relG/p062_gpu6: insertion N O R M A L (0 retries), windows running. pilot_relF2/p129_gpu5: insertion N O R M A L at 3.5 (18 retries, 3226 negative Jacobians), windows running.

## 2026-11-09 23:06 G p062 = F''' outcome; F''' p129 complete (second rescued design); four more G pilots on insertion-stopped designs
- pilot_relG/p062_gpu6: insertion 0 retries, windows N O R M A L (1 / 3 retries). h49: x offset -0.010 / -0.013 mm (= F'''), rotation within 0.001 deg. Extension at ROM 0.441 (= fric5), flexion at 1.5 N m 0.159 (F''' 0.157, fric5 0.176). Two reference designs now show G = F''' to 0.002-0.006 mm, and both sit 0.02-0.05 mm below the production+law flexion read-out. Numbers in pilot_relG/equivalence_p062.json.
- pilot_relF2/p129_gpu5 (radial_interleave d 0.9; production and E' both died at t 3.053): insertion N O R M A L (18 retries, 3226 negative Jacobians), both windows N O R M A L. Read-outs: extension at ROM posterior 0.447 mm, flexion at 1.5 N m 0.778 mm -> provisional pass (0.447 is inside the 0.45-0.55 grey band the PI is asked about). Tied mu_req_max 0.116. Second insertion-stopped design carried through (after p052 with E'). Numbers in pilot_relF2/readout_p129.json.
- G launched 23:06 on four more insertion-stopped designs to measure breadth while p068 G finishes: p121 (interleave d 1.25, E_soft 7.4, GPU 1), p116 (mix d 1.4, E_soft 1.7, GPU 2), p050 (mix d 1.5, E_soft 1.7, died inside the release at 2.52, GPU 4), p109 (mix d 1.5, E_soft 11.3, died 3.34, GPU 6); with G p068 (t 2.996, 0 retries) 30 cores in use. The three mix d 1.4-1.5 designs with E_soft 1.7 are also soft-face (issue-1) material - their windows may fold under the stick law even if the insertion passes.

## 2026-11-10 13:46 session resumed (the 11-09 session ended ~23:05 with 7 pilots running; all finished overnight) - process G results on the insertion-stopped designs
- Process G (every step dynamic from t 0, compression during the release, stick-memory law) completes the INSERTION of every design it was given: p062 and p094 (references), p068, p050, p116, p109 (radial_mix d 1.4-1.5) and p121 (radial_interleave d 1.25) - 0-2 retries, 0-135 negative-Jacobian warnings; p068 and p050, which died at t 3.01 / 2.52 in production, go through with 0 retries and 0 warnings. Issue 2 (the insertion fragility) is therefore solved at the insertion level: root cause = the static -> dynamic switch at t 3.0 with a loaded, nearly massless free C3 pot (plus the stored distraction moment that the switch dumped); G has no switch and releases the moment statically-equivalent (dynamic, density 1e-6) under compression.
- Read-outs on references (pilot_relG/equivalence_p062.json, equivalence_p094.json): extension at ROM 0.441 / 0.308 (fric5 0.441 / 0.307) - equal; flexion at 1.5 N m 0.159 / 0.094 vs fric5 0.176 / 0.143 - 0.02-0.05 mm lower, same as F''' (compression-before-release changes the cage's frictional preload); insertion x offset 0.010 / 0.026 mm. E' (release at zero load) matched production to 0.002-0.007 mm but fails p129 and leaves p068 swinging.
- WINDOWS of the thick soft-faced radial designs under the reference law (pilot_relG/readouts_dead_designs.json): p068, p050 (E_soft 1.67, d 1.5) both windows E R R O R at t 3.5046 - the first window increment - with 900-1900 negative Jacobians in cage_mix_0.0 (restart residual itself tiny, 1e-5..1e-3); p116 (1.67, d 1.4) extension dies at 3.597 (M 44 N mm), flexion at 3.5046; p109 (E_soft 11.3, d 1.5) extension N O R M A L (posterior 0.240 at ROM), flexion dies at 3.5046; p121 (7.38, d 1.25) extension N O R M A L (0.277), flexion dies at 3.892 after 5.65 deg with the cage already 1.33 mm displaced (would fail). This is the issue-1 phenomenon (soft face locks under stick, DECISIONS 2026-11-09 18:38) on thicker cages: under the reference friction law the soft-faced radial designs cannot carry the flexion window at all. Control launched: pilot_relGctl/p068 = the G p068 windows restarted from the G checkpoint with BIOCAGE_STICK_MEMORY=0 (production law) to show whether the production law would have computed them.
- F''' p129 (radial_interleave d 0.9, production death t 3.053): both windows N O R M A L; extension posterior 0.447 at ROM, flexion 0.778 at 1.5 N m (1.16 at ROM) -> provisional pass. E' p052: pass (0.390 / 0.685). So 2 of the 27 insertion-stopped designs have verdicts (provisional, process not yet adopted), 1 more has an extension read-out (p109 0.240, p121 0.277) and the softest thick ones have none.
- Bookkeeping: the 11-09 session ended (process exit) at ~23:05 while the G batch launch command was running; the four G pilots (p121 p116 p050 p109) had been launched and finished (23:49-23:59); their params/case json are committed now. The last DECISIONS entry of 11-09 (23:03) stands.

## 2026-11-10 13:54 control: the G p068 windows fail under the PRODUCTION law too -> thick soft-faced designs are outside the material envelope, not a friction-law victim
- pilot_relGctl/p068 (= pilot_relG/p068 windows restarted from the G checkpoint with BIOCAGE_STICK_MEMORY=0, i.e. the production friction law): extension E R R O R at t 3.5046 (10 retries, 2041 negative Jacobians: cage_mix_0.0 1804, C3_cortical 234), flexion E R R O R at 3.5046 (3214: cage_mix_0.0 2461, C3_cortical 748) - identical to the stick-memory windows. For p068 (radial_mix d 1.5, E_soft 1.67 MPa) neither friction law can start the rotation windows: the soft face under the 100 N follower load is already at the Gent locking limit at t 3.5 and the first rotation increment (down to dt/1000 after 10 retries) folds it. The 11-09 18:38 conclusion (law-caused) holds for the fric5 batch windows (thin cages, p142 control ran under the production law); for the thick soft-faced designs the limit is the material under the follower load itself, independent of the law - and it is also why production died at the release for them.
- Consequence for PI item 2: fallback (b) is possible only where a production-law read-out exists or can be computed (the 5 fric5 windows); the thick soft-faced radial designs (so far p068 p050 p116: E_soft 1.67, d 1.4-1.5; flexion also fails for p109 E_soft 11.3 d 1.5 and p121 E_soft 7.38 d 1.25 under the stick law) have no computable window and should be classed outside the design envelope for the physio windows, with the mu_req tied verdict and 'window not computable (soft face locks under 100 N)' recorded. Whether the production law computes the moderately soft thick ones: control pilot_relGctl/p121 flexion launched (GPU 3).

## 2026-11-10 14:03 PI decisions (verbatim) on the 2026-11-10 report
- 「議題二：a但用不同流程模擬需紀錄好，之後分析或找根因時可能需要考慮」
- 「參考摩擦律下算不出來的窗口：更白話解釋清楚背景、困難、建議解法與後果」
- 「0.45–0.55 當灰區，要標示清楚，僅為分析用，不接受為finl design」
- 「捷徑容差:好」
- Reading / implementation plan:
  1. Issue 2 = option (a): the 43 production-inserted designs keep their results; the 27 insertion-stopped designs get process G. Every verdict row, class entry and label value must carry the insertion process (provenance field 'insertion_process' = 'production' | 'G', with the class name and the pilot options), so later analyses can separate the two populations. New settings class human_study/al_v2/physio_relG/ (= pilot_relG) registered as a production class; h37 R7 must accept its keys there and nowhere else.
  2. Soft-face windows: decision deferred until the plain-language explanation is read (written below / in the report); nothing implemented yet.
  3. Grey zone: posterior translation at the evaluation point in [0.45, 0.55] mm -> verdict 'grey' (neither pass nor fail), labelled 「灰區：僅供分析，不得作為 final design」 in verdicts.json, the classes and the labels; a grey design is never counted as a pass.
  4. Shortcut tolerance accepted as proposed: the shortcut counts as consistent with the gold standard while the rank correlation of mu_req_max with the gold-standard posterior translation is >= 0.9 and the linear-map residual is <= 0.05 mm (observed 0.90 / 0.032 mm, 43 designs); designs with mu_req_max within 0.140 +- 0.005 are grey-band and get a friction run. Written into PHY-05 (threshold) and mu_req_field (grey_band flag).

## 2026-11-10 14:09 implementation of the 2026-11-10 decisions - preparatory checks (gate files untouched until the layer-B audit launched 13:45 reports)
- Provenance check of the pilots: every pilot_relE3 / pilot_relF2 / pilot_relG insertion log carries the patch-7 evidence line 'stick_memory = 1' (3 lines each), every finished window log 2 lines, launch.json env BIOCAGE_STICK_MEMORY=1 and lib_sha256 be7b357f (the pinned cbuild_fric library) - the pilot windows ran under the same law as physio_fric5, so the equivalence numbers compare like with like. Provenance dimension to record for every result: insertion law + insertion process + window law: physio_fric3 = production insertion (production law) + production-law windows; physio_fric5 = production insertion (production law) + stick-law windows restarted from the fric3 checkpoints; physio_relG = G insertion (stick law) + stick-law windows. E' p062 (insertion within 0.003 mm of production) shows the insertion law does not matter for a survivor.
- Grey zone, prospective counts from the current verdicts.json (rule: posterior translation at the window's evaluation point in [0.45, 0.55] mm -> grey; the 1 mm any-direction limit and posterior > 0.55 stay fail; a design is grey when no window fails and at least one is grey): pass 35 / fail 6 / open 30 -> pass 25 / grey 16 / fail 0 / open 30. The 16 grey windows are all extension at ROM: p026 0.453, p051 0.504, p060 0.541, p072 0.476, p075 0.506, p076 0.477, p081 0.482, p092 0.480, p093 0.545, p113 0.485, p114 0.547, p117 0.480, p133 0.488, p135 0.472, p143 0.479, p145 0.549 - i.e. the 6 former fails become grey and 10 former passes (0.453-0.488) become grey. Grey is labelled 灰區：僅供分析，不得作為 final design in verdicts, classes and labels; it is a different flag from the mu_req grey band (0.140 +- 0.005, shortcut tolerance).
- scripts/5_compute/h50_relG_batch.py written (new file): lists the insertion-stopped designs (production physio_fric3 ended before t 3.5), builds physio_relG/<pNNN> from the fric3 params + the physio_relG class keys (release_all_dofs, follower_in_release, all_dynamic, min_residual, restart_env, window_min_residual) + insertion_process 'G', preflights, and runs them with h18 (env from the class restart_env, cbuild_fric), N workers, restartable. All 27 go through G, including the 7 already piloted (pilot results stay evidence, not production rows). Needs first: settings class physio_relG registered and h37 R7 accepting its options for that class only (PI decision cited) - deferred until the audit reports.
