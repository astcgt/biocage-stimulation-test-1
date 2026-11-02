"""Equivalent contact-skin law, step 1: patch models that calibrate and test the law (2026-10-31, user: start the prototype).

A plane-strain strip of cage material (thickness t, width w, free side faces = bulge) bonded between a fixed base and a rigid
platen, FEBio static:
  comp  - uniform compression to 40 %                -> normal law p(eps) per width (shape factor S = w / 2t)
  tilt  - platen rotated about the strip's left edge -> local base pressure vs the local compression: is the response local
          (Winkler: p(x) = f(eps(x))) or coupled to the neighbours (Pasternak / thin incompressible layer)?
  shear - 10 % compression held, platen moved tangentially by 0.5 t -> tangential law, compared with G / t
usage: python h32_eqlaw_patch.py <out_dir> <G> <Jm> <k> [t=0.2] [widths=0.4,1.2,3.0]
       python h32_eqlaw_patch.py --post <out_dir>
"""
import os, sys, json, subprocess, glob
import numpy as np

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEBIO = os.path.join(P, 'third_party/FEBio/cbuild/bin/febio4')
ENV = dict(os.environ, OMP_NUM_THREADS='2', LD_LIBRARY_PATH=os.path.join(P, 'third_party/mkl/lib'))
H = 0.025                                            # element size (mm): 8 elements through a 0.2 mm skin


def build(path, G, Jm, k, t, w, test):
    nx, nz = int(round(w / H)), int(round(t / H))
    xs, zs = np.linspace(0, w, nx + 1), np.linspace(0, t + H, nz + 2)      # top row of elements = rigid platen
    nid = {}; nodes = []
    for j in (0, 1):
        for kk, z in enumerate(zs):
            for i, x in enumerate(xs):
                nid[i, j, kk] = len(nodes) + 1; nodes.append((x, j * H, z))
    def hexa(i, kk): return [nid[i, 0, kk], nid[i + 1, 0, kk], nid[i + 1, 1, kk], nid[i, 1, kk],
                             nid[i, 0, kk + 1], nid[i + 1, 0, kk + 1], nid[i + 1, 1, kk + 1], nid[i, 1, kk + 1]]
    soft = [hexa(i, kk) for kk in range(nz) for i in range(nx)]
    rig = [hexa(i, nz) for i in range(nx)]
    base = [nid[i, j, 0] for i in range(nx + 1) for j in (0, 1)]
    top = {nid[i, j, kk] for i in range(nx + 1) for j in (0, 1) for kk in (nz, nz + 1)}
    yfix = [n for n in range(1, len(nodes) + 1) if n not in top and n not in base]
    dz, th = -0.4 * t, 0.0
    if test == 'tilt': dz, th = 0.0, -0.4 * t / w                    # 0 % at x = 0 -> 40 % at x = w (rotation about the left edge)
    L = []
    L.append('<?xml version="1.0" encoding="ISO-8859-1"?>\n<febio_spec version="2.5">\n<Module type="solid"/>')
    L.append('<Control><time_steps>40</time_steps><step_size>0.025</step_size><max_refs>25</max_refs><max_ups>10</max_ups>'
             '<dtol>0.001</dtol><etol>0.01</etol><rtol>0</rtol><lstol>0.9</lstol><time_stepper><dtmin>0.0001</dtmin>'
             '<dtmax>0.025</dtmax><max_retries>10</max_retries><opt_iter>15</opt_iter></time_stepper><analysis type="static"/><plot_level>PLOT_MAJOR_ITRS</plot_level><output_level>OUTPUT_MAJOR_ITRS</output_level></Control>')
    L.append(f'<Material><material id="1" name="skin" type="Gent"><density>1e-06</density><G>{G}</G><Jm>{Jm}</Jm><k>{k}</k></material>'
             f'<material id="2" name="platen" type="rigid body"><density>1</density><center_of_mass>0,0,{t}</center_of_mass></material></Material>')
    L.append('<Geometry><Nodes>' + ''.join(f'<node id="{i + 1}">{x:.6g},{y:.6g},{z:.6g}</node>' for i, (x, y, z) in enumerate(nodes)) + '</Nodes>')
    L.append('<Elements type="hex8" mat="1" name="skin">' + ''.join(f'<elem id="{i + 1}">{",".join(map(str, e))}</elem>' for i, e in enumerate(soft)) + '</Elements>')
    L.append('<Elements type="hex8" mat="2" name="platen">' + ''.join(f'<elem id="{len(soft) + i + 1}">{",".join(map(str, e))}</elem>' for i, e in enumerate(rig)) + '</Elements>')
    L.append('<NodeSet name="base">' + ''.join(f'<node id="{n}"/>' for n in base) + '</NodeSet>')
    L.append('<NodeSet name="yfix">' + ''.join(f'<node id="{n}"/>' for n in yfix) + '</NodeSet></Geometry>')
    BC = '<Boundary><fix bc="x,y,z" node_set="base"/><fix bc="y" node_set="yfix"/>'
    if test == 'shear':                                              # 10 % compression (t 0-0.5), then tangential 0.5 t (t 0.5-1)
        L.append('<LoadData><loadcurve id="1" type="linear"><point>0,0</point><point>0.5,1</point><point>1,1</point></loadcurve>'
                 '<loadcurve id="2" type="linear"><point>0,0</point><point>0.5,0</point><point>1,1</point></loadcurve></LoadData>')
        L.append(BC + f'<rigid_body mat="2"><prescribed bc="z" lc="1">{-0.1 * t:.6g}</prescribed><prescribed bc="x" lc="2">{0.5 * t:.6g}</prescribed>'
                 '<fixed bc="y"/><fixed bc="Rx"/><fixed bc="Ry"/><fixed bc="Rz"/></rigid_body></Boundary>')
    else:
        L.append('<LoadData><loadcurve id="1" type="linear"><point>0,0</point><point>1,1</point></loadcurve></LoadData>')
        L.append(BC + f'<rigid_body mat="2"><prescribed bc="z" lc="1">{dz:.6g}</prescribed><prescribed bc="Ry" lc="1">{-th:.6g}</prescribed>'
                 '<fixed bc="x"/><fixed bc="y"/><fixed bc="Rx"/><fixed bc="Rz"/></rigid_body></Boundary>')
    L.append('<Output><plotfile type="febio"><var type="displacement"/><var type="stress"/></plotfile><logfile>'
             '<rigid_body_data data="x;z;thy;Fx;Fz;My" file="platen.txt" delim=",">2</rigid_body_data>'
             '<element_data data="x;sz" file="base.txt" delim=",">' + ','.join(str(i + 1) for i in range(nx)) + '</element_data>'
             '</logfile></Output>\n</febio_spec>')
    os.makedirs(path, exist_ok=True)
    open(os.path.join(path, 'patch.feb'), 'w').write('\n'.join(L))
    json.dump(dict(G=G, Jm=Jm, k=k, t=t, w=w, test=test, nx=nx, nz=nz, dz=dz, theta=th), open(os.path.join(path, 'patch.json'), 'w'))


def read_log(f):
    rows, t = [], None
    for line in open(f):
        if line.startswith('*Time'): t = float(line.split('=')[1]); rows.append((t, []))
        elif line[:1].isdigit() and t is not None: rows[-1][1].append([float(v) for v in line.split(',')])
    return [(t, np.array(r)) for t, r in rows if r]


def post(out):
    res = {}
    for d in sorted(glob.glob(os.path.join(out, '*/'))):
        m = json.load(open(os.path.join(d, 'patch.json'))); name = os.path.basename(d.rstrip('/'))
        log = open(os.path.join(d, 'patch.log'), errors='ignore').read() if os.path.exists(os.path.join(d, 'patch.log')) else ''
        r = dict(normal='N O R M A L' in log)
        if not os.path.exists(os.path.join(d, 'platen.txt')): res[name] = r; continue
        pl = read_log(os.path.join(d, 'platen.txt')); ba = read_log(os.path.join(d, 'base.txt'))
        A = m['w'] * H                                           # loaded area of the strip (one element deep)
        if m['test'] == 'comp':
            r['eps'] = [round(-(row[0][2] - m['t']) / m['t'], 4) for _, row in pl]
            r['p_MPa'] = [round(-row[0][5] / A, 5) for _, row in pl]
            i1 = next((i for i, e in enumerate(r['eps']) if e > 0), None); r['E_app_0'] = r['p_MPa'][i1] / r['eps'][i1] if i1 is not None else None
        elif m['test'] == 'shear':
            r['ux'] = [round(row[0][1], 5) for _, row in pl]; r['tau_MPa'] = [round(row[0][4] / A, 5) for _, row in pl]
        else:                                                    # tilt: base pressure profile at the last converged state
            t_, b = ba[-1]; o = np.argsort(b[:, 1]); x = b[o, 1]          # bottom element row: centroid x, Cauchy sz
            th = abs(pl[-1][1][0][3])                                       # platen rotation (rad)
            r['t_end'] = t_; r['x'] = np.round(x, 4).tolist(); r['p_local_MPa'] = np.round(-b[o, 2], 5).tolist()
            r['eps_local'] = np.round(np.sin(th) * x / m['t'], 4).tolist()
        res[name] = r
    json.dump(res, open(os.path.join(out, 'results.json'), 'w'), indent=1)
    return res


if __name__ == '__main__':
    if sys.argv[1] == '--post':
        print(json.dumps({k: {kk: (v[kk][-1] if isinstance(v.get(kk), list) else v.get(kk)) for kk in v} for k, v in post(sys.argv[2]).items()}, indent=1)); sys.exit()
    out, G, Jm, k = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    t = float(sys.argv[5]) if len(sys.argv) > 5 else 0.2
    widths = [float(v) for v in sys.argv[6].split(',')] if len(sys.argv) > 6 else [0.4, 1.2, 3.0]
    jobs = [(f'comp_w{w}', w, 'comp') for w in widths] + [(f'tilt_w{max(widths)}', max(widths), 'tilt'), (f'shear_w{max(widths)}', max(widths), 'shear')]
    procs = []
    for name, w, test in jobs:
        d = os.path.join(out, name); build(d, G, Jm, k, t, w, test)
        procs.append(subprocess.Popen([FEBIO, '-i', 'patch.feb', '-silent'], cwd=d, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for p_ in procs: p_.wait()
    print(json.dumps({k: {kk: (v[kk][-1] if isinstance(v.get(kk), list) else v.get(kk)) for kk in v} for k, v in post(out).items()}, indent=1))
