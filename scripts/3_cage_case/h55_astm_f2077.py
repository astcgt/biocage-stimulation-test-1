"""ASTM F2077-24 style static tests of the cage ALONE between rigid blocks (PI 2026-11-19 test-gap item 2, decision 6).

Why: F2077 characterises the structural integrity of the device itself, not the bone-implant interface (1.4); static tests use
metal (rigid) blocks whose surfaces mate with the device the way the endplates do (6.3, Fig. 7). The F2077 numbers to report are
stiffness, 2 % offset yield (offset = 2 % of the intradiscal height, 3.2.14) and ultimate (8.4); acceptance values are not part of
the standard (1.2, X1.9).
Model (one deck per test, built from a production case so the cage mesh and materials are the ones that were judged):
  cage  = the cage_* hex blocks of the source case.feb at their reference (as-manufactured) coordinates; each material = the
          Gent 'elastic' child of the production 'uncoupled prestrain elastic' wrapper (the insertion prestrain is not part of a
          bench test). No biodisc, no bone.
  blocks = two rigid bodies; the cage_top / cage_bot face nodes are attached to them (= blocks machined to the device surface,
          bonded: upper bound of the block support; pocket = the face itself, so > 50 % of the device height is exposed, 6.6).
          Rotation centre of the superior block = the device geometric centre (ball / gimbal centre in Figs. 2-5).
  inferior block fixed in all 6 dof.
  compression : superior block moved -Z by D (x, y, Rz held; Rx, Ry free = ball joint, 6.3)
  shear45     : superior block moved along (+X, -Z)/sqrt2 by D (y, Rz held; Rx, Ry free) = compression-shear with the load
                axis at 45 deg, anterior shear Fx = compressive Fz initially (6.4)
  torsion     : step 1 compressive preload 100 N (cervical, 8.3; x, y, Rz held, Rx, Ry free), step 2 Rz to ROT deg with the
                preload held (x, y held). DEVIATION: Rx, Ry are held in step 2 (FEBio cannot mix prescribed and free rigid rotations),
                where 6.5 asks for a gimbal with negligible bending moment; the bending moment is logged (My, Mx) to size the effect.
Quasi-static (rate-independent hyperelastic material; F2077 rate <= 25 mm/min / 60 deg/min has no effect here).
Before building, the SOURCE case is checked with h24 (rebuild by the current h14 byte-identical = current code and settings);
the result is stored in astm.json. Read-out: biocage-evo/methods/e11_astm.py.
Elastoplastic variant (PI 2026-11-20 decision 8 option B, so the 2 % offset yield is comparable to FDA / Peck 2017 bench values):
  with a 5th build argument WE (0 <= WE < 1) every cage material becomes FEBio 'reactive plasticity' (constrained reactive
  mixture elastoplasticity, Zimmerman, Jiang, Weiss, Timmins & Ateshian 2021, J Mech Phys Solids 155:104534) around the same
  Gent elastic child: von Mises yield criterion, one yielding bond family (flow curve 'PFC paper', nf 1) with yield
  Y0 = sig_of_phi(phi) = sig_soft + phi (sig_hard - sig_soft) (h14 rule, phi from the block name, params of the source case),
  w0 = 1 - WE and a never-yielding bond fraction WE -> bilinear response, post-yield tangent ~ WE x initial modulus
  (WE 0 = perfectly plastic). The hard-phase plastic strain is plotted ('octahedral plastic strain').
  SCOPE (6th argument): 'all' (default, every phase yields at its sig_of_phi) or 'hard' (only the pure hard-phase blocks yield;
  the mixed layers stay Gent elastic) - 'hard' is the PI decision 8 wording.
usage: python h55_astm_f2077.py build <out_dir> <source_case_dir> [D_mm=0.6] [ROT_deg=10] [WE=elastic] [SCOPE=all]
       python h55_astm_f2077.py run <out_dir> <test> <cores>      (test = compression | shear45 | torsion)
"""
import os, sys, json, copy, time, subprocess, fcntl, hashlib, numpy as np, xml.etree.ElementTree as ET
H = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(P, 'scripts', '5_compute'))
TESTS = ('compression', 'shear45', 'torsion')
CTRL = ('<Control><time_steps>{n}</time_steps><step_size>{dt}</step_size><max_refs>25</max_refs><max_ups>10</max_ups><dtol>0.001</dtol>'
        '<etol>0.01</etol><rtol>0</rtol><lstol>0.9</lstol><time_stepper><dtmin>{dtmin}</dtmin><dtmax>{dt}</dtmax><max_retries>10</max_retries>'
        '<opt_iter>15</opt_iter></time_stepper><analysis type="static" /><symmetric_stiffness>0</symmetric_stiffness></Control>')


def sha(f): return hashlib.sha256(open(f, 'rb').read()).hexdigest()


def build(out, src, D=0.6, ROT=10.0, WE=None, SCOPE='all'):
    # h24 equivalent without writing into the production run dir: the source passed h24 at launch (preflight.json ok) and the
    # CURRENT h14 rebuilds its case.feb byte-identical from its params (h24 check 2) -> current code and settings
    src = os.path.normpath(src); pf = json.load(open(os.path.join(src, 'preflight.json')))
    tmp = os.path.join(out, '_source_rebuild'); os.makedirs(out, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(H, 'h14_build_case.py'), src + '_params.json', tmp], check=True, cwd=P, stdout=subprocess.DEVNULL)
    same = sha(os.path.join(tmp, 'case.feb')) == sha(os.path.join(src, 'case.feb'))
    chk = dict(ok=bool(pf.get('ok')) and same, launch_preflight_ok=pf.get('ok'), rebuild_identical=same, warnings=pf.get('warnings'), errors=pf.get('errors'))
    import shutil; shutil.rmtree(tmp)
    if not chk['ok']: sys.exit(f'source {src} fails the preflight equivalent: {chk}')
    root = ET.parse(os.path.join(src, 'case.feb')).getroot(); g = root.find('Geometry')
    X = {int(n.get('id')): [float(v) for v in n.text.split(',')] for n in g.find('Nodes')}
    blocks = [eb for eb in g.findall('Elements') if eb.get('name').startswith('cage_') and eb.get('type') == 'hex8']
    mats = {m.get('id'): m for m in root.find('Material')}
    used = sorted({int(v) for eb in blocks for e in eb for v in e.text.split(',')}); nid = {o: i + 1 for i, o in enumerate(used)}
    C = np.array([X[o] for o in used]); ctr = (C.min(0) + C.max(0)) / 2
    surf = {s: sorted({nid[int(v)] for f in g.find(f"Surface[@name='{s}']") for v in f.text.split(',')}) for s in ('cage_top', 'cage_bot')}
    zt = np.array([C[i - 1][2] for i in surf['cage_top']]); zb = np.array([C[i - 1][2] for i in surf['cage_bot']])
    # intradiscal height (Fig. 1): block-to-block distance along Z through the device centre = top face z - bottom face z at the
    # face nodes nearest the centre axis
    near = lambda ids: min(ids, key=lambda i: np.hypot(C[i - 1][0] - ctr[0], C[i - 1][1] - ctr[1]))
    h_id = float(C[near(surf['cage_top']) - 1][2] - C[near(surf['cage_bot']) - 1][2])
    hx = 0.5                                                          # dummy rigid hex half size, placed outside the cage
    zs = {'sup': C[:, 2].max() + 3 + hx, 'inf': C[:, 2].min() - 3 - hx}
    meta = dict(source=os.path.relpath(src, P), source_case_sha256=sha(os.path.join(src, 'case.feb')), h24=chk,
                n_nodes=len(used), n_hex=sum(len(list(eb)) for eb in blocks), centre_mm=ctr.tolist(), intradiscal_height_mm=h_id,
                face_z_range_mm=dict(top=[float(zt.min()), float(zt.max())], bottom=[float(zb.min()), float(zb.max())]),
                D_mm=D, ROT_deg=ROT, preload_N=100.0, materials={eb.get('name'): {c.tag: c.text for c in mats[eb.get('mat')].find('elastic')} for eb in blocks},
                built=time.strftime('%Y-%m-%d %H:%M'), builder=os.path.relpath(__file__, P), builder_sha256=sha(__file__))
    if WE is not None:
        prm = json.load(open(src + '_params.json')); cs = json.load(open(os.path.join(P, 'human_study', 'current_settings.json')))['common']
        ss, sh = float(prm.get('sig_soft', cs.get('sig_soft', 3.0))), float(prm.get('sig_hard', cs.get('sig_hard', 15.0)))
        phi = lambda n: float(n.rsplit('_', 1)[-1]) if n.rsplit('_', 1)[-1].replace('.', '', 1).isdigit() else 0.0
        pmax = max(phi(eb.get('name')) for eb in blocks)
        meta['plastic'] = dict(model='reactive plasticity, DC von Mises stress, PFC paper nf 1', we=float(WE), sig_soft=ss, sig_hard=sh, scope=SCOPE,
                               Y0={eb.get('name'): ss + phi(eb.get('name')) * (sh - ss) for eb in blocks if SCOPE == 'all' or phi(eb.get('name')) >= pmax - 1e-9})
    os.makedirs(out, exist_ok=True)
    for test in TESTS:
        r = ET.Element('febio_spec', version='2.5'); ET.SubElement(r, 'Module', type='solid')
        M = ET.SubElement(r, 'Material'); mid = {}
        for k, eb in enumerate(blocks):
            el = copy.deepcopy(mats[eb.get('mat')].find('elastic'))
            if WE is None or eb.get('name') not in meta['plastic']['Y0']:   # SCOPE 'hard': only the pure hard-phase blocks yield (PI decision 8 wording)
                m = ET.SubElement(M, 'material', id=str(k + 1), name=eb.get('name'), type=el.get('type'))
                for c in el: m.append(c)
            else:
                m = ET.SubElement(M, 'material', id=str(k + 1), name=eb.get('name'), type='reactive plasticity')
                ET.SubElement(m, 'density').text = '1e-06'
                el.tag = 'elastic'; [el.remove(c) for c in el.findall('density')]; m.append(el)
                ET.SubElement(m, 'yield_criterion', type='DC von Mises stress')
                fc = ET.SubElement(m, 'flow_curve', type='PFC paper')
                for kk, vv in (('Y0', meta['plastic']['Y0'][eb.get('name')]), ('Ymax', meta['plastic']['Y0'][eb.get('name')]), ('w0', 1 - float(WE)), ('we', float(WE)), ('nf', 1), ('r', 1)):
                    ET.SubElement(fc, kk).text = f'{vv:.6g}' if isinstance(vv, float) else str(vv)
                ET.SubElement(m, 'isochoric').text = '1'
            mid[eb.get('name')] = str(k + 1)
        rb = {}
        for j, s in enumerate(('sup', 'inf')):
            rb[s] = str(len(blocks) + 1 + j)
            m = ET.SubElement(M, 'material', id=rb[s], name='block_' + s, type='rigid body'); ET.SubElement(m, 'density').text = '1e-06'
            ET.SubElement(m, 'center_of_mass').text = ','.join(f'{v:.6g}' for v in ctr)
        G = ET.SubElement(r, 'Geometry'); N = ET.SubElement(G, 'Nodes', name='all')
        for o in used: ET.SubElement(N, 'node', id=str(nid[o])).text = ','.join(f'{v:.9g}' for v in X[o])
        n0 = len(used); dummy = {}
        for s in ('sup', 'inf'):
            ids = []
            for dx, dy, dz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
                n0 += 1; ids.append(n0); ET.SubElement(N, 'node', id=str(n0)).text = f'{ctr[0] + dx * hx:.6g},{ctr[1] + dy * hx:.6g},{zs[s] + dz * hx:.6g}'
            dummy[s] = ids
        eid = 0
        for eb in blocks:
            E = ET.SubElement(G, 'Elements', type='hex8', mat=mid[eb.get('name')], name=eb.get('name'))
            for e in eb: eid += 1; ET.SubElement(E, 'elem', id=str(eid)).text = ','.join(str(nid[int(v)]) for v in e.text.split(','))
        for s in ('sup', 'inf'):
            E = ET.SubElement(G, 'Elements', type='hex8', mat=rb[s], name='block_' + s); eid += 1; ET.SubElement(E, 'elem', id=str(eid)).text = ','.join(map(str, dummy[s]))
        for nm, s in (('face_top', 'cage_top'), ('face_bot', 'cage_bot')):
            ns = ET.SubElement(G, 'NodeSet', name=nm)
            for i in surf[s]: ET.SubElement(ns, 'node', id=str(i))
        B = ET.SubElement(r, 'Boundary')
        ET.SubElement(B, 'rigid', rb=rb['sup'], node_set='face_top'); ET.SubElement(B, 'rigid', rb=rb['inf'], node_set='face_bot')
        bi = ET.SubElement(B, 'rigid_body', mat=rb['inf'])
        for d in ('x', 'y', 'z', 'Rx', 'Ry', 'Rz'): ET.SubElement(bi, 'fixed', bc=d)
        LD = ET.SubElement(r, 'LoadData')
        def lc(i, pts):
            c = ET.SubElement(LD, 'loadcurve', id=str(i), type='linear')
            for t, v in pts: ET.SubElement(c, 'point').text = f'{t},{v}'
        O = ET.SubElement(r, 'Output'); pl = ET.SubElement(O, 'plotfile', type='febio')
        for v in ('displacement', 'stress', 'Lagrange strain') + (('octahedral plastic strain',) if WE is not None else ()): ET.SubElement(pl, 'var', type=v)
        lg = ET.SubElement(O, 'logfile'); ET.SubElement(lg, 'rigid_body_data', data='x;y;z;thx;thy;thz;Fx;Fy;Fz;Mx;My;Mz', file='block_sup.txt', delim=',').text = rb['sup']
        if test in ('compression', 'shear45'):
            st = ET.SubElement(r, 'Step', name=test); st.append(ET.fromstring(CTRL.format(n=50, dt=0.02, dtmin=1e-4)))
            sb = ET.SubElement(ET.SubElement(st, 'Boundary'), 'rigid_body', mat=rb['sup']); lc(1, [(0, 0), (1, 1)])
            if test == 'compression':
                for d in ('x', 'y', 'Rz'): ET.SubElement(sb, 'fixed', bc=d)
                ET.SubElement(sb, 'prescribed', bc='z', lc='1').text = f'{-D}'
            else:
                for d in ('y', 'Rz'): ET.SubElement(sb, 'fixed', bc=d)
                ET.SubElement(sb, 'prescribed', bc='x', lc='1').text = f'{D / np.sqrt(2):.6g}'
                ET.SubElement(sb, 'prescribed', bc='z', lc='1').text = f'{-D / np.sqrt(2):.6g}'
        else:
            lc(1, [(0, 0), (1, 1), (2, 1)]); lc(2, [(1, 0), (2, 1)])
            for name, t in (('preload', 1), ('twist', 2)):
                st = ET.SubElement(r, 'Step', name=name); st.append(ET.fromstring(CTRL.format(n=20 if t == 1 else 50, dt=0.05 if t == 1 else 0.02, dtmin=1e-4)))
                sb = ET.SubElement(ET.SubElement(st, 'Boundary'), 'rigid_body', mat=rb['sup'])
                for d in ('x', 'y'): ET.SubElement(sb, 'fixed', bc=d)
                ET.SubElement(sb, 'force', bc='z', lc='1').text = '-100'
                if t == 1: ET.SubElement(sb, 'fixed', bc='Rz')
                else:                                     # FEBio: rigid rotations cannot mix prescribed and free components -> the
                    for d in ('Rx', 'Ry'): ET.SubElement(sb, 'fixed', bc=d)   # twist step holds Rx, Ry (deviation from the gimbal of 6.5, F2077 10.2.5)
                    ET.SubElement(sb, 'prescribed', bc='Rz', lc='2').text = f'{np.radians(ROT):.6g}'
        d = os.path.join(out, test); os.makedirs(d, exist_ok=True)
        ET.ElementTree(r).write(os.path.join(d, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
        meta.setdefault('decks', {})[test] = sha(os.path.join(d, 'case.feb'))
    json.dump(meta, open(os.path.join(out, 'astm.json'), 'w'), indent=1)
    print(out, 'built: intradiscal height %.2f mm, %d hex, h24 source OK' % (h_id, meta['n_hex']))


def run(out, test, ncores):
    from h06_run_cpu_batch import cpu_busy, claimed_cores, FEBIO
    meta = json.load(open(os.path.join(out, 'astm.json'))); d = os.path.join(out, test)
    if sha(os.path.join(d, 'case.feb')) != meta['decks'][test] or sha(__file__) != meta['builder_sha256']: sys.exit(f'{d}: deck or builder changed since build - rebuild')
    lock = open(os.path.join(P, 'human_study', '.cpu_launch.lock'), 'w'); fcntl.flock(lock, fcntl.LOCK_EX)
    busy = cpu_busy(); usable = [c for c in sorted(busy, key=busy.get) if busy[c] < 0.10 and c not in claimed_cores()]
    if len(usable) < ncores: sys.exit(3)
    cores = sorted(usable[:ncores]); libs = os.path.join(P, 'third_party/mkl/lib')
    env = dict(os.environ, OMP_NUM_THREADS=str(ncores), MKL_NUM_THREADS=str(ncores), LD_LIBRARY_PATH=libs, KMP_STACKSIZE='1G', OMP_STACKSIZE='1G')
    cmd = ['prlimit', '--stack=unlimited', 'taskset', '-c', ','.join(map(str, cores)), FEBIO, '-i', 'case.feb', '-o', 'case.log', '-silent']
    t0 = time.time(); p = subprocess.Popen(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=open(os.path.join(d, 'stderr.log'), 'w'))
    time.sleep(3); fcntl.flock(lock, fcntl.LOCK_UN); p.wait()
    txt = open(os.path.join(d, 'case.log'), errors='ignore').read()
    json.dump(dict(exit=p.returncode, normal='N O R M A L' in txt[-4000:], wall_s=round(time.time() - t0, 1), cores=ncores, febio=FEBIO, febio_sha256=sha(FEBIO)),
              open(os.path.join(d, 'resources.json'), 'w'), indent=1)
    print(d, 'normal' if 'N O R M A L' in txt[-4000:] else 'NOT normal', round(time.time() - t0), 's', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'build': build(a[1], a[2], *[float(x) for x in a[3:6]], *a[6:7])
    elif a and a[0] == 'run': run(a[1], a[2], int(a[3]))
    else: sys.exit(__doc__)
