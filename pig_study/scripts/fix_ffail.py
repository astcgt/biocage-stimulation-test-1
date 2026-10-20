"""Set F_fail_N = peak load in Test-1 summaries written by workers started before the run_tests.py fix."""
import json, glob
for f in glob.glob('results/test1_static/*/summary.json'):
    s = json.load(open(f))
    if s.get('F_fail_definition') is None:
        s['F_fail_N_at_15pct_damage'] = s['F_fail_N']; s['F_fail_N'] = s['peak_Fz_N']
        s['F_fail_definition'] = 'peak axial force in displacement-controlled compression (structural failure)'
        json.dump(s, open(f, 'w'), indent=1); print('fixed', f, s['F_fail_N'])
