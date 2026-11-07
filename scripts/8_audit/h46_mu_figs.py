#!/usr/bin/env python3
"""h46: two figures on the tied screen's friction lower bound (mu_squeeze): fig_mu_poster (what holds up) and fig_mu_gaps (what does not yet).
Reads result files only: best_by_design_merged.json, numconv and degr compare.json, fric/compare.json, gpufe_verify/v2/v17a_hold.json, figures/mu_requirement/mu_face_scan.json (h45).
usage: python h46_mu_figs.py    outputs in human_study/figures/mu_requirement/
"""
import os, re, glob, json, collections, datetime
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = f'{ROOT}/human_study'; EVO = f'{os.path.dirname(ROOT)}/biocage-evo'; M = f'{EVO}/results/method'; OUT = f'{HS}/figures/mu_requirement'
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#8a8982', '#e4e3df'
BLUE, ORANGE, AQUA, CRIT = '#2a78d6', '#eb6834', '#1baf7a', '#d03b3b'
BAND = '#e3f1e3'; PHI = LinearSegmentedColormap.from_list('phi', ['#f7c9a9', '#2c5f9e']); DISC = '#e9efe6'
WIN = ['flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right']
NAME = dict(flexion='Bending forward', extension='Bending backward', LB_right='Side bending, right', LB_left='Side bending, left', AR_left='Twisting, left', AR_right='Twisting, right')
MM = 1 / 25.4; W = 180


class F:
    def __init__(self, h):
        self.h = h; self.fig = plt.figure(figsize=(W * MM, h * MM), facecolor='white')
    def ax(self, x, y, w, h): return self.fig.add_axes([x / W, 1 - (y + h) / self.h, w / W, h / self.h])
    def text(self, x, y, s, **k):
        k.setdefault('fontsize', 5.6); k.setdefault('va', 'top'); k.setdefault('color', INK); self.fig.text(x / W, 1 - y / self.h, s, **k)
    def label(self, x, y, l, t, fs=6.8):
        self.text(x, y, l, fontsize=8.5, fontweight='bold'); self.text(x + 3.9, y + 0.4, t, fontsize=fs, fontweight='bold')


def wrap(t, n):
    L, c = [], ''
    for w in t.split(' '):
        if c and len(c) + 1 + len(w) > n: L.append(c); c = w
        else: c = (c + ' ' + w) if c else w
    return '\n'.join(L + [c])


def setup():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'font.size': 6, 'axes.linewidth': 0.5, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5,
                         'xtick.major.size': 2, 'ytick.major.size': 2, 'axes.labelsize': 6, 'xtick.labelsize': 5.6, 'ytick.labelsize': 5.6, 'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'mathtext.default': 'regular', 'axes.labelpad': 1.5, 'xtick.major.pad': 1.5, 'ytick.major.pad': 1.5})


def load():
    B = json.load(open(f'{M}/split/best_by_design_merged.json'))
    R = [dict(design=p, window=w, mu=v[w]['mu_squeeze']) for p, v in B.items() for w in WIN if w in v and v[w].get('target_reached')]
    per = collections.defaultdict(dict)
    for r in R: per[r['design']][r['window']] = r['mu']
    six = {p: max(x.values()) for p, x in per.items() if len(x) == 6}; part = {p: max(x.values()) for p, x in per.items() if len(x) < 6}
    return B, R, per, six, part


def robustness():
    N = json.load(open(f'{M}/numconv/compare.json')); out = []
    lab = dict(numconv_dt=('Time step halved', 'one design'), numconv_pen05=('Contact stiffness halved', 'one design'), numconv_pen20=('Contact stiffness doubled', 'one design'), numconv_hz01=('Cage mesh twice as fine', 'one design'))
    for r in N['runs']:
        if r['set'] in lab:
            d = [abs(x['mu'] - x['mu'] / (1 + x['d_mu'])) for x in r['windows'].values() if x.get('d_mu') is not None and x.get('mu')]
            rel = [abs(x['d_mu']) for x in r['windows'].values() if x.get('d_mu') is not None]
            out.append((lab[r['set']][0], max(d), max(rel), lab[r['set']][1]))
    D = json.load(open(f'{M}/degr/compare.json')); dd = [abs(x['mu_worst'] - x['base_mu_worst']) for x in D if x.get('mu_worst') is not None and x.get('n_reached') == 6]
    out.append(('Soft plastic 2–10 times softer', max(dd), None, f"{len({x['design'] for x in D})} designs"))
    # GPU vs CPU on byte-identical inputs: valid pairs from the h38 scan
    fd = json.load(open(f'{HS}/figures/febio_agreement/figure_data.json'))['tied']['valid_pairs']; d = []; rel = []
    for a_set, a, b_set, b, w in fd:
        def get(s, cd):
            tag = ('' if s == 'physio_rot_split2' else s + '__') + cd + '__' + w
            return json.load(open(f'{M}/split/{tag}.e04.json'))['windows'][w]['mu_squeeze']
        x, y = get(a_set, a), get(b_set, b); d.append(abs(x - y)); rel.append(abs(x - y) / x)
    out.append(('GPU vs CPU linear solver', max(d), max(rel), f'{len(d)} load cases'))
    return out


def slice_poly(ax, name):
    z = np.load(f'{HS}/al/meshes/{name}.npz', allow_pickle=True); Q, H = z['Q'], z['hexes']; c = Q[H].mean(1); k = np.abs(c[:, 1] - np.median(c[:, 1])) < 0.11
    polys = Q[H[k]][:, [0, 1, 5, 4]][..., [0, 2]]; cg = z['region'][k] == 0; v = np.nan_to_num(z['phi'][k].astype(float))
    col = np.where(cg[:, None], PHI(np.clip(v, 0, 1))[:, :3], np.array(matplotlib.colors.to_rgb(DISC)))
    ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.08, rasterized=True))
    return polys


def poster(B, R, per, six, part, rob):
    f = F(127); fig = f.fig
    worst = np.array(list(six.values())); allmu = np.array([r['mu'] for r in R])
    # a concept
    f.label(2, 2, 'a', 'The question')
    ax = f.ax(3, 9, 48, 34); polys = slice_poly(ax, 'cage_A_axial_mix_d0.800')
    x0, x1 = polys[..., 0].min(), polys[..., 0].max(); z0, z1 = polys[..., 1].min(), polys[..., 1].max()
    ax.add_patch(Rectangle((x0 - 1, z1 + 0.02), x1 - x0 + 2, 1.15, fc='#c9c7be', ec='none')); ax.add_patch(Rectangle((x0 - 1, z0 - 1.17), x1 - x0 + 2, 1.15, fc='#c9c7be', ec='none'))
    ax.text((x0 + x1) / 2, z1 + 0.6, 'Bone (C3)', ha='center', va='center', fontsize=5.6); ax.text((x0 + x1) / 2, z0 - 0.6, 'Bone (C4)', ha='center', va='center', fontsize=5.6)
    zm = (z0 + z1) / 2
    ax.add_patch(FancyArrowPatch((x0 + 4.2, zm), (x0 - 0.9, zm), arrowstyle='-|>', mutation_scale=9, lw=1.6, color=ORANGE, zorder=5))
    ax.text(x0 + 4.4, zm, 'Tissues push\nthe cage out', fontsize=5.6, va='center', color=INK, zorder=6, fontweight='bold', linespacing=1.05)
    for zz in (z1 - 0.32, z0 + 0.32):
        ax.add_patch(FancyArrowPatch((x0 + 2.2, zz), (x0 + 6.4, zz), arrowstyle='-|>', mutation_scale=7, lw=1.2, color=BLUE, zorder=5))
    ax.text(x0 + 6.6, z1 - 0.32, 'Friction', fontsize=5.4, va='center', color=INK, zorder=6, fontweight='bold'); ax.text(x0 + 6.6, z0 + 0.32, 'Friction', fontsize=5.4, va='center', color=INK, zorder=6, fontweight='bold')
    ax.set_xlim(x0 - 1.2, x1 + 0.2); ax.set_ylim(z0 - 1.25, z1 + 1.25); ax.set_aspect('equal'); ax.axis('off')
    f.text(3, 44.5, wrap('With no screws, only friction holds the cage. How much friction does it need? A low number means a safe margin: this is the friction lower bound (μ$_{req}$).', 58), fontsize=5.6, color=INK2, linespacing=1.12)
    # b strip
    f.label(56, 2, 'b', f'Friction needed to stop the whole cage being squeezed out: below the assumed friction in all {len(R)} load cases', fs=6.5)
    ax = f.ax(84, 10, 92, 42); rng = np.random.default_rng(1)
    ax.add_patch(Rectangle((0.2, -0.6), 0.25, 6.2, fc=BAND, ec='none', zorder=0)); ax.axvline(0.3, color=INK, lw=0.8, zorder=1)
    for i, w in enumerate(WIN):
        v = np.array([r['mu'] for r in R if r['window'] == w]); y = 5 - i + rng.uniform(-0.24, 0.24, len(v))
        ax.scatter(v, y, s=5, color=BLUE, alpha=0.7, lw=0, zorder=3); ax.plot([np.median(v)] * 2, [5 - i - 0.34, 5 - i + 0.34], color=INK, lw=1.0, zorder=4)
    ax.set_yticks(range(6)); ax.set_yticklabels([NAME[w] for w in WIN][::-1], fontsize=5.6); ax.set_xlim(0, 0.5); ax.set_ylim(-0.6, 5.6); ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5]); ax.tick_params(axis='y', length=0); ax.spines['left'].set_visible(False)
    ax.set_xlabel('Friction coefficient μ'); ax.text(0.325, 5.45, 'Assumed available\n0.3 (range 0.2–0.45)', fontsize=5.4, va='top', color=INK, linespacing=1.05)
    # c histogram
    y2 = 57
    f.label(2, y2 + 5, 'c', f'Every design has margin ({len(six)} designs, worst of six motions)')
    ax = f.ax(10, y2 + 12, 62, 38); bins = np.arange(0, 0.5001, 0.02)
    ax.add_patch(Rectangle((0.2, 0), 0.25, 1, transform=ax.get_xaxis_transform(), fc=BAND, ec='none', zorder=0)); ax.axvline(0.3, color=INK, lw=0.8, zorder=1)
    ax.hist(worst, bins=bins, color=BLUE, edgecolor='white', lw=0.4, zorder=3); ax.set_xlim(0, 0.5); ax.set_xlabel('Friction needed, worst motion of each design'); ax.set_ylabel('Designs')
    ax.annotate(f'Highest: {worst.max():.3f}', xy=(worst.max(), 2), xytext=(0.215, ax.get_ylim()[1] * 0.55), fontsize=5.8, color=INK, fontweight='bold', arrowprops=dict(arrowstyle='-', lw=0.5, color=INK2))
    # tiles
    for i, (big, small) in enumerate(((f'{0.3 / worst.max():.1f}×', 'margin of the worst design\nat the assumed μ of 0.3'), (f'{0.2 / worst.max():.1f}×', 'margin at the low end\nof the range, μ 0.2'))):
        f.text(76, y2 + 12 + i * 19, big, fontsize=15, fontweight='bold', color=BLUE); f.text(76, y2 + 20.5 + i * 19, small, fontsize=5.4, color=INK2, linespacing=1.1)
    # d robustness
    f.label(103, y2 + 5, 'd', 'The answer barely moves when settings change')
    ax = f.ax(133, y2 + 12, 43, 38); names = [r[0] for r in rob][::-1]; vals = [r[1] for r in rob][::-1]; notes = [r[3] for r in rob][::-1]
    ax.barh(range(len(rob)), vals, color=BLUE, height=0.5, zorder=2)
    for i, (v, n) in enumerate(zip(vals, notes)): ax.text(max(v, 0) + 0.00015, i, f'{v:.4f}', va='center', fontsize=5.2, color=INK)
    ax.set_yticks(range(len(rob))); ax.set_yticklabels([f'{a} ({b})' if False else a for a, b in zip(names, notes)], fontsize=5.4); ax.set_xlim(0, 0.0065); ax.set_xticks([0, 0.002, 0.004, 0.006]); ax.tick_params(axis='y', length=0); ax.spines['left'].set_visible(False)
    ax.set_xlabel('Largest change in μ (gap to μ 0.3 is at least 0.13)')
    f.text(2, y2 + 58.5, wrap(f'Formula check: exact on textbook cases (0.3000 computed, 0.3000 expected). Settings tests used one family A design, except softening ({rob[4][3]}) and GPU vs CPU ({rob[5][3]}). Model: cage glued to bone at 1.5 N·m under a 100 N load. μ$_{{req}}$ covers the whole cage being squeezed out, not slip distance. μ of this plastic on bone is assumed, not yet measured; not yet confirmed by real-friction runs. Abbreviations: C3, C4, neck vertebrae; GPU, CPU, graphics and central processors; N·m, newton-metre; μ, friction coefficient.', 215), fontsize=5, color=INK2, linespacing=1.12)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))): fig.savefig(f'{OUT}/fig_mu_poster.{ext}', facecolor='white', **kw)
    plt.close(fig)


def gaps(B, R, per, six, part, rob, S):
    f = F(160); fig = f.fig
    n_all = sum(len(v) for v in json.load(open(f'{M}/split/verdict_classes_merged.json'))['classes'].values())
    rows = [r for r in S if r.get('top_mu_scaled') is not None and r.get('bot_mu_scaled') is not None]
    ten = np.array([max(r['top_tension_frac'], r['bot_tension_frac']) for r in rows]); pf = np.array([max(r['top_mu_scaled'], r['bot_mu_scaled']) for r in rows]); ms = np.array([r['mu_squeeze'] for r in rows])
    grp = np.array([0 if r['window'] in ('flexion', 'extension') else (1 if r['window'].startswith('LB') else 2) for r in rows])
    # a tension
    f.label(2, 2, 'a', 'The glue pulls on the bone; a real cage cannot')
    ax = f.ax(10, 10, 46, 32); is_ext = np.array([r['window'] == 'extension' for r in rows]); tp = np.clip(100 * ten, 0, 209)
    ax.hist([tp[~is_ext], tp[is_ext]], bins=np.arange(0, 215, 10), stacked=True, color=[MUTED, ORANGE], edgecolor='white', lw=0.4, label=['Other five motions', 'Bending backward'])
    ax.set_xlabel('Tension on the glued face (% of its net pressing force)'); ax.set_ylabel('Load cases'); ax.set_xlim(0, 210)
    ax.legend(loc='upper center', frameon=False, fontsize=5.3, borderpad=0, handlelength=1, bbox_to_anchor=(0.62, 0.78))
    ax.text(0.97, 0.97, f'Bending backward: median {100 * np.median(ten[is_ext]):.0f}%\nOther motions: median {100 * np.median(ten[~is_ext]):.0f}%', transform=ax.transAxes, ha='right', va='top', fontsize=5.6, fontweight='bold', linespacing=1.1)
    # b one face vs both
    n03 = int((pf > 0.3).sum()); n035 = int((pf > 0.35).sum())
    f.label(62, 2, 'b', 'μ$_{req}$ counts both faces; one face can need far more')
    ax = f.ax(71, 10, 42, 32)
    for g, c, m, l in ((0, BLUE, 'o', 'Bending'), (1, ORANGE, 's', 'Side bending'), (2, AQUA, '^', 'Twisting')):
        k = grp == g; ax.scatter(ms[k], pf[k], s=6, color=c, marker=m, lw=0, alpha=0.8, label=l, zorder=3)
    ax.axhline(0.3, color=INK, lw=0.7); ax.text(0.0006, 0.32, 'Assumed μ 0.3', fontsize=5.2, va='bottom'); ax.plot([5e-4, 1], [5e-4, 1], color=MUTED, lw=0.5)
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(5e-4, 1); ax.set_ylim(5e-3, 5)
    for a in (ax.xaxis, ax.yaxis): a.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}')); a.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel('μ$_{req}$, whole cage, both faces'); ax.set_ylabel('Friction needed, worst single face')
    ax.legend(loc='lower right', frameon=False, fontsize=5, handletextpad=0.1, borderpad=0, labelspacing=0.3)
    f.text(115, 11, wrap(f'{n03} of {len(rows)} load cases need more than 0.3 on one face, and {int((pf > 1).sum())} need more than 1. That includes every side-bending and twisting case: a glued face carries the twist that a real face would slip under.', 35), fontsize=5.3, linespacing=1.12)
    f.text(115, 30, wrap('Once a face slides, load shifts to the rest of the cage, so the real need probably lies between the two measures. Not yet tested.', 35), fontsize=5.3, color=INK2, linespacing=1.12)
    # c assumed mu
    y = 49
    f.label(2, y, 'c', 'Margin rests on an unmeasured friction')
    ax = f.ax(10, y + 8, 46, 31); mus = np.linspace(0, 0.8, 321); w6 = np.array(list(six.values()))
    pfd = collections.defaultdict(float)
    for r, v in zip(rows, pf): pfd[r['design']] = max(pfd[r['design']], v)
    w1 = np.array([pfd[p] for p in six if p in pfd])
    ax.add_patch(Rectangle((0.07, 0), 0.73, 1, transform=ax.get_xaxis_transform(), fc='#f4f3f0', ec='none', zorder=0)); ax.axvline(0.3, color=INK, lw=0.7)
    ax.plot(mus, [100 * (w6 <= m).mean() for m in mus], color=BLUE, lw=1.2, label='Whole cage (μ$_{req}$)'); ax.plot(mus, [100 * (w1 <= m).mean() for m in mus], color=ORANGE, lw=1.2, label='Every single face')
    ax.text(0.79, 8, f'Every single face: no design holds below μ {w1.min():.2f}', fontsize=5.1, ha='right', color=INK); ax.set_xlim(0, 0.8); ax.set_ylim(0, 103); ax.set_xlabel('Friction assumed available, μ'); ax.set_ylabel('Designs that hold (%)'); ax.legend(loc='center right', frameon=False, fontsize=5.2, borderpad=0, handlelength=1.2, bbox_to_anchor=(1.0, 0.42))
    ax.text(0.33, 78, 'Grey: range assumed in\nother simulation studies', fontsize=4.9, color=INK2, linespacing=1.05)
    at = lambda arr, m: 100 * (arr <= m).mean()
    # d screen vs friction run, with the PI evaluation point
    C = json.load(open(f'{M}/fric/compare.json')); T = []
    for r in C:
        if r['set'] != 'physio_fric3' or r.get('tied_mu_squeeze') is None or r['window'] not in ('flexion', 'extension'): continue
        if r['fric_reached']: u, p = r['fric_translation_mm'], r['fric_posterior_mm']
        elif r.get('rom_reached'): u, p = r['u_h_at_rom'], r['post_at_rom']
        else: continue
        T.append(dict(mu=r['tied_mu_squeeze'], frac=max(u, p / 0.5), w=r['window'], fm=r.get('fric_mu_from_tractions')))
    E = []
    for r in C:
        if r['set'] not in ('physio_fric', 'physio_fric2') or r.get('tied_mu_squeeze') is None or r['window'][:2] not in ('LB', 'AR'): continue
        if r['fric_reached']: u, p = r['fric_translation_mm'], r['fric_posterior_mm']
        elif r.get('rom_reached'): u, p = r['u_h_at_rom'], r['post_at_rom']
        else: continue
        E.append(dict(mu=r['tied_mu_squeeze'], frac=max(u, p / 0.5), w=r['window'], d=r['design']))
    f.label(62, y, 'd', 'Screen says safe; the friction run still moves')
    ax = f.ax(71, y + 8, 42, 31)
    for w, c, m, l in (('flexion', BLUE, 's', 'Bending forward'), ('extension', ORANGE, 'o', 'Bending backward')):
        s_ = [t for t in T if t['w'] == w]; ax.scatter([t['mu'] for t in s_], [t['frac'] for t in s_], s=6, color=c, marker=m, lw=0, label=l, zorder=3)
    ax.scatter([t['mu'] for t in E], [t['frac'] for t in E], s=8, color=AQUA, marker='^', lw=0, label=f'Side bending, twisting ({len({t["d"] for t in E})} early designs)', zorder=3)
    ax.axhline(1, color=INK, lw=0.7); ax.set_xlim(0, 0.18); ax.set_ylim(0, 1.5); ax.set_xlabel('\u03bc$_{req}$ of the glued model (all far below 0.3)'); ax.set_ylabel('Cage slip / allowed limit, friction run')
    ax.legend(loc='upper right', frameon=False, fontsize=4.8, borderpad=0, handletextpad=0.1, labelspacing=0.3)
    nover = sum(t['frac'] > 1 for t in T)
    sp = {w: stats.spearmanr([t['mu'] for t in T if t['w'] == w], [t['frac'] for t in T if t['w'] == w]) for w in ('flexion', 'extension')}
    # e drift
    f.label(121, y, 'e', 'That run is not a clean check: it drifts')
    ax = f.ax(130, y + 8, 46, 31); H = json.load(open(f'{EVO}/results/gpufe_verify/v2/v17a_hold.json'))['cases']; hold = {}
    for c in H:
        if c['window'] == 'extension' and c['set'] in ('pilot_holdA', 'pilot_holdE'): hold.setdefault(c['dir'][:4], {})[c['set']] = (c['n_hold'], c['drift_total_mm'])
    for (d, v), col, mk in zip(sorted(hold.items()), (BLUE, ORANGE), ('o', 's')):
        pts = sorted(v.values()); ax.plot([0] + [p[0] for p in pts], [0] + [p[1] for p in pts], color=col, lw=1.0, marker=mk, ms=3, label=d)
    ax.set_xlabel('Solver steps during the hold'); ax.set_ylabel('Cage drift at a fixed angle (mm)'); ax.set_xlim(0, 400); ax.set_ylim(0, 0.55); ax.legend(loc='upper left', frameon=False, fontsize=5.2, borderpad=0, handlelength=1.2)
    ax.text(0.97, 0.05, 'Same hold time.\nCorrect answer: 0', transform=ax.transAxes, ha='right', fontsize=5.3, color=INK, linespacing=1.1)
    # f table
    y = 94
    f.label(2, y, 'f', 'What the friction lower bound cannot yet tell us, and what would close each gap')
    tb = f.ax(2, y + 6, 176, 46); tb.set_xlim(0, 176); tb.set_ylim(9, 0); tb.axis('off')
    no_mu = n_all - len(per); incomplete = len(part)
    fm = {w: np.median([t['fm'] / t['mu'] for t in T if t['w'] == w and t['fm'] and t['mu'] > 0]) for w in ('flexion', 'extension')}
    data = [('Gap', 'What we know today', 'What would close it'),
            ('Glued contact', f'Median {100 * np.median(ten):.0f}% tension on a face; force scaling is an estimate (older rule 1.4–2.8× too low, F-0021)', 'Contact that can separate but not slide, then recompute μ'),
            ('One face vs whole cage', f'{n03} load cases need above 0.3 on one face; μ$_{{req}}$ does not flag them', 'Report both; decide whether one-face slip matters'),
            ('Friction value', 'No measurement of this plastic on wet bone; other studies assume 0.07–0.8', 'Bench friction test, wet, 50–150 N'),
            ('Friction coverage', f'Production runs: bending only ({len({r["design"] for r in C if r["set"] == "physio_fric3"})} designs). Side bending, twisting: {len({t["d"] for t in E})} early designs only', 'Six-motion friction runs after the fix'),
            ('No clean reference', f'Friction runs give {fm["flexion"]:.1f}× (forward) and {fm["extension"]:.1f}× (backward) the glued μ, but carry drift (e)', 'Fix FEBio stick point, rerun at fixed step counts'),
            ('Single moment', 'One state at 1.5 N·m; no repeated cycles, no build-up of slip, no time course over 16 weeks', 'Cycle tests after the fix; staged material changes'),
            ('Coverage', f'{no_mu} of {n_all} designs have no value (nearly all failed compression or stopped first); {incomplete} lack a motion', 'Fix insertion stops; report missing, never as pass'),
            ('Convergence', 'Mesh, step and stiffness tested on one family A design; changes up to 7.7% in relative terms', 'Repeat on a family B design and on threaded designs')]
    cx = (0, 34, 118)
    for i, row in enumerate(data):
        yy = i + 0.5
        for j, (x, t) in enumerate(zip(cx, row)):
            tb.text(x, yy, t, fontsize=5.4 if i == 0 else 5.1, va='center', color=INK if j != 1 else INK2, fontweight='bold' if (i == 0 or j == 0) else 'normal')
    tb.plot([0, 176], [1, 1], color=INK2, lw=0.4)
    note = ('Panel d uses the gate-4 evaluation point: 1.5 N·m when transmitted, otherwise the intact range of motion. Panel d, triangles: early runs (physio_fric, physio_fric2), usable windows only. Panel e: two designs, bending backward, hold from t 3.9; points are runs, lines are guides (DECISIONS 2026-11-06). Verdicts remain provisional. '
            'Abbreviations: F-0021, red-team finding; N·m, newton-metre; p062, p139, design numbers; μ, friction coefficient; μ$_{req}$, least friction coefficient that prevents the whole cage being squeezed out (glued model).')
    f.text(2, y + 54, wrap(note, 220), fontsize=4.9, color=INK2, linespacing=1.12)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))): fig.savefig(f'{OUT}/fig_mu_gaps.{ext}', facecolor='white', **kw)
    plt.close(fig)
    return dict(n_rows=len(rows), tension_median=float(np.median(ten)), above20=float((ten > 0.2).mean()), above_03=n03, above_035=n035, ratio_median=float(np.median(pf / ms)), hold_at={k: {m: (at(w6, m), at(w1, m)) for m in (0.07, 0.1, 0.2, 0.3, 0.45)} for k in ['whole,face']}, n_fric=len(T), n_early=len(E), early_frac_max=max(t['frac'] for t in E), early_mu=(min(t['mu'] for t in E), max(t['mu'] for t in E)), n_over=int(nover), w1=(float(w1.min()), float(np.median(w1)), float(w1.max())), pf_over1=int((pf > 1).sum()), ext_tension=float(np.median(ten[is_ext])), other_tension=float(np.median(ten[~is_ext])), n_over_by_window={w: int(sum(t['frac'] > 1 for t in T if t['w'] == w)) for w in ('flexion', 'extension')}, n_by_window={w: sum(t['w'] == w for t in T) for w in ('flexion', 'extension')}, spearman={w: (float(sp[w][0]), float(sp[w][1])) for w in sp}, tension_quartiles=[float(np.percentile(ten, q)) for q in (25, 50, 75)], faces_above_mu_force=int((np.array([max(r['top_mu_force'], r['bot_mu_force']) for r in rows]) > 0.3).sum()), pf_max=float(pf.max()), pf_median=float(np.median(pf)), by_group={g: dict(n=int((grp == i).sum()), over03=int((pf[grp == i] > 0.3).sum()), median=float(np.median(pf[grp == i])) if (grp == i).any() else None) for i, g in enumerate(('bending', 'side', 'twist'))}, fric_mu_ratio=fm, no_mu=no_mu, incomplete=incomplete, hold=hold)


def main():
    setup(); B, R, per, six, part = load(); rob = robustness()
    poster(B, R, per, six, part, rob)
    import sys
    if 'poster' in sys.argv: print(rob, len(R), len(per), len(six), len(part)); return
    S = json.load(open(f'{OUT}/mu_face_scan.json')); print('scan rows', len(S['rows']), 'errors', len(S['errors']), list(S['errors'].items())[:3])
    g = gaps(B, R, per, six, part, rob, S['rows'])
    w = np.array(list(six.values())); a = np.array([r['mu'] for r in R])
    out = dict(generated=datetime.datetime.now().isoformat(timespec='minutes'), n_windows=len(R), n_designs=len(per), n_six=len(six), worst_median=float(np.median(w)), worst_max=float(w.max()), all_max=float(a.max()), robustness=rob, gaps=g)
    json.dump(out, open(f'{OUT}/figure_numbers.json', 'w'), indent=1, default=str); print(json.dumps(out, default=str)[:1800])


if __name__ == '__main__':
    main()
