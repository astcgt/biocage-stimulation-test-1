"""Extract C3 caudal / C4 cranial endplate height maps from the STL on a 0.2 mm XY grid (GPU ray casting)."""
import numpy as np, torch, struct, json
from scipy import ndimage as ndi
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
dev = 'cuda'
f = open('input/Pig C3-C4.stl', 'rb').read()
n = struct.unpack('<I', f[80:84])[0]
d = np.frombuffer(f[84:84 + n * 50], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
V = torch.tensor(np.ascontiguousarray(d['v']).reshape(-1, 3, 3), dtype=torch.float64, device=dev)
h = 0.2
x0, x1, y0, y1 = 12.0, 62.0, 22.0, 56.0            # region around vertebral body
xs = torch.arange(x0 + h / 2, x1, h, device=dev, dtype=torch.float64)
ys = torch.arange(y0 + h / 2, y1, h, device=dev, dtype=torch.float64)
A, B, C = V[:, 0], V[:, 1], V[:, 2]
lox = torch.minimum(torch.minimum(A[:, 0], B[:, 0]), C[:, 0]); hix = torch.maximum(torch.maximum(A[:, 0], B[:, 0]), C[:, 0])
loy = torch.minimum(torch.minimum(A[:, 1], B[:, 1]), C[:, 1]); hiy = torch.maximum(torch.maximum(A[:, 1], B[:, 1]), C[:, 1])
ZREF = 61.3
nx, ny = len(xs), len(ys)
bot = np.full((nx, ny), np.nan); top = np.full((nx, ny), np.nan); nb = np.zeros((nx, ny), int)
for i in range(nx):
    x = xs[i]
    s = (lox <= x) & (hix >= x)
    if s.sum() == 0: continue
    a, b, c = A[s], B[s], C[s]; ly, hy = loy[s], hiy[s]
    Y = ys[:, None]
    v0 = c[:, :2] - a[:, :2]; v1 = b[:, :2] - a[:, :2]
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = den.abs() > 1e-14; den = torch.where(ok, den, torch.ones_like(den))
    p0 = x - a[None, :, 0]; p1 = Y - a[None, :, 1]
    u = (p0 * v1[None, :, 1] - v1[None, :, 0] * p1) / den
    w = (v0[None, :, 0] * p1 - p0 * v0[None, :, 1]) / den
    m = ok[None] & (u >= 0) & (w >= 0) & (u + w <= 1) & (ly[None] <= Y) & (hy[None] >= Y)
    z = a[None, :, 2] + u * (c[None, :, 2] - a[None, :, 2]) + w * (b[None, :, 2] - a[None, :, 2])
    zb = torch.where(m & (z < ZREF), z, torch.full_like(z, -1e9)).max(1).values
    zt = torch.where(m & (z > ZREF), z, torch.full_like(z, 1e9)).min(1).values
    cnt = (m & (z < ZREF)).sum(1)
    bot[i] = zb.cpu().numpy(); top[i] = zt.cpu().numpy(); nb[i] = cnt.cpu().numpy()
bot[bot < -1e8] = np.nan; top[top > 1e8] = np.nan
gap = top - bot
outside = (nb % 2 == 0)                           # ZREF lies outside bone (parity)
valid = outside & np.isfinite(gap) & (gap > 1.0) & (gap < 7.0) & (bot > 55) & (top < 67)
lab, nl = ndi.label(valid)
X, Y = np.meshgrid(xs.cpu().numpy(), ys.cpu().numpy(), indexing='ij')
seed = (np.argmin(abs(X[:, 0] - 36)), np.argmin(abs(Y[0] - 46)))
body = lab == lab[seed]
body = ndi.binary_opening(body, iterations=3); body = ndi.binary_fill_holes(body)
lab2, _ = ndi.label(body); body = lab2 == lab2[seed]
np.savez('00_prep/endplates.npz', xs=X[:, 0], ys=Y[0], bot=bot, top=top, body=body, h=h)
bx, by = X[body], Y[body]
info = dict(area_mm2=float(body.sum() * h * h), x_range=[float(bx.min()), float(bx.max())], y_range=[float(by.min()), float(by.max())],
            gap_pct_5_50_95=np.percentile(gap[body], [5, 50, 95]).round(2).tolist(),
            C4_cranial_z_pct=np.percentile(bot[body], [5, 50, 95]).round(2).tolist(), C3_caudal_z_pct=np.percentile(top[body], [5, 50, 95]).round(2).tolist())
json.dump(info, open('00_prep/endplates_info.json', 'w'), indent=1); print(json.dumps(info, indent=1))
fig, axs = plt.subplots(1, 3, figsize=(18, 5.5))
ext = [x0, x1, y0, y1]
for a, (M, t, cm) in zip(axs, [(np.where(body, bot, np.nan), 'C4 cranial endplate z (mm)', 'viridis'), (np.where(body, top, np.nan), 'C3 caudal endplate z (mm)', 'viridis'), (np.where(valid, gap, np.nan), 'gap height (mm), body outlined', 'magma')]):
    im = a.imshow(M.T, origin='lower', extent=ext, cmap=cm); plt.colorbar(im, ax=a); a.set_title(t); a.set_xlabel('x (mm, lateral)'); a.set_ylabel('y (mm, anterior +)')
    a.contour(X, Y, body.astype(float), [0.5], colors='r', linewidths=1)
plt.tight_layout(); plt.savefig('00_prep/endplate_maps.png', dpi=90)
