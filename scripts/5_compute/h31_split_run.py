"""Run a split physio_rot case (h30): the insertion run (case.feb, dumped at the end of each analysis step), then each
window as an independent FEBio restart from that end state (w_<name>/restart.feb), one after the other on the same cores.
A window that already terminated is skipped (resume after an interruption); a failed window does not stop the others.
Called by h06 / h18 (inside their taskset / GPU environment) when the case dir has split.json.
usage: python h31_split_run.py <case_dir> [extra FEBio args, e.g. -cnf <cudss.xml>]
A restart needs the same -cnf as the insertion run (the archive refers to the cuDSS solver plugin).
Integrity (2026-11-02, [觀測] OBS-05 / T13): after every window a w_<name>/window_check.json is written (FEBio exit code,
termination banner, converged steps, last time, negative-Jacobian count, static retry, drive.txt rows / shortest step /
moment reached), and <case>/split_check.json collects them; the post-processing refuses windows without valid states.
"""
import os, sys, json, glob, re, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import FEBIO, febio_args

d, extra = sys.argv[1], sys.argv[2:]
ended = lambda log: os.path.exists(log) and any(k in open(log, errors='ignore').read()[-4000:] for k in ('N O R M A L', 'E R R O R'))


def window_check(wd, rc):
    """facts about a finished window, from its log and drive.txt (no physics): -> dict, also written to window_check.json."""
    lg = open(os.path.join(wd, 'case.log'), errors='ignore').read() if os.path.exists(os.path.join(wd, 'case.log')) else ''
    conv = [float(v) for v in re.findall(r'converged at time : ([0-9.eE+-]+)', lg)]
    c = dict(exit=rc, banner='NORMAL' if 'N O R M A L' in lg[-4000:] else ('ERROR' if 'E R R O R' in lg[-4000:] else None),
             n_converged=len(conv), t_last=max(conv) if conv else None, n_negjac=lg.count('Negative jacobian was detected'),
             static_retry=os.path.exists(os.path.join(wd, 'case_dyn_fail.log')), drive_rows=0, dt_min=None, M_max_Nmm=None, target_reached=None)
    try:
        sch = json.load(open(os.path.join(wd, 'physio_schedule.json'))); w = sch['windows'][0]
        col = dict(Rx=4, Ry=5, Rz=6)[w['dof']]; t, tp, rows = None, w['t0'], []
        for line in open(os.path.join(wd, 'drive.txt')):
            if line.startswith('*Time'): t = float(line.split('=')[1])
            elif line.startswith('1,') and t is not None and w['t0'] < t <= w['t_peak'] + 1e-9: rows.append((t, t - tp, float(line.split(',')[col]))); tp = t
        # rigid-body dynamic residual per state (C3pot.txt Fx..Mz; NUM-14, same 2 % rule as biocage-evo e03.filter_rows): a
        # retried / chattering step's joint moment is off by the body's inertial moment residual and must not count as
        # "reached"; the force residual (off the follower load) is reported only
        rb, t, c3 = {}, None, os.path.join(wd, 'C3pot.txt')
        for line in (open(c3, errors='ignore') if os.path.exists(c3) else []):
            if line.startswith('*Time'): t = float(line.split('=')[1])
            elif line[:1].isdigit() and t is not None and w['t0'] < t <= w['t_peak'] + 1e-9:
                v = [float(a) for a in line.split(',')[7:13]]; rb[t] = ((v[3] ** 2 + v[4] ** 2 + v[5] ** 2) ** 0.5, (v[0] ** 2 + v[1] ** 2) ** 0.5, v[2])
        fz = sorted(v[2] for v in rb.values())[len(rb) // 2] if rb else None
        dyn = lambda tt: tt in rb and rb[tt][0] > 0.02 * sch['target_moment_Nmm']
        if rows:
            c.update(drive_rows=len(rows), dt_min=min(r[1] for r in rows), M_max_Nmm=max(abs(r[2]) for r in rows),
                     n_dyn=sum(bool(dyn(r[0])) for r in rows), rb_res_max_Nmm=max((rb[r[0]][0] for r in rows if r[0] in rb and not dyn(r[0])), default=None),
                     rb_fres_max_N=max((rb[r[0]][1] + abs(rb[r[0]][2] - fz) for r in rows if r[0] in rb), default=None) if fz is not None else None,
                     target_reached=any(abs(r[2]) >= sch['target_moment_Nmm'] and r[1] >= 1e-4 and not dyn(r[0]) for r in rows))
    except (OSError, ValueError, KeyError, IndexError) as e:
        c['drive_error'] = repr(e)
    json.dump(c, open(os.path.join(wd, 'window_check.json'), 'w'), indent=1)
    return c


if not ended(os.path.join(d, 'case.log')):
    fargs, _ = febio_args(d, 'case.feb')
    subprocess.run([FEBIO] + fargs + extra, cwd=d, stdout=subprocess.DEVNULL)
if 'N O R M A L' not in open(os.path.join(d, 'case.log'), errors='ignore').read()[-4000:]: sys.exit(1)   # insertion failed
checks = {}
for w in json.load(open(os.path.join(d, 'split.json')))['windows']:
    wd = os.path.join(d, 'w_' + w)
    if ended(os.path.join(wd, 'case.log')):
        cj = os.path.join(wd, 'window_check.json')
        checks[w] = json.load(open(cj)) if os.path.exists(cj) else window_check(wd, None); continue
    for f in os.listdir(wd):                                # outputs of an interrupted attempt (FEBio appends to them)
        if not f.endswith(('.feb', '.json', '.npz')): os.remove(os.path.join(wd, f))
    shutil.copy(os.path.join(d, 'case.xplt'), wd)           # the restart reopens the plot file named in the archive
    rc = subprocess.run([FEBIO, '-r', 'restart.feb', '-o', 'case.log', '-silent', '-output_negative_jacobians=50'] + extra,
                        cwd=wd, stdout=subprocess.DEVNULL).returncode
    # dynamic window that failed before its first converged step (seen in flexion/extension, 2026-10-31): one static retry
    lg = open(os.path.join(wd, 'case.log'), errors='ignore').read()
    if 'E R R O R' in lg[-4000:] and 'converged at time' not in lg and 'type="dynamic"' in open(os.path.join(wd, 'restart.feb')).read():
        os.rename(os.path.join(wd, 'case.log'), os.path.join(wd, 'case_dyn_fail.log'))
        rs = open(os.path.join(wd, 'restart.feb')).read().replace('<analysis type="dynamic" />', '<analysis type="static" />')
        open(os.path.join(wd, 'restart_static.feb'), 'w').write(rs)
        for f in os.listdir(wd):
            if f.endswith(('.xplt', '.txt')): os.remove(os.path.join(wd, f))
        shutil.copy(os.path.join(d, 'case.xplt'), wd)
        rc = subprocess.run([FEBIO, '-r', 'restart_static.feb', '-o', 'case.log', '-silent', '-output_negative_jacobians=50'] + extra,
                            cwd=wd, stdout=subprocess.DEVNULL).returncode
    checks[w] = window_check(wd, rc)
json.dump(dict(windows=checks, n_error=sum(c['banner'] != 'NORMAL' for c in checks.values()),
               n_below_target=sum(not c.get('target_reached') for c in checks.values())),
          open(os.path.join(d, 'split_check.json'), 'w'), indent=1)
