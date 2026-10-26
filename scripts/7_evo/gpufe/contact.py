"""Node-to-facet penalty contact (explicit / dynamic relaxation), following FEBio's sliding-elastic and tied-elastic logic.

Slave side: nodes with tributary areas (facet area / n per node). Master side: triangles (quads split in two).
Penalty (FEBio auto_penalty, FEContactInterface::AutoPenalty): eps = penalty * E_n * A / V of the facet's own element
(N / mm^3, traction = eps * gap); per slave node eps from its facets (area-weighted), force = eps * A_node * gap.
sliding (frictionless or Coulomb friction, FESlidingElasticInterface::ContactTraction):
  stick trial with the anchor = master point under the slave node at the start of the load increment:
     t = eps * (x_anchor - x_slave);  stick if t_n < 0 (compressive) and |t_t| < mu |t_n|
  else slip: p_n = max(eps * g, 0), t = p_n * n_master + mu * p_n * (direction of the tangential part of x_anchor - x_slave)
tied (FETiedElasticInterface): x_slave is held to its master point (fixed barycentric coordinates) at the tie time, offset kept.
two_pass: the same with the roles swapped, both passes added (as FEBio).
"""
import numpy as np, torch
from mech import DT


def tri_faces(faces):
    out = []
    for f in faces:
        if len(f) == 3: out.append(f)
        elif len(f) == 4: out.append(f[[0, 1, 2]]); out.append(f[[0, 2, 3]])
        else: raise NotImplementedError('facet with %d nodes' % len(f))
    return np.array(out)


def node_areas(faces, X):
    nodes = np.unique(np.concatenate(faces)); idx = {n: k for k, n in enumerate(nodes)}; A = np.zeros(len(nodes))
    fa = []
    for f in faces:
        P = X[f]
        a = 0.5 * np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) if len(f) == 3 else \
            0.5 * np.linalg.norm(np.cross(P[2] - P[0], P[3] - P[1]))
        fa.append(a)
        for n in f: A[idx[n]] += a / len(f)
    return nodes, A, np.array(fa)


def closest_on_tris(p, a, b, c):
    """Closest point on triangles (Ericson, Real-Time Collision Detection 5.1.5), batched. Returns barycentrics (.., 3)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = p - b; d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = p - c; d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc
    den = torch.where(den.abs() < 1e-30, torch.full_like(den, 1e-30), den)
    v = vb / den; w = vc / den; u = 1 - v - w                             # interior
    L = torch.stack([u, v, w], -1)
    def setw(mask, val):
        nonlocal L
        L = torch.where(mask[..., None], val, L)
    one, zero = torch.ones_like(d1), torch.zeros_like(d1)
    # edge regions
    m_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0); t_ab = d1 / torch.where((d1 - d3).abs() < 1e-30, one, d1 - d3)
    setw(m_ab, torch.stack([1 - t_ab, t_ab, zero], -1))
    m_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0); t_ac = d2 / torch.where((d2 - d6).abs() < 1e-30, one, d2 - d6)
    setw(m_ac, torch.stack([1 - t_ac, zero, t_ac], -1))
    m_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    den_bc = (d4 - d3) + (d5 - d6); t_bc = (d4 - d3) / torch.where(den_bc.abs() < 1e-30, one, den_bc)
    setw(m_bc, torch.stack([zero, 1 - t_bc, t_bc], -1))
    # vertex regions
    setw((d1 <= 0) & (d2 <= 0), torch.stack([one, zero, zero], -1))
    setw((d3 >= 0) & (d4 <= d3), torch.stack([zero, one, zero], -1))
    setw((d6 >= 0) & (d5 <= d6), torch.stack([zero, zero, one], -1))
    return L


class Pass:
    """one slave-node / master-triangle pass."""
    def __init__(self, slave_faces, master_faces, X, eps_node, dev, kind, mu=0.0, search_radius=1.0, k_cand=8):
        self.kind = kind; self.mu = mu; self.R = search_radius; self.K = k_cand
        nodes, A, _ = node_areas(slave_faces, X)
        self.s = torch.tensor(nodes, device=dev); self.A = torch.tensor(A, dtype=DT, device=dev)
        self.k = torch.tensor(eps_node(nodes) * A, dtype=DT, device=dev)          # N / mm per node
        self.tri = torch.tensor(tri_faces(master_faces), device=dev)
        n = len(nodes)
        self.cand = None
        self.anchor_tri = torch.zeros(n, dtype=torch.long, device=dev); self.anchor_L = torch.zeros(n, 3, dtype=DT, device=dev)
        self.anchor_ok = torch.zeros(n, dtype=torch.bool, device=dev)
        self.tie_off = None
        self.force_n = torch.zeros(n, dtype=DT, device=dev); self.force_t = torch.zeros(n, 3, dtype=DT, device=dev)
        self.stick = torch.zeros(n, dtype=torch.bool, device=dev); self.gap = torch.zeros(n, dtype=DT, device=dev)
        self._fn = None

    def search(self, x):
        """candidate master triangles: the K nearest centroids of each slave node (brute force in chunks)."""
        cen = x[self.tri].mean(1); ps = x[self.s]; out = []
        for s0 in range(0, len(ps), 4096):
            d = torch.cdist(ps[s0:s0 + 4096], cen)
            out.append(torch.topk(d, min(self.K, cen.shape[0]), largest=False).indices)
        self.cand = torch.cat(out)

    def project(self, x):
        if self.cand is None: self.search(x)
        ps = x[self.s]; T = self.tri[self.cand]                 # (n, K, 3)
        a, b, c = x[T[..., 0]], x[T[..., 1]], x[T[..., 2]]
        L = closest_on_tris(ps[:, None], a, b, c)
        q = L[..., 0:1] * a + L[..., 1:2] * b + L[..., 2:3] * c
        d = (ps[:, None] - q).norm(dim=-1)
        k = d.argmin(1); ar = torch.arange(len(ps), device=x.device)
        tri = T[ar, k]; Lk = L[ar, k]
        A_, B_, C_ = a[ar, k], b[ar, k], c[ar, k]
        nrm = torch.cross(B_ - A_, C_ - A_, dim=-1); nrm = nrm / nrm.norm(dim=-1, keepdim=True).clamp_min(1e-30)
        return tri, Lk, q[ar, k], nrm, d[ar, k]

    def set_anchor(self, x):
        tri, L, q, nrm, d = self.project(x)
        self.anchor_tri, self.anchor_L, self.anchor_ok = tri, L, d < self.R

    def tie(self, x):
        self.search(x)
        tri, L, q, nrm, d = self.project(x)
        self.anchor_tri, self.anchor_L = tri, L
        self.tie_off = x[self.s] - q
        self.anchor_ok = d < self.R

    def forces(self, x, f, psf=1.0):
        """adds contact forces to f (N, 3) in place; master nodes get the reaction through the barycentrics."""
        if psf == 0 or (self.kind == 'tied' and self.tie_off is None): self.force_n.zero_(); self.force_t.zero_(); return
        if self.cand is None: self.search(x)
        if self._fn is None:
            fn = tied_fn if self.kind == 'tied' else sliding_fn
            self._fn = torch.compile(fn, dynamic=False) if COMPILE else fn
        k = self.k * psf
        if self.kind == 'tied':
            fa, fs = self._fn(x, self.s, self.anchor_tri, self.anchor_L, self.tie_off, self.anchor_ok, k, x.shape[0])
            self.force_t = fs
        else:
            fa, fs, fn_, stick, g = self._fn(x, self.s, self.tri[self.cand], k, self.R, self.mu, self.anchor_tri, self.anchor_L,
                                             self.anchor_ok, x.shape[0])
            self.force_t, self.force_n, self.stick, self.gap = fs, fn_, stick, g
        f += fa


COMPILE = True


def _project(ps, T, x):
    a, b, c = x[T[..., 0]], x[T[..., 1]], x[T[..., 2]]
    L = closest_on_tris(ps[:, None], a, b, c)
    q = L[..., 0:1] * a + L[..., 1:2] * b + L[..., 2:3] * c
    d = ((ps[:, None] - q)**2).sum(-1)
    k = d.argmin(1); ar = torch.arange(ps.shape[0], device=x.device)
    A_, B_, C_ = a[ar, k], b[ar, k], c[ar, k]
    nrm = torch.cross(B_ - A_, C_ - A_, dim=-1); nrm = nrm / nrm.norm(dim=-1, keepdim=True).clamp_min(1e-30)
    return T[ar, k], L[ar, k], q[ar, k], nrm, torch.sqrt(d[ar, k])


def sliding_fn(x, s, T, k, R: float, mu: float, anchor_tri, anchor_L, anchor_ok, N: int):
    ps = x[s]
    tri, L, q, nrm, d = _project(ps, T, x)
    g = ((q - ps) * nrm).sum(-1)                              # > 0: slave behind the master facet (penetration)
    g = torch.where(d < R, g, torch.full_like(g, -1.0))
    pn = (k * g).clamp_min(0.0)
    if mu > 0:
        xa = (anchor_L[:, :, None] * x[anchor_tri]).sum(1)
        dg = xa - ps                                          # anchor - slave
        ft = k[:, None] * dg                                  # stick trial force on the slave
        fn_ = (ft * nrm).sum(-1)
        ftt = ft - fn_[:, None] * nrm
        stick = anchor_ok & (fn_ > 0) & (ftt.norm(dim=-1) < mu * fn_)
        tdir = dg - (dg * nrm).sum(-1, keepdim=True) * nrm
        tdir = tdir / tdir.norm(dim=-1, keepdim=True).clamp_min(1e-30)
        fslip = pn[:, None] * nrm + mu * pn[:, None] * tdir
        fs = torch.where(stick[:, None], ft, fslip)
    else:
        stick = torch.zeros_like(g, dtype=torch.bool)
        fs = pn[:, None] * nrm
    f = torch.zeros(N, 3, dtype=x.dtype, device=x.device)
    f.index_add_(0, s, fs)
    f.index_add_(0, tri.reshape(-1), (-L[:, :, None] * fs[:, None, :]).reshape(-1, 3))
    return f, fs, (fs * nrm).sum(-1), stick, g


def tied_fn(x, s, anchor_tri, anchor_L, tie_off, ok, k, N: int):
    ps = x[s]
    q = (anchor_L[:, :, None] * x[anchor_tri]).sum(1)
    fs = -k[:, None] * (ps - q - tie_off) * ok[:, None]
    f = torch.zeros(N, 3, dtype=x.dtype, device=x.device)
    f.index_add_(0, s, fs)
    f.index_add_(0, anchor_tri.reshape(-1), (-anchor_L[:, :, None] * fs[:, None, :]).reshape(-1, 3))
    return f, fs
