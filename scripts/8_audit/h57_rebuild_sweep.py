"""Rebuild-identity sweep over the production verdict sources (2026-11-21, capability re-score).

Question it answers: did the edits to the builder chain since the evidence dates of the capability checks (h14 BUILD, h30 SPLIT,
h12 / cage_geom MESH, current_settings.json SETTINGS) change any deck that a verdict in use came from? For a sample of run
directories of every set that is a verdict source (tied: results/method/split/best_by_design_merged.json 'source'; friction:
results/method/fric/verdicts.json 'set' / 'case_dir', plus the insertion sets they restart from) the CURRENT h14 rebuilds the case
from its params file into a temporary directory (nothing is written into the run directory - h24 check would refresh its
preflight.json) and the result is compared byte for byte:
  case.feb                 vs the run directory's launched_feb.sha256 (the deck FEBio actually read) or its case.feb
  w_*/restart.feb, restart_static.feb, physio_schedule.json   vs the run directory's (split / restart windows)
  settings                 params vs common + class of current_settings.json (the h24 check 1 rule)
h37 R8 does this for one deck (p062 physio_fric3); this sweep takes K designs per set (first / middle / last of the sorted
verdict sources) so every production recipe is covered: tied non-split, tied split, friction insertion, stick-memory restart,
route-E restart, process-G insertion, process-G route E, production-law fallback, mu 0.3.
usage: python h57_rebuild_sweep.py [K=3] [workers=3]   -> human_study/qa/rebuild_sweep.json, exit 1 when any deck differs
"""
import os, sys, json, glob, hashlib, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EV = os.path.normpath(os.path.join(P, '..', 'biocage-evo')); A = os.path.join(P, 'human_study/al_v2')
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py'); SETTINGS = os.path.join(P, 'human_study/current_settings.json')
INSERTION_OF = {'physio_fric5': 'physio_fric3', 'physio_fric5r': 'physio_fric3', 'physio_relGr': 'physio_relG', 'physio_relG_pl': 'physio_relG',
                'pilot_mu03r': 'pilot_mu03', 'pilot_mu03Gr': 'pilot_mu03G'}


def sha(f): return hashlib.sha256(open(f, 'rb').read()).hexdigest()


def sources():
    """{set: sorted run-directory names that are verdict sources}"""
    out = {}
    t = json.load(open(os.path.join(EV, 'results/method/split/best_by_design_merged.json')))
    for p, w in t.items():
        for wn, r in w.items():
            if isinstance(r, dict) and r.get('source') and '/' in str(r['source']):
                s, d = str(r['source']).split('/')[:2]; out.setdefault(s, set()).add(d)
    v = json.load(open(os.path.join(EV, 'results/method/fric/verdicts.json')))
    for p, d in v.items():
        if p.startswith('_'): continue
        for wn, x in d.get('windows', {}).items():
            if x.get('set') and x.get('case_dir'): out.setdefault(x['set'], set()).add(x['case_dir'])
    for s, ins in INSERTION_OF.items():               # the insertion run each restart set was built from (run dir with a finished case.log)
        for d in list(out.get(s, ())):
            c = [x for x in sorted(glob.glob(os.path.join(A, ins, d[:4] + '_gpu*'))) + [os.path.join(A, ins, d[:4])] if os.path.exists(os.path.join(x, 'case.dmp'))]
            if c: out.setdefault(ins, set()).add(os.path.basename(c[0]))
    return {s: sorted(d) for s, d in out.items()}


def one(job):
    s, d = job; cd = os.path.join(A, s, d); base = d.split('_gpu')[0]; pj = os.path.join(A, s, base + '_params.json')
    r = dict(set=s, case_dir=d, problems=[])
    if not os.path.exists(pj): r['problems'].append('no params file'); return r
    if not os.path.exists(os.path.join(cd, 'case.feb')): r['problems'].append('no case.feb in the run directory'); return r
    prm = json.load(open(pj)); S = json.load(open(SETTINGS)); want = dict(S['common']); rel = os.path.relpath(cd, P)
    for prefix, v in S['classes'].items():
        if rel.startswith(prefix): want.update(v)
    defaults = dict(insert_mode='overlap', biodisc=True, annulus_remnant=True)
    bad = {k: (prm.get(k, defaults.get(k)), v) for k, v in want.items() if prm.get(k, defaults.get(k)) != v}
    if bad: r['problems'].append(f'settings differ from the current class: {bad}')
    with tempfile.TemporaryDirectory() as td:
        x = subprocess.run([sys.executable, H14, pj, td], cwd=P, capture_output=True, text=True)
        if x.returncode: r['problems'].append('h14 failed: ' + x.stderr.strip()[-200:]); return r
        new = sha(os.path.join(td, 'case.feb')); lf = os.path.join(cd, 'launched_feb.sha256')
        ref = open(lf).read().split()[0] if os.path.exists(lf) else sha(os.path.join(cd, 'case.feb'))
        r.update(case_feb=new[:12], reference=ref[:12], reference_kind='launched_feb.sha256' if os.path.exists(lf) else 'case.feb', windows={})
        if new != ref: r['problems'].append('case.feb differs from a rebuild with the current h14')
        for w in sorted(glob.glob(os.path.join(td, 'w_*'))):
            wn = os.path.basename(w)
            for f in ('restart.feb', 'restart_static.feb', 'physio_schedule.json'):
                a, b = os.path.join(w, f), os.path.join(cd, wn, f)
                if not os.path.exists(a): continue
                if not os.path.exists(b): r['windows'][f'{wn}/{f}'] = 'absent in the run directory'; continue      # insertion run whose windows were restarted elsewhere
                same = sha(a) == sha(b); r['windows'][f'{wn}/{f}'] = 'identical' if same else 'DIFFERS'
                if not same: r['problems'].append(f'{wn}/{f} differs from a rebuild with the current h14 / h30')
    return r


if __name__ == '__main__':
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 3; nw = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    src = sources(); jobs = []
    for s, ds in sorted(src.items()):
        pick = sorted({ds[0], ds[len(ds) // 2], ds[-1]}) if K == 3 else ds[:K]
        jobs += [(s, d) for d in pick]
    with ThreadPoolExecutor(nw) as ex: res = list(ex.map(one, jobs))
    bad = [r for r in res if r['problems']]
    out = dict(time=time.strftime('%Y-%m-%dT%H:%M'), sets={s: len(d) for s, d in src.items()}, n_checked=len(res), n_identical=len(res) - len(bad),
               gate_files={os.path.relpath(f, P): time.strftime('%Y-%m-%dT%H:%M', time.localtime(os.path.getmtime(f))) for f in
                           (H14, os.path.join(P, 'scripts/3_cage_case/h30_split_windows.py'), os.path.join(P, 'scripts/3_cage_case/h12_cage_mesh.py'),
                            os.path.join(P, 'scripts/common/cage_geom.py'), SETTINGS)}, results=res)
    json.dump(out, open(os.path.join(P, 'human_study/qa/rebuild_sweep.json'), 'w'), indent=1)
    for r in res: print(r['set'], r['case_dir'], 'OK' if not r['problems'] else r['problems'])
    print(f"{out['n_identical']} / {out['n_checked']} identical"); sys.exit(1 if bad else 0)
