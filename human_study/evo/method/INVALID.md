# INVALID: every physio run built before 2026-10-26 (combined loading)
Cause: h14 physio moment curves lacked the window-start point, so LB and AR moments ramped from t 3.5 (DECISIONS.md 2026-10-26,
I-001, red-team F-0001). Invalid: al_v2/cases/*physio*, al_v2/physio_test/, al_v2/facet_test/, al_v2/lb_test/, al_v2/physio_analysis/,
evo/method/fl_*.json and every number derived from them (METHODS_COMPARISON.md section A tables, ISSUES.md I-002, DECISIONS.md physio
entries 2026-10-23..25). Kept only as a record. Valid reruns: al_v2/physio_fix/ (built with the fixed h14). 154 run directories affected.
