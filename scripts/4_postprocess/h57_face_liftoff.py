"""Face lift-off of the cage in a finished physiological window (2026-11-20, for the 彈勾 review): how much of the cage top
(C3) and bottom (C4) bearing face carries no normal traction at the window peak, by anterior / middle / posterior third.
Why: a pre-compressed finger can only add holding force where the bearing face has lifted off (its preload is otherwise an
internal force between cage and endplate); the finger stroke worth designing for equals the lift-off gap.
Method: as e02_friction_limit (evo repo) - per top / bottom face element the normal traction from the element stress at the
window states (contact pressure is not logged per element); 'lifted' = compressive normal traction < P_MIN (0.01 MPa, the
follower load 100 N over the 37 mm2 face is ~2.7 MPa). Gap proxy: the normal traction is 0 where the face has lifted, so the
geometric gap is read from node displacements of the top face corners (cage_nodes.txt) relative to the window start.
Usage: python3 h57_face_liftoff.py RUN_DIR/w_extension [RUN_DIR/w_flexion ...]  -> prints one row per window, json next to it.
"""
import sys, os, json, numpy as np, xml.etree.ElementTree as ET
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(P), 'biocage-evo', 'common'))
import xplt
P_MIN = 0.01


def faces_of(cd):
    root = ET.parse(os.path.join(cd, 'case.feb')).getroot(); g = root.find('Geometry')
    X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
    blocks = [(eb.get('name'), np.array([[int(v) for v in e.text.split(',')] for e in eb])) for eb in g.findall('Elements')]
    dom = {n: i for i, (n, E) in enumerate(blocks)}; conn = dict(blocks)
    ce = np.load(os.path.join(cd, 'cage_elems.npz')); K = int(ce['K'])
    faces, pos = [], {}
    for b, lay in zip(ce['block'], ce['layer']):
        pos[b] = pos.get(b, -1) + 1
        if 'biodisc' in b or lay not in (0, K - 1): continue
        h = conn[b][pos[b]]; q = h[4:8] if lay == K - 1 else h[0:4]
        Pq = np.array([X[i] for i in q]); nrm = np.cross(Pq[2] - Pq[0], Pq[3] - Pq[1]); A = 0.5 * np.linalg.norm(nrm); nrm /= 2 * A
        sgn = 1.0 if lay == K - 1 else -1.0
        if nrm[2] * sgn < 0: nrm = -nrm
        faces.append((dom[b], pos[b], 'top' if lay == K - 1 else 'bot', nrm, A, Pq.mean(0)))
    return faces


def main(cd):
    faces = faces_of(cd); pf = xplt.read(os.path.join(cd, 'case.xplt')); states = pf['states']
    sch = json.load(open(os.path.join(cd, 'physio_schedule.json'))); w = sch['windows'][0]
    xs = np.array([c[0] for *_, c in faces]); x_lo, x_hi = np.percentile(xs, [33, 67])
    band = lambda x: 'post' if x < x_lo else ('mid' if x < x_hi else 'ant')     # x = anterior (+)
    out = dict(window=w['name'], dir=os.path.relpath(cd, P), P_MIN=P_MIN, states={})
    for st in states:
        tt = st['time']
        if not (w['t0'] - 1e-6 <= tt <= w['t1'] + 1e-6): continue
        S = st['elem'].get('stress', {}); acc = {}
        for di, i, side, n, A, c in faces:
            Sg = S.get(di + 1)
            if Sg is None: continue
            s6 = Sg[i]; sig = np.array([[s6[0], s6[3], s6[5]], [s6[3], s6[1], s6[4]], [s6[5], s6[4], s6[2]]])
            pn = max(-float(n @ (sig @ n)), 0.0)
            a = acc.setdefault((side, band(c[0])), [0.0, 0.0, 0.0]); a[0] += A; a[1] += A * (pn < P_MIN); a[2] += pn * A
        row = {}
        for (side, b), (A, Al, F) in acc.items(): row[f'{side}_{b}'] = dict(area=round(A, 2), lifted_frac=round(Al / A, 3), force_N=round(F, 2))
        for side in ('top', 'bot'):
            A = sum(v[0] for k, v in acc.items() if k[0] == side); Al = sum(v[1] for k, v in acc.items() if k[0] == side); F = sum(v[2] for k, v in acc.items() if k[0] == side)
            row[f'{side}_all'] = dict(area=round(A, 2), lifted_frac=round(Al / A, 3), force_N=round(F, 2))
        out['states'][f'{tt:.4f}'] = row
    keys = sorted(out['states'], key=float); first, last = out['states'][keys[0]], out['states'][keys[-1]]
    out['summary'] = {k: dict(start=first[k]['lifted_frac'], peak=last[k]['lifted_frac'], force_start=first[k]['force_N'], force_peak=last[k]['force_N']) for k in last}
    json.dump(out, open(os.path.join(cd, 'face_liftoff.json'), 'w'), indent=1)
    s = out['summary']
    print(f"{os.path.relpath(cd, P):55s} {w['name']:9s} lifted area fraction at peak (start): top ant {s['top_ant']['peak']:.2f} ({s['top_ant']['start']:.2f}) mid {s['top_mid']['peak']:.2f} post {s['top_post']['peak']:.2f} | "
          f"bot ant {s['bot_ant']['peak']:.2f} ({s['bot_ant']['start']:.2f}) mid {s['bot_mid']['peak']:.2f} post {s['bot_post']['peak']:.2f} | face force N top {s['top_all']['force_peak']:.0f} bot {s['bot_all']['force_peak']:.0f}")


if __name__ == '__main__':
    for cd in sys.argv[1:]: main(cd)
