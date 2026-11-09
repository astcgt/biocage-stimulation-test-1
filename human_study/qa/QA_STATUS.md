# QA status 2026-11-09 11:41 — FAIL

h37_qa_check.py (layer A, deterministic). PASS = check held; FAIL = drift found, fix before any number is reported; WARN = information or an audit is due. Layer B (meaning of the decisions) = qa-auditor agent, register human_study/qa/QA_SPEC.json.

| check | status | detail |
|---|---|---|
| R1-case-dir | PASS | 128 friction rows; windows without finished log + xplt: 0 [] |
| R1-ambiguous | PASS | designs with several run dirs in one set: 0 [] |
| R2-gate4 | PASS | gate 4 passes without both usable windows: [] |
| R2-shear | PASS | interface-shear passes without both windows: [] |
| R2-merged | PASS | merged passes with a non-pass gate: []; without gate record: [] |
| R3-faces | PASS | 86 windows, 43 cases recounted; mismatches 0 [] |
| R4-insertion-state | PASS | insertion value state within 0.05 of t 3.5; violations 0 [] |
| R5-counts | PASS | classes {'friction-check-exceeded': (13, 13), 'interface-shear': (18, 18), 'radial-mix': (28, 27), 'friction-computability': (14, 14)} (all / among tied passes); stale document counts: [] |
| R6-retracted | PASS | 4 retracted claims checked in 4 current documents; hits: [] |
| R7-pilot-keys | PASS | settings/h14: []; production cases scanned 722, with pilot options / extra keys: [] |
| R8-golden-rebuild | PASS | p062 physio_fric3 rebuild md5 4f3208b5 vs recorded 4f3208b5 (12 s) |
| R9-material-blocks | PASS | golden rebuild: one FEBio block per cage material in 1 cases (tmp4_ib4n16:4); problems: [] |
| R9-material-blocks | PASS | production: one FEBio block per cage material in 3 cases (p002:3, p036:4, p039:2); problems: [] |
| R11-constants | PASS | intact ROM constants: {'scripts/3_cage_case/h14_build_case.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907), 'scripts/6_active_learning/h28_physio_prerun.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907), '../biocage-evo/ops/fric_compare.py': (0.1009, 0.1286, 0.0713, 0.0717, 0.0905, 0.0907)} |
| R12-file-index | PASS | 205 paths in FILE_INDEX.md; missing [] |
| R14-patch7-logs | PASS | production logs scanned for the patch-7 env switches and the FECore profile guard; hits: [] |
| R15-fric5-law | PASS | physio_fric5 class pinned, superseded sets clean; 0 finished window logs checked; problems: [] |
| R10-register | FAIL | 136 register items; unmapped []; 不符 ['D-20261107-7L', 'D-20261109-1b', 'D-20261109-2L', 'D-20261109-3', 'D-20261109-M1', 'D-20261109-L1'] |
| R10-llm-audit-due | PASS | LLM audit current: last 2026-11-09 11:37; gate files changed since: []; decision entries since: [] |
