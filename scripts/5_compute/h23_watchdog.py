"""Keep the pipeline moving unattended (PI 2026-10-21: never let simulations or progress stall; keep checking for idle resources).

Every 5 min:
  1. restarts gpu_sampler / h19 scheduler / h24 preflight daemon / h22 AL loop in their tmux sessions if their process is gone;
  2. re-queues AL and physio pre-run jobs (al_*, physv3_*, physfix_*) that left queue/running without FEBio terminating (no 'N O R M A L' / 'E R R O R' in any case.log,
     e.g. a runner that died at launch) and are neither queued nor running again; at most MAX_RETRY times per job.
The scheduler itself polls for idle GPUs / CPU cores every 60 s.  Log: human_study/watchdog.log.
usage: python h23_watchdog.py
"""
import os, sys, re, time, json, glob, shutil, subprocess
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
from h06_run_cpu_batch import P

Q = os.path.join(P, 'human_study/queue'); LOG = os.path.join(P, 'human_study/watchdog.log')
RETRY = os.path.join(P, 'human_study/watchdog_retries.json'); MAX_RETRY, PERIOD = 5, 300
DAEMONS = [   # (tmux session, process pattern, command run from P)
    ('biocage_gpusamp', 'gpu_sampler.py', 'python scripts/5_compute/gpu_sampler.py human_study/gpu_samples.csv'),
    ('biocage_sched', 'h19_scheduler.py', 'python scripts/5_compute/h19_scheduler.py 2>> human_study/scheduler.err'),
    ('biocage_preflight', 'h24_preflight.py --daemon',
     'python scripts/5_compute/h24_preflight.py --daemon 2>> human_study/preflight.err'),
    ('biocage_al_loop', 'h22_active_learning.py loop',
     'python scripts/6_active_learning/h22_active_learning.py loop >> human_study/al/loop.out 2>&1'),
]


def log(msg):
    with open(LOG, 'a') as f: f.write(time.strftime('%m-%d %H:%M:%S ') + msg + '\n')


def alive(pattern):
    return subprocess.run(['pgrep', '-u', str(os.getuid()), '-f', pattern], capture_output=True).returncode == 0


def ensure_daemons():
    for sess, pat, cmd in DAEMONS:
        if alive(pat): continue
        subprocess.run(['tmux', 'kill-session', '-t', sess], capture_output=True)
        subprocess.run(['tmux', 'new-session', '-d', '-s', sess, f"cd '{P}' && {cmd}"])
        log(f'restarted {sess}')


def terminated(case):
    for d in [os.path.join(P, case)] + glob.glob(os.path.join(P, case) + '_gpu*'):
        lg = os.path.join(d, 'case.log')
        if os.path.exists(lg) and any(k in open(lg, errors='ignore').read()[-4000:] for k in ('N O R M A L', 'E R R O R')):
            return True
    return False


def requeue_failed():
    last = {}
    for l in open(os.path.join(P, 'human_study/scheduler.log'), errors='ignore'):
        m = re.search(r'finished (\S+) exit=(\S+)', l)
        if m: last[m.group(1)] = m.group(2)
    busy = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(Q, '*.job')) + glob.glob(os.path.join(Q, 'running', '*.job'))}
    tries = json.load(open(RETRY)) if os.path.exists(RETRY) else {}
    for name, ex in last.items():
        # exit 0 without a termination line = FEBio killed (e.g. OOM) but the wrapper exited cleanly (2026-10-25; v2 only)
        if not name.startswith(('al_', 'physv3_', 'physfix_')) or (ex == '0' and name.startswith('al_') and not name.startswith('al_v2')) or name in busy or tries.get(name, 0) >= MAX_RETRY: continue
        js = sorted(glob.glob(os.path.join(Q, 'done', f'*_{name}.job')))
        if not js or terminated(json.load(open(js[-1]))['case_dir']): continue
        shutil.copy(js[-1], os.path.join(Q, name + '.job')); tries[name] = tries.get(name, 0) + 1
        log(f'requeued {name} (exit={ex}, FEBio never terminated; try {tries[name]})')
    json.dump(tries, open(RETRY, 'w'))


STALL = os.path.join(P, 'human_study/watchdog_stall.json'); STALL_MIN, STALL_DT = 45, 0.005


def stop_stalled():
    """2026-10-23: a run whose simulated time advanced < STALL_DT within STALL_MIN minutes is stopped and its log is closed
    with an ERROR TERMINATION line (as FEBio would after max retries), so the AL treats it like any other stop (a test
    stopped after its endpoint is truncated there; a stop before t 3 makes the point 'invalid'). Auto-stepping lets some runs
    crawl for hours in retry loops while holding a memory slot."""
    try: hist = json.load(open(STALL))
    except (OSError, ValueError): hist = {}
    now = time.time(); seen = {}
    for pid in subprocess.run(['pgrep', '-u', str(os.getuid()), 'febio4'], capture_output=True, text=True).stdout.split():
        try: cwd = os.readlink(f'/proc/{pid}/cwd')
        except OSError: continue
        lg = os.path.join(cwd, 'case.log')
        if not os.path.exists(lg): continue
        with open(lg, 'rb') as fh:
            fh.seek(max(0, os.path.getsize(lg) - 200000)); tail = fh.read().decode(errors='ignore')
        m = re.findall(r'beginning time step \d+ : ([0-9.e+-]+)', tail)
        if not m: continue
        t = max(float(v) for v in m); h = hist.get(cwd)
        if h is None or t > h['t'] + STALL_DT: h = dict(t=t, since=now)
        seen[cwd] = h
        if now - h['since'] > STALL_MIN * 60:
            subprocess.run(['kill', pid])
            with open(lg, 'a') as fh: fh.write(f'\n\n E R R O R   T E R M I N A T I O N   (watchdog: stalled at t {t:.4f} for {STALL_MIN} min)\n')
            log(f'stopped stalled run {os.path.relpath(cwd, P)} at t {t:.4f}'); seen.pop(cwd)
    json.dump(seen, open(STALL, 'w'))


if __name__ == '__main__':
    log('watchdog start')
    while True:
        try:
            ensure_daemons(); requeue_failed(); stop_stalled()
        except Exception:
            import traceback; log('ERROR ' + traceback.format_exc().replace('\n', ' | '))
        time.sleep(PERIOD)
