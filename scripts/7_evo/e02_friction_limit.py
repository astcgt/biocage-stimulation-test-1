"""Friction needed to hold the cage, two methods, on a finished tied-contact FEBio run (methodology comparison, evo PLAN).

Both start from the bonded (tied) solution: the cage is glued, so the interface tractions are what the friction would have to carry.
  M2 'force ratio' (h15, Q47): mu_force = |sum of shear forces| / sum of compressive normal forces, per face.
     Ignores the twisting moment about the face normal and where the pressure sits.
  M3 'friction limit': smallest mu for which SOME friction distribution with |f_i| <= mu * P_i (P_i = local compressive normal
     force of contact element i, 0 where the glue is in tension) balances both the in-plane shear force AND the twisting moment
     the glue carries. Linear program (friction circle -> inscribed 16-gon, error < 2 %, conservative).
     This is the rigid-body sliding limit (limit surface; Goyal 1991, Lynch): mu >= mu_lim is needed, otherwise the face must
     slide as a whole (translate and / or spin). mu_lim >= mu_force always.
usage: python e02_friction_limit.py <case_dir> [out.json]
"""
import sys, os, json, numpy as np, xml.etree.ElementTree as ET
from scipy.optimize import linprog
sys.path[:0] = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
import xplt

M_POLY = 16
U = np.c_[np.cos(2 * np.pi * np.arange(M_POLY) / M_POLY), np.sin(2 * np.pi * np.arange(M_POLY) / M_POLY)]


def friction_limit(c, P, F, Mz):
    """c: (n, 2) element centres (about the face centroid), P: (n,) compressive normal forces, F: (2,) shear, Mz: twisting moment.
    Returns the smallest mu, or inf when no compressive contact is left."""
    keep = P > 1e-9 * max(P.max(), 1e-30) if len(P) else P > 0
    c, P = c[keep], P[keep]; n = len(P)
    if n == 0: return float('inf')
    # variables: lambda_ik >= 0 (n * M), mu; f_i = sum_k lambda_ik U_k; sum_k lambda_ik <= mu P_i
    nv = n * M_POLY + 1
    Aeq = np.zeros((3, nv)); Aeq[0, :-1] = np.tile(U[:, 0], n); Aeq[1, :-1] = np.tile(U[:, 1], n)
    cr = c[:, 0:1] * U[None, :, 1] - c[:, 1:2] * U[None, :, 0]          # r x u_k
    Aeq[2, :-1] = cr.ravel()
    from scipy.sparse import csr_matrix
    rows = np.repeat(np.arange(n), M_POLY); cols = np.arange(n * M_POLY)
    Aub = csr_matrix((np.r_[np.ones(n * M_POLY), -P], (np.r_[rows, np.arange(n)], np.r_[cols, np.full(n, nv - 1)])), shape=(n, nv))
    cost = np.zeros(nv); cost[-1] = 1.0
    r = linprog(cost, A_ub=Aub, b_ub=np.zeros(n), A_eq=Aeq, b_eq=[F[0], F[1], Mz], bounds=(0, None), method='highs')
    return float(r.x[-1]) if r.status == 0 else float('nan')


def main(cd, out=None):
    case = json.load(open(os.path.join(cd, 'case.json'))); prm = case['params']
    assert prm.get('contact_type') == 'tied', 'needs a tied run'
    root = ET.parse(os.path.join(cd, 'case.feb')).getroot(); g = root.find('Geometry')
    X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
    blocks = [(eb.get('name'), np.array([[int(v) for v in e.text.split(',')] for e in eb])) for eb in g.findall('Elements')]
    dom = {n: i for i, (n, E) in enumerate(blocks)}; conn = dict(blocks)
    ce = np.load(os.path.join(cd, 'cage_elems.npz')); K = int(ce['K'])
    faces, pos = [], {}
    for b, lay in zip(ce['block'], ce['layer']):
        pos[b] = pos.get(b, -1) + 1
        if 'biodisc' in b or lay not in (0, K - 1): continue
        h = conn[b][pos[b]]; q = h[4:8] if lay == K - 1 else h[0:4]
        Pq = np.array([X[i] for i in q]); nrm = np.cross(Pq[2] - Pq[0], Pq[3] - Pq[1]); A = 0.5 * np.linalg.norm(nrm); nrm /= 2 * A
        sgn = 1.0 if lay == K - 1 else -1.0
        if nrm[2] * sgn < 0: nrm = -nrm
        faces.append((dom[b], pos[b], 'top' if lay == K - 1 else 'bot', nrm, A, Pq.mean(0)))
    pf = xplt.read(os.path.join(cd, 'case.xplt')); states = pf['states']
    sch = json.load(open(os.path.join(cd, 'physio_schedule.json')))
    rows = []
    for st in states:
        tt = st['time']; w = next((w for w in sch['windows'] if w['t0'] - 1e-6 <= tt <= w['t1'] + 1e-6), None)
        if w is None: continue
        S = st['elem'].get('stress', {}); acc = {}
        for di, i, side, n, A, c in faces:
            Sg = S.get(di + 1)
            if Sg is None: continue
            s6 = Sg[i]; sig = np.array([[s6[0], s6[3], s6[5]], [s6[3], s6[1], s6[4]], [s6[5], s6[4], s6[2]]])
            tv = sig @ n; sn = float(n @ tv); tau = tv - sn * n
            a = acc.setdefault(side, dict(c=[], P=[], f=[], A=[]))
            a['c'].append(c[:2]); a['P'].append(max(-sn, 0.0) * A); a['f'].append(tau[:2] * A); a['A'].append(A)
        r = dict(t=tt, window=w['name'])
        for side, a in acc.items():
            c = np.array(a['c']); P = np.array(a['P']); f = np.array(a['f']); Ar = np.array(a['A'])
            c0 = (c * Ar[:, None]).sum(0) / Ar.sum(); c = c - c0
            F = f.sum(0); Mz = float((c[:, 0] * f[:, 1] - c[:, 1] * f[:, 0]).sum()); N = P.sum()
            r[side] = dict(N=N, F=float(np.linalg.norm(F)), Mz_Nmm=Mz, mu_force=float(np.linalg.norm(F) / N) if N > 0 else float('inf'),
                           mu_limit=friction_limit(c, P, F, Mz))
        rows.append(r)
    per = {}
    for w in sch['windows']:
        rw = [r for r in rows if r['window'] == w['name']]
        if not rw: continue
        f = lambda key: max(max(r[s][key] for s in ('top', 'bot') if s in r) for r in rw)
        per[w['name']] = dict(n_states=len(rw), mu_force=f('mu_force'), mu_limit=f('mu_limit'),
                              max_twist_Nmm=max(max(abs(r[s]['Mz_Nmm']) for s in ('top', 'bot') if s in r) for r in rw))
    res = dict(case=cd, windows=per)
    if out: json.dump(dict(res, states=rows), open(out, 'w'), indent=1)
    return res


if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), indent=1))
