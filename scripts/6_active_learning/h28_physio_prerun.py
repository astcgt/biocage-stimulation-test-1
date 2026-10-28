"""Physio test (fixed load curves, 2026-10-26) for every finished v2 AL point: build, preflight, queue.

The physio runs before 2026-10-26 had combined loading (h14 bug, al_v2/PHYSIO_INVALID_2026-10-26.md). Each finished point's
compress case parameters are reused with test = 'physio'; cases go to human_study/al_v2/physio_v3/pXXX (settings class
'human_study/al_v2/physio_v3/' = physio_test class). Already built / queued / finished cases are skipped, so the script can be
re-run at any time (e.g. after a server restart).
usage: python h28_physio_prerun.py [workers] [test] [out_subdir] [job_prefix] [ids]
  default: physio, al_v2/physio_v3, physv3_ ; 2026-10-28 rotation control: physio_rot al_v2/physio_rot physrot_ [p062,p001]
"""
import os, sys, json, subprocess
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE))
TEST = sys.argv[2] if len(sys.argv) > 2 else 'physio'
OUT = os.path.join(P, 'human_study', sys.argv[3] if len(sys.argv) > 3 else 'al_v2/physio_v3'); QUEUE = os.path.join(P, 'human_study/queue')
PREFIX = sys.argv[4] if len(sys.argv) > 4 else 'physv3_'
ONLY = set(sys.argv[5].split(',')) if len(sys.argv) > 5 else None
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py'); H24 = os.path.join(P, 'scripts/5_compute/h24_preflight.py')


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
