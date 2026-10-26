"""Summary of the physiological-load test (physio, PI 2026-10-23) over the v2 AL points that have one.

Post-processes every ended physio run (h15, in parallel) and tabulates per point: how far the protocol got (follower load,
six moment windows), C3 rotation at each peak moment, min anti-slip SF at mu 0.2, max CoP eccentricity, max cage slip,
plus the point's design factors and compression capacity. Writes human_study/al_v2/physio_analysis/{cases.json, report.md}.
usage: python h27_physio_summary.py
"""
import os, sys, re, json, subprocess, collections
import numpy as np
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(P, 'scripts/6_active_learning'))
import h22_active_learning as al

OUT = os.path.join(al.AL, 'physio_analysis'); MU_WORST, MU_SIM = al.MU_WORST, al.MU_SIM


def post(d):
    if not os.path.exists(os.path.join(d, 'summary.json')) or os.path.getmtime(os.path.join(d, 'summary.json')) < os.path.getmtime(os.path.join(d, 'case.log')):
        subprocess.run(['python', os.path.join(P, 'scripts/4_postprocess/h15_post_case.py'), d], cwd=P, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: return json.load(open(os.path.join(d, 'summary.json')))
    except (OSError, ValueError): return None


def main():
    st = al.load(); rows = []
    jobs = [(p, al.ended_dir(os.path.relpath(os.path.join(al.AL, 'cases', f"p{p['id']:03d}_physio"), P))) for p in st['points']]
    jobs = [(p, d) for p, d in jobs if d]
    with ThreadPoolExecutor(2) as ex:                # 8 parallel h15 runs (xplt loading) caused 2 OOM kills under the 128 GB cap
        sums = list(ex.map(lambda t: post(t[1]), jobs))
    for (p, d), s in zip(jobs, sums):
        if not s: continue
        txt = open(os.path.join(d, 'case.log'), errors='ignore').read()
        m = re.findall(r'beginning time step \d+ : ([0-9.e+-]+)', txt); t_end = max(float(v) for v in m) if m else 0.0
        w = s.get('physio_windows', [])
        rows.append(dict(id=p['id'], x=p['x'], dir=os.path.relpath(d, P), t_end=t_end, n_complete=sum(1 for v in w if v['complete']),
                         windows=[dict(v, min_sf_mu02=(v['min_sf'] * MU_WORST / MU_SIM if v.get('min_sf') is not None else None)) for v in w],
                         C=(p.get('res') or {}).get('C'), clamp=s.get('clamp_after_release_N')))
    os.makedirs(OUT, exist_ok=True); json.dump(rows, open(os.path.join(OUT, 'cases.json'), 'w'), indent=1)
    L = [f'# Physiological-load test (v2), {len(rows)} ended runs\n',
         'Windows completed (of 6): ' + ', '.join(f'{k}: {v}' for k, v in sorted(collections.Counter(r['n_complete'] for r in rows).items()))]
    names = ['flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right']
    for f in ('design', 'grad', 'fab'):
        g = collections.defaultdict(list)
        for r in rows: g[r['x'][f]].append(r['n_complete'])
        L.append(f'- windows completed by {f}: ' + ', '.join(f'{k} {np.mean(v):.2f} (n {len(v)})' for k, v in g.items()))
    L.append('\n| id | design | grad | fab | d | windows done | ' + ' | '.join(f'{n} ROM deg / SF0.2' for n in names) + ' | C N |')
    L.append('|' + '---|' * (7 + len(names)))
    for r in sorted(rows, key=lambda r: (-r['n_complete'], -r['t_end'])):
        x = r['x']; byn = {v['name']: v for v in r['windows']}
        cells = []
        for n in names:
            v = byn.get(n)
            cells.append('-' if not v or v.get('rom_deg') is None else
                         f"{v['rom_deg']:+.2f} / " + (f"{v['min_sf_mu02']:.2f}" if v.get('min_sf_mu02') is not None else '-'))
        L.append(f"| {r['id']} | {x['design']} | {x['grad']} | {x['fab']} | {x['d']:.2f} | {r['n_complete']} | " + ' | '.join(cells)
                 + f" | {r['C'] if r['C'] is None else round(r['C'])} |")
    open(os.path.join(OUT, 'report.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    main()
