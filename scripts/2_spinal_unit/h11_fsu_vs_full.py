"""Compare intact C3-C4 FSU (deformable bone, potted) with the C3-C4 level of the validated C0-C7 model at 1.5 N m:
total ROM (both directions) about each axis and C3-4 facet contact force (Herron's rules).
usage: python h11_fsu_vs_full.py <fsu_runs> <full_runs> <full_results.json> <out.json>
"""
import sys, os, json, numpy as np
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
import xplt
from scipy.spatial.transform import Rotation
fsu, full, full_res, out = sys.argv[1:5]

def read_log(path):
    steps, cur = [], None
    for line in open(path):
        if line.startswith('*Data'): cur = {}; steps.append(cur)
        elif line[0].isdigit() and cur is not None:
            v = line.strip().split(','); cur[int(v[0])] = np.array(v[1:], float)
    return steps

def kabsch(A, B):
    a, b = A - A.mean(0), B - B.mean(0); U, _, Vt = np.linalg.svd(a.T @ b)
    return Vt.T @ np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T

trk = json.load(open(os.path.join(fsu, 'tracking_nodes.json')))
AX = {'x': 0, 'y': 1, 'z': 2}
res = {}
for case in ('flex_pos_y', 'flex_neg_y', 'lb_pos_x', 'lb_neg_x', 'ar_pos_z', 'ar_neg_z'):
    d = os.path.join(fsu, case); R = {}
    for v in ('C3', 'C4'):
        s = read_log(os.path.join(d, f'{v}.txt'))[-1]; X0 = np.array(trk['ref'][v])
        R[v] = kabsch(X0, X0 + np.array([s[i] for i in trk['track'][v]]))
    rot = np.degrees(Rotation.from_matrix(R['C4'].T @ R['C3']).as_rotvec()[AX[case[-1]]])
    pf = xplt.read(os.path.join(d, 'fsu.xplt')); sid = {n: k for k, n in pf['surfaces'].items()}
    cf = pf['states'][-1]['face']['contact force']
    fac = {s: float(np.linalg.norm(cf[sid[f'C34_{s}_FC_master']])) for s in ('L', 'R')}
    res[case] = dict(rot_deg=float(rot), facet_N=fac)
F = json.load(open(full_res))
def full_rot(case):
    return abs(F[case]['rot_deg']['C3-C4'][-1])
def full_fac(case):
    import xplt as X
    pf = X.read(os.path.join(full, case, 'C0C7.xplt')); sid = {n: k for k, n in pf['surfaces'].items()}
    cf = pf['states'][-1]['face']['contact force']
    return {s: float(np.linalg.norm(cf[sid[f'C34_{s}_FC_master']])) for s in ('L', 'R')}
cmp = {}
for mode, cs in (('flexion_extension', ('flex_pos_y', 'flex_neg_y')), ('lateral_bending', ('lb_pos_x', 'lb_neg_x')),
                 ('axial_rotation', ('ar_pos_z', 'ar_neg_z'))):
    o = sum(abs(res[c]['rot_deg']) for c in cs); f = sum(full_rot(c) for c in cs)
    cmp[mode] = dict(C3C4_total_ROM_fsu=round(o, 2), C3C4_total_ROM_full=round(f, 2), diff_pct=round(100 * (o - f) / f, 1))
    for c in cs:
        ff = full_fac(c)
        cmp[mode][f'facet_{c}_fsu_N'] = {k: round(v, 1) for k, v in res[c]['facet_N'].items()}
        cmp[mode][f'facet_{c}_full_N'] = {k: round(v, 1) for k, v in ff.items()}
json.dump(cmp, open(out, 'w'), indent=1); print(json.dumps(cmp, indent=1))
