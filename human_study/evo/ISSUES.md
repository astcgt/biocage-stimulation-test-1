# Open items (evo) - digest for the PI

| id | from | item | status |
|---|---|---|---|
| I-001 | integrator (e02 batch, 75 tied physio runs) | twist on the glued cage faces in flexion / extension (median ~170 N mm) although the model is left-right symmetric: check cage-mesh symmetry (h12 grid origin), stress sampling, frame Y = 0 plane; affects the friction-limit numbers, not FEBio results | CAUSE FOUND 2026-10-26: h14 physio load-curve bug (moments of later windows ramped from t 3.5 -> combined loading); fixed, physio runs to be redone; remaining mesh asymmetry small |
| I-002 (INVALID data, combined loading) | integrator | friction needed, tied FEBio runs: force ratio (optimistic) flexion 0.24 / extension 0.23 / LB ~0.5 vs friction limit with twist (pessimistic) 0.37 / 0.57 / ~2; real-friction GPU runs to decide | open |
