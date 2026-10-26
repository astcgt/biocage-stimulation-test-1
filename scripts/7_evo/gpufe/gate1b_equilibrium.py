"""Credibility gate 1b (solver verification): non-homogeneous equilibrium, GPU dynamic relaxation vs FEBio 4 (Newton).

A 6 x 2 x 2 mm bar (hex8 neo-Hookean / hex8 uncoupled Gent three-field / tet4 orthotropic cortex), x = 0 face clamped,
x = 6 face given a prescribed lift (bending + stretch); compares every node displacement and the reaction on the
prescribed face (FEBio reports reactions only for prescribed dofs).
Pass: max node displacement difference < 1e-3 of the largest displacement, total reaction difference < 1e-3.
"""
import os, sys, json, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feb, model as mdl, solver as slv
from gate1_patch import FEBIO, P, read_log, tets_from_hexes

OUT = os.path.join(P, 'human_study/evo/gpufe_verify/gate1b')


def bar(nx=12, ny=4, nz=4, L=(6.0, 2.0, 2.0)):
    gx, gy, gz = (np.linspace(0, L[i], n + 1) for i, n in enumerate((nx, ny, nz)))
    X = np.array([[x, y, z] for z in gz for y in gy for x in gx])
    idx = lambda i, j, k: k * (ny + 1) * (nx + 1) + j * (nx + 1) + i
    H = [[idx(i, j, k), idx(i + 1, j, k), idx(i + 1, j + 1, k), idx(i, j + 1, k), idx(i, j, k + 1), idx(i + 1, j, k + 1),
          idx(i + 1, j + 1, k + 1), idx(i, j + 1, k + 1)] for k in range(nz) for j in range(ny) for i in range(nx)]
    return X, np.array(H)


def write(path, X, E, etype, mat_xml, lift):
    clamp = np.where(X[:, 0] < 1e-9)[0]; end = np.where(X[:, 0] > X[:, 0].max() - 1e-9)[0]
    L = ['<?xml version="1.0" encoding="ISO-8859-1"?>', '<febio_spec version="2.5">', '<Module type="solid"/>',
         '<Control><time_steps>4</time_steps><step_size>0.25</step_size><max_refs>25</max_refs><max_ups>0</max_ups>'
         '<dtol>1e-7</dtol><etol>1e-9</etol><rtol>0</rtol><lstol>0.9</lstol><time_stepper><dtmin>0.01</dtmin><dtmax>0.25</dtmax>'
         '<max_retries>5</max_retries><opt_iter>10</opt_iter></time_stepper><analysis type="static"/></Control>',
         '<Material>' + mat_xml + '</Material>', '<Geometry><Nodes>']
    L += [f'<node id="{i + 1}">{x[0]:.12g},{x[1]:.12g},{x[2]:.12g}</node>' for i, x in enumerate(X)]
    L += ['</Nodes>', f'<Elements type="{etype}" mat="1" name="part">']
    L += [f'<elem id="{i + 1}">' + ','.join(str(v + 1) for v in e) + '</elem>' for i, e in enumerate(E)]
    L += ['</Elements>', '<NodeSet name="clamp">' + ''.join(f'<node id="{i + 1}"/>' for i in clamp) + '</NodeSet>',
          '<NodeSet name="end">' + ''.join(f'<node id="{i + 1}"/>' for i in end) + '</NodeSet>', '</Geometry><Boundary>',
          '<fix bc="x,y,z" node_set="clamp"/>',
          f'<prescribe bc="z" node_set="end"><scale lc="1">{lift[2]}</scale><relative>0</relative></prescribe>',
          f'<prescribe bc="x" node_set="end"><scale lc="1">{lift[0]}</scale><relative>0</relative></prescribe>',
          '</Boundary><LoadData><loadcurve id="1" type="linear"><point>0,0</point><point>1,1</point></loadcurve></LoadData>',
          '<Output><logfile><node_data data="ux;uy;uz" file="u.txt" delim=",">' + ','.join(str(i + 1) for i in range(len(X))) + '</node_data>'
          '<node_data data="Rx;Ry;Rz" file="react.txt" delim=",">' + ','.join(str(i + 1) for i in end) + '</node_data></logfile></Output></febio_spec>']
    open(path, 'w').write('\n'.join(L))
    return end


def run(name, X, E, etype, mat_xml, lift, opts=None):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
    clamp = write(fp, X, E, etype, mat_xml, lift)
    subprocess.run([FEBIO, '-i', 'case.feb', '-silent'], cwd=d, capture_output=True,
                   env=dict(os.environ, LD_LIBRARY_PATH=os.path.join(P, 'third_party/mkl/lib'), OMP_NUM_THREADS='1'))
    ok = 'N O R M A L   T E R M I N A T I O N' in open(os.path.join(d, 'case.log')).read()
    Uf = read_log(os.path.join(d, 'u.txt')); Rf = read_log(os.path.join(d, 'react.txt'))
    m = feb.read(fp); M = mdl.build(m)
    o = dict(verbose=False, tol_r=1e-7, tol_dx=1e-9); o.update(opts or {})
    s = slv.Solver(M, o); res = {}; iters = []
    def cb(sol, row):
        t = round(sol.t, 6); u = (sol.x - sol.X0).cpu().numpy()
        r = sol.residual(sol.x).cpu().numpy()[clamp]             # = -internal force: FEBio reaction sign (gate 1)
        uf = Uf[t]; sc = np.abs(uf).max()
        res[t] = dict(u_rel_err=float(np.abs(u - uf).max() / sc), R_sum_gpu=r.sum(0).tolist(), R_sum_febio=Rf[t].sum(0).tolist(),
                      R_rel_err=float(np.abs(r.sum(0) - Rf[t].sum(0)).max() / max(np.abs(Rf[t].sum(0)).max(), 1e-12)),
                      iters=row['iters'], converged=row['converged'], seconds=round(row['seconds'], 2))
    s.run(on_increment=cb)
    worst = max(max(v['u_rel_err'], v['R_rel_err']) for v in res.values())
    return dict(case=name, febio_normal=ok, worst=worst, passed=bool(ok and worst < 1e-3 and all(v['converged'] for v in res.values())), per_time=res)


def main():
    os.makedirs(OUT, exist_ok=True); X, H = bar(); T = tets_from_hexes(X, H)
    neo = '<material id="1" name="m" type="neo-Hookean"><density>1</density><E>100</E><v>0.3</v></material>'
    gent = ('<material id="1" name="cage" type="uncoupled prestrain elastic"><elastic type="Gent"><density>1</density><G>105.984</G>'
            '<Jm>0.7</Jm><k>671.234</k></elastic><prestrain type="prestrain gradient"><ramp lc="1">0.5</ramp><F0>1,0,0,0,1,0,0,0,1.25</F0></prestrain></material>')
    orth = ('<material id="1" name="Cortical" type="orthotropic elastic"><mat_axis type="vector"><a>0.952720,0.000000,0.303840</a>'
            '<d>0.000000,1.000000,0.000000</d></mat_axis><density>1</density><E1>8000</E1><E2>8000</E2><E3>12000</E3><G12>2857</G12>'
            '<G23>3677</G23><G31>444</G31><v12>0.4</v12><v23>0.3</v23><v31>0.35</v31></material>')
    cases = [run('neo_hex_bend', X, H, 'hex8', neo, (0.3, 0, 1.0)),
             run('gent_prestrain_hex_bend', X, H, 'hex8', gent, (0.1, 0, 0.6)),
             run('ortho_tet_bend', X, T, 'tet4', orth, (0.02, 0, 0.1))]
    rep = dict(gate='1b non-homogeneous equilibrium (GPU dynamic relaxation vs FEBio Newton)', all_passed=all(c['passed'] for c in cases), cases=cases)
    json.dump(rep, open(os.path.join(OUT, 'gate1b_report.json'), 'w'), indent=1)
    for c in cases:
        last = c['per_time'][max(c['per_time'])]
        print(f"{c['case']:26s} worst {c['worst']:.2e} iters/inc {[v['iters'] for v in c['per_time'].values()]} s {[v['seconds'] for v in c['per_time'].values()]} {'PASS' if c['passed'] else 'FAIL'}")
    print('ALL PASSED' if rep['all_passed'] else 'SOME FAILED')


if __name__ == '__main__':
    main()
