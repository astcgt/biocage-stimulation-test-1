#!/usr/bin/env python3
"""h45: per-face friction demand and interface tension on every tied window used in best_by_design_merged.json.

Runs e03_mu_req.main on each source case (post-processing only, no solver) and reads, at the state where e04 evaluated mu_squeeze, each face's
mu_scaled (e04's force scaling, per face), mu_force (force ratio) and tension_frac (share of tension over net normal force on the glued face).
States are interpolated with the bracket that e04 used. Output: human_study/figures/mu_requirement/mu_face_scan.json
usage: python h45_mu_face_scan.py [workers]
"""
import os, sys, json, multiprocessing as mp
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVO = f'{os.path.dirname(ROOT)}/biocage-evo'; AL = f'{ROOT}/human_study/al_v2'; OUT = f'{ROOT}/human_study/figures/mu_requirement/mu_face_scan.json'
sys.path[:0] = [f'{EVO}/methods', f'{EVO}/common']; sys.dont_write_bytecode = True
WIN = ['flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right']


def job(cd):
    import e03_mu_req as e3, tempfile, io, contextlib
    try:
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            f = os.path.join(td, 'e03.json'); e3.main(os.path.join(AL, cd), f)
            r = json.load(open(f))
        return cd, r['states'], None
    except Exception as e:
        return cd, None, repr(e)[:200]


def main():
    B = json.load(open(f'{EVO}/results/method/split/best_by_design_merged.json'))
    need = {}
    only = sys.argv[2].split(',') if len(sys.argv) > 2 else None        # optional: test on a few case dirs
    for p, v in B.items():
        for w in WIN:
            if w in v and v[w].get('target_reached'): need.setdefault(v[w]['source'], []).append((p, w, v[w]['t'], v[w].get('eval'), v[w]['mu_squeeze']))
    print(len(need), 'case dirs', sum(len(x) for x in need.values()), 'windows', flush=True)
    if only: need = {k: v for k, v in need.items() if k in only}
    res, errs = [], {}
    with mp.Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 12) as pool:
        for i, (cd, st, err) in enumerate(pool.imap_unordered(job, list(need))):
            if err: errs[cd] = err; continue
            for p, w, t, ev, mu in need[cd]:
                s = [x for x in st if x.get('window') == w] or st
                if not s: errs[f'{cd}:{w}'] = 'no states'; continue
                s = sorted(s, key=lambda x: x['t'])
                a = max((x for x in s if x['t'] <= t + 1e-9), key=lambda x: x['t'], default=s[0]); b = min((x for x in s if x['t'] >= t - 1e-9), key=lambda x: x['t'], default=s[-1])
                f = 0.0 if b['t'] == a['t'] else (t - a['t']) / (b['t'] - a['t'])
                g = lambda face, k: None if a[face].get(k) is None or b[face].get(k) is None else (1 - f) * a[face][k] + f * b[face][k]
                res.append(dict(design=p, window=w, t=t, mu_squeeze=mu, gap=abs(b['t'] - a['t']), **{f'{fc}_{k}': g(fc, k) for fc in ('top', 'bot') for k in ('mu_scaled', 'mu_drop', 'mu_force', 'tension_frac', 'N_net', 'T')}))
            if i % 20 == 0:
                print(i, flush=True); json.dump(dict(rows=res, errors=errs), open(OUT, 'w'))
    json.dump(dict(rows=res, errors=errs), open(OUT, 'w')); print('done', len(res), 'errors', len(errs), flush=True)


if __name__ == '__main__':
    main()
