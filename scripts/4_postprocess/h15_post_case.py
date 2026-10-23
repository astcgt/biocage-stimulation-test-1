"""Post-process one BIOCAGE case run (h14). Time windows: 0-1 distract, 1-2 seat, 2-3 release, 3- test.

Outputs (summary.json): distraction force, clamp force after release (cage-endplate contact force), and per test:
  compress : force-displacement of the C3 pot along the disc normal from the post-release state, and the four endpoints
             (a) cage damaged volume > 15 % (also 10 / 20 %): element von Mises > local strength or max principal stress >
                 0.8 x local strength (FDM inter-layer); post-processing only;
             (b) bone: trabecular elements within 3 mm below the cage footprint (C3 and C4) yielded if min principal
                 Lagrange strain < -0.75 % or max > +0.70 %; onset when yielded volume > 10 %;
             (c) height loss > d;  (d) peak force.   capacity = force at the first endpoint reached.
  iso / push_* : cage slip relative to C4 (in-plane displacement of the cage contact nodes minus the rigid-body motion of
             the C4 endplate nodes), clamp, push-out force (sum of prescribed-node reactions).
usage: python h15_post_case.py <case_dir>
"""
import sys, os, json, numpy as np, xml.etree.ElementTree as ET
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
import xplt
from cage_geom import Endplates
import shapely.geometry as sg
from shapely import vectorized

cd = sys.argv[1]; case = json.load(open(os.path.join(cd, 'case.json'))); prm = case['params']; test = prm['test']; d = prm['d']
T_REL, T_TEST = 3.0, 3.0


def read_log(name):
    out, t = [], None
    for line in open(os.path.join(cd, name)):
        if line.startswith('*Time'): t = float(line.split('=')[1])
        elif line[:1].isdigit(): out.append([t] + [float(v) for v in line.split(',')])
    return np.array(out)


rb = read_log('C3pot.txt')          # t, id, x, y, z, thx, thy, thz, Fx, Fy, Fz, Mx, My, Mz
t, z, Fz = rb[:, 0], rb[:, 4], rb[:, 10]
k1 = np.argmin(abs(t - 1.0))
res = dict(test=test, d=d, completed_time=float(t[-1]), distraction_force_N=float(Fz[k1]))

# --- geometry for volumes / regions from the .feb (frame coordinates)
root = ET.parse(os.path.join(cd, 'case.feb')).getroot(); g = root.find('Geometry')
X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
blocks = [(eb.get('name'), eb.get('mat'), np.array([[int(v) for v in e.text.split(',')] for e in eb])) for eb in g.findall('Elements')]
pf = xplt.read(os.path.join(cd, 'case.xplt'))
states = pf['states']; st_t = np.array([s['time'] for s in states])
sid = {n: k for k, n in pf['surfaces'].items()}
def clamp_at(k):
    cf = states[k]['face'].get('contact force', {})
    return {s: float(np.linalg.norm(cf[sid[s]])) for s in ('cage_top', 'cage_bot') if sid.get(s) in cf}
# cage axial force from element stresses: sum of sigma_zz x area over the mid-height layer (cage + biodisc)
ce = np.load(os.path.join(cd, 'cage_elems.npz')); dom_index = {n: i for i, (n, m, E) in enumerate(blocks)}
mid_layer = int(ce['K']) // 2
def cage_axial(k):
    s = states[k]['elem'].get('stress', {}); Fz_c, pos = 0.0, {}
    for b, lay, a in zip(ce['block'], ce['layer'], ce['area']):
        pos[b] = pos.get(b, -1) + 1
        if lay != mid_layer: continue
        S = s.get(dom_index[b] + 1)
        if S is not None: Fz_c += -S[pos[b], 2] * a
    return Fz_c
# PI 2026-10-20: capacity endpoint (e) = contact-layer crush - the cage elements touching the endplates (first / last element
# layer, biodisc excluded) with minimum principal Lagrange strain < -30 %; capacity when >= 50 % of them are crushed
CRUSH_STRAIN, CRUSH_FRAC = -0.30, 0.50
SLIP_LIMIT_MM = 1.0          # Q51 (PI 2026-10-21): validation dislocation threshold (was 2 mm, Q13)
K_lay = int(ce['K'])
def contact_crush(k):
    E_ = states[k]['elem'].get('Lagrange strain', {}); n_tot, n_cr, pos = 0, 0, {}
    for b, lay in zip(ce['block'], ce['layer']):
        pos[b] = pos.get(b, -1) + 1
        if 'biodisc' in b or lay not in (0, K_lay - 1): continue
        Eg = E_.get(dom_index[b] + 1)
        if Eg is None: continue
        e = Eg[pos[b]]; M = np.array([[e[0], e[3], e[5]], [e[3], e[1], e[4]], [e[5], e[4], e[2]]])
        n_tot += 1; n_cr += np.linalg.eigvalsh(M)[0] < CRUSH_STRAIN
    return n_cr / max(n_tot, 1)
# Q47 friction demand (bonded screening interface): contact-layer elements, outward face normal from the element's top / bottom
# nodes (reference configuration), traction t = sigma n (element-average Cauchy stress); sigma_n < 0 compressive
TIED = prm.get('contact_type') == 'tied'; MU = float(prm.get('mu_true', prm.get('mu', 0.35)) or 0.35)
conn_of = {n: E for (n, m, E) in blocks}
def _face_geom():
    out, pos = [], {}
    for b, lay in zip(ce['block'], ce['layer']):
        pos[b] = pos.get(b, -1) + 1
        if 'biodisc' in b or lay not in (0, K_lay - 1): continue
        h = conn_of[b][pos[b]]; q = h[4:8] if lay == K_lay - 1 else h[0:4]
        P = np.array([X[i] for i in q]); nrm = np.cross(P[2] - P[0], P[3] - P[1]); A = 0.5 * np.linalg.norm(nrm); nrm /= 2 * A
        sgn = 1.0 if lay == K_lay - 1 else -1.0
        if nrm[2] * sgn < 0: nrm = -nrm
        out.append((b, pos[b], 'top' if lay == K_lay - 1 else 'bot', nrm, A, P.mean(0)))
    return out
FACES = _face_geom() if TIED else []
def friction_demand(k):
    S_ = states[k]['elem'].get('stress', {}); acc = {}
    for b, i, side, n, A, c in FACES:
        Sg = S_.get(dom_index[b] + 1)
        if Sg is None: continue
        s6 = Sg[i]; sig = np.array([[s6[0], s6[3], s6[5]], [s6[3], s6[1], s6[4]], [s6[5], s6[4], s6[2]]])
        tvec = sig @ n; sn = float(n @ tvec); tau = tvec - sn * n
        a = acc.setdefault(side, dict(A=0.0, slipA=0.0, tensA=0.0, N=0.0, T=np.zeros(3), Ns=0.0, M=np.zeros(2), C=np.zeros(2), XY=[]))
        a['A'] += A; a['N'] += max(-sn, 0.0) * A; a['T'] += tau * A
        a['Ns'] += -sn * A; a['M'] += -sn * A * c[:2]; a['C'] += A * c[:2]; a['XY'].append(c[:2])
        if sn >= 0: a['tensA'] += A; a['slipA'] += A
        elif np.linalg.norm(tau) > MU * (-sn): a['slipA'] += A
    out = {}
    for sd, a in acc.items():
        # tipping indicator: centre of pressure (CoP) of the net (signed) normal force relative to the face centroid, as a fraction
        # of the face half-extent in that direction (>= 1: CoP at / beyond the edge -> the cage would rotate / lift off)
        cen = a['C'] / a['A']; xy = np.array(a['XY']) - cen
        cop = a['M'] / a['Ns'] - cen if a['Ns'] > 1e-9 else np.array([np.inf, np.inf])
        d_ = np.linalg.norm(cop); u = cop / d_ if np.isfinite(d_) and d_ > 0 else np.array([1.0, 0.0])
        ecc = d_ / max((xy @ u).max(), 1e-9) if np.isfinite(d_) else np.inf
        out[sd] = dict(excess_shear_N=float(np.linalg.norm(a['T']) - MU * a['N']),   # > 0: friction cannot hold, drives slip
                       slip_area_frac=a['slipA'] / a['A'], tension_area_frac=a['tensA'] / a['A'],
                       safety_factor=(MU * a['N'] / max(np.linalg.norm(a['T']), 1e-12)), normal_N=a['N'],
                       shear_N=float(np.linalg.norm(a['T'])), cop_eccentricity=float(ecc))
    return out
kr = int(np.argmin(abs(st_t - T_REL)))
res['clamp_after_release_N'] = float(cage_axial(kr)) if st_t[-1] >= T_REL - 1e-6 else None
res['retained_distraction_mm'] = float(z[np.argmin(abs(t - T_REL))]) if t[-1] >= T_REL - 1e-6 else None
res['contact_layer_crush_after_release'] = float(contact_crush(kr)) if st_t[-1] >= T_REL - 1e-6 else None
if TIED:
    fd = [dict(t=float(st_t[k]), **{f'{sd}_{kk}': v for sd, dd in friction_demand(k).items() for kk, v in dd.items()})
          for k in range(len(states)) if st_t[k] >= T_REL - 1e-6]
    res['friction_demand'] = fd
    if fd:
        sf = [min(r.get('top_safety_factor', 1e9), r.get('bot_safety_factor', 1e9)) for r in fd]
        sl = [max(r.get('top_slip_area_frac', 0), r.get('bot_slip_area_frac', 0)) for r in fd]
        res['friction_demand_after_release'] = {kk: v for kk, v in fd[0].items() if kk != 't'}
        res['min_safety_factor'] = float(min(sf)); res['t_min_safety_factor'] = fd[int(np.argmin(sf))]['t']
        res['max_slip_area_frac'] = float(max(sl)); res['mu_used'] = MU
        ec = [max(r.get('top_cop_eccentricity', 0), r.get('bot_cop_eccentricity', 0)) for r in fd]
        ta = [max(r.get('top_tension_area_frac', 0), r.get('bot_tension_area_frac', 0)) for r in fd]
        res['max_cop_eccentricity'] = float(max(ec)); res['max_tension_area_frac'] = float(max(ta))
        ex = [max(r.get('top_excess_shear_N', -1e9), r.get('bot_excess_shear_N', -1e9)) for r in fd]
        res['max_excess_shear_N'] = float(max(ex))                                   # slip intensity (driving force beyond friction)
        # fraction of the test time with SF < 1 (time-weighted over the stored states of the test step)
        tt = np.array([r['t'] for r in fd]); sfa = np.array(sf)
        if len(tt) > 1:
            dtt = np.diff(tt); res['slip_time_frac'] = float(((sfa[1:] < 1) * dtt).sum() / dtt.sum())

def tet_vol(P): return abs(np.einsum('ij,ij->i', P[:, 1] - P[:, 0], np.cross(P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]))) / 6
def hex_vol(P):
    tets = [(0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7)]
    return sum(tet_vol(P[:, list(tt)]) for tt in tets)

if test == 'compress' and st_t[-1] > T_TEST:
    mats = case['materials']
    cage_dom = [i for i, (n, m, E) in enumerate(blocks) if n.startswith('cage_') and 'biodisc' not in n]
    vol = {i: hex_vol(np.array([[X[j] for j in e] for e in blocks[i][2]])) for i in cage_dom}
    Vc = sum(v.sum() for v in vol.values())
    # trabecular bone within 3 mm below the cage footprint
    ep = Endplates(prm['fsu'], prm['frame']); fp = ep.footprint
    bone = {}
    for i, (n, m, E) in enumerate(blocks):
        if n in ('C3_trabecular', 'C4_trabecular'):
            C = np.array([np.mean([X[j] for j in e], 0) for e in E])
            ref = ep.z_top(C[:, 0], C[:, 1]) if n.startswith('C3') else ep.z_bot(C[:, 0], C[:, 1])
            dz = (C[:, 2] - ref) if n.startswith('C3') else (ref - C[:, 2])
            sel = vectorized.contains(fp, C[:, 0], C[:, 1]) & (dz >= -0.5) & (dz <= 3.0)
            bone[i] = (sel, tet_vol(np.array([[X[j] for j in e] for e in E])))
    curve = []
    for k in np.where(st_t >= T_TEST - 1e-6)[0]:
        s = states[k]; kk = int(np.argmin(abs(t - st_t[k])))
        dmg_v = 0.0
        for i in cage_dom:
            S = s['elem']['stress'][i + 1]
            sx, sy, sz, sxy, syz, sxz = S.T
            vm = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + sxz ** 2))
            M = np.array([[sx, sxy, sxz], [sxy, sy, syz], [sxz, syz, sz]]).transpose(2, 0, 1)
            s1 = np.linalg.eigvalsh(M)[:, -1]
            strength = mats[blocks[i][1]]['strength']
            dmg = (vm > strength) | (s1 > 0.8 * strength)
            dmg_v += vol[i][dmg].sum()
        yv, tv = 0.0, 0.0
        for i, (sel, v) in bone.items():
            Eg = s['elem']['Lagrange strain'][i + 1][sel]
            M = np.array([[Eg[:, 0], Eg[:, 3], Eg[:, 5]], [Eg[:, 3], Eg[:, 1], Eg[:, 4]], [Eg[:, 5], Eg[:, 4], Eg[:, 2]]]).transpose(2, 0, 1)
            ev = np.linalg.eigvalsh(M)
            y = (ev[:, 0] < -0.0075) | (ev[:, -1] > 0.0070)
            yv += v[sel][y].sum(); tv += v[sel].sum()
        curve.append(dict(t=float(st_t[k]), disp_mm=float(z[kk] - z[np.argmin(abs(t - T_TEST))]), F_N=float(-Fz[kk]),
                          cage_damage_frac=float(dmg_v / Vc), bone_yield_frac=float(yv / max(tv, 1e-9)),
                          cage_axial_N=float(cage_axial(k)), contact_layer_crush_frac=float(contact_crush(k))))
    F = np.array([c['F_N'] for c in curve]); disp = np.array([c['disp_mm'] for c in curve])
    dmg = np.array([c['cage_damage_frac'] for c in curve]); byd = np.array([c['bone_yield_frac'] for c in curve])
    crush = np.array([c['contact_layer_crush_frac'] for c in curve])
    first = lambda m: int(np.argmax(m)) if m.any() else None
    ev = {'a_cage_damage_15pct': first(dmg > 0.15), 'b_bone_yield_10pct': first(byd > 0.10),
          'c_height_loss_gt_d': first(-disp > d), 'e_contact_layer_crush_50pct': first(crush >= CRUSH_FRAC), 'd_peak_force': (int(np.argmax(F)) if np.argmax(F) < len(F) - 1 else None)}
    hit = {k: v for k, v in ev.items() if v is not None}
    mode = min(hit, key=hit.get) if hit else None
    # Q40: run ended before any endpoint -> lower bound + functional-failure annotation (state and time at the last converged state)
    ended_early = 'E R R O R' in open(os.path.join(cd, 'case.log'), errors='ignore').read()
    func = None
    if mode is None and ended_early and len(curve):
        k = int(np.where(st_t >= T_TEST - 1e-6)[0][-1]); s = states[k]; worst = (0.0, None)
        for i in cage_dom + [j for j, (n, m, E) in enumerate(blocks) if 'biodisc' in n]:
            Eg = s['elem'].get('Lagrange strain', {}).get(i + 1)
            if Eg is None: continue
            M = np.array([[Eg[:, 0], Eg[:, 3], Eg[:, 5]], [Eg[:, 3], Eg[:, 1], Eg[:, 4]], [Eg[:, 5], Eg[:, 4], Eg[:, 2]]]).transpose(2, 0, 1)
            e1 = np.linalg.eigvalsh(M)[:, 0].min()
            if e1 < worst[0]: worst = (float(e1), blocks[i][0])
        func = dict(type='functional failure (solver stopped before any endpoint)', time=float(st_t[k]), disp_mm=float(disp[-1]),
                    F_N=float(F[-1]), height_loss_mm=float(-disp[-1]), peak_compressive_strain=worst[0], where=worst[1])
    res.update(capacity_lower_bound_N=(float(F.max()) if func else None), functional_failure=func)
    res.update(curve=curve, endpoints={k: (None if v is None else dict(F_N=float(F[v]), disp_mm=float(disp[v]))) for k, v in ev.items()},
               damage_10pct=None if first(dmg > 0.10) is None else float(F[first(dmg > 0.10)]),
               damage_20pct=None if first(dmg > 0.20) is None else float(F[first(dmg > 0.20)]),
               capacity_N=None if mode is None else float(F[hit[mode]]), failure_mode=mode,
               max_force_N=float(F.max()), stiffness_N_per_mm=float(np.polyfit(-disp[:5], F[:5], 1)[0]) if len(F) > 5 else None)
def kabsch_T(A, B):
    ca, cb = A.mean(0), B.mean(0); U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    R = Vt.T @ np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T
    return R, cb - R @ ca

def slip_history():
    """In-plane (X-Y) displacement of the cage contact nodes relative to the rigid motion of the C4 endplate."""
    cn = read_log('cage_nodes.txt'); c4 = read_log('C4_endplate_nodes.txt')
    times = np.unique(cn[:, 0]); out = []
    for tt in times:
        a = cn[cn[:, 0] == tt]; b = c4[c4[:, 0] == tt]
        Xa = np.array([X[int(i)] for i in a[:, 1]]); Xb = np.array([X[int(i)] for i in b[:, 1]])
        R, T = kabsch_T(Xb, Xb + b[:, 2:5])
        rel = (Xa + a[:, 2:5]) - (Xa @ R.T + T)              # cage motion not explained by C4's rigid motion
        v = rel.mean(0); out.append([tt, v[0], v[1], v[2], float(np.hypot(v[0], v[1]))])
    return np.array(out)

if test in ('iso', 'physio', 'push_ant', 'push_post') and t[-1] > T_TEST:
    sh = slip_history(); s0 = sh[np.argmin(abs(sh[:, 0] - T_TEST))]
    rel = sh.copy(); rel[:, 1:4] -= s0[1:4]; rel[:, 4] = np.hypot(rel[:, 1], rel[:, 2])
    res['slip_after_insertion_mm'] = float(s0[4])
    res['slip_history'] = rel[rel[:, 0] >= T_TEST].round(5).tolist()
if test == 'iso' and t[-1] > T_TEST:
    sch = json.load(open(os.path.join(cd, 'iso_schedule.json'))); ncyc = sch['cycles']
    per_level = []
    for L, ts in zip(sch['levels'], sch['t_level_start']):
        cyc = []
        for c in range(ncyc):
            m = (rel[:, 0] >= ts + c - 1e-6) & (rel[:, 0] <= ts + c + 1 + 1e-6)
            if m.any(): cyc.append(dict(max_slip_mm=float(rel[m, 4].max()), end_slip_mm=float(rel[m, 4][-1]),
                                        complete=bool(rel[m, 0].max() >= ts + c + 1 - 1e-3)))
        ratchet = (cyc[2]['end_slip_mm'] - cyc[1]['end_slip_mm']) if len(cyc) >= 3 and cyc[2]['complete'] else None
        per_level.append(dict(level=L, cycles=cyc, ratchet_mm_per_cycle=ratchet,
                              slipped=any(c['max_slip_mm'] > SLIP_LIMIT_MM for c in cyc)))
    first_slip = next((p['level'] for p in per_level if p['slipped']), None)
    res.update(iso_levels=per_level, slip_level=first_slip, max_slip_mm=float(rel[:, 4].max()),
               no_slip_up_to_level=max([p['level'] for p in per_level if not p['slipped'] and all(c['complete'] for c in p['cycles'])], default=None))
if test == 'physio' and t[-1] > T_TEST:
    # per loading direction: C3 rotation at the peak moment (range of motion), max cage slip, min anti-slip SF (mu 0.2 is
    # applied in h22), max centre-of-pressure eccentricity and tension area, and whether the window was completed
    sch = json.load(open(os.path.join(cd, 'physio_schedule.json'))); fdl = res.get('friction_demand', [])
    per = []
    for w in sch['windows']:
        mrel = (rel[:, 0] >= w['t0'] - 1e-6) & (rel[:, 0] <= w['t1'] + 1e-6)
        kp = int(np.argmin(abs(t - w['t_peak']))); dof = {'Rx': 5, 'Ry': 6, 'Rz': 7}[w['dof']]
        fw = [r for r in fdl if w['t0'] - 1e-6 <= r['t'] <= w['t1'] + 1e-6]
        per.append(dict(name=w['name'], complete=bool(t[-1] >= w['t1'] - 1e-3),
                        rom_deg=float(np.degrees(rb[kp, dof])) if t[-1] >= w['t_peak'] - 1e-3 else None,
                        max_slip_mm=float(rel[mrel, 4].max()) if mrel.any() else None,
                        min_sf=min([min(r.get('top_safety_factor', 1e9), r.get('bot_safety_factor', 1e9)) for r in fw], default=None),
                        max_cop=max([max(r.get('top_cop_eccentricity', 0), r.get('bot_cop_eccentricity', 0)) for r in fw], default=None)))
    res.update(physio_windows=per, max_slip_mm=float(rel[:, 4].max()))
if test in ('push_ant', 'push_post') and t[-1] > T_TEST:
    rx = read_log('push_reaction.txt'); times = np.unique(rx[:, 0])
    Fpush = np.array([[tt, abs(rx[rx[:, 0] == tt, 2].sum())] for tt in times])
    pr = Fpush[Fpush[:, 0] >= 3.2 - 1e-6]
    disp = np.clip((pr[:, 0] - 3.2) / 1.0, 0, 1) * 3.0
    res.update(push_curve=np.c_[disp, pr[:, 1]].round(4).tolist(), push_out_force_N=float(pr[:, 1].max()) if len(pr) else None,
               push_reached_mm=float(disp.max()) if len(pr) else 0.0)
# Q40 for the slip tests: run stopped with an error before the protocol finished -> functional-failure annotation
if test in ('iso', 'physio', 'push_ant', 'push_post') and 'E R R O R' in open(os.path.join(cd, 'case.log'), errors='ignore').read():
    k = len(states) - 1; tk = float(st_t[k])
    E_ = states[k]['elem'].get('Lagrange strain', {}); worst = (1.0, None)
    for i, (n, m, Eb) in enumerate(blocks):
        Eg = E_.get(i + 1)
        if Eg is None or not n.startswith('cage_'): continue
        C = np.array([[1 + 2 * Eg[:, 0], 2 * Eg[:, 3], 2 * Eg[:, 5]], [2 * Eg[:, 3], 1 + 2 * Eg[:, 1], 2 * Eg[:, 4]],
                      [2 * Eg[:, 5], 2 * Eg[:, 4], 1 + 2 * Eg[:, 2]]]).transpose(2, 0, 1)
        lam = np.sqrt(np.clip(np.linalg.eigvalsh(C)[:, 0], 0, None)).min()
        if lam < worst[0]: worst = (float(lam), n)
    phase = ('ramp to ISO start pose (fraction %.2f)' % (tk - 3.0) if test == 'iso' and tk < 4.0 else
             'ISO cycling' if test == 'iso' else ('follower load' if tk < 3.5 else 'moment ' + str(int(tk - 3.5))) if test == 'physio'
             else 'preload' if tk < 3.2 else 'push')
    res['functional_failure_slip'] = dict(type='solver stopped before the protocol finished (Q40)', time=tk, phase=phase,
                                          slip_at_stop_mm=res.get('max_slip_mm', res.get('slip_after_insertion_mm')),
                                          contact_layer_crush_frac=float(contact_crush(k)), min_principal_stretch=worst[0],
                                          where=worst[1])
json.dump(res, open(os.path.join(cd, 'summary.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('curve', 'slip_history', 'push_curve')}, indent=1))
