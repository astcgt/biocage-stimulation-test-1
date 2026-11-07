#!/usr/bin/env python3
"""h44: Nature-style 4:3 figure of the multi-agent adversarial loop: who hands what to whom, who challenges whom, who decides.
Edges come from biocage-evo/docs/GOVERNANCE.md and roles/prompts; the status line is computed from the findings and verdict files.
usage: python h44_multiagent_loop_fig.py    outputs in human_study/figures/main_results/
"""
import os, json, glob, collections, textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HS = f'{ROOT}/human_study'; EVO = f'{os.path.dirname(ROOT)}/biocage-evo'; OUT = f'{HS}/figures/main_results'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8982'
BLUE, PALE, RED, PINK, GREY = '#2c5f9e', '#eaf0f7', '#c2427a', '#fbeef4', '#f4f3f0'
W, H = 180, 135; MM = 1 / 25.4
BW, BH = 38, 14
CX = {1: 28, 2: 90, 3: 152}; CY = {1: 20, 2: 55, 3: 90}
DASH = (0, (2.5, 1.5))


def main():
    plt.rcParams.update({'font.family': ['Lato', 'DejaVu Sans'], 'pdf.fonttype': 42})
    F = [json.load(open(f)) for f in glob.glob(f'{EVO}/work/findings/F-*.json')]; sev = collections.Counter(x['severity'] for x in F)
    ver = [json.load(open(f))['verdict'] for f in sorted(glob.glob(f'{EVO}/work/board/r*/verifier.json'))]; assert set(ver) == {'HOLD'}
    fig = plt.figure(figsize=(W * MM, H * MM), facecolor='white'); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')

    def pos(c, r): return CX[c], CY[r]
    def edge(c, r, side):
        x, y = pos(c, r); dx, dy = BW / 2, BH / 2
        return {'l': (x - dx, y), 'r': (x + dx, y), 't': (x, y - dy), 'b': (x, y + dy), 'tl': (x - dx, y - dy), 'tr': (x + dx, y - dy), 'bl': (x - dx, y + dy), 'br': (x + dx, y + dy)}[side]

    def box(c, r, title, body, kind, dashed=False, tag=None):
        x, y = pos(c, r); fc, ec = {'flow': (PALE, BLUE), 'red': (PINK, RED), 'gov': (GREY, INK2)}[kind]
        ax.add_patch(FancyBboxPatch((x - BW / 2, y - BH / 2), BW, BH, boxstyle='round,pad=0,rounding_size=0.9', fc='white' if dashed else fc, ec=MUTED if dashed else ec, lw=0.7, ls=DASH if dashed else '-', zorder=3))
        ax.text(x, y - BH / 2 + 1.0, title, ha='center', va='top', fontsize=5.8, fontweight='bold', color=INK2 if dashed else INK, zorder=4)
        ax.text(x, y - BH / 2 + 3.9, '\n'.join(textwrap.wrap(body, 36)), ha='center', va='top', fontsize=4.5, color=INK2, linespacing=1.12, zorder=4)
        if tag: ax.text(x + BW / 2 - 1.0, y - BH / 2 + 1.1, tag, ha='right', va='top', fontsize=4.3, color=MUTED if dashed else ec, fontstyle='italic', zorder=4)

    def arrow(a, b, kind, dashed=False, bi=False, rad=0.0):
        col = {'flow': BLUE, 'red': RED, 'gov': INK2}[kind]
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<|-|>' if bi else '-|>', mutation_scale=5.5, lw=0.85, color=MUTED if dashed else col, ls=DASH if dashed else '-', shrinkA=0, shrinkB=0, zorder=2, connectionstyle=f'arc3,rad={rad}'))

    def label(x, y, s, ha='center', va='center', col=INK2):
        ax.text(x, y, s, ha=ha, va=va, fontsize=4.4, color=col, linespacing=1.1, zorder=6, bbox=dict(fc='white', ec='none', pad=0.35, alpha=0.92))

    def badge(x, y, n, col=BLUE):
        ax.add_patch(Circle((x, y), 1.7, fc=col, ec='white', lw=0.4, zorder=7)); ax.text(x, y + 0.05, str(n), ha='center', va='center', fontsize=4.6, color='white', fontweight='bold', zorder=8)

    ax.text(3, 2.2, 'Multi-agent adversarial loop: who hands work to whom, who challenges whom, who decides', fontsize=6.8, fontweight='bold', va='top', color=INK)
    # boxes
    box(1, 1, 'Designer', 'proposes new shapes; sees only a short round digest; scored by designs that survive', 'flow', True, 'not started')
    box(2, 1, 'Engine', 'evolution loop and design archive; today only the human-design pipeline runs', 'flow', True, 'not started')
    box(3, 1, 'Verifier', 'blinded re-runs with fixed seeds; checks code versions and gates; PASS or HOLD', 'flow', False, '3 rounds')
    box(3, 2, 'Safety guard', 'blinded check of each promoted design against S1–S10 and anatomy; can veto a design', 'flow', False, '3 rounds')
    box(2, 2, 'Red team', 'attacks every step; a finding needs evidence and 2–3 fixes; scored by findings others reproduce', 'red', False, '3 rounds')
    box(2, 3, 'Integrator', 'owns code, solver and archive; answers every finding: fix, reject with reason, or escalate', 'flow', False)
    box(3, 3, 'Principal investigator', 'sets rules and limits; settles what two rounds cannot', 'gov', False)
    box(1, 2, 'QA auditor', 'outside the loop: automatic checks plus an auditor agent compare code and labels with PI decisions', 'gov', False)
    box(1, 3, 'Foreman', 'operations agent, hourly: keeps GPUs busy and restarts jobs; may not touch science', 'gov', False)
    # round flow
    arrow(edge(1, 1, 'r'), edge(2, 1, 'l'), 'flow', True); badge(52, 20, 1); label(59, 15.5, 'up to 10 proposals')
    arrow(edge(2, 1, 'r'), edge(3, 1, 'l'), 'flow', True); badge(114, 20, 2); label(121, 15.5, 'results + provenance')
    arrow(edge(3, 1, 'b'), edge(3, 2, 't'), 'flow'); badge(152, 31.5, 3); label(156, 38, 'gate: PASS or HOLD', ha='left')
    arrow(edge(3, 2, 'bl'), edge(2, 3, 'tr'), 'flow'); badge(130.5, 68, 4); label(131, 75.5, 'verdict, veto,\nchange requests', ha='left')
    # red team challenges
    arrow(edge(2, 2, 'tl'), edge(1, 1, 'br'), 'red', True); label(57, 38, 'exploits of the fast model', ha='right')
    arrow(edge(2, 2, 't'), edge(2, 1, 'b'), 'red', True); label(92, 37.5, 'solver gaps, data mix-ups', ha='left')
    arrow(edge(2, 2, 'tr'), edge(3, 1, 'bl'), 'red', False, True); label(118, 43.5, 'plants canaries /\nreproduces findings', ha='left')
    arrow(edge(2, 2, 'r'), edge(3, 2, 'l'), 'red'); label(121, 51.5, 'missed checks, loopholes')
    arrow(edge(2, 2, 'b'), edge(2, 3, 't'), 'red', False, True); label(92, 72.5, 'findings / fix or reject, with reasons', ha='left')
    badge(78, 49.5, 5, RED)
    # governance
    arrow(edge(3, 2, 'b'), edge(3, 3, 't'), 'gov', False, True); label(154, 72.5, 'rule-change proposals /\napproval', ha='left')
    arrow(edge(2, 3, 'r'), edge(3, 3, 'l'), 'gov', False, True); label(121, 85, 'escalates / decides')
    arrow(edge(1, 3, 'r'), edge(2, 3, 'l'), 'gov'); label(59, 85, 'status, restarts')
    arrow(edge(1, 2, 'br'), edge(2, 3, 'tl'), 'gov', False, True); label(52, 72.5, 'code and labels vs PI\ndecisions / mismatch list', ha='right')
    # loop closure
    x0, y0 = pos(2, 3); y_bot = y0 + BH / 2
    ax.plot([x0, x0, 3], [y_bot, 103, 103], color=MUTED, lw=0.85, ls=DASH, zorder=2); ax.plot([3, 3], [103, 20], color=MUTED, lw=0.85, ls=DASH, zorder=2)
    arrow((3, 20), (CX[1] - BW / 2, 20), 'flow', True)
    badge(x0, 100.0, 6); label(x0 - 3, 100.1, 'round digest to the Designer; the next round starts only if neither Verifier nor Safety guard is on HOLD', ha='right')
    # legend and status
    y = 109
    ax.add_patch(FancyBboxPatch((3, y - 1.4), 8, 3.4, boxstyle='round,pad=0,rounding_size=0.6', fc=PALE, ec=BLUE, lw=0.7)); ax.text(13, y + 0.3, 'has run', fontsize=4.7, va='center', color=INK2)
    ax.add_patch(FancyBboxPatch((28, y - 1.4), 8, 3.4, boxstyle='round,pad=0,rounding_size=0.6', fc='white', ec=MUTED, lw=0.7, ls=DASH)); ax.text(38, y + 0.3, 'designed, not started', fontsize=4.7, va='center', color=INK2)
    for x, col, t in ((72, BLUE, 'round flow, numbered 1–6'), (108, RED, 'challenge by the red team'), (142, INK2, 'governance and operations')):
        ax.add_patch(FancyArrowPatch((x, y + 0.3), (x + 7, y + 0.3), arrowstyle='-|>', mutation_scale=5, lw=0.85, color=col)); ax.text(x + 9, y + 0.3, t, fontsize=4.7, va='center', color=INK2)
    status = (f"Status today. Verifier, safety guard and red team have run {len(ver)} rounds (26–28 Oct 2026); the verifier said HOLD every time. They reviewed the solver and methods, not yet any design. "
              f"{len(F)} findings ({sev['critical']} critical, {sev['major']} major, {sev['minor']} minor), none formally closed; HOLD is not yet enforced by software. Designer and engine have not started, so no AI-generated design exists.")
    ax.text(3, 114.2, '\n'.join(textwrap.wrap(status, 195)), fontsize=4.7, va='top', color=INK, linespacing=1.15)
    abbr = ('Abbreviations: S1–S10, the design requirements (stays in disc space, insertable, one part, room for the disc, printable, load capacity, height, bone protection, no slip-out, bond strength); PI, principal investigator; QA, quality assurance; '
            'GPU, graphics processing unit; HOLD, verdict that stops the round; blinded, without sight of the designer’s reasoning; fast model, quick approximate simulation for screening, not built yet; canary, a result planted to test the verifier; '
            'change request, a written request to the owner of code or rules, passed on by the integrator.')
    ax.text(3, 124.2, '\n'.join(textwrap.wrap(abbr, 215)), fontsize=4.5, va='top', color=INK2, linespacing=1.12)
    for ext, kw in (('pdf', {}), ('svg', {}), ('png', dict(dpi=600))):
        fig.savefig(f'{OUT}/fig5_multiagent_loop.{ext}', facecolor='white', **kw)
    plt.close(fig); print(len(ver), len(F), dict(sev))


if __name__ == '__main__':
    main()
