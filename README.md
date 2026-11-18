# BIOCAGE simulation studies

**English** | [繁體中文](README.zh-TW.md)

Finite-element (FE) studies of the **BIOCAGE**: a bioresorbable PLCL (poly(L-lactide-co-ε-caprolactone)) cage for the human
cervical spine (C3-C4) that gives **temporary support and fixation while a tissue-engineered intervertebral disc
(biodisc) matures in the body**. It is neither a fusion cage nor a permanent motion-preserving disc.

> Status (2026-11-18): research in progress, unpublished. Numbers quoted here are intermediate results of the simulation
> platform; the authoritative, time-stamped values are in `human_study/` (see "Where to look"). Several platform
> capabilities are still graded "not yet qualified" (section 5); treat every verdict as a screening result, not a final one.

## 1. Why this exists (design rationale)

- **Clinical need.** Engineered discs integrate with the host in 6 weeks to 9 months (rat), 16 weeks (dog), 8 weeks (goat),
  but are far softer than a native disc when implanted. They need a temporary, resorbable support for at least 16 weeks.
- **Lab history.** FDM-printed PLA cages in minipigs (Lintz 2021, Cornell PhD dissertation, ch. 4) collapsed or fractured at
  two posterior sites caused by a posterior bony process (a geometry problem, not a material one); a uniform platen
  compression test had predicted success and was misleading; PLA softened at 37 °C. Slip-out of constructs was seen in the
  earlier canine study. Design consequences are applied here: realistic, moment-controlled loading instead of a platen
  test; posterior contact hot spots checked; one-piece integrity; wet 37 °C material properties.
- **Success means** (>= 16 weeks): the cage keeps the disc height, **does not slide out in any direction** (never toward the
  spinal cord), does not overload or sink into the endplates, and leaves connected space for the biodisc. The main
  endpoint is therefore **slip-out**, expressed as the friction coefficient the interface must provide (`mu_req`) and the
  interface shear it must carry, judged against a conservative real friction coefficient.
- **Evolving the design.** Human-drawn cage families (axial / radial gradients of hard PLCL 85:15 and soft PLCL 50:50,
  mixed or interleaved) were screened first. Because friction alone was marginal for most of them and the family is narrow,
  the design space is now opened up: a sister repository grows free-form cages (see section 4).

## 2. Repository layout

| Folder | Content |
|---|---|
| `human_study/` | **Current study.** Human C3-C4 model, implantation following disc-arthroplasty surgical practice (ACDR in the decision log; discectomy with the bony endplates preserved), loading, verdicts, quality assurance. `DECISIONS.md` lists every agreed parameter and design decision in order; `PLATFORM_CAPABILITIES.md` + `CAPABILITY_SCORECARD.md` grade the platform; `FILE_INDEX.md` maps every file. Large run outputs are not tracked. |
| `scripts/` | Pipeline, by stage: `common/`, `1_validation/`, `2_spinal_unit/`, `3_cage_case/`, `4_postprocess/`, `5_compute/`, `6_active_learning/`, `7_evo/gpufe/`, `8_audit/`. See `scripts/README.md`. |
| `febio_patches/` | Eight FEBio 4.13 source patches (NaN guard, line-search fix, delayed tie, restart fix, prestrain volume fix, frictional stick memory, ...), each with rationale and verification. |
| `febio_cudss/` | cuDSS (GPU) linear-solver plugin for FEBio 4.13. |
| `pig_study/` | **Earlier study** on a porcine C3-C4 model; kept for reference (`pig_study/README.md`). |

Third-party data (the Herron FEBio model, SimTK) is not redistributed.

## 3. Model and method

**Anatomy.** FEBio human cervical model, 26-year-old female (Herron et al. 2020, J Biomech): deformable C3/C4 bone, facet
contact, ligaments, fibre-reinforced annulus. A C3-C4 functional spinal unit (FSU) is cut out of the validated C0-C7 model;
the bone is re-meshed to 0.5 mm at the endplates, the cage is a 0.2 mm hex mesh.

**Validation first.** Before any cage was added the C0-C7 model was reproduced against Herron 2020 (moment-rotation, ROM
per level, C3-C4 facet force; 18 of 22 ROM values within 10 %, facet forces within 2 %), and the FSU was checked against the
C3-C4 level of the full spine (total ROM within about 1 %). The cage pipeline is only trusted where this chain holds; open
gaps are listed in section 5.

**Cage and material.** Gent hyperelastic PLCL with a local hard fraction (hard 85:15 / soft 50:50 blend, wet 37 °C
properties from the literature). The material layout stays **fully resolved element by element** (no homogenisation) so
that design detail matters in the simulation. Design genes: gradient direction, mix / interleave pattern, distraction
height (about 0.5-1.5 mm).

**Procedure.** Distract -> insert / seat -> release -> test. Screening uses a bonded (tied) cage-endplate interface and
derives the friction demand `mu_req` in post-processing; frictional contact is then run as the **verification** of the
shortcut, with the shortcut's conservatism measured rather than assumed.

**Physiological test (replaces the ISO 18192-1 wear test, 2026-10-23).** 100 N follower load plus pure moments of 1.5 N·m,
one direction at a time (flexion, extension, left/right lateral bending, left/right axial rotation), moment-controlled with
the upper vertebra free in rotation and in-plane translation. Endpoints per direction: ROM, net cage translation (slip),
friction demand, interface shear, completion. Rotations are applied as a relative prescribed rigid rotation ("route E"),
which removed an initial-pull-back artefact of the earlier joint-driven windows.

**Evaluation-state rules.** States are discarded when the time step is below 1e-4 (solver micro-steps), when the driven
rigid body's moment residual exceeds 2 % of target, or on an isolated moment spike; metrics are interpolated between the two
states bracketing 1.5 N·m.

**Solver engineering.** FEBio 4.13 with eight patches (`febio_patches/`), cuDSS GPU linear solver, restartable checkpoints,
a GPU scheduler with watchdog, and a pre-flight check (`h24_preflight.py`) that must pass before any run.

**Active learning.** `scripts/6_active_learning/`: Sobol start, Gaussian-process surrogates, robust batch selection.

## 4. Free-form evolution and shared data

- **Sister repository `biocage-evo`** (separate repository): designs are grown on a 0.2 mm voxel grid inside the disc space
  (void or PLCL with local hard fraction), encoded by compositional pattern-producing networks, short design programs
  evolved against an automatic evaluator, and direct growth/erosion moves; a MAP-Elites quality-diversity archive keeps
  unconventional designs alive. Four independent AI agent roles (designer, verifier, safety guard, red team) generate,
  check, guard and attack the work under explicit rules. A PyTorch + cuDSS GPU finite-element solver (`gpufe`) with
  FEBio-ported materials and Coulomb stick/slip contact is the fast level; FEBio frictional runs are the reference.
- **Second round (planned, 2026-11-18).** Surrogate-guided active learning on the simulated designs, a two-stage
  "novice then mentor" idea-generation step for the designer, and design-principle extraction from the results; the surrogate
  only chooses what to simulate next and never replaces a simulation verdict. Sampling weight: 80 % margin, 20 % biodisc
  space, with the constraint "living-disc space >= 50 %" kept.
- **Interface shear** (required shear at the cage-bone interface) is recorded as a flag and a ranking criterion; the 3 MPa
  level is a provisional marker until a PLCL-endplate bond-strength test exists.
- **Hugging Face.** Training tables and the surrogate validation are public at
  <https://huggingface.co/ast-atp/biocage_evo>: `data/mu_req_field.csv` (one row per simulated design, 149 rows: genes,
  family, `mu_req`, verdict class, required shear), `data/fric_verdicts.json` (frictional-window read-outs, 73 designs),
  `surrogate/` (geometric descriptors, Gaussian-process fit with leave-one-group-out and leave-one-family-out validation,
  90 % coverage checks). The surrogate meets the 90 % coverage check inside known design families for posterior translation
  and `mu_req`, not for interface shear, and it cannot predict a design family it has not seen.
- **Intermediate results (2026-11-17/18).** Of 73 designs with frictional-window verdicts: 53 pass, 16 grey zone (cage
  translation 0.45-0.55 mm against a 0.5 mm limit), 0 fail, 4 open. Radial-mix designs (28) are an excluded class; with the
  shear rule turned into a flag, the final-candidate list is 31 pass / 12 grey (counts are recomputed by the platform's
  quality-assurance checks and may change).

## 5. Quality assurance and honesty about limits

- **Capability labels.** The platform is graded per configuration (TIED shortcut, FRIC real friction, GPUFE fast solver) on
  physical realism (validation), numerical correctness (verification), speed, observation of only the target quantities, and
  diversity of designs; robustness of conclusions and support-period coverage are registered but deferred. The generated
  `human_study/CAPABILITY_SCORECARD.md` currently lists open items, e.g. cage-bone interface realism, mesh / time-step /
  contact convergence for real friction, and an unmeasured PLCL-endplate friction coefficient.
- **Checks.** `scripts/8_audit/h37_qa_check.py` (regression checks run before commits and reports) plus an independent audit of
  whether the code implements each recorded decision. The pre-commit hook refuses a commit when a check fails.
- **Not yet covered:** support-period creep and degradation to 26 weeks, bench measurements of PLCL friction and modulus,
  cadaver push-out validation, 59/64-year-old bone checks.

## 6. Literature (core references)

Full compilation with key numbers and candidate experiments: `paper/LITERATURE.md` in the `biocage-evo` repository (entries
marked UNVERIFIED there must be checked before citation).

- Herron MR, Brockmeyer DL, Dailey AT, Ellis BJ. FEBio cervical spine model (26-year-old female). *J Biomech* 2020.
- Maas SA, Ellis BJ, Ateshian GA, Weiss JA. FEBio: finite elements for biomechanics. *J Biomech Eng* 2012.
- Lintz M. PhD dissertation, Cornell University, 2021 (3D-printed PLA cages in the minipig; ch. 4).
- Anderst W et al. 2013, cervical instantaneous centre of rotation (loading frame).
- ISO 18192-1:2011 (cervical disc wear test; original screening protocol, kept for final candidates).
- Mouret J-B, Clune J. Illuminating search spaces by mapping elites (MAP-Elites), 2015.
- Cheney N, MacCurdy R, Clune J, Lipson H. Unshackling evolution: evolving soft robots with multiple materials and a
  powerful generative encoding (compositional pattern-producing networks), 2013.
- Romera-Paredes B et al. FunSearch, *Nature* 2023; AlphaEvolve (Google DeepMind, 2025): evolving programs against an
  automatic evaluator.
- ASME V&V 40 / FDA guidance on credibility of computational models; Erdemir A et al. 2020, reporting of model credibility.
- 2026 design-method literature consulted for the second round: D'Ambrosio, Albalak, Lehman, Stanley (arXiv 2611.11725,
  novice-then-mentor idea generation); Abstraction Agent (arXiv 2609.04303, design-principle extraction); active learning
  with FE simulation for structural optimisation (Zhang 2026, *Materials Genome Engineering Advances*); inverse-forward
  design network for porous spinal-fusion cage structures (*Struct Multidisc Optim* 69:146, 2026). Reinforcement learning was
  not adopted (thousands of evaluations at 1-3 GPU hours each).

## Where to look

- What was decided and why: `human_study/DECISIONS.md`; open items for the study lead: `human_study/PI_PENDING_DECISIONS.md`
- What each script does: `scripts/README.md`; what each data folder means: `human_study/README.md`
- Where every file is: `human_study/FILE_INDEX.md`
- Platform grading: `human_study/PLATFORM_CAPABILITIES.md`, `human_study/CAPABILITY_SCORECARD.md`
- FEBio modifications: `febio_patches/README.md`
- Free-form evolution: the `biocage-evo` repository; shared data: Hugging Face `ast-atp/biocage_evo`
