# scripts/ - human C3-C4 BIOCAGE pipeline

Run every script from the **project root** (paths in the examples are relative to it). Scripts keep their `hNN_` prefix
because `human_study/DECISIONS.md` refers to them by number (e.g. "h14"). Each file starts with a docstring giving its
exact usage.

## Pipeline at a glance

```
1_validation   Herron C0-C7 model  ->  FEBio 4 conversion  ->  validation vs Herron 2020
2_spinal_unit  C3-C4 FSU cut out of C0-C7  ->  endplate mesh refinement (0.5 mm)  ->  FSU vs full-spine check
3_cage_case    cage hex mesh  ->  one FEBio case per (design, test)   [distract -> insert/seat -> release -> test]
4_postprocess  capacity endpoints, slip / friction demand, tipping  ->  summary.json in the case folder
5_compute      run cases on CPU / GPU, scheduler, checkpoints, monitoring
6_active_learning  design screening loop (Sobol start, GP surrogates, robust batch selection)
common         shared modules (geometry / frame, .xplt reader)
```

## common/ - shared modules

| File | Purpose |
|---|---|
| `cage_geom.py` | Endplate geometry of the C3-C4 unit in the disc mid-plane frame (X anterior, Y left, Z disc normal, origin = ICR); cage footprint and window. |
| `xplt.py` | Reader for FEBio `.xplt` plot files (states, element / face data, surfaces, domains). |

## 1_validation/ - full-spine model and validation

| File | Purpose | Main output |
|---|---|---|
| `h01_extract_febio.py` | Extract C3 / C4 bone surfaces and the C3-C4 disc from the Herron model. | `human bone/stl/*.stl` |
| `h02_view_bones.py` | Render the extracted bones and disc (sagittal / coronal / axial). | PNG |
| `h03_icr.py` | Locate the C3-C4 instantaneous centre of rotation (Anderst 2013). | `human_study/icr_c3c4.json/.png` |
| `h04_frame.py` | Disc mid-plane loading frame (ISO 18192-1 axes, origin at the ICR). | `human_study/frame_c3c4.json` |
| `h05_prepare_c0c7.py` | Convert the C0-C7 model (FEBio 2.5 dialect) for FEBio 4 and write the validation load cases. Its `convert()` is reused by h10 / h14. | `human_study/validation/runs/*` |
| `h07_validation_post.py` | Per-level range of motion and facet forces; comparison with Herron 2020. | `human_study/validation/results/` |

## 2_spinal_unit/ - C3-C4 functional spinal unit (FSU)

| File | Purpose | Main output |
|---|---|---|
| `h08_extract_fsu.py` | Cut the deformable-bone C3-C4 FSU (5 mm potting) out of C0-C7. | `human_study/fsu/C34_fsu_intact.feb` |
| `h09_view_fsu.py` | Render an FSU coloured by element role. | PNG |
| `h10_fsu_cases.py` | 1.5 N m pure-moment load cases on an FSU (6 directions). | `human_study/fsu/runs_*` |
| `h11_fsu_vs_full.py` | Compare FSU vs the C3-C4 level of the validated full spine (ROM, facet forces). | `human_study/fsu/*_vs_full.json` |
| `h16_remesh_bone.py` | Refine the C3 / C4 tet mesh at the endplates (gmsh; needs `third_party/glu`). | `human_study/remesh/*.npz` |
| `h17_fsu_refined.py` | Build the FSU with the refined bone and a tied disc-endplate interface. | `human_study/fsu/C34_fsu_refined.feb` |

## 3_cage_case/ - cage and simulation cases

| File | Purpose | Main output |
|---|---|---|
| `h12_cage_mesh.py` | Cage hex mesh (design A contoured / B planar + pad; axial / radial / both gradient; mix / interleave). | `cage_*.npz` |
| `h13_view_cage.py` | Plot a cage mesh (footprint and sections). | PNG |
| `h14_build_case.py` | Assemble one FEBio case from a `params_*.json` (surgery, cage, materials, contact, loading steps). Key options: `contact_type` (`tied` = screening), `cage_mat` (`gent`), `penalty`, `iso_cycles`. | `<case>/case.feb`, `case.json`, `cage_elems.npz` |
| `h21_penalty_ramp.py` | Legacy helper (penalty ramp for per-step contact); superseded by h14's global contact. | - |

## 4_postprocess/

| File | Purpose | Main output |
|---|---|---|
| `h15_post_case.py` | Distraction / clamp / retained distraction; compression endpoints (cage damage, bone yield, height loss, contact-layer crush); friction demand, slip intensity and tipping (bonded screening model); ISO and push-out slip; Q40 functional-failure notes. | `<case>/summary.json` |

## 5_compute/ - running cases

| File | Purpose |
|---|---|
| `h06_run_cpu_batch.py` | Run cases on idle CPU cores (pinned); writes checkpoints and resumes interrupted cases automatically. |
| `h18_run_gpu_case.py` | Run one case on a GPU (cuDSS) in a copy `<case>_gpuN`; same checkpoint / resume logic. |
| `h19_scheduler.py` | Queue (`human_study/queue/*.job`) -> idle GPUs / CPU cores within the 64 GiB memory cap; re-queues interrupted jobs on start. |
| `h20_push_watch.py` | Stops push-out runs once expulsion or a stall is detected, then post-processes them. |
| `kill_febio.sh` | Stop this user's FEBio run in one exact case folder (`scripts/5_compute/kill_febio.sh cage_test/<case>`). |
| `gpu_sampler.py`, `cpu_sampler.py` | Resource sampling (GPU idle detection, CPU use per run). |
| `progress_report.py`, `my_usage.sh`, `my_usage_gpu.sh` | One-line progress report; live resource view. |

## 6_active_learning/

| File | Purpose |
|---|---|
| `h22_active_learning.py` | Active-learning screening: builds / queues design points, scores dislocation and capacity, fits GPs, proposes batches. See `6_active_learning/README.md`. |

## Typical use

```bash
python scripts/3_cage_case/h14_build_case.py human_study/cage_test/params_A_iso_tied2.json human_study/cage_test/case_A_iso_tied2
python scripts/5_compute/h18_run_gpu_case.py 1 human_study/cage_test/case_A_iso_tied2        # or queue it for h19
python scripts/4_postprocess/h15_post_case.py human_study/cage_test/case_A_iso_tied2_gpu1
```

FEBio, MKL and the cuDSS plugin are expected under `third_party/` (not tracked); see `febio_patches/README.md` for the
patched FEBio 4.13 build.
