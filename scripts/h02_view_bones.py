"""Render the extracted human C3/C4 + disc (sagittal, coronal, axial-from-above-C4) to PNG."""
import sys, numpy as np, pyvista as pv, trimesh
d = sys.argv[1]
pv.OFF_SCREEN = True
M = {k: pv.read(f'{d}/{k}.stl') for k in ['C3', 'C4', 'C3C4_disc', 'C3C4_nucleus']}
col = dict(C3='#d9c7a3', C4='#c9b48a', C3C4_disc='#6fa8dc', C3C4_nucleus='#e06666')
views = [('sagittal (x=AP, z=up)', 'xz', False), ('coronal (y=LR)', 'yz', False), ('C4 from above + disc', 'xy', True)]
p = pv.Plotter(shape=(1, 3), window_size=(2100, 750))
for i, (t, v, top) in enumerate(views):
    p.subplot(0, i)
    for k, m in M.items():
        if top and k == 'C3':
            continue
        p.add_mesh(m, color=col[k], opacity=0.35 if (k == 'C3C4_disc' and not top) else 1.0, smooth_shading=True)
    p.add_text(t, font_size=11)
    getattr(p, f'view_{v}')()
    p.show_axes()
p.screenshot(sys.argv[2])
# endplate gap stats under the disc footprint: vertical distance C3 underside -> C4 top
c3 = trimesh.load(f'{d}/C3.stl'); c4 = trimesh.load(f'{d}/C4.stl'); dk = trimesh.load(f'{d}/C3C4_disc.stl')
(x0, y0, _), (x1, y1, _) = dk.bounds
gx, gy = np.meshgrid(np.arange(x0, x1, 0.25), np.arange(y0, y1, 0.25))
P = np.c_[gx.ravel(), gy.ravel()]
zc = 0.5 * (c3.bounds[0, 2] + c4.bounds[1, 2])
def hit(m, sign):
    o = np.c_[P, np.full(len(P), zc)]; dvec = np.tile([0, 0, sign], (len(P), 1))
    loc, ri, _ = m.ray.intersects_location(o, dvec, multiple_hits=False)
    z = np.full(len(P), np.nan); z[ri] = loc[:, 2]; return z
gap = hit(c3, 1) - hit(c4, -1)
g = gap[np.isfinite(gap)]
print('disc-footprint grid pts with both endplates:', g.size, 'gap mm min/mean/median/max: %.2f %.2f %.2f %.2f' % (g.min(), g.mean(), np.median(g), g.max()))
