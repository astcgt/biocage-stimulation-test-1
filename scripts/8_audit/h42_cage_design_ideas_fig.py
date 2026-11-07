#!/usr/bin/env python3
"""h42: plain-language Nature-style gallery of the cage design ideas: the choices that define a cage and one representative of each of the 12 design types.

Geometry comes from the real simulation meshes (al/meshes, built by h12); types, parameters and outcomes from the params files and merged verdict classes.
Representative of a type = among designs with the type's most common outcome, the one closest to the median of that group in (d, E_soft, E_hard, theta), each scaled by its range over the screen.
usage: python h42_cage_design_ideas_fig.py    outputs in human_study/figures/main_results/
"""
import os, re, glob, json, collections, datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = f'{ROOT}/human_study'; EVO = f'{os.path.dirname(ROOT)}/biocage-evo'; M = f'{EVO}/results/method'; OUT = f'{HS}/figures/main_results'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8982'
PHI = LinearSegmentedColormap.from_list('phi', ['#f7c9a9', '#2c5f9e'])
DISC = '#e9efe6'; MM = 1 / 25.4; W, H_FIG = 180, 216
OUTCOME = dict(compress=('Soft part squeezed too much', '#eb6834'), slip=('Slips too far with real friction', '#2a78d6'), shear=('Bond overloaded (provisional)', '#1baf7a'), unf=('Simulation could not finish', '#b5b4ad'), exc=('Excluded by design decision', '#e1e0da'))
FACES = np.array([[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])


def reason(c):
    if c.startswith('DESIGN/compression'): return 'compress'
    if c == 'DESIGN/dislocation-friction': return 'slip'
    if c == 'DESIGN/interface-shear-provisional': return 'shear'
    if c == 'DESIGN/radial-mix-excluded': return 'exc'
    return 'unf'


def load_designs():
    par = {}
    for f in glob.glob(f'{HS}/al_v2/physio_rot_split*/p*_params.json') + glob.glob(f'{HS}/al_v2/physio_rot/p*_params.json'):
        k = os.path.basename(f)[:4]
        if k in par: continue
        q = json.load(open(f)); m = re.search(r'cage_([AB])_(\w+?)_(mix|interleave)_d(\d+\.\d+)', q['cage_npz'])
        par[k] = dict(id=k, fam=m.group(1), grad=m.group(2), fab=m.group(3), d=float(m.group(4)), E_soft=q['E_soft'], E_hard=q['E_hard'], theta=q['theta'], npz=q['cage_npz'])
    cl = json.load(open(f'{M}/split/verdict_classes_merged.json'))['classes']
    for c, v in cl.items():
        for d in v:
            if d in par: par[d]['out'] = reason(c)
    par = {k: v for k, v in par.items() if 'out' in v}
    extra = [d for v in cl.values() for d in v if d not in par]        # p059 = p074 (DECISIONS): counted, no params file of its own
    return par, cl, extra


def pick(par):
    keys = ('d', 'E_soft', 'E_hard', 'theta'); all_ = np.array([[p[k] for k in keys] for p in par.values()]); span = all_.max(0) - all_.min(0)
    T = {}
    for fam in 'AB':
        for fab in ('mix', 'interleave'):
            for grad in ('axial', 'radial', 'both'):
                g = [p for p in par.values() if (p['fam'], p['fab'], p['grad']) == (fam, fab, grad)]
                cnt = collections.Counter(p['out'] for p in g); top, n = cnt.most_common(1)[0]
                s = [p for p in g if p['out'] == top]; X = np.array([[p[k] for k in keys] for p in s]) / span; c = np.median(X, 0)
                best = s[int(np.argmin(((X - c) ** 2).sum(1)))]
                T[(fam, fab, grad)] = dict(rep=best, n=len(g), top=top, n_top=n, counts=cnt)
    return T


def mesh(npz):
    z = np.load(npz if os.path.isabs(npz) else os.path.join(ROOT, npz), allow_pickle=True); Q = z['Q']; H = z['hexes']; cage = z['region'] == 0
    v = np.where(z['hard'].astype(bool), 1.0, 0.0) if 'interleave' in npz else z['phi'].astype(float)
    return Q, H, cage, v, z


def cutaway(ax, npz, az=np.radians(-28), el=np.radians(26)):
    Q, H, cage, v, _ = mesh(npz); c = Q[H].mean(1); ym = np.median(c[:, 1])
    keep = np.where(cage & (c[:, 1] >= ym))[0]
    F = H[keep][:, FACES]; owner = np.repeat(keep, 6); F = F.reshape(-1, 4)
    key = np.sort(F, 1); _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True); ext = cnt[inv.ravel()] == 1
    F, owner = F[ext], owner[ext]; P = Q[F]; cen = P.mean(1)
    n = np.cross(P[:, 2] - P[:, 0], P[:, 3] - P[:, 1]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    n *= np.sign(((cen - c[owner]) * n).sum(1, keepdims=True))
    ca, sa, ce, se = np.cos(az), np.sin(az), np.cos(el), np.sin(el)
    def rot(a):
        x1 = a[..., 0] * ca - a[..., 1] * sa; y1 = a[..., 0] * sa + a[..., 1] * ca; z1 = a[..., 2]
        return x1, y1 * ce - z1 * se, z1 * ce + y1 * se
    sx, depth, sz = rot(P); nx, ny, nz = rot(n)
    vis = ny < 0; order = np.argsort(-depth.mean(1)[vis])
    polys = np.stack([sx[vis], sz[vis]], -1)[order]
    base = PHI(np.clip(v[owner[vis]][order], 0, 1))[:, :3]
    light = np.clip(0.62 + 0.38 * (-ny[vis][order] * 0.75 + nz[vis][order] * 0.65), 0.45, 1.0)[:, None]
    col = base * light
    ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.08, rasterized=True))
    ax.set_xlim(polys[..., 0].min() - 0.2, polys[..., 0].max() + 0.2); ax.set_ylim(polys[..., 1].min() - 0.2, polys[..., 1].max() + 0.2); ax.set_aspect('equal'); ax.axis('off')


def slice_view(ax, npz, xlim=None):
    Q, H, cage, v, _ = mesh(npz); c = Q[H].mean(1); k = np.abs(c[:, 1] - np.median(c[:, 1])) < 0.11
    if xlim: k &= (c[:, 0] > xlim[0] - 0.2) & (c[:, 0] < xlim[1] + 0.2)
    polys = Q[H[k]][:, [0, 1, 5, 4]][..., [0, 2]]; vv = v[k]; cg = cage[k]
    col = np.where(cg[:, None], PHI(np.clip(np.nan_to_num(vv), 0, 1))[:, :3], np.array(matplotlib.colors.to_rgb(DISC)))
    ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.08, rasterized=True))
    ax.set_xlim(xlim if xlim else (polys[..., 0].min(), polys[..., 0].max())); ax.set_ylim(polys[..., 1].min() - 0.05, polys[..., 1].max() + 0.05); ax.set_aspect('equal'); ax.axis('off')


def face_view(ax, npz):
    Q, H, cage, v, z = mesh(npz); lay = z['layer']; k = lay == lay.max()
    polys = Q[H[k]][:, [4, 5, 6, 7]][..., [0, 1]]; vv = v[k]; cg = cage[k]
    col = np.where(cg[:, None], PHI(np.clip(np.nan_to_num(vv), 0, 1))[:, :3], np.array(matplotlib.colors.to_rgb(DISC)))
    ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.08, rasterized=True))
    ax.set_xlim(polys[..., 0].min(), polys[..., 0].max()); ax.set_ylim(polys[..., 1].min(), polys[..., 1].max()); ax.set_aspect('equal'); ax.axis('off')


class F:
    def __init__(self, h):
        self.h = h; self.fig = plt.figure(figsize=(W * MM, h * MM), facecolor='white')
    def ax(self, x, y, w, h): return self.fig.add_axes([x / W, 1 - (y + h) / self.h, w / W, h / self.h])
    def text(self, x, y, s, **k):
        k.setdefault('fontsize', 5.3); k.setdefault('va', 'top'); k.setdefault('color', INK); self.fig.text(x / W, 1 - y / self.h, s, **k)
    def label(self, x, y, l, t):
        self.text(x, y, l, fontsize=8, fontweight='bold'); self.text(x + 3.6, y + 0.45, t, fontsize=6.3, fontweight='bold')


def main():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'font.size': 6, 'pdf.fonttype': 42, 'mathtext.default': 'regular'})
    par, cl, extra = load_designs(); T = pick(par)
    f = F(H_FIG); fig = f.fig
    ex = lambda fam, fab, grad: T[(fam, fab, grad)]['rep']['npz']
    # a: the choices
    f.label(2, 2, 'a', 'Every cage comes from three design choices')
    cols = [2, 62, 134]
    f.text(cols[0], 8.5, '1  Shape: how it meets the bone', fontweight='bold', fontsize=5.8)
    f.text(cols[1], 8.5, '2  Layout: where the softer material sits', fontweight='bold', fontsize=5.8)
    f.text(cols[2], 8.5, '3  Printing: how the two plastics combine', fontweight='bold', fontsize=5.8)
    for i, (fam, lab, sub) in enumerate((('A', 'Family A: contoured', 'follows the bone surface'), ('B', 'Family B: flat', 'with a 0.6 mm soft pad'))):
        a = f.ax(cols[0] + i * 28, 12, 26, 13); slice_view(a, ex(fam, 'mix', 'axial')); f.text(cols[0] + i * 28, 26, lab, fontweight='bold', fontsize=5.3); f.text(cols[0] + i * 28, 28.2, sub, fontsize=5, color=INK2)
    for i, (g, lab, sub) in enumerate((('axial', 'Towards the faces', 'where it touches bone'), ('radial', 'Towards the disc', 'hard ring outside'), ('both', 'Both', 'the softer one applies'))):
        a = f.ax(cols[1] + i * 24, 12, 22, 13); slice_view(a, ex('A', 'mix', g)); f.text(cols[1] + i * 24, 26, lab, fontweight='bold', fontsize=5.3); f.text(cols[1] + i * 24, 28.2, sub, fontsize=5, color=INK2)
    for i, (fb, lab, sub) in enumerate((('mix', 'Blended', 'mixing nozzle, smooth steps'), ('interleave', 'Alternating threads', '0.4 mm hard and soft lines'))):
        a = f.ax(cols[2] + i * 23, 12, 20, 13); slice_view(a, ex('A', fb, 'radial'), xlim=(-5.4, -3.2)); f.text(cols[2] + i * 23, 26, lab, fontweight='bold', fontsize=5.3); f.text(cols[2] + i * 23, 28.2, wrap(sub, 24), fontsize=5, color=INK2, linespacing=1.1)
    f.text(2, 32.6, wrap('Four numbers also vary across designs: how far the vertebrae are spread during insertion (d, 0.5–1.5 mm), the stiffness of the soft plastic (1.5–12 MPa) and of the hard plastic (250–890 MPa), and the blending rule (θ). Every cage has a central window that holds the engineered disc.', 225), fontsize=5.1, color=INK2, linespacing=1.1)
    # b: gallery
    y0 = 40
    f.label(2, y0, 'b', 'The 12 design types, one representative of each')
    gx = [17, 71, 125]; cw = 53; rh = 39.5; yg = y0 + 10
    for x, s in zip(gx, ('Softer towards the faces', 'Softer towards the disc', 'Both')):
        f.text(x, y0 + 6, s, fontweight='bold', fontsize=6)
    rows = [('A', 'mix', 'Family A\ncontoured\nblended'), ('A', 'interleave', 'Family A\ncontoured\nthreads'), ('B', 'mix', 'Family B\nflat\nblended'), ('B', 'interleave', 'Family B\nflat\nthreads')]
    sel = {}
    for r, (fam, fab, lab) in enumerate(rows):
        y = yg + r * rh
        f.text(2, y + 1, lab, fontweight='bold', fontsize=5.5, linespacing=1.15)
        for c, grad in enumerate(('axial', 'radial', 'both')):
            t = T[(fam, fab, grad)]; p = t['rep']; x = gx[c]; sel[f'{fam}/{fab}/{grad}'] = dict(id=p['id'], d=p['d'], E_soft=p['E_soft'], E_hard=p['E_hard'], theta=p['theta'], n=t['n'], outcome=t['top'], n_outcome=t['n_top'], counts=dict(t['counts']))
            a = f.ax(x, y, 32, 25); cutaway(a, p['npz'])
            a = f.ax(x + 33, y + 1, 18, 14); face_view(a, p['npz'])
            f.text(x + 33, y + 16, 'Face on bone', fontsize=4.7, color=INK2)
            f.text(x, y + 26, f"{p['id']}: d {p['d']:.2f} mm, soft {p['E_soft']:.1f} MPa, hard {p['E_hard']:.0f} MPa", fontsize=5.0, color=INK2)
            lab_o, col = OUTCOME[t['top']]
            fig.add_artist(Rectangle((x / W, 1 - (y + 30.8) / f.h), 1.6 / W, 1.6 / f.h, color=col, transform=fig.transFigure))
            f.text(x + 2.4, y + 29.0, wrap(lab_o, 44), fontsize=5.1)
            f.text(x + 2.4, y + 31.2, f"{t['n_top']} of {t['n']} designs of this type", fontsize=5.0, color=INK2)
    # key
    yk = yg + 4 * rh - 2
    a = f.ax(2, yk, 16, 1.7); a.imshow(np.linspace(0, 1, 64)[None, :], cmap=PHI, aspect='auto'); a.axis('off')
    f.text(2, yk + 2, 'Soft', fontsize=4.9, color=INK2); f.text(18, yk + 2, 'Hard', fontsize=4.9, color=INK2, ha='right')
    fig.add_artist(Rectangle((21 / W, 1 - (yk + 1.7) / f.h), 3 / W, 1.7 / f.h, color=DISC, transform=fig.transFigure))
    f.text(25, yk + 0.1, 'Window for the engineered disc', fontsize=4.9, color=INK2)
    note = ('All pictures are the real simulation meshes. 3D views show half of the cage, cut down the middle, with the front at right. Each representative has the most common result of its type and the most typical settings among those designs; it is not the best design. '
            'Coloured squares give the first test that designs of the type fail; real-friction and bond results are provisional. No design passes every test so far. '
            'Abbreviations: d, distraction, the spreading of the vertebrae during insertion; MPa, megapascal, a unit of stiffness; θ, blending parameter of the plastic mixture.')
    f.text(2, yk + 5, wrap(note, 215), fontsize=4.9, color=INK2, linespacing=1.12)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig3_cage_design_ideas.{ext}', facecolor='white', **kw)
    plt.close(fig)
    ds = np.array([p['d'] for p in par.values()]); es = np.array([p['E_soft'] for p in par.values()]); eh = np.array([p['E_hard'] for p in par.values()]); th = np.array([p['theta'] for p in par.values()])
    out = dict(generated=datetime.datetime.now().isoformat(timespec='minutes'), n_with_params=len(par), extra=extra, ranges=dict(d=(ds.min(), ds.max()), E_soft=(es.min(), es.max()), E_hard=(eh.min(), eh.max()), theta=(th.min(), th.max())), representatives=sel)
    json.dump(out, open(f'{OUT}/fig3_representatives.json', 'w'), indent=1, default=str)
    print(json.dumps(out['ranges'], default=str)); print(extra)
    for k, v in sel.items(): print(k, v['id'], v['d'], round(v['E_soft'], 1), v['outcome'], v['n_outcome'], '/', v['n'])


def wrap(t, n):
    L, c = [], ''
    for w in t.split(' '):
        if c and len(c) + 1 + len(w) > n: L.append(c); c = w
        else: c = (c + ' ' + w) if c else w
    return '\n'.join(L + [c])


if __name__ == '__main__':
    main()
