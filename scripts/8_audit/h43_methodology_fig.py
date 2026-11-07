#!/usr/bin/env python3
"""h43: Nature-style methodology figure: platform requirements, method and process, the multi-agent adversarial loop, and how designs are filtered and confirmed.
Status is computed from the register, findings and verdict files; solid = has run, dashed = designed but not started.
usage: python h43_methodology_fig.py    outputs in human_study/figures/main_results/
"""
import os, json, glob, collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = f'{ROOT}/human_study'; EVO = f'{os.path.dirname(ROOT)}/biocage-evo'; OUT = f'{HS}/figures/main_results'
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#8a8982', '#e4e3df'
BLUE, PALE, RED = '#2c5f9e', '#eaf0f7', '#c2427a'
W, H = 180, 163; MM = 1 / 25.4


def box(ax, x, y, w, h, title=None, body=None, fc=PALE, ec=BLUE, dashed=False, fs=5.2, tfs=5.6, align='center', lw=0.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.8', fc='white' if dashed else fc, ec=MUTED if dashed else ec, lw=lw, ls=(0, (2.5, 1.5)) if dashed else '-', zorder=2))
    tx = x + w / 2 if align == 'center' else x + 1.2; ha = 'center' if align == 'center' else 'left'
    if title and body:
        ax.text(tx, y + 1.1, title, ha=ha, va='top', fontsize=tfs, fontweight='bold', color=INK2 if dashed else INK, zorder=3, linespacing=1.05)
        n = title.count('\n') + 1
        ax.text(tx, y + 1.3 + 2.25 * n, body, ha=ha, va='top', fontsize=fs, color=INK2, zorder=3, linespacing=1.12)
    elif title: ax.text(tx, y + h / 2, title, ha=ha, va='center', fontsize=tfs, fontweight='bold', color=INK2 if dashed else INK, zorder=3, linespacing=1.05)


def arrow(ax, a, b, col=INK2, dashed=False, lw=0.7, rad=0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=5.5, lw=lw, color=MUTED if dashed else col, ls=(0, (2.5, 1.5)) if dashed else '-', shrinkA=0, shrinkB=0, zorder=4, connectionstyle=f'arc3,rad={rad}'))


def label(ax, x, y, l, t):
    ax.text(x, y, l, fontsize=8, fontweight='bold', va='top', color=INK); ax.text(x + 3.6, y + 0.45, t, fontsize=6.3, fontweight='bold', va='top', color=INK)


def main():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'pdf.fonttype': 42, 'mathtext.default': 'regular'})
    d = json.load(open(f'{HS}/platform_capabilities.json'))
    tally = lambda cfg, cap: (sum(1 for c in d['checks'] if cfg in c.get('configs', []) and c.get('required') and c['cap'] == cap and c['status'].get(cfg, {}).get('state') == 'pass'),
                              sum(1 for c in d['checks'] if cfg in c.get('configs', []) and c.get('required') and c['cap'] == cap))
    F = [json.load(open(f)) for f in glob.glob(f'{EVO}/work/findings/F-*.json')]; sev = collections.Counter(x['severity'] for x in F)
    ver = [json.load(open(f))['verdict'] for f in sorted(glob.glob(f'{EVO}/work/board/r*/verifier.json'))]; nr = len(ver); assert set(ver) == {'HOLD'}
    cl = json.load(open(f'{EVO}/results/method/split/verdict_classes_merged.json'))['classes']; cnt = {k: len(v) for k, v in cl.items()}
    comp = sum(v for k, v in cnt.items() if k.startswith('DESIGN/compression')); unf0 = cnt['[數值]/unstable-window'] + cnt['[多元]/computability']; exc = cnt['DESIGN/radial-mix-excluded']
    slip, fc, shear = cnt['DESIGN/dislocation-friction'], cnt['[多元]/friction-computability'], cnt['DESIGN/interface-shear-provisional']; total = sum(cnt.values()); npass = cnt.get('PASS', 0)
    fig = plt.figure(figsize=(W * MM, H * MM), facecolor='white'); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
    # a requirements
    label(ax, 2, 2, 'a', 'Requirements: what a cage must do, and what the platform must prove')
    ax.text(2, 8.2, 'Design requirements (agreed with the principal investigator)', fontsize=5.6, fontweight='bold', color=INK, va='top')
    S = [('S1', 'Stays inside the disc space'), ('S2', 'Insertable in one piece from the front'), ('S3', 'One connected part, no loose pieces'), ('S4', 'At least 50% of the space left for the disc'), ('S5', 'Printable: 0.4 mm features, 0.2 mm layers'),
         ('S6', 'Carries at least 1164 N'), ('S7', 'Height loss at most d/2 at 150 N'), ('S8', 'No overload of the bone surface'), ('S9', 'No slip-out: 1 mm, or 0.5 mm towards the cord'), ('S10', 'Hard–soft bond: 3 MPa (provisional)')]
    for i, (a, t) in enumerate(S):
        y = 11.4 + i * 2.95
        ax.text(2, y, a, fontsize=5.2, fontweight='bold', color=BLUE, va='top'); ax.text(7.5, y, t, fontsize=5.2, color=INK, va='top')
    ax.text(2, 41.3, 'Fixation by shape and friction only. Support for at least 16 weeks, then resorbs.', fontsize=5, color=INK2, va='top')
    ax.text(70, 8.2, 'Platform capability labels (required checks passed today)', fontsize=5.6, fontweight='bold', color=INK, va='top')
    ax.text(137, 11.2, 'Glued\ncage', fontsize=5, color=INK2, va='top', ha='center', linespacing=1.0, fontweight='bold'); ax.text(160, 11.2, 'Real\nfriction', fontsize=5, color=INK2, va='top', ha='center', linespacing=1.0, fontweight='bold')
    caps = [('PHY', 'Physics', 'Does the model behave like a real neck and cage?'), ('NUM', 'Numerical', 'Are the equations solved accurately enough?'), ('SPD', 'Speed', 'Fastest route to the same answer?'), ('OBS', 'Observation', 'Do we measure what matters, correctly and traceably?'), ('DIV', 'Diversity', 'Can every kind of design be built and computed?')]
    for i, (k, n, q) in enumerate(caps):
        y = 16.4 + i * 4.6
        ax.text(70, y, n, fontsize=5.4, fontweight='bold', color=INK, va='top'); ax.text(83, y, q, fontsize=5.0, color=INK2, va='top')
        for x0, cfg in ((127, 'TIED'), (150, 'FRIC')):
            p, t = tally(cfg, k)
            ax.add_patch(Rectangle((x0, y + 0.2), 14, 1.6, fc=GRID, ec='none')); ax.add_patch(Rectangle((x0, y + 0.2), 14 * p / max(t, 1), 1.6, fc=BLUE, ec='none'))
            ax.text(x0 + 15, y + 1.0, f'{p}/{t}', fontsize=5, color=INK, va='center')
    ax.text(70, 39.6, 'Secondary, deferred by decision: Generalisation (other anatomies, materials) and Time course (0–16 weeks).', fontsize=5, color=INK2, va='top')
    # b platform
    label(ax, 2, 46, 'b', 'Method and process: one simulation chain, with checks around it')
    st = [('1 Anatomy', 'Published C0–C7 neck\nmodel, refined to\nC3–C4 segment'), ('2 Cage builder', '0.2 mm mesh; hard/soft\nmap kept, never\naveraged out'), ('3 Surgery and load', 'Spread, expand, release;\n100 N; six motions\nto 1.5 N·m'),
          ('4 Solver', 'FEBio 4.13 + patches;\nCPU or GPU linear\nsolver'), ('5 Measures', 'Slip, friction needed,\nsqueeze of soft part,\nbond shear'), ('6 Verdict', 'Limits decided by the\nPI, applied per design;\nmissing never = pass')]
    bw, gap = 27.6, 2.2; y = 52
    for i, (t, b) in enumerate(st):
        x = 2 + i * (bw + gap); box(ax, x, y, bw, 12.5, t, b, fs=4.9)
        if i < 5: arrow(ax, (x + bw + 0.1, y + 6.2), (x + bw + gap - 0.1, y + 6.2))
    y2 = 66.5
    ax.add_patch(FancyBboxPatch((2, y2), 176, 10.5, boxstyle='round,pad=0,rounding_size=0.8', fc='#f4f3f0', ec=INK2, lw=0.5, zorder=1))
    ax.text(3.2, y2 + 1.0, 'Around every run', fontsize=5.5, fontweight='bold', color=INK, va='top')
    A = [('Before', 'preflight compares each input\nwith current code and settings'), ('During', 'scheduler, watchdog and restart;\nstorage archived off the fast disk'), ('Numerical checks', 'mesh, time step, contact stiffness,\nGPU vs CPU on identical inputs'), ('After', 'automatic QA checks, independent\nauditor, decision log, data hashes')]
    for i, (t, b) in enumerate(A):
        x = 3.2 + i * 43.8
        ax.text(x, y2 + 3.5, t, fontsize=5, fontweight='bold', color=INK2, va='top'); ax.text(x, y2 + 5.5, b, fontsize=4.8, color=INK2, va='top', linespacing=1.08)
    # c agents
    y0 = 79.5
    label(ax, 2, y0, 'c', 'Multi-agent adversarial generation: independent AI roles that check one another')
    ax.plot([122, 126], [y0 + 2, y0 + 2], color=BLUE, lw=0.8); ax.text(127, y0 + 2, 'Has run', fontsize=5, va='center', color=INK2)
    ax.plot([140, 144], [y0 + 2, y0 + 2], color=MUTED, lw=0.8, ls=(0, (2.5, 1.5))); ax.text(145, y0 + 2, 'Designed, not started', fontsize=5, va='center', color=INK2)
    yt = y0 + 7; bh = 13.5
    R = [(2, 'Designer', 'proposes new shapes;\nscored only by designs\nthat survive', True), (32, 'Engine', 'builds and simulates;\nstores every result\nin an archive', True), (62, 'Verifier', 'blinded re-runs and\nreproducibility;\nPASS or HOLD', False), (92, 'Safety guard', 'blinded check against\nS1–S10 and anatomy;\ncan veto a design', False)]
    for i, (x, t, b, dsh) in enumerate(R):
        box(ax, x, yt, 26, bh, t, b, dashed=dsh, fs=4.9)
    arrow(ax, (28.1, yt + 6.5), (31.9, yt + 6.5), dashed=True); arrow(ax, (58.1, yt + 6.5), (61.9, yt + 6.5), dashed=True); arrow(ax, (88.1, yt + 6.5), (91.9, yt + 6.5))
    yb = yt + bh + 7.5
    box(ax, 47, yb, 41, 12, 'Red team', 'attacks every step; each finding needs\nevidence and two or three fixes', fc='#fbeef4', ec=RED, fs=4.9)
    box(ax, 92, yb, 26, 12, 'Integrator', 'answers each finding,\nfixes code, reports', fs=4.9)
    box(ax, 2, yb, 41, 12, 'Principal investigator', 'decides rules and limits; resolves what\ntwo rounds cannot settle', fc='#f4f3f0', ec=INK2, fs=4.9)
    for xa in (15, 45, 75, 105):
        tx = 67.5 + (xa - 60) * 0.35
        arrow(ax, (tx, yb - 0.1), (xa, yt + bh + 0.1), col=RED, lw=0.7, dashed=xa < 60)
    arrow(ax, (88.1, yb + 6), (91.9, yb + 6)); arrow(ax, (105, yt + bh + 0.1), (105, yb - 0.1)) if False else None
    arrow(ax, (92, yb + 9), (43.1, yb + 9), rad=0.0) if False else None
    arrow(ax, (47, yb + 6), (43.1, yb + 6), col=INK2) if False else None
    ax.annotate('', xy=(43.1, yb + 13.3), xytext=(105, yb + 12.1), arrowprops=dict(arrowstyle='-|>', lw=0.7, color=INK2, mutation_scale=5.5, connectionstyle='angle,angleA=-90,angleB=0,rad=0'), zorder=4) if False else None
    ax.plot([105, 105, 22.5], [yb + 12.1, yb + 14.0, yb + 14.0], color=INK2, lw=0.7, zorder=4); arrow(ax, (22.5, yb + 14.0), (22.5, yb + 12.1))
    ax.text(62, yb + 14.3, 'escalates decisions', fontsize=4.8, color=INK2, va='top', ha='center')
    # rules and status
    x = 122
    ax.text(x, yt, 'Rules that make it adversarial', fontsize=5.5, fontweight='bold', color=INK, va='top')
    rules = 'Each role is a separate AI process with its own\nprompt and private notes. No role approves\nits own work. Checkers never see the designer’s\nreasoning. Roles hand over checked JSON files.\nA HOLD stops results from moving forward.\nFindings count only when reproduced.'
    ax.text(x, yt + 2.5, rules, fontsize=4.9, color=INK2, va='top', linespacing=1.13)
    ax.text(x, yt + 18.2, 'Status today', fontsize=5.5, fontweight='bold', color=INK, va='top')
    status = f"Verifier, safety guard, red team: {nr} rounds, last on\n28 Oct; HOLD in all {nr}. {len(F)} findings ({sev['critical']} critical, {sev['major']}\nmajor, {sev['minor']} minor), none formally closed. HOLD is not\nyet enforced automatically. Designer and engine\nhave not started: no AI-generated design exists."
    ax.text(x, yt + 20.7, status, fontsize=4.9, color=INK, va='top', linespacing=1.13)
    # d funnel
    y0 = yb + 17.5
    label(ax, 2, y0, 'd', 'Filtering and confirming: cheap tests first, the strictest last')
    col = [('Candidates', 'human designs now;\nAI proposals planned', f'{total} human designs,\nchosen by active learning', False), ('L0 geometry', 'S1–S5 in\nmilliseconds', 'not coded yet; families\nbuilt to S1, S3\u2013S5', True), ('L1 fast screen', 'surrogate model; in-house\nGPU solver after gates', 'not used', True),
           ('L2 glued cage', 'FEBio, whole segment,\nabout 23 min each', f'{exc} excluded,\n{comp} crushed, {unf0} unfinished', False), ('Real friction', 'FEBio, hours each;\nslip-out verdict', f'{slip} slip too far,\n{fc} cannot finish', False), ('Bond and re-check', 'S10; verifier and\nsafety guard re-check', f'{shear} over the bond limit;\n{npass} remain', False), ('Bench tests', 'friction, stiffness, bond\nstrength on real parts', 'not done', True), ('PI decision', 'confirmed design\ngoes forward', 'none yet', True)]
    n = len(col); bw = 20.3; gp = 1.8; yy = y0 + 6.5
    ax.text(2, yy + 11.9, 'Today', fontsize=4.9, fontweight='bold', color=BLUE, va='top')
    for i, (t, b, today, dsh) in enumerate(col):
        x = 2 + i * (bw + gp); box(ax, x, yy, bw, 11, t, b, dashed=dsh, fs=4.6, tfs=5.2)
        if i < n - 1: arrow(ax, (x + bw + 0.05, yy + 5.5), (x + bw + gp - 0.05, yy + 5.5), dashed=dsh or col[i + 1][3])
        ax.text(x + bw / 2, yy + 14.2, today, ha='center', va='top', fontsize=4.6, color=INK2 if dsh else INK, linespacing=1.08)
    ax.text(2, yy + 20.3, 'Real-friction and bond verdicts are provisional. Each result records its code version and input hashes. The AI loop adds an append-only archive of every proposal.', fontsize=4.9, color=INK2, va='top')
    abbr = ('Abbreviations: C0–C7, C3, C4, neck vertebrae; d, spreading of the vertebrae at insertion; FEBio, Finite Elements for Biomechanics; GPU, CPU, graphics and central processors; HOLD, verdict that blocks a round; '
            'JSON, a structured data format; L0–L2, test levels of rising cost; MPa, megapascal; N, newton; N·m, newton-metre; PI, principal investigator; QA, quality assurance; S1–S10, design requirements.')
    import textwrap
    ax.text(2, yy + 23.2, '\n'.join(textwrap.wrap(abbr, 225)), fontsize=4.8, color=INK2, va='top', linespacing=1.12)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig4_methodology.{ext}', facecolor='white', **kw)
    plt.close(fig)
    print(nr, ver, sev, total, exc, comp, unf0, slip, fc, shear, npass, {k: (tally('TIED', k), tally('FRIC', k)) for k, _, _ in caps}, 'end', yy + 23.2)


if __name__ == '__main__':
    main()
