"""Why do ISO runs stop at the very start of the protocol? (PI 2026-10-23: analyse automatically once enough v2 ISO runs end.)

For every terminated ISO case of the v2 active learning (human_study/al_v2): phase and time of the stop, ISO completion,
clamp after release, C3-pot rotations / moments at the stop, inverted elements by tissue / material (FEBio
-output_negative_jacobians in the log; runs started before 2026-10-23 04:40 lack it), soft-layer compression at the last
converged state, and the design / material inputs. Writes human_study/al_v2/iso_analysis/{cases.json, report.md}.
usage: python h26_iso_failure_analysis.py [min_cases]      # exits 2 if fewer ISO runs have ended
"""
import os, sys, re, json, glob, subprocess, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(P, 'scripts/common'), os.path.join(P, 'scripts/6_active_learning')]
import xplt
import h22_active_learning as al

OUT = os.path.join(al.AL, 'iso_analysis'); T_ISO0, T_ISO1 = 3.0, 13.0


def read_log(fn):
    out, t = [], None
    for l in open(fn):
        if l.startswith('*Time'): t = float(l.split('=')[1])
        elif l[:1].isdigit(): out.append([t] + [float(v) for v in l.split(',')])
    return np.array(out)


def block_ranges(feb):
    rng = {}
    for m in re.finditer(r'<Elements type="(\w+)" mat="(\d+)" name="([^"]+)">(.*?)</Elements>', feb, re.S):
        es = [int(x) for x in re.findall(r'<elem id="(\d+)"', m.group(4))]
        rng[m.group(3)] = (min(es), max(es))
    return rng


def tissue(name):
    if name.startswith('cage_'): return 'cage ' + ('soft' if 'soft' in name or name.endswith('_0.0') or '_0.25' in name else 'hard/mix')
    if 'cortical' in name: return name.split('_')[0] + ' cortical'
    if 'trabecular' in name: return name.split('_')[0] + ' trabecular'
    if name == 'disc_or_facet_mat5': return 'facet cartilage'
    return 'other ' + name


def soft_compression(d):
    """Min principal Lagrange strain of the cage contact layers and inner elements at the last stored state."""
    import xml.etree.ElementTree as ET
    names = [eb.get('name') for eb in ET.parse(os.path.join(d, 'case.feb')).getroot().find('Geometry').findall('Elements')]
    di = {n: i for i, n in enumerate(names)}
    st = xplt.read(os.path.join(d, 'case.xplt'))['states'][-1]; E_ = st['elem'].get('Lagrange strain', {})
    ce = np.load(os.path.join(d, 'cage_elems.npz')); K = int(ce['K']); out = {'contact': [], 'inner': []}; pos = {}
    for b, lay in zip(ce['block'], ce['layer']):
        pos[b] = pos.get(b, -1) + 1
        Eg = E_.get(di[b] + 1)
        if Eg is None: continue
        e = Eg[pos[b]]; M = np.array([[e[0], e[3], e[5]], [e[3], e[1], e[4]], [e[5], e[4], e[2]]])
        out['contact' if lay in (0, K - 1) else 'inner'].append(np.linalg.eigvalsh(M)[0])
    return {k: (float(np.min(v)), float(np.mean(np.array(v) < -0.30))) for k, v in out.items() if v}


def analyse_case(p):
    d = al.ended_dir(p['cases']['iso'])
    if d is None: return None
    txt = open(os.path.join(d, 'case.log'), errors='ignore').read()
    m = re.findall(r'beginning time step \d+ : ([0-9.e+-]+)', txt); t_end = float(m[-1]) if m else 0.0
    phase = 'distract' if t_end < 1 else 'insert' if t_end < 2 else 'release' if t_end < 3 else 'iso'
    if not os.path.exists(os.path.join(d, 'summary.json')):
        subprocess.run(['python', os.path.join(P, 'scripts/4_postprocess/h15_post_case.py'), d], cwd=P, stdout=subprocess.DEVNULL)
    s = json.load(open(os.path.join(d, 'summary.json'))) if os.path.exists(os.path.join(d, 'summary.json')) else {}
    rb = read_log(os.path.join(d, 'C3pot.txt')); k = len(rb) - 1          # t id x y z thx thy thz Fx Fy Fz Mx My Mz
    ids = [int(x) for x in re.findall(r'Negative jacobian was detected at element (\d+)', txt)]
    rng = block_ranges(open(os.path.join(d, 'case.feb')).read())
    inv = collections.Counter(tissue(n) for i in ids for n, (a, b) in rng.items() if a <= i <= b)
    try: comp = soft_compression(d)
    except Exception as e: comp = {'error': str(e)}
    return dict(id=p['id'], x=p['x'], dir=os.path.relpath(d, P), t_end=t_end, phase=phase,
                iso_completion=max(0.0, min(1.0, (t_end - T_ISO0) / (T_ISO1 - T_ISO0))),
                clamp_N=s.get('clamp_after_release_N'), retained_mm=s.get('retained_distraction_mm'),
                rot_deg_at_stop=[float(np.degrees(v)) for v in rb[k, 5:8]], moment_Nmm_at_stop=[float(v) for v in rb[k, 11:14]],
                Fz_at_stop=float(rb[k, 10]), inverted=dict(inv), n_inverted_ids=len(ids), soft=comp,
                compress_C=(p.get('res') or {}).get('C'))


def main():
    need = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    st = al.load(); rows = [r for r in (analyse_case(p) for p in st['points'] if p.get('cases')) if r]
    if len(rows) < need: print(f'only {len(rows)} ISO runs ended (< {need})'); sys.exit(2)
    os.makedirs(OUT, exist_ok=True); json.dump(rows, open(os.path.join(OUT, 'cases.json'), 'w'), indent=1)
    L = [f'# ISO stop analysis (v2), {len(rows)} terminated ISO runs\n']
    ph = collections.Counter(r['phase'] for r in rows)
    L.append('Phase of the stop: ' + ', '.join(f'{k} {v}' for k, v in ph.most_common()))
    it = [r for r in rows if r['phase'] == 'iso']
    if it:
        c = np.array([r['iso_completion'] for r in it])
        L.append(f'ISO completion (stopped in ISO): median {np.median(c):.3f}, max {c.max():.3f}; '
                 f'{int((c < 0.02).sum())} of {len(c)} stop within the first 2 % (ramp to the start pose)')
    tot = collections.Counter()
    for r in rows: tot.update(r['inverted'])
    L.append('Inverted elements, all runs with ids: ' + ', '.join(f'{k} {v}' for k, v in tot.most_common()))
    L.append('\n| id | design | grad | fab | d | E_soft | phase | t_end | clamp N | rot at stop (deg) | top inverted | soft contact min strain / crushed % |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in sorted(rows, key=lambda r: r['t_end']):
        x = r['x']; top = max(r['inverted'], key=r['inverted'].get) if r['inverted'] else '-'
        sc = r['soft'].get('contact') if isinstance(r['soft'], dict) else None
        L.append(f"| {r['id']} | {x['design']} | {x['grad']} | {x['fab']} | {x['d']:.2f} | {x['E_soft']:.1f} | {r['phase']} | "
                 f"{r['t_end']:.3f} | {r['clamp_N'] or float('nan'):.1f} | {', '.join(f'{v:.2f}' for v in r['rot_deg_at_stop'])} | {top} | "
                 + (f'{sc[0]:+.2f} / {100 * sc[1]:.0f}' if sc else '-') + ' |')
    # simple factor comparison of the stop time
    L.append('\nMean t_end by factor:')
    for f in ('design', 'grad', 'fab'):
        g = collections.defaultdict(list)
        for r in rows: g[r['x'][f]].append(r['t_end'])
        L.append(f'- {f}: ' + ', '.join(f'{k} {np.mean(v):.3f} (n {len(v)})' for k, v in g.items()))
    for f in ('d', 'E_soft', 'E_hard', 'theta'):
        a = np.array([r['x'][f] for r in rows]); b = np.array([r['t_end'] for r in rows])
        if a.std() > 0 and b.std() > 0: L.append(f'- corr(t_end, {f}) = {np.corrcoef(a, b)[0, 1]:+.2f}')
    cl = [(r['clamp_N'], r['t_end']) for r in rows if r['clamp_N'] is not None]
    if len(cl) > 2: a, b = np.array(cl).T; L.append(f'- corr(t_end, clamp) = {np.corrcoef(a, b)[0, 1]:+.2f}')
    open(os.path.join(OUT, 'report.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    main()
