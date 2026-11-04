# QA status 2026-11-05 04:39 — WARN

h37_qa_check.py (layer A, deterministic). PASS = check held; FAIL = drift found, fix before any number is reported; WARN = information or an audit is due. Layer B (meaning of the decisions) = qa-auditor agent, register human_study/qa/QA_SPEC.json.

| check | status | detail |
|---|---|---|
| R1-case-dir | PASS | 128 friction rows; windows without finished log + xplt: 0 [] |
| R1-ambiguous | PASS | designs with several run dirs in one set: 0 [] |
| R2-gate4 | PASS | gate 4 passes without both usable windows: [] |
| R2-shear | PASS | interface-shear passes without both windows: [] |
| R2-merged | PASS | merged passes with a non-pass gate: []; without gate record: [] |
| R3-faces | PASS | skipped (--quick); 86 e07 window files |
| R5-counts | PASS | classes {'dislocation-friction': (17, 17), 'interface-shear': (14, 14), 'radial-mix': (28, 27), 'friction-computability': (14, 14)} (all / among tied passes); stale document counts: [] |
| R6-retracted | PASS | 4 retracted claims checked in 4 current documents; hits: [] |
| R7-pilot-keys | PASS | settings/h14: []; production cases scanned 722, with pilot options / extra keys: [] |
| R9-material-blocks | PASS | production: one FEBio block per cage material in 3 cases (p002:3, p036:4, p039:2); problems: [] |
| R11-constants | PASS | intact ROM constants: {'scripts/3_cage_case/h14_build_case.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907), 'scripts/6_active_learning/h28_physio_prerun.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907), '../biocage-evo/ops/fric_compare.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907)} |
| R12-file-index | PASS | 133 paths in FILE_INDEX.md; missing [] |
| R10-register | PASS | 88 register items; unmapped []; 不符 [] |
| R10-llm-audit-due | WARN | LLM audit required: last 2026-11-05 04:29; gate files changed since: ['scripts/5_compute/h24_preflight.py']; decision entries since: [] |
