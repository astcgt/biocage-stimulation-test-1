"""Hybrid GPU + CPU scheduler for queued FEBio cases (PI 2026-10-20: grab every idle resource, no reserve).

Queue: human_study/queue/*.job (JSON {"case_dir": ..., "cores": 16, "cpu_only": false, "mem_gb": 8, "host_mem_gb_gpu": 4});
oldest first. A job starts only if the account cgroup memory headroom covers its estimate + 4 GB. A job moves to queue/running/ when
launched and to queue/done/ when its process exits.
Every 60 s:
  GPU g (all GPUs on the node) is idle when its last IDLE_MIN one-minute samples in human_study/gpu_samples.csv
  (written by gpu_sampler.py) average < 10 % utilisation, it has >= MEM_NEED_MB free now and none of my runs is on it
  (one worker per GPU). An idle GPU takes the next job via h18_run_gpu_case.py (cuDSS + idle CPU cores).
  If no GPU is idle but >= 16 idle unclaimed cores exist, the next job runs on CPU via h06_run_cpu_batch.py.
Log: human_study/scheduler.log.   usage: python h19_scheduler.py
"""
import os, sys, time, json, glob, csv, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import cpu_busy, claimed_cores, P

IDLE_MIN, UTIL_MAX, MEM_NEED_MB = 15, 10.0, int(1.5 * 7000)   # cage case peak ~7 GB on GPU (measured 2026-10-20)
Q = os.path.join(P, 'human_study/queue'); RUN = os.path.join(Q, 'running'); DONE = os.path.join(Q, 'done')
SAMPLES = os.path.join(P, 'human_study/gpu_samples.csv'); LOG = os.path.join(P, 'human_study/scheduler.log')
for d in (Q, RUN, DONE): os.makedirs(d, exist_ok=True)


CG = '/sys/fs/cgroup' + open('/proc/self/cgroup').read().strip().split(':')[-1]


def mem_free_gb():
    """Headroom under this account's cgroup memory limit (64 GiB on this server; found 2026-10-20 after an OOM kill)."""
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
        capture_output=True, text=True).stdout.strip().splitlines())}
    uuid = dict(l.split(', ') for l in subprocess.run(['nvidia-smi', '--query-gpu=uuid,index', '--format=csv,noheader'],
                                                      capture_output=True, text=True).stdout.strip().splitlines())
    mine = set()
    for l in subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'],
                            capture_output=True, text=True).stdout.strip().splitlines():
        u, pid = l.split(', ')
        try:
            if os.stat(f'/proc/{pid}').st_uid == os.getuid(): mine.add(int(uuid[u]))
        except OSError: pass
    out = {}
    for g, (util, used, tot) in now.items():
        hist = [int(r[2]) for r in rows if int(r[1]) == g][-IDLE_MIN:]
        idle = len(hist) >= IDLE_MIN and sum(hist) / len(hist) < UTIL_MAX and tot - used >= MEM_NEED_MB and g not in mine
        out[g] = dict(idle=idle, mean_util=round(sum(hist) / max(1, len(hist)), 1), free_mb=tot - used, mine=g in mine)
    return out


def launch(job, gpu=None):
    spec = json.load(open(job)); name = os.path.basename(job)[:-4]; case = spec['case_dir']; cores = spec.get('cores', 16)
    if gpu is not None:
        cmd = ['python', 'scripts/h18_run_gpu_case.py', str(gpu), case, str(cores)]
    else:
        cmd = ['python', 'scripts/h06_run_cpu_batch.py', '--cores', str(cores), os.path.dirname(case.rstrip('/')),
               os.path.basename(case.rstrip('/'))]
    out = open(os.path.join(RUN, name + '.out'), 'w')
    p = subprocess.Popen(cmd, cwd=P, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)   # survive scheduler restarts
    shutil.move(job, os.path.join(RUN, name + '.job'))
    log(f'launch {name} on ' + (f'GPU {gpu}' if gpu is not None else 'CPU') + f' ({cores} cores)')
    return p


def main():
    running = {}
    log('scheduler start')
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
        jobs = sorted(glob.glob(os.path.join(Q, '*.job')), key=os.path.getmtime)
        if jobs:
            st = gpu_state()
            for g in sorted(g for g, s in st.items() if s['idle']):
                gj = [j for j in jobs if not json.load(open(j)).get('cpu_only')]       # cpu_only: too big for GPU memory
                if not gj: break
                if mem_free_gb() < json.load(open(gj[0])).get('host_mem_gb_gpu', 4) + 4: break   # host-RAM headroom
                jobs.remove(gj[0]); running[os.path.basename(gj[0])[:-4]] = launch(gj[0], g); time.sleep(20)
            if jobs:
                b = cpu_busy(); c = claimed_cores(); free = sum(1 for k, v in b.items() if v < 0.10 and k not in c)
                spec = json.load(open(jobs[0]))
                if free >= spec.get('cores', 16) and mem_free_gb() >= spec.get('mem_gb', 8) + 4:
                    j = jobs.pop(0); running[os.path.basename(j)[:-4]] = launch(j); time.sleep(20)
      except Exception:                     # never die: a crash used to take the launched runs with it
        import traceback; log('ERROR ' + traceback.format_exc().replace('\n', ' | '))
      time.sleep(60)


if __name__ == '__main__':
    main()
