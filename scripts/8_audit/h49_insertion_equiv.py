"""Insertion-state equivalence (issue 2, DECISIONS 2026-11-09): is the t 3.5 pre-state of an alternative insertion process (pilot_relE:
all C3-pot reactions released statically, follower step static) the same as the production process (physio_fric3 / fric5 checkpoints)?
Compares, at the last logged state <= 3.5 of each run dir: cage centroid relative to the C4 endplate (x, y, z, mm), C3 pot pose
(x, y, z mm; thx, thy, thz deg) and C3 pot reactions (Fx..Mz) from C3pot.txt, and the cage rigid-body horizontal translation.
usage: python h49_insertion_equiv.py <run_dir_A> <run_dir_B> [more pairs ...]      (A = production, B = alternative)
       python h49_insertion_equiv.py <run_dir>                                      (print the state only)"""
import os, sys, json, numpy as np
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(os.path.dirname(_REPO), 'biocage-evo', p) for p in ('methods', 'common')]
import e04_dislocation as e4

def c3pot(d):
    T, out = None, {}
    for l in open(os.path.join(d, 'C3pot.txt')):
        if l.startswith('*Time'): T = float(l.split('=')[1])
        elif l[:1].isdigit() and ',' in l: out[T] = [float(x) for x in l.split(',')[1:]]
    return out

def state(d, t_target=3.5):
    cn = e4.read_log(os.path.join(d, 'cage_nodes.txt')); c4 = e4.read_log(os.path.join(d, 'C4_endplate_nodes.txt')); C = c3pot(d)
    ts = [t for t in sorted(cn) if t <= t_target + 1e-6]; t = ts[-1]
    u = np.array(list(e4.nearest(cn, t)[0].values())).mean(0) - np.array(list(e4.nearest(c4, t)[0].values())).mean(0)
    tc = max(x for x in C if x <= t_target + 1e-6); r = C[tc]
    return dict(dir=os.path.relpath(d), t=round(t, 4), cage_rel_C4_mm=[round(float(v), 4) for v in u], cage_horiz_mm=round(float(np.hypot(u[0], u[1])), 4),
                C3_pos_mm=[round(v, 4) for v in r[0:3]], C3_rot_deg=[round(float(np.degrees(v)), 3) for v in r[3:6]], C3_reactions=[round(v, 2) for v in r[6:12]])

def compare(a, b):
    A, B = state(a), state(b)
    d = dict(A=A, B=B, d_cage_rel_C4_mm=[round(y - x, 4) for x, y in zip(A['cage_rel_C4_mm'], B['cage_rel_C4_mm'])],
             d_cage_horiz_mm=round(B['cage_horiz_mm'] - A['cage_horiz_mm'], 4), d_C3_pos_mm=[round(y - x, 4) for x, y in zip(A['C3_pos_mm'], B['C3_pos_mm'])],
             d_C3_rot_deg=[round(y - x, 3) for x, y in zip(A['C3_rot_deg'], B['C3_rot_deg'])])
    return d

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1: print(json.dumps(state(args[0]), indent=1))
    else:
        for a, b in zip(args[::2], args[1::2]): print(json.dumps(compare(a, b), indent=1))
