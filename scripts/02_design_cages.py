"""Design contour-matched cages (A: smooth, B: shoe-tread lugs) for pig C3/C4 and build the voxel FE model.

Voxel labels: 0 void, 1 C4 cancellous, 2 C4 cortical, 3 C3 cancellous, 4 C3 cortical, 5 cage (PLCL), 6 biodisc
"""
import json, os, sys
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
import trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from params import H, DESIGN as D, PRINT, MAT

OUT = 'design'; os.makedirs(OUT, exist_ok=True)
E = np.load('00_prep/endplates.npz')
xs, ys, bot, top, body = E['xs'], E['ys'], E['bot'], E['top'], E['body']
assert abs(E['h'] - H) < 1e-9

# ---- crop to body bbox + margin
ii, jj = np.where(body)
i0, i1, j0, j1 = ii.min() - 4, ii.max() + 5, jj.min() - 4, jj.max() + 5
xs, ys, bot, top, body = xs[i0:i1], ys[j0:j1], bot[i0:i1, j0:j1], top[i0:i1, j0:j1], body[i0:i1, j0:j1]
nx, ny = body.shape

# ---- smooth endplate surfaces (fill outside body by nearest so the blur is not polluted)
def smooth(Z):
    idx = ndi.distance_transform_edt(~body, return_distances=False, return_indices=True)
    Zf = Z[tuple(idx)]
    return ndi.gaussian_filter(Zf, D['surface_smoothing_mm'] / H)
bot_s, top_s = smooth(bot), smooth(top)

# ---- footprint and window
px = lambda mm: int(round(mm / H))
foot = ndi.binary_erosion(body, iterations=px(D['footprint_inset_mm']))
foot = ndi.binary_opening(foot, iterations=2)
lab, _ = ndi.label(foot); foot = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1
dist_in = ndi.distance_transform_edt(foot) * H
best = None
for t in np.arange(D['min_wall_mm'], 6, 0.05):
    win = dist_in > t
    win = ndi.binary_opening(win, iterations=2)
    lab, n = ndi.label(win)
    if n == 0: break
    win = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1
    frac = win.sum() / foot.sum()
    if best is None or abs(frac - D['window_area_fraction']) < abs(best[1] - D['window_area_fraction']):
        best = (t, frac, win)
wall_t, win_frac, window = best
wall = foot & ~window
# actual minimum wall thickness (twice max inscribed radius along the wall medial axis is overkill; use distance to window)
dist_to_win = ndi.distance_transform_edt(~window) * H
min_wall = float(dist_to_win[foot & ndi.binary_dilation(~foot, iterations=1)].min())

# ---- chevron (herringbone) tread pattern on the wall faces
X, Y = np.meshgrid(xs, ys, indexing='ij')
xc = X[foot].mean(); yc = Y[foot].mean()
ang = np.deg2rad(D['lug_angle_deg'])
s = (Y - yc) * np.cos(ang) + np.abs(X - xc) * np.sin(ang)          # chevron coordinate, apex on midline
lug2d = (np.mod(s, D['lug_pitch_mm']) < D['lug_width_mm'])
wall_core = wall & ndi.binary_erosion(wall, iterations=max(1, px(D['lug_edge_margin_mm'])))
lug2d &= wall_core

# ---- 3D voxel grid
z0, z1 = D['bone_slab_below_mm'], D['bone_slab_above_mm']
nz = int(round((z1 - z0) / H)); zs = z0 + (np.arange(nz) + 0.5) * H
ZC = zs[None, None, :]
lug_k = px(D['lug_height_mm'])

def build(tread):
    L = np.zeros((nx, ny, nz), np.uint8)
    b3, t3 = bot_s[:, :, None], top_s[:, :, None]
    bodyc = body[:, :, None]
    c4 = bodyc & (ZC < b3)
    c3 = bodyc & (ZC > t3)
    between = (ZC >= b3) & (ZC <= t3)
    cage = wall[:, :, None] & between
    bio = window[:, :, None] & between
    if tread:
        K = np.arange(nz)[None, None, :]
        # lugs protrude into bone (seated / impacted state: bone conforms to lugs)
        lug_dn = lug2d[:, :, None] & (K < (np.floor((bot_s - z0) / H + 0.5))[:, :, None]) & (K >= (np.floor((bot_s - z0) / H + 0.5) - lug_k)[:, :, None])
        lug_up = lug2d[:, :, None] & (K > (np.floor((top_s - z0) / H - 0.5))[:, :, None]) & (K <= (np.floor((top_s - z0) / H - 0.5) + lug_k)[:, :, None])
        cage |= lug_dn | lug_up
        c4 &= ~lug_dn; c3 &= ~lug_up
    # cortical layers: bony endplate (within t of the disc-facing surface) + lateral shell
    shell2d = body & ~ndi.binary_erosion(body, iterations=px(D['cortical_shell_mm']))
    ep = px(D['cortical_endplate_mm'])
    # endplate: voxels of bone whose voxel `ep` steps toward the disc is not bone of the same vertebra
    def near_surface(bone, direction):
        m = np.zeros_like(bone)
        for k in range(1, ep + 1):
            sh = np.roll(bone, -direction * k, axis=2)
            if direction > 0: sh[:, :, -k:] = True
            else: sh[:, :, :k] = True
            m |= bone & ~sh
        return m
    c4_cort = near_surface(c4, +1) | (c4 & shell2d[:, :, None])
    c3_cort = near_surface(c3, -1) | (c3 & shell2d[:, :, None])
    L[c4] = 1; L[c4_cort] = 2; L[c3] = 3; L[c3_cort] = 4; L[bio] = 6; L[cage] = 5
    return L

models = {'A_smooth': build(False), 'B_tread': build(True)}
grid = dict(x0=float(xs[0] - H / 2), y0=float(ys[0] - H / 2), z0=float(z0), h=H, shape=[nx, ny, nz])
ref_point = [float(xc), float(yc), float(np.mean((bot_s[foot] + top_s[foot]) / 2))]
for k, L in models.items():
    np.savez_compressed(f'{OUT}/model_{k}.npz', L=L, **{kk: np.array(v) for kk, v in grid.items()}, ref=np.array(ref_point),
                        wall=wall, window=window, lug2d=lug2d if k == 'B_tread' else np.zeros_like(lug2d))

# ---- STL export of the cages (marching cubes on voxel occupancy, lightly smoothed)
def export_stl(L, fn):
    occ = (L == 5).astype(np.float32)
    occ = np.pad(occ, 1)
    occ = ndi.gaussian_filter(occ, 0.6)
    v, f, _, _ = measure.marching_cubes(occ, 0.5, spacing=(H, H, H))
    v += np.array([grid['x0'], grid['y0'], z0]) - H
    m = trimesh.Trimesh(v, f); trimesh.smoothing.filter_taubin(m, iterations=10)
    m.export(fn); return m
meshes = {k: export_stl(L, f'{OUT}/cage_{k}.stl') for k, L in models.items()}

# ---- design parameter table
hgt = (top_s - bot_s)[wall]
cage_vol = {k: float((L == 5).sum() * H ** 3) for k, L in models.items()}
lug_area = float(lug2d.sum() * H * H)
rows = [
    ('Target segment', 'Pig C3/C4 (Gottingen minipig STL)', ''),
    ('Material', MAT['PLCL']['name'], ''),
    ('Footprint (outer) LR x AP', f"{np.ptp(X[foot]) + H:.1f} x {np.ptp(Y[foot]) + H:.1f}", 'mm'),
    ('Footprint area', f"{foot.sum() * H * H:.1f}", 'mm^2'),
    ('Vertebral body endplate area', f"{body.sum() * H * H:.1f}", 'mm^2'),
    ('Inset from body rim', f"{D['footprint_inset_mm']}", 'mm'),
    ('Biodisc window area', f"{window.sum() * H * H:.1f} ({100 * win_frac:.1f}% of footprint)", 'mm^2'),
    ('Nominal wall thickness', f"{wall_t:.2f}", 'mm'),
    ('Minimum wall thickness', f"{min_wall:.2f}", 'mm'),
    ('Wall (load-bearing) area', f"{wall.sum() * H * H:.1f}", 'mm^2'),
    ('Height (contour-matched), min / mean / max', f"{hgt.min():.2f} / {hgt.mean():.2f} / {hgt.max():.2f}", 'mm'),
    ('Upper surface', 'conforms to C3 caudal endplate (smoothed STL height map)', ''),
    ('Lower surface', 'conforms to C4 cranial endplate (smoothed STL height map)', ''),
    ('Posterior outline', 'follows posterior notch and posterolateral uncinate zones with the 1 mm inset', ''),
    ('Cage volume A (smooth)', f"{cage_vol['A_smooth']:.1f}", 'mm^3'),
    ('Cage volume B (tread)', f"{cage_vol['B_tread']:.1f}", 'mm^3'),
    ('Tread pattern (B)', f"chevron/herringbone, arm angle {D['lug_angle_deg']} deg, apex on midline", ''),
    ('Lug height / width / pitch (B)', f"{D['lug_height_mm']} / {D['lug_width_mm']} / {D['lug_pitch_mm']}", 'mm'),
    ('Lug footprint area per face (B)', f"{lug_area:.1f} ({100 * lug_area / (wall.sum() * H * H):.0f}% of wall)", 'mm^2'),
    ('Print process', PRINT['process'], ''),
    ('Nozzle / layer / line width', f"{PRINT['nozzle_diameter_mm']} / {PRINT['layer_height_mm']} / {PRINT['line_width_mm']}", 'mm'),
    ('Infill', f"{PRINT['infill_percent']}", '%'),
    ('XY accuracy', f"+/-{PRINT['xy_accuracy_mm']}", 'mm'),
    ('Nozzle / bed temperature', f"{PRINT['nozzle_temp_C']} / {PRINT['bed_temp_C']}", 'C'),
    ('Build orientation', PRINT['build_orientation'], ''),
    ('FE voxel size', f"{H}", 'mm'),
]
with open(f'{OUT}/design_parameters.csv', 'w') as fh:
    fh.write('parameter,value,unit\n')
    for r in rows: fh.write('"%s","%s","%s"\n' % r)
with open(f'{OUT}/design_parameters.md', 'w') as fh:
    fh.write('| Parameter | Value | Unit |\n|---|---|---|\n')
    for r in rows: fh.write('| %s | %s | %s |\n' % r)
json.dump(dict(grid=grid, ref_point=ref_point, wall_t=wall_t, window_frac=win_frac, min_wall=min_wall, cage_vol=cage_vol,
               wall_area=float(wall.sum() * H * H), foot_area=float(foot.sum() * H * H)), open(f'{OUT}/design_summary.json', 'w'), indent=1)

# ---- figures
ext = [xs[0] - H / 2, xs[-1] + H / 2, ys[0] - H / 2, ys[-1] + H / 2]
fig, axs = plt.subplots(2, 3, figsize=(19, 11))
a = axs[0, 0]; img = np.zeros((nx, ny, 3)); img[body] = [.85, .85, .85]; img[wall] = [.2, .45, .8]; img[window] = [.95, .6, .6]
a.imshow(img.transpose(1, 0, 2), origin='lower', extent=ext); a.set_title('Footprint: body (grey), cage wall (blue), biodisc window (pink)')
a = axs[0, 1]; img2 = img.copy(); img2[lug2d] = [.05, .15, .35]
a.imshow(img2.transpose(1, 0, 2), origin='lower', extent=ext); a.set_title('Design B tread: chevron lugs (dark) on both faces')
a = axs[0, 2]; im = a.imshow(np.where(foot, top_s - bot_s, np.nan).T, origin='lower', extent=ext, cmap='viridis'); plt.colorbar(im, ax=a, label='mm')
a.set_title('Cage height (contour-matched) over footprint')
jm = np.argmin(abs(ys - yc)); im_ = np.argmin(abs(xs - xc))
for a, (Lk, t) in zip(axs[1, :2], [(models['A_smooth'], 'A smooth'), (models['B_tread'], 'B tread')]):
    cmap = np.array([[1, 1, 1], [.93, .85, .7], [.75, .6, .4], [.93, .85, .7], [.75, .6, .4], [.2, .45, .8], [.95, .6, .6]])
    a.imshow(cmap[Lk[:, jm, :]].transpose(1, 0, 2), origin='lower', extent=[ext[0], ext[1], z0, z1], aspect='equal')
    a.set_ylim(55, 67); a.set_title(f'{t}: coronal section y={ys[jm]:.1f} mm (bone: cancellous/cortical)'); a.set_xlabel('x (mm)'); a.set_ylabel('z (mm)')
a = axs[1, 2]
a.imshow(cmap[models['B_tread'][im_, :, :]].transpose(1, 0, 2), origin='lower', extent=[ext[2], ext[3], z0, z1], aspect='equal')
a.set_ylim(55, 67); a.set_title(f'B tread: sagittal section x={xs[im_]:.1f} mm (anterior right)'); a.set_xlabel('y (mm)')
for a in axs[0]: a.set_xlabel('x (mm, lateral)'); a.set_ylabel('y (mm, anterior +)')
plt.tight_layout(); plt.savefig(f'{OUT}/design_overview.png', dpi=90); plt.close()

# 3D renders
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
fig = plt.figure(figsize=(18, 8))
for n_, (k, m) in enumerate(meshes.items()):
    for v_, (el, az) in enumerate([(35, -60), (-35, -60)]):
        a = fig.add_subplot(2, 2, 2 * n_ + v_ + 1, projection='3d')
        tri = m.vertices[m.faces]; nrm = m.face_normals
        shade = 0.35 + 0.65 * np.clip(nrm @ np.array([0.3, -0.4, 0.85]), 0, 1)
        col = np.c_[0.2 * shade, 0.45 * shade, 0.8 * shade, np.ones_like(shade)]
        pc = Poly3DCollection(tri, facecolors=col, edgecolor='none'); a.add_collection3d(pc)
        c = m.vertices.mean(0); r = np.ptp(m.vertices, 0).max() / 2
        a.set_xlim(c[0] - r, c[0] + r); a.set_ylim(c[1] - r, c[1] + r); a.set_zlim(c[2] - r / 2, c[2] + r / 2)
        a.view_init(el, az); a.set_title(f"cage {k} ({'top' if el > 0 else 'bottom'} view)"); a.set_box_aspect((1, 1, 0.5))
plt.tight_layout(); plt.savefig(f'{OUT}/cages_3d.png', dpi=90); plt.close()
print(json.dumps(json.load(open(f'{OUT}/design_summary.json')), indent=1))
print('\n'.join('%s: %s %s' % r for r in rows))
