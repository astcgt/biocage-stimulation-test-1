"""One-line progress report for the human C3-C4 study (used for the hourly notification).

Running FEBio cases: progress = simulated time / end time of each case's .feb, ETA from the rate since the log was
created. Project progress: weighted steps from human_study/status.json (edited as steps complete).
usage: python progress_report.py [--json]
"""
import os, re, sys, glob, time, json
import xml.etree.ElementTree as ET

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(P, 'human_study', 'status.json')


def case_progress(d):
    feb = glob.glob(os.path.join(d, '*.feb')); log = glob.glob(os.path.join(d, '*.log'))
    if not feb or not log:
        return None
    r = ET.parse(feb[0]).getroot()
    ctrls = [r.find('Control')] if r.find('Control') is not None else [s.find('Control') for s in r.findall('Step')]
    t_end = sum(int(c.find('time_steps').text) * float(c.find('step_size').text) for c in ctrls)
    txt = open(log[0], errors='ignore').read()
    done = 'N O R M A L' in txt or 'E R R O R   T E R M' in txt
    ts = re.findall(r'beginning time step \d+ : ([0-9.eE+-]+)', txt)
    t = float(ts[-1]) if ts else 0.0
    frac = 1.0 if done else min(t / t_end, 0.999)
    st = os.path.join(d, 'started_at')                       # written by the batch runner at launch
    t0 = float(open(st).read()) if os.path.exists(st) else os.path.getmtime(feb[0])
    age = time.time() - t0; age_end = os.path.getmtime(log[0]) - t0
    eta = 0 if done else (age * (1 - frac) / frac if frac > 0.02 else None)
    return dict(frac=frac, done=done, failed='E R R O R   T E R M' in txt, eta_s=eta, elapsed_s=age_end if done else age)


def main():
    runs = {}
    for d in glob.glob(os.path.join(P, 'human_study', '**', 'runs', '*'), recursive=True) + glob.glob(os.path.join(P, 'human_study', '**', 'case_*'), recursive=True):
        if os.path.isdir(d):
            p = case_progress(d)
            if p: runs[os.path.relpath(d, os.path.join(P, 'human_study'))] = p
    active = {k: v for k, v in runs.items() if not v['done']}
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    steps = st.get('steps', [])
    tot = sum(s['weight'] for s in steps) or 1
    proj = sum(s['weight'] * s.get('done_frac', 0) for s in steps) / tot
    cur = next((s for s in steps if s.get('done_frac', 0) < 1), None)
    if active:
        bf = sum(v['frac'] for v in active.values()) / len(active)
        etas = [v['eta_s'] for v in active.values() if v['eta_s'] is not None]
        eta = f'{max(etas) / 60:.0f} min' if etas else 'n/a'
        run_txt = f'{len(active)} runs {bf * 100:.0f}% (ETA {eta})'
    else:
        run_txt = 'no runs active'
    left = st.get('project_eta', '?')
    msg = (f'BIOCAGE project {proj * 100:.0f}% | now: {cur["name"] if cur else "done"} | {run_txt} | '
           f'project ETA ~{left}')
    if '--json' in sys.argv:
        print(json.dumps(dict(message=msg, runs=runs, project_frac=proj), indent=1))
    else:
        print(msg[:200])


if __name__ == '__main__':
    main()
