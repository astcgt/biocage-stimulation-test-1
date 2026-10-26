"""Quasi-static solution of a FEBio 2.5 model on the GPU by adaptive dynamic relaxation (explicit).

Per load increment the equilibrium is found by the damped explicit iteration (Joldes, Wittek & Miller 2011, Int J Numer
Meth Biomed Eng 27: 'An adaptive dynamic relaxation method for solving nonlinear finite element problems'):
    dx_{n+1} = beta dx_n + alpha M^-1 r_n,  alpha = 2 h^2 / (2 + c h), beta = (2 - c h) / (2 + c h), h = 1
with fictitious masses from the Gershgorin bound of the stiffness (stable for h = 1) and the damping c = 2 omega_min,
omega_min from the Rayleigh quotient of the last increments. No global matrix, no Newton iteration: frictional contact
cannot 'fail to converge', it just needs more iterations. Nodes that start a period-2 oscillation (the signature of an
unstable explicit step) get a heavier mass, locally.

Load / time handling follows the FEBio steps: step BCs (node fixes, rigid fixed / prescribed / force / ramp) replace the
previous step's, global BCs always apply; load curves in absolute time; contacts with penalty load curves and tie times.
"""
import json, time as _time, numpy as np, torch
import mech, contact, kern
from mech import DT

ROT = {'Rx': 0, 'Ry': 1, 'Rz': 2}; TRA = {'x': 0, 'y': 1, 'z': 2}


def rotvec_to_R(w):
    th = w.norm()
    if th < 1e-14: return torch.eye(3, dtype=DT, device=w.device) + skew(w)
    k = w / th; K = skew(k)
    return torch.eye(3, dtype=DT, device=w.device) + torch.sin(th) * K + (1 - torch.cos(th)) * (K @ K)


def R_to_rotvec(R):
    c = ((R.trace() - 1) / 2).clamp(-1, 1); th = torch.arccos(c)
    if th < 1e-12: return torch.stack([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / 2
    return th / (2 * torch.sin(th)) * torch.stack([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])


def skew(v):
    z = torch.zeros((), dtype=DT, device=v.device)
    return torch.stack([torch.stack([z, -v[2], v[1]]), torch.stack([v[2], z, -v[0]]), torch.stack([-v[1], v[0], z])])


class Solver:
    def __init__(self, model, opts=None):
        o = dict(compile=True, coarse_every=200, clusters=(('C3', 'C3_'), ('C4', 'C4_'), ('cage', 'cage')), tol_r=1e-4, tol_dx=1e-6, max_iter=200000, min_iter=50, search_every=50, contact_penalty_mult=1.0,
                 friction_override=None, disable_contacts=(), log_every=0, increments_per_step=None, verbose=True)
        o.update(opts or {}); self.o = o
        self.m = model; self.dev = model['dev']; self.feb = model['feb']; N = model['N']
        self.X0 = model['X0']; self.x = self.X0.clone()
        self.mass_base = torch.tensor(model['mass_elem'], dtype=DT, device=self.dev)
        self.groups = model['groups']; self.springs = model['springs']
        self.lcs = self.feb['lcs']
        self._cfun = {}
        for g in self.groups:
            if g.kind == 'ortho':
                g.mu_t = torch.tensor(g.prm['const_mu'], dtype=DT, device=self.dev); g.lam_t = torch.tensor(g.prm['const_lam'], dtype=DT, device=self.dev)
            if g.kind == 'gentps': g.ramp_lcs = [int(v) for v in torch.unique(g.prm['ramp_lc']).tolist() if v >= 0]
        sp = self.springs
        if sp:
            S = max(len(q['ys']) for q in sp)
            self.spr = dict(i=torch.cat([q['i'] for q in sp]), j=torch.cat([q['j'] for q in sp]), L0=torch.cat([q['L0'] for q in sp]),
                            cid=torch.cat([torch.full((len(q['i']),), k, dtype=torch.long, device=self.dev) for k, q in enumerate(sp)]),
                            x0=torch.tensor([q['x0'] for q in sp], dtype=DT, device=self.dev), dx=torch.tensor([q['dx'] for q in sp], dtype=DT, device=self.dev),
                            ys=torch.stack([q['ys'] for q in sp]))
        else:
            self.spr = None
        self.t = 0.0
        # rigid bodies: state = translation of COM, rotation matrix
        self.rb = {}
        for k, r in model['rigid'].items():
            nodes = r['nodes']; com0 = torch.tensor(r['com0'], dtype=DT, device=self.dev)
            self.rb[k] = dict(nodes=nodes, com0=com0, r0=self.X0[nodes] - com0, c=com0.clone(), R=torch.eye(3, dtype=DT, device=self.dev),
                              v=torch.zeros(3, dtype=DT, device=self.dev), w=torch.zeros(3, dtype=DT, device=self.dev),
                              F=torch.zeros(3, dtype=DT, device=self.dev), M=torch.zeros(3, dtype=DT, device=self.dev), name=r['name'])
        self.is_rigid = torch.zeros(N, dtype=torch.bool, device=self.dev)
        for r in self.rb.values(): self.is_rigid[r['nodes']] = True
        # contacts
        self.passes = []
        self._setup_contacts()
        self.mass = self.mass_base.clone()
        for p in self.passes:
            self.mass.index_add_(0, p.s, 2 * p.k * p.pmax)
            # master nodes share the reaction; add a bound too (each tri node gets at most the node stiffness)
            self.mass.index_add_(0, p.tri.reshape(-1), (2 * p.k.mean() * p.pmax).expand(p.tri.numel()) / 3)
        self.mass = self.mass * 0.25 * 1.0 + 1e-12          # m >= h^2/4 * row sum (h = 1)
        self.mass_scale = torch.ones(N, dtype=DT, device=self.dev)
        self._setup_clusters()
        self.log = []
        self.pressure = []
        for L in self.feb['global_loads']: self._add_pressure(L)

    # ------------------------------------------------------------------ setup
    def _face_eps(self, faces):
        """FEBio auto penalty E_n * A / V per facet, from the deformable element that owns the facet."""
        X = self.feb['X']; owner = {}
        node_el = {}
        need = set(np.concatenate(faces).tolist())
        for bi, (conn, D, V) in enumerate(self.m['blocks_mech']):
            for e, row in enumerate(conn):
                for n in row:
                    if n in need: node_el.setdefault(n, []).append((bi, e))
        eps = []
        for f in faces:
            fs = set(f.tolist()); cand = node_el.get(f[0], [])
            own = next(((bi, e) for bi, e in cand if fs <= set(self.m['blocks_mech'][bi][0][e].tolist())), None)
            P = X[f]
            nrm = np.cross(P[1] - P[0], P[2] - P[0]) if len(f) == 3 else np.cross(P[2] - P[0], P[3] - P[1])
            A = 0.5 * np.linalg.norm(nrm); n = nrm / (2 * A)
            if own is None: eps.append(0.0); continue
            conn, D, V = self.m['blocks_mech'][own[0]]
            Sv = np.linalg.inv(D); v = np.array([n[0]**2, n[1]**2, n[2]**2, n[0] * n[1], n[1] * n[2], n[2] * n[0]])
            En = 1.0 / (v @ Sv @ v)
            eps.append(En * A / V[own[1]])
        return np.array(eps)

    def _node_eps(self, faces, eps_f):
        X = self.feb['X']
        def f(nodes):
            idx = {n: k for k, n in enumerate(nodes)}; num = np.zeros(len(nodes)); den = np.zeros(len(nodes))
            for fc, e in zip(faces, eps_f):
                for n in fc: num[idx[n]] += e; den[idx[n]] += 1
            return num / np.maximum(den, 1)
        return f

    def _setup_contacts(self):
        feb = self.feb; X = feb['X']
        for c in feb['contacts']:
            if c['name'] in self.o['disable_contacts']: continue
            ms, ss = feb['pairs'][c['pair']]
            mf, sf = feb['surfaces'][ms], feb['surfaces'][ss]
            pen = c.get('penalty', 1.0) * self.o['contact_penalty_mult']
            kind = 'tied' if c['type'] == 'tied-elastic' else 'sliding'
            mu = c.get('fric_coeff', 0.0) or 0.0
            if kind == 'sliding' and self.o['friction_override'] is not None and c['name'] in self.o['friction_override']:
                mu = self.o['friction_override'][c['name']]
            sr = c.get('search_radius', 1.0)
            if c['type'] == 'sliding-tension-compression': sr = sr * 145.71   # FEBio <= 3 relative radius (h05 note)
            plc = c.get('penalty_lc'); init = c.get('init_time', 0.0) if kind == 'tied' else 0.0
            passes = [(sf, mf)] + ([(mf, sf)] if c.get('two_pass', 0) else [])
            for slave, master in passes:
                if c.get('auto_penalty', 0):
                    eps_f = self._face_eps(slave) * pen
                else:
                    eps_f = np.full(len(slave), pen)
                p = contact.Pass(slave, master, X, self._node_eps(slave, eps_f), self.dev, kind, mu=mu, search_radius=sr)
                p.name = c['name']; p.plc = plc; p.init_time = init; p.tied_done = False
                p.pmax = 1.0 if plc is None else max(1.0, float(np.max(feb['lcs'][plc].y)))
                self.passes.append(p)

    def _add_pressure(self, L):
        faces = self.feb['surfaces'][L['surface']]
        q = np.array([f for f in faces if len(f) == 4]); t3 = np.array([f for f in faces if len(f) == 3])
        if len(t3): raise NotImplementedError('pressure on triangles')
        self.pressure.append(dict(q=torch.tensor(q, device=self.dev), lc=L['lc'], scale=L['scale']))

    # ------------------------------------------------------------------ forces
    def lc(self, i, t=None):
        return float(self.lcs[i](self.t if t is None else t))

    def _compiled(self, name, want):
        key = (name, want)
        if key not in self._cfun:
            fn = getattr(kern, name)
            self._cfun[key] = torch.compile(fn, dynamic=False) if self.o['compile'] else fn
        return self._cfun[key]

    def internal(self, x, want_stress=False):
        f = torch.zeros_like(x); out = {}; N = self.m['N']
        for g in self.groups:
            fn = self._compiled(g.kind, want_stress); p = g.prm
            if g.kind == 'neo': r = fn(x, g.conn, g.G, g.w, p['mu'], p['lam'], N, want_stress)
            elif g.kind == 'ortho': r = fn(x, g.conn, g.G, g.w, p['A'], g.mu_t, g.lam_t, N, want_stress)
            elif g.kind == 'hmfib':
                r = fn(x, g.conn, g.G, g.w, p['mu'], p['lam'], p['beta'], p['a0'], p['ksi0'], p['alpha0'], p['fbeta0'],
                       p['a1'], p['ksi1'], p['alpha1'], p['fbeta1'], N, want_stress)
            elif g.kind == 'gentps': r = fn(x, g.conn, g.G, g.w, g.V0, p['G'], p['k'], p['Jm'], self._Fp(g), N, want_stress)
            else: raise NotImplementedError(g.kind)
            if want_stress: f = f + r[0]; out[id(g)] = r[1]
            else: f = f + r
        return (f, out) if want_stress else f

    def _Fp(self, g):
        r = g.prm['ramp_scale'].clone(); lcid = g.prm['ramp_lc']
        for v in g.ramp_lcs:
            r = torch.where(lcid == v, r * self.lc(int(v)), r)
        I = torch.eye(3, dtype=DT, device=self.dev)
        return I * (1 - r)[:, None, None] + g.prm['F0'] * r[:, None, None]

    def springs_f(self, x, f):
        if self.spr is None: return
        sp = self.spr
        f += self._compiled('springs', False)(x, sp['i'], sp['j'], sp['L0'], sp['cid'], sp['x0'], sp['dx'], sp['ys'], self.m['N'])

    def pressure_f(self, x, f):
        if not self.pressure: return
        gp = torch.tensor([-1, 1], dtype=DT, device=self.dev) / np.sqrt(3)
        for P in self.pressure:
            p = P['scale'] * self.lc(P['lc'])
            if p == 0: continue
            xq = x[P['q']]                                          # (Q, 4, 3)
            for a in gp:
                for b in gp:
                    N = torch.stack([(1 - a) * (1 - b), (1 + a) * (1 - b), (1 + a) * (1 + b), (1 - a) * (1 + b)]) / 4
                    dNa = torch.stack([-(1 - b), (1 - b), (1 + b), -(1 + b)]) / 4
                    dNb = torch.stack([-(1 - a), -(1 + a), (1 + a), (1 - a)]) / 4
                    ta = (dNa[None, :, None] * xq).sum(1); tb = (dNb[None, :, None] * xq).sum(1)
                    nA = torch.cross(ta, tb, dim=-1)
                    fn = -p * N[None, :, None] * nA[:, None, :]
                    f.index_add_(0, P['q'].reshape(-1), fn.reshape(-1, 3))

    def contacts_f(self, x, f):
        for p in self.passes:
            psf = 1.0 if p.plc is None else self.lc(p.plc)
            if p.kind == 'tied' and self.t < p.init_time - 1e-12: continue
            p.forces(x, f, psf)

    def residual(self, x):
        fi = self.internal(x); self._fint = fi
        r = -fi
        self.springs_f(x, r); self.pressure_f(x, r); self.contacts_f(x, r)
        return r

    # ------------------------------------------------------------------ BC bookkeeping
    def _step_setup(self, step, t_start, t_end):
        N = self.m['N']; fixed = torch.zeros(N, 3, dtype=torch.bool, device=self.dev)
        bcs = list(self.feb['global_bcs']) + list(step['bcs'])
        rmode = {k: {d: 'free' for d in ('x', 'y', 'z', 'Rx', 'Ry', 'Rz')} for k in self.rb}
        rval = {k: {} for k in self.rb}
        presc_val = torch.zeros(N, 3, dtype=DT, device=self.dev); presc_lc = []
        for b in bcs:
            if b['kind'] == 'prescribe':
                ids = torch.tensor(self.feb['nodesets'][b['node_set']], device=self.dev); d = TRA[b['bc']]
                fixed[ids, d] = True; presc_lc.append((ids, d, torch.full((len(ids),), b['scale'], dtype=DT, device=self.dev), b['lc']))
            elif b['kind'] == 'fix':
                ids = torch.tensor(self.feb['nodesets'][b['node_set']], device=self.dev)
                for d in b['bc']: fixed[ids, TRA[d]] = True
            elif b['kind'] == 'rigid_fixed': rmode[b['mat']][b['bc']] = 'fixed'
            elif b['kind'] == 'rigid_prescribed': rmode[b['mat']][b['bc']] = 'presc'; rval[b['mat']][b['bc']] = b
            elif b['kind'] == 'rigid_force':
                rmode[b['mat']][b['bc']] = 'force'; bb = dict(b)
                if b['ramp']:
                    rb = self.rb[b['mat']]; d = b['bc']
                    bb['f0'] = float((rb['F'] if d in TRA else rb['M'])[TRA.get(d, ROT.get(d))])     # reaction at activation
                    bb['t0'], bb['t1'] = t_start, t_end
                rval[b['mat']][b['bc']] = bb
        self.fixed = fixed; self.rmode = rmode; self.rval = rval
        # nodes of a rigid body with all 6 dofs fixed are simply fixed
        self.presc = presc_lc                                        # fixes are zero displacement (FEBio 'fix')
        self._update_fixed_val()
        for L in step['loads']: self._add_pressure(L)

    def _update_fixed_val(self):
        v = self.X0.clone()
        for ids, d, val, lc in self.presc: v[ids, d] = self.X0[ids, d] + val * self.lc(lc)
        self.fixed_val = v

    def _rigid_targets(self, k):
        """prescribed dof values (absolute displacement from the initial COM / rotation vector) and applied loads."""
        F = torch.zeros(3, dtype=DT, device=self.dev); M = torch.zeros(3, dtype=DT, device=self.dev)
        for d, b in self.rval[k].items():
            if self.rmode[k][d] != 'force': continue
            if b.get('ramp'):
                w = (self.t - b['t0']) / max(b['t1'] - b['t0'], 1e-30); val = b['f0'] + (b['scale'] - b['f0']) * w
            else:
                val = b['scale'] * (self.lc(b['lc']) if b['lc'] else 1.0)
            (F if d in TRA else M)[TRA.get(d, ROT.get(d))] += val
        return F, M

    def _apply_rigid(self, x):
        for k, r in self.rb.items():
            x[r['nodes']] = r['c'] + r['r0'] @ r['R'].T


    # ------------------------------------------------------------------ coarse (rigid-cluster) correction
    def _setup_clusters(self):
        """clusters = nodes of the element blocks whose name starts with a prefix (a vertebra, the cage), plus the rigid
        bodies sharing nodes with them. Their 6 rigid modes are the slow modes of the relaxation (stiff bone moved by soft
        tissue); a Galerkin correction on these modes is solved every coarse_every iterations (two-level method)."""
        self.clusters = []
        blocks = self.feb['blocks']
        for name, pre in self.o['clusters']:
            ids = [b['conn'].ravel() for b in blocks if b['name'].startswith(pre)]
            if not ids: continue
            nodes = torch.tensor(np.unique(np.concatenate(ids)), device=self.dev)
            mask = torch.zeros(self.m['N'], dtype=torch.bool, device=self.dev); mask[nodes] = True
            rbs = [k for k, r in self.rb.items() if mask[r['nodes']].any()]
            for k in rbs: mask[self.rb[k]['nodes']] = True
            self.clusters.append(dict(name=name, mask=mask, nodes=torch.nonzero(mask)[:, 0], rbs=rbs))

    def _cluster_modes(self, cl):
        """allowed mode indices (0-2 translation, 3-5 rotation) given the current BCs; None if the cluster is held."""
        nodes = cl['nodes']
        if self.fixed[nodes].any(): return None
        allowed = [True] * 6
        for k in cl['rbs']:
            mode = self.rmode[k]
            for d, i in TRA.items():
                if mode[d] in ('fixed', 'presc'): allowed[i] = False
            for d, i in ROT.items():
                if mode[d] in ('fixed', 'presc'): allowed[3 + i] = False
        idx = [i for i in range(6) if allowed[i]]
        return idx or None

    def _gen_force(self, x, r, cl, p):
        nodes = cl['nodes']; rr = x[nodes] - p; fn = r[nodes]
        F = fn.sum(0); M = torch.cross(rr, fn, dim=-1).sum(0)
        for k in cl['rbs']:
            Fa, Ma = self._rigid_targets(k)
            F = F + Fa; M = M + Ma + torch.cross(self.rb[k]['c'] - p, Fa, dim=-1)
        return torch.cat([F, M])

    def _move(self, x, cl, p, d6):
        t, w = d6[:3], d6[3:]
        nodes = cl['nodes']; xn = x[nodes]
        Rw = rotvec_to_R(w)
        x = x.clone(); x[nodes] = p + t + (xn - p) @ Rw.T
        return x

    def coarse_step(self, x):
        changed = False
        for cl in self.clusters:
            idx = self._cluster_modes(cl)
            if idx is None: continue
            p = x[cl['nodes']].mean(0)
            r0 = self.residual(x); g0 = self._gen_force(x, r0, cl, p)[idx]
            n = len(idx); K = torch.zeros(n, n, dtype=DT, device=self.dev)
            for a, j in enumerate(idx):
                e = torch.zeros(6, dtype=DT, device=self.dev); e[j] = 1e-4 if j < 3 else 1e-5
                xj = self._move(x, cl, p, e)
                gj = self._gen_force(xj, self.residual(xj), cl, p)[idx]
                K[:, a] = -(gj - g0) / e[j]
            K = 0.5 * (K + K.T)
            try:
                dl = torch.linalg.solve(K + 1e-9 * K.diagonal().abs().max() * torch.eye(n, dtype=DT, device=self.dev), g0)
            except RuntimeError:
                continue
            d6 = torch.zeros(6, dtype=DT, device=self.dev); d6[idx] = dl
            n0 = g0.norm()
            for _ in range(4):                                   # backtracking on the generalised residual
                xn = self._move(x, cl, p, d6)
                if self._gen_force(xn, self.residual(xn), cl, p)[idx].norm() < n0: break
                d6 = d6 * 0.5
            else:
                continue
            x = xn; changed = True
            for k in cl['rbs']:                                  # keep the rigid-body state consistent
                rb = self.rb[k]; Rw = rotvec_to_R(d6[3:])
                rb['c'] = p + d6[:3] + Rw @ (rb['c'] - p); rb['R'] = Rw @ rb['R']
        return x, changed

    # ------------------------------------------------------------------ relaxation
    def relax(self, label=''):
        o = self.o; x = self.x; m = self.mass * self.mass_scale
        self._update_fixed_val()
        free = ~(self.fixed | self.is_rigid[:, None])
        x = torch.where(self.fixed, self.fixed_val, x); self._apply_rigid(x)
        dx = torch.zeros_like(x); r_prev = None; c = 0.0
        for p in self.passes:
            if p.kind != 'tied': p.search(x)
            if p.kind == 'sliding' and p.mu > 0: p.set_anchor(x)
        # rigid generalised masses
        for k, rb in self.rb.items():
            mn = m[rb['nodes']]; rr = x[rb['nodes']] - rb['c']
            rb['mt'] = mn.sum().clamp_min(1e-12)
            rb['I'] = (mn[:, None, None] * ((rr * rr).sum(-1)[:, None, None] * torch.eye(3, dtype=DT, device=self.dev) - rr[:, :, None] * rr[:, None, :])).sum(0) * 2.0
            rb['I'] = rb['I'] + 1e-12 * torch.eye(3, dtype=DT, device=self.dev)
            rb['v'].zero_(); rb['w'].zero_()
        osc = torch.zeros(self.m['N'], dtype=torch.int32, device=self.dev)
        t0 = _time.time(); it = 0; conv = False
        for it in range(1, o['max_iter'] + 1):
            if it % o['search_every'] == 0:
                for p in self.passes:
                    if p.kind != 'tied': p.search(x)
            if o['coarse_every'] and it % o['coarse_every'] == 0:
                x, ch = self.coarse_step(x)
                if ch:
                    dx = torch.zeros_like(x); r_prev = None
                    for rb in self.rb.values(): rb['v'].zero_(); rb['w'].zero_()
            r = self.residual(x)
            # rigid bodies: reduce nodal forces
            for k, rb in self.rb.items():
                rr = x[rb['nodes']] - rb['c']; fn = r[rb['nodes']]
                Fr = fn.sum(0); Mr = torch.cross(rr, fn, dim=-1).sum(0)
                Fa, Ma = self._rigid_targets(k)
                rb['F'], rb['M'] = -Fr, -Mr                         # reaction the body exerts / needs (FEBio 'rigid force')
                rb['Rf'], rb['Rm'] = Fr + Fa, Mr + Ma
            rf = torch.where(free, r, torch.zeros_like(r))
            # damping from the Rayleigh quotient (Joldes 2011, eq. 13)
            if r_prev is not None:
                num = (dx * (r_prev - rf)).sum(); den = (m[:, None] * dx * dx).sum()
                if den > 0 and num > 0:
                    om = torch.sqrt(num / den).item(); c = min(1.9, 2 * om) if it > 3 else c
            a_ = 2.0 / (2.0 + c); b_ = (2.0 - c) / (2.0 + c)
            dx_new = b_ * dx + a_ * rf / m[:, None]
            # local instability guard: growing period-2 oscillation -> heavier node
            prod = (dx_new * dx).sum(-1); grow = (prod < -0.81 * dx_new.norm(dim=-1) * dx.norm(dim=-1)) & (dx_new.norm(dim=-1) > 1.05 * dx.norm(dim=-1))
            osc = torch.where(grow, osc + 1, torch.zeros_like(osc))
            bad = osc >= 3
            if bad.any():
                self.mass_scale[bad] *= 2.0; m = self.mass * self.mass_scale; osc[bad] = 0
                dx_new[bad] = 0.0
            x = x + dx_new; dx = dx_new; r_prev = rf
            # rigid updates
            for k, rb in self.rb.items():
                mode = self.rmode[k]
                for d, i in TRA.items():
                    if mode[d] in ('fixed', 'presc'):
                        tgt = 0.0 if mode[d] == 'fixed' else self.rval[k][d]['scale'] * self.lc(self.rval[k][d]['lc'])
                        rb['v'][i] = rb['com0'][i] + tgt - rb['c'][i]
                    else:
                        rb['v'][i] = b_ * rb['v'][i] + a_ * rb['Rf'][i] / rb['mt']
                wd = torch.linalg.solve(rb['I'], rb['Rm'])
                for d, i in ROT.items():
                    if mode[d] in ('fixed', 'presc'):
                        cur = R_to_rotvec(rb['R'])[i]
                        tgt = 0.0 if mode[d] == 'fixed' else self.rval[k][d]['scale'] * self.lc(self.rval[k][d]['lc'])
                        rb['w'][i] = tgt - cur
                    else:
                        rb['w'][i] = b_ * rb['w'][i] + a_ * wd[i]
                rb['c'] = rb['c'] + rb['v']; rb['R'] = rotvec_to_R(rb['w']) @ rb['R']
            self._apply_rigid(x)
            if it >= o['min_iter'] and it % 25 == 0:
                fscale = max(self._fint.norm().item(), self.internal_scale * 1e-3, 1e-9)
                res = rf.norm().item() / fscale
                rbres = max([max(rb['Rf'].norm().item() / fscale * np.sqrt(len(rb['nodes'])), 0) for k, rb in self.rb.items()
                             if any(self.rmode[k][d] in ('free', 'force') for d in self.rmode[k])] or [0])
                dxm = dx.abs().max().item()
                if o['log_every'] and it % o['log_every'] == 0:
                    print(f'  {label} it {it} res {res:.2e} rb {rbres:.2e} dx {dxm:.2e} c {c:.3e}', flush=True)
                if res < o['tol_r'] and rbres < o['tol_r'] and dxm < o['tol_dx']:
                    conv = True; break
        self.x = x
        return dict(iters=it, converged=conv, seconds=_time.time() - t0)

    # ------------------------------------------------------------------ driver
    def run(self, t_stop=None, on_increment=None):
        t = 0.0; hist = []
        self.internal_scale = 1.0
        for si, st in enumerate(self.feb['steps']):
            ctl = st['control']; n = ctl['time_steps']; h = ctl['step_size']
            inc = self.o['increments_per_step'] or n
            t_end = t + n * h
            self._step_setup(st, t, t_end)
            for k in range(1, inc + 1):
                self.t = t + (t_end - t) * k / inc
                # ties are created at their init time
                for p in self.passes:
                    if p.kind == 'tied' and not p.tied_done and self.t >= p.init_time - 1e-12:
                        p.tie(self.x); p.tied_done = True
                self.internal_scale = max(self._force_scale(), 1e-6)
                info = self.relax(label=f"{st['name']} t={self.t:.4f}")
                row = self.record(); row.update(info, step=st['name'])
                hist.append(row)
                if self.o['verbose']:
                    print(f"[{st['name']}] t={self.t:.4f} iters {info['iters']} conv {info['converged']} {info['seconds']:.1f}s "
                          + ' '.join(f"{v['name']}: x {np.round(v['x'], 4).tolist()} th {np.round(v['th'], 5).tolist()} F {np.round(v['F'], 3).tolist()} M {np.round(v['M'], 2).tolist()}"
                                     for v in row['rigid'].values() if v['name'] != 'Fixed'), flush=True)
                if on_increment: on_increment(self, row)
                if t_stop is not None and self.t >= t_stop - 1e-12: return hist
            t = t_end
        return hist

    def _force_scale(self):
        f = self.internal(self.x)
        s = float(f.abs().sum().item()) / max(len(f), 1)
        ext = sum(abs(v) for k in self.rb for v in torch.cat(self._rigid_targets(k)).tolist())
        return max(s * np.sqrt(len(f)), ext, 1.0)

    def record(self):
        out = dict(t=self.t, rigid={})
        for k, rb in self.rb.items():
            out['rigid'][k] = dict(name=rb['name'], x=(rb['c'] - rb['com0']).tolist(), th=R_to_rotvec(rb['R']).tolist(),
                                   F=rb['F'].tolist(), M=rb['M'].tolist())
        out['contacts'] = {}
        for p in self.passes:
            out['contacts'].setdefault(p.name, 0.0)
            out['contacts'][p.name] += float(p.force_t.norm(dim=-1).sum().item()) if p.force_t is not None else 0.0
        return out
