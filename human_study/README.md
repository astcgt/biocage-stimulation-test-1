# human_study/ - human C3-C4 BIOCAGE study (data and decisions)

**Start here:** `DECISIONS.md` - every agreed parameter, method choice and result summary, in the order they were made
(Q-numbers = questions answered by the PI). `status.json` - progress per study step.

Large run outputs (`.xplt`, `.feb`, `.log`, `.dmp`, node `.txt`, `.npz`) stay on the compute server and are not in git;
each case folder keeps its small `summary.json` / `case.json` / `resources.json`.

## Folders

| Folder | Content |
|---|---|
| `validation/` | Herron 2020 C0-C7 validation: `runs/` (one folder per load case), `results/` (ROM / facet-force comparison, figures), digitised reference data. |
| `fsu/` | C3-C4 functional spinal unit: `C34_fsu_intact.*`, `C34_fsu_refined.*` (refined endplates), FSU-vs-full-spine checks (`*_vs_full.json`), `runs_*` (1.5 N m cases), `bench/` (thread benchmarks), `buggy_v1/` (superseded refined mesh, kept for the record). |
| `remesh/` | Refined C3 / C4 bone meshes from h16 (`C3_h0.5.npz` = 0.5 mm endplate, also 1.0 / 0.25 mm). |
| `cage_test/` | Development cases of the cage pipeline (design A / B), see naming below. `params_*.json` are the inputs to h14. |
| `meshconv/` | Mesh-convergence cases (endplate 1.0 / 0.5 / 0.25 mm, cage Z 0.1 mm, ...). |
| `verify_patch/`, `verify_patch3/` | Re-runs of validated models with the patched FEBio build (identical-result checks). |
| `queue/` | Scheduler (h19) job files: `*.job` waiting, `running/`, `done/`. |

Other files: `frame_c3c4.json` / `icr_c3c4.*` (loading frame, ICR), `resources_ledger.json` (cumulative compute use),
`gpu_samples.csv` (GPU idle detection), `scheduler.log`.

## Case folder names

`case_<design>_<test>_<variant>[_gpuN]`, e.g. `case_A_iso_tied2_gpu1`:

| Part | Meaning |
|---|---|
| `A` / `B` | design A (contoured to the endplates, no pad) / design B (planar between the uncinates + 0.6 mm soft pad) |
| `compress`, `iso`, `push_ant`, `push_post` | test: axial compression (capacity), ISO 18192-1 motion (slip), push-out driving the cage anteriorly / posteriorly |
| variant | what was changed in that run (see the matching `params_*.json` and `DECISIONS.md`): e.g. `ref` refined bone, `g10` global contact penalty 10, `u` uncoupled (three-field) cage, `gent` Gent cage material, `tied` / `tied2` bonded screening interface, `n49` Poisson's ratio 0.49 test, `p30`/`pen3` penalty variants, `dt` smaller time steps, `fless` frictionless |
| `_gpuN` | the copy that ran on GPU N (h18); without it the case ran on CPU (h06) |

Current screening setup (DECISIONS Q45-Q52): Gent cage, bonded cage-endplate interface from release (`contact_type: tied`),
friction demand / tipping in post-processing, ISO one cycle per level - e.g. `case_A_iso_tied2`, `case_B_iso_tied2`.
