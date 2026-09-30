"""GPU voxel finite-element solver (PyTorch, fp64) for cage / vertebra contact problems.

Model
-----
* Structured 8-node trilinear hexahedra (voxel size h), small-strain linear elasticity, per-element Lame parameters.
* Two bodies on the same lattice with duplicated nodes: BONE (C3 + C4, labels 1-4) and CAGE (PLCL cage 5 + biodisc 6).
  The biodisc is bonded to the cage; bodies interact ONLY through contact (normal pressure + Coulomb friction).
* Contact: node-to-node pairs at every lattice node shared by a bone voxel and a cage-body voxel (conformal initial
  state, zero gap). Normal n = outward bone normal from a smoothed bone indicator (so sloped endplates and lug flanks get
  their true orientation, not the voxel staircase). Penalty kN = pf*E_cage*A/h, kT = kN, stick/slip return mapping with a
  slip history s per pair (needed for unloading / cyclic loading).
* Loading: C4 bottom face fixed. C3 top face kinematically tied to a rigid reference point (6 DOF q = [U, theta]);
  each q component is displacement- or force-controlled.
* Damage: cage elements whose von Mises or max principal stress exceed the breakage limits are deleted (stiffness x1e-3);
  progressive within each increment until no new failures. Fatigue damage handled by the cyclic driver.
* Linear solves: matrix-free Jacobi-PCG on the GPU with warm start; outer active-set iterations for contact.
"""
import math, time
import numpy as np
import torch
from scipy import ndimage as ndi

DT = torch.float64
CORNERS = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]


def hex_B(h, xi):
    """Strain-displacement matrix (6x24) of a cube element of size h at natural point xi in [-1,1]^3."""
    B = np.zeros((6, 24))
    for n, (a, b, c) in enumerate(CORNERS):
        sa, sb, sc = 2 * a - 1, 2 * b - 1, 2 * c - 1
        dx = sa * (1 + sb * xi[1]) * (1 + sc * xi[2]) / 8 * 2 / h
        dy = sb * (1 + sa * xi[0]) * (1 + sc * xi[2]) / 8 * 2 / h
        dz = sc * (1 + sa * xi[0]) * (1 + sb * xi[1]) / 8 * 2 / h
        j = 3 * n
        B[0, j] = dx; B[1, j + 1] = dy; B[2, j + 2] = dz
        B[3, j] = dy; B[3, j + 1] = dx          # gamma_xy
        B[4, j + 1] = dz; B[4, j + 2] = dy      # gamma_yz
        B[5, j] = dz; B[5, j + 2] = dx          # gamma_xz
    return B


def hex_K_parts(h):
    """K = lam*Kl + mu*Km for an isotropic cube element (2x2x2 Gauss)."""
    Dl = np.zeros((6, 6)); Dl[:3, :3] = 1.0
    Dm = np.diag([2, 2, 2, 1, 1, 1.0])
    g = 1 / math.sqrt(3); Kl = np.zeros((24, 24)); Km = np.zeros((24, 24))
    for xi in [(a, b, c) for a in (-g, g) for b in (-g, g) for c in (-g, g)]:
        B = hex_B(h, xi); w = (h / 2) ** 3
        Kl += B.T @ Dl @ B * w; Km += B.T @ Dm @ B * w
    return Kl, Km


def lame(E, nu):
    return E * nu / ((1 + nu) * (1 - 2 * nu)), E / (2 * (1 + nu))


class Body:
    """Dense sub-lattice holding one body. Elements: (ex,ey,ez) ; nodes (ex+1,ey+1,ez+1)."""

    def __init__(self, occ_lab, off, lam, mu, dev):
        self.off = np.array(off)
        self.shape = occ_lab.shape
        self.lam0 = torch.tensor(lam, dtype=DT, device=dev)
        self.mu0 = torch.tensor(mu, dtype=DT, device=dev)
        self.dmg = torch.ones_like(self.lam0)            # stiffness multiplier (1 intact, 1e-3 failed)
        occ = lam + mu > 0
        nodeocc = np.zeros(tuple(s + 1 for s in self.shape), bool)
        for a, b, c in CORNERS:
            nodeocc[a:a + self.shape[0], b:b + self.shape[1], c:c + self.shape[2]] |= occ
        self.node_active = torch.tensor(nodeocc, device=dev)
        self.nshape = nodeocc.shape

    @property
    def lam(self): return self.lam0 * self.dmg

    @property
    def mu(self): return self.mu0 * self.dmg


class VoxelContactModel:
    def __init__(self, L, h, origin, ref_point, mat, contact, dev='cuda', cage_labels=(5, 6), log=print):
        self.dev = dev; self.h = h; self.log = log
        self.origin = np.array(origin, float)
        self.ref = np.array(ref_point, float)
        self.mu_f = contact['mu']
        Kl, Km = hex_K_parts(h)
        self.Kl = torch.tensor(Kl, dtype=DT, device=dev); self.Km = torch.tensor(Km, dtype=DT, device=dev)
        self.dKl = torch.tensor(np.diag(Kl), dtype=DT, device=dev); self.dKm = torch.tensor(np.diag(Km), dtype=DT, device=dev)
        Bc = hex_B(h, (0, 0, 0)); self.Bc = torch.tensor(Bc, dtype=DT, device=dev)
        props = {1: mat['cancellous'], 2: mat['cortical'], 3: mat['cancellous'], 4: mat['cortical'], 5: mat['PLCL'], 6: mat['biodisc']}
        lamv = np.zeros(8); muv = np.zeros(8)
        for k, p in props.items(): lamv[k], muv[k] = lame(p['E'], p['nu'])
        self.L = L
        # ---- bone body: full lattice
        bone = np.isin(L, (1, 2, 3, 4))
        self.bone = Body(L, (0, 0, 0), np.where(bone, lamv[L], 0), np.where(bone, muv[L], 0), dev)
        # ---- cage body: cropped in z to its extent (+1)
        cg = np.isin(L, cage_labels)
        kk = np.where(cg.any((0, 1)))[0]; k0, k1 = kk.min(), kk.max() + 1
        Lc = L[:, :, k0:k1]; cgc = cg[:, :, k0:k1]
        self.cage = Body(Lc, (0, 0, k0), np.where(cgc, lamv[Lc], 0), np.where(cgc, muv[Lc], 0), dev)
        self.is_plcl = torch.tensor(Lc == 5, device=dev)
        self.cage_vol = float((L == 5).sum()) * h ** 3
        self.sig_vm_fail = mat['PLCL']['sigma_vm_fail']; self.sig_1_fail = mat['PLCL']['sigma_1_fail']
        # ---- boundary sets on bone
        nx, ny, nz = L.shape
        bn = self.bone.node_active
        self.fixed = torch.zeros_like(bn); self.fixed[:, :, 0] = bn[:, :, 0]          # C4 base
        self.tied = torch.zeros_like(bn); self.tied[:, :, nz] = bn[:, :, nz]           # C3 top -> rigid ref
        ii, jj, kk_ = torch.meshgrid(*[torch.arange(s, device=dev, dtype=DT) for s in bn.shape], indexing='ij')
        self.bone_xyz = torch.stack([ii * h + origin[0], jj * h + origin[1], kk_ * h + origin[2]], -1)
        self.r_tied = (self.bone_xyz - torch.tensor(self.ref, dtype=DT, device=dev))[self.tied]   # (Nt,3)
        # ---- contact pairs
        self._build_pairs(L, cg, bone, contact, mat)
        # ---- dof bookkeeping
        self.nb = int(np.prod(self.bone.nshape)) * 3; self.nc = int(np.prod(self.cage.nshape)) * 3
        self.N = self.nb + self.nc + 6
        mb = (self.bone.node_active & ~self.fixed & ~self.tied)[..., None].expand(*self.bone.nshape, 3).reshape(-1)
        mc = self.cage.node_active[..., None].expand(*self.cage.nshape, 3).reshape(-1)
        self.free_mask = torch.cat([mb, mc, torch.ones(6, dtype=torch.bool, device=dev)]).to(DT)
        # ---- state
        self.x = torch.zeros(self.N, dtype=DT, device=dev)
        self.s_hist = torch.zeros(self.np_, 3, dtype=DT, device=dev)       # converged slip history
        self.s_eff = torch.zeros(self.np_, 3, dtype=DT, device=dev)        # iterate: effective spring offset
        self.status = torch.zeros(self.np_, dtype=torch.int8, device=dev)  # 0 open, 1 stick, 2 slip
        self.lamN = torch.zeros(self.np_, dtype=DT, device=dev)
        self.tdir = torch.zeros(self.np_, 3, dtype=DT, device=dev)
        # weak stabilisation (rigid modes when contact opens / fully slips)
        self.k_stab_q = torch.tensor([0.5, 0.5, 0.5, 50., 50., 50.], dtype=DT, device=dev)   # N/mm, Nmm/rad
        self.k_stab_cage = 1e-8 * mat['PLCL']['E'] * h
        self.log(f'model: bone nodes {int(self.bone.node_active.sum())}, cage nodes {int(self.cage.node_active.sum())}, '
                 f'pairs {self.np_}, free dofs {int(self.free_mask.sum())}, PLCL vol {self.cage_vol:.1f} mm3')

    # ------------------------------------------------------------------ contact pairs
    def _build_pairs(self, L, cg, bone, contact, mat):
        h = self.h; nx, ny, nz = L.shape
        # tributary interface area per node from voxel faces separating cage-body and bone voxels
        area = np.zeros((nx + 1, ny + 1, nz + 1))
        for ax in range(3):
            a = [slice(None)] * 3; b = [slice(None)] * 3
            a[ax] = slice(0, -1); b[ax] = slice(1, None)
            face = (cg[tuple(a)] & bone[tuple(b)]) | (bone[tuple(a)] & cg[tuple(b)])   # face between voxel i and i+1 along ax
            idx = np.array(np.nonzero(face)); idx[ax] += 1                            # node-plane index of the face
            others = [d for d in range(3) if d != ax]
            for d1 in (0, 1):
                for d2 in (0, 1):
                    q = idx.copy(); q[others[0]] += d1; q[others[1]] += d2
                    np.add.at(area, tuple(q), h * h / 4)
        pn = np.array(np.nonzero(area > 0)).T                 # lattice node coords of pairs
        # outward bone normal from smoothed bone indicator at nodes
        bnode = np.zeros((nx + 1, ny + 1, nz + 1))
        for c in CORNERS:
            bnode[c[0]:c[0] + nx, c[1]:c[1] + ny, c[2]:c[2] + nz] += bone
        bnode = ndi.gaussian_filter(bnode / 8, 1.5)
        g = np.stack(np.gradient(bnode), -1)[tuple(pn.T)]
        n = -g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
        dev = self.dev
        self.np_ = len(pn)
        self.pn = torch.tensor(pn, device=dev)
        self.pnrm = torch.tensor(n, dtype=DT, device=dev)
        A = area[tuple(pn.T)]; self.parea = torch.tensor(A, dtype=DT, device=dev)
        # penalty scaled to the cage-side material at the node (PLCL if any adjacent PLCL voxel, else biodisc)
        adj_plcl = np.zeros(len(pn), bool)
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    adj_plcl |= L[np.clip(pn[:, 0] - a, 0, nx - 1), np.clip(pn[:, 1] - b, 0, ny - 1), np.clip(pn[:, 2] - c, 0, nz - 1)] == 5
        Eloc = np.where(adj_plcl, mat['PLCL']['E'], mat['biodisc']['E'])
        self.p_plcl = torch.tensor(adj_plcl, device=self.dev)
        kN = contact['penalty_factor'] * Eloc * A / h
        self.kN = torch.tensor(kN, dtype=DT, device=dev); self.kT = contact.get('kT_ratio', 0.1) * self.kN
        # flat node indices in each body
        bshape = (nx + 1, ny + 1, nz + 1)
        self.p_b = torch.tensor(np.ravel_multi_index(tuple(pn.T), bshape), device=dev)
        k0 = self.cage.off[2]
        cshape = self.cage.nshape
        self.p_c = torch.tensor(np.ravel_multi_index((pn[:, 0], pn[:, 1], pn[:, 2] - k0), cshape), device=dev)
        # interface side: C3 pairs lie above the reference mid-plane, C4 pairs below
        zc = pn[:, 2] * h + self.origin[2]
        self.p_upper = torch.tensor(zc > self.ref[2], device=dev)

    # ------------------------------------------------------------------ helpers
    def split(self, x):
        ub = x[:self.nb].view(*self.bone.nshape, 3)
        uc = x[self.nb:self.nb + self.nc].view(*self.cage.nshape, 3)
        return ub, uc, x[-6:]

    def rigid_disp(self, q):
        return q[:3][None] + torch.cross(q[3:][None].expand_as(self.r_tied), self.r_tied, dim=1)

    def body_force(self, body, u):
        ex, ey, ez = body.shape
        ue = torch.cat([u[a:a + ex, b:b + ey, c:c + ez] for a, b, c in CORNERS], -1)        # (ex,ey,ez,24)
        fe = body.lam[..., None] * (ue @ self.Kl) + body.mu[..., None] * (ue @ self.Km)
        f = torch.zeros_like(u)
        for n, (a, b, c) in enumerate(CORNERS):
            f[a:a + ex, b:b + ey, c:c + ez] += fe[..., 3 * n:3 * n + 3]
        return f

    def body_diag(self, body):
        ex, ey, ez = body.shape
        de = body.lam[..., None] * self.dKl + body.mu[..., None] * self.dKm
        d = torch.zeros(*body.nshape, 3, dtype=DT, device=self.dev)
        for n, (a, b, c) in enumerate(CORNERS):
            d[a:a + ex, b:b + ey, c:c + ez] += de[..., 3 * n:3 * n + 3]
        return d

    def rel_disp(self, ub, uc):
        return uc.reshape(-1, 3)[self.p_c] - ub.reshape(-1, 3)[self.p_b]

    # ------------------------------------------------------------------ linear operator for a fixed contact status
    def apply(self, x):
        ub, uc, q = self.split(x)
        ub = ub.clone()
        ub[self.tied] = self.rigid_disp(q)
        fb = self.body_force(self.bone, ub)
        fc = self.body_force(self.cage, uc) + self.k_stab_cage * uc
        d = self.rel_disp(ub, uc); n = self.pnrm
        dn = (d * n).sum(1, keepdim=True)
        closed = (self.status > 0)[:, None].to(DT)
        fp = closed * (self.kN[:, None] * dn * n + self.kT[:, None] * (d - dn * n))
        fc.view(-1, 3).index_add_(0, self.p_c, fp)
        fb.view(-1, 3).index_add_(0, self.p_b, -fp)
        ft = fb[self.tied]
        Fq = torch.cat([ft.sum(0), torch.cross(self.r_tied, ft, dim=1).sum(0)]) + self.k_stab_q * q
        fb[self.tied] = 0
        return torch.cat([fb.reshape(-1), fc.reshape(-1), Fq]) * self.free_mask

    def diag(self):
        db = self.body_diag(self.bone); dc = self.body_diag(self.cage) + self.k_stab_cage
        n = self.pnrm
        closed = (self.status > 0)[:, None].to(DT)
        dp = closed * (self.kN[:, None] * n * n + self.kT[:, None] * (1 - n * n))
        dc.view(-1, 3).index_add_(0, self.p_c, dp); db.view(-1, 3).index_add_(0, self.p_b, dp)
        dt = db[self.tied]
        r2 = (self.r_tied ** 2).sum(1, keepdim=True)
        dq = torch.cat([dt.sum(0), (dt * (r2 - self.r_tied ** 2)).sum(0)]) + self.k_stab_q
        out = torch.cat([db.reshape(-1), dc.reshape(-1), dq])
        out = torch.where(out > 0, out, torch.ones_like(out))
        return out

    def rhs_contact(self):
        """RHS of the tangential springs: kT * s_eff on closed pairs (s_eff = committed slip for sticking pairs,
        return-mapped slip for slipping pairs, so that the spring force equals mu*lamN on slipping pairs)."""
        f = torch.zeros(self.N, dtype=DT, device=self.dev)
        fb = f[:self.nb].view(-1, 3); fc = f[self.nb:self.nb + self.nc].view(-1, 3)
        closed = (self.status > 0)[:, None].to(DT)
        fp = closed * self.kT[:, None] * self.s_eff
        fc.index_add_(0, self.p_c, fp); fb.index_add_(0, self.p_b, -fp)
        return f

    def pcg(self, b, x0, tol=1e-6, maxit=4000):
        Minv = self.free_mask / self.diag()
        x = x0 * self.free_mask
        r = b - self.apply(x); z = Minv * r; p = z.clone(); rz = (r * z).sum()
        bn = torch.linalg.norm(b) + 1e-30
        for it in range(maxit):
            Ap = self.apply(p); alpha = rz / (p * Ap).sum()
            x += alpha * p; r -= alpha * Ap
            res = torch.linalg.norm(r) / bn
            if res < tol: break
            z = Minv * r; rz_new = (r * z).sum(); p = z + (rz_new / rz) * p; rz = rz_new
        return x, it + 1, float(res)

    # ------------------------------------------------------------------ contact update
    def update_contact(self, x):
        ub, uc, q = self.split(x)
        ub = ub.clone(); ub[self.tied] = self.rigid_disp(q)
        d = self.rel_disp(ub, uc); n = self.pnrm
        dn = (d * n).sum(1)
        lamN = torch.clamp(-self.kN * dn, min=0)            # compressive when cage moves into bone (dn<0)
        dT = d - dn[:, None] * n
        s_t = self.s_hist - (self.s_hist * n).sum(1, keepdim=True) * n
        ttrial = -self.kT[:, None] * (dT - s_t)
        tn = torch.linalg.norm(ttrial, dim=1)
        new = torch.where(dn < 0, torch.where(tn <= self.mu_f * lamN, 1, 2), 0).to(torch.int8)
        tdir = -ttrial / tn.clamp(min=1e-30)[:, None]      # unit vector of (slip) = opposite to friction on cage
        s_slip = dT - (self.mu_f * lamN / self.kT)[:, None] * tdir
        s_eff = torch.where((new == 2)[:, None], s_slip, s_t)
        return new, lamN, tdir, dT, s_t, s_eff

    def commit_slip(self, x):
        """After convergence of an increment: update slip history for slipping pairs, clear for open pairs."""
        new, lamN, tdir, dT, s_t, s_eff = self.update_contact(x)
        self.s_hist = torch.where((new == 0)[:, None], dT, s_eff)
        self.s_eff = self.s_hist.clone()

    def solve_increment(self, q_presc, F_ext, max_outer=15, tol=1e-6, verbose=False, dx_tol=5e-3, chg_frac=1 / 40):
        """q_presc: dict {dof_index: value} displacement-controlled rigid DOFs; F_ext: (6,) applied load on the rest."""
        dev = self.dev
        qmask = torch.ones(6, dtype=DT, device=dev); qv = torch.zeros(6, dtype=DT, device=dev)
        for k, v in q_presc.items(): qmask[k] = 0; qv[k] = v
        self.free_mask[-6:] = qmask
        x = self.x.clone(); x[-6:] = torch.where(qmask > 0, x[-6:], qv)
        Fe = torch.as_tensor(F_ext, dtype=DT, device=dev) * qmask
        total_it = 0; t0 = time.time()
        if (self.status == 0).all():
            self.status[:] = 1
        x_start = x.clone()
        for outer in range(max_outer):
            xp = torch.zeros_like(x); xp[-6:] = (1 - qmask) * qv
            b = self.rhs_contact(); b[-6:] += Fe
            b = b - self.apply_full_presc(xp)
            x_old = x.clone()
            dx, it, res = self.pcg(b * self.free_mask, x * self.free_mask, tol=tol)
            x = dx * self.free_mask + xp
            total_it += it
            new, lamN, tdir, _, _, s_eff = self.update_contact(x)
            changed = int((new != self.status).sum())
            dxr = float(torch.linalg.norm(x - x_old) / (torch.linalg.norm(x - x_start) + 1e-30))
            self.status, self.lamN, self.tdir, self.s_eff = new, lamN, tdir, s_eff
            if verbose: self.log(f'   outer {outer}: pcg {it} it res {res:.1e}, status changed {changed} (slip {int((new == 2).sum())}, open {int((new == 0).sum())}), |dx|/|Dx| {dxr:.2e}')
            if outer > 0 and changed <= max(5, int(self.np_ * chg_frac)) and dxr < dx_tol:
                break
        self.x = x
        return dict(outer=outer + 1, pcg_it=total_it, t=time.time() - t0)

    def apply_full_presc(self, xp):
        """Internal force of a vector that only contains prescribed rigid DOFs (for moving them to the RHS)."""
        fm = self.free_mask.clone(); self.free_mask[:] = 1
        f = self.apply(xp)
        self.free_mask[:] = fm
        return f

    # ------------------------------------------------------------------ results
    def reaction(self):
        """Resultant load transmitted through the C3 top face (N, Nmm), = force applied to the rigid reference."""
        fm = self.free_mask.clone(); self.free_mask[:] = 1
        x = self.x.clone()
        f = self.apply(x)
        self.free_mask[:] = fm
        return (f[-6:] - self.k_stab_q * self.x[-6:]).cpu().numpy()

    def cage_stress(self):
        """Element-centre stress in the cage body: returns von Mises, max principal, full tensor (ex,ey,ez,...)"""
        ub, uc, q = self.split(self.x)
        b = self.cage; ex, ey, ez = b.shape
        ue = torch.cat([uc[a:a + ex, bb:bb + ey, c:c + ez] for a, bb, c in CORNERS], -1)
        eps = ue @ self.Bc.T                                           # (…,6) engineering strains
        tr = eps[..., :3].sum(-1, keepdim=True)
        lam, mu = b.lam[..., None], b.mu[..., None]
        sig = torch.cat([lam * tr + 2 * mu * eps[..., :3], mu * eps[..., 3:]], -1)   # sxx syy szz sxy syz sxz
        sxx, syy, szz, sxy, syz, sxz = sig.unbind(-1)
        vm = torch.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + sxz ** 2))
        S = torch.stack([torch.stack([sxx, sxy, sxz], -1), torch.stack([sxy, syy, syz], -1), torch.stack([sxz, syz, szz], -1)], -2)
        m = self.is_plcl
        s1 = torch.zeros_like(vm); s3 = torch.zeros_like(vm)
        ev = torch.linalg.eigvalsh(S[m]); s1[m] = ev[:, 2]; s3[m] = ev[:, 0]
        return vm, s1, s3, sig

    def damage_fraction(self):
        failed = self.is_plcl & (self.cage.dmg < 0.5)
        return float(failed.sum()) * self.h ** 3 / self.cage_vol

    def apply_failure(self, vm, s1, max_frac_per_pass=0.01):
        intact = self.is_plcl & (self.cage.dmg > 0.5)
        crit = torch.maximum(vm / self.sig_vm_fail, s1 / self.sig_1_fail)
        over = intact & (crit >= 1.0)
        n_over = int(over.sum())
        if n_over == 0: return 0
        cap = max(1, int(max_frac_per_pass * int(self.is_plcl.sum())))
        if n_over > cap:                                 # fail the most over-stressed first (stable progressive failure)
            thr = torch.topk(crit[over], cap).values[-1]
            over = over & (crit >= thr)
        self.cage.dmg[over] = 1e-3
        return int(over.sum())

    def interface_slip(self):
        """Mean relative tangential displacement (vector mean, mm) of cage vs C4 and vs C3 over closed/all pairs."""
        ub, uc, q = self.split(self.x)
        ub = ub.clone(); ub[self.tied] = self.rigid_disp(q)
        d = self.rel_disp(ub, uc); n = self.pnrm
        dT = d - (d * n).sum(1, keepdim=True) * n
        lo = dT[~self.p_upper].mean(0); up = dT[self.p_upper].mean(0)
        return float(torch.linalg.norm(lo[:2])), float(torch.linalg.norm(up[:2])), lo.cpu().numpy(), up.cpu().numpy()

    def contact_pressure(self):
        return (self.lamN / self.parea).cpu().numpy(), self.status.cpu().numpy()

    def snapshot(self):
        return dict(x=self.x.clone(), s=self.s_hist.clone(), se=self.s_eff.clone(), st=self.status.clone(), lamN=self.lamN.clone(),
                    tdir=self.tdir.clone(), dmg=self.cage.dmg.clone())

    def restore(self, sn):
        self.x = sn['x'].clone(); self.s_hist = sn['s'].clone(); self.s_eff = sn['se'].clone(); self.status = sn['st'].clone()
        self.lamN = sn['lamN'].clone(); self.tdir = sn['tdir'].clone(); self.cage.dmg = sn['dmg'].clone()
