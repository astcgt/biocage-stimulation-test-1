"""Stop push-out runs once the push-out force is known (frees resources; the remaining push adds nothing to the endpoint).

Every 60 s for each case dir given: push force F(d) = |sum of prescribed-node X reactions| (as h15). A run is stopped
(scripts/kill_febio.sh) and post-processed with h15 when
  expelled : d >= d_peak + 0.3 mm and F <= 0.5 * F_peak (force has peaked and dropped -> cage sliding out), or
  stalled  : FEBio time has not advanced for STALL_MIN minutes after the push started (stick-slip loop after the peak).
A note (stop_reason.json) is written in the case dir. Exits when all listed runs have ended.
usage: python h20_push_watch.py <case_dir> [<case_dir> ...]
"""
import os, sys, time, json, subprocess, numpy as np

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STALL_MIN, T_PUSH = 20, 3.2


def push_curve(cd):
    out, t = [], None
    try:
        for line in open(os.path.join(cd, 'push_reaction.txt')):
            if line.startswith('*Time'): t = float(line.split('=')[1])
            elif line[:1].isdigit(): out.append((t, float(line.split(',')[1])))
    except OSError:
        return None
    if not out: return None
    a = np.array(out); ts = np.unique(a[:, 0]); ts = ts[ts >= T_PUSH - 1e-6]
    if not len(ts): return None
    F = np.array([abs(a[a[:, 0] == tt, 1].sum()) for tt in ts])
    return ts, np.clip((ts - T_PUSH) / 1.0, 0, 1) * 3.0, F


def ended(cd):
    try: return any(k in open(os.path.join(cd, 'case.log'), errors='ignore').read()[-3000:] for k in ('N O R M A L', 'E R R O R'))
    except OSError: return False


cases = [c.rstrip('/') for c in sys.argv[1:]]; last = {c: (None, time.time()) for c in cases}
while cases:
    for c in list(cases):
        if ended(c): cases.remove(c); continue
        pc = push_curve(c)
        if pc is None: continue
        ts, d, F = pc; k = int(np.argmax(F)); reason = None
        if d[-1] >= d[k] + 0.3 and F[-1] <= 0.5 * F[k]: reason = 'expelled'
        if last[c][0] != ts[-1]: last[c] = (ts[-1], time.time())
        elif time.time() - last[c][1] > STALL_MIN * 60: reason = 'stalled'
        if reason:
            json.dump(dict(reason=reason, t=float(ts[-1]), push_mm=float(d[-1]), F_peak_N=float(F[k]), d_peak_mm=float(d[k]),
                           F_last_N=float(F[-1]), when=time.strftime('%Y-%m-%d %H:%M')), open(os.path.join(c, 'stop_reason.json'), 'w'), indent=1)
            subprocess.run([os.path.join(P, 'scripts/kill_febio.sh'), os.path.relpath(c, os.path.join(P, 'human_study'))])
            time.sleep(5); subprocess.run(['python', os.path.join(P, 'scripts/h15_post_case.py'), c], stdout=subprocess.DEVNULL)
            print(c, reason, flush=True); cases.remove(c)
    time.sleep(60)
