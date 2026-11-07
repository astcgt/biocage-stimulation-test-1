#!/usr/bin/env python3
"""h40: plain-language Nature-style figure: how close the in-house GPU solver (gpufe) is to FEBio, and which capability labels are still open.

Reads result files only. Evidence on the current Newton solver: gate 1 report (verifier re-ran it on 1f09ae2, element code unchanged since), h39 outputs,
gate 2 runs (human_study/figures/febio_agreement/gate2_rerun_20261105 and gate2_fine here). Limits are the ones already written in the gate plan and the capability register.
usage: python h40_gpu_solver_fig.py    outputs in human_study/figures/gpu_solver_agreement/
"""
import os, re, csv, json, datetime, textwrap, importlib.util
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.transforms import blended_transform_factory

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = os.path.join(ROOT, 'human_study'); EVO = os.path.join(os.path.dirname(ROOT), 'biocage-evo')
OUT = os.path.join(HS, 'figures/gpu_solver_agreement'); NR = os.path.join(OUT, 'newton_reverify'); FINE = os.path.join(OUT, 'gate2_fine')
RERUN = os.path.join(HS, 'figures/febio_agreement/gate2_rerun_20261105'); OLDLOG = os.path.join(EVO, 'work/agents'); VER = os.path.join(EVO, 'results/gpufe_verify')
DIRS = ['flex_pos_y', 'flex_neg_y', 'lb_pos_x', 'lb_neg_x', 'ar_pos_z', 'ar_neg_z']
NAME = dict(flex_pos_y='Bending forward', flex_neg_y='Bending backward', lb_pos_x='Side bending, one way', lb_neg_x='Side bending, other way', ar_pos_z='Twisting, one way', ar_neg_z='Twisting, other way')
AX = dict(x=0, y=1, z=2)
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#8a8982', '#e4e3df'
GPU, ZONE = '#eb6834', '#e3f1e3'
GOOD, CRIT, WARN = '#0ca30c', '#d03b3b', '#8a8982'
MM = 1 / 25.4; W, H = 180, 202


def jl(p, d=None): return json.load(open(p)) if os.path.exists(p) else d


def read_rigid(p):
    out, t = [], None
    for l in open(p):
        if l.startswith('*Time'): t = float(l.split('=')[1])
        elif l[:1].isdigit() and t is not None: out.append((t, [float(v) for v in l.split(',')[1:]]))
    return out


def parse(p, ax):
    if not os.path.exists(p): return None
    s = open(p, errors='ignore').read()
    st = re.findall(r'\[step\] t=([\d.]+) .*?th \[([^\]]+)\]', s)
    if not st: return None
    t = np.array([float(a) for a, _ in st]); th = np.array([float(b.split(',')[ax]) for _, b in st])
    rep = re.findall(r'\{"direction".*\}', s)
    return dict(t=t, th=th, diverged=bool(re.search(r'RuntimeError: Newton not converged', s)), rep=json.loads(rep[-1]) if rep else None)


def gate2():
    """Per direction: FEBio curve, runs on current code, furthest moment reached, agreement before the stop (gate 2 rule: |dev| / |FEBio end value|)."""
    G = {}
    for d in DIRS:
        ax = AX[d[-1]]; R = read_rigid(f'{EVO}/snapshot/reference/fsu_intact/{d}/C3pot_rigid.txt')
        rt = np.array([r[0] for r in R]); rth = np.array([r[1][3 + ax] for r in R])
        runs = {k: parse(p, ax) for k, p in (('fine', f'{FINE}/{d}.log'), ('today', f'{RERUN}/{d}.log'), ('oct28', f'{OLDLOG}/gate2_{d}.log'))}
        runs = {k: v for k, v in runs.items() if v}
        reach = max(100 * min(1, v['t'][-1] - 1) for v in runs.values())
        best = runs.get('fine') or runs['today']
        k = (rt >= 1.0) & (rt <= best['t'][-1] + 1e-9)
        dev = np.abs(np.interp(rt[k], best['t'], best['th']) - rth[k]) / abs(rth[-1])
        G[d] = dict(rt=rt, rth=rth, runs=runs, reach=reach, best=best, dev=dev, dev_t=rt[k], finished=any(v['rep'] for v in runs.values()), end_err=next((v['rep']['end_rel_err'] for v in runs.values() if v['rep']), None))
    return G


def facets():
    fv = jl(f'{EVO}/snapshot/reference/fsu_intact/fsu_refined_vs_full.json'); fac = {}
    for sect in fv.values():
        for k, v in sect.items():
            m = re.match(r'facet_(\w+)_fsu_N', k)
            if m: fac[m.group(1)] = v['L'] + v['R']
    return fac


def equiv(e, delta):
    e = np.abs(np.asarray(e, float)); n = len(e)
    if n < 2: return None
    m, s = e.mean(), e.std(ddof=1)
    return float(stats.t.sf((delta - m) / (s / np.sqrt(n)), n - 1)) if s > 0 else (0.0 if m < delta else 1.0)


def rows():
    """(group, label, abs. relative differences, limit, kind of reference, status override, note)"""
    g1 = {c['case']: c for c in jl(f'{VER}/gate1/gate1_report.json')['cases']}
    w = lambda c: g1[c]['worst_rel_err']
    R = [('A', 'Spongy bone, cartilage, disc core (rubber-like)', [w('neo_hex'), w('neo_tet')], 0.01, 'FEBio'),
         ('A', 'Hard outer bone (stiffer along the grain)', [w('ortho_tet')], 0.01, 'FEBio'),
         ('A', 'Disc ring (soft matrix + two fibre families)', [w('hm_fiber_hex')], 0.01, 'FEBio'),
         ('A', 'Soft cage polymer, pre-expanded', [w('gent_prestrain_hex')], 0.01, 'FEBio'),
         ('A', 'Ligaments (non-linear springs)', [w('spring_smooth')], 0.01, 'FEBio')]
    bs = jl(f'{NR}/bend_strict.json', []); bd = jl(f'{NR}/bend.json', [])
    lab = dict(neo_hex_bend='Soft rubber-like bar', gent_prestrain_hex_bend='Cage polymer bar, pre-expanded', ortho_tet_bend='Hard bone bar')
    for c in bs:
        R.append(('B', lab[c['case']], [max(v['R_rel_err'] for v in c['per_time'].values())], 1e-3, 'FEBio'))
    if bd:
        R.append(('B', 'Same bars, solver’s default stopping rule (0.05 N)', [max(v['R_rel_err'] for v in c['per_time'].values()) for c in bd], 1e-3, 'FEBio'))
    sl = {c['mu']: c for c in jl(f'{NR}/slide.json', [])}; R_sl = {}
    st = jl(f'{NR}/stick.json', [])
    if st and all('cycle_end_Fx_over_Fz' in r for r in st):
        R.append(('C', 'Sticking: no force left over after repeated shear', [max(r['cycle_end_Fx_over_Fz']) for r in st], 1e-3, 'physics law'))
    for mu in (0.2, 0.35, 0.5):
        c = sl.get(mu)
        if c is None: continue
        lb = f'Sliding: friction force / pressing force at μ {mu}'
        if 'ratio_err_max' in c: R.append(('C', lb, [c['ratio_err_max']], 0.02, 'physics law'))
        else: R.append(('C', lb, [], 0.02, 'physics law', 'Stopped early'))
    for mu, c in sl.items():
        fr = [r for r in c['rows'] if r.get('febio_F')]
        pr = [r for r in fr if abs(r['t'] - 0.5) < 1e-6]; sd = [r for r in fr if r['t'] >= 0.85]
        if pr and sd and 'ratio_err_max' in c:
            R.append(('C', f'Pressing force before sliding, \u03bc {mu}', [abs(pr[0]['F'][2] / pr[0]['febio_F'][2] - 1)], None, 'FEBio'))
            R.append(('C', f'Pressing force while sliding, \u03bc {mu}', [abs(np.mean([r['F'][2] for r in sd]) / np.mean([r['febio_F'][2] for r in sd]) - 1)], None, 'FEBio'))
    G = gate2(); f = G['flex_pos_y']
    R.append(('D', 'Bending forward: final rotation', [f['end_err']], 0.05, 'FEBio'))
    R.append(('D', 'Bending forward: whole load–rotation curve', [f['dev'].max()], 0.05, 'FEBio'))
    pre = [G[d]['dev'].max() for d in DIRS[1:] if len(G[d]['dev'])]
    R.append(('D', 'Other motions, up to where the solver stops (4 of 5 reach a check point)', pre, 0.05, 'FEBio', None if pre else 'No data'))
    return R, G


def setup():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'font.size': 6, 'axes.linewidth': 0.5, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
                         'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.major.size': 2, 'ytick.major.size': 2, 'axes.labelsize': 6, 'xtick.labelsize': 5.5, 'ytick.labelsize': 5.5,
                         'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'mathtext.default': 'regular', 'axes.labelpad': 1.5, 'xtick.major.pad': 1.5, 'ytick.major.pad': 1.5})


def ax_mm(fig, x, y, w, h, **k): return fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H], **k)


def plabel(fig, x, y, letter, title):
    fig.text(x / W, 1 - y / H, letter, fontsize=8, fontweight='bold', va='top', color=INK)
    fig.text((x + 3.6) / W, 1 - (y + 0.45) / H, title, fontsize=6.3, va='top', color=INK, fontweight='bold')


def box(ax, x, y, w, h, text, fc='white', ec=INK2, fs=5.4, fw='normal'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.8', fc=fc, ec=ec, lw=0.6))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, color=INK, fontweight=fw, linespacing=1.15)


def arrow(ax, a, b): ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=5, lw=0.6, color=INK2, shrinkA=0, shrinkB=0))


def pct(x):
    if x is None: return '—'
    x = x * 100
    if x >= 0.0095: return f'{x:.2g}%'
    e = int(np.floor(np.log10(x))); return f'{x / 10 ** e:.1f}×10$^{{{e}}}$%'


def wrap(t, n):
    vis = lambda w: len(re.sub(r'[$]|\\mu|_\{|\}', '', w)); L, c = [], ''
    for w in t.split(' '):
        if c and vis(c) + 1 + vis(w) > n: L.append(c); c = w
        else: c = (c + ' ' + w) if c else w
    return '\n'.join(L + [c])


def capability_rows(G, hold):
    stops = [G[d]['reach'] for d in DIRS[1:]]
    cr = [h['creep_mm'] for h in hold if h['ratio'] == 0.9 and 'creep_mm' in h]; cl = [h['creep_mm'] for h in hold if h['ratio'] == 0.5 and 'creep_mm' in h]
    fsl = jl(f'{NR}/slide.json', [])
    nf = sum('ratio_err_max' not in c for c in fsl)
    press = max(abs(np.mean([r['F'][2] for r in c['rows'] if r['t'] >= 0.85 and r.get('febio_F')]) / np.mean([r['febio_F'][2] for r in c['rows'] if r['t'] >= 0.85 and r.get('febio_F')]) - 1) for c in fsl if 'ratio_err_max' in c and any(r.get('febio_F') for r in c['rows']))
    press = max((abs(np.mean([r['F'][2] for r in c['rows'] if r['t'] >= 0.85 and r.get('febio_F')]) / np.mean([r['febio_F'][2] for r in c['rows'] if r['t'] >= 0.85 and r.get('febio_F')]) - 1) for c in fsl if 'ratio_err_max' in c and any(r.get('febio_F') for r in c['rows'])), default=None)
    strict = jl(f'{NR}/slide_strict.json', [])
    C = [('Numerical', 'Whole segment, six motions (gate 2, NUM-12)', 'within 5% of FEBio', f'1 of 6 finishes; the other 5 stop at {min(stops):.0f}–{max(stops):.0f}% of the load', 'out'),
         ('Numerical', 'Facet joint contact force (gate 2, NUM-12)', 'compare with FEBio', 'no finished run in which the facet joints touch', 'unk'),
         ('Numerical', 'Cage glued to bone (gate 3, NUM-12)', 'within 10% of FEBio', 'never run', 'unk'),
         ('Numerical', 'Cage with real friction, slip-out (gate 4, NUM-12)', 'compare with FEBio', 'never run; FEBio itself differs by up to 33% between runs of one input (NUM-17)', 'unk'),
         ('Numerical', 'Block under constant sideways force (NUM-13)', 'drift ≤ 0.01 mm', f'{min(cl):.3f}–{max(cl):.3f} mm at half the friction limit, {min(cr):.2f}–{max(cr):.2f} mm at 90% (FEBio 0.08–0.60 mm)', 'out'),
         ('Numerical', 'Sliding block at every friction coefficient (gate 1c)', 'finishes, within 2%', f'{nf} of {len(fsl)} stops while pressing; under the strict stopping rule all {len(strict)} stop by early sliding', 'out'),
         ('Numerical', 'Bars and sliding under one stopping rule', 'both inside limit', 'not achieved: bars need the strict rule, sliding finishes only at the default rule', 'out'),
         ('Numerical', 'Pressing force in contact vs FEBio (gate 1c)', 'none set', f'{pct(press)} apart while sliding at μ 0.5', 'unk'),
         ('Observation', 'All failure modes have a metric (OBS-01)', 'one metric per mode', 'hard-phase stress metric and two others are missing', 'inc'),
         ('Diversity', 'Free-form designs can be built (DIV-01)', 'each design class', 'never checked on this solver', 'unk'),
         ('Diversity', 'Cage material detail kept (DIV-02)', '100% match', 'never checked on this solver', 'unk'),
         ('Physics', 'Realism against cadaver data', 'no check defined', 'not assessed for this solver; needs the gates above first', 'unk'),
         ('Speed', 'Time per design', 'no check defined', 'not assessed for this solver', 'unk')]
    return C


def figure():
    setup(); R, G = rows(); fac = facets(); hold = jl(f'{NR}/hold.json', [])
    fig = plt.figure(figsize=(W * MM, H * MM), facecolor='white')
    # a: how the comparison works
    plabel(fig, 2, 2, 'a', 'The test: same problem, two solvers')
    ax = ax_mm(fig, 2, 8, 58, 33); ax.set_xlim(0, 58); ax.set_ylim(0, 33); ax.axis('off')
    box(ax, 0, 12, 11, 9, 'Same\ninput file', fc='#f4f3f0')
    box(ax, 17, 21, 16, 10, 'FEBio\ntrusted reference', fc='#f4f3f0', ec=INK, fw='bold')
    box(ax, 17, 2, 16, 10, 'In-house\nGPU solver\n(gpufe)', fc='#fde8df', ec=GPU, fw='bold')
    box(ax, 38, 10.5, 20, 12, 'Difference =\n|gpufe − FEBio| / |FEBio|', fs=5)
    arrow(ax, (11, 18), (17, 26)); arrow(ax, (11, 15), (17, 7)); arrow(ax, (33, 26), (38, 19)); arrow(ax, (33, 7), (38, 14))
    ax.text(48.5, 7.6, 'Passes if inside a limit\nset before the test', ha='center', va='top', fontsize=5.1, color=INK2, linespacing=1.15)
    # b: flexion overlay
    plabel(fig, 66, 2, 'b', 'Where gpufe works: bending forward')
    ax = ax_mm(fig, 73, 9, 42, 28); f = G['flex_pos_y']; m = f['rt'] >= 1 - 1e-9
    ax.plot(np.r_[0, 1.5 * (f['rt'][m] - 1)], np.r_[abs(np.degrees(np.interp(1.0, f['rt'], f['rth']))), np.abs(np.degrees(f['rth'][m]))], color=INK, lw=1.0, zorder=2, label='FEBio')
    r = f['runs'].get('today'); k = r['t'] >= 1 - 1e-9
    ax.plot(1.5 * (r['t'][k] - 1), np.abs(np.degrees(r['th'][k])), ls='', marker='o', ms=3, color=GPU, mec='white', mew=0.3, zorder=3, label='In-house GPU solver (gpufe)')
    ax.set_xlim(0, 1.55); ax.set_ylim(0, 6.3); ax.set_xticks([0, 0.5, 1, 1.5]); ax.set_xlabel('Applied moment (N·m)'); ax.set_ylabel('Rotation of C3 vertebra (°)')
    ax.legend(loc='upper left', frameon=False, fontsize=5.2, handlelength=1.4, borderpad=0, labelspacing=0.3)
    ax.text(1.5, 0.5, f"Final difference {pct(f['end_err'])}\nDots sit on the line", ha='right', fontsize=5.2, color=INK2, linespacing=1.15)
    # c: reach
    plabel(fig, 122, 2, 'c', 'Where gpufe stops: when facet joints touch')
    ax = ax_mm(fig, 144, 9, 34, 28); y = np.arange(6)[::-1]; vals = [G[d]['reach'] for d in DIRS]
    ax.barh(y, vals, color=GPU, height=0.62, zorder=2)
    ax.axvline(100, color=INK, lw=0.7, zorder=3); ax.text(100, 5.62, 'FEBio finishes', ha='right', fontsize=5, color=INK, va='bottom')
    ax.set_yticks(y); ax.set_yticklabels([NAME[d] for d in DIRS], fontsize=5.3); ax.set_xlim(0, 104); ax.set_xticks([0, 50, 100]); ax.set_ylim(-0.6, 6.2)
    ax.set_xlabel('Load reached (% of 1.5 N·m)'); ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
    for yy, d, v in zip(y, DIRS, vals):
        ax.text(v + 2 if v < 70 else v - 2, yy, f"{v:.0f}%, FEBio facet force {fac[d]:.0f} N" if v < 70 else f'{v:.0f}%, no facet contact', va='center', ha='left' if v < 70 else 'right', fontsize=4.8, color=INK if v < 70 else 'white')
    # d: scorecard
    y0 = 44.5
    tested = [r for r in R if len(r) < 6 or r[5] is None]
    inside = sum(1 for r in R if r[3] and len(r[2]) and max(r[2]) < r[3]); total = len(R)
    plabel(fig, 2, y0, 'd', f'Physical processes checked on the current solver: {inside} of {total} inside their limit')
    grp = {'A': 'Materials: one small block, each tissue model', 'B': 'Whole-body deformation: bar clamped at one end, other end lifted (strict stopping rule unless stated)', 'C': 'Contact: one block pressed on another (default stopping rule; friction is checked against the physics law, because FEBio forgets stick between steps)', 'D': 'Whole C3–C4 spinal segment with all tissues'}
    n_groups = len({r[0] for r in R}); nr = len(R) + n_groups; rh = 3.55
    fx, fw = 72, 62
    ax = ax_mm(fig, fx, y0 + 8, fw, nr * rh)
    ax.set_xscale('log'); ax.set_xlim(1e-13, 0.3); ax.set_ylim(nr, 0); ax.spines['left'].set_visible(False); ax.set_yticks([])
    ax.set_xticks([1e-12, 1e-9, 1e-6, 1e-3, 1e-1 / 10, 1e-1]); ax.set_xticklabels(['0.0000000001%', '0.0000001%', '0.0001%', '0.1%', '1%', '10%'], fontsize=4.9, rotation=0)
    ax.set_xticks([1e-12, 1e-9, 1e-6, 1e-3, 1e-1]); ax.set_xticklabels(['10$^{-10}$%', '10$^{-7}$%', '10$^{-4}$%', '0.1%', '10%'], fontsize=5.3); ax.minorticks_off()
    ax.set_xlabel('Difference from reference (log scale: each gridline is 1,000 times closer than the next one to its right)', fontsize=5.2)
    for x in [1e-12, 1e-9, 1e-6, 1e-3, 1e-1]: ax.axvline(x, color=GRID, lw=0.4, zorder=0)
    tr = blended_transform_factory(fig.transFigure, ax.transData)
    colx = dict(ref=137, lim=146.5, val=155.5, st=163)
    ty = 1 - (y0 + 7.6) / H
    for k, s, ha in [('ref', 'Compared\nwith', 'center'), ('lim', 'Limit', 'center'), ('val', 'Largest\ndifference', 'center'), ('st', 'Result', 'left')]:
        fig.text(colx[k] / W, ty, s, fontsize=5.3, fontweight='bold', va='bottom', ha=ha, color=INK, linespacing=1.0)
    yy = 0.0; cur = None
    for r in R:
        if r[0] != cur:
            cur = r[0]
            ax.text(2 / W, yy + 0.75, grp[cur], transform=tr, fontsize=5.5, fontweight='bold', color=INK, va='baseline', clip_on=False)
            ax.plot([2 / W, 178 / W], [yy + 1.0, yy + 1.0], transform=tr, color=INK2, lw=0.35, clip_on=False, zorder=1)
            ax.add_patch(Rectangle((1e-13, yy + 1.0), 0, 0)); yy += 1
        c = yy + 0.5; e = np.array(r[2], float); lim = r[3]
        if lim:
            ax.add_patch(Rectangle((1e-13, c - 0.34), lim - 1e-13, 0.68, fc=ZONE, ec='none', zorder=1))
            ax.plot([lim, lim], [c - 0.42, c + 0.42], color=INK, lw=0.9, zorder=3, solid_capstyle='butt')
        ax.text(2.5 / W, c, r[1], transform=tr, fontsize=5.4, va='center', color=INK)
        ax.text(colx['ref'] / W, c, r[4], transform=tr, fontsize=5.0, va='center', ha='center', color=INK2)
        ax.text(colx['lim'] / W, c, pct(lim) if lim else 'none set', transform=tr, fontsize=5.2, va='center', ha='center', color=INK)
        if len(e):
            ok = lim and e.max() < lim
            ax.scatter(np.clip(e, 1.5e-13, None), [c] * len(e), s=9, color=GPU, edgecolor='white', lw=0.3, zorder=4)
            ax.text(colx['val'] / W, c, pct(e.max()), transform=tr, fontsize=5.2, va='center', ha='center', color=INK)
            ic, col, tx = ('✓', GOOD, 'Inside limit') if ok else (('✗', CRIT, 'Outside limit') if lim else ('?', WARN, 'No limit set'))
        else:
            ax.text(colx['val'] / W, c, '—', transform=tr, fontsize=5.2, va='center', ha='center', color=INK)
            ic, col, tx = ('✗', CRIT, r[5] if len(r) > 5 and r[5] else 'No result')
        ax.text(colx['st'] / W, c, ic, transform=tr, fontsize=6, va='center', color=col, fontweight='bold', family='DejaVu Sans')
        ax.text((colx['st'] + 2.6) / W, c, tx, transform=tr, fontsize=5.1, va='center', color=INK)
        yy += 1
    # e: open capability labels
    ye = y0 + 8 + nr * rh + 8.2
    C = capability_rows(G, hold)
    plabel(fig, 2, ye, 'e', 'Capability labels of the in-house GPU solver (gpufe) not yet inside a limit, or not possible to judge')
    ax = ax_mm(fig, 2, ye + 5, 176, 3.15 * (len(C) + 1)); ax.set_xlim(0, 176); ax.set_ylim(len(C) + 1, 0); ax.axis('off')
    cx = [0, 15, 69, 90, 164]
    for x, s in zip(cx, ['Label', 'What is checked', 'Limit', 'Status today', '']):
        ax.text(x, 0.55, s, fontsize=5.4, fontweight='bold', va='center', color=INK)
    ax.plot([0, 176], [1, 1], color=INK2, lw=0.35)
    for i, (lab, what, lim, now, st) in enumerate(C):
        c = i + 1.5
        ax.text(cx[0], c, lab, fontsize=5.2, va='center', color=INK, fontweight='bold')
        ax.text(cx[1], c, what, fontsize=5.2, va='center', color=INK)
        ax.text(cx[2], c, lim, fontsize=5.0, va='center', color=INK2)
        ax.text(cx[3], c, wrap(now, 90), fontsize=4.9, va='center', color=INK, linespacing=0.95)
        ic, col, tx = {'out': ('✗', CRIT, 'Outside limit'), 'inc': ('✗', CRIT, 'Incomplete'), 'unk': ('?', WARN, 'Cannot judge')}[st]
        ax.text(162.5, c, ic, fontsize=6, va='center', color=col, fontweight='bold', family='DejaVu Sans')
        ax.text(165.2, c, tx, fontsize=5.1, va='center', color=INK)
    yk = ye + 5 + 3.15 * (len(C) + 1) + 1.2
    abbr = ('C3, C4, third and fourth neck vertebrae; cage, the implant placed between them; facet joints, small paired joints at the back of each vertebra; FEBio, Finite Elements for Biomechanics, an established open-source solver; '
            'gate 1–4, planned verification stages of gpufe; GPU, graphics processing unit; gpufe, the in-house GPU finite-element solver (not the GPU linear solver cuDSS inside FEBio); moment, turning force; N, newton; N·m, newton-metre; NUM-, OBS-, DIV-, check numbers in the capability register; '
            'solver, program that computes the physics; stopping rule, how small the leftover force must be before the solver accepts a step (default 0.05 N, strict 0.0000001 N); μ, friction coefficient. Green bar, allowed range; black tick, limit; orange dot, one case. Limits were written in the gate plan and register before this figure. Equivalence test (mean difference below the limit, one-sided t test): materials n = 5 and bars n = 3, both p < 0.001.')
    fig.text(2 / W, 1 - yk / H, 'Abbreviations and key', fontsize=5.3, fontweight='bold', va='top', color=INK)
    fig.text(2 / W, 1 - (yk + 2.2) / H, wrap(abbr, 215), fontsize=5, va='top', color=INK2, linespacing=1.15)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig_gpu_solver_vs_febio.{ext}', facecolor='white', **kw)
    plt.close(fig)
    return R, G, C, yk


def write_legend(R, G, gt):
    local = {d: [round(100 * abs(np.interp(t, G[d]['best']['t'], G[d]['best']['th']) - np.interp(t, G[d]['rt'], G[d]['rth'])) / abs(np.interp(t, G[d]['rt'], G[d]['rth'])), 1) for t in G[d]['dev_t']] for d in DIRS[1:]}
    qa = open(f'{HS}/qa/QA_STATUS.md', errors='ignore').readline().strip().lstrip('# ')
    hold = jl(f'{NR}/hold.json'); strict = jl(f'{NR}/slide_strict.json')
    stops = [(c['mu'], re.search(r't=([\d.]+)', c.get('error', '')).group(1)) for c in strict if c.get('error')]
    L = f"""# Figure legend (generated by scripts/8_audit/h40_gpu_solver_fig.py, {datetime.datetime.now().isoformat(timespec='minutes')})

**Fig. | The in-house GPU solver (gpufe) reproduces FEBio for tissue materials and contact-free deformation, but not yet for motions in which joints touch or for any cage model.**

**a**, Both solvers receive the same input file. **b**, C3 rotation under an applied moment, bending forward, the one motion that finishes. FEBio facet force is 0 N here, so this run does not exercise joint contact. **c**, Furthest load reached on the current code, from the runs of 28 Oct and 5 Nov 2026 (coarse and fine load steps). Some of the 5 Nov runs ended at a time limit rather than by divergence. **d**, Difference from the reference for each process; each dot is one case, and the column shows the largest. **e**, Open items for the GPU solver column of the capability register, plus findings from this analysis.

## Evidence and solver version
- Materials: gate 1 report (10-26); the verifier re-ran it on commit 1f09ae2, and the element code is unchanged since.
- Bars, sticking, sliding, hold: re-run on the current Newton solver by scripts/8_audit/h39_gpufe_newton_reverify.py, because gates 1b and 1c had used the older dynamic-relaxation solver (findings F-0014, F-0026). FEBio was not re-run; its values are those stored in the gate reports. Bar difference = resultant reaction force; displacement was compared with the older solver only.
- Sliding: at the default stopping rule mu 0.2 stops at t = 0.04, mu 0.35 and 0.5 finish. At the strict rule the stop times are (mu, t) {stops}. Sliding results therefore hold only at the default rule, and the bar results only at the strict rule.
- Whole segment: the difference follows the gate 2 rule, |deviation| / |FEBio final rotation|. Relative to the local FEBio rotation at each comparison time the differences are (%): {local}; so the row is inside 5 % under the gate 2 rule, which is the more lenient reading at small rotations.
- Hold test (friction-limit fraction, increments, creep mm): {[(h['ratio'], h['n'], round(h['creep_mm'], 4)) for h in hold]}. FEBio values from verifier run V07.

## Statistics
One-sided t test of mean difference >= limit: materials n = {gt['A']['n']}, p = {gt['A']['p_equiv']:.1e}; bars n = {gt['B']['n']}, p = {gt['B']['p_equiv']:.1e}. Errors span many orders of magnitude, so the t test is only indicative; the plain check that every case is inside its limit is the main evidence. An exact rank test cannot reach p < 0.05 with n = 3. Other groups have too few comparable cases for a test.

## Limits
These benchmarks do not show that gpufe can replace FEBio for cage design. Restriction R04 still bars it from design ranking until gates 2-4 pass.
QA at generation: {qa}. The qa-auditor agent has not reviewed this figure. Font: Lato with DejaVu Sans fallback (Helvetica or Arial are not installed).
"""
    open(f'{OUT}/figure_legend.md', 'w', encoding='utf-8').write(L)


def main():
    R, G, C, yk = figure()
    with open(f'{OUT}/process_table.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['group', 'process', 'reference', 'limit', 'n', 'max_abs_difference', 'cases', 'inside_limit'])
        for r in R: w.writerow([r[0], r[1], r[4], r[3], len(r[2]), max(r[2]) if len(r[2]) else '', ';'.join(f'{x:.4g}' for x in r[2]), bool(r[3] and len(r[2]) and max(r[2]) < r[3])])
    for r in R: print(r[0], r[1][:58].ljust(58), r[4][:6], r[3], pct(max(r[2])) if len(r[2]) else (r[5] if len(r) > 5 else None), 'n', len(r[2]))
    print({d: (round(G[d]['reach'], 1), None if not len(G[d]['dev']) else round(float(G[d]['dev'].max()), 4), list(G[d]['runs'])) for d in DIRS}, 'yk', yk, 'of', H)
    # group-level tests
    gt = {}
    for g in 'AB':
        e = [max(r[2]) for r in R if r[0] == g and 'default' not in r[1]]; lim = {'A': 0.01, 'B': 1e-3}[g]
        gt[g] = dict(n=len(e), limit=lim, max=max(e) if e else None, p_equiv=equiv(e, lim) if e else None)
    write_legend(R, G, gt)
    json.dump(dict(generated=datetime.datetime.now().isoformat(timespec='seconds'), group_tests=gt), open(f'{OUT}/group_tests.json', 'w'), indent=1); print(gt)


if __name__ == '__main__':
    main()
