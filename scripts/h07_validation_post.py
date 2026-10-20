"""Post-process the C0-C7 validation runs: per-vertebra rigid rotation (Kabsch on tracked cortical nodes), level ROM,
moment-rotation curves, comparison with Herron 2020 (26 y.o.) digitised values, and figures.

usage: python h07_validation_post.py <runs_dir> <herron_digitised.json> <out_dir>
"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xplt
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

runs, ref_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
trk = json.load(open(os.path.join(runs, 'tracking_nodes.json')))
H = json.load(open(ref_json))
VERTS = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']
AXIS = {'x': 0, 'y': 1, 'z': 2}


def read_log(path):
    """FEBio logfile blocks -> list of (time, {id: row})."""
    steps, cur, t = [], None, None
    for line in open(path):
        if line.startswith('*Time'):
            t = float(line.split('=')[1])
        elif line.startswith('*Data'):
            cur = {}; steps.append((t, cur))
        elif line[0].isdigit() and cur is not None:
            v = line.strip().split(','); cur[int(v[0])] = np.array(v[1:], float)
    return steps


def kabsch(A, B):
    a, b = A - A.mean(0), B - B.mean(0)
    U, _, Vt = np.linalg.svd(a.T @ b)
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    return Vt.T @ D @ U.T


def case_rotations(d):
    """Return times and rotation matrices of C0..C6 (C7 fixed = identity)."""
    rig = read_log(os.path.join(d, 'C0_rigid.txt'))
    times = [t for t, _ in rig]
    R = {'C0': [Rotation.from_rotvec(r[2][3:6]).as_matrix() for _, r in rig]}
    for v in VERTS:
        steps = read_log(os.path.join(d, f'{v}.txt'))
        X0 = np.array(trk['ref'][v]); ids = trk['track'][v]
        R[v] = [kabsch(X0, X0 + np.array([s[i] for i in ids])) for _, s in steps]
    R['C7'] = [np.eye(3)] * len(times)
    return np.array(times), R


def rel_angle(Ru, Rl, ax):
    """Rotation of the upper relative to the lower vertebra, component about global axis ax (deg)."""
    return np.degrees(Rotation.from_matrix(Rl.T @ Ru).as_rotvec()[ax])


levels = [('C0-C1', 'C0', 'C1'), ('C1-C2', 'C1', 'C2'), ('C2-C3', 'C2', 'C3'), ('C3-C4', 'C3', 'C4'),
          ('C4-C5', 'C4', 'C5'), ('C5-C6', 'C5', 'C6'), ('C6-C7', 'C6', 'C7'), ('C3-C7', 'C3', 'C7'), ('C0-C7', 'C0', 'C7')]
res = {}
for case in sorted(os.listdir(runs)):
    d = os.path.join(runs, case)
    if not os.path.isdir(d) or not os.path.exists(os.path.join(d, 'C0_rigid.txt')):
        continue
    times, R = case_rotations(d)
    ax = AXIS[case.split('_')[-1]]
    M = np.clip(times - 1.0, 0, 1) * 1.5 * (1 if 'pos' in case else -1)          # N m, ramp t = 1..2
    rot = {lv: [rel_angle(R[u][k], R[l][k], ax) for k in range(len(times))] for lv, u, l in levels}
    pf = xplt.read(os.path.join(d, 'C0C7.xplt')); last = pf['states'][-1]
    sid = {v: k for k, v in pf['surfaces'].items()}
    cf = last['face']['contact force']
    facet = {s: float(np.linalg.norm(cf[sid[f'C34_{s}_FC_master']])) for s in ('L', 'R')}
    res[case] = dict(time=times.tolist(), moment_Nm=M.tolist(), rot_deg=rot, completed=bool(times[-1] >= 1.99), t_end=float(times[-1]),
                     facet_C34_N=facet)
json.dump(res, open(os.path.join(out, 'validation_results.json'), 'w'))

# map sign conventions to anatomical directions from the C0-C7 sagittal motion of the head:
# flexion = head rotates so that its front goes down; with x anterior, z superior that is a positive rotation about +y
# (rotating +z toward +x). For LB / AR, left/right labels do not matter for this symmetric model (averaged as in Herron).
def final(case, lv):
    r = res.get(case); return None if r is None else abs(r['rot_deg'][lv][-1]) if r['completed'] else None

# which FE sign is flexion: flexion moves the head (C0 rigid body) anteriorly (+x)
def c0_dx(case):
    rig = read_log(os.path.join(runs, case, 'C0_rigid.txt')); return rig[-1][1][2][0] - rig[0][1][2][0]
flex_case, ext_case = (('flex_pos_y', 'flex_neg_y') if c0_dx('flex_pos_y') > c0_dx('flex_neg_y') else ('flex_neg_y', 'flex_pos_y'))
print('flexion case:', flex_case, ' extension case:', ext_case)
cmp = {}
H3 = H['fig3_C0C7_total_rotation_deg_at_1p5Nm']; H4 = H['fig4_level_rotation_deg_at_1p5Nm']
pairs = {'flexion': [flex_case], 'extension': [ext_case], 'lateral_bending': ['lb_pos_x', 'lb_neg_x'],
         'axial_rotation': ['ar_pos_z', 'ar_neg_z']}
# Fig 3: one-direction C0-C7 rotation
for mode, hv in (('flexion', H3['flexion']), ('extension', H3['extension']),
                 ('lateral_bending', (H3['lateral_bending_right'] + H3['lateral_bending_left']) / 2),
                 ('axial_rotation', (H3['axial_rotation_right'] + H3['axial_rotation_left']) / 2)):
    v = [final(c, 'C0-C7') for c in pairs[mode]]; v = [x for x in v if x is not None]
    o = float(np.mean(v)) if v else None
    cmp.setdefault(mode, {})['C0-C7_one_direction'] = dict(ours_deg=None if o is None else round(o, 2), herron_deg=hv,
                                                             diff_pct=None if o is None else round(100 * (o - hv) / hv, 1))
# Fig 4: two-direction total ROM per level
tot_cases = {'flexion_extension': [flex_case, ext_case], 'lateral_bending': ['lb_pos_x', 'lb_neg_x'],
             'axial_rotation': ['ar_pos_z', 'ar_neg_z']}
for mode, cs in tot_cases.items():
    for lv in ['C0-C1', 'C1-C2', 'C2-C3', 'C3-C7', 'C3-C4']:
        v = [final(c, lv) for c in cs]
        o = None if any(x is None for x in v) else float(sum(v))
        h = H4[mode].get(lv)
        cmp.setdefault(mode, {})[f'{lv}_total_ROM'] = dict(ours_deg=None if o is None else round(o, 2), herron_deg=h,
            diff_pct=None if (o is None or h is None) else round(100 * (o - h) / h, 1))
Hf = H['fig5_facet_force_N_C3C4_at_1p5Nm']
def facet(mode):
    if mode == 'extension':
        r = res.get(ext_case); return None if not r or not r['completed'] else np.mean(list(r['facet_C34_N'].values()))
    cs = pairs[mode]; v = [max(res[c]['facet_C34_N'].values()) for c in cs if c in res and res[c]['completed']]
    return float(np.mean(v)) if v else None
for mode in ('extension', 'lateral_bending', 'axial_rotation'):
    o = facet(mode)
    cmp.setdefault(mode, {})['facet_force_C3C4'] = dict(ours_N=None if o is None else round(o, 1), herron_N=Hf[mode],
                                         diff_pct=None if o is None else round(100 * (o - Hf[mode]) / Hf[mode], 1))
json.dump(cmp, open(os.path.join(out, 'comparison.json'), 'w'), indent=1)
print(json.dumps(cmp, indent=1))

# figures: moment-rotation (C0-C7) like Herron Fig 3, and level bars like Fig 4 (1.5 N m)
fig, axs = plt.subplots(1, 3, figsize=(13, 4))
for a, (title, cs, hk) in zip(axs, [('Flexion / extension', ['flex_pos_y', 'flex_neg_y'], ('flexion', 'extension')),
                                    ('Lateral bending', ['lb_pos_x', 'lb_neg_x'], ('lateral_bending_right', 'lateral_bending_left')),
                                    ('Axial rotation', ['ar_pos_z', 'ar_neg_z'], ('axial_rotation_right', 'axial_rotation_left'))]):
    cs = [flex_case, ext_case] if cs[0].startswith('flex') else cs
    for c, hkey in zip(cs, hk):
        if c not in res: continue
        r = res[c]; m = np.array(r['moment_Nm']); th = np.array(r['rot_deg']['C0-C7'])
        sel = np.array(r['time']) >= 1.0
        a.plot(m[sel], th[sel], color='#d62728', lw=2, label='this study (FEBio 4.13)' if c == cs[0] else None)
        a.plot(np.sign(m[sel][-1]) * 1.5, np.sign(th[sel][-1]) * H3[hkey], 'ks', ms=7,
               label='Herron 2020, 26 y.o. (digitised)' if c == cs[0] else None)
    a.axhline(0, color='0.7', lw=0.8); a.axvline(0, color='0.7', lw=0.8)
    a.set_title(title); a.set_xlabel('Moment (N m)'); a.set_ylabel('C0-C7 rotation (deg)'); a.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(out, 'moment_rotation_C0C7.png'), dpi=150)

fig, axs = plt.subplots(1, 3, figsize=(13, 4))
for a, mode in zip(axs, ['flexion_extension', 'lateral_bending', 'axial_rotation']):
    lvs = ['C0-C1', 'C1-C2', 'C2-C3', 'C3-C7']
    o = [cmp[mode].get(f'{lv}_total_ROM', {}).get('ours_deg') or 0 for lv in lvs]
    h = [H4[mode][lv] for lv in lvs]
    x = np.arange(len(lvs))
    a.bar(x - 0.2, o, 0.4, color='#d62728', label='this study')
    a.bar(x + 0.2, h, 0.4, color='0.5', label='Herron 2020 26 y.o. (digitised, +/-2 deg)')
    a.set_xticks(x); a.set_xticklabels(lvs); a.set_title(f'{mode.replace("_", " ")}: total ROM at 1.5 N m'); a.set_ylabel('Total ROM, both directions (deg)')
    a.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(out, 'level_rom_1p5Nm.png'), dpi=150)
