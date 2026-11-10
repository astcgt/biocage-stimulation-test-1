"""Production-law fallback windows of the process-G production set (PI 2026-11-10 item 1 extended to process G; DECISIONS 2026-11-10 14:45, 17:xx).

A physio_relG window that stops under the stick-memory law before its evaluation point - but NOT in the first increments (soft-face locking,
PI item 2: no fallback) - is restarted from the SAME process-G t 3.5 checkpoint with the production friction law (BIOCAGE_STICK_MEMORY=0),
the pilot_relGctl control recipe (h47 build + run), as set physio_relG_pl (settings class human_study/al_v2/physio_relG_pl/ = physio_relG
+ restart_env 0). ops/fric_compare.py uses such a window ONLY as the fallback source of the unusable physio_relG window (read-out + 0.043 mm
margin, flagged 'fallback', window_law 'production (fallback)'); h37 R17 pins the class, the sources, the evidence lines and that use.
Control windows (windows that computed under both laws) measure the law shift on process-G checkpoints (ops/law_shift.py ->
relG_law_shift.json): the transfer check of the margin, which was measured on production-inserted checkpoints.

usage: python h51_relG_fallback.py list                     needed windows (from the evo verdicts: run ops/fric_compare.py first), skipped ones (locking,
                                                            source still live, fallback applied), done markers
       python h51_relG_fallback.py build [pNNN ...]         physio_relG_pl/<pNNN> from the finished physio_relG/<pNNN>_gpuK run (h47 build, class check by h24);
                                                            a valid case or one with started windows is never rebuilt (h47 build wipes the case dir)
       python h51_relG_fallback.py run <workers> <gpus e.g. 1,2,3,4> <cores> [pNNN:window ...] [+pNNN:window ...]
                                                            'pNNN:window' = run ONLY these; '+pNNN:window' = these in addition to the needed windows
                                                            (controls, queued after the needed ones each pass)
                                                            driver: every 15 min reruns fric_compare, builds + queues the needed windows (or only the given
                                                            ones, e.g. controls); a window starts only when the physio_relG drive (ops/relG_drive.py) has
                                                            nothing left to start, my h18 + h47 runs x cores + cores <= 32 (cgroup quota) and the GPU holds
                                                            < 60 % memory; ends with 'RELG_PL DONE' when the drive is done and nothing is queued or live
       python h51_relG_fallback.py controls                 usable physio_relG windows (control candidates), one 'pNNN:window' per line
"""
import os, sys, json, glob, re, subprocess, time, threading, queue, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import P
from h50_relG_batch import gpu_busy
import h24_preflight
H47 = os.path.join(P, 'scripts/5_compute/h47_restart_pilot.py')
EV = os.path.normpath(os.path.join(P, '..', 'biocage-evo')); FRIC_COMPARE = os.path.join(EV, 'ops/fric_compare.py'); VERD = os.path.join(EV, 'results/method/fric/verdicts.json')
SRC = os.path.join(P, 'human_study/al_v2/physio_relG'); DST = os.path.join(P, 'human_study/al_v2/physio_relG_pl'); DRIVE_LOG = os.path.join(SRC, 'drive.log')
QUOTA = 32                       # this account's cgroup core quota (ops/relG_drive.py: 6 x 6 threads ran 26-28 % throttled)
RESTART_ENV = 'restart_env={"BIOCAGE_STICK_MEMORY": "0"}'
sfx = lambda w: '' if w == 'extension' else '_' + w
marker = lambda p, w, kind='done': os.path.join(DST, p, kind + sfx(w))


def source_run(p):
    """the finished physio_relG run dir of a design (resources.json, case.dmp, window dirs); None while it runs or when its insertion failed"""
    c = [d for d in glob.glob(f'{SRC}/{p}_gpu*') if os.path.exists(d + '/resources.json') and os.path.exists(d + '/case.dmp') and glob.glob(d + '/w_*')]
    return max(c, key=os.path.getmtime) if c else None


def needed(v=None):
    """([(design, window, reason)], [(design, window, why skipped)]) from the evo verdicts: windows of a physio_relG design that are missing
    (no evaluation point), not soft-face locking, without an applied fallback, whose source run is finished"""
    v = v or (json.load(open(VERD)) if os.path.exists(VERD) else {}); out, skip = [], []
    for p, d in sorted(v.items()):
        W = d.get('windows') or {}
        if p.startswith('_') or not any((x or {}).get('set') == 'physio_relG' for x in W.values()): continue
        for w in d.get('missing', []):
            x = W.get(w) or {}
            if w in (d.get('soft_face_locking') or []): skip.append((p, w, 'soft-face locking: ' + str((d.get('soft_face_locking_evidence') or {}).get(w)))); continue
            if x.get('fallback'): skip.append((p, w, 'fallback applied')); continue
            if not source_run(p): skip.append((p, w, 'physio_relG run still live')); continue
            out.append((p, w, 'stick-law window stopped before an evaluation point' + (' (fallback window done, no evaluation point either)' if os.path.exists(marker(p, w)) else '')))
    return out, skip


def build(only=()):
    todo = sorted({p for p, w, _ in needed()[0]} | set(only)); os.makedirs(DST, exist_ok=True)
    for p in todo:
        cd = os.path.join(DST, p)
        if h24_preflight.valid(cd): print(p, 'already valid', flush=True); continue
        if os.path.isdir(cd) and glob.glob(cd + '/started_at*'): print(p, 'has started windows, not rebuilt', flush=True); continue
        src = source_run(p)
        if not src: print(p, 'no finished physio_relG run', flush=True); continue
        r = subprocess.run([sys.executable, H47, 'build', cd, src, RESTART_ENV], cwd=P, capture_output=True, text=True)
        print(time.strftime('%H:%M'), p, 'build from', os.path.basename(src), 'OK' if r.returncode == 0 else f'FAIL {r.returncode}', (r.stdout.strip().splitlines() or [''])[-1][:200], r.stderr.strip()[-300:], flush=True)


def ps_args():
    return subprocess.run(['ps', '-u', str(os.getuid()), '-o', 'args='], capture_output=True, text=True).stdout.splitlines()   # never pgrep -f: the pattern would match this shell


def busy_threads():
    """threads of my live FEBio runs: h18 (process-G runs, '<gpu> <case> <cores>') and h47 ('run <case> <gpu> <cores>')"""
    n = 0
    for l in ps_args():
        m = re.search(r'h18_run_gpu_case\.py \d+ \S+ (\d+)', l) or re.search(r'h47_restart_pilot\.py run \S+ \d+ (\d+)', l)
        if m: n += int(m.group(1))
    return n


def relg_todo():
    """designs ops/relG_drive.py still has to start (its rule: finished = any resources.json in a run dir other than _gpu5; live = h18 / h50 run)"""
    live = {m.group(1) for l in ps_args() for m in [re.search(r'(?:h18_run_gpu_case\.py \d+ \S*physio_relG/|h50_relG_batch\.py run 1 \d+ \d+ )(p\d{3})', l)] if m}
    fin = {os.path.basename(d).split('_gpu')[0] for d in glob.glob(SRC + '/p*_gpu*') if os.path.exists(d + '/resources.json') and not d.endswith('_gpu5')}
    return sorted(os.path.basename(f)[:4] for f in glob.glob(SRC + '/p[0-9][0-9][0-9]_params.json') if os.path.basename(f)[:4] not in fin | live)


def drive_done(): return os.path.exists(DRIVE_LOG) and 'RELG DRIVE DONE' in open(DRIVE_LOG).read()


def refresh():
    r = subprocess.run([sys.executable, FRIC_COMPARE, '2'], cwd=EV, capture_output=True, text=True)
    if r.returncode: print(time.strftime('%H:%M'), 'fric_compare FAILED:', r.stderr[-400:], flush=True)
    return r.returncode == 0


def run(nw, gpus, ncores, only):
    extra = [tuple(x[1:].split(':')) for x in only if x.startswith('+')]; only = [x for x in only if not x.startswith('+')]
    q = queue.Queue(); queued = set(); inflight = set(); fails = collections.Counter(); lock = threading.Lock(); stop = threading.Event()
    def enqueue():
        items = ([(p, w) for p, w, _ in needed()[0]] + extra) if not only else [tuple(x.split(':')) for x in only]
        new = [it for it in items if it not in queued and not os.path.exists(marker(*it)) and fails[it] < 6]
        for p in sorted({p for p, w in new}):
            if not h24_preflight.valid(os.path.join(DST, p)): build([p])
        for it in new:
            if h24_preflight.valid(os.path.join(DST, it[0])): q.put(it); queued.add(it)
            else: fails[it] += 1
        if new: print(time.strftime('%H:%M'), 'queued', [f'{p}:{w}' for p, w in new], flush=True)
    def slot_free(gpu): return (drive_done() or not relg_todo()) and busy_threads() + ncores <= QUOTA and not gpu_busy(gpu)
    def worker(i, gpu):
        while not stop.is_set():
            try: it = q.get(timeout=30)
            except queue.Empty: continue
            with lock: inflight.add(it)
            p, w = it
            try:
                if os.path.exists(marker(p, w)): continue
                waited = 0
                while not slot_free(gpu) and waited < 24 * 3600 and not stop.is_set(): time.sleep(120); waited += 120
                if not slot_free(gpu): q.put(it); continue
                t0 = time.time(); print(time.strftime('%H:%M'), f'worker {i} gpu {gpu} start {p} {w}', flush=True)
                with open(os.path.join(DST, f'{p}_run.log'), 'a') as fo:
                    r = subprocess.run([sys.executable, H47, 'run', os.path.join(DST, p), str(gpu), str(ncores), w], cwd=P, stdout=fo, stderr=subprocess.STDOUT)
                dt = time.time() - t0; print(time.strftime('%H:%M'), f'{p} {w} exit {r.returncode} {dt / 60:.0f} min', flush=True)
                if not os.path.exists(marker(p, w)):
                    fails[it] += 1
                    if fails[it] >= 6: print(time.strftime('%H:%M'), f'{p} {w}: 6 attempts without a done marker, given up', flush=True); continue
                    if dt < 120: print(time.strftime('%H:%M'), f'{p} {w} ended within 2 min (idle cores / launcher, not a solver result): requeued, worker {i} pauses 5 min', flush=True); time.sleep(300)
                    q.put(it)
            finally:
                with lock: inflight.discard(it)
    os.makedirs(DST, exist_ok=True)
    th = [threading.Thread(target=worker, args=(i, gpus[i % len(gpus)]), daemon=True) for i in range(nw)]; [t.start() for t in th]
    print(time.strftime('%H:%M'), f'start: {nw} workers, GPUs {gpus}, {ncores} cores, quota {QUOTA}', 'only ' + ' '.join(only) if only else 'needed windows from the verdicts' + (' + controls ' + ' '.join(f'{p}:{w}' for p, w in extra) if extra else ''), flush=True)
    while True:
        if not only: refresh()
        enqueue()
        if (only or drive_done()) and q.empty() and not inflight: break
        time.sleep(900)
    stop.set(); [t.join() for t in th]; print('RELG_PL DONE', time.strftime('%Y-%m-%d %H:%M'), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'list':
        out, skip = needed()
        print(len(out), 'needed:'); [print(f'  {p}:{w}  {why}' + ('  [done marker]' if os.path.exists(marker(p, w)) else '')) for p, w, why in out]
        print(len(skip), 'skipped:'); [print(f'  {p}:{w}  {why}') for p, w, why in skip]
    elif a[0] == 'build': build(a[1:])
    elif a[0] == 'run': run(int(a[1]), [int(g) for g in a[2].split(',')], int(a[3]), a[4:])
    elif a[0] == 'controls':
        v = json.load(open(VERD))
        for p, d in sorted(v.items()):
            if p.startswith('_'): continue
            for w, x in (d.get('windows') or {}).items():
                if x.get('set') == 'physio_relG' and x.get('usable'): print(f'{p}:{w}  {x.get("eval_point")} {"fallback" if x.get("fallback") else ""}')
    else: sys.exit(__doc__)
