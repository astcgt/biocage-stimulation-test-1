"""physio_fric5 rerun (PI 2026-11-09 decision 1): every physio_fric3 run dir whose insertion reached t 3.5 with a checkpoint is rebuilt
as human_study/al_v2/physio_fric5/<pNNN> (bare name: the h47 case IS the run dir, params <pNNN>_params.json beside it; no _gpuK suffix,
see FILE_INDEX) and its flexion + extension windows are restarted from the checkpoint with the stick-memory law (h47: restart_env from the
settings class, window min_residual 1e-4). Workers run one CASE at a time (both windows in sequence: h47 keeps per-case files), N workers
over the given GPUs, restartable (a window with done_<window> / done is skipped).
usage: python h48_fric5_batch.py build [pNNN ...]            rebuild all (or the given) cases from physio_fric3 (h47 build, h24 preflight)
       python h48_fric5_batch.py run <workers> <gpus e.g. 3,4> <cores_per_window> [pNNN ...]"""
import os, sys, json, glob, re, subprocess, time, threading, queue
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import P
H47 = os.path.join(P, 'scripts/5_compute/h47_restart_pilot.py'); SRC = os.path.join(P, 'human_study/al_v2/physio_fric3'); DST = os.path.join(P, 'human_study/al_v2/physio_fric5')
WINDOWS = ('flexion', 'extension')

def sources():
    out = {}
    for d in sorted(glob.glob(SRC + '/p[0-9][0-9][0-9]*')):   # bare pNNN dirs that ran in place (13 production runs) AND pNNN_gpuK copies (QA 2026-11-09 不符 #1: the _gpu-only glob missed 13 usable checkpoints incl. p062)
        if not os.path.isdir(d) or not os.path.exists(d + '/case.dmp') or not os.path.exists(d + '/case.log'): continue
        txt = open(d + '/case.log', errors='ignore').read()[-300000:]; m = re.findall(r'Nonlinear solution status: time= *([\d.eE+-]+)', txt)
        if not m or float(m[-1]) < 3.499: continue
        p = os.path.basename(d)[:4]
        if p in out: sys.exit(f'two usable run dirs for {p}: {out[p]} {d}')
        out[p] = d
    return out

def law_keys():
    """the reference friction law = the physio_fric5 settings class (h37 R15 pins it): passed to h47 build as key=json so the params carry it"""
    S = json.load(open(os.path.join(P, 'human_study/current_settings.json')))['classes'][os.path.relpath(DST, P) + '/']
    return [f'{k}={json.dumps(S[k])}' for k in ('restart_env', 'window_min_residual')]

def build(only, nworkers=4):
    import h24_preflight
    src = sources(); print(len(src), 'usable checkpoints', flush=True); keys = law_keys()
    todo = [(p, d) for p, d in src.items() if (not only or p in only) and not h24_preflight.valid(os.path.join(DST, p))]   # valid = passing preflight whose fingerprint still holds
    print(len(todo), 'to build with', keys, flush=True)
    def one(pd):
        p, d = pd; r = subprocess.run([sys.executable, H47, 'build', os.path.join(DST, p), d] + keys, cwd=P, capture_output=True, text=True)
        return f"{p} build {'OK' if r.returncode == 0 else 'FAIL'} {(r.stdout + r.stderr).strip()[-300:]}"
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(nworkers) as ex:
        for line in ex.map(one, todo): print(time.strftime('%H:%M'), line, flush=True)

def run(nw, gpus, ncores, only):
    cases = [os.path.join(DST, p) for p in sorted(os.listdir(DST)) if re.match(r'p\d{3}$', p) and (not only or p in only) and os.path.exists(os.path.join(DST, p, 'case.dmp'))]
    todo = [c for c in cases if not all(os.path.exists(os.path.join(c, 'done' + ('' if w == 'extension' else '_' + w))) for w in WINDOWS)]
    print(f'{len(cases)} cases, {len(todo)} with windows to run, {nw} workers on GPUs {gpus}', flush=True)
    q = queue.Queue(); [q.put(c) for c in todo]
    def worker(i):
        gpu = gpus[i % len(gpus)]
        while True:
            try: c = q.get_nowait()
            except queue.Empty: return
            for w in WINDOWS:
                if os.path.exists(os.path.join(c, 'done' + ('' if w == 'extension' else '_' + w))): continue
                with open(os.path.join(c, f'run_{w}.out'), 'w') as fo:
                    r = subprocess.run([sys.executable, H47, 'run', c, str(gpu), str(ncores), w], cwd=P, stdout=fo, stderr=subprocess.STDOUT)
                print(time.strftime('%H:%M'), os.path.basename(c), w, 'exit', r.returncode, flush=True)
                if r.returncode: break      # e.g. no idle cores / no preflight: leave the case for a rerun of this batch
            q.task_done()
    th = [threading.Thread(target=worker, args=(i,)) for i in range(nw)]
    for i, t in enumerate(th): t.start(); time.sleep(20)     # staggered: h47 claims cores under a lock, and the first FEBio start is the memory peak
    for t in th: t.join()
    print('BATCH DONE', time.strftime('%Y-%m-%d %H:%M'), flush=True)

if __name__ == '__main__':
    if sys.argv[1] == 'build': build(set(sys.argv[2:]))     # (re)builds every case without a valid preflight; a valid one is kept
    elif sys.argv[1] == 'run': run(int(sys.argv[2]), [int(g) for g in sys.argv[3].split(',')], int(sys.argv[4]), set(sys.argv[5:]))
    else: sys.exit(__doc__)
