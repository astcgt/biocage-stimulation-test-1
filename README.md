# BIOCAGE simulation studies

Finite-element studies of the BIOCAGE cervical cage (graded PLCL hard/soft polymer).

## Layout

| Folder | Content |
|---|---|
| `human_study/` | **Current study.** Human C3-C4 (FEBio 26-year-old female model, Herron et al. 2020), ACDR implantation, load-bearing capacity and dislocation (slip / tipping) screening. `DECISIONS.md` lists every agreed parameter and design decision; `status.json` tracks progress. Large run outputs are not tracked. |
| `scripts/` | Pipeline for the human study, grouped by stage: `common/`, `1_validation/`, `2_spinal_unit/`, `3_cage_case/`, `4_postprocess/`, `5_compute/`. See `scripts/README.md` for what every script does. |
| `febio_cudss/` | cuDSS (GPU) linear-solver plugin for FEBio 4.13. |
| `febio_patches/` | Four FEBio 4.13 source patches used in the human study (incl. checkpoint/restart fix), with rationale and verification. |
| `pig_study/` | **Earlier study** on a porcine C3-C4 model (tests 1-3, custom GPU contact solver); kept for reference. Its scripts expect to be run from inside `pig_study/`. See `pig_study/README.md`. |

## Where to look

- What was decided and why: `human_study/DECISIONS.md`
- What each script does: `scripts/README.md`
- What each data folder / case folder name means: `human_study/README.md`
- FEBio modifications: `febio_patches/README.md`

Third-party data (the Herron FEBio model from SimTK) is not redistributed here.
