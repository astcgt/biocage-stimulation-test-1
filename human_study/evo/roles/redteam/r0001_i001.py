"""Red team r0001, I-001: independent re-check of the twist on the glued cage faces (e02) for one tied physio case.
Checks
 1. xplt domain order / sizes vs the feb Elements blocks (e02 assumes domain index = block index + 1).
 2. face position: the e02 'top' / 'bot' quads vs the cage_top / cage_bot surfaces of the feb.
 3. cage equilibrium: the cage touches only the two glued faces (no biodisc, no annulus remnant), so
    F_top + F_bot ~ 0 and the total moment about Z ~ 0 if the element-stress sampling is a good traction estimate.
 4. mirror decomposition of the face traction field (y -> -y): which part of the twist is antisymmetric.
 5. which face data the xplt holds (contact traction would allow a direct check).
usage: python -I r0001_i001.py [case_dir]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import json, numpy as np, xml.etree.ElementTree as ET
from scipy.spatial import cKDTree
import xplt
ROOT = _env.ROOT
cd = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else 'human_study/al_v2/cases/p062_physio')
root = ET.parse(os.path.join(cd, 'case.feb')).getroot(); g = root.find('Geometry')
X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
blocks = [(eb.get('name'), np.array([[int(v) for v in e.text.split(',')] for e in eb])) for eb in g.findall('Elements')]
dom = {n: i for i, (n, E) in enumerate(blocks)}; conn = dict(blocks)
surf = {s.get('name'): np.array([[int(v) for v in e.text.split(',')] for e in s]) for s in g.findall('Surface')}
ce = np.load(os.path.join(cd, 'cage_elems.npz')); K = int(ce['K'])
print('npz keys', list(ce.keys()), 'K', K)
faces, pos = [], {}
for b, lay in zip(ce['block'], ce['layer']):
    pos[b] = pos.get(b, -1) + 1
    if 'biodisc' in b or lay not in (0, K - 1): continue
    h = conn[b][pos[b]]; q = h[4:8] if lay == K - 1 else h[0:4]
    Pq = np.array([X[i] for i in q]); nrm = np.cross(Pq[2] - Pq[0], Pq[3] - Pq[1]); A = 0.5 * np.linalg.norm(nrm); nrm /= 2 * A
    sgn = 1.0 if lay == K - 1 else -1.0
    if nrm[2] * sgn < 0: nrm = -nrm
    faces.append((dom[b], pos[b], 'top' if lay == K - 1 else 'bot', nrm, A, Pq.mean(0), tuple(sorted(q))))
print('faces top', sum(f[2] == 'top' for f in faces), 'bot', sum(f[2] == 'bot' for f in faces))
# 2. face position check
for side, sname in (('top', 'cage_top'), ('bot', 'cage_bot')):
    if sname not in surf: print('no surface', sname); continue
    S = {tuple(sorted(r)) for r in surf[sname]}
    mine = [f[6] for f in faces if f[2] == side]
    print(f'{side}: e02 quads found in feb surface {sname}: {sum(q in S for q in mine)}/{len(mine)} (surface has {len(S)})')
    n_mean = np.mean([f[3] for f in faces if f[2] == side], 0); print(f'  mean normal {side}', np.round(n_mean, 3))

pf = xplt.read(os.path.join(cd, 'case.xplt'))
print('xplt domains', [(d['name'], d['n']) for d in pf['domains']][:40])
print('feb blocks  ', [(n, len(E)) for n, E in blocks][:40])
print('face vars', list(pf['states'][-1]['face'].keys()), 'elem vars', list(pf['states'][-1]['elem'].keys()))
print('surfaces', pf['surfaces'])
sch = json.load(open(os.path.join(cd, 'physio_schedule.json')))
rows = []
C = np.array([f[5] for f in faces]); side = np.array([f[2] for f in faces])
# mirror partner of every face (same side), for the decomposition
partner = np.full(len(faces), -1); gap = np.full(len(faces), np.nan)
for s in ('top', 'bot'):
    ii = np.where(side == s)[0]; t = cKDTree(C[ii]); d, j = t.query(C[ii] * [1, -1, 1]); partner[ii] = ii[j]; gap[ii] = d
print('face mirror partner gap: median %.4f p95 %.4f max %.4f mm' % (np.median(gap), np.percentile(gap, 95), gap.max()))
for st in pf['states']:
    tt = st['time']; w = next((w for w in sch['windows'] if w['t0'] - 1e-6 <= tt <= w['t1'] + 1e-6), None)
    if w is None: continue
    S = st['elem'].get('stress', {})
    tr = np.zeros((len(faces), 3)); sn = np.zeros(len(faces)); A = np.array([f[4] for f in faces])
    for k, (di, i, sd, n, a, c, q) in enumerate(faces):
        s6 = S[di + 1][i]; sig = np.array([[s6[0], s6[3], s6[5]], [s6[3], s6[1], s6[4]], [s6[5], s6[4], s6[2]]])
        tv = sig @ n; sn[k] = n @ tv; tr[k] = tv * a          # full traction force on the face (outward normal of the cage)
    r = dict(t=float(tt), window=w['name'])
    for s in ('top', 'bot'):
        m = side == s
        c0 = (C[m] * A[m, None]).sum(0) / A[m].sum(); rr = C[m] - c0
        tau = tr[m] - (sn[m] * A[m])[:, None] * np.array([f[3] for f in faces])[m]
        Mz = float((rr[:, 0] * tau[:, 1] - rr[:, 1] * tau[:, 0]).sum())
        # mirror decomposition of the shear field: symmetric part has tau_x even, tau_y odd
        tp = tau[np.searchsorted(np.where(m)[0], partner[m])]
        anti = 0.5 * (tau - tp * [1, -1, 1])
        Mz_anti = float((rr[:, 0] * anti[:, 1] - rr[:, 1] * anti[:, 0]).sum())
        r[s] = dict(F=tr[m].sum(0).tolist(), shearF=tau.sum(0).tolist(), Mz=Mz, Mz_anti=Mz_anti, c0=c0.tolist(),
                    N=float(-(sn[m] * A[m]).sum()))
    # total moment of the face forces about the cage centroid (cage equilibrium check)
    cc = (C * A[:, None]).sum(0) / A.sum(); Mtot = np.cross(C - cc, tr).sum(0)
    r['sumF'] = tr.sum(0).tolist(); r['sumM'] = Mtot.tolist()
    rows.append(r)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r0001_i001_' + os.path.basename(cd) + '.json')
json.dump(rows, open(out, 'w'), indent=1)
print('t window | top Fxyz | bot Fxyz | sum F | Mz top / bot | Mz_anti top | sum M')
for r in rows[::3]:
    print('%.2f %-9s' % (r['t'], r['window']), np.round(r['top']['F'], 1), np.round(r['bot']['F'], 1), np.round(r['sumF'], 1),
          '%.0f / %.0f' % (r['top']['Mz'], r['bot']['Mz']), '%.0f' % r['top']['Mz_anti'], np.round(r['sumM'], 0))
