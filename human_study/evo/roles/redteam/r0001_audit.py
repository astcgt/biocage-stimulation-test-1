"""Red team r0001: (1) which physio windows each e02 result covers (mu_req is meant to be the worst of 6 directions);
(2) provenance fields in e02 outputs; (3) twist vs the applied (buggy) Rz moment curve over all cases;
(4) whether the invalid physio results carry any 'invalid / superseded' marker; (5) file-system write permission of
this role process on files it must not change (os.access only, nothing is written)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import json, glob, numpy as np
R = _env.ROOT
fl = sorted(glob.glob(os.path.join(R, 'human_study/evo/method/fl_*.json')))
allw = ['flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right']
cover = {}; prov = set(); ratio = []
for f in fl:
    d = json.load(open(f)); prov |= set(d.keys())
    w = tuple(x for x in allw if x in d['windows']); cover[w] = cover.get(w, 0) + 1
    # applied Rz moment of the buggy curve (3.5,0)->(8,1): 1500 * (t - 3.5) / 4.5 for t in [3.5, 8]
    for s in d.get('states', []):
        t = s['t']
        if 3.9 <= t <= 7.5 and 'top' in s:
            ratio.append(abs(s['top']['Mz_Nmm']) / (1500 * (t - 3.5) / 4.5))
print('e02 files', len(fl)); print('top-level keys (provenance?)', sorted(prov))
for w, n in sorted(cover.items(), key=lambda x: -x[1]): print(f'  {n:3d} cases cover {len(w)} windows: {w}')
r = np.array(ratio); print('|face twist top| / applied Rz (buggy curve), t 3.9-7.5, all cases: median %.2f, p10 %.2f, p90 %.2f, n %d' % (np.median(r), np.percentile(r, 10), np.percentile(r, 90), len(r)))
# 4. invalid markers
mk = 0; tot = 0
for s in glob.glob(os.path.join(R, 'human_study/al_v2/cases/p*_physio*/summary.json')):
    tot += 1; t = open(s).read().lower()
    if any(k in t for k in ('invalid', 'superseded', 'combined_loading', 'load_curve_bug')): mk += 1
print(f'physio summary.json files: {tot}, with an invalid/superseded marker: {mk}')
mk = sum(1 for f in fl if any(k in open(f).read().lower() for k in ('invalid', 'superseded')))
print(f'e02 files with an invalid/superseded marker: {mk}/{len(fl)}')
# 5. write permission (no write is done)
for p in ('human_study/DECISIONS.md', 'scripts/7_evo/gpufe/contact.py', 'scripts/7_evo/roles/redteam.md', 'scripts/7_evo/e10_run_roles.sh',
          'human_study/evo/archive', 'human_study/evo/roles/verifier', 'human_study/evo/roles/safety', 'human_study/evo/board/r0001',
          'human_study/evo/gpufe_verify/VERIFICATION.md', 'human_study/evo/requests'):
    q = os.path.join(R, p); print(f'  writable by this role process: {os.access(q, os.W_OK)!s:5s} {p}')
