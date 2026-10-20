"""BIOCAGE hex mesh (0.2 mm) for the ACDR C3-C4 model, built in the disc mid-plane frame in the DISTRACTED configuration.

Design A: top/bottom faces follow the bony endplates (C3 surface raised by the distraction d); no pad.
Design B: generic planar cage between the uncinate processes (|Y| <= 3.5 mm), 0.6 mm soft pad; each plane is the plane parallel to the least-squares fit of its
          (distracted) endplate, shifted until it touches the endplate without penetrating it (gaps elsewhere close as
          the soft pad conforms under load).
Mesh: structured columns on a 0.2 mm X-Y grid over the footprint (cage = footprint minus window, biodisc = window);
      K layers swept between the bottom and top faces (K = round(mean height / 0.2)), so faces conform exactly.
Hard-material fraction phi per element (DECISIONS.md):
  axial  : B pad 0-0.6 mm from a face = 0 %; then 0.2 mm steps 25 / 50 / 75 %; core 100 %  (A: steps start at the face)
  radial : distance from the window edge < 0.4 mm = 0 %, 0.4-0.8 mm = 50 %, beyond = 100 %
  both   : min(axial, radial)  (the softer one wins)        
  design B pads are 0 % in every gradient option.
Printability (PI): wall = whole number of 0.4 mm perimeters (60 % window rounded to the nearest perimeter count);
radial bands are whole perimeters; axial steps are whole 0.2 mm layers.
Fabrication: 'mix' = element phi as blend fraction; 'interleave' = contour-following 0.4 mm perimeters (2 elements wide),
each perimeter per layer all-hard or all-soft, hard if (perimeter + layer) mod 4 < 4*phi.
Output: npz with frame/global node coords, hex connectivity, region (0 cage, 1 biodisc), phi, hard (interleave flag),
top/bottom face quads and the anterior/posterior wall node sets (push-out).
usage: python h12_cage_mesh.py <fsu.feb> <frame.json> <design A|B> <d_mm> <grad axial|radial|both> <fab mix|interleave> <out.npz> [H=0.2] [HZ=H]
"""
import sys, json, numpy as np
import shapely.geometry as sg
from shapely import vectorized
import os; sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
from cage_geom import Endplates

fsu, frame, design, d, grad, fab, out = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5], sys.argv[6], sys.argv[7]
H = float(sys.argv[8]) if len(sys.argv) > 8 else 0.2      # in-plane element size (mesh convergence)
HZ = float(sys.argv[9]) if len(sys.argv) > 9 else H       # through-thickness element size (z-only refinement: H 0.2, HZ 0.1)
ep = Endplates(fsu, frame)
LINE = 0.4                  # nozzle / extrusion line width (mm)
fp = ep.footprint
B_HALF_WIDTH = 3.5          # design B: generic planar cage between the uncinate processes, |Y| <= 3.5 mm (PI Q37)
if design == 'B':
    fp = fp.intersection(sg.box(-50, -B_HALF_WIDTH, 50, B_HALF_WIDTH))
# printable wall (PI: respect nozzle precision): the 60 % window is converted to a whole number of 0.4 mm perimeters
win60 = Endplates._shrink_to(fp, 0.60)
wall60 = fp.exterior.distance(win60.exterior)
N_PERIM = max(1, int(round(wall60 / LINE)))
win = fp.buffer(-N_PERIM * LINE, join_style=1)

# --- column grid
b = fp.bounds
x0, y0 = np.floor(b[0] / H) * H, np.floor(b[1] / H) * H
nx, ny = int(np.ceil((b[2] - x0) / H)), int(np.ceil((b[3] - y0) / H))
xc, yc = np.meshgrid(x0 + (np.arange(nx) + 0.5) * H, y0 + (np.arange(ny) + 0.5) * H, indexing='ij')
active = vectorized.contains(fp, xc, yc)
inwin = vectorized.contains(win, xc, yc) & active
# distance of cell centres from the window edge (radial gradient) and from the outer edge
dwin = np.vectorize(lambda a, c: win.exterior.distance(sg.Point(a, c)))(xc, yc)
dout = np.vectorize(lambda a, c: fp.exterior.distance(sg.Point(a, c)))(xc, yc)
perim = np.clip((dout // LINE).astype(int), 0, N_PERIM - 1)          # 0 = outermost perimeter

# --- face surfaces at node positions
xn, yn = np.meshgrid(x0 + np.arange(nx + 1) * H, y0 + np.arange(ny + 1) * H, indexing='ij')
zt = ep.z_top(xn.ravel(), yn.ravel()).reshape(xn.shape) + d
zb = ep.z_bot(xn.ravel(), yn.ravel()).reshape(xn.shape)
if design == 'B':
    m = vectorized.contains(fp.buffer(0.3), xn, yn)
    A = np.c_[xn[m], yn[m], np.ones(m.sum())]
    ct = np.linalg.lstsq(A, zt[m], rcond=None)[0]; pt = A @ ct; ct[2] -= np.max(pt - zt[m])     # plane below C3 surface, touching
    cb = np.linalg.lstsq(A, zb[m], rcond=None)[0]; pb = A @ cb; cb[2] -= np.min(pb - zb[m])     # plane above C4 surface, touching
    zt = ct[0] * xn + ct[1] * yn + ct[2]; zb = cb[0] * xn + cb[1] * yn + cb[2]
hgt = zt - zb
K = int(round(np.mean(hgt[vectorized.contains(fp, xn, yn)]) / HZ))

# --- nodes / elements
used = np.zeros((nx + 1, ny + 1), bool)
for di in (0, 1):
    for dj in (0, 1):
        used[di:nx + di, dj:ny + dj] |= active
nid = -np.ones((nx + 1, ny + 1, K + 1), int)
ii, jj = np.nonzero(used)
cnt = 0; coords = []
for k in range(K + 1):
    nid[ii, jj, k] = np.arange(cnt, cnt + len(ii)); cnt += len(ii)
    coords.append(np.c_[xn[ii, jj], yn[ii, jj], zb[ii, jj] + hgt[ii, jj] * k / K])
Q = np.vstack(coords)
ci, cj = np.nonzero(active)
hexes, region, phi, hard, layer, lineidx = [], [], [], [], [], []
for k in range(K):
    for i, j in zip(ci, cj):
        n = [nid[i, j, k], nid[i + 1, j, k], nid[i + 1, j + 1, k], nid[i, j + 1, k],
             nid[i, j, k + 1], nid[i + 1, j, k + 1], nid[i + 1, j + 1, k + 1], nid[i, j + 1, k + 1]]
        hexes.append(n); region.append(1 if inwin[i, j] else 0); layer.append(k)
        # axial fraction from the distance (mm) of the element centre to the nearer face
        hcol = 0.25 * (hgt[i, j] + hgt[i + 1, j] + hgt[i, j + 1] + hgt[i + 1, j + 1])
        s = min(k + 0.5, K - k - 0.5) * hcol / K
        if design == 'B' and s < 0.6:
            ax, pad = 0.0, True
        else:
            pad = False; s0 = s - (0.6 if design == 'B' else 0.0)
            ax = 0.25 if s0 < 0.2 else 0.5 if s0 < 0.4 else 0.75 if s0 < 0.6 else 1.0
        # radial bands in whole perimeters counted from the window side: innermost 0 %, next 50 %, others 100 %
        p_in = N_PERIM - 1 - perim[i, j]
        rd = 0.0 if p_in == 0 else 0.5 if p_in == 1 else 1.0
        if pad: f = 0.0
        elif grad == 'axial': f = ax
        elif grad == 'radial': f = rd
        else: f = min(ax, rd)
        phi.append(f)
        # interleave: thin walls are printed as contour-following perimeters (0.4 mm); each perimeter in a layer is
        # all-hard or all-soft; hard if (perimeter + layer) mod 4 < 4*phi, so the local hard fraction averages phi
        li = perim[i, j] + k; lineidx.append(li)
        hard.append(bool((li % 4) < round(4 * f)))
hexes = np.array(hexes); region = np.array(region); phi = np.array(phi); hard = np.array(hard)
phi[region == 1] = np.nan
# faces: bottom quads (k = 0) and top quads (k = K-1) of cage + biodisc, outward normals (-Z / +Z)
bot = np.array([[h[0], h[3], h[2], h[1]] for h, l in zip(hexes, layer) if l == 0])
top = np.array([[h[4], h[5], h[6], h[7]] for h, l in zip(hexes, layer) if l == K - 1])
# outer wall nodes on the anterior / posterior sides (push-out loading faces)
onb = np.array([fp.exterior.distance(sg.Point(p[0], p[1])) < 0.11 for p in Q])
cx = fp.centroid.x
post = np.where(onb & (Q[:, 0] < cx) & (np.abs(Q[:, 1] - fp.centroid.y) < 0.5 * (b[3] - b[1]) * 0.6))[0]
ant = np.where(onb & (Q[:, 0] > cx) & (np.abs(Q[:, 1] - fp.centroid.y) < 0.5 * (b[3] - b[1]) * 0.6))[0]
G = ep.F.back(Q)
info = dict(H_mm=H, HZ_mm=HZ, footprint_area_mm2=round(fp.area, 2), window_area_mm2=round(win.area, 2), window_frac=round(win.area / fp.area, 3),
            n_perimeters=N_PERIM, wall_mm=round(N_PERIM * LINE, 2), design=design, d_mm=d, gradient=grad, fabrication=fab, K_layers=K, n_nodes=len(Q), n_hex=len(hexes),
            n_cage=int((region == 0).sum()), n_biodisc=int((region == 1).sum()),
            height_mm_min_mean_max=[round(float(hgt[used].min()), 3), round(float(hgt[used].mean()), 3), round(float(hgt[used].max()), 3)],
            cage_volume_mm3=round(float((region == 0).sum() * H * H * np.mean(hgt[used]) / K), 1),
            phi_hist={str(v): int((phi[region == 0] == v).sum()) for v in (0.0, 0.25, 0.5, 0.75, 1.0)},
            interleave_hard_frac=round(float(hard[region == 0].mean()), 3))
np.savez_compressed(out, Q=Q, G=G, hexes=hexes, region=region, phi=phi, hard=hard, layer=np.array(layer),
                    top=top, bot=bot, post=post, ant=ant, info=json.dumps(info))
print(json.dumps(info, indent=1))
