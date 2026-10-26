# Round 1 digest (2026-10-26), roles active: verifier, safety guard, red team (designer not started; no designs yet)

State:
- Methods: tied FEBio physio runs (75 of 76) analysed with two friction checks (e02): force ratio (optimistic) vs friction
  limit with twist (pessimistic); summary in human_study/evo/ISSUES.md I-002, per-case files human_study/evo/method/fl_*.json.
- GPU solver scripts/7_evo/gpufe/: feb.py (reader), mech.py + kern.py (materials, elements, autodiff tangents),
  contact.py (penalty contact, tie, Coulomb friction), solver.py (dynamic relaxation, superseded for large models),
  newton.py (GPU Newton with cuDSS, PI accepted 2026-10-26). Gates 1 / 1b / 1c passed (VERIFICATION.md);
  gate 2 (intact FSU vs FEBio, human_study/fsu/runs_refined/*) in progress: Newton converges linearly (60 iterations,
  residual 1e-5 at t 0.3), tangent incomplete (pressure follower, facet, tie terms suspected).
- PI decisions of today: DECISIONS.md last lines (friction coefficient from literature; 6 directions x 3 cycles; I-001 to be analysed first).
Your round number is 1. Write your verdict to human_study/evo/board/r0001/<role>.json.
