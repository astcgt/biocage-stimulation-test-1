# BIOCAGE simulation studies

Finite-element studies of the BIOCAGE cervical cage (graded PLCL hard/soft polymer).

## Layout

| Folder | Content |
|---|---|
| `human_study/` | **Current study.** Human C3-C4 (FEBio 26-year-old female model, Herron et al. 2020), ACDR implantation, load-bearing capacity and dislocation (slip / tipping) screening. `DECISIONS.md` lists every agreed parameter and design decision; `status.json` tracks progress. Large run outputs are not tracked. |
| `scripts/` | Pipeline for the human study (`h01`-`h21`, `cage_geom.py`, `xplt.py`, scheduler and helpers). |
| `febio_cudss/` | cuDSS (GPU) linear-solver plugin for FEBio 4.13. |
| `febio_patches/` | Three FEBio 4.13 source patches used in the human study, with rationale and verification. |
| `pig_study/` | **Earlier study** on a porcine C3-C4 model (tests 1-3, custom GPU contact solver); kept for reference. Its scripts expect to be run from inside `pig_study/`. See `pig_study/README.md`. |

## Human study pipeline (short)

1. `h01`-`h07`: extract the C0-C7 FEBio model, convert to FEBio 4, validate against Herron 2020.
2. `h08`-`h11`, `h16`-`h17`: C3-C4 functional spinal unit, locally refined endplates (0.5 mm), check against the full spine.
3. `h12`-`h15`, `h21`: cage meshing, case assembly (distraction, insertion, release, test), post-processing.
4. `h18`-`h20`: GPU/CPU runners, scheduler, push-out watcher.

Third-party data (the Herron FEBio model from SimTK) is not redistributed here.
