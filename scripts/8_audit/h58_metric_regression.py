"""Regression of the verdict metric programs against their stored results (2026-11-21, capability re-score).

Question it answers: do the CURRENT e03 / e04 / e05 programs (biocage-evo methods; e03 edited 2026-11-17, e04 2026-11-18) still give
the numbers stored when the verdicts were computed? ops/collect_split.py and ops/fric_compare.py skip a window whose result file
exists, so 'the pipeline was rerun and nothing changed' says nothing about an edit of the metric programs. Here a sample of stored
result files (every k-th of the sorted list: tied split windows results/method/split/*.e04.json / *.e05.json, friction windows
results/method/fric/*.e04.json) is recomputed from the same window directory into a temporary file and compared leaf by leaf:
numbers within REL (relative) or ABS (absolute), other values equal; keys that exist only in the new output (read-outs added later,
e.g. T19) are listed, not counted; 'provenance' is ignored.
usage: python h58_metric_regression.py [n_tied=8] [n_fric=8] [n_e05=3] [workers=3]  -> human_study/qa/metric_regression.json, exit 1 on a difference
"""
import os, sys, json, glob, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); EV = os.path.normpath(os.path.join(P, '..', 'biocage-evo'))
REL, ABS = 1e-6, 1e-9
SKIP = ('provenance',)


def diff(a, b, path=''):
    """-> (differences, keys only in the new output)"""
    d, new = [], []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in SKIP: continue
            if k not in b: d.append(f'{path}/{k}: missing in the recomputed output'); continue
            x, y = diff(a[k], b[k], f'{path}/{k}'); d += x; new += y
        new += [f'{path}/{k}' for k in b if k not in a and k not in SKIP]
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): d.append(f'{path}: length {len(a)} -> {len(b)}')
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                p, q = diff(x, y, f'{path}[{i}]'); d += p; new += q
    elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        if a != b: d.append(f'{path}: {a!r} -> {b!r}')
    else:
        if abs(a - b) > max(ABS, REL * max(abs(a), abs(b))): d.append(f'{path}: {a!r} -> {b!r}')
    return d, new


def one(job):
    kind, f = job; j = json.load(open(f)); wd = j.get('case')
    if not wd and os.path.exists(f.replace('.e05.json', '.e04.json')): wd = json.load(open(f.replace('.e05.json', '.e04.json'))).get('case')   # e05 files carry no 'case': same window as the e04 file of the same tag
    r = dict(kind=kind, stored=os.path.relpath(f, EV), stored_time=time.strftime('%Y-%m-%dT%H:%M', time.localtime(os.path.getmtime(f))), window=wd)
    if not wd or not os.path.exists(os.path.join(wd, 'case.xplt')): r['skipped'] = 'window directory or case.xplt not found'; return r
    prog = 'methods/e05_compression.py' if kind.endswith('e05') else 'methods/e04_dislocation.py'
    with tempfile.TemporaryDirectory() as td:
        o = os.path.join(td, 'o.json')
        x = subprocess.run(['timeout', '2400', sys.executable, os.path.join(EV, prog), wd, o], capture_output=True, text=True)
        if x.returncode or not os.path.exists(o): r['error'] = x.stderr.strip()[-300:]; return r
        d, new = diff(j, json.load(open(o))); r.update(n_diff=len(d), differences=d[:12], new_keys=sorted({k.split('/')[-1] for k in new})[:12])
    return r


if __name__ == '__main__':
    a = [int(x) for x in sys.argv[1:]] + [8, 8, 3, 3][len(sys.argv) - 1:]; nt, nf, n5, nw = a[:4]
    pick = lambda fs, n: [fs[i] for i in sorted({round(k * (len(fs) - 1) / max(1, n - 1)) for k in range(n)})] if fs else []
    jobs = [('tied e04', f) for f in pick(sorted(glob.glob(os.path.join(EV, 'results/method/split/*.e04.json'))), nt)] + \
           [('tied e05', f) for f in pick(sorted(glob.glob(os.path.join(EV, 'results/method/split/*.e05.json'))), n5)] + \
           [('fric e04', f) for f in pick(sorted(glob.glob(os.path.join(EV, 'results/method/fric/*.e04.json'))), nf)]
    with ThreadPoolExecutor(nw) as ex: res = list(ex.map(one, jobs))
    bad = [r for r in res if r.get('n_diff') or r.get('error')]; done = [r for r in res if 'n_diff' in r]
    progs = {p: time.strftime('%Y-%m-%dT%H:%M', time.localtime(os.path.getmtime(os.path.join(EV, 'methods', p)))) for p in ('e03_mu_req.py', 'e04_dislocation.py', 'e05_compression.py')}
    json.dump(dict(time=time.strftime('%Y-%m-%dT%H:%M'), tolerance=dict(rel=REL, abs=ABS), programs=progs, n_jobs=len(res), n_compared=len(done),
                   n_identical=len([r for r in done if not r['n_diff']]), results=res), open(os.path.join(P, 'human_study/qa/metric_regression.json'), 'w'), indent=1)
    for r in res: print(r['kind'], r['stored'], r.get('skipped') or r.get('error') or ('identical' if not r['n_diff'] else r['differences'][:3]), 'new keys', r.get('new_keys'))
    print(f'{len([r for r in done if not r["n_diff"]])} / {len(done)} compared identical; {len(res) - len(done)} skipped or failed'); sys.exit(1 if bad else 0)
