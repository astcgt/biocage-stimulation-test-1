"""Safety guard r0001: geometry facts for S1 / S2 / S7 from the agreed FSU model (read-only).
Run from the repo root: python human_study/evo/roles/safety/s01_geometry.py
Writes human_study/evo/roles/safety/s01_geometry.json
"""
import json, sys, xml.etree.ElementTree as ET
import numpy as np
sys.path.insert(0, 'scripts/common')
from cage_geom import Endplates
import shapely.geometry as sg

FSU, FRAME = 'human_study/fsu/C34_fsu_refined.feb', 'human_study/frame_c3c4.json'
ep = Endplates(FSU, FRAME)
out, fp = {}, ep.footprint

def box(p):
    x0, y0, x1, y1 = p.bounds
    return dict(x_min=x0, x_max=x1, y_min=y0, y_max=y1, AP=x1 - x0, LR=y1 - y0, area=p.area)

out['outline'] = box(ep.outline)
out['footprint_inset1mm'] = box(fp)

# gap height inside the footprint (native, undistracted)
x0, y0, x1, y1 = fp.bounds
xs, ys = np.meshgrid(np.arange(x0, x1, 0.2), np.arange(y0, y1, 0.2))
inside = np.array([fp.contains(sg.Point(a, b)) for a, b in zip(xs.ravel(), ys.ravel())])
P = np.c_[xs.ravel(), ys.ravel()][inside]
h = ep.z_top(P[:, 0], P[:, 1]) - ep.z_bot(P[:, 0], P[:, 1])
out['gap_in_footprint_mm'] = dict(min=float(h.min()), p05=float(np.percentile(h, 5)), median=float(np.median(h)),
                                  max=float(h.max()))
mid = np.abs(P[:, 1]) < 0.5
for name, sel in [('anterior_2mm', P[:, 0] > x1 - 2), ('posterior_2mm', P[:, 0] < x0 + 2)]:
    s = sel & mid
    out['gap_midline_' + name] = float(np.median(h[s])) if s.any() else None
# footprint volume = upper bound of design space
out['disc_space_volume_mm3'] = float(h.sum() * 0.04)

# width of the footprint along Y at each X (insertion along -X needs Y width <= anterior opening)
widths = []
for x in np.arange(x0 + 0.1, x1, 0.5):
    seg = fp.intersection(sg.LineString([(x, -50), (x, 50)]))
    widths.append((float(x), float(seg.length)))
out['footprint_Y_width_vs_X'] = widths
out['footprint_max_Y_width'] = max(w for _, w in widths)

# anterior opening implied by DECISIONS.md l.22: anterior rim removed over +/-60 deg about anterior from the disc centre
c = ep.outline.centroid
ray = lambda ang: sg.LineString([(c.x, c.y), (c.x + 50 * np.cos(ang), c.y + 50 * np.sin(ang))])
pts = [ep.outline.exterior.intersection(ray(np.deg2rad(a))) for a in (60, -60)]
pts = [p if p.geom_type == 'Point' else list(p.geoms)[0] for p in pts]
out['anterior_120deg_sector_chord_Y_mm'] = float(abs(pts[0].y - pts[1].y))
out['disc_centroid_xy'] = [c.x, c.y]

# Posterior edge of the footprint vs posterior edge of the disc outline (= posterior vertebral wall ~ canal front)
out['posterior_clearance_to_outline_mm'] = float(fp.bounds[0] - ep.outline.bounds[0])

# uncinate processes: C4 bone nodes above the C4 endplate level just lateral to the footprint
r, X, blocks = ep.root, ep.X, ep.blocks
c4 = np.unique(np.vstack([E for k, (t, m, E) in blocks.items() if k.startswith('C4_')]))
Q = ep.F.to(np.array([X[i] for i in c4]))
zb = ep.z_bot(np.clip(Q[:, 0], x0, x1), np.clip(Q[:, 1], y0, y1))
unc = Q[(Q[:, 2] > zb + 0.5) & (np.abs(Q[:, 1]) > 3) & (Q[:, 0] > x0) & (Q[:, 0] < x1)]
if len(unc):
    out['uncinate_points_n'] = int(len(unc))
    out['uncinate_min_abs_Y_mm'] = float(np.abs(unc[:, 1]).min())
    out['uncinate_max_height_above_C4_endplate_mm'] = float((unc[:, 2] - ep.z_bot(np.clip(unc[:, 0], x0, x1), np.clip(unc[:, 1], y0, y1))).max())
    out['footprint_half_width_mm'] = float(max(abs(y0), abs(y1)))

json.dump(out, open('human_study/evo/roles/safety/s01_geometry.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'footprint_Y_width_vs_X'}, indent=1))
