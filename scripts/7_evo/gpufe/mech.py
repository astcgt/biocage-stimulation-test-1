"""Total-Lagrangian elements and FEBio materials (batched, torch, float64).

Elements: tet4 (1 point), hex8 (2x2x2 Gauss; uncoupled materials use the FEBio three-field form for hex8: deviatoric stress
at each Gauss point, pressure p = U'(Jbar) from the element volume ratio Jbar = v / V).
Every material returns the 2nd Piola-Kirchhoff stress S (reference configuration) from C (and J); formulas follow the FEBio
user manual (FEBio 4.x) definitions:
  neo-Hookean      W = mu/2 (I1 - 3) - mu ln J + lam/2 (ln J)^2
  orthotropic      W = 1/2 sum_a [2 mu_a A_a : E^2 + sum_b lam_ab (A_a : E)(A_b : E)],  A_a = a_a x a_a, E Green-Lagrange
  Holmes-Mow       W = c/2 (exp Q - 1), Q = beta / (lam + 2 mu) [(2 mu - lam)(I1 - 3) + lam (I2 - 3) - (lam + 2 mu) ln I3], c = (lam + 2 mu) / (2 beta)
  fiber-exp-pow    W = ksi / (alpha beta) (exp[alpha (In - 1)^beta] - 1) for In = a0.C.a0 > 1
  Gent (uncoupled) W~ = -G Jm / 2 ln(1 - (I1~ - 3) / Jm),  U = k/2 (ln J)^2
  prestrain        stress of Fhat = F Fp (Fp = I + ramp (F0 - I)); S = Fp Shat Fp^T / det Fp
"""
import numpy as np, torch

DT = torch.float64


# ------------------------------------------------------------------ unrolled 3x3 algebra (fuses under torch.compile;
# batched torch.linalg / @ on (..., 3, 3) launch many small kernels and were 30x slower)
def mm3(A, B):
    return torch.stack([torch.stack([A[..., i, 0] * B[..., 0, j] + A[..., i, 1] * B[..., 1, j] + A[..., i, 2] * B[..., 2, j]
                                     for j in range(3)], -1) for i in range(3)], -2)


def tr3(A): return A[..., 0, 0] + A[..., 1, 1] + A[..., 2, 2]


def T3(A): return A.transpose(-1, -2)


def det3(A):
    return (A[..., 0, 0] * (A[..., 1, 1] * A[..., 2, 2] - A[..., 1, 2] * A[..., 2, 1])
            - A[..., 0, 1] * (A[..., 1, 0] * A[..., 2, 2] - A[..., 1, 2] * A[..., 2, 0])
            + A[..., 0, 2] * (A[..., 1, 0] * A[..., 2, 1] - A[..., 1, 1] * A[..., 2, 0]))


def inv3(A, d=None):
    d = det3(A) if d is None else d
    c = lambda i, j: (A[..., (i + 1) % 3, (j + 1) % 3] * A[..., (i + 2) % 3, (j + 2) % 3]
                      - A[..., (i + 1) % 3, (j + 2) % 3] * A[..., (i + 2) % 3, (j + 1) % 3])
    return torch.stack([torch.stack([c(j, i) / d for j in range(3)], -1) for i in range(3)], -2)


def outer3(a, b): return a[..., :, None] * b[..., None, :]


def eye(dev):
    return torch.eye(3, dtype=DT, device=dev)


# ------------------------------------------------------------------ kinematics
HEX_NAT = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
GP = 1 / np.sqrt(3)
HEX_GP = np.array([[a, b, c] for c in (-GP, GP) for b in (-GP, GP) for a in (-GP, GP)])


def hex_dN(xi):
    """dN/dxi at natural points xi (g, 3) -> (g, 8, 3)."""
    s = HEX_NAT[None]; x = xi[:, None, :]
    f = 1 + s * x                                      # (g, 8, 3)
    d = np.empty((len(xi), 8, 3))
    d[..., 0] = s[..., 0] * f[..., 1] * f[..., 2] / 8; d[..., 1] = f[..., 0] * s[..., 1] * f[..., 2] / 8; d[..., 2] = f[..., 0] * f[..., 1] * s[..., 2] / 8
    return d


def reference_gradients(X, conn, etype):
    """Shape-function gradients in the reference configuration and integration weights.
    tet4 -> G (E, 1, 4, 3), w (E, 1); hex8 -> G (E, 8, 8, 3), w (E, 8)."""
    Xe = X[conn]                                       # (E, n, 3)
    if etype == 'tet4':
        dNdxi = np.array([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
        J = np.einsum('eni,nj->eij', Xe, dNdxi)        # dX/dxi
        detJ = np.linalg.det(J); Ji = np.linalg.inv(J)
        G = np.einsum('nj,eji->eni', dNdxi, Ji)[:, None]
        w = (detJ / 6.0)[:, None]
    elif etype == 'hex8':
        dN = hex_dN(HEX_GP)                            # (8gp, 8n, 3)
        J = np.einsum('eni,gnj->egij', Xe, dN)
        detJ = np.linalg.det(J); Ji = np.linalg.inv(J)
        G = np.einsum('gnj,egji->egni', dN, Ji)
        w = detJ                                       # Gauss weights = 1
    else:
        raise NotImplementedError(etype)
    if (w <= 0).any(): raise ValueError(f'{etype}: {(w <= 0).sum()} inverted integration points in the reference mesh')
    return G, w


def local_axes_vector(a, d):
    e1 = a / np.linalg.norm(a); e3 = np.cross(e1, d); e3 /= np.linalg.norm(e3); e2 = np.cross(e3, e1)
    return np.stack([e1, e2, e3])                      # rows = local axes


def local_axes_nodes(Xe, ids):
    """FEBio mat_axis type 'local' n1,n2,n3 (1-based local node numbers): e1 = x2 - x1, d = x3 - x1."""
    a = Xe[:, ids[1] - 1] - Xe[:, ids[0] - 1]; d = Xe[:, ids[2] - 1] - Xe[:, ids[0] - 1]
    e1 = a / np.linalg.norm(a, axis=1, keepdims=True); e3 = np.cross(e1, d); e3 /= np.linalg.norm(e3, axis=1, keepdims=True)
    e2 = np.cross(e3, e1)
    return np.stack([e1, e2, e3], axis=1)              # (E, 3, 3) rows = axes


# ------------------------------------------------------------------ materials (per Gauss point, batched)
def inv_sym(C):
    return inv3(C)


def S_neohookean(C, J, mu, lam):
    Ci = inv_sym(C); I = eye(C.device)
    return mu[..., None, None] * (I - Ci) + (lam * torch.log(J))[..., None, None] * Ci


def S_holmes_mow(C, J, mu, lam, beta):
    Ci = inv_sym(C); I = eye(C.device)
    I1 = tr3(C); I2 = 0.5 * (I1**2 - (C * C).sum((-2, -1))); I3_ = J**2
    M = lam + 2 * mu
    Q = beta / M * ((2 * mu - lam) * (I1 - 3) + lam * (I2 - 3) - M * torch.log(I3_))
    c = M / (2 * beta)
    dQ = (beta / M)[..., None, None] * ((2 * mu - lam)[..., None, None] * I + lam[..., None, None] * (I1[..., None, None] * I - C) - M[..., None, None] * Ci)
    return (c * torch.exp(Q))[..., None, None] * dQ


def S_fiber_exp_pow(C, a0, ksi, alpha, beta):
    In = sum(a0[..., i] * C[..., i, j] * a0[..., j] for i in range(3) for j in range(3))
    x = torch.clamp(In - 1, min=0.0)
    # beta >= 2 in this model -> smooth at In = 1
    dW = ksi * x**(beta - 1) * torch.exp(alpha * x**beta)
    return (2 * dW)[..., None, None] * outer3(a0, a0)


def S_ortho(C, A, mu_a, lam_ab):
    """A: (..., 3, 3) rows = material axes; mu_a (3,), lam_ab (3, 3) constants (FEBio FEOrthoElastic)."""
    I = eye(C.device); E = 0.5 * (C - I)
    AE = [sum(A[..., a, i] * A[..., a, j] * E[..., i, j] for i in range(3) for j in range(3)) for a in range(3)]
    S = torch.zeros_like(C)
    for a in range(3):
        Aa = outer3(A[..., a, :], A[..., a, :])
        S = S + mu_a[a] * (mm3(Aa, E) + mm3(E, Aa)) + (lam_ab[a, 0] * AE[0] + lam_ab[a, 1] * AE[1] + lam_ab[a, 2] * AE[2])[..., None, None] * Aa
    return S


def ortho_constants(m):
    """FEBio: mu_a from shear moduli, lam_ab from the inverse compliance (c_ab) minus 2 mu_a on the diagonal."""
    E1, E2, E3, G12, G23, G31, v12, v23, v31 = (m[k] for k in ('E1', 'E2', 'E3', 'G12', 'G23', 'G31', 'v12', 'v23', 'v31'))
    S = np.array([[1 / E1, -v12 / E1, -v31 / E3], [-v12 / E1, 1 / E2, -v23 / E2], [-v31 / E3, -v23 / E2, 1 / E3]])
    c = np.linalg.inv(S)
    # mu_1 + mu_2 = 2 G12 etc. so that the small-strain shear stress is S_12 = 2 G12 E_12 (checked in gate 1)
    mu = np.array([G12 + G31 - G23, G12 + G23 - G31, G31 + G23 - G12])
    lam = c.copy(); lam[np.diag_indices(3)] -= 2 * mu
    return mu, lam, float(c.max())


def S_gent_dev(C, J, G, Jm):
    """deviatoric 2nd PK of the uncoupled Gent: J^-2/3 Dev[S~], S~ = 2 dW~/dC~ = G / (1 - (I1~ - 3) / Jm) I."""
    Ci = inv_sym(C); I = eye(C.device)
    Jm23 = J**(-2.0 / 3.0)
    I1t = Jm23 * tr3(C)
    den = torch.clamp(1 - (I1t - 3) / Jm, min=1e-6)
    St = (G / den)[..., None, None] * I
    # Dev[S~] = S~ - 1/3 (S~ : C~) C~^-1, pulled back: S_dev = J^-2/3 (S~ - 1/3 (S~ : C) C^-1)
    tr = (St * C).sum((-2, -1))
    return Jm23[..., None, None] * (St - (tr / 3)[..., None, None] * Ci)


def lame(E, v):
    return E / (2 * (1 + v)), E * v / ((1 + v) * (1 - 2 * v))
