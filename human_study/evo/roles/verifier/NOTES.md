# Verifier notes (private)

## r0001 (2026-10-26) -> HOLD
- Gate 1 re-run bit-identical (v01_compare_gate1.json).
- V02 stick creep (v02_stick_creep.py): GPU and FEBio both creep under constant sub-limit tangential load, linear in the
  increment count, ~1/E. Root cause both codes: stick anchor re-projected at every increment start. Critical for slip-out.
  Results: v02_results_E10.json, v02_stick_creep_newton.json (E 400).
- Newton line-search rigid-state bug (newton.py:202-208), unconverged increments accepted, untracked code, ignored laugon.
- Running scripts: `python -I` drops the user site and env-based library lookup; v02 header shows the workaround
  (user site first, CUDA_PATH, preload libnvrtc + libcudss, site.ENABLE_USER_SITE).

## Next round to-do
- Re-run V02 after CR-v1; must give creep < 1e-4 mm for n = 10 and 80.
- Write gate 1d (rotation 45 deg, nu 0.49, follower pressure, rigid force/moment, tied, two-pass) through NewtonSolver.
- Check gate 2 driver once committed (tie force 0 in flex_pos_y_gpu.json).
