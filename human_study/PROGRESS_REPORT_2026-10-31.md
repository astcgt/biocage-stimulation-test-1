# BIOCAGE human C3-C4 study: progress report for the next sessions (written 2026-10-31, ~10:40)

Read this first, then `DECISIONS.md` (authoritative, chronological; last ~250 lines = current state), then the EVO repo
(`/raid/jupyter-alz.ee09/projects/claude-work/biocage-evo`) docs listed in section 10. Every number here is reproducible from
the files named; when this report and DECISIONS.md disagree, DECISIONS.md wins.

## 1. What the project is, in one paragraph
A bioresorbable PLCL cage (hard 85:15 + compliant 50:50 phases, FDM-printed) for the human C3-C4 segment that gives
TEMPORARY support and fixation while a tissue-engineered disc (biodisc) matures (>= 16 weeks), then resorbs. Fixation must come
from shape and friction only (no screws, teeth, keels, bone shaping). Main goal: no dislocation in any direction, never toward
the cord. Two repositories: OLD (this one: validated FEBio model, cage builder, scheduler, 150-point active-learning screen of
human-designed families A/B) and EVO (biocage-evo: free-form evolutionary design with four adversarial AI roles, a GPU
solver under verification, and the post-processing methods e02-e05 that define the metrics).

## 2. Current protocol (physio_rot, independent windows "split2")
Per design: distract C3 by d (t 0-1), insert the cage (built shrunk 0.8, expands; t 1-2), release (t 2-3), 100 N follower load
(t 3-3.5, slow dynamic: density 1e-6 t/mm3, rho_inf 0), dump. Then six INDEPENDENT FEBio restarts from t 3.5 (flexion,
extension, left/right lateral bending, left/right axial rotation): C3 rotation prescribed through a generic rigid joint until
the reaction moment passes 1.5 N m; the window stops at the peak (t 4.0). A dynamic window that fails before its first
converged step is retried statically once. Post-processing per window: `e04_dislocation.py` (mu_squeeze = friction coefficient
needed, both tied faces, limit-surface LP; one_face_slip_bound_mm; target_reached; M_at_target) and `e05_compression.py`
(soft-PLCL compression, 99th percentile: sustained at t 3.5 <= 15 %, peak in a window <= 25 %, interim rule PI 2026-10-31).
Verdict: pass = all six windows reach 1.5 N m AND the compression rule holds; fail = compression rule violated; open =
otherwise. Scripts: h14 (build), h30 (split), h24 (preflight, mandatory), h19 (scheduler), h31 (run), h28 (build + queue per
design list with amplitude retargeting from a previous pass, now split-aware), EVO `ops/collect_split.py` (post-process every
window and AGGREGATE from all per-run files).

## 3. Results as of 10:40 (merged, `biocage-evo/results/method/split/*_merged.json`)
- 150 AL points = 133 unique designs (12 duplicate groups; GP acquisition clamped at bounds), 148 valid.
- Verdicts: **62 pass, 62 fail (compression), 24 open** (12 non-computable: inversion under the follower load; 12 with a
  window below 1.5 N m, second pass queued), 2 invalid.
- Fixation: every evaluable design needs mu_req < 0.17 (median worst-window 0.12); lateral bending governs in 67 of 68 fully
  evaluated designs; flexion ~0.02, extension ~0.01. Assumed available friction 0.3 (unmeasured). One-face slip bound <= 0.73 mm
  (p125), typically 0.1-0.3 mm (limit 1 mm; 0.5 mm posterior).
- Compression discriminates: sustained > 15 % in 62 designs; E_soft is the dominant factor (F3); 13 of 42 split2 designs invert
  at E_soft 1.5-4.2 MPa (9 of 15 below 2.5 MPa), mostly family B and "both" gradients (F5).
- Best passing designs by worst-window mu_req: p048 0.076 (A radial interleave, d 1.5, E_soft 1.67), p115, p084, p064, p109 ~0.08-0.09;
  radial gradient passes 45/65, axial 17/58, both 0/25; family B passes 0/24.
- Split protocol validated on p062: flexion/LB within 1 % of the sequential run; extension/AR slip bound 4-9 % higher, equal to
  the moment ratio at the first step past the target (sampling, not mechanics) (F4).
- Validation pilots (proc_val, 10-31 01:40): real-friction (mu 0.35) physio_rot completes all six windows on p062; posterior
  push-out p062 93 N peak (< 135 N guard); ISO 3 cycles complete only for p002.
- Validation of the model: 18/22 quantities within 10 % of Herron 2020, facet forces within 2 % (F1).
- Compute: 10,149 CPU core-h and 996 GPU-h since 10-20 (scheduler log; `resources_ledger.json` is stale since 10-20).
- Figures F1-F7 (PDF/PNG, Nature style) in `biocage-evo/paper/figures/` with captions in `figures.json`.

## 4. What happened on 2026-10-31 (chronological)
1. 05:54 /raid full (0 MB): 4 runs lost, watchdog state truncated. Deleted .dmp checkpoints of finished runs (252 GB) and invalid
   outputs; 721 GB free at 08:20; launches restored.
2. Split v1 (physrotS_) found INVALID: the restart LoadData redefinition did not act (FEBio redefines curves by controller
   index, not id); rotation was never applied except in flexion. Fix in h30 (curves moved in the insertion run; windows stop at
   the peak); h31 static retry added. Rebuilt as split2 (physrotT_, 38 designs; later + p041, p044, p098).
3. split2 validated on p062 (section 3) and accepted; batch finished 09:30 (29 of 42 insertions ok, 164 windows ok, 10 window
   failures, 13 insertion failures).
4. Post-processing audit: (a) `run_e04/e05` batches of earlier sessions only globbed `p*_gpu*` dirs, so 18 CPU-run cases
   (6 complete sequential runs among them) were never evaluated; computed now. (b) collect_split crashed on sustained = None;
   fixed. (c) collect_split now AGGREGATES verdicts from every per-run result file with an explicit invalid list and recorded
   sources instead of merging into hand-made intermediates; p049/p141 insertion state entered via
   `results/method/split/manual_overrides.json` (same design point; sustained 39.6 %, fail).
5. Multi-agent review workflow (29 agents) hit the account's 5-hour usage limit: 4 completed (evo-infrastructure audit, 3
   literature sweeps), 25 failed; the rest of the review was done inline by the main session. Rule for future sessions: keep
   agent fan-out small; do synthesis inline.
6. Queued at 10:20-10:30: second pass physrotU_ (al_v2/physio_rot_split3) for the 12 open designs with retargeted amplitudes
   (h28 now reads split runs: w_*/drive.txt); real-friction check physrotFr_ (al_v2/physio_fric: contact elastic mu 0.35,
   non-symmetric stiffness, dynamic, independent windows) on p062 (cross-check vs its sequential friction pilot), p048, p125,
   p060, p115, p109, p084. Settings classes added to current_settings.json. Expected end: second pass ~11:30-12:00, friction
   batch ~16:00-20:00 (sequential friction pilots took 2.1 and 4.0 h on a GPU).
7. Documents written (section 10): literature compilation, abstract/outline, risk analysis, ideas/architecture, designer
   kickoff plan and DRAFT designer prompt, publication figures, this report, a visual report for the PI (artifact).

## 5. Problems found (audit) and their status
| # | Problem | Status |
|---|---|---|
| 1 | Restart load-curve redefinition inert (split v1 invalid) | fixed (h30); lesson: validate every protocol change on all six windows |
| 2 | Post-processing skipped CPU-run case dirs (18) | fixed (aggregator enumerates all case dirs); add a per-batch completeness report |
| 3 | Verdict merge crashed on None sustained; verdict lists were hand-merged intermediates | fixed (aggregate from per-run files, sources recorded) |
| 4 | 150 AL points, 133 unique (GP acquisition clamps at bounds; 17 redundant runs) | open; report unique counts; fix acquisition before any new AL |
| 5 | resources_ledger.json stale since 10-20 | open; compute from scheduler.log (done in report_data) or automate |
| 6 | Disk guard missing in the scheduler (foreman edits constants by hand; one edit truncated h19 on the full disk) | open; proposal: scheduler_tuning.json + pause below 30 GB + nightly .dmp cleanup |
| 7 | Target-crossing sampling overshoot (4-13 % in M) biases slip bound / mu_req | open; implement interpolation to 1.5 N m in e04/e05 |
| 8 | 12 designs invert under the 100 N follower load (E_soft 1.5-4 MPa) in every solver mode | open; PI decision: compression failure vs non-computable; contact-skin law (h32) in progress |
| 9 | Compression rule interim; no PLCL compression-set / creep data; soft phase degrades in weeks | open; bench tests; degradation sweep |
| 10 | Hard-phase sustained-stress (creep rupture) not checked | open; e06 proposal |
| 11 | Posterior push-out 93 N < 135 N guard on p062 | open; re-derive the requirement; interlock designs |
| 12 | EVO: gpufe gate 2 fails 5/6 directions, no attempt since 10-28; VERIFICATION.md says "running" | open (audit A5-F01) |
| 13 | EVO: no designer prompt / constraints.py / design space / archive / engine; L2 copy of h14 stale; HOLD not enforced; 29 findings unanswered; GPU selection includes other users' GPUs | open (A5-F02..F14); plan in DESIGNER_KICKOFF.md |
| 14 | Agent usage limit: large fan-outs fail | rule: small fan-out, inline synthesis |

## 6. Open PI decisions (collected)
1. Verdict rule for designs that invert under the follower load (fail vs non-computable).
2. Confirm or replace the interim compression limits (15 % / 25 %) once bench data exist; verdict sensitivity to be reported.
3. Posterior push-out requirement 135 N: derivation (Moroney 1988) and whether 93 N on p062 is acceptable.
4. S8 subsidence number; S2 transient distraction (surgeon).
5. Fitness definition for the evolution (e04 mu_squeeze vs e03 per-face; Pareto?).
6. Start of the designer role and engine (2-3 weeks of integrator work; see DESIGNER_KICKOFF.md section 7).
7. Models of the 59- and 64-year-old subjects (download) for patient variability.
8. Folder rename of this repository (scheduled after daemons stop; absolute paths in several scripts).

## 7. Next steps (ordered) and time estimates
1. When physrotU_ ends (~12:00): `python ops/collect_split.py 4` (EVO) -> final verdicts; regenerate figures
   (`python paper/figures/make_figs.py`); update DECISIONS.md with the counts.
2. When physrotFr_ ends (~16:00-20:00): compare friction vs tied per window (e04 on friction runs gives slip directly from
   cage node motion; write a small comparison script); decide gate 4; add F8 (tied vs friction).
3. Implement exact-moment interpolation in e04/e05 (half a day); re-run post-processing (1-2 h of CPU).
4. Degradation sweep (E_soft x 0.5, 0.2, 0.1) on 5 passing designs (split2 settings; ~2 h compute).
5. Hard-phase sustained-stress check (e06) on existing states (half a day).
6. Scheduler: disk guard + tuning file + nightly .dmp cleanup + completeness report (half a day); benchmark 2-core GPU runs.
7. EVO: answer the 29 findings; schedule round 4 with the new digest; start W0-W3 of the kickoff plan.
8. Bench tests (lab): friction, compression set, creep rupture, hydrolysis (weeks); surgeon confirmation.
Completion estimates: in-silico screen of the human families with friction confirmation: ~1 week; degradation and UQ
sweeps: +1 week; evolutionary rounds 1-3: 3-5 weeks after the engine exists; paper draft for JOR Spine / J Biomech level:
~6-8 weeks; Nature-tier claim needs bench + cadaver data: 4-6 months.

## 8. Hardware and automation
Host: 256 cores but our cgroup quota is 32 cores; 7 A100 40 GB, ours 1-4 (0, 5, 6 other users); 1 TB RAM (cgroup ~137 GB);
/raid 14 TB shared, 721 GB free at 08:20 (keep > 50 GB). Throughput: a split2 design takes ~23 min on a GPU (4 cores + cuDSS),
~46 min on CPU; 8 concurrent 4-core runs saturate the quota -> ~8-10 designs/hour. Daemons (tmux): biocage_sched (h19),
biocage_watchdog (h23), biocage_preflight (h24 daemon), biocage_gpusamp, evo_daemon (+ foreman hourly), evo_keepalive;
`biocage-evo/ops/resume_all.sh` restarts them after a server restart. Proposed automation (see IDEAS_ARCHITECTURE.md section
4): tuning file instead of code edits, disk guard, post-processing inside h31, content-addressed results, hourly dashboard,
2-core GPU runs after a benchmark, GPU whitelist in EVO config.

## 9. Missing data (for the final report / paper)
PLCL-bone friction coefficient (assumed 0.3, sensitivity 0.2/0.45); PLCL 85:15 yield and creep rupture (wet 37 C); PLCL 50:50
compression set and relaxation; hydrolysis 0-26 weeks of printed grades; blend-gradient stiffness map (Duan 2021 sigmoid is an
estimate); surgeon confirmation of the 2 mm transient distraction; S8 subsidence number; 59/64-year-old models; push-out and ISO
results per design (only pilots); real-friction confirmation (queued); degradation-aware fixation; FEBio build patch set
committed; gate-2 rotation-controlled references for gpufe.

## 10. File index
OLD repo (this): `human_study/DECISIONS.md`; `human_study/al_v2/points.json` (150 points); run sets `al_v2/physio_rot*`,
`al_v2/physio_rot_split2` (current), `al_v2/physio_rot_split3` (second pass), `al_v2/physio_fric` (friction check),
`proc_val/` (validation pilots), `eqlaw/` (contact-skin prototype); `scripts/3_cage_case/h14, h30, h32`,
`scripts/5_compute/h19, h23, h24, h31`, `scripts/6_active_learning/h28, h29`; `human_study/queue/` (jobs), `scheduler.log`.
EVO repo: `methods/e03_mu_req.py, e04_dislocation.py, e05_compression.py`; `ops/collect_split.py` (aggregator);
`results/method/split/{best_by_design_merged, comp_by_design_merged, verdict_lists_merged}.json`, `manual_overrides.json`;
`paper/LITERATURE.md` (5 topics, ~130 references with verification flags), `paper/ABSTRACT_OUTLINE.md`,
`paper/figures/make_figs.py` + F1-F7; `docs/RISKS.md`, `docs/IDEAS_ARCHITECTURE.md`, `docs/DESIGNER_KICKOFF.md`,
`roles/prompts/designer.md` (DRAFT); audit of the evo infrastructure (14 findings) summarised in RISKS.md B5/E1-E4 and
DESIGNER_KICKOFF.md; `work/agents/foreman/report_*.md` (hourly ops reports).

## 11. How to resume
```bash
cd "/raid/jupyter-alz.ee09/projects/claude-work/biocage stimulation test 1"
tmux ls; tail -20 human_study/scheduler.log; ls human_study/queue/*.job | wc -l; df -h /raid
cd /raid/jupyter-alz.ee09/projects/claude-work/biocage-evo && python ops/collect_split.py 4 && python paper/figures/make_figs.py
```
Rules that still apply: h24 preflight before any FEBio run (h28 does it); commits authored by austonliuyi only, no Claude
trailer; reply to the PI in Traditional Chinese; do not homogenise the cage interior; validation of the simulation environment
before production batches; ask the PI before assuming an undecided parameter.

## Addendum 11:40: second pass finished
- physrotU_ (al_v2/physio_rot_split3, 12 designs, retargeted amplitudes): all 12 insertions and 72 windows ended normally
  (11:32). collect_split now scans split2 AND split3 (file tag `<set>__<design dir>__<window>` for sets after split2;
  ORDER prefers split3).
- Merged verdicts now **68 pass, 63 fail, 17 open** (12 non-computable + 5 still below 1.5 N m in one or more directions:
  p036, p093, p113 extension at 1427-1479 N mm; p082 AR_left 1487; p051 LB/AR 856-981). p068 p100 p101 p112 p117 became
  pass; p003 and p015 became fail (their evaluated states from split3 exceed the compression rule). Figures F1-F7 and the
  PI report regenerated. Next: a third pass for the 5 (amplitude x 1.3-1.5; check why p051's moment barely rose).

## Addendum 12:35: third pass finished; screen of the human families complete
- Second-pass bug: for designs whose previous run was a split run, h28 rot_retarget visited the never-run build dir first
  and kept the amplitudes; fixed (skip dirs without window drive data). Third pass physrotV_ (al_v2/physio_rot_split4):
  p036 p051 p082 p093 p113 all six windows reached 1.5 N m.
- Merged verdicts now **73 pass, 63 fail, 12 open**; the 12 open are exactly the follower-load inversion cases (verdict rule
  pending PI). Every computable design has six evaluated directions. Figures and the PI report (version 3) regenerated.
- Still running: the real-friction check physrotFr_ (7 designs); compare with `biocage-evo/ops/fric_compare.py` when done.
