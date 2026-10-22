"""Endplate geometry of the intact C3-C4 FSU in the disc mid-plane frame, and the cage footprint / window.

Frame (h04_frame.py): X anterior, Y left, Z disc normal (superior), origin = C3-C4 ICR.
The Herron disc shares nodes with the C3 and C4 cortex: disc nodes shared with C3 = C3 inferior endplate, with C4 = C4
superior endplate. Height maps z_top(x, y) (C3) and z_bot(x, y) (C4) are interpolated from those nodes.
Footprint = outline of the disc in the frame X-Y plane, inset by INSET mm; window = same shape shrunk to WINDOW_FRAC of the
footprint area (uniform inward offset), centred where the offset puts it.
"""
import json, xml.etree.ElementTree as ET
import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
import shapely.geometry as sg
from shapely.ops import unary_union

INSET, WINDOW_FRAC = 1.0, 0.60


def load_feb(path):
    r = ET.parse(path).getroot(); g = r.find('Geometry')
    X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
    blocks = {eb.get('name'): (eb.get('type'), eb.get('mat'), np.array([[int(v) for v in e.text.split(',')] for e in eb]))
              for eb in g.findall('Elements') if len(eb)}
    return r, X, blocks


class Frame:
    def __init__(self, path):
        f = json.load(open(path))
        self.O = np.array(f['origin_ICR']); self.R = np.array([f['X_anterior'], f['Y_left'], f['Z_superior']])
    def to(self, P): return (np.atleast_2d(P) - self.O) @ self.R.T
    def back(self, Q): return np.atleast_2d(Q) @ self.R + self.O


class Endplates:
    def __init__(self, feb, frame_json, disp=None):
        """disp: optional {'top': {node_id: u}, 'bot': {node_id: u}} frame-coordinate displacements of the endplate nodes
        (e.g. the real distracted state from the gap library, h25); the face surfaces then follow the deformed endplates."""
        self.root, self.X, self.blocks = load_feb(feb)
        self.F = Frame(frame_json)
        disc = [k for k, (t, m, E) in self.blocks.items() if t == 'hex8' and k.startswith('disc_or_facet') and k != 'disc_or_facet_mat5']
        self.disc_blocks = disc
        dn = set(np.unique(np.vstack([self.blocks[k][2] for k in disc])))
        c3 = set(np.unique(np.vstack([self.blocks[k][2] for k in self.blocks if k.startswith('C3_')])))
        c4 = set(np.unique(np.vstack([self.blocks[k][2] for k in self.blocks if k.startswith('C4_')])))
        self.top_ids = np.array(sorted(dn & c3)); self.bot_ids = np.array(sorted(dn & c4))
        T = self.F.to(np.array([self.X[i] for i in self.top_ids])); B = self.F.to(np.array([self.X[i] for i in self.bot_ids]))
        if disp is not None:
            T = T + np.array([disp['top'].get(int(i), np.zeros(3)) for i in self.top_ids])
            B = B + np.array([disp['bot'].get(int(i), np.zeros(3)) for i in self.bot_ids])
        self.T, self.B = T, B
        self._zt = LinearNDInterpolator(T[:, :2], T[:, 2]); self._zt_n = NearestNDInterpolator(T[:, :2], T[:, 2])
        self._zb = LinearNDInterpolator(B[:, :2], B[:, 2]); self._zb_n = NearestNDInterpolator(B[:, :2], B[:, 2])
        # disc outline in the frame plane: union of the projected bottom-face quads of the disc hexes
        quads, bset = [], set(self.bot_ids)
        for k in disc:
            for e in self.blocks[k][2]:
                ids = [i for i in e if i in bset]
                if len(ids) >= 3:
                    q = self.F.to(np.array([self.X[i] for i in ids]))
                    poly = sg.MultiPoint([tuple(p) for p in q[:, :2]]).convex_hull
                    if poly.area > 1e-6: quads.append(poly)
        self.n_bottom_faces = len(quads)
        self.outline = unary_union(quads).buffer(0)
        self.footprint = self.outline.buffer(-INSET, join_style=2)
        self.window = self._shrink_to(self.footprint, WINDOW_FRAC)

    @staticmethod
    def _shrink_to(poly, frac):
        lo, hi, target = 0.0, 10.0, frac * poly.area
        for _ in range(60):
            mid = 0.5 * (lo + hi); a = poly.buffer(-mid, join_style=1).area
            lo, hi = (mid, hi) if a > target else (lo, mid)
        return poly.buffer(-0.5 * (lo + hi), join_style=1)

    def z_top(self, x, y):
        z = self._zt(x, y); m = np.isnan(z); z[m] = self._zt_n(np.asarray(x)[m], np.asarray(y)[m]) if np.any(m) else z[m]; return z

    def z_bot(self, x, y):
        z = self._zb(x, y); m = np.isnan(z); z[m] = self._zb_n(np.asarray(x)[m], np.asarray(y)[m]) if np.any(m) else z[m]; return z

    def summary(self):
        mn = self.footprint.bounds
        x, y = np.meshgrid(np.arange(mn[0], mn[2], 0.2), np.arange(mn[1], mn[3], 0.2))
        inside = np.array([self.footprint.contains(sg.Point(a, b)) for a, b in zip(x.ravel(), y.ravel())])
        gap = (self.z_top(x.ravel(), y.ravel()) - self.z_bot(x.ravel(), y.ravel()))[inside]
        return dict(outline_area_mm2=round(self.outline.area, 1), footprint_area_mm2=round(self.footprint.area, 1),
                    window_area_mm2=round(self.window.area, 1), window_frac=round(self.window.area / self.footprint.area, 3),
                    footprint_AP_LR_mm=[round(mn[2] - mn[0], 2), round(mn[3] - mn[1], 2)],
                    gap_mm_min_mean_max=[round(float(gap.min()), 2), round(float(gap.mean()), 2), round(float(gap.max()), 2)],
                    wall_min_mm=round(float(self.footprint.exterior.distance(self.window.exterior)), 2))
