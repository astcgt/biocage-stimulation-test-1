#!/usr/bin/env python3
"""h38: Nature-style figure + equivalence tests: how far the platform agrees with FEBio, read only from result files.

What is compared (nothing here runs a solver):
  A. Production platform = FEBio 4.13 + patches. (1) rebuild vs baseline build: verify_patch_20261105/compare.json (NUM-10);
     (2) GPU cuDSS vs CPU Pardiso on windows whose case.feb and restart.feb are byte-identical (found by the hash scan below; NUM-11);
     (3) the same scan for real-friction windows (physio_fric3), including GPU vs GPU repeats.
  B. In-house GPU solver gpufe vs FEBio: reports in ../biocage-evo/results/gpufe_verify (gates 1, 1b, 1c) + gate 2 logs
     (history in ../biocage-evo/work/agents, today's rerun in gate2_rerun_20261105/). Gates 3-4 have no data.
Test: e = relative difference per case (window / direction / material); H0 mean|e| >= margin vs H1 mean|e| < margin, one-sided t test,
Holm-adjusted over the rows tested. |e| >= 0 makes the lower half of TOST vacuous, so this is TOST with the stricter |e|.
A row is called equivalent only if the adjusted p < 0.05 AND every case is inside the margin. Margins come from existing documents only.
usage: python h38_febio_agreement_fig.py [--rescan]     outputs in human_study/figures/febio_agreement/
"""
import os, re, sys, csv, glob, json, hashlib, collections, itertools, datetime
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = os.path.join(ROOT, 'human_study')
EVO = os.path.join(os.path.dirname(ROOT), 'biocage-evo')
OUT = os.path.join(HS, 'figures/febio_agreement')
AL = os.path.join(HS, 'al_v2')
SPLIT = os.path.join(EVO, 'results/method/split')
SCAN = os.path.join(OUT, 'same_input_scan.json')
RERUN = os.path.join(OUT, 'gate2_rerun_20261105')
DIRS = ['flex_pos_y', 'flex_neg_y', 'lb_pos_x', 'lb_neg_x', 'ar_pos_z', 'ar_neg_z']
DIRNAME = dict(flex_pos_y='Flexion', flex_neg_y='Extension', lb_pos_x='Lateral bending +x', lb_neg_x='Lateral bending −x',
               ar_pos_z='Axial rotation +z', ar_neg_z='Axial rotation −z')
AXIS = dict(x=0, y=1, z=2)

# margins (existing documents only)
D_NUM10 = 1e-4      # platform_capabilities.json NUM-10 threshold (integrator 2026-10-21)
D_NUM11 = 1e-4      # NUM-11 threshold
D_PI_DT = 0.02      # PI 2026-11-03: time-step tolerance on mu_req (the PI's strictest numerical tolerance)
D_PI_NUM = 0.05     # PI 2026-11-03: mesh / penalty tolerance (the PI's loosest numerical tolerance)
D_GATE1 = 0.01      # docs/METHODS_COMPARISON.md gate 1
D_GATE1C = 0.02     # gpufe/gate1c_friction.py passes at err < 0.02
D_GATE2 = 0.05      # docs/METHODS_COMPARISON.md gate 2
D_GATE3 = 0.10      # docs/METHODS_COMPARISON.md gate 3


# ---------------------------------------------------------------- same-input scan
def _sha(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()


def _solver(w):
    for line in open(w + '/case.log', errors='ignore'):
        m = re.search(r'Selecting linear solver (\w+)', line)
        if m: return m.group(1)


def rescan():
    rows, ch = [], {}
    for s in ['physio_rot_split2', 'physio_rot_split3', 'physio_rot_split4', 'physio_fric', 'physio_fric2', 'physio_fric3']:
        for rd in sorted(glob.glob(f'{AL}/{s}/p*/')):
            rd = rd.rstrip('/')
            if not os.path.exists(rd + '/case.log'): continue
            for w in sorted(glob.glob(rd + '/w_*')):
                if not (os.path.exists(w + '/case.log') and os.path.exists(w + '/restart.feb')): continue
                ch.setdefault(rd, _sha(rd + '/case.feb'))
                ended = 'N O R M A L   T E R M I N A T I O N' in open(w + '/case.log', errors='ignore').read()[-6000:]
                rows.append(dict(set=s, dir=os.path.basename(rd), win=os.path.basename(w)[2:], solver=_solver(w), parent_solver=_solver(rd),
                                 ended=ended, case=ch[rd], restart=_sha(w + '/restart.feb')))
    json.dump(rows, open(SCAN, 'w'))
    return rows


# ---------------------------------------------------------------- tied cage metrics
def tied_metrics(r):
    tag = ('' if r['set'] == 'physio_rot_split2' else r['set'] + '__') + r['dir'] + '__' + r['win']
    f = f'{SPLIT}/{tag}.e04.json'
    if not os.path.exists(f): return None
    x = json.load(open(f))['windows'].get(r['win'])
    if not isinstance(x, dict) or 'mu_squeeze' not in x: return None
    m = dict(mu=x['mu_squeeze'], slip=x['one_face_slip_bound_mm'], N=x['N_total'], trans=float(np.linalg.norm(x['cage_translation_tied_mm'])),
             reached=bool(x['target_reached']), complete=bool(x['window_check'].get('complete')))
    f5 = f'{SPLIT}/{tag}.e05.json'
    if os.path.exists(f5):
        y = json.load(open(f5))
        m['peak'] = (y.get('windows', {}).get(r['win']) or {}).get('peak')
    return m


def tied_pairs(rows):
    """Byte-identical case.feb + restart.feb, Pardiso (window + parent) vs cuDSS (window + parent); one pair per input."""
    g = collections.defaultdict(list)
    for r in rows:
        if r['set'].startswith('physio_rot'): g[(r['case'], r['restart'], r['win'])].append(r)
    out = []
    for k, v in g.items():
        P = [x for x in v if x['solver'] == 'pardiso' and x['parent_solver'] == 'pardiso']
        C = [x for x in v if x['solver'] == 'cudss' and x['parent_solver'] == 'cudss']
        if not (P and C): continue
        ma, mb = tied_metrics(P[0]), tied_metrics(C[0])
        if not (ma and mb): continue
        valid = ma['reached'] and mb['reached'] and ma['complete'] and mb['complete']
        discord = (ma['reached'] and ma['complete']) != (mb['reached'] and mb['complete'])
        out.append(dict(a=P[0], b=C[0], ma=ma, mb=mb, valid=valid, discordant=discord, design_key=k[0][:8], win=k[2]))
    return out


# ---------------------------------------------------------------- friction: gate-4 quantity at the PI evaluation point
def friction_groups(rows):
    C = json.load(open(f'{EVO}/results/method/fric/compare.json'))
    idx = {(r['set'], r.get('case_dir'), r['window']): r for r in C if r.get('case_dir')}
    sh = {}
    with open(f'{EVO}/results/method/fric/e07_summary.csv') as f:
        for r in csv.DictReader(f):
            vals = [r.get('horizontal_shear_p99_at_rom'), r.get('vertical_shear_p99_at_rom')]
            vals = [float(x) for x in vals if x not in (None, '')]
            if vals and r.get('rom_reached') == 'True': sh[(r['case_dir'], r['window'])] = max(vals)   # S10 quantity (ops/e07_batch.py)
    g = collections.defaultdict(list)
    for r in rows:
        if r['set'] != 'physio_fric3': continue
        c = idx.get((r['set'], r['dir'], r['win']))
        if c is None: continue
        ev = '1.5Nm' if c['fric_reached'] else ('ROM' if c.get('rom_reached') else None)      # ops/fric_compare.py, PI 2026-11-05 item 1
        u = c['fric_translation_mm'] if ev == '1.5Nm' else (c['u_h_at_rom'] if ev == 'ROM' else None)
        post = c['fric_posterior_mm'] if ev == '1.5Nm' else (c['post_at_rom'] if ev == 'ROM' else None)
        g[(r['case'], r['restart'], r['win'])].append(dict(dir=r['dir'], win=r['win'], solver=r['solver'], parent=r['parent_solver'], ev=ev, u=u, post=post,
                                                            shear=sh.get((r['dir'], r['win']))))
    return [v for v in g.values() if len(v) > 1]


def fail(x): return x['u'] > 1.0 or x['post'] > 0.5           # gate-4 rule, strict >


# ---------------------------------------------------------------- gate 2 logs
def read_rigid(path):
    out, t = [], None
    for line in open(path):
        if line.startswith('*Time'): t = float(line.split('=')[1])
        elif line[:1].isdigit() and t is not None: out.append((t, [float(v) for v in line.split(',')[1:]]))
    return out


def parse_gate2(path, ax):
    s = open(path, errors='ignore').read()
    steps = re.findall(r'\[step\] t=([\d.]+) .*?th \[([^\]]+)\]', s)
    t = np.array([float(a) for a, _ in steps])
    th = np.array([float(b.split(',')[ax]) for _, b in steps])
    err = re.findall(r'RuntimeError: Newton not converged at t=([\d.]+)', s)
    rep = re.findall(r'\{"direction".*\}', s)
    infra = bool(re.search(r'CUDA\w*Error', s))
    return dict(t=t, th=th, stop=float(err[-1]) if err else None, passed=json.loads(rep[-1]) if rep else None, infra=infra)


def rerun_exit():
    f = f'{RERUN}/status.txt'; out = {}
    if os.path.exists(f):
        for line in open(f):
            a = line.split()
            if len(a) == 3: out[a[0]] = int(a[2])
    return out


def gate2_history():
    """Per direction: {attempt: dict(reach %, how it ended)}. Attempts 1-4 = the logs of 27-28 Oct in suffix order (time-ordered; the
    prev3 batch is left out: a GPU driver assert stopped it, flexion was stopped by hand at t 1.5), attempt 'today' = the rerun."""
    H = {}
    log = f'{EVO}/work/agents'
    for d in DIRS:
        ax = AXIS[d[-1]]; rows = {}
        for k, suf in enumerate(['.prev', '.prev2', '.prev4', '']):
            f = f'{log}/gate2_{d}{suf}.log'
            if not os.path.exists(f): continue
            g = parse_gate2(f, ax)
            if g['infra'] or len(g['t']) == 0: continue
            rows[k] = dict(when=datetime.datetime.fromtimestamp(os.path.getmtime(f)), reach=100 * max(0, min(1, g['t'][-1] - 1)),
                           end='pass' if g['passed'] else ('diverged' if g['stop'] else 'stopped'))
        f = f'{RERUN}/{d}.log'
        if os.path.exists(f):
            g = parse_gate2(f, ax)
            if len(g['t']):
                rows[4] = dict(when=datetime.datetime.fromtimestamp(os.path.getmtime(f)), reach=100 * max(0, min(1, g['t'][-1] - 1)),
                               end='pass' if g['passed'] else ('diverged' if g['stop'] else 'running'))
                if rows[4]['end'] == 'running':
                    if d in rerun_exit(): rows[4]['end'] = 'stopped'   # hit the time limit of the rerun
                    else: del rows[4]                                  # not ended yet: nothing to report
        H[d] = rows
    return H


# ---------------------------------------------------------------- stats
def equiv(e, delta):
    e = np.abs(np.asarray(e, float)); n = len(e)
    if n < 2: return dict(n=n, mean=float(e.mean()) if n else None, max=float(e.max()) if n else None, p=None, ucb=None, p_wilcoxon=None)
    m, s = e.mean(), e.std(ddof=1)
    p = (0.0 if m < delta else 1.0) if s == 0 else float(stats.t.sf((delta - m) / (s / np.sqrt(n)), n - 1))
    ucb = m + stats.t.ppf(0.95, n - 1) * s / np.sqrt(n)
    d = delta - e
    pw = float(stats.wilcoxon(d, alternative='greater', method='exact').pvalue) if np.any(d != 0) and len(set(np.abs(d))) == n else None
    return dict(n=n, mean=float(m), max=float(e.max()), p=p, ucb=float(ucb), p_wilcoxon=pw)


def pdiff(signed):
    signed = np.asarray(signed, float)
    if len(signed) < 2 or np.all(signed == 0): return None
    return float(stats.wilcoxon(signed, alternative='two-sided', method='exact').pvalue)


def holm(ps):
    idx = [i for i, p in enumerate(ps) if p is not None]; m = len(idx); out = [None] * len(ps); run = 0.0
    for rank, i in enumerate(sorted(idx, key=lambda i: ps[i])):
        run = max(run, min(1.0, (m - rank) * ps[i])); out[i] = run
    return out


def fmt_p(p):
    if p is None: return '—'
    return '<0.001' if p < 0.001 else (f'{p:.3f}' if p < 0.1 else f'{p:.2f}')


def fmt_pct(x):
    if x is None: return '—'
    x = x * 100
    if x == 0: return '0'
    if x >= 0.0095: return f'{x:.2g}%' if x < 100 else f'{x:.0f}%'
    e = int(np.floor(np.log10(x))); return f'{x / 10 ** e:.1f}×10$^{{{e}}}$%'


# ---------------------------------------------------------------- build rows
def build():
    rows = rescan() if ('--rescan' in sys.argv or not os.path.exists(SCAN)) else json.load(open(SCAN))
    R = {}
    # A1-3: NUM-10
    cmp = json.load(open(f'{HS}/verify_patch_20261105/compare.json'))['cases']
    R['fsu_cpu'] = [v['worst_rel'] for k, v in cmp.items() if k.startswith('fsu/')]
    R['fsu_gpu'] = [v['worst_rel'] for k, v in cmp.items() if k.startswith('fsu_gpu/')]
    R['c0c7'] = [v['worst_rel'] for k, v in cmp.items() if k.startswith('c0c7/')]
    # A4-7: tied, byte-identical inputs
    tp = tied_pairs(rows)
    val = [p for p in tp if p['valid']]
    for q in ('mu', 'slip', 'N', 'peak', 'trans'):
        R['tied_' + q] = [(p['mb'][q] - p['ma'][q]) / abs(p['ma'][q]) for p in val if p['ma'].get(q) and p['mb'].get(q) is not None]
    R['_tied_pairs'] = tp
    # A8-10: friction
    gr = friction_groups(rows)
    cpu_gpu, gpu_gpu, shear, plot_pairs, flips, discord = [], [], [], [], [], []
    for v in gr:
        P = [x for x in v if x['solver'] == 'pardiso']; C = [x for x in v if x['solver'] == 'cudss']
        for a, b in itertools.combinations(v, 2):
            if a['ev'] is None or b['ev'] is None or a['ev'] != b['ev']:
                discord.append((a['dir'], b['dir'], a['win'], a['ev'], b['ev'])); continue
            plot_pairs.append(dict(a=a, b=b, cg=(a['solver'] != b['solver']), flip=fail(a) != fail(b)))
        def worst(A, B):
            best = None
            for a in A:
                for b in B:
                    if a is b or a['ev'] is None or a['ev'] != b['ev']: continue
                    e = (b['u'] - a['u']) / abs(a['u'])
                    if best is None or abs(e) > abs(best[0]): best = (e, a, b)
            return best
        w = worst(P, C)
        if w: cpu_gpu.append(w[0])
        sym = lambda x, y: abs(x - y) / (0.5 * (abs(x) + abs(y)))        # repeat runs are exchangeable: symmetric |e|, no direction
        cc = [sym(a['u'], b['u']) for a, b in itertools.combinations(C, 2) if a['ev'] is not None and a['ev'] == b['ev']]
        if cc: gpu_gpu.append(max(cc))
        # shear: same input, whichever solvers, both ROM reached
        s = [x for x in v if x['shear'] is not None]
        if len(s) > 1:
            shear.append(max(sym(a['shear'], b['shear']) for a, b in itertools.combinations(s, 2)))
    R.update(fr_cpu_gpu=cpu_gpu, fr_gpu_gpu=gpu_gpu, fr_shear=shear)
    R['_fr_pairs'] = plot_pairs; R['_fr_discord'] = discord; R['_fr_groups'] = gr
    # B: gpufe
    v = f'{EVO}/results/gpufe_verify'
    g1 = json.load(open(f'{v}/gate1/gate1_report.json'))['cases']
    R['g1_stress'] = [max(t['stress_rel_err'] for t in c['per_time'].values()) for c in g1 if 'stress_rel_err' in next(iter(c['per_time'].values()))]
    R['g1_react'] = [max(t['reaction_rel_err'] for t in c['per_time'].values()) for c in g1]
    g1b = json.load(open(f'{v}/gate1b/gate1b_report.json'))['cases']
    R['g1b_u'] = [max(t['u_rel_err'] for t in c['per_time'].values()) for c in g1b]
    g1c = json.load(open(f'{v}/gate1c/gate1c_report.json'))['cases']
    rat, fz, coul, ri = [], [], [], {}
    for c in g1c:
        s = [r for r in c['rows'] if r['t'] >= 0.85 and r.get('febio_F') is not None]
        g, f = np.mean([r['gpu_ratio'] for r in s]), np.mean([r['febio_ratio'] for r in s])
        gz, fz_ = np.mean([r['gpu_F'][2] for r in s]), np.mean([r['febio_F'][2] for r in s])
        rat.append((g - f) / f); fz.append((gz - fz_) / fz_); coul.append(c['sliding_ratio_rel_err']); ri[c['mu']] = (float(g), float(f))
    R.update(g1c_ratio=rat, g1c_fz=fz, g1c_coulomb=coul, _g1c=ri)
    # gate 2
    G2 = {}
    for d in DIRS:
        ax = AXIS[d[-1]]
        ref = read_rigid(f'{EVO}/snapshot/reference/fsu_intact/{d}/C3pot_rigid.txt')
        rt = np.array([r[0] for r in ref]); rth = np.array([r[1][3 + ax] for r in ref])
        f = f'{RERUN}/{d}.log'
        g = parse_gate2(f, ax) if os.path.exists(f) else dict(t=np.array([]), th=np.array([]), stop=None, passed=None, infra=False)
        g['source'] = 'today'
        if not (g['passed'] or g['stop'] is not None):            # rerun not ended yet: use the last full attempt, labelled with its date
            g = parse_gate2(f'{EVO}/work/agents/gate2_{d}.log', ax); g['source'] = '28 Oct'
        G2[d] = dict(rt=rt, rth=rth, **g)
    R['_G2'] = G2
    R['g2_rom'] = [G2[d]['passed']['end_rel_err'] for d in DIRS if G2[d]['passed']]
    R['_hist'] = gate2_history()
    return R


def table(R):
    """(section, label, key, margin, signed?, note)"""
    T = [
        ('A', 'Intact FSU: nodal displacement, rebuild vs baseline, CPU solver', 'fsu_cpu', D_NUM10, False, None),
        ('A', 'Intact FSU: nodal displacement, rebuild vs baseline, GPU solver', 'fsu_gpu', D_NUM10, False, None),
        ('A', 'C0–C7 spine: nodal displacement, rebuild vs baseline', 'c0c7', D_NUM10, False, None),
        ('A', 'Tied cage: squeeze-out friction coefficient $\\mu_{sq}$', 'tied_mu', D_PI_DT, True, D_NUM11),
        ('A', 'Tied cage: one-face slip bound', 'tied_slip', D_PI_DT, True, D_NUM11),
        ('A', 'Tied cage: total normal force $N$', 'tied_N', D_PI_DT, True, D_NUM11),
        ('A', 'Tied cage: peak soft-phase compression', 'tied_peak', D_PI_DT, True, D_NUM11),
        ('A', 'Friction: interface shear (p99), repeat runs', 'fr_shear', D_PI_NUM, False, None),
        ('A', 'Friction: cage slip $u_h$, GPU vs CPU solver', 'fr_cpu_gpu', D_PI_NUM, True, None),
        ('A', 'Friction: cage slip $u_h$, two GPU-solver runs', 'fr_gpu_gpu', D_PI_NUM, False, None),
        ('B', 'Element Cauchy stress (gate 1)', 'g1_stress', D_GATE1, False, None),
        ('B', 'Nodal reaction force (gate 1)', 'g1_react', D_GATE1, False, None),
        ('B', 'Static equilibrium displacement (gate 1b)†', 'g1b_u', D_GATE1, False, None),
        ('B', 'Sliding $F_x/F_z$ vs Coulomb law, not FEBio (gate 1c)†', 'g1c_coulomb', D_GATE1C, False, None),
        ('B', 'Sliding normal force $F_z$ (gate 1c)†', 'g1c_fz', None, False, None),
        ('B', 'Intact FSU: ROM, six directions (gate 2)', 'g2_rom', D_GATE2, False, None),
        ('B', 'Intact FSU: facet contact force (gate 2)', None, None, False, None),
        ('B', 'Tied cage: ROM, forces, $\\mu$, tractions (gate 3)', None, D_GATE3, False, None),
        ('B', 'Friction cage: slip $u_h$, shear (gate 4)', None, None, False, None),
    ]
    out = []
    for sec, label, key, delta, signed, strict in T:
        e = R.get(key, []) if key else []
        st = equiv(e, delta) if (key and delta and len(e)) else dict(n=len(e), mean=None, max=float(np.abs(e).max()) if len(e) else None, p=None, ucb=None, p_wilcoxon=None)
        out.append(dict(sec=sec, label=label, key=key, delta=delta, strict=strict, e=list(np.abs(e)), signed=signed,
                        p_diff=pdiff(e) if signed else None, **st))
    padj = holm([r['p'] for r in out])
    for r, p in zip(out, padj):
        r['p_adj'] = p
        if r['key'] == 'g2_rom': r['verdict'], r['why'] = 'na', f"Not testable, {r['n']}/6"
        elif r['key'] is None: r['verdict'], r['why'] = ('na', 'No result, 0/5') if 'facet' in r['label'] else ('none', 'Not run')
        elif r['delta'] is None: r['verdict'], r['why'] = 'na', 'No margin set'
        elif r['p_adj'] is not None and r['p_adj'] < 0.05 and r['max'] < r['delta']:
            r['verdict'] = 'eq'
            r['why'] = 'Equivalent' if (r['strict'] is None or r['max'] < r['strict']) else f"Equivalent at {fmt_pct(r['delta'])}\nnot at {fmt_pct(r['strict'])}"
        elif r['max'] >= r['delta']: r['verdict'], r['why'] = 'ne', 'Not equivalent'
        else: r['verdict'], r['why'] = 'na', 'Inconclusive'
        r['strict_pass'] = (r['strict'] is not None and r['max'] is not None and r['max'] < r['strict'])
    return out


# ---------------------------------------------------------------- figure
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#8a8982', '#e4e3df'
BLUE, ORANGE = '#2a78d6', '#eb6834'
GOOD, CRIT = '#0ca30c', '#d03b3b'
MM = 1 / 25.4
W, H = 180, 226


def setup():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'font.size': 6, 'axes.linewidth': 0.5, 'axes.edgecolor': INK2, 'axes.labelcolor': INK,
                         'xtick.color': INK2, 'ytick.color': INK2, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.major.size': 2, 'ytick.major.size': 2,
                         'xtick.minor.size': 1, 'ytick.minor.size': 1, 'xtick.minor.width': 0.3, 'ytick.minor.width': 0.3, 'axes.labelsize': 6, 'xtick.labelsize': 5.5, 'ytick.labelsize': 5.5,
                         'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'mathtext.default': 'regular', 'axes.labelpad': 1.5,
                         'xtick.major.pad': 1.5, 'ytick.major.pad': 1.5, 'lines.linewidth': 0.9})


def ax_mm(fig, x, y, w, h, **k):
    return fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H], **k)


def plabel(fig, x, y, letter, title):
    fig.text(x / W, 1 - y / H, letter, fontsize=8, fontweight='bold', va='top', color=INK)
    fig.text((x + 3.6) / W, 1 - (y + 0.45) / H, title, fontsize=6.2, va='top', color=INK, fontweight='bold')


def identity(ax, xs, ys, hx=(), hy=(), scale=1.0, label='', unit='', note=''):
    all_ = np.array(list(xs) + list(ys) + list(hx) + list(hy), float) * scale
    lo, hi = all_.min(), all_.max(); pad = 0.08 * (hi - lo)
    lim = (max(0, lo - pad), hi + pad)
    ax.plot(lim, lim, color=MUTED, lw=0.5, zorder=1)
    if len(hx): ax.scatter(np.array(hx) * scale, np.array(hy) * scale, s=11, facecolor='white', edgecolor=ORANGE, lw=0.6, zorder=2)
    ax.scatter(np.array(xs) * scale, np.array(ys) * scale, s=8, color=BLUE, edgecolor='white', lw=0.25, zorder=3)
    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect('equal', adjustable='box')
    ax.locator_params(nbins=3)
    ax.set_xlabel(f'{label}, CPU run{unit}', fontsize=5.5); ax.set_ylabel(f'{label}, GPU run{unit}', fontsize=5.5)
    ax.text(0.04, 0.96, note, transform=ax.transAxes, va='top', fontsize=5.2, color=INK2)


def figure(R, T):
    setup()
    fig = plt.figure(figsize=(W * MM, H * MM), facecolor='white')
    # ---- a tied identity
    tp = R['_tied_pairs']; val = [p for p in tp if p['valid']]; dis = [p for p in tp if p['discordant']]
    plabel(fig, 2, 2, 'a', f"FEBio with GPU vs CPU linear solver, tied cage, identical inputs (n = {len(val)} windows, {len({p['design_key'] for p in val})} designs)")
    spec = [('mu', '$\\mu_{sq}$', 1, ''), ('slip', 'Slip bound', 1, ' (mm)'), ('N', '$N$', 1, ' (N)'), ('peak', 'Peak compr.', 100, ' (%)')]
    for i, (q, lab, sc, un) in enumerate(spec):
        ax = ax_mm(fig, 9 + i * 29.5, 8.5, 20.5, 20.5)
        xs = [p['ma'][q] for p in val]; ys = [p['mb'][q] for p in val]
        hx = [p['ma'][q] for p in dis]; hy = [p['mb'][q] for p in dis]
        e = np.abs(R['tied_' + q]).max()
        identity(ax, xs, ys, hx, hy, sc, lab, un, f'max |e| {fmt_pct(e)}')
    fig.legend(handles=[Line2D([], [], marker='o', ls='', color=BLUE, ms=3, label=f'both windows valid (tested, n = {len(val)})'),
                        Line2D([], [], marker='o', ls='', mfc='white', mec=ORANGE, ms=3.2, mew=0.6, label=f'CPU run incomplete, GPU run not (excluded, n = {len(dis)})'),
                        Line2D([], [], color=MUTED, lw=0.5, label='line of identity')],
               loc='upper left', bbox_to_anchor=(9 / W, 1 - 35.3 / H), ncol=3, frameon=False, fontsize=5.2, handletextpad=0.2, columnspacing=1.0, borderpad=0)
    # ---- b friction identity
    plabel(fig, 127, 2, 'b', 'Real-friction cage slip: repeat runs, same input')
    ax = ax_mm(fig, 134, 8.5, 23, 23)
    pp = R['_fr_pairs']
    lim = (0, 1.3)
    ax.plot(lim, lim, color=MUTED, lw=0.5, zorder=1)
    ax.axvline(0.5, color=INK2, lw=0.4, ls=(0, (2, 2))); ax.axhline(0.5, color=INK2, lw=0.4, ls=(0, (2, 2)))
    ax.axvline(1.0, color=INK2, lw=0.4, ls=(0, (1, 2))); ax.axhline(1.0, color=INK2, lw=0.4, ls=(0, (1, 2)))
    for p in pp:
        a, b = p['a'], p['b']
        ext = a['win'] == 'extension'
        c = CRIT if p['flip'] else BLUE
        ax.scatter(a['u'], b['u'], s=11 if p['flip'] else 8, marker='o' if ext else 's', facecolor=c if p['cg'] else 'white', edgecolor=c, lw=0.6, zorder=3)
    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect('equal'); ax.set_xticks([0, 0.5, 1.0]); ax.set_yticks([0, 0.5, 1.0])
    ax.set_xlabel('$u_h$, run A (mm)', fontsize=5.5); ax.set_ylabel('$u_h$, run B (mm)', fontsize=5.5)
    nflip = sum(p['flip'] for p in pp)
    ax.annotate(f'{nflip} same-input pairs\ngive opposite verdicts', xy=(0.53, 0.56), xytext=(0.66, 0.20), fontsize=5, color=INK, ha='left', va='center', linespacing=1.1,
                arrowprops=dict(arrowstyle='-', lw=0.4, color=INK2, shrinkB=1, shrinkA=1))
    lx = 159
    hs = [Line2D([], [], marker='o', ls='', color=INK2, ms=2.8, label='extension'), Line2D([], [], marker='s', ls='', color=INK2, ms=2.6, label='flexion'),
          Line2D([], [], marker='o', ls='', color=BLUE, ms=2.8, label='GPU vs CPU run'), Line2D([], [], marker='o', ls='', mfc='white', mec=BLUE, ms=2.8, mew=0.6, label='GPU vs GPU run'),
          Line2D([], [], marker='o', ls='', color=CRIT, ms=2.8, label='verdict flips'), Line2D([], [], color=INK2, lw=0.4, ls=(0, (2, 2)), label='0.5 mm post.'), Line2D([], [], color=INK2, lw=0.4, ls=(0, (1, 2)), label='1 mm any')]
    fig.legend(handles=hs, loc='upper left', bbox_to_anchor=(lx / W, 1 - 8 / H), frameon=False, fontsize=5, labelspacing=0.45, handletextpad=0.25, borderpad=0, handlelength=1.3)
    # ---- c gate 2 small multiples
    fv = json.load(open(f'{EVO}/snapshot/reference/fsu_intact/fsu_refined_vs_full.json'))
    fac = {}
    for sect in fv.values():
        for k, v in sect.items():
            m = re.match(r'facet_(\w+)_fsu_N', k)
            if m: fac[m.group(1)] = v['L'] + v['R']
    plabel(fig, 2, 42.5, 'c', 'Intact segment: in-house solver gpufe vs FEBio')
    G = R['_G2']
    for i, d in enumerate(DIRS):
        ax = ax_mm(fig, 9 + (i % 3) * 39, 49.5 + (i // 3) * 22.5, 29, 15.5)
        g = G[d]; m = g['rt'] >= 1.0 - 1e-9
        mr = 1.5 * (g['rt'][m] - 1); ref = np.abs(np.degrees(g['rth'][m])) 
        ref0 = abs(np.degrees(np.interp(1.0, g['rt'], g['rth'])))
        ax.plot(np.r_[0, mr], np.r_[ref0, ref], color=INK, lw=0.9, zorder=2)
        k = g['t'] >= 1.0 - 1e-9
        tg, thg = g['t'][k], np.abs(np.degrees(g['th'][k]))
        col = ORANGE
        if len(tg):
            ax.plot(1.5 * (tg - 1), thg, ls='', marker='o', ms=2.2, color=col, mec='white', mew=0.2, zorder=3)
        if g['passed']:
            txt = f"finished, end |e| {fmt_pct(g['passed']['end_rel_err'])}"
        elif g['stop'] is not None:
            xs = 1.5 * (tg[-1] - 1); ax.plot([xs], [thg[-1]], marker='x', ms=4, mew=0.9, color=CRIT, zorder=4)
            txt = f"diverged at {100 * (tg[-1] - 1):.0f}% of moment" + ('\n(run of 28 Oct)' if g['source'] != 'today' else '')
        else:
            if len(tg): ax.plot([1.5 * (tg[-1] - 1)], [thg[-1]], marker='>', ms=2.8, color=MUTED, zorder=4)
            txt = f"still running at {100 * max(0, tg[-1] - 1):.0f}%" if len(tg) else 'pending'
        ax.set_xlim(0, 1.5); ax.set_ylim(bottom=0); ax.set_xticks([0, 0.5, 1, 1.5])
        ax.text(0.03, 1.0, DIRNAME[d], transform=ax.transAxes, fontsize=5.6, fontweight='bold', va='top', color=INK)
        ax.text(0.97, 0.03, f"{txt}\nFEBio facet force {fac[d]:.0f} N", transform=ax.transAxes, fontsize=4.9, va='bottom', ha='right', color=INK2, linespacing=1.15)
        if i % 3 == 0: ax.set_ylabel('C3 rotation (°)', fontsize=5.5)
        if i // 3 == 1: ax.set_xlabel('Moment (N·m)', fontsize=5.5)
    fig.legend(handles=[Line2D([], [], color=INK, lw=0.9, label='FEBio'), Line2D([], [], ls='', marker='o', ms=2.4, color=ORANGE, label='gpufe (current code)'),
                        Line2D([], [], ls='', marker='x', ms=3.4, mew=0.9, color=CRIT, label='solver diverged')],
               loc='upper left', bbox_to_anchor=(70 / W, 1 - 42.9 / H), ncol=3, frameon=False, fontsize=5.2, handletextpad=0.3, columnspacing=0.9, borderpad=0)
    # ---- d attempts
    plabel(fig, 128, 42.5, 'd', 'Has gpufe been getting closer?')
    ax = ax_mm(fig, 136, 49.5, 40, 31)
    Hh = R['_hist']
    for d in DIRS:
        flex = d == 'flex_pos_y'; col = ORANGE if flex else MUTED
        done = sorted(k for k, r in Hh[d].items() if r['end'] in ('pass', 'diverged'))
        ax.plot(done, [Hh[d][k]['reach'] for k in done], color=col, lw=0.9 if flex else 0.6, zorder=3 if flex else 2)
        for k, r in Hh[d].items():
            ax.plot([k], [r['reach']], marker='o', ms=2.6, mfc=col if r['end'] in ('pass', 'diverged') else 'white', mec=col, mew=0.5, zorder=4)
    ax.axhline(100, color=INK2, lw=0.4, ls=(0, (2, 2)))
    ax.set_xticks([0, 1, 2, 3, 4]); ax.set_xticklabels(['1', '2', '3', '4', 'Today'])
    ax.set_xlim(-0.25, 4.3); ax.set_ylim(0, 108); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel('Moment reached (% of 1.5 N\u00b7m)', fontsize=5.5); ax.set_xlabel('Gate 2 attempt (1\u20134: 27\u201328 Oct; today: 5 Nov)', fontsize=5.5)
    ax.text(0.15, 96, 'Flexion: no facet contact, finishes', fontsize=5, color=INK, va='top', ha='left')
    ax.text(4.25, 31, 'Five directions with facet\ncontact: no finish, no trend', fontsize=5, color=INK, va='bottom', ha='right', linespacing=1.15)
    ax.plot([], [], marker='o', ms=2.6, mfc='white', mec=MUTED, mew=0.5, ls='', label='run stopped before a result')
    ax.legend(loc='center left', bbox_to_anchor=(0.0, 0.62), frameon=False, fontsize=5, handletextpad=0.1, borderpad=0)
    # ---- e forest
    y0 = 97.5
    n_eq = sum(r['verdict'] == 'eq' for r in T); n_ne = sum(r['verdict'] == 'ne' for r in T); n_na = sum(r['verdict'] in ('na', 'none') for r in T)
    plabel(fig, 2, y0, 'e', f'Equivalence tests: {n_eq} rows equivalent, {n_ne} not equivalent, {n_na} without a conclusive test. No real-friction cage metric is equivalent.')
    nr = len(T) + 2; rh = 4.1
    fx, fw = 57, 56
    ax = ax_mm(fig, fx, y0 + 8.5, fw, nr * rh)
    ax.set_xscale('log'); ax.set_xlim(1e-14, 2); ax.set_ylim(nr, 0)
    ax.spines['left'].set_visible(False); ax.set_yticks([])
    ax.set_xticks([1e-12, 1e-9, 1e-6, 1e-3, 1]); ax.set_xticklabels(['10$^{-12}$', '10$^{-9}$', '10$^{-6}$', '10$^{-3}$', '1'])
    ax.minorticks_off()
    for x in [1e-12, 1e-9, 1e-6, 1e-3, 1]: ax.axvline(x, color=GRID, lw=0.4, zorder=0)
    ax.set_xlabel('Relative difference |e| from the reference, FEBio unless stated (log scale)', fontsize=5.5)
    tr = blended_transform_factory(fig.transFigure, ax.transData)
    cols = dict(n=117.5, d=126, m=137, pd=146.5, pe=155, v=160.5)
    ty = 1 - (y0 + 8.2) / H
    for k, s, ha in [('n', 'n', 'center'), ('d', 'Margin\nΔ', 'center'), ('m', 'Max\n|e|', 'center'), ('pd', '$p_{diff}$', 'center'), ('pe', '$p_{equiv}$', 'center'), ('v', 'Verdict', 'left')]:
        fig.text(cols[k] / W, ty, s, fontsize=5.5, fontweight='bold', va='bottom', ha=ha, color=INK, linespacing=1.0)
    y = 0.0
    secs = {'A': 'Production platform: FEBio 4.13 + patches, linear solver cuDSS (GPU) or Pardiso (CPU); every reported cage result comes from here',
            'B': 'In-house GPU solver (gpufe) vs FEBio, same input deck (barred from design ranking until gates 2\u20134 pass, restriction R04)'}
    cur = None; mark = {'eq': ('✓', GOOD), 'ne': ('✗', CRIT), 'na': ('–', MUTED), 'none': ('○', MUTED)}
    for r in T:
        if r['sec'] != cur:
            cur = r['sec']
            ax.text(2 / W, y + 0.72, secs[cur], transform=tr, fontsize=5.6, fontweight='bold', color=INK, va='baseline', clip_on=False)
            ax.plot([2 / W, 178 / W], [y + 0.98, y + 0.98], transform=tr, color=INK2, lw=0.4, clip_on=False, zorder=1)
            y += 1
        c = y + 0.5
        ax.text(2.5 / W, c, r['label'], transform=tr, fontsize=5.6, va='center', ha='left', color=INK)
        if r['delta']:
            ax.plot([r['delta']] * 2, [c - 0.38, c + 0.38], color=INK, lw=1.0, zorder=3, solid_capstyle='butt')
        if r['strict']:
            ax.plot([r['strict']], [c], marker='|', ms=4.5, mew=0.5, color=MUTED, zorder=3)
        if len(r['e']):
            e = np.clip(np.array(r['e'], float), 1.5e-14, None)
            jit = np.linspace(-0.17, 0.17, len(e)) if len(e) > 1 else [0]
            ax.scatter(e, c + np.array(jit), s=4, color=INK2, alpha=0.65, lw=0, zorder=2)
            if r['ucb'] is not None:
                ax.plot([max(r['mean'], 1.5e-14), max(r['ucb'], 1.5e-14)], [c, c], color=mark[r['verdict']][1], lw=1.0, zorder=4)
            if r['mean'] is not None and len(e) > 1:
                ax.plot([max(r['mean'], 1.5e-14)], [c], marker='D', ms=2.8, color=mark[r['verdict']][1], mec='white', mew=0.3, zorder=5)
        ax.text(cols['n'] / W, c, str(r['n']), transform=tr, fontsize=5.5, va='center', ha='center', color=INK)
        ax.text(cols['d'] / W, c, fmt_pct(r['delta']) if r['delta'] else '—', transform=tr, fontsize=5.3, va='center', ha='center', color=INK)
        ax.text(cols['m'] / W, c, fmt_pct(r['max']), transform=tr, fontsize=5.3, va='center', ha='center', color=INK)
        ax.text(cols['pd'] / W, c, fmt_p(r['p_diff']), transform=tr, fontsize=5.3, va='center', ha='center', color=INK)
        ax.text(cols['pe'] / W, c, fmt_p(r['p_adj']), transform=tr, fontsize=5.3, va='center', ha='center', color=INK)
        ic, col = mark[r['verdict']]
        ax.text(cols['v'] / W, c, ic, transform=tr, fontsize=6.3, va='center', ha='left', color=col, fontweight='bold', family='DejaVu Sans')
        ax.text((cols['v'] + 2.8) / W, c, r['why'], transform=tr, fontsize=5.3 if '\n' not in r['why'] else 4.8, va='center', ha='left', color=INK, linespacing=1.0)
        y += 1
    # key + abbreviations
    yk = y0 + 8.5 + nr * rh + 6.6
    key = ("Black bar, equivalence margin \u0394 taken from existing project documents; grey tick, stricter NUM-11 margin of 0.01% (2\u20133 tied windows per metric exceed it); grey dots, single cases; "
           "diamond and whisker, mean |e| and its one-sided 95% upper bound. $p_{equiv}$: one-sided $t$ test of mean |e| \u2265 \u0394 (two one-sided tests, whose lower test is vacuous because |e| \u2265 0), Holm-adjusted. "
           "Equivalent: $p_{equiv}$ < 0.05 and every case inside \u0394. Not equivalent: at least one case outside \u0394. $p_{diff}$: two-sided exact Wilcoxon signed-rank test, for signed scalars with a natural direction only; "
           "a large $p_{diff}$ alone is not evidence of agreement. \u2020 Gates 1b and 1c ran on the earlier dynamic-relaxation solver, not the current Newton solver. In gate 1c FEBio itself is 8.6% below the Coulomb law at friction coefficient 0.5, so the law is the reference for that row.")
    abbr = ("Baseline, FEBio build of 21 Oct 2026; compr., compression; C0\u2013C7, C3, C4, cervical spine levels; CPU, central processing unit; cuDSS, CUDA Direct Sparse Solver (NVIDIA); e, relative difference; FEBio, Finite Elements for Biomechanics; "
            "$F_x$, $F_z$, friction and normal force; FSU, functional spinal unit; gate 1\u20134, planned verification stages of gpufe against FEBio; GPU, graphics processing unit; linear solver, the step inside FEBio that solves the system of equations (not the in-house solver); gpufe, in-house GPU finite-element solver; "
            "$\\mu_{sq}$, least friction coefficient that prevents squeeze-out of the tied cage; $N$, total normal force on the cage faces; NUM-11, numerical check in the capability register; "
            "Pardiso, Parallel Direct Sparse Solver (Intel Math Kernel Library); post., posterior; p99, 99th percentile; R04, restriction in the capability register; rebuild, FEBio build of 3 Nov 2026; ROM, range of motion; "
            "run, one FEBio run (its linear solver named; CPU run, GPU run); run A, B, two runs of byte-identical inputs; tied, cage glued to the endplates; $u_h$, horizontal cage translation at the evaluation point (1.5 N\u00b7m if transmitted, otherwise intact ROM).")
    import textwrap
    def vis(w): return len(re.sub(r'[$]|\\\\?mu|_\{|\}', '', w))
    def wrap(text, n):
        lines, cur = [], ''
        for w in text.split(' '):
            if cur and vis(cur) + 1 + vis(w) > n: lines.append(cur); cur = w
            else: cur = (cur + ' ' + w) if cur else w
        return '\n'.join(lines + [cur])
    fig.text(2 / W, 1 - yk / H, 'How to read', fontsize=5.3, fontweight='bold', va='top', color=INK)
    fig.text(2 / W, 1 - (yk + 2.3) / H, wrap(key, 222), fontsize=5.1, va='top', color=INK2, linespacing=1.2)
    fig.text(2 / W, 1 - (yk + 11.4) / H, 'Abbreviations', fontsize=5.3, fontweight='bold', va='top', color=INK)
    fig.text(2 / W, 1 - (yk + 13.7) / H, wrap(abbr, 222), fontsize=5.1, va='top', color=INK2, linespacing=1.2)
    os.makedirs(OUT, exist_ok=True)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig_febio_agreement.{ext}', facecolor='white', **kw)
    plt.close(fig)
    return dict(n_eq=n_eq, n_ne=n_ne, n_na=n_na)


def write_legend(R, T, counts, s):
    by = {r['key']: r for r in T if r['key']}
    pct = lambda x: fmt_pct(x).replace('$^{', '^').replace('}$', '')
    tied = s['tied']; fr = s['friction']['pairs']; flips = [p for p in fr if p['flip']]
    qa = open(f'{HS}/qa/QA_STATUS.md', errors='ignore').readline().strip().lstrip('# ')
    g2 = s['gate2']
    today = [d for d in DIRS if g2[d]['source'] == 'today']
    fam = []
    for a in sorted({(p['a']['set'], p['a']['dir']) for p in R['_tied_pairs'] if p['valid']}):
        q = json.load(open(f"{AL}/{a[0]}/{a[1].split('_')[0]}_params.json"))
        m = re.search(r'cage_([AB])_(\w+?)_(mix|interleave)_d([\d.]+)\.npz', q['cage_npz'])
        fam.append(f"{a[1]}: family {m.group(1)}, {m.group(2)} {m.group(3)}, d {float(m.group(4)):.2f} mm")
    fam = '; '.join(fam)
    stops = '; '.join(f"{DIRNAME[d]} {100 * (g2[d]['last_t'] - 1):.0f}%" for d in DIRS if not g2[d]['passed'])
    L = f"""# Figure legend (generated by scripts/8_audit/h38_febio_agreement_fig.py, {s['generated']})

**Fig. | Agreement of the simulation platform with FEBio holds for tied-contact cage metrics and element-level physics, but not for real-friction cage slip, and the in-house solver gpufe has no cage-level result.**

**a**, Tied-contact cage metrics from runs whose case.feb and restart.feb are byte-identical, one with the Pardiso CPU linear solver and one with the cuDSS GPU linear solver (FEBio 4.13 + patches); {tied['valid']} windows in which both runs completed and reached the target moment. Orange circles: {len(tied['discordant'])} windows where only the GPU run completed, excluded from the test and shown. A further {len(tied['neither'])} windows reached the target in neither run.
**b**, Horizontal cage translation under real friction (mu 0.35) at the evaluation point, for pairs of runs with byte-identical inputs. {len(fr)} pairs, {len(flips)} of which fall on opposite sides of the gate-4 limits. Largest separation: {max(fr, key=lambda p: abs(p['ua'] - p['ub']))['a']} {max(fr, key=lambda p: abs(p['ua'] - p['ub']))['ua']:.3f} mm and {max(fr, key=lambda p: abs(p['ua'] - p['ub']))['b']} {max(fr, key=lambda p: abs(p['ua'] - p['ub']))['ub']:.3f} mm.
**c**, C3 rotation against applied moment in the intact C3-C4 segment. FEBio reference line, gpufe markers. Moment reached by gpufe where it diverged: {stops}. Flexion, the only direction that finishes, has no facet contact (FEBio facet force 0 N). Directions rerun on 2026-11-05 at the time of generation: {', '.join(DIRNAME[d] for d in today)}; other directions show the last full attempt of 2026-10-28 (gpufe solver files last changed 2026-10-28 02:27).
**d**, Moment reached in each gate 2 attempt. One batch lost to a GPU driver assert is left out.
**e**, Equivalence tests. Dots are single cases (a window, direction or material), never time points, because time points within a run are not independent. Margins come only from documents that predate this analysis: NUM-10 and NUM-11 0.01%; PI 2026-11-03 numerical tolerances 2% (time step, strictest) and 5% (mesh and penalty, loosest); gate plan 1% (gate 1), 2% (gate 1c script), 5% (gate 2), 10% (gate 3).

## Statistics
- e = (platform - reference) / |reference|, or a norm-based relative error where the quantity is a field. Repeat runs have no natural reference, so they use |a - b| / mean(a, b), and for groups of three runs the largest pair.
- Test: H0 mean|e| >= margin against H1 mean|e| < margin, one-sided t test, Holm-adjusted over the {sum(r['p'] is not None for r in T)} rows tested. Two one-sided tests reduce to this because |e| >= 0, and the test on |e| is stricter than the usual test on signed e.
- Equivalent = adjusted p < 0.05 AND every case inside the margin. Not equivalent = at least one case outside the margin.
- The simulations are deterministic in intent, so the p-values describe the spread over the tested cases, not sampling of a population. They do not extend to designs or load cases outside the tested set.
- Robustness: errors span many orders of magnitude, so the exact Wilcoxon version is in equivalence_tests.csv. It agrees on every row, except that n = 2 or 3 cannot reach p < 0.05 by construction (gate 1b, n = 3: exact p = 0.125; its maximum error is 4 orders below the margin).
- Windows of one design share an insertion. Design-level sensitivity, one value per design (3 designs), worst-window p (margin 2%): mu_sq {s['tied_design_level']['mu']['worst']['p']:.2g}, slip bound {s['tied_design_level']['slip']['worst']['p']:.2g}, N {s['tied_design_level']['N']['worst']['p']:.2g}, peak compression {s['tied_design_level']['peak']['worst']['p']:.2g}.
- At the registered NUM-11 margin of 0.01%, tied metrics are not equivalent: windows above it are {tied['exceed_1e4']}. Maximum |e|: mu_sq {pct(by['tied_mu']['max'])}, slip bound {pct(by['tied_slip']['max'])}, N {pct(by['tied_N']['max'])}, peak compression {pct(by['tied_peak']['max'])}, tied cage translation {pct(tied['max_trans'])}.

## Limits of this figure
- Section A compares FEBio with itself under different linear solvers and builds. It shows that the platform's changes do not move tied results by more than the margins. It is not an independent validation of the FEBio model; that is the role of the PHY checks against cadaver data.
- Tied results were compared on 3 designs ({fam}), so they do not cover the whole design space.
- Friction comparisons have few independent inputs (n = {by['fr_cpu_gpu']['n']} GPU vs CPU, {by['fr_gpu_gpu']['n']} GPU vs GPU). They come from physio_fric3 (density 1e-6), which is provisional; the physio_fric4 reference rerun has not replaced it.
- Gates 1b and 1c ran on the earlier dynamic-relaxation solver, not the current Newton solver (findings F-0014, F-0026). In gate 1c the gate's own 2 % criterion is against the Coulomb law, so that row uses the law: with n = 2 the test cannot conclude, though both cases are inside the margin ({pct(R['g1c_coulomb'][0])}, {pct(R['g1c_coulomb'][1])}). At mu 0.5 gpufe gives {R['_g1c'][0.5][0]:.3f} and FEBio {R['_g1c'][0.5][1]:.3f}, so the 8.6 % gap between them is FEBio's own distance from the law, not a gpufe error. FEBio is also not a valid reference for stick memory (verifier note v05).
- C0-C7 row: the PI ruled NUM-10 partial on this case (2026-11-05 06:38).
- Sliding normal force row: gate 1c reports about 2 % as an observation, no margin was ever set, so no verdict is given.

## Terms used in this legend
PI, principal investigator; QA, quality assurance; PHY, physics checks of the capability register (against cadaver and literature data); NUM-10, FEBio patch regression check; NUM-11, GPU versus CPU linear solver check; gate 1d, stick-memory benchmark of gpufe (not plotted, FEBio is not a valid reference for it).

## Sources
verify_patch_20261105/compare.json; results/method/split/*.e04.json and *.e05.json; results/method/fric/compare.json and e07_summary.csv; results/gpufe_verify/gate1, gate1b, gate1c; work/agents/gate2_*.log; gate2_rerun_20261105/; snapshot/reference/fsu_intact. Numbers per row: equivalence_tests.csv; pairs: figure_data.json; hashes: same_input_scan.json.

QA at generation: {qa}. The qa-auditor agent has not reviewed this figure.
Font: Lato with DejaVu Sans fallback (Helvetica or Arial are not installed; change font.family before submission).
"""
    open(f'{OUT}/figure_legend.md', 'w').write(L)


def design_level(R):
    """Sensitivity: windows share one insertion per design, so repeat the tied test with one value per design (mean |e| of its windows, and its worst window)."""
    out = {}
    val = [p for p in R['_tied_pairs'] if p['valid']]
    for q in ('mu', 'slip', 'N', 'peak'):
        g = collections.defaultdict(list)
        for p in val:
            if p['ma'].get(q) and p['mb'].get(q) is not None: g[p['design_key']].append(abs(p['mb'][q] - p['ma'][q]) / abs(p['ma'][q]))
        out[q] = dict(designs=len(g), mean_of_means=equiv([np.mean(v) for v in g.values()], D_PI_DT), worst=equiv([np.max(v) for v in g.values()], D_PI_DT))
    return out


def main():
    R = build(); T = table(R)
    counts = figure(R, T)
    with open(f'{OUT}/equivalence_tests.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['section', 'row', 'n', 'margin', 'stricter_margin', 'within_stricter', 'mean_abs_e', 'max_abs_e', 'ucb95_mean_abs_e', 'p_equiv_raw', 'p_equiv_holm', 'p_equiv_wilcoxon_exact', 'p_diff_wilcoxon', 'verdict', 'abs_e_cases'])
        for r in T:
            w.writerow([r['sec'], re.sub(r'[$\\{}]', '', r['label']), r['n'], r['delta'], r['strict'], r['strict_pass'] if r['strict'] else '', r['mean'], r['max'], r['ucb'], r['p'], r['p_adj'], r['p_wilcoxon'], r['p_diff'], r['why'], ';'.join(f'{x:.4g}' for x in r['e'])])
    tp = R['_tied_pairs']
    s = dict(generated=datetime.datetime.now().isoformat(timespec='seconds'), counts=counts,
             tied=dict(pairs=len(tp), valid=sum(p['valid'] for p in tp), discordant=[(p['a']['dir'], p['b']['dir'], p['win']) for p in tp if p['discordant']],
                       neither=[(p['a']['dir'], p['b']['dir'], p['win']) for p in tp if not p['valid'] and not p['discordant']],
                       valid_pairs=[(p['a']['set'], p['a']['dir'], p['b']['set'], p['b']['dir'], p['win']) for p in tp if p['valid']],
                       exceed_1e4={q: int(np.sum(np.abs(R['tied_' + q]) > 1e-4)) for q in ('mu', 'slip', 'N', 'peak')}, max_trans=float(np.abs(R['tied_trans']).max())),
             friction=dict(pairs=[dict(a=p['a']['dir'], b=p['b']['dir'], win=p['a']['win'], ev=p['a']['ev'], ua=p['a']['u'], ub=p['b']['u'], post_a=p['a']['post'], post_b=p['b']['post'], cpu_gpu=p['cg'], flip=p['flip']) for p in R['_fr_pairs']], discordant=R['_fr_discord']),
             gate1c_ratio=R['_g1c'], gate1c_coulomb=R['g1c_coulomb'],
             gate2={d: dict(source=R['_G2'][d]['source'], stop=R['_G2'][d]['stop'], passed=bool(R['_G2'][d]['passed']), last_t=float(R['_G2'][d]['t'][-1]) if len(R['_G2'][d]['t']) else None) for d in DIRS},
             gate2_history={d: {str(k): dict(when=r['when'].isoformat(timespec='minutes'), reach=r['reach'], end=r['end']) for k, r in R['_hist'][d].items()} for d in DIRS},
             tied_design_level=design_level(R))
    json.dump(s, open(f'{OUT}/figure_data.json', 'w'), indent=1, default=str)
    write_legend(R, T, counts, s)
    for r in T:
        print(f"{r['sec']} {re.sub(r'[$]', '', r['label'])[:52]:52s} n={r['n']:<3d} D={r['delta']} mean={r['mean'] if r['mean'] is None else float('%.3g' % r['mean'])} max={r['max'] if r['max'] is None else float('%.3g' % r['max'])} p={r['p_adj'] if r['p_adj'] is None else float('%.3g' % r['p_adj'])} pW={r['p_wilcoxon']} pdiff={r['p_diff'] if r['p_diff'] is None else float('%.3g' % r['p_diff'])} {r['why']}")
    print(json.dumps(s['tied'], default=str)[:900]); print(counts)
    print([(p['a']['dir'], p['b']['dir'], p['a']['win'], round(p['a']['u'], 3), round(p['b']['u'], 3), p['flip']) for p in R['_fr_pairs']])
    print(R['_fr_discord'])


if __name__ == '__main__':
    main()
