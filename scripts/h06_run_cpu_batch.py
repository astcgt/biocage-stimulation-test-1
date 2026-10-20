"""Run a batch of FEBio cases on idle CPU cores (16 pinned cores per case, every idle core usable).

Idle cores are found from two /proc/stat samples; each case is pinned with taskset to its own 16 least-busy cores.
Writes <batch_dir>/resources.json (wall time, core-hours, per-case status) when all cases finish.
usage: python h06_run_cpu_batch.py [--cores N] <batch_dir> <case1> [<case2> ...]   (each case dir holds one .feb)
"""
import sys, os, time, json, glob, subprocess

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEBIO = os.path.join(P, 'third_party/FEBio/cbuild/bin/febio4')
LIBS = os.path.join(P, 'third_party/mkl/lib')
CORES_PER_CASE, RESERVE = 16, 0   # PI 2026-10-20: no reserved cores, use every idle core


def cpu_busy(dt=3.0):
    def snap():
        out = {}
        for line in open('/proc/stat'):
            if line.startswith('cpu') and line[3].isdigit():
                f = line.split(); v = list(map(int, f[1:]))
                out[int(f[0][3:])] = (sum(v), v[3] + v[4])
        return out
    a = snap(); time.sleep(dt); b = snap()
    return {c: 1 - (b[c][1] - a[c][1]) / max(1, b[c][0] - a[c][0]) for c in a}


def claimed_cores():
    """Cores pinned to this user's running FEBio processes (a just-started run is not yet visible as busy load)."""
    out = set()
    for p in os.listdir('/proc'):
        if not p.isdigit(): continue
        try:
            if os.stat(f'/proc/{p}').st_uid != os.getuid(): continue
            if b'febio4' not in open(f'/proc/{p}/cmdline', 'rb').read(): continue
            aff = os.sched_getaffinity(int(p))
            if len(aff) < os.cpu_count(): out |= aff
        except (OSError, ProcessLookupError):
            pass
    return out


def main():
    global CORES_PER_CASE
    args = sys.argv[1:]
    if args[0] == '--cores':
        CORES_PER_CASE = int(args[1]); args = args[2:]
    batch, cases = args[0], args[1:]
    import fcntl
    lock = open(os.path.join(P, 'human_study', '.cpu_launch.lock'), 'w')
    fcntl.flock(lock, fcntl.LOCK_EX)          # serialise core selection across concurrent runners
    busy = cpu_busy()
    idle = sorted(busy, key=busy.get)
    usable = idle[:max(0, len(idle) - RESERVE)]
    usable = [c for c in usable if busy[c] < 0.10 and c not in claimed_cores()]
    n = min(len(cases), len(usable) // CORES_PER_CASE)
    if n < len(cases):
        print(f'only {n} of {len(cases)} cases fit on idle cores now; running those', flush=True)
    if n == 0:
        fcntl.flock(lock, fcntl.LOCK_UN); sys.exit(3)          # nothing launched (scheduler re-queues on exit 3)
    t0 = time.time(); procs = {}
    for k, case in enumerate(cases[:n]):
        cores = sorted(usable[k * CORES_PER_CASE:(k + 1) * CORES_PER_CASE])
        d = os.path.join(batch, case); feb = os.path.basename(glob.glob(os.path.join(d, '*.feb'))[0])
        env = dict(os.environ, OMP_NUM_THREADS=str(CORES_PER_CASE), MKL_NUM_THREADS=str(CORES_PER_CASE),
                   LD_LIBRARY_PATH=LIBS, KMP_STACKSIZE='1G', OMP_STACKSIZE='1G')
        cmd = ['prlimit', '--stack=unlimited', 'taskset', '-c', ','.join(map(str, cores)), FEBIO, '-i', feb, '-silent']
        open(os.path.join(d, 'started_at'), 'w').write(str(time.time()))
        procs[case] = (subprocess.Popen(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT),
                       time.time(), cores)
        print(f'started {case} on cores {cores[0]}..{cores[-1]}', flush=True)
    time.sleep(2); fcntl.flock(lock, fcntl.LOCK_UN)
    res = {}
    while procs:
        for case, (p, ts, cores) in list(procs.items()):
            if p.poll() is not None:
                log = glob.glob(os.path.join(batch, case, '*.log'))
                txt = open(log[0]).read() if log else ''
                res[case] = dict(exit=p.returncode, normal='N O R M A L' in txt, wall_s=round(time.time() - ts, 1),
                                 cores=len(cores), core_h=round(len(cores) * (time.time() - ts) / 3600, 3))
                print(f'finished {case}: {res[case]}', flush=True)
                del procs[case]
        time.sleep(10)
    summary = dict(cases=res, batch_wall_s=round(time.time() - t0, 1),
                   total_core_h=round(sum(r['core_h'] for r in res.values()), 3), gpu_h=0.0,
                   not_run=cases[n:])
    json.dump(summary, open(os.path.join(batch, 'resources.json'), 'w'), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
