"""Pure element-force functions (one per material kind), written with unrolled 3x3 algebra so torch.compile fuses each
into a few GPU kernels. Same formulas as mech.py (verified against FEBio in gate 1); f = nodal internal forces (N, 3).
"""
import torch
import mech
from mech import mm3, T3, det3, inv3, tr3


def defgrad(xe, G):
    """F[e, g, i, j] = sum_n x[e, n, i] G[e, g, n, j]."""
    return (xe[:, None, :, :, None] * G[:, :, :, None, :]).sum(2)


def elem_forces(P, G, w):
    return (P[:, :, None, :, :] * G[:, :, :, None, :] * w[:, :, None, None, None]).sum((1, 4))     # (E, n, 3)


def assemble(P, G, w, conn, N):
    fe = elem_forces(P, G, w)
    f = torch.zeros(N, 3, dtype=P.dtype, device=P.device)
    f.index_add_(0, conn.reshape(-1), fe.reshape(-1, 3))
    return f


def cauchy_avg(P, F, J, w):
    sig = mm3(P, T3(F)) / J[..., None, None]
    return (sig * w[..., None, None]).sum(1) / w.sum(1)[:, None, None]


def neo(x, conn, G, w, mu, lam, N: int, want: bool = False):
    F = defgrad(x[conn], G); J = det3(F); C = mm3(T3(F), F)
    P = mm3(F, mech.S_neohookean(C, J, mu[:, None], lam[:, None]))
    f = assemble(P, G, w, conn, N)
    return (f, cauchy_avg(P, F, J, w)) if want else f


def ortho(x, conn, G, w, A, mu_a, lam_ab, N: int, want: bool = False):
    F = defgrad(x[conn], G); J = det3(F); C = mm3(T3(F), F)
    P = mm3(F, mech.S_ortho(C, A[:, None], mu_a, lam_ab))
    f = assemble(P, G, w, conn, N)
    return (f, cauchy_avg(P, F, J, w)) if want else f


def hmfib(x, conn, G, w, mu, lam, beta, a0, ksi0, al0, be0, a1, ksi1, al1, be1, N: int, want: bool = False):
    F = defgrad(x[conn], G); J = det3(F); C = mm3(T3(F), F)
    S = mech.S_holmes_mow(C, J, mu[:, None], lam[:, None], beta[:, None])
    S = S + mech.S_fiber_exp_pow(C, a0[:, None], ksi0[:, None], al0[:, None], be0[:, None])
    S = S + mech.S_fiber_exp_pow(C, a1[:, None], ksi1[:, None], al1[:, None], be1[:, None])
    P = mm3(F, S)
    f = assemble(P, G, w, conn, N)
    return (f, cauchy_avg(P, F, J, w)) if want else f


def gentps(x, conn, G, w, V0, Gmod, k, Jm, Fp, N: int, want: bool = False):
    """uncoupled Gent with prestrain, FEBio three-field hex8 (FE3FieldElasticSolidDomain, FEPreStrainUncoupledElastic)."""
    F = defgrad(x[conn], G); J = det3(F)
    Jp = det3(Fp)
    Fh = mm3(F, Fp[:, None]); Jh = det3(Fh)
    Jbar = (J * w).sum(1) / V0
    JJ = Jbar * Jp
    p = k * torch.log(JJ) / JJ
    b = mm3(Fh, T3(Fh)) * Jh[..., None, None]**(-2.0 / 3.0)
    I1 = tr3(b)
    W1 = 0.5 * Gmod[:, None] * Jm[:, None] / (Jm[:, None] - I1 + 3.0).clamp_min(1e-9)
    T = b * W1[..., None, None]
    I = torch.eye(3, dtype=x.dtype, device=x.device)
    dev = T - (tr3(T) / 3)[..., None, None] * I
    sig = dev * (2.0 / Jh)[..., None, None] + p[:, None, None, None] * I
    P = J[..., None, None] * mm3(sig, T3(inv3(F, J)))
    f = assemble(P, G, w, conn, N)
    if want:
        return f, (sig * w[..., None, None]).sum(1) / w.sum(1)[:, None, None]
    return f


def springs(x, i, j, L0, cid, x0, dx, ys, N: int):
    """all nonlinear springs at once; ys (n_curves, S) sampled force curves (scale included), linear interpolation."""
    d = x[j] - x[i]; L = torch.sqrt((d * d).sum(-1)); DL = L - L0
    S = ys.shape[1]
    u = ((DL - x0[cid]) / dx[cid]).clamp(0, S - 1.000001)
    k0 = u.floor().long(); a = u - k0
    flat = ys.reshape(-1); base = cid * S
    Fm = flat[base + k0] * (1 - a) + flat[base + k0 + 1] * a
    fv = (Fm / L.clamp_min(1e-30))[:, None] * d
    f = torch.zeros(N, 3, dtype=x.dtype, device=x.device)
    f.index_add_(0, i, fv); f.index_add_(0, j, -fv)
    return f


# ------------------------------------------------------------------ element tangents (exact, by forward-mode autodiff)
def P_neo(xe, G, w, mu, lam):
    F = defgrad(xe, G); J = det3(F); C = mm3(T3(F), F)
    return mm3(F, mech.S_neohookean(C, J, mu[:, None], lam[:, None]))


def P_ortho(xe, G, w, A, mu_a, lam_ab):
    F = defgrad(xe, G); C = mm3(T3(F), F)
    return mm3(F, mech.S_ortho(C, A[:, None], mu_a, lam_ab))


def P_hmfib(xe, G, w, mu, lam, beta, a0, ksi0, al0, be0, a1, ksi1, al1, be1):
    F = defgrad(xe, G); J = det3(F); C = mm3(T3(F), F)
    S = mech.S_holmes_mow(C, J, mu[:, None], lam[:, None], beta[:, None])
    S = S + mech.S_fiber_exp_pow(C, a0[:, None], ksi0[:, None], al0[:, None], be0[:, None])
    S = S + mech.S_fiber_exp_pow(C, a1[:, None], ksi1[:, None], al1[:, None], be1[:, None])
    return mm3(F, S)


def P_gentps(xe, G, w, V0, Gmod, k, Jm, Fp):
    F = defgrad(xe, G); J = det3(F); Jp = det3(Fp)
    Fh = mm3(F, Fp[:, None]); Jh = det3(Fh)
    JJ = (J * w).sum(1) / V0 * Jp
    p = k * torch.log(JJ) / JJ
    b = mm3(Fh, T3(Fh)) * Jh[..., None, None]**(-2.0 / 3.0)
    W1 = 0.5 * Gmod[:, None] * Jm[:, None] / (Jm[:, None] - tr3(b) + 3.0).clamp_min(1e-9)
    T = b * W1[..., None, None]
    I = torch.eye(3, dtype=xe.dtype, device=xe.device)
    sig = (T - (tr3(T) / 3)[..., None, None] * I) * (2.0 / Jh)[..., None, None] + p[:, None, None, None] * I
    return J[..., None, None] * mm3(sig, T3(inv3(F, J)))


PFUN = dict(neo=P_neo, ortho=P_ortho, hmfib=P_hmfib, gentps=P_gentps)


def elem_tangent(kind, xe, G, w, params, chunk=8192):
    """element stiffness K[e, a, i, b, j] = d f_e[a, i] / d x_e[b, j] by forward-mode autodiff, in chunks.
    params: per-element tensors (first dim E) and constants (as a tuple; constants are passed through)."""
    Pf = PFUN[kind]; E_, n = xe.shape[0], xe.shape[1]
    out = []
    for s0 in range(0, E_, chunk):
        sl = slice(s0, s0 + chunk)
        pp = [p[sl] if torch.is_tensor(p) and p.dim() >= 1 and p.shape[0] == E_ else p for p in params]
        xs, Gs, ws = xe[sl], G[sl], w[sl]
        def fe(x_):
            return elem_forces(Pf(x_, Gs, ws, *pp), Gs, ws)
        cols = []
        for b in range(n):
            for j in range(3):
                t = torch.zeros_like(xs); t[:, b, j] = 1.0
                _, d = torch.func.jvp(fe, (xs,), (t,))
                cols.append(d)                                   # (e, n, 3)
        K = torch.stack(cols, -1).reshape(xs.shape[0], n, 3, n, 3)
        out.append(K)
    return torch.cat(out)
