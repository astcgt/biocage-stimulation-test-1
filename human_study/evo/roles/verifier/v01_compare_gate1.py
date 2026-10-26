"""Verifier r0001: compare the original gate-1 report with the verifier re-run (reproducibility) and hash the inputs.
usage: python human_study/evo/roles/verifier/v01_compare_gate1.py
"""
import json, hashlib, os
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
A = os.path.join(P, 'human_study/evo/gpufe_verify/gate1'); B = os.path.join(P, 'human_study/evo/roles/verifier/gate1_rerun')
a = json.load(open(os.path.join(A, 'gate1_report.json'))); b = json.load(open(os.path.join(B, 'gate1_report.json')))
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
out = []
for x, y in zip(a['cases'], b['cases']):
    assert x['case'] == y['case']
    fa, fb = os.path.join(A, x['case'], 'case.feb'), os.path.join(B, y['case'], 'case.feb')
    same_in = md5(fa) == md5(fb)
    d = max(abs(x['per_time'][t][k] - y['per_time'][t][k]) for t in x['per_time'] for k in x['per_time'][t])
    # FEBio outputs identical?
    same_fe = all(md5(os.path.join(A, x['case'], f)) == md5(os.path.join(B, y['case'], f))
                  for f in ('stress.txt', 'react.txt') if os.path.exists(os.path.join(A, x['case'], f)))
    row = dict(case=x['case'], orig_worst=x['worst_rel_err'], rerun_worst=y['worst_rel_err'], orig_pass=x['passed'],
               rerun_pass=y['passed'], input_feb_identical=same_in, febio_logs_identical=same_fe,
               max_abs_diff_of_metrics=d, times=list(x['per_time']))
    out.append(row); print(row)
json.dump(out, open(os.path.join(P, 'human_study/evo/roles/verifier/v01_compare_gate1.json'), 'w'), indent=1)
