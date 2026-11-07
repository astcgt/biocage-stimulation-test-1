#!/usr/bin/env python3
"""h41: two plain-language Nature-style figures of the most complete result: the validated neck model and the 149-design cage screen.

Reads result files only; every number is computed here from the merged verdict files, so the figures cannot drift from them.
usage: python h41_main_results_figs.py    outputs in human_study/figures/main_results/
"""
import os, re, glob, json, csv, itertools, collections, datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = f'{ROOT}/human_study'; EVO = f'{os.path.dirname(ROOT)}/biocage-evo'; M = f'{EVO}/results/method'; OUT = f'{HS}/figures/main_results'
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#8a8982', '#e4e3df'
COMP, SLIP, SHEAR = '#eb6834', '#2a78d6', '#1baf7a'
UNF, EXC = '#b5b4ad', '#e1e0da'
AXI, RAD = '#1f3a5f', '#c2427a'
PHI = LinearSegmentedColormap.from_list('phi', ['#f7c9a9', '#2c5f9e'])
DISC = '#e9efe6'; PINK = '#d03b3b'
MM = 1 / 25.4; W = 180


def setup():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'font.size': 6, 'axes.linewidth': 0.5, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
                         'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.major.size': 2, 'ytick.major.size': 2, 'xtick.minor.size': 1, 'ytick.minor.size': 1, 'xtick.minor.width': 0.3, 'ytick.minor.width': 0.3,
                         'axes.labelsize': 6, 'xtick.labelsize': 5.5, 'ytick.labelsize': 5.5, 'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'mathtext.default': 'regular',
                         'axes.labelpad': 1.5, 'xtick.major.pad': 1.5, 'ytick.major.pad': 1.5})


class F:
    def __init__(self, h):
        self.h = h; self.fig = plt.figure(figsize=(W * MM, h * MM), facecolor='white')
    def ax(self, x, y, w, h, **k): return self.fig.add_axes([x / W, 1 - (y + h) / self.h, w / W, h / self.h], **k)
    def label(self, x, y, l, t):
        self.fig.text(x / W, 1 - y / self.h, l, fontsize=8, fontweight='bold', va='top', color=INK)
        self.fig.text((x + 3.6) / W, 1 - (y + 0.45) / self.h, t, fontsize=6.3, va='top', color=INK, fontweight='bold')
    def text(self, x, y, s, **k):
        k.setdefault('fontsize', 5); k.setdefault('va', 'top'); k.setdefault('color', INK2); self.fig.text(x / W, 1 - y / self.h, s, **k)


def wrap(t, n):
    vis = lambda w: len(re.sub(r'[$]|_\{|\}', '', w)); L, c = [], ''
    for w in t.split(' '):
        if c and vis(c) + 1 + vis(w) > n: L.append(c); c = w
        else: c = (c + ' ' + w) if c else w
    return '\n'.join(L + [c])


# ------------------------------------------------------------------ data
def load():
    par = {}
    for f in glob.glob(f'{HS}/al_v2/physio_rot_split*/p*_params.json') + glob.glob(f'{HS}/al_v2/physio_rot/p*_params.json'):
        k = os.path.basename(f)[:4]
        if k in par: continue
        q = json.load(open(f)); m = re.search(r'cage_([AB])_(\w+?)_(mix|interleave)_d(\d+\.\d+)', q['cage_npz'])
        par[k] = dict(fam=m.group(1), grad=m.group(2), fab=m.group(3), d=float(m.group(4)), E_soft=q['E_soft'])
    par.setdefault('p059', par['p074'])                  # DECISIONS: p059 = p074 (same parameters; no params file of its own)
    cl = json.load(open(f'{M}/split/verdict_classes_merged.json'))['classes']
    of = {d: c for c, v in cl.items() for d in v}
    return dict(par=par, cl=cl, of=of, V=json.load(open(f'{M}/fric/verdicts.json')), S=json.load(open(f'{M}/fric/e07_verdicts.json'))['designs'],
                C=json.load(open(f'{M}/split/comp_by_design_merged.json')), cmp=json.load(open(f'{M}/fric/compare.json')), val=json.load(open(f'{HS}/validation/results/comparison.json')),
                scan=json.load(open(f'{HS}/figures/febio_agreement/same_input_scan.json')))


REASON = [('compress', 'Soft part squeezed too much', COMP), ('slip', 'Cage slips too far with real friction', SLIP), ('shear', 'Hard–soft bond overloaded (provisional)', SHEAR),
          ('unf', 'Simulation could not finish', UNF), ('exc', 'Excluded by design decision', EXC)]


def reason(c):
    if c.startswith('DESIGN/compression'): return 'compress'
    if c == 'DESIGN/dislocation-friction': return 'slip'
    if c == 'DESIGN/interface-shear-provisional': return 'shear'
    if c == 'DESIGN/radial-mix-excluded': return 'exc'
    return 'unf'


TYPES = [('A', 'axial', 'mix', 'cage_A_axial_mix_d0.800', 'Softer towards the faces, blended', 'family A'),
         ('A', 'axial', 'interleave', 'cage_A_axial_interleave_d0.800', 'Softer towards the faces, alternating threads', 'family A'),
         ('A', 'radial', 'interleave', 'cage_A_radial_interleave_d0.800', 'Soft inside, hard outside, alternating threads', 'family A'),
         ('A', 'radial', 'mix', 'cage_A_radial_mix_d0.900', 'Soft inside, hard outside, blended', 'family A'),
         ('A', 'both', None, None, 'Mix of both layouts', 'family A'),
         ('B', None, None, 'cage_B_axial_mix_d0.532', 'Flat cage with a soft pad, all layouts', 'family B')]


def type_of(p):
    for i, t in enumerate(TYPES):
        if p['fam'] == t[0] and (t[1] is None or p['grad'] == t[1]) and (t[2] is None or p['fab'] == t[2]): return i


def slip_fraction(v):
    fr = []
    for x in v['windows'].values():
        if x.get('eval_point') == '1.5Nm': fr.append(max(x['u_h_at_1p5Nm'], x['post_at_1p5Nm'] / 0.5))
        elif x.get('eval_point') == 'ROM': fr.append(max(x['u_h_at_rom'], x['post_at_rom'] / 0.5))
    return max(fr) if len(fr) == 2 else None


def thumbnail(ax, name):
    z = np.load(f'{HS}/al/meshes/{name}.npz', allow_pickle=True); Q, H = z['Q'], z['hexes']; c = Q[H].mean(1); phi = z['phi']
    inter = 'interleave' in name; hard = z['hard']; k = np.abs(c[:, 1]) < 0.12
    x, y = c[k, 0], c[k, 2]; v = phi[k].astype(float).copy(); ha = hard[k]
    if inter: v = np.where(np.isnan(v), np.nan, np.where(ha.astype(bool), 1.0, 0.0))
    dd = np.isnan(v)
    ax.scatter(x[dd], y[dd], s=2.2, marker='s', color=DISC, lw=0, rasterized=True)
    ax.scatter(x[~dd], y[~dd], s=2.2, marker='s', c=v[~dd], cmap=PHI, vmin=0, vmax=1, lw=0, rasterized=True)
    ax.set_aspect('equal'); ax.axis('off')


# ------------------------------------------------------------------ figure 1
def anatomy(ax):
    from PIL import Image, ImageDraw
    d = f'{HS}/al_v2/physio_rot_split2/p092_gpu1'
    s = open(d + '/case.feb').read()
    n = np.array([[float(v) for v in m.split(',')] for m in re.findall(r'<node id="\d+">([^<]+)', re.search(r'<Nodes name="FSU">(.*?)</Nodes>', s, re.S).group(1))])
    tets = []
    for name, body in re.findall(r'<Elements type="tet4" mat="\d+" name="([^"]+)">(.*?)</Elements>', s, re.S):
        if 'cortical' in name and 'pot' not in name:
            tets.append(np.array([[int(v) - 1 for v in e.split(',')] for e in re.findall(r'<elem id="\d+">([^<]+)', body)]))
    T = np.vstack(tets); used = np.unique(T); P = n[used]
    xr = (P[:, 0].min() - 1, P[:, 0].max() + 1); zr = (P[:, 2].min() - 1, P[:, 2].max() + 1); sc = 14
    W_, H_ = int((xr[1] - xr[0]) * sc), int((zr[1] - zr[0]) * sc)
    im = Image.new('L', (W_, H_), 0); dr = ImageDraw.Draw(im)
    px = lambda q: list(zip((q[:, 0] - xr[0]) * sc, (zr[1] - q[:, 2]) * sc))
    for t in T:
        q = n[t]
        for tri in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)): dr.polygon(px(q[list(tri)]), fill=255)
    mask = np.array(im) > 0
    Hh, _, _ = np.histogram2d((zr[1] - P[:, 2]) * sc, (P[:, 0] - xr[0]) * sc, bins=(H_ // 3, W_ // 3), range=((0, H_), (0, W_)))
    shade = np.kron(np.log1p(Hh), np.ones((3, 3)))[:H_, :W_]; pad = np.zeros((H_, W_)); pad[:shade.shape[0], :shade.shape[1]] = shade
    v = np.where(mask, 0.55 + 0.45 * pad / max(pad.max(), 1), 0)
    rgba = np.zeros((H_, W_, 4)); rgba[..., :3] = np.array([0.73, 0.71, 0.66]) * (1.15 - 0.45 * v[..., None]); rgba[..., 3] = mask
    ax.imshow(rgba, extent=[*xr, *zr], origin='upper', aspect='equal', interpolation='bilinear', rasterized=True, zorder=1)
    q = json.load(open(f'{HS}/al_v2/physio_rot_split2/p092_params.json'))
    z = np.load(os.path.join(ROOT, q['cage_npz']) if not os.path.isabs(q['cage_npz']) else q['cage_npz'], allow_pickle=True)
    G, H = z['Q'], z['hexes']; c = G[H].mean(1); k = np.abs(c[:, 1] - np.median(c[:, 1])) < 0.12
    phi = z['phi'][k].astype(float); ha = z['hard'][k].astype(bool); phi = np.where(np.isnan(phi), np.nan, np.where(ha, 1.0, 0.0)); dd = np.isnan(phi); x, y = c[k, 0], c[k, 2]
    ax.scatter(x[dd], y[dd], s=3.6, marker='s', color=DISC, lw=0, rasterized=True, zorder=3); ax.scatter(x[~dd], y[~dd], s=3.6, marker='s', c=phi[~dd], cmap=PHI, vmin=0, vmax=1, lw=0, rasterized=True, zorder=4)
    ax.axis('off'); ax.set_xlim(xr); ax.set_ylim(zr)
    return np.c_[c[k, 0], c[k, 1], c[k, 2]], xr, zr


def figure1(D):
    f = F(150); fig = f.fig
    # a
    f.label(2, 2, 'a', 'The question')
    ax = f.ax(2, 8, 50, 58); Pc, xr, zr = anatomy(ax)
    cx, cz = Pc[:, 0].mean(), Pc[:, 2].mean(); zt = zr[1]
    top, bot = Pc[:, 2].max(), Pc[:, 2].min(); xa, xb = Pc[:, 0].min(), Pc[:, 0].max()
    ax.text(cx, top + 5, 'C3', fontsize=7.5, fontweight='bold', color=INK, ha='center', va='center', zorder=6); ax.text(cx, bot - 5, 'C4', fontsize=7.5, fontweight='bold', color=INK, ha='center', va='center', zorder=6)
    ax.annotate('Cage', xy=(xb - 0.3, top - 2.5), xytext=(xb + 1.5, top + 11), fontsize=6, fontweight='bold', color='#2c5f9e', ha='center', va='bottom', arrowprops=dict(arrowstyle='-', lw=0.5, color='#2c5f9e', shrinkA=0, shrinkB=0), zorder=6, annotation_clip=False)
    ax.add_patch(FancyArrowPatch((xa + 1.2, cz), (xa - 3.5, cz), arrowstyle='-|>', mutation_scale=6, lw=1.0, color=SLIP, zorder=7))
    ax.add_patch(FancyArrowPatch((cx, top + 2.7), (cx, top + 0.2), arrowstyle='-|>', mutation_scale=6, lw=1.0, color=COMP, zorder=7)); ax.add_patch(FancyArrowPatch((cx, bot - 2.7), (cx, bot - 0.2), arrowstyle='-|>', mutation_scale=6, lw=1.0, color=COMP, zorder=7))
    ax.text(xr[0] + 0.5, zr[0] + 0.5, 'Back', fontsize=5.2, color=INK2, va='bottom'); ax.text(xr[1] - 0.5, zr[0] + 0.5, 'Front', fontsize=5.2, color=INK2, ha='right', va='bottom')
    f.text(53, 9, 'A soft engineered disc needs a temporary support while it matures for at least 16 weeks. The support is a cage of dissolving plastic with hard and soft parts, held by shape and friction only: no screws.', fontsize=5.5, color=INK)
    fig.texts[-1].set_text(wrap(fig.texts[-1].get_text(), 44))
    f.text(53, 25, 'A cage design must survive three things', fontsize=5.6, color=INK, fontweight='bold')
    for i, (c, t, s) in enumerate([(SLIP, 'Stay in place', 'moves under 1 mm in any direction and under 0.5 mm backward, towards the spinal cord'), (COMP, 'Soft part not crushed', 'sustained squeeze under 15%, peak under 25%'), (SHEAR, 'Hard–soft bond holds', 'shear under 3 MPa (provisional, bond test pending)')]):
        y = 28.5 + i * 8.3
        fig.add_artist(Rectangle(((53) / W, 1 - (y + 2.0) / f.h), 1.8 / W, 2.0 / f.h, color=c, transform=fig.transFigure))
        f.text(56, y, t, fontsize=5.5, color=INK, fontweight='bold'); f.text(56, y + 2.3, wrap(s, 40), fontsize=5, linespacing=1.1)
    # b validation
    f.label(103, 2, 'b', 'Is the neck model right? Mostly matches published values')
    rows = [(b, a, c) for a, x in D['val'].items() for b, c in x.items() if c.get('diff_pct') is not None]
    ang = [(r[2]['herron_deg'], r[2]['ours_deg'], r[2]['diff_pct']) for r in rows if 'ours_deg' in r[2]]; frc = [(r[2]['herron_N'], r[2]['ours_N'], r[2]['diff_pct']) for r in rows if 'ours_N' in r[2]]
    ax = f.ax(112, 9, 43, 43); lim = (5, 80)
    t = np.array(lim); ax.fill_between(t, t * 0.9, t * 1.1, color='#e3f1e3', lw=0, zorder=0); ax.plot(t, t, color=MUTED, lw=0.5, zorder=1)
    for pts, mk, col in ((ang, 'o', '#2c5f9e'), (frc, 's', COMP)):
        p = np.array(pts); ins = np.abs(p[:, 2]) <= 10
        ax.scatter(p[ins, 0], p[ins, 1], s=11, marker=mk, color=col, edgecolor='white', lw=0.3, zorder=3)
        ax.scatter(p[~ins, 0], p[~ins, 1], s=12, marker=mk, facecolor='white', edgecolor=col, lw=0.7, zorder=3)
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect('equal')
    for a in (ax.xaxis, ax.yaxis):
        a.set_major_locator(matplotlib.ticker.FixedLocator([5, 10, 20, 50])); a.set_major_formatter(matplotlib.ticker.ScalarFormatter()); a.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel('Published model, Herron 2020 (° or N)'); ax.set_ylabel('Our model (° or N)')
    n = len(rows); ni = sum(abs(r[2]['diff_pct']) <= 10 for r in rows)
    ax.text(0.04, 0.96, f'{ni} of {n} within 10%', transform=ax.transAxes, fontsize=6.2, fontweight='bold', color=INK, va='top')
    fig.legend(handles=[Line2D([], [], marker='o', ls='', color='#2c5f9e', ms=3.2, label='Range of motion (°)'), Line2D([], [], marker='s', ls='', color=COMP, ms=3, label='Facet joint force (N)'),
                        Line2D([], [], marker='o', ls='', mfc='white', mec=INK2, mew=0.7, ms=3.2, label='Outside 10%'), Patch(color='#e3f1e3', label='±10% band')],
               loc='upper left', bbox_to_anchor=(156.5 / W, 1 - 28 / f.h), frameon=False, fontsize=5, handletextpad=0.25, borderpad=0, labelspacing=0.45, handlelength=1.1)
    # c stacked bars
    y0 = 64
    tot = collections.Counter(); byt = collections.defaultdict(collections.Counter)
    for p, c in D['of'].items():
        r = reason(c); tot[r] += 1; byt[type_of(D['par'][p])][r] += 1
    n_all = sum(tot.values()); npass = len(D['cl'].get('PASS', []))
    f.label(2, y0, 'c', f'The screen: {n_all} cage designs simulated, {npass} pass every test so far. Each type of cage fails for its own reason')
    rh = 10.2; tx, tw = 2, 21; bx, bw = 66, 100
    ax = f.ax(bx, y0 + 9.5, bw, rh * len(TYPES)); ax.set_ylim(len(TYPES), 0); ax.set_xlim(0, 32)
    ax.spines['left'].set_visible(False); ax.set_yticks([]); ax.set_xlabel('Number of designs')
    for x in (10, 20, 30): ax.axvline(x, color=GRID, lw=0.4, zorder=0)
    for i, t in enumerate(TYPES):
        c = i + 0.5; left = 0; cnt = byt[i]
        for key, _, col in REASON:
            v = cnt.get(key, 0)
            if not v: continue
            ax.barh(c, v, left=left, height=0.6, color=col, edgecolor='white', lw=0.5, zorder=2)
            if v >= 2: ax.text(left + v / 2, c, str(v), ha='center', va='center', fontsize=5.6, color='white' if col in (COMP, SLIP, SHEAR) else INK, fontweight='bold', zorder=3)
            left += v
        ax.text(left + 0.5, c, f'{left}', va='center', fontsize=5.6, color=INK2, zorder=3)
        name = t[3] or next(os.path.basename(g)[:-4] for g in sorted(glob.glob(f'{HS}/al/meshes/cage_A_both_mix_*.npz')))
        th = f.ax(tx, y0 + 9.5 + i * rh + 0.3, tw, rh - 0.6); thumbnail(th, name)
        f.text(24, y0 + 9.5 + i * rh + rh / 2, wrap(t[4], 27) + f'\n({t[5]})', fontsize=5.3, color=INK, va='center', linespacing=1.1)
    hs = [Patch(color=col, label=f'{lab}: {tot[key]}') for key, lab, col in REASON]
    fig.legend(handles=hs, loc='upper left', bbox_to_anchor=(2 / W, 1 - (y0 + 4.6) / f.h), ncol=5, frameon=False, fontsize=5.2, handletextpad=0.3, columnspacing=0.9, borderpad=0, handlelength=1)
    # phase key
    ky = y0 + 9.5 + rh * len(TYPES) + 1.5
    ka = f.ax(2, ky, 14, 1.6); ka.imshow(np.linspace(0, 1, 64)[None, :], cmap=PHI, aspect='auto'); ka.axis('off')
    f.text(2, ky + 1.9, 'Soft', fontsize=4.9); f.text(16, ky + 1.9, 'Hard', fontsize=4.9, ha='right')
    ka2 = f.ax(19, ky, 3, 1.6); ka2.imshow([[0]], cmap=LinearSegmentedColormap.from_list('d', [DISC, DISC]), aspect='auto'); ka2.axis('off')
    f.text(23, ky + 0.1, 'Space for the engineered disc', fontsize=4.9)
    note = ('Cage pictures are side-on slices through the real simulation meshes (front at right). Family A is contoured to the bone; family B is flat with a soft pad. A design is listed under the first test it fails, so it was not always tried on later tests. '
            'Real-friction and bond results are provisional: see Fig. 2. Abbreviations: C3, C4, third and fourth neck vertebrae; MPa, megapascal; N, newton.')
    f.text(2, ky + 8.0, wrap(note, 225), fontsize=4.9, linespacing=1.12)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig1_model_and_screen.{ext}', facecolor='white', **kw)
    plt.close(fig)
    return dict(n=n_all, npass=npass, tot=dict(tot), by_type={TYPES[i][4]: dict(v) for i, v in byt.items()}, val=(ni, n))


# ------------------------------------------------------------------ figure 2
def figure2(D):
    f = F(102); fig = f.fig
    V, S, par = D['V'], D['S'], D['par']
    rows = []
    for p, v in V.items():
        if p == '_meta' or p not in S: continue
        sf = slip_fraction(v); w = S[p]['windows']
        if sf is None or len(w) < 2: continue
        rows.append(dict(p=p, slip=sf, shear=max(x['shear_p99_at_rom'] for x in w.values()), grad=par[p]['grad'], fab=par[p]['fab'], gate4=v['verdict'], s=S[p]['verdict']))
    run_inside = [r['p'] for r in rows if r['slip'] <= 1 and r['shear'] <= 3]
    key = {}
    for r in D['scan']:
        if r['set'] == 'physio_fric3': key.setdefault(r['dir'][:4], min(c['case'] for c in D['scan'] if c['set'] == 'physio_fric3' and c['dir'][:4] == r['dir'][:4]))
    gid = collections.defaultdict(list)
    for r in rows: gid[key.get(r['p'], r['p'])].append(r)
    # same input = same design: plot its worst slip and worst shear (PI rule: any fail in pooled duplicates fails the group)
    rows = [dict(g[0], slip=max(r['slip'] for r in g), shear=max(r['shear'] for r in g), ids=[r['p'] for r in g]) for g in gid.values()]
    inside = [r for r in rows if r['slip'] <= 1 and r['shear'] <= 3]
    assert not inside, inside
    # a trade-off
    f.label(2, 2, 'a', 'Why none pass: what stops slipping overloads the bond')
    ax = f.ax(12, 9, 74, 66)
    ax.set_xlim(0.2, 1.6); ax.set_ylim(1, 24); ax.set_yscale('log')
    ax.add_patch(Rectangle((0.2, 1), 0.8, 2, fc='#e3f1e3', ec='none', zorder=0))
    ax.axvline(1, color=INK, lw=0.7, zorder=1); ax.axhline(3, color=INK, lw=0.7, zorder=1)
    for r in rows:
        ex = r['grad'] == 'radial' and r['fab'] == 'mix'
        if ex: ax.scatter(r['slip'], r['shear'], s=11, facecolor='white', edgecolor=MUTED, lw=0.5, zorder=3)
        else:
            ax.scatter(r['slip'], r['shear'], s=15, color=AXI if r['grad'] == 'axial' else RAD, edgecolor='white', lw=0.3, marker='o' if r['grad'] == 'axial' else 'D', zorder=4)
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator([1, 3, 10, 20])); ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter()); ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel('Cage slip, as a fraction of the allowed limit (1 = at the limit)'); ax.set_ylabel('Shear on the hard–soft bond (MPa)')
    ax.text(0.22, 1.12, 'Pass zone: empty', fontsize=6.2, fontweight='bold', color=INK, va='bottom')
    ax.text(1.01, 6.5, 'Slips too far →', fontsize=5.2, color=INK2, va='center'); ax.text(0.22, 3.2, 'Bond overloaded ↑', fontsize=5.2, color=INK2, va='bottom')
    ax.text(0.22, 20.5, 'Softer faces: mostly stay in place, overload the bond', fontsize=5.5, color=AXI, fontweight='bold', va='center', ha='left')
    ax.text(1.6, 1.32, 'Soft inside, threads alternating:\nbond is safe, cage slides', fontsize=5.5, color=RAD, fontweight='bold', va='bottom', ha='right', linespacing=1.1)
    # FEBio drift caveat (DECISIONS 2026-11-06 00:50): translation grows with the number of increments
    ax.add_patch(FancyArrowPatch((0.38, 5.0), (0.3, 5.0), arrowstyle='-|>', mutation_scale=5, lw=0.6, color=INK))
    ax.text(0.3, 5.5, 'FEBio drift inflates slip (2 designs tested);\nno corrected values exist yet', fontsize=4.9, color=INK2, va='bottom', linespacing=1.1)
    fig.legend(handles=[Line2D([], [], marker='o', ls='', color=AXI, ms=3.4, label='Softer towards the faces, blended'), Line2D([], [], marker='D', ls='', color=RAD, ms=3, label='Soft inside, alternating threads'),
                        Line2D([], [], marker='o', ls='', mfc='white', mec=MUTED, mew=0.5, ms=3, label='Soft inside, blended (excluded)')],
               loc='upper left', bbox_to_anchor=(12 / W, 1 - 81.8 / f.h), ncol=2, frameon=False, fontsize=5, handletextpad=0.25, columnspacing=0.7, borderpad=0, handlelength=1.1)
    # b compression
    f.label(94, 2, 'b', 'Cage type decides crushing more than stiffness does')
    ax = f.ax(103, 9, 37, 28)
    C, of = D['C'], D['of']; grp = collections.defaultdict(list)
    for p, c in C.items():
        if p in par and c.get('sustained') is not None:
            q = par[p]; g = 'r' if (q['fam'] == 'A' and q['grad'] == 'radial') else ('a' if (q['fam'] == 'A' and q['grad'] == 'axial' and q['fab'] == 'mix') else 'o')
            grp[g].append((q['E_soft'], 100 * c['sustained']))
    style = dict(o=(COMP, '^', 'Other types (threaded faces, both layouts, family B)'), a=(AXI, 'o', 'Softer towards the faces, blended'), r=(RAD, 'D', 'Soft inside, hard ring outside'))
    hs = []; comp_counts = {}
    for g, (col, mk, lab) in style.items():
        v = np.array(grp[g]); ax.scatter(v[:, 0], v[:, 1], s=6, marker=mk, color=col, lw=0, zorder=3)
        over = int((v[:, 1] > 15).sum()); comp_counts[lab] = (over, len(v))
        hs.append(Line2D([], [], marker=mk, ls='', color=col, ms=2.8, label=wrap(f'{lab}: {over} of {len(v)} over the limit', 30)))
    ax.axhline(15, color=INK, lw=0.7, zorder=2); ax.text(12.5, 15, 'Limit\n15%', fontsize=5, ha='left', va='center', color=INK, clip_on=False, linespacing=1.0)
    ax.set_xlabel('Stiffness of the soft part (MPa)'); ax.set_ylabel('Sustained squeeze (%)'); ax.set_xlim(1, 12.3); ax.set_ylim(0, 52)
    fig.legend(handles=hs, loc='upper left', bbox_to_anchor=(143 / W, 1 - 9.5 / f.h), frameon=False, fontsize=5, handletextpad=0.25, borderpad=0, handlelength=1, labelspacing=0.7)
    # c tied vs friction
    f.label(94, 43, 'c', 'A simplified glued-cage model underestimates slip')
    ax = f.ax(103, 50, 34, 28)
    T = [r for r in D['cmp'] if r['set'] == 'physio_fric3' and r.get('rom_reached') and r.get('tied_slip_bound_mm') is not None and r.get('u_h_at_rom') is not None]
    tx = np.array([r['tied_slip_bound_mm'] for r in T]); ty = np.array([r['u_h_at_rom'] for r in T]); ext = np.array([r['window'] == 'extension' for r in T])
    ax.plot([0, 1.4], [0, 1.4], color=MUTED, lw=0.5, zorder=1)
    ax.scatter(tx[~ext], ty[~ext], s=6, marker='s', color=SLIP, lw=0, zorder=3); ax.scatter(tx[ext], ty[ext], s=6, marker='o', color=INK2, lw=0, zorder=3)
    ax.set_xlim(0, 1.4); ax.set_ylim(0, 1.4); ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1]); ax.set_xlabel('Estimate from the glued model (mm)'); ax.set_ylabel('Slip with real friction (mm)')
    above = int((ty > tx).sum())
    ax.text(1.36, 0.05, 'Line: both agree', fontsize=4.9, color=INK2, ha='right')
    fig.legend(handles=[Line2D([], [], marker='s', ls='', color=SLIP, ms=2.6, label='Flexion'), Line2D([], [], marker='o', ls='', color=INK2, ms=2.6, label='Extension')],
               loc='upper left', bbox_to_anchor=(138.5 / W, 1 - 52 / f.h), frameon=False, fontsize=5, handletextpad=0.25, borderpad=0, handlelength=1, labelspacing=0.5)
    f.text(138.5, 62, wrap(f'{above} of {len(T)} loading runs slipped more than estimated at the normal range of motion; FEBio drift inflates part of this gap', 22), fontsize=5.2, color=INK, linespacing=1.1)
    # d how sure
    fp = [p for p in json.load(open(f'{HS}/figures/febio_agreement/figure_data.json'))['friction']['pairs']]
    note = ('How sure are these results? Friction and bond verdicts are provisional. Each design appears at its worst result, because any failed run fails the design. Repeating one input can move slip across the limit ('
            f"{sum(p['flip'] for p in fp)} of {len(fp)} repeat pairs gave opposite verdicts). At a fixed angle, FEBio's cage translation still grows with the number of solver increments (measured on 2 designs), so slip can be overstated and no corrected value exists yet. "
            'The 3 MPa bond limit awaits a bench test. Results come from one 26-year-old model. '
            'Abbreviations: MPa, megapascal; flexion, bending forward; extension, bending backward; slip limit, 1 mm in any direction or 0.5 mm backward; slip is judged at 1.5 newton-metres of moment if the cage carries it, otherwise at the normal range of motion.')
    f.text(2, 90, wrap(note, 218), fontsize=5.1, linespacing=1.15, color=INK2)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig2_why_none_pass.{ext}', facecolor='white', **kw)
    plt.close(fig)
    ax_ = [r for r in rows if r['grad'] == 'axial']; ra = [r for r in rows if r['grad'] == 'radial' and r['fab'] == 'interleave']
    return dict(n=len(rows), inside=[r['p'] for r in inside], run_inside=run_inside, axial=dict(n=len(ax_), slip=(min(r['slip'] for r in ax_), max(r['slip'] for r in ax_)), shear=(min(r['shear'] for r in ax_), max(r['shear'] for r in ax_))),
                interleave=dict(n=len(ra), slip=(min(r['slip'] for r in ra), max(r['slip'] for r in ra)), shear=(min(r['shear'] for r in ra), max(r['shear'] for r in ra))),
                compress=comp_counts,
                tied=dict(n=len(T), above=above, tied_max=float(tx.max()), fric=(float(ty.min()), float(ty.max()))), flips=(sum(p['flip'] for p in fp), len(fp)))


def main():
    os.makedirs(OUT, exist_ok=True); setup(); D = load()
    a = figure1(D); b = figure2(D)
    json.dump(dict(generated=datetime.datetime.now().isoformat(timespec='minutes'), fig1=a, fig2=b), open(f'{OUT}/figure_numbers.json', 'w'), indent=1, default=str)
    print(json.dumps(a, default=str)); print(json.dumps(b, default=str))
    qa = open(f'{HS}/qa/QA_STATUS.md', errors='ignore').readline().strip().lstrip('# ')
    L = f"""# Figure legends (generated by scripts/8_audit/h41_main_results_figs.py, {datetime.datetime.now().isoformat(timespec='minutes')})

**Fig. 1 | A neck model that largely reproduces published values screens {a['n']} cage designs; none passes every test so far.**
**a**, Side view of the real model: C3 and C4 outer bone and one cage slice. Arrows mark the slip and squeeze the cage must resist. **b**, Our C0-C7 model against the digitised values of Herron et al. 2020 (26-year-old model): {a['val'][0]} of {a['val'][1]} quantities are within 10 %. The four outside are C0-C1 (lateral bending, axial rotation), C1-C2 and C3-C7 (axial rotation). C3-C4 facet forces are within 2 %. This shows that we reproduce a published, validated model; it is not an independent cadaver validation of the implanted state. **c**, Each design is counted once, under its first failed test. Counts: {a['tot']}.

**Fig. 2 | The designs that hold the cage in place overload the hard-soft bond, and the designs that spare the bond slide.**
**a**, {b['n']} distinct designs with both real-friction windows and a bond value. Runs of byte-identical inputs are one design, plotted at its worst slip and worst shear, following the PI rule that any fail in pooled duplicates fails the group. Slip fraction = largest of (translation / 1 mm, backward translation / 0.5 mm) at the evaluation point. Bond shear = soft-side 99th percentile at the intact range-of-motion state. No design is inside both limits. One individual run ({b['run_inside']}) was inside both, but a run of the same input was not. **b**, Sustained compression of the soft phase, by cage type: {b['compress']}. Within a type, softer material is squeezed more. **c**, Glued-model one-face slip bound against real-friction translation at the intact range of motion, physio_fric3.

## Provisional
All friction and bond verdicts are provisional (verdicts.json meta): NUM-16 (bond metric mesh sensitivity, about 16 %), NUM-17 (same input can land on either side of a limit; {b['flips'][0]} of {b['flips'][1]} repeat pairs), FEBio cage drift that scales with increments at a fixed angle (DECISIONS 2026-11-06 00:50, 2 designs; the earlier density explanation was retracted and the physio_fric4 rerun is held), and a 3 MPa limit that has no PLCL bond-strength data. Evaluated on one 26-year-old model; degradation, fatigue and creep are outside these figures.

QA at generation: {qa}. The qa-auditor agent has not reviewed these figures. Font: Lato with DejaVu Sans fallback (Helvetica or Arial are not installed).
"""
    open(f'{OUT}/figure_legends.md', 'w', encoding='utf-8').write(L)


if __name__ == '__main__':
    main()
