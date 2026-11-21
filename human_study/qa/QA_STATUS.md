# QA status 2026-11-22 01:17 — WARN

h37_qa_check.py (layer A, deterministic). PASS = check held; FAIL = drift found, fix before any number is reported; WARN = information or an audit is due. Layer B (meaning of the decisions) = qa-auditor agent, register human_study/qa/QA_SPEC.json.

| check | status | detail |
|---|---|---|
| R1-case-dir | PASS | 533 friction rows; windows without finished log + xplt: 0 [] |
| R1-ambiguous | PASS | designs with several run dirs in one set: 0 [] |
| R2-gate4 | PASS | gate 4 passes without both usable windows: [] |
| R2-shear | PASS | interface-shear passes without both windows: [] |
| R2-merged | PASS | merged passes with a non-pass gate: []; without gate record: [] |
| R3-faces | PASS | 519 windows, 259 cases recounted; mismatches 0 [] |
| R4-insertion-state | PASS | insertion value state within 0.05 of t 3.5; violations 0 [] |
| R5-counts | PASS | classes {'friction-check-exceeded': (5, 5), 'interface-shear': (52, 51), 'radial-mix': (28, 27), 'friction-computability': (0, 0)} (all / among tied passes); stale document counts: [] |
| R6-retracted | PASS | 6 retracted claims checked in 4 current documents; hits: [] |
| R7-pilot-keys | PASS | settings/h14: []; production cases scanned 917, with pilot options / extra keys: [] |
| R8-golden-rebuild | PASS | p062 physio_fric3 rebuild md5 4f3208b5 vs recorded 4f3208b5 (12 s) |
| R9-material-blocks | PASS | golden rebuild: one FEBio block per cage material in 1 cases (tmpf3la_4mn:4); problems: [] |
| R9-material-blocks | PASS | production: one FEBio block per cage material in 4 cases (p002:3, p036:4, p039:2, p102:2); problems: [] |
| R11-constants | PASS | intact ROM constants: {'scripts/3_cage_case/h14_build_case.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907), 'scripts/6_active_learning/h28_physio_prerun.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907), '../biocage-evo/ops/fric_compare.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907)} |
| R12-file-index | PASS | 409 paths in FILE_INDEX.md; missing [] |
| R14-patch7-logs | PASS | production logs scanned for the patch-7 env switches and the FECore profile guard; hits: [] |
| R15-fric5-law | PASS | physio_fric5 class pinned, superseded sets clean; 86 finished window logs checked; problems: [] |
| R16-relG-law | PASS | physio_relG: class law = fric5 law; 28 finished run dirs checked (insertion + window evidence lines, launch env/lib, stderr); problems: [] |
| R17-relG-fallback | PASS | 17 physio_relG_pl cases, 24 finished windows checked; 2 fallback windows in the verdicts; problems: [] |
| R19-route-E | PASS | route-E classes: 141 cases, 264 finished windows checked (class = base + window_drive_mode, source run, params, deck hash, restart.feb no joint + relative Ry, evidence, lib/env, stderr); problems: [] |
| R20-replicate-agreement | WARN | sets ['physio_fric5r', 'physio_relGr', 'pilot_mu03rN', 'pilot_mu03GrN', 'pilot_mu03r', 'pilot_mu03Gr']: 9 deck groups, 29 windows with >= 2 computed replicates, 5 disagree (> 0.005 mm or mixed evaluation point), worst spread 0.012415672940065736 mm |
| R21-estimator-separation | PASS | usable windows without an existing run directory: 0 []; verdict programs that mention estimator outputs: [] |
| R23-estimator-validation | WARN | validation_2026-11-18.json: grouped True (nominal 0.9, 132 groups); input tables newer than the report: ['mu_req_field.csv', 'verdicts.json'] |
| R18-agent-prompts | PASS | .claude/agents vs human_study/agent_prompts: in sync |
| R10-register | PASS | 414 register items; unmapped []; 不符 [] |
| R10-llm-audit-due | WARN | LLM audit required: last 2026-11-21 20:56; gate files changed since: ['human_study/current_settings.json', '../biocage-evo/ops/fric_compare.py', '../biocage-evo/ops/e07_batch.py', '../biocage-evo/ops/collect_split.py']; decision entries since: ['2026-11-22', '2026-11-22'] |
