"""Hybrid GPU + CPU scheduler for queued FEBio cases (PI 2026-10-20: grab every idle resource, no reserve).

Queue: human_study/queue/*.job (JSON {"case_dir": ..., "cores": 16, "cpu_only": false, "mem_gb": 8, "host_mem_gb_gpu": 4});
oldest first, only jobs with a valid preflight check (h24), backfilled (a later job may start when the oldest does not fit). A job starts only if the account cgroup memory headroom covers its estimate + 4 GB. A job moves to queue/running/ when
launched and to queue/done/ when its process exits.
Every 60 s:
  GPU g (all GPUs on the node) is idle when its last IDLE_MIN one-minute samples in human_study/gpu_samples.csv
  (written by gpu_sampler.py) average < 10 % utilisation, it has >= MEM_NEED_MB free now and none of my runs is on it.
  A GPU already running my jobs takes up to MAX_PER_GPU of them while it averages < SHARE_UTIL_MAX % (2026-10-22). An idle GPU takes the next job via h18_run_gpu_case.py (cuDSS + idle CPU cores).
  If no GPU is idle but >= 16 idle unclaimed cores exist, the next job runs on CPU via h06_run_cpu_batch.py.
On start, interrupted jobs (in queue/running but without a live FEBio process) are re-queued and resume from their
checkpoint (runners write <case>.dmp every 5 converged steps and restart with 'febio4 -r').
Log: human_study/scheduler.log.   usage: python h19_scheduler.py
"""
import os, sys, time, json, glob, csv, shutil, subprocess
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
from h06_run_cpu_batch import cpu_busy, claimed_cores, P
import h24_preflight

IDLE_MIN, UTIL_MAX, MEM_NEED_MB = 15, 10.0, int(1.5 * 7000)   # cage case peak ~7 GB on GPU (measured 2026-10-20)
MAX_PER_GPU, SHARE_UTIL_MAX = 5, 60.0                         # my runs barely load a GPU (< 25 %, 2026-10-22)
CPU_LAUNCH_MAX = 8                                              # CPU jobs launched per 60 s pass
RESERVE_H = 12                                                  # backfill may pass the head job for at most this long
Q = os.path.join(P, 'human_study/queue'); RUN = os.path.join(Q, 'running'); DONE = os.path.join(Q, 'done')
SAMPLES = os.path.join(P, 'human_study/gpu_samples.csv'); LOG = os.path.join(P, 'human_study/scheduler.log')
for d in (Q, RUN, DONE): os.makedirs(d, exist_ok=True)


CG = '/sys/fs/cgroup' + open('/proc/self/cgroup').read().strip().split(':')[-1]


def mem_free_gb():
    """Headroom under this account's cgroup memory limit (64 GiB until 2026-10-21, now 128 GiB; read live each check)."""
    try:
        lim = open(CG + '/memory.max').read().strip()
        st = dict(l.split() for l in open(CG + '/memory.stat'))
        used = int(st['anon']) + int(st.get('slab', 0)) + int(st.get('kernel_stack', 0))   # page cache is reclaimable
        return (int(lim) - used) / 2**30 if lim != 'max' else 1e9
    except OSError:
        return 1e9


def log(msg):
    with open(LOG, 'a') as f: f.write(time.strftime('%m-%d %H:%M:%S ') + msg + '\n')


def gpu_state():
    rows = list(csv.reader(open(SAMPLES)))
    now = {int(r[0]): (int(r[1]), int(r[2]), int(r[3])) for r in (l.split(', ') for l in subprocess.run(
        ['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
        capture_output=True, text=True, timeout=60).stdout.strip().splitlines())}
    uuid = dict(l.split(', ') for l in subprocess.run(['nvidia-smi', '--query-gpu=uuid,index', '--format=csv,noheader'],
                                                      capture_output=True, text=True, timeout=60).stdout.strip().splitlines())
    mine = {}
    for l in subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'],
                            capture_output=True, text=True, timeout=60).stdout.strip().splitlines():
        u, pid = l.split(', ')
        try:
            if os.stat(f'/proc/{pid}').st_uid == os.getuid(): mine[int(uuid[u])] = mine.get(int(uuid[u]), 0) + 1
        except OSError: pass
    out = {}
    for g, (util, used, tot) in now.items():
        hist = [int(r[2]) for r in rows if int(r[1]) == g][-IDLE_MIN:]
        mean = sum(hist) / max(1, len(hist)); n = mine.get(g, 0)
        idle = len(hist) >= IDLE_MIN and tot - used >= MEM_NEED_MB and (
            mean < UTIL_MAX if n == 0 else (n < MAX_PER_GPU and mean < SHARE_UTIL_MAX))   # share a GPU only among my runs
        out[g] = dict(idle=idle, mean_util=round(mean, 1), free_mb=tot - used, mine=n)
    return out


def launch(job, gpu=None):
    spec = json.load(open(job)); name = os.path.basename(job)[:-4]; case = spec['case_dir']; cores = spec.get('cores', 16)
    if gpu is not None:
        cmd = ['python', 'scripts/5_compute/h18_run_gpu_case.py', str(gpu), case, str(cores)]
    else:
        cmd = ['python', 'scripts/5_compute/h06_run_cpu_batch.py', '--cores', str(cores), os.path.dirname(case.rstrip('/')),
               os.path.basename(case.rstrip('/'))]
    out = open(os.path.join(RUN, name + '.out'), 'w')
    p = subprocess.Popen(cmd, cwd=P, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)   # survive scheduler restarts
    shutil.move(job, os.path.join(RUN, name + '.job'))
    log(f'launch {name} on ' + (f'GPU {gpu}' if gpu is not None else 'CPU') + f' ({cores} cores)')
    return p


def febio_cwds():
    """Working directories of this user's running FEBio processes."""
    out = set()
    for pid in os.listdir('/proc'):
        if not pid.isdigit(): continue
        try:
            if os.stat(f'/proc/{pid}').st_uid != os.getuid(): continue
            if b'febio4' not in open(f'/proc/{pid}/cmdline', 'rb').read(): continue
            out.add(os.path.realpath(os.readlink(f'/proc/{pid}/cwd')))
        except OSError:
            pass
    return out


def resume_orphans():
    """After a restart of the scheduler (or of the whole server), put jobs that were running but whose FEBio process is gone
    back in the queue; the runners then continue them from their checkpoint (<case>.dmp) instead of starting over."""
    alive = febio_cwds()
    for j in glob.glob(os.path.join(RUN, '*.job')):
        case = os.path.realpath(os.path.join(P, json.load(open(j))['case_dir']))
        if any(c == case or c.startswith(case + '_gpu') for c in alive): continue      # still running (detached child)
        name = os.path.basename(j)[:-4]
        logs = glob.glob(os.path.join(case, '*.log')) + glob.glob(os.path.join(case + '_gpu*', '*.log'))
        if any(any(k in open(l, errors='ignore').read()[-4000:] for k in ('N O R M A L', 'E R R O R')) for l in logs):
            os.replace(j, os.path.join(DONE, time.strftime('%H%M%S_') + name + '.job')); log(f'archived stale {name} (already ended)')
            continue
        os.replace(j, os.path.join(Q, name + '.job')); log(f'requeued interrupted {name} (resumes from checkpoint)')


def reap_adopted(running):
    """Jobs in queue/running/ that this scheduler instance did not launch (they survived a restart) are archived once their
    FEBio process is gone; exit '?' lets the watchdog requeue them if FEBio never terminated."""
    alive = febio_cwds()
    for j in glob.glob(os.path.join(RUN, '*.job')):
        name = os.path.basename(j)[:-4]
        if name in running: continue
        case = os.path.realpath(os.path.join(P, json.load(open(j))['case_dir']))
        if any(c == case or c.startswith(case + '_gpu') for c in alive): continue
        for ext in ('.job', '.out'):
            src = os.path.join(RUN, name + ext)
            if os.path.exists(src): os.replace(src, os.path.join(DONE, time.strftime('%H%M%S_') + name + ext))
        log(f'finished {name} exit=? (adopted after a scheduler restart)')


def first_fit(jobs, fits):
    """Backfill (2026-10-22): the oldest queued job that fits the free cores / memory now, instead of waiting until the head
    of the queue fits (a 60 GB case at the head used to block every 8 GB case behind it). A head job that has waited
    RESERVE_H hours gets a reservation: nothing may pass it, so memory drains until it fits."""
    for k, j in enumerate(jobs):
        try: sp = json.load(open(j))
        except (OSError, ValueError): continue      # moved meanwhile (preflight -> queue/failed); one pass used to abort
        if not h24_preflight.valid(os.path.join(P, sp['case_dir'])): continue    # not (or no longer) preflight-checked
        if fits(sp): return j
        if k == 0 and time.time() - os.path.getmtime(j) > RESERVE_H * 3600: return None
    return None


def main():
    running = {}
    log('scheduler start')
    resume_orphans()
    while True:
      try:
        for name, p in list(running.items()):
            if p.poll() is not None:
                if p.returncode == 3 and os.path.exists(os.path.join(RUN, name + '.job')):   # not launched: back to the queue
                    os.replace(os.path.join(RUN, name + '.job'), os.path.join(Q, name + '.job'))
                    log(f'requeued {name} (no idle cores at launch)'); del running[name]; continue
                for ext in ('.job', '.out'):
                    src = os.path.join(RUN, name + ext)
                    if os.path.exists(src): os.replace(src, os.path.join(DONE, time.strftime('%H%M%S_') + name + ext))
                log(f'finished {name} exit={p.returncode}'); del running[name]
        reap_adopted(running)
        jobs = sorted(glob.glob(os.path.join(Q, '*.job')), key=os.path.getmtime)
        if jobs:
            st = gpu_state()
            b = cpu_busy(); c = claimed_cores(); free = sum(1 for k, v in b.items() if v < 0.10 and k not in c)
            for g in sorted(g for g, s in st.items() if s['idle']):           # GPU runs need idle cores too (h18)
                j = first_fit(jobs, lambda sp: not sp.get('cpu_only') and free >= sp.get('cores', 16)
                              and mem_free_gb() >= sp.get('host_mem_gb_gpu', 4) + 4)
                if j is None: break                                                    # cpu_only: too big for GPU memory
                jobs.remove(j); free -= json.load(open(j)).get('cores', 16)
                running[os.path.basename(j)[:-4]] = launch(j, g); time.sleep(20)
            if jobs:
                for _ in range(CPU_LAUNCH_MAX):            # several CPU launches per pass: fill an idle machine in minutes
                    j = first_fit(jobs, lambda sp: free >= sp.get('cores', 16) and mem_free_gb() >= sp.get('mem_gb', 8) + 4)
                    if j is None: break
                    jobs.remove(j); free -= json.load(open(j)).get('cores', 16)
                    running[os.path.basename(j)[:-4]] = launch(j); time.sleep(20)
      except Exception:                     # never die: a crash used to take the launched runs with it
        import traceback; log('ERROR ' + traceback.format_exc().replace('\n', ' | '))
      time.sleep(60)


if __name__ == '__main__':
    main()
