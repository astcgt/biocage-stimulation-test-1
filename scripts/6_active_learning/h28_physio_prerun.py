"""Physio test (fixed load curves, 2026-10-26) for every finished v2 AL point: build, preflight, queue.

The physio runs before 2026-10-26 had combined loading (h14 bug, al_v2/PHYSIO_INVALID_2026-10-26.md). Each finished point's
compress case parameters are reused with test = 'physio'; cases go to human_study/al_v2/physio_v3/pXXX (settings class
'human_study/al_v2/physio_v3/' = physio_test class). Already built / queued / finished cases are skipped, so the script can be
re-run at any time (e.g. after a server restart).
usage: python h28_physio_prerun.py [workers] [test] [out_subdir] [job_prefix] [ids|all] [prev_subdir|-] [overrides json]
  default: physio, al_v2/physio_v3, physv3_ ; 2026-10-28 rotation control: physio_rot al_v2/physio_rot physrot_ [p062,p001]
  2026-10-29 second pass: physio_rot al_v2/physio_rot_r2 physrot2_ all al_v2/physio_rot (windows below target, larger amplitude)
"""
import os, sys, json, glob, subprocess
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE))
TEST = sys.argv[2] if len(sys.argv) > 2 else 'physio'
OUT = os.path.join(P, 'human_study', sys.argv[3] if len(sys.argv) > 3 else 'al_v2/physio_v3'); QUEUE = os.path.join(P, 'human_study/queue')
PREFIX = sys.argv[4] if len(sys.argv) > 4 else 'physv3_'
ONLY = set(sys.argv[5].split(',')) if len(sys.argv) > 5 and sys.argv[5] != 'all' else None
PREV = os.path.join(P, 'human_study', sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != '-' else None   # physio_rot second pass
EXTRA = json.loads(sys.argv[7]) if len(sys.argv) > 7 else {}       # parameter overrides (e.g. facet sensitivity)
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py'); H24 = os.path.join(P, 'scripts/5_compute/h24_preflight.py')


INTACT = dict(flexion=0.1009, extension=0.1286, LB_right=0.0713, LB_left=0.0717, AR_left=0.0905, AR_right=0.0907)  # rad at 1.5 N m
RATIO_MED = dict(flexion=0.38, extension=0.28, LB_right=0.30, LB_left=0.30, AR_left=0.33, AR_right=0.33)  # cage / intact, physio_v3


def rot_targets(name):
    """physio_rot (2026-10-28): per-window rotation amplitude for this design. Driving to the intact ROM overshot 1.5 N m
    ~3x (cage ROM = 0.25-0.71 x intact) and inverted cage elements (p001). Use 1.15 x the rotation this design reached at
    the moment-control peak (physio_v3 C3pot.txt, absolute rotation), else 1.4 x the median cage / intact ratio x intact."""
    ax = dict(flexion=5, extension=5, LB_right=4, LB_left=4, AR_left=6, AR_right=6)   # id, x, y, z, thx, thy, thz
    out = {k: 1.4 * RATIO_MED[k] * INTACT[k] for k in INTACT}
    v3 = os.path.join(P, 'human_study/al_v2/physio_v3')
    for d in sorted(glob.glob(os.path.join(v3, name)) + glob.glob(os.path.join(v3, name + '_gpu*'))):
        f, sf = os.path.join(d, 'C3pot.txt'), os.path.join(d, 'physio_schedule.json')
        if not (os.path.exists(f) and os.path.exists(sf)): continue
        rows, t = {}, None
        for line in open(f):
            if line.startswith('*Time'): t = float(line.split('=')[1])
            elif line[:1].isdigit(): rows[t] = [float(a) for a in line.split(',')]
        for w in json.load(open(sf))['windows']:
            ts = [x for x in rows if w['t0'] - 1e-6 <= x <= w['t_peak'] + 0.03]
            if ts and max(ts) >= w['t_peak'] - 0.03:
                out[w['name']] = 1.15 * abs(rows[min(ts, key=lambda x: abs(x - w['t_peak']))][ax[w['name']]])
    return out


def rot_retarget(name, prev, base):
    """second pass (2026-10-29): windows whose driving moment stayed below the target in the previous physio_rot run of this
    design (al_v2/physio_rot) get a larger amplitude, extrapolated with the tangent of the moment-rotation curve at the last
    up-ramp point (the curve stiffens, so this undershoots less than a secant and overshoots little) x 1.15; windows that
    reached the target, or have no data (run stopped earlier), keep their amplitude."""
    out = dict(base); col = dict(Rx=4, Ry=5, Rz=6)
    def drive(df):
        rows, t = [], None
        for line in open(df):
            if line.startswith('*Time'): t = float(line.split('=')[1]); rows.append((t, {}))
            elif line[:1].isdigit() and t is not None: v = line.split(','); rows[-1][1][int(v[0])] = [float(a) for a in v]
        return rows
    for d in sorted(glob.glob(os.path.join(prev, name)) + glob.glob(os.path.join(prev, name + '_gpu*'))):
        sf = os.path.join(d, 'physio_schedule.json')
        if not os.path.exists(sf): continue
        sch = json.load(open(sf)); amp = sch['rot_rad']; Mt = sch['target_moment_Nmm']
        if os.path.exists(os.path.join(d, 'split.json')):      # split run (h30): one restart per window, joint 1, its own schedule
            curves = []
            for w in sch['windows']:
                wd = os.path.join(d, 'w_' + w['name']); wsf, wdf = os.path.join(wd, 'physio_schedule.json'), os.path.join(wd, 'drive.txt')
                if not (os.path.exists(wsf) and os.path.exists(wdf)): curves.append((w, [])); continue
                ww = json.load(open(wsf))['windows'][0]
                curves.append((ww, [(amp[w['name']] * (tt - ww['t0']) / (ww['t_peak'] - ww['t0']), abs(dd[1][col[ww['dof']]]))
                                    for tt, dd in drive(wdf) if 1 in dd and ww['t0'] + 1e-9 < tt <= ww['t_peak'] + 1e-9]))
        else:
            df = os.path.join(d, 'drive.txt')
            if not os.path.exists(df): continue
            rows = drive(df)
            curves = [(w, [(amp[w['name']] * (tt - w['t0']) / (w['t_peak'] - w['t0']), abs(dd[i + 1][col[w['dof']]]))
                           for tt, dd in rows if (i + 1) in dd and w['t0'] + 1e-9 < tt <= w['t_peak'] + 1e-9]) for i, w in enumerate(sch['windows'])]
        for w, up in curves:
            if not up or any(m >= Mt for _, m in up): out[w['name']] = amp[w['name']]; continue
            if max(th for th, _ in up) < 0.95 * amp[w['name']]: out[w['name']] = amp[w['name']]; continue   # stopped inside the ramp
            (t1, m1), (t2, m2) = up[-2], up[-1]; k = (m2 - m1) / (t2 - t1) if len(up) > 1 and t2 > t1 else 0
            new = t2 + 1.15 * (Mt - m2) / k if k > 0 else 2.0 * amp[w['name']]
            out[w['name']] = min(max(new, 1.1 * amp[w['name']]), 2.5 * amp[w['name']])
        break
    return out


def queued_or_done(name):
    for sub in ('', 'running', 'done'):
        d = os.path.join(QUEUE, sub)
        if os.path.isdir(d) and any(f.endswith(name + '.job') for f in os.listdir(d)): return True
    return False


def one(pid):
    name = f'p{pid:03d}'; cd = os.path.join(OUT, name); job = f'{PREFIX}{name}'
    if queued_or_done(job): return name, 'skip (queued / done)'
    src = os.path.join(P, f'human_study/al_v2/cases/{name}_compress_params.json')
    if not os.path.exists(src): return name, 'skip (no compress params)'
    prm = json.load(open(src)); prm['test'] = TEST
    cur = json.load(open(os.path.join(P, 'human_study/current_settings.json')))   # current study settings win (older points
    prm.update(cur['common']); prm.update(cur['classes'][os.path.relpath(OUT, P) + '/'])   # lack e.g. insert_dt)
    if TEST == 'physio_rot':
        prm['physio_rot_rad'] = rot_targets(name)
        if PREV: prm['physio_rot_rad'] = rot_retarget(name, PREV, prm['physio_rot_rad'])
    prm.update(EXTRA)
    pj = os.path.join(OUT, f'{name}_params.json'); json.dump(prm, open(pj, 'w'), indent=1)
    for attempt in (0, 1):
        if attempt or not os.path.exists(os.path.join(cd, 'case.feb')):
            r = subprocess.run(['python', H14, pj, cd], cwd=P, capture_output=True, text=True)
            if r.returncode: return name, 'build failed: ' + r.stderr[-300:]
        r = subprocess.run(['python', H24, cd], cwd=P, capture_output=True, text=True)
        if 'OK' in r.stdout: break
    else:
        return name, 'preflight failed: ' + (r.stdout + r.stderr)[-300:]
    json.dump(dict(case_dir=os.path.relpath(cd, P), cores=4, mem_gb=4, host_mem_gb_gpu=3), open(os.path.join(QUEUE, job + '.job'), 'w'))
    return name, 'queued'


def main():
    os.makedirs(OUT, exist_ok=True)
    pts = json.load(open(os.path.join(P, 'human_study/al_v2/points.json')))['points']
    ids = [p['id'] for p in pts if p.get('status') == 'done' and (ONLY is None or f"p{p['id']:03d}" in ONLY)]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 8) as ex:
        for name, msg in ex.map(one, ids): print(name, msg, flush=True)


if __name__ == '__main__':
    main()
