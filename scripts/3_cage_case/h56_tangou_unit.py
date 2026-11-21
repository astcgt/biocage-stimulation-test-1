"""Stage-1 sub-model of one 彈勾 (elastic-hook anti-migration finger, PI 2026-11-20) against a rigid endplate plate.

Purpose (DESIGN_REVIEW_elastic_fingers_2026-11-20.md, stage 1): rank finger geometry / lean angle / thickness / modulus /
friction by the holding force they give per direction, the strain at the root and the load they take under over-travel,
before anything goes into the C3-C4 cage model. Standalone FEBio deck (not a production case; outside the h24 gate).

Model (x = finger projection direction = 'outward' from the cage wall, y = width (plane strain: uy = 0), z = toward the endplate):
  finger  = hex8 slab swept along a centre line in the x-z plane (Gent, as the cage hard phase: G = E/(2(1+nu)), k, Jm 0.7),
            root face fixed; unloaded tip at z = +delta above the cage bearing face (z = 0)
  plate   = rigid body, bottom face at z = tip + gap; it descends to z = 0 (t 0..1: pre-compression delta), then either
            slides in x by +u / -u at z = 0 (t 1..2; deck 'out' = plate moves toward -x = cage moves toward the tip,
            deck 'in' = the opposite) or over-travels to z = -over (deck 'press': the face settles / segment compression)
  mode    = 'ext' (root on the outer wall plane x = 0, finger outside the outline) | 'pocket' (root at x = -W on the back
            wall of a pocket of width W cut into the bearing face; rigid pocket floor just under the root)
Geometries (tangent angle phi(s) from +x, s = arc length 0..L): 'strut' phi = 90 - theta (straight, lean theta from the
  normal; self-lock needs tan theta <= mu), 'arc' 60 -> 5 deg (PI design 1), 'hook' 60 -> 180 deg (design 2, tip inward),
  's2' 40 + 30 cos(3 pi s / L) (design 3, convex-concave-convex, tip outward).
Read-outs (rigid-body log of the plate): Fz = normal (preload) force, Fx = tangential holding force vs plate x; element
  log: principal Lagrange strains E1 / E3 of every finger element (max over the finger and over the root 0.4 mm).

Usage:
  python3 h56_tangou_unit.py build OUT geom=arc mode=ext t=0.8 L=3 E=400 mu=0.3 delta=0.3 [theta=17 W=1.2 b=2 u=0.5 over=0.3]
  python3 h56_tangou_unit.py run OUT [deck] [ncores]        # runs out / in / press (or one deck), serial
  python3 h56_tangou_unit.py collect OUT...                 # summary.json + one-line table per case
  python3 h56_tangou_unit.py batch LIST.json NPAR NCORES    # build + run every spec in the list, NPAR at a time
"""
import os, sys, json, time, subprocess, fcntl, hashlib, numpy as np, xml.etree.ElementTree as ET
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(P, 'scripts', '5_compute'))
NU, JM, DS, HZ = 0.35, 0.7, 0.2, 0.2        # hard-phase Poisson ratio (h14 NU_HARD), Gent Jm (Q45), element size along s / through t
CTRL = ('<Control><time_steps>{n}</time_steps><step_size>{dt}</step_size><max_refs>25</max_refs><max_ups>0</max_ups><dtol>0.001</dtol>'
        '<etol>0.01</etol><rtol>0</rtol><lstol>0.9</lstol><time_stepper><dtmin>1e-5</dtmin><dtmax>{dt}</dtmax><max_retries>12</max_retries>'
        '<opt_iter>15</opt_iter></time_stepper><analysis type="static" /><symmetric_stiffness>0</symmetric_stiffness></Control>')
sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()[:16]


def phi_of(geom, L, theta):
    if geom == 'strut': return lambda s: np.radians(90 - theta) + 0 * s
    if geom == 'arc':   return lambda s: np.radians(60 - 55 * s / L)
    if geom == 'hook':  return lambda s: np.radians(60 + 120 * s / L)
    if geom == 's2':    return lambda s: np.radians(40 + 30 * np.cos(3 * np.pi * s / L))
    raise SystemExit('geom must be strut | arc | hook | s2')


def build(out, **kw):
    g = dict(geom='arc', mode='ext', t=0.8, L=3.0, E=400.0, mu=0.3, delta=0.3, theta=17.0, W=1.2, b=2.0, u=0.5, over=0.3, gap=0.02, alpha=0.0)
    for k, v in kw.items(): g[k] = type(g[k])(v) if k in g else v
    t, L, b = g['t'], g['L'], g['b']
    ns, nt, nb = max(4, int(round(L / DS))), max(2, int(round(t / HZ))), 2
    phi = phi_of(g['geom'], L, g['theta'])
    s = np.linspace(0, L, ns + 1); dx = np.cos(phi(s)); dz = np.sin(phi(s))
    cx = np.concatenate([[0], np.cumsum(0.5 * (dx[1:] + dx[:-1]) * np.diff(s))]); cz = np.concatenate([[0], np.cumsum(0.5 * (dz[1:] + dz[:-1]) * np.diff(s))])
    # normal n = (-sin phi, 0, cos phi); the tip's upper skin must reach z = delta: shift so max over the top skin = delta
    nx, nz = -np.sin(phi(s)), np.cos(phi(s))
    # highest point of EITHER skin (on a curled hook the '+n' skin is the inner one) reaches z = delta
    ztop = np.maximum(cz + 0.5 * t * nz, cz - 0.5 * t * nz); shift = g['delta'] - ztop.max(); cz = cz + shift
    xr = 0.0 if g['mode'] == 'ext' else -g['W']
    cx = cx + xr
    # nodes (j through thickness, i along s, k across width); hex ordering chosen for a positive Jacobian (checked below)
    X = {}; nid = {}; n = 0
    for i in range(ns + 1):
        for j in range(nt + 1):
            off = -0.5 * t + j * t / nt
            for k in range(nb + 1):
                n += 1; nid[(i, j, k)] = n; X[n] = (cx[i] + off * nx[i], k * b / nb, cz[i] + off * nz[i])
    hexes = []
    for i in range(ns):
        for j in range(nt):
            for k in range(nb):
                hexes.append([nid[(i, j, k)], nid[(i, j + 1, k)], nid[(i + 1, j + 1, k)], nid[(i + 1, j, k)],
                              nid[(i, j, k + 1)], nid[(i, j + 1, k + 1)], nid[(i + 1, j + 1, k + 1)], nid[(i + 1, j, k + 1)]])
    def jac(h):
        p = np.array([X[a] for a in h]); return np.dot(np.cross(p[1] - p[0], p[3] - p[0]), p[4] - p[0])
    if jac(hexes[0]) < 0: hexes = [[h[0], h[3], h[2], h[1], h[4], h[7], h[6], h[5]] for h in hexes]
    assert min(jac(h) for h in hexes) > 0, 'negative Jacobian in the finger mesh'
    # outer skin of the finger (faces not shared by two hexes, y-faces excluded by the plane-strain idea: keep only top /
    # bottom / tip faces), oriented outward
    faces = {}
    FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    for h in hexes:
        c = np.mean([X[a] for a in h], axis=0)
        for f in FACES:
            q = tuple(h[a] for a in f); key = frozenset(q)
            faces[key] = None if key in faces else (q, c)
    skin = []
    for key, v in faces.items():
        if v is None: continue
        q, c = v; p = np.array([X[a] for a in q])
        if abs(p[:, 1].max() - p[:, 1].min()) < 1e-9: continue                 # y-faces (width sides, root end excluded below too)
        nrm = np.cross(p[1] - p[0], p[2] - p[0])
        if np.dot(nrm, p.mean(axis=0) - c) < 0: q = (q[0], q[3], q[2], q[1])
        skin.append(q)
    root = [nid[(0, j, k)] for j in range(nt + 1) for k in range(nb + 1)]
    rootset = set(root); skin = [q for q in skin if not set(q) <= rootset]
    # rigid plate (bottom face at z0) and, in pocket mode, a rigid floor (top face at z_floor)
    z0 = g['delta'] + g['gap']; xlo, xhi = min(cx) - 6, max(cx) + 6
    def box(x0, x1, y0, y1, zb, zt):
        nonlocal n
        ids = []
        for dz_ in (zb, zt):
            for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                n += 1; ids.append(n); X[n] = (px, py, dz_)
        return ids
    plate = box(xlo, xhi, -1, b + 1, z0, z0 + 1.0)
    if g.get('alpha', 0.0):
        # 2026-11-20 stage 1b (form-fit): incline the plate by alpha deg about y through the tip contact point (x_tip, z0):
        # the endplate RISES toward the rim (+x = outward), so an outward slide must climb the slope (C4 superior endplate
        # lateral slope 23-43 deg at 3-7 mm from the centre, C3 inferior 25 deg at 5-7 mm; h57-era measurement, p062 model)
        a = np.radians(g['alpha']); xt = float(cx[-1]); c_, s_ = np.cos(a), np.sin(a)
        for i_ in plate:
            x_, y_, z_ = X[i_]; dx_, dz_ = x_ - xt, z_ - z0
            X[i_] = (xt + c_ * dx_ - s_ * dz_, y_, z0 + s_ * dx_ + c_ * dz_)
        # 2026-11-20 fix (advisor): pivoting at the centre-line tip leaves part of the finger above the inclined plane (the
        # overlap grew with alpha: arc preload 1.8 / 5.4 / 68 N at a nominal 0.1 mm). Shift the plate so that the first
        # contact point has exactly the clearance 'gap' at t = 0; the press step then gives the nominal interference.
        zplane = lambda x_: z0 + np.tan(a) * (x_ - xt)
        clear = min(zplane(X[i_][0]) - X[i_][2] for i_ in range(1, len(nid) + 1))
        for i_ in plate: X[i_] = (X[i_][0], X[i_][1], X[i_][2] + (g['gap'] - clear))
        meta_shift = g['gap'] - clear
    else: meta_shift = 0.0
    floor = None
    zfloor = (cz - 0.5 * t * nz).min() - 0.05
    if g['mode'] == 'pocket': floor = box(xr - 0.5, 1.0, -1, b + 1, zfloor - 1.0, zfloor)
    # deck
    mu_, K_ = g['E'] / (2 * (1 + NU)), g['E'] / (3 * (1 - 2 * NU))
    decks = {'out': (-g['u'], 0.0), 'in': (g['u'], 0.0), 'press': (0.0, g['over'])}
    meta = dict(params=g, ns=ns, nt=nt, nb=nb, n_hex=len(hexes), x_root=xr, plate_shift_mm=float(meta_shift), x_extent=[float(min(cx) - 0.5 * t), float(max(cx) + 0.5 * t)],
                root_depth_below_face_mm=float(-cz[0]), tip_x_mm=float(cx[-1]), z_floor=float(zfloor), built=time.strftime('%Y-%m-%d %H:%M'),
                builder=os.path.relpath(__file__, P), builder_sha256=sha(__file__), decks={})
    os.makedirs(out, exist_ok=True)
    for deck, (ux, over) in decks.items():
        r = ET.Element('febio_spec', version='2.5'); ET.SubElement(r, 'Module', type='solid')
        M = ET.SubElement(r, 'Material')
        m = ET.SubElement(M, 'material', id='1', name='finger', type='Gent'); ET.SubElement(m, 'density').text = '1'
        ET.SubElement(m, 'G').text = f'{mu_:.6g}'; ET.SubElement(m, 'Jm').text = f'{JM:g}'; ET.SubElement(m, 'k').text = f'{K_:.6g}'
        for mid, nm, ids in (('2', 'plate', plate),) + ((('3', 'floor', floor),) if floor else ()):
            m = ET.SubElement(M, 'material', id=mid, name=nm, type='rigid body'); ET.SubElement(m, 'density').text = '1e-06'
            ET.SubElement(m, 'center_of_mass').text = ','.join(f'{v:.6g}' for v in np.mean([X[a] for a in ids], axis=0))
        G = ET.SubElement(r, 'Geometry'); N = ET.SubElement(G, 'Nodes', name='all')
        for i in sorted(X): ET.SubElement(N, 'node', id=str(i)).text = ','.join(f'{v:.9g}' for v in X[i])
        E = ET.SubElement(G, 'Elements', type='hex8', mat='1', name='finger')
        for e, h in enumerate(hexes, 1): ET.SubElement(E, 'elem', id=str(e)).text = ','.join(map(str, h))
        eid = len(hexes)
        for mid, nm, ids in (('2', 'plate', plate),) + ((('3', 'floor', floor),) if floor else ()):
            E = ET.SubElement(G, 'Elements', type='hex8', mat=mid, name=nm); eid += 1; ET.SubElement(E, 'elem', id=str(eid)).text = ','.join(map(str, ids))
        ns_ = ET.SubElement(G, 'NodeSet', name='root')
        for i in root: ET.SubElement(ns_, 'node', id=str(i))
        ns_ = ET.SubElement(G, 'NodeSet', name='finger_all')
        for i in range(1, len(nid) + 1): ET.SubElement(ns_, 'node', id=str(i))
        S = ET.SubElement(G, 'Surface', name='finger_skin')
        for q_, q in enumerate(skin, 1): ET.SubElement(S, 'quad4', id=str(q_)).text = ','.join(map(str, q))
        S = ET.SubElement(G, 'Surface', name='plate_bot'); ET.SubElement(S, 'quad4', id='1').text = ','.join(map(str, (plate[0], plate[3], plate[2], plate[1])))
        sp = ET.SubElement(G, 'SurfacePair', name='c_plate'); ET.SubElement(sp, 'master', surface='plate_bot'); ET.SubElement(sp, 'slave', surface='finger_skin')
        if floor:
            S = ET.SubElement(G, 'Surface', name='floor_top'); ET.SubElement(S, 'quad4', id='1').text = ','.join(map(str, (floor[4], floor[5], floor[6], floor[7])))
            sp = ET.SubElement(G, 'SurfacePair', name='c_floor'); ET.SubElement(sp, 'master', surface='floor_top'); ET.SubElement(sp, 'slave', surface='finger_skin')
        B = ET.SubElement(r, 'Boundary')
        ET.SubElement(B, 'fix', bc='x,y,z', node_set='root'); ET.SubElement(B, 'fix', bc='y', node_set='finger_all')
        rb = ET.SubElement(B, 'rigid_body', mat='2')
        for d in ('y', 'Rx', 'Ry', 'Rz'): ET.SubElement(rb, 'fixed', bc=d)
        ET.SubElement(rb, 'prescribed', bc='x', lc='2').text = f'{ux:.6g}'
        ET.SubElement(rb, 'prescribed', bc='z', lc='1').text = f'{-(z0 + over):.6g}'
        if floor:
            rb = ET.SubElement(B, 'rigid_body', mat='3')
            for d in ('x', 'y', 'z', 'Rx', 'Ry', 'Rz'): ET.SubElement(rb, 'fixed', bc=d)
        C = ET.SubElement(r, 'Contact')
        for nm in ('c_plate',) + (('c_floor',) if floor else ()):
            c = ET.SubElement(C, 'contact', type='sliding-elastic', name=nm, surface_pair=nm)
            for k, v in (('laugon', 0), ('tolerance', 0.01), ('penalty', 1), ('auto_penalty', 1), ('two_pass', 0), ('search_tol', 0.01),
                         ('search_radius', 1.0), ('symmetric_stiffness', 0), ('tension', 0), ('fric_coeff', g['mu']), ('knmult', 0), ('minaug', 1), ('maxaug', 10)):
                ET.SubElement(c, k).text = f'{v:g}'
        LD = ET.SubElement(r, 'LoadData')
        a = z0 / (z0 + over) if over else 1.0
        for i, pts in ((1, [(0, 0), (1, a), (2, 1)]), (2, [(0, 0), (1, 0), (2, 1)])):
            c = ET.SubElement(LD, 'loadcurve', id=str(i), type='linear')
            for tt, v in pts: ET.SubElement(c, 'point').text = f'{tt},{v:.6g}'
        O = ET.SubElement(r, 'Output'); pl = ET.SubElement(O, 'plotfile', type='febio')
        for v in ('displacement', 'stress', 'Lagrange strain', 'contact pressure'): ET.SubElement(pl, 'var', type=v)
        lg = ET.SubElement(O, 'logfile')
        ET.SubElement(lg, 'rigid_body_data', data='x;y;z;Fx;Fy;Fz', file='plate.txt', delim=',').text = '2'
        ET.SubElement(lg, 'element_data', data='E1;E3;s1;s3', file='finger_elems.txt', delim=',').text = ','.join(str(e) for e in range(1, len(hexes) + 1))
        st = ET.SubElement(r, 'Step', name=deck); st.append(ET.fromstring(CTRL.format(n=100, dt=0.02)))
        d = os.path.join(out, deck); os.makedirs(d, exist_ok=True)
        ET.ElementTree(r).write(os.path.join(d, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
        meta['decks'][deck] = sha(os.path.join(d, 'case.feb'))
    json.dump(meta, open(os.path.join(out, 'unit.json'), 'w'), indent=1)
    print(out, f"built: {g['geom']} {g['mode']} t {t} L {L} -> {len(hexes)} hex, x extent {meta['x_extent'][0]:.2f}..{meta['x_extent'][1]:.2f} mm, root {meta['root_depth_below_face_mm']:.2f} mm below the face")
    return meta


def idle_cores(n):
    from h06_run_cpu_batch import cpu_busy, claimed_cores
    busy = cpu_busy(); usable = [c for c in sorted(busy, key=busy.get) if busy[c] < 0.10 and c not in claimed_cores()]
    return sorted(usable[:n]) if len(usable) >= n else None


def run(out, deck=None, ncores=2, cores=None):
    from h06_run_cpu_batch import FEBIO
    meta = json.load(open(os.path.join(out, 'unit.json')))
    for dk in ([deck] if deck else list(meta['decks'])):
        d = os.path.join(out, dk)
        lock = open(os.path.join(P, 'human_study', '.cpu_launch.lock'), 'w')
        if cores is None:                       # single run: pick idle cores under the shared launch lock (as h55)
            fcntl.flock(lock, fcntl.LOCK_EX); cores = idle_cores(ncores)
            if cores is None: fcntl.flock(lock, fcntl.LOCK_UN); print(d, 'no idle cores'); return
        libs = os.path.join(P, 'third_party/mkl/lib')
        env = dict(os.environ, OMP_NUM_THREADS=str(ncores), MKL_NUM_THREADS=str(ncores), LD_LIBRARY_PATH=libs, KMP_STACKSIZE='1G', OMP_STACKSIZE='1G')
        cmd = ['prlimit', '--stack=unlimited', 'taskset', '-c', ','.join(map(str, cores)), FEBIO, '-i', 'case.feb', '-o', 'case.log', '-silent']
        t0 = time.time(); p = subprocess.Popen(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=open(os.path.join(d, 'stderr.log'), 'w'))
        try: fcntl.flock(lock, fcntl.LOCK_UN)
        except Exception: pass
        p.wait()
        txt = open(os.path.join(d, 'case.log'), errors='ignore').read()
        ok = 'N O R M A L' in txt[-4000:]
        json.dump(dict(exit=p.returncode, normal=ok, wall_s=round(time.time() - t0, 1), cores=ncores, febio_sha256=sha(FEBIO)), open(os.path.join(d, 'resources.json'), 'w'), indent=1)
        print(d, 'normal' if ok else 'NOT normal', round(time.time() - t0), 's', flush=True)


def readlog(f):
    """FEBio logfile -> list of (time, array rows)"""
    out = []; t = None; rows = []
    for line in open(f):
        if line.startswith('*Time'):
            if t is not None: out.append((t, np.array(rows))); rows = []
            t = float(line.split('=')[1])
        elif line[0] not in '*' and line.strip(): rows.append([float(v) for v in line.split(',')])
    if t is not None: out.append((t, np.array(rows)))
    return out


def collect(outs):
    for out in outs:
        if not os.path.exists(os.path.join(out, 'unit.json')): print(os.path.basename(out), 'UNBUILDABLE'); continue
        meta = json.load(open(os.path.join(out, 'unit.json'))); g = meta['params']; res = {}
        root_elems = set(range(1, 2 * meta['nt'] * meta['nb'] + 1))        # first two stations along s (0.4 mm) = root region
        for dk in meta['decks']:
            d = os.path.join(out, dk); pf, ef = os.path.join(d, 'plate.txt'), os.path.join(d, 'finger_elems.txt')
            if not os.path.exists(pf): continue
            pl = readlog(pf); el = readlog(ef)
            if not pl or not el or len(el) < 2: res[dk] = dict(normal=False, t_end=0.0); continue
            T = np.array([t for t, _ in pl]); x = np.array([r[0, 1] for _, r in pl]); z = np.array([r[0, 3] for _, r in pl])
            Fx = np.array([r[0, 4] for _, r in pl]); Fz = np.array([r[0, 6] for _, r in pl])
            i1 = int(np.argmin(abs(T - 1.0)))
            r_ = dict(t_end=float(T[-1]), normal=json.load(open(os.path.join(d, 'resources.json'))).get('normal') if os.path.exists(os.path.join(d, 'resources.json')) else None,
                      preload_Fz_N=float(Fz[i1]), preload_Fx_N=float(Fx[i1]))
            if dk in ('out', 'in'):
                s2 = T > 1.0 + 1e-9
                if s2.any():
                    ux = abs(x[s2] - x[i1]); fx = Fx[s2]; fz = Fz[s2]
                    r_.update(slide_mm=float(ux[-1]), Fx_peak_N=float(np.max(abs(fx))), Fx_end_N=float(abs(fx[-1])), Fz_end_N=float(fz[-1]),
                              Fx_at={f'{u:.1f}': float(abs(np.interp(u, ux, fx))) for u in (0.1, 0.2, 0.3, 0.5) if u <= ux[-1] + 1e-6},
                              rising_at_end=bool(len(fx) > 5 and abs(fx[-1]) > abs(fx[-5]) * 1.02))
            else:
                s2 = T > 1.0 + 1e-9
                if s2.any():
                    dz = -(z[s2] - z[i1]); r_.update(over_mm=float(dz[-1]), Fz_over_N=float(Fz[-1]), Fz_at={f'{o:.1f}': float(np.interp(o, dz, Fz[s2])) for o in (0.1, 0.2, 0.3) if o <= dz[-1] + 1e-6})
            E1 = np.array([r[:, 1] for _, r in el]); E3 = np.array([r[:, 2] for _, r in el]); ids = el[0][1][:, 0].astype(int)
            rm = np.isin(ids, list(root_elems))
            r_.update(E_max_abs=float(max(abs(E1).max(), abs(E3).max())), E_max_abs_preload=float(max(abs(E1[i1]).max(), abs(E3[i1]).max())),
                      E_root_max_abs=float(max(abs(E1[:, rm]).max(), abs(E3[:, rm]).max())), eps_limit_15MPa=float(15.0 / g['E']), eps_limit_40MPa=float(40.0 / g['E']))
            res[dk] = r_
        json.dump(res, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
        o, i, p_ = res.get('out', {}), res.get('in', {}), res.get('press', {})
        print(f"{os.path.basename(out):28s} {g['geom']:5s} {g['mode']:6s} t{g['t']:.1f} L{g['L']:.0f} E{g['E']:.0f} mu{g['mu']:.2f} d{g['delta']:.2f} | "
              f"preload {o.get('preload_Fz_N', float('nan')):6.2f} N | hold out {o.get('Fx_peak_N', float('nan')):6.2f} (end {o.get('Fx_end_N', float('nan')):6.2f}{'^' if o.get('rising_at_end') else ' '}) in {i.get('Fx_peak_N', float('nan')):6.2f} N | "
              f"press 0.3 {p_.get('Fz_over_N', float('nan')):7.1f} N | strain max {o.get('E_max_abs', float('nan')):.3f} root {o.get('E_root_max_abs', float('nan')):.3f} (lim {o.get('eps_limit_15MPa', float('nan')):.3f}) | "
              f"{'ok' if all(r.get('normal') for r in res.values()) and len(res) == 3 else 'INCOMPLETE ' + str({k: (v.get('normal'), round(v.get('t_end', 0), 2)) for k, v in res.items()})}")


def batch(listfile, npar, ncores):
    from concurrent.futures import ThreadPoolExecutor
    import queue
    specs = json.load(open(listfile)); base = os.path.dirname(os.path.abspath(listfile))
    cores = idle_cores(npar * ncores)                 # one fixed core set per worker, chosen once (the per-deck sampling
    if cores is None: sys.exit('not enough idle cores')  # and launch lock of h55 would serialise ~3000 two-second runs)
    pool = queue.Queue()
    for w in range(npar): pool.put(cores[w * ncores:(w + 1) * ncores])
    def one(sp):
        out = os.path.join(base, sp.pop('name'))
        if all(os.path.exists(os.path.join(out, dk, 'resources.json')) for dk in ('out', 'in', 'press')): return out
        try: build(out, **sp)
        except AssertionError as e:                 # e.g. curvature too tight for the thickness (inner skin folds)
            os.makedirs(out, exist_ok=True); json.dump(dict(unbuildable=str(e), params=sp), open(os.path.join(out, 'unbuildable.json'), 'w')); print(out, 'UNBUILDABLE', e); return out
        cs = pool.get()
        try: run(out, None, ncores, cores=cs)
        finally: pool.put(cs)
        return out
    with ThreadPoolExecutor(npar) as ex: outs = list(ex.map(one, specs))
    collect(outs)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'build': build(a[1], **dict(x.split('=', 1) for x in a[2:]))
    elif a and a[0] == 'run': run(a[1], a[2] if len(a) > 2 and a[2] in ('out', 'in', 'press') else None, int(a[-1]) if a[-1].isdigit() else 2)
    elif a and a[0] == 'collect': collect(a[1:])
    elif a and a[0] == 'batch': batch(a[1], int(a[2]), int(a[3]))
    else: sys.exit(__doc__)
