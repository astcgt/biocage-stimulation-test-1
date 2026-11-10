"""Process-G production batch for the insertion-stopped designs (PI 2026-11-10: issue 2 option (a) - the 43 production-inserted designs
keep their results, the 27 designs whose production insertion stopped before t 3.5 are run with process G, and every result carries the
insertion process as provenance).

Process G (DECISIONS 2026-11-09 22:10, 2026-11-10 13:46) = the production physio_fric5 deck with the settings class
human_study/al_v2/physio_relG/: release_all_dofs (the stored C3 moment is ramped to zero over t 2-3 instead of being dumped at t 3),
follower_in_release [2.0, 2.5] (the 100 N follower load is on before most of the moment is released), all_dynamic (every step dynamic,
no static -> dynamic switch), main-deck min_residual 1e-4, stick-memory friction law for insertion AND windows (restart_env ->
BIOCAGE_STICK_MEMORY, cbuild_fric binary). The keys come from the settings class, never from this script, so h24 compares them.

Cases: human_study/al_v2/physio_relG/<pNNN>_params.json = physio_fric3/<pNNN>_params.json + the class keys; the build dir
physio_relG/<pNNN> (h14) is never run; h18 copies it to <pNNN>_gpuK and runs insertion + both windows (h31) there - the same
layout as physio_fric3, so fric_compare / e07 / collect_split read it with set = 'physio_relG'.
usage: python h50_relG_batch.py list                       the insertion-stopped designs (production physio_fric3 run ended before t 3.5)
       python h50_relG_batch.py build [pNNN ...]           params + h14 build + h24 preflight for all (or the given) designs
       python h50_relG_batch.py run <workers> <gpus e.g. 1,2,3,4,5> <cores> [pNNN ...]   N workers, one design each, restartable
"""
import os, sys, json, glob, re, subprocess, time, threading, queue
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import P
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py'); H18 = os.path.join(P, 'scripts/5_compute/h18_run_gpu_case.py')
SRC = os.path.join(P, 'human_study/al_v2/physio_fric3'); DST = os.path.join(P, 'human_study/al_v2/physio_relG'); CLS = os.path.relpath(DST, P) + '/'
FEBIO_FRIC = os.path.join(P, 'third_party/FEBio/cbuild_fric/bin/febio4')
PROCESS_KEYS = ('release_all_dofs', 'follower_in_release', 'all_dynamic', 'min_residual', 'restart_env', 'window_min_residual')


def cls():
    S = json.load(open(os.path.join(P, 'human_study/current_settings.json')))['classes']
    if CLS not in S: sys.exit(f'settings class {CLS} missing (register it first; h37 R7 must list its production options)')
    return S[CLS]


def stopped():
    """designs whose production physio_fric3 insertion never reached t 3.5 (largest final time over the run dirs)"""
    out = {}
    for pj in sorted(glob.glob(SRC + '/p[0-9][0-9][0-9]_params.json')):
        p = os.path.basename(pj)[:4]; best = 0.0
        for d in glob.glob(f'{SRC}/{p}*'):
            lg = os.path.join(d, 'case.log')
            if not os.path.isdir(d) or not os.path.exists(lg): continue
            m = re.findall(r'Nonlinear solution status: time= *([\d.eE+-]+)', open(lg, errors='ignore').read()[-300000:])
            if m: best = max(best, float(m[-1]))
        if best < 3.499: out[p] = best
    return out


def build(only):
    import h24_preflight
    c = cls(); todo = [p for p in stopped() if not only or p in only]
    os.makedirs(DST, exist_ok=True); print(len(todo), 'designs to build with', {k: c.get(k) for k in PROCESS_KEYS}, flush=True)
    for p in todo:
        if h24_preflight.valid(os.path.join(DST, p)): print(p, 'already valid', flush=True); continue
        prm = json.load(open(f'{SRC}/{p}_params.json'))
        for k in PROCESS_KEYS:
            if k in c: prm[k] = c[k]
        prm['insertion_process'] = 'G'           # provenance (PI 2026-11-10): recorded in the params, hence in case.json of every run dir
        json.dump(prm, open(f'{DST}/{p}_params.json', 'w'), indent=1)
        r = subprocess.run([sys.executable, H14, f'{DST}/{p}_params.json', f'{DST}/{p}'], cwd=P, capture_output=True, text=True)
        if r.returncode: print(p, 'h14 FAIL', r.stderr.strip()[-300:], flush=True); continue
        chk = h24_preflight.check(os.path.join(DST, p)); print(time.strftime('%H:%M'), p, 'preflight', 'OK' if chk['ok'] else 'FAIL', chk['errors'], chk['warnings'], flush=True)


def done(p):
    for d in glob.glob(f'{DST}/{p}_gpu*'):
        rj = os.path.join(d, 'resources.json')
        if os.path.exists(rj) and json.load(open(rj)).get('normal'): return d
    return None


def run(nw, gpus, ncores, only):
    import h24_preflight
    c = cls(); env = dict(os.environ, BIOCAGE_FEBIO=FEBIO_FRIC, **{k: str(v) for k, v in (c.get('restart_env') or {}).items()})
    todo = [p for p in stopped() if (not only or p in only)]
    q = queue.Queue(); [q.put(p) for p in todo if not done(p) and h24_preflight.valid(os.path.join(DST, p))]
    skipped = [p for p in todo if done(p) or not h24_preflight.valid(os.path.join(DST, p))]
    print(f'{q.qsize()} designs queued, {len(skipped)} skipped (done or no valid preflight): {skipped}', flush=True)
    def worker(i, gpu):
        while True:
            try: p = q.get_nowait()
            except queue.Empty: return
            t0 = time.time(); print(time.strftime('%H:%M'), f'worker {i} gpu {gpu} start {p}', flush=True)
            with open(f'{DST}/{p}_run.log', 'a') as fo:
                r = subprocess.run([sys.executable, H18, str(gpu), f'{DST}/{p}', str(ncores)], cwd=P, env=env, stdout=fo, stderr=subprocess.STDOUT)
            print(time.strftime('%H:%M'), f'{p} exit {r.returncode} {(time.time() - t0) / 60:.0f} min', flush=True)
            if r.returncode == 3: q.put(p); time.sleep(300)      # h18 exit 3 = not enough idle cores: back in the queue
    th = [threading.Thread(target=worker, args=(i, gpus[i % len(gpus)])) for i in range(nw)]
    [t.start() for t in th]; [t.join() for t in th]
    print('BATCH DONE', time.strftime('%Y-%m-%d %H:%M'), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'list': s = stopped(); print(len(s), 'insertion-stopped designs:', ' '.join(f'{p}@{t:.2f}' for p, t in s.items()))
    elif a[0] == 'build': build(a[1:])
    elif a[0] == 'run': run(int(a[1]), [int(g) for g in a[2].split(',')], int(a[3]), a[4:])
    else: sys.exit(__doc__)
