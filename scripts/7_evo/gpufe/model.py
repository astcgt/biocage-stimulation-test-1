"""Build the GPU model (torch tensors) from a parsed FEBio file (feb.read).

Pieces: deformable element groups (per element type + material kind, per-element parameters), rigid bodies, node dof
classes (free / fixed / rigid), nonlinear springs (load curves sampled finely), pressure loads, contact interfaces
(node-to-facet; master quads split into two triangles), dynamic-relaxation masses (Gershgorin row sums of the reference
element stiffness).
"""
import numpy as np, torch
import mech
from mech import DT

LC_SAMPLES = 20001          # spring load curves sampled on this many points (linear interpolation on the GPU)


class ElemGroup:
    pass


def _lame(E, v): return mech.lame(E, v)


def _iso_D(lam, mu):
    D = np.zeros((6, 6)); D[:3, :3] = lam; D[np.arange(3), np.arange(3)] += 2 * mu; D[np.arange(3, 6), np.arange(3, 6)] = mu
    return D


def _ortho_D(m, A):
    """small-strain stiffness (Voigt, global axes) of the FEBio orthotropic material with axes rows A."""
    mu, lam, _ = mech.ortho_constants(m)
    Dl = np.zeros((6, 6)); Dl[:3, :3] = lam + np.diag(2 * mu)
    Dl[3, 3] = (mu[0] + mu[1]) / 2; Dl[4, 4] = (mu[1] + mu[2]) / 2; Dl[5, 5] = (mu[2] + mu[0]) / 2
    R = A.T                                            # columns = local axes in global coords
    # build D_g numerically: apply to unit engineering strains
    Dg = np.zeros((6, 6))
    for J in range(6):
        e = np.zeros(6); e[J] = 1.0
        Eg = np.array([[e[0], e[3] / 2, e[5] / 2], [e[3] / 2, e[1], e[4] / 2], [e[5] / 2, e[4] / 2, e[2]]])
        El = R.T @ Eg @ R
        el = np.array([El[0, 0], El[1, 1], El[2, 2], 2 * El[0, 1], 2 * El[1, 2], 2 * El[2, 0]])
        sl = Dl @ el
        Sl = np.array([[sl[0], sl[3], sl[5]], [sl[3], sl[1], sl[4]], [sl[5], sl[4], sl[2]]])
        Sg = R @ Sl @ R.T
        Dg[:, J] = [Sg[0, 0], Sg[1, 1], Sg[2, 2], Sg[0, 1], Sg[1, 2], Sg[2, 0]]
    return Dg


def _B(G):
    """strain-displacement matrices (E, g, 6, 3n) from gradients G (E, g, n, 3), engineering shear order xx yy zz xy yz zx."""
    E_, g, n, _ = G.shape; B = np.zeros((E_, g, 6, 3 * n))
    for a in range(n):
        gx, gy, gz = G[:, :, a, 0], G[:, :, a, 1], G[:, :, a, 2]
        B[:, :, 0, 3 * a] = gx; B[:, :, 1, 3 * a + 1] = gy; B[:, :, 2, 3 * a + 2] = gz
        B[:, :, 3, 3 * a] = gy; B[:, :, 3, 3 * a + 1] = gx
        B[:, :, 4, 3 * a + 1] = gz; B[:, :, 4, 3 * a + 2] = gy
        B[:, :, 5, 3 * a + 2] = gx; B[:, :, 5, 3 * a] = gz
    return B


def gershgorin_rows(G, w, D, chunk=20000):
    """row sums of |K_e| per element node (max over its 3 dofs): (E, n). D: (6, 6) or (E, 6, 6)."""
    out = []
    for s in range(0, len(G), chunk):
        Gc, wc = G[s:s + chunk], w[s:s + chunk]
        B = _B(Gc)
        Dc = D if D.ndim == 2 else D[s:s + chunk]
        if Dc.ndim == 2: K = np.einsum('egia,ij,egjb,eg->eab', B, Dc, B, wc)
        else: K = np.einsum('egia,eij,egjb,eg->eab', B, Dc, B, wc)
        r = np.abs(K).sum(-1).reshape(len(Gc), -1, 3).max(-1)
        out.append(r)
    return np.concatenate(out)


def build(m, dev='cuda', sample_lc=LC_SAMPLES):
    X = m['X']; N = len(X); mats = m['mats']
    model = dict(N=N, X0=torch.tensor(X, dtype=DT, device=dev), dev=dev, feb=m)
    rigid_mats = {k for k, v in mats.items() if v['type'] == 'rigid body'}
    mass = np.zeros(N)
    groups = {}
    elem_nodes_deform = np.zeros(N, bool)
    rigid_nodes = {k: set() for k in rigid_mats}
    vol_rigid = {k: [0.0, np.zeros(3)] for k in rigid_mats}
    blocks_mech = []                                    # (conn, small-strain D, volume) per deformable block: contact auto penalty
    for b in m['blocks']:
        mid = b['mat']; mt = mats[mid]; conn = b['conn']
        if mid in rigid_mats:
            rigid_nodes[mid].update(conn.ravel().tolist())
            G, w = mech.reference_gradients(X, conn, b['etype'])
            vol_rigid[mid][0] += w.sum(); vol_rigid[mid][1] += (w.sum(1)[:, None] * X[conn].mean(1)).sum(0)
            continue
        elem_nodes_deform[conn.ravel()] = True
        G, w = mech.reference_gradients(X, conn, b['etype'])
        kind, prm, D, Emod = _material_setup(mt, X, conn, b['etype'], m)
        rows = gershgorin_rows(G, w, D)
        blocks_mech.append((conn, D, w.sum(1)))
        np.add.at(mass, conn, rows)
        key = (b['etype'], kind)
        gr = groups.setdefault(key, dict(etype=b['etype'], kind=kind, conn=[], G=[], w=[], prm={}, blocks=[], Emod=[]))
        off = sum(len(c) for c in gr['conn'])
        gr['blocks'].append((b['name'], off, len(conn), b['eid']))
        gr['conn'].append(conn); gr['G'].append(G); gr['w'].append(w); gr['Emod'].append(np.full(len(conn), Emod))
        for k, v in prm.items(): gr['prm'].setdefault(k, []).append(v)
    egroups = []
    for key, gr in groups.items():
        eg = ElemGroup(); eg.etype, eg.kind, eg.blocks = gr['etype'], gr['kind'], gr['blocks']
        conn = np.concatenate(gr['conn'])
        eg.conn = torch.tensor(conn, dtype=torch.long, device=dev)
        eg.G = torch.tensor(np.concatenate(gr['G']), dtype=DT, device=dev)
        eg.w = torch.tensor(np.concatenate(gr['w']), dtype=DT, device=dev)
        eg.V0 = eg.w.sum(1)
        eg.Emod = np.concatenate(gr['Emod'])
        eg.prm = {}
        for k, v in gr['prm'].items():
            if k.startswith('const_'): eg.prm[k] = v[0]          # same for every block of the group (checked below)
            else: eg.prm[k] = torch.tensor(np.concatenate(v), dtype=DT, device=dev)
        for k, v in gr['prm'].items():
            if k.startswith('const_') and any(not np.allclose(v[0], x) for x in v): raise ValueError(f'{key}: {k} differs between blocks')
        egroups.append(eg)
    model['groups'] = egroups
    # rigid bodies
    rbs = {}
    for k in rigid_mats:
        ids = np.array(sorted(rigid_nodes[k]), dtype=np.int64)
        com = mats[k].get('com')
        if com is None: com = vol_rigid[k][1] / vol_rigid[k][0]
        rbs[k] = dict(mat=k, nodes=torch.tensor(ids, device=dev), com0=np.array(com, float), name=mats[k]['name'])
    model['rigid'] = rbs
    # springs
    springs = []
    for d in m['discrete']:
        pairs = m['discrete_sets'][d['set']]; lc = m['lcs'][d['lc']]
        L0 = np.linalg.norm(X[pairs[:, 1]] - X[pairs[:, 0]], axis=1)
        lo, hi = lc.x[0] - 0.1 * (lc.x[-1] - lc.x[0]), lc.x[-1] + 0.1 * (lc.x[-1] - lc.x[0])
        xs = np.linspace(lo, hi, sample_lc); ys = d['scale'] * lc(xs)
        kmax = np.max(np.abs(np.diff(ys) / np.diff(xs)))
        springs.append(dict(name=d['set'], i=torch.tensor(pairs[:, 0], device=dev), j=torch.tensor(pairs[:, 1], device=dev),
                            L0=torch.tensor(L0, dtype=DT, device=dev), x0=lo, dx=(hi - lo) / (sample_lc - 1),
                            ys=torch.tensor(ys, dtype=DT, device=dev), kmax=kmax))
        np.add.at(mass, pairs[:, 0], 2 * kmax); np.add.at(mass, pairs[:, 1], 2 * kmax)
    model['springs'] = springs
    model['mass_elem'] = mass                           # Gershgorin row sums from elements + springs (contacts added later)
    model['deform_nodes'] = elem_nodes_deform
    model['blocks_mech'] = blocks_mech
    return model


def _fiber_dirs(axes, theta, phi):
    th, ph = np.radians(theta), np.radians(phi)
    a = np.array([np.cos(th) * np.sin(ph), np.sin(th) * np.sin(ph), np.cos(ph)])
    return np.einsum('eij,i->ej', axes, a)              # local -> global (axes rows)


def _material_setup(mt, X, conn, etype, m):
    t = mt['type']; E_ = len(conn)
    if t == 'neo-Hookean':
        mu, lam = _lame(mt['E'], mt['v'])
        return 'neo', dict(mu=np.full(E_, mu), lam=np.full(E_, lam)), _iso_D(lam, mu), lam + 2 * mu
    if t == 'orthotropic elastic':
        kind_ax = mt.get('axis')
        if kind_ax is None: A = np.eye(3)                       # FEBio default: global axes
        elif kind_ax[0] == 'vector': A = mech.local_axes_vector(kind_ax[1], kind_ax[2])
        else: raise NotImplementedError('orthotropic mat_axis ' + kind_ax[0])
        mu, lam, cmax = mech.ortho_constants(mt)
        D = _ortho_D(mt, A)
        return 'ortho', dict(A=np.repeat(A[None], E_, 0), const_mu=mu, const_lam=lam), D, cmax
    if t == 'solid mixture':
        sol = mt['solids']; types = [s['type'] for s in sol]
        if types[0] != 'Holmes-Mow' or any(s != 'fiber-exp-pow' for s in types[1:]): raise NotImplementedError(types)
        hm = sol[0]; mu, lam = _lame(hm['E'], hm['v'])
        ax = mt.get('axis')
        if ax is None or ax[0] != 'local': raise NotImplementedError('mixture axis')
        axes = mech.local_axes_nodes(X[conn], ax[1])
        prm = dict(mu=np.full(E_, mu), lam=np.full(E_, lam), beta=np.full(E_, hm['beta']))
        for k, f in enumerate(sol[1:]):
            prm[f'a{k}'] = _fiber_dirs(axes, f['theta'], f['phi'])
            prm[f'ksi{k}'] = np.full(E_, f['ksi']); prm[f'alpha{k}'] = np.full(E_, f['alpha']); prm[f'fbeta{k}'] = np.full(E_, f['beta'])
        if len(sol) != 3: raise NotImplementedError('mixture with != 2 fibers')
        return 'hmfib', prm, _iso_D(lam, mu), lam + 2 * mu
    if t == 'uncoupled prestrain elastic':
        el = mt['elastic']
        if el['type'] != 'Gent' or etype != 'hex8': raise NotImplementedError('prestrain needs Gent hex8')
        G, k, Jm = el['G'], el['k'], el['Jm']
        mu, lam = G, k - 2 * G / 3
        lc, r = mt['ramp']
        return 'gentps', dict(G=np.full(E_, G), k=np.full(E_, k), Jm=np.full(E_, Jm), F0=np.repeat(mt['F0'][None], E_, 0),
                              ramp_scale=np.full(E_, r), ramp_lc=np.full(E_, -1 if lc is None else lc)), _iso_D(lam, mu), k + 4 * G / 3
    if t == 'Gent':
        if etype != 'hex8': raise NotImplementedError('Gent needs hex8')
        G, k, Jm = mt['G'], mt['k'], mt['Jm']
        return 'gentps', dict(G=np.full(E_, G), k=np.full(E_, k), Jm=np.full(E_, Jm), F0=np.repeat(np.eye(3)[None], E_, 0),
                              ramp_scale=np.zeros(E_), ramp_lc=np.full(E_, -1)), _iso_D(k - 2 * G / 3, G), k + 4 * G / 3
    raise NotImplementedError(t)
