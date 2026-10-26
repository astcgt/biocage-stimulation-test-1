"""Verifier r0001, test V02: does a block held in STICK under a constant tangential force creep with the number of load
increments? (Coulomb stick must not depend on the increment count.)

Upper block (neo-Hookean, soft E = 10 MPa like a soft PLCL, or 400 MPa) on a clamped lower block, sliding-elastic contact
mu 0.3, auto penalty. A rigid plate on top: fixed y / Rx / Ry / Rz, force-controlled z (-Fn) and x (Ft = 0.5 mu Fn).
t 0-0.4: press; t 0.4-0.5: Ft ramps on; t 0.5-1.0: everything constant (hold). Run with 10 / 20 / 40 / 80 increments.
Reported: plate x displacement at t = 0.5 and t = 1.0; creep during the hold = x(1.0) - x(0.5). Correct stick: creep ~ 0
and independent of the increment count. Also runs FEBio 4 on the same file (fixed steps) for the same quantity.
usage: python -I human_study/evo/roles/verifier/v02_stick_creep.py [solver: dr|newton]
"""
import os, sys, site, json, subprocess
sys.path.insert(0, site.getusersitepackages())          # python -I drops the user site (torch, cupy and their numpy live there)
os.environ.setdefault('CUDA_PATH', os.path.join(site.getusersitepackages(), 'nvidia/cuda_runtime'))   # CuPy kernel headers
import ctypes                                            # NVIDIA pip-wheel libraries are not found under python -I: preload
for _l in ('cuda_nvrtc/lib/libnvrtc.so.12', 'cu12/lib/libcudss.so.0'):
    ctypes.CDLL(os.path.join(site.getusersitepackages(), 'nvidia', _l), mode=ctypes.RTLD_GLOBAL)
site.ENABLE_USER_SITE = True
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(P, 'scripts/7_evo/gpufe'))
import feb, model as mdl, solver as slv
from gate1_patch import FEBIO, read_log
from gate1b_equilibrium import bar

OUT = os.path.join(HERE, 'v02_stick_creep')
MU, FN = 0.3, 4.0


def write(path, E_up, n_steps):
    Xa, Ha = bar(4, 4, 2, (4.0, 4.0, 2.0)); Xb, Hb = bar(3, 3, 3, (2.0, 2.0, 1.5))
    Xb = Xb + np.array([1.0, 1.0, 2.0])
    X = np.vstack([Xa, Xb]); Hb = Hb + len(Xa)
    zc = X[Hb].mean(1)[:, 2]; Hd, Hr = Hb[zc < 3.0], Hb[zc >= 3.0]          # top layer of the upper block = rigid plate
    base = np.where(X[:, 2] < 1e-9)[0]
    mf = [[h[4], h[5], h[6], h[7]] for h in Ha if all(X[h[4:8], 2] > 2.0 - 1e-9)]
    sf = [[h[0], h[3], h[2], h[1]] for h in Hd if all(X[h[0:4], 2] < 2.0 + 1e-9)]
    mats = (f'<material id="1" name="lo" type="neo-Hookean"><density>1</density><E>400</E><v>0.3</v></material>'
            f'<material id="2" name="up" type="neo-Hookean"><density>1</density><E>{E_up}</E><v>0.3</v></material>'
            '<material id="3" name="plate" type="rigid body"><density>1</density></material>')
    L = ['<?xml version="1.0" encoding="ISO-8859-1"?>', '<febio_spec version="2.5">', '<Module type="solid"/>',
         f'<Control><time_steps>{n_steps}</time_steps><step_size>{1.0 / n_steps:.12g}</step_size><max_refs>50</max_refs><max_ups>0</max_ups>'
         '<dtol>1e-6</dtol><etol>1e-8</etol><rtol>0</rtol><lstol>0.9</lstol><analysis type="static"/></Control>',
         '<Material>' + mats + '</Material>', '<Geometry><Nodes>']
    L += [f'<node id="{i + 1}">{x[0]:.12g},{x[1]:.12g},{x[2]:.12g}</node>' for i, x in enumerate(X)]
    eid = 1
    for name, mat, H in (('lower', 1, Ha), ('upper', 2, Hd), ('plate', 3, Hr)):
        L.append(f'</Nodes>' if eid == 1 else '')
        L.append(f'<Elements type="hex8" mat="{mat}" name="{name}">')
        for e in H: L.append(f'<elem id="{eid}">' + ','.join(str(v + 1) for v in e) + '</elem>'); eid += 1
        L.append('</Elements>')
    L += ['<NodeSet name="base">' + ''.join(f'<node id="{i + 1}"/>' for i in base) + '</NodeSet>',
          '<Surface name="master">' + ''.join(f'<quad4 id="{k + 1}">' + ','.join(str(v + 1) for v in f) + '</quad4>' for k, f in enumerate(mf)) + '</Surface>',
          '<Surface name="slave">' + ''.join(f'<quad4 id="{k + 1}">' + ','.join(str(v + 1) for v in f) + '</quad4>' for k, f in enumerate(sf)) + '</Surface>',
          '<SurfacePair name="pair"><master surface="master"/><slave surface="slave"/></SurfacePair>',
          '</Geometry><Boundary>', '<fix bc="x,y,z" node_set="base"/>',
          '<rigid_body mat="3"><fixed bc="y"/><fixed bc="Rx"/><fixed bc="Ry"/><fixed bc="Rz"/>'
          f'<force bc="z" lc="1">{-FN}</force><force bc="x" lc="2">{0.5 * MU * FN}</force></rigid_body>',
          '</Boundary><Contact><contact type="sliding-elastic" name="c" surface_pair="pair"><laugon>0</laugon><penalty>1</penalty>'
          '<auto_penalty>1</auto_penalty><two_pass>0</two_pass><search_tol>0.01</search_tol><search_radius>1.0</search_radius>'
          f'<symmetric_stiffness>0</symmetric_stiffness><tension>0</tension><fric_coeff>{MU}</fric_coeff></contact></Contact>',
          '<LoadData><loadcurve id="1" type="linear"><point>0,0</point><point>0.4,1</point><point>1,1</point></loadcurve>'
          '<loadcurve id="2" type="linear"><point>0,0</point><point>0.4,0</point><point>0.5,1</point><point>1,1</point></loadcurve></LoadData>',
          '<Output><logfile><rigid_body_data data="x;y;z;Fx;Fz" file="rb.txt" delim=",">3</rigid_body_data></logfile></Output></febio_spec>']
    open(path, 'w').write('\n'.join(L))


def gpu(fp, which):
    m = feb.read(fp); M = mdl.build(m)
    if which == 'newton':
        import newton
        s = newton.NewtonSolver(M, dict(verbose=False, log_every=0))
    else:
        s = slv.Solver(M, dict(verbose=False, tol_r=1e-7, tol_dx=1e-9, search_every=20, max_iter=30000))
    rows = []
    def cb(sol, row):
        rows.append(dict(t=round(sol.t, 6), x=row['rigid'][3]['x'][0], z=row['rigid'][3]['x'][2], conv=row['converged'], iters=row['iters'],
                         stick=float(np.mean([p.stick.float().mean().item() for p in sol.passes]))))
        print('   ', rows[-1], flush=True)
    s.run(on_increment=cb)
    return rows


def febio(d):
    subprocess.run([FEBIO, '-i', 'case.feb', '-silent'], cwd=d, capture_output=True,
                   env=dict(os.environ, LD_LIBRARY_PATH=os.path.join(P, 'third_party/mkl/lib'), OMP_NUM_THREADS='1'))
    ok = 'N O R M A L   T E R M I N A T I O N' in open(os.path.join(d, 'case.log')).read()
    f = os.path.join(d, 'rb.txt')
    R = read_log(f) if os.path.exists(f) else {}
    return ok, {t: v[0].tolist() for t, v in R.items()}


def at(rows, t):
    r = min(rows, key=lambda r: abs(r['t'] - t)); return r['x'] if abs(r['t'] - t) < 1e-6 else None


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'newton'
    Es = [float(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 else [10.0, 400.0]
    ns = [int(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else [10, 20, 40, 80]
    os.makedirs(OUT, exist_ok=True); res = []
    for E_up in Es:
        for n in ns:
            d = os.path.join(OUT, f'E{E_up:g}_n{n}'); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
            write(fp, E_up, n)
            ok, R = febio(d)
            print(f'E {E_up:g} n {n}: FEBio normal {ok}, states {len(R)}', flush=True)
            rows = gpu(fp, which)
            fx = lambda t: (R[round(t, 6)][0] if round(t, 6) in R else None)
            g05, g10 = at(rows, 0.5), at(rows, 1.0)
            f05, f10 = fx(0.5), fx(1.0)
            r = dict(E_up=E_up, n_increments=n, solver=which, gpu_x_t05=g05, gpu_x_t10=g10, gpu_creep_hold=None if g10 is None else g10 - g05,
                     gpu_all_converged=all(q['conv'] for q in rows), febio_normal=ok, febio_x_t05=f05, febio_x_t10=f10,
                     febio_creep_hold=None if (f05 is None or f10 is None) else f10 - f05, gpu_rows=rows)
            res.append(r)
            print(f"E {E_up:5g} n {n:3d} GPU x(0.5) {g05} x(1) {g10} creep {r['gpu_creep_hold']} conv {r['gpu_all_converged']} | "
                  f"FEBio ok {ok} x(0.5) {f05} x(1) {f10} creep {r['febio_creep_hold']}", flush=True)
            json.dump(res, open(os.path.join(HERE, f'v02_stick_creep_{which}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
