"""Credibility gate 1c (friction verification): sliding block, GPU explicit contact vs Coulomb's law and vs FEBio 4.

Two stacked blocks (neo-Hookean E 400 MPa, as hard PLCL); the lower block's base is clamped, the upper block's top face is
pressed down (t 0-0.5) and then dragged along x (t 0.5-1) by prescribed displacements. While the block slides, the
tangential / normal reaction on the top face must equal mu (Coulomb). Also checks the stick phase (no slip below mu N)
and compares with FEBio sliding-elastic (same penalty, auto_penalty).
Pass: |Fx / Fz - mu| < 2 % of mu once sliding (GPU); FEBio shown for reference.
"""
import os, sys, json, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feb, model as mdl, solver as slv
from gate1_patch import FEBIO, P, read_log
from gate1b_equilibrium import bar

OUT = os.path.join(P, 'human_study/evo/gpufe_verify/gate1c')


def write(path, mu, drag=0.3, press=0.02):
    Xa, Ha = bar(4, 4, 2, (4.0, 4.0, 2.0)); Xb, Hb = bar(3, 3, 2, (2.0, 2.0, 1.0))
    Xb = Xb + np.array([1.0, 1.0, 2.0])                       # upper block sits on the lower one (touching)
    X = np.vstack([Xa, Xb]); Hb = Hb + len(Xa)
    base = np.where(X[:, 2] < 1e-9)[0]; top = len(Xa) + np.where(Xb[:, 2] > 3.0 - 1e-9)[0]
    # contact faces: lower block top face (master), upper block bottom face (slave); outward normals
    mf = [[h[4], h[5], h[6], h[7]] for h in Ha if all(X[h[4:8], 2] > 2.0 - 1e-9)]
    sf = [[h[0], h[3], h[2], h[1]] for h in Hb if all(X[h[0:4], 2] < 2.0 + 1e-9)]
    neo = '<material id="1" name="m" type="neo-Hookean"><density>1</density><E>400</E><v>0.3</v></material>'
    L = ['<?xml version="1.0" encoding="ISO-8859-1"?>', '<febio_spec version="2.5">', '<Module type="solid"/>',
         '<Control><time_steps>40</time_steps><step_size>0.025</step_size><max_refs>25</max_refs><max_ups>0</max_ups>'
         '<dtol>1e-5</dtol><etol>1e-6</etol><rtol>0</rtol><lstol>0.9</lstol><time_stepper><dtmin>0.0001</dtmin><dtmax>0.025</dtmax>'
         '<max_retries>10</max_retries><opt_iter>20</opt_iter></time_stepper><analysis type="static"/></Control>',
         '<Material>' + neo + '</Material>', '<Geometry><Nodes>']
    L += [f'<node id="{i + 1}">{x[0]:.12g},{x[1]:.12g},{x[2]:.12g}</node>' for i, x in enumerate(X)]
    L += ['</Nodes>', '<Elements type="hex8" mat="1" name="lower">'] + [f'<elem id="{i + 1}">' + ','.join(str(v + 1) for v in e) + '</elem>' for i, e in enumerate(Ha)]
    L += ['</Elements>', '<Elements type="hex8" mat="1" name="upper">'] + [f'<elem id="{len(Ha) + i + 1}">' + ','.join(str(v + 1) for v in e) + '</elem>' for i, e in enumerate(Hb)]
    L += ['</Elements>', '<NodeSet name="base">' + ''.join(f'<node id="{i + 1}"/>' for i in base) + '</NodeSet>',
          '<NodeSet name="top">' + ''.join(f'<node id="{i + 1}"/>' for i in top) + '</NodeSet>',
          '<Surface name="master">' + ''.join(f'<quad4 id="{k + 1}">' + ','.join(str(v + 1) for v in f) + '</quad4>' for k, f in enumerate(mf)) + '</Surface>',
          '<Surface name="slave">' + ''.join(f'<quad4 id="{k + 1}">' + ','.join(str(v + 1) for v in f) + '</quad4>' for k, f in enumerate(sf)) + '</Surface>',
          '<SurfacePair name="pair"><master surface="master"/><slave surface="slave"/></SurfacePair>',
          '</Geometry><Boundary>', '<fix bc="x,y,z" node_set="base"/>', '<fix bc="y" node_set="top"/>',
          f'<prescribe bc="z" node_set="top"><scale lc="1">{-press}</scale><relative>0</relative></prescribe>',
          f'<prescribe bc="x" node_set="top"><scale lc="2">{drag}</scale><relative>0</relative></prescribe>',
          '</Boundary><Contact><contact type="sliding-elastic" name="c" surface_pair="pair"><laugon>0</laugon><penalty>1</penalty>'
          f'<auto_penalty>1</auto_penalty><two_pass>0</two_pass><search_tol>0.01</search_tol><search_radius>1.0</search_radius>'
          f'<symmetric_stiffness>0</symmetric_stiffness><tension>0</tension><fric_coeff>{mu}</fric_coeff></contact></Contact>',
          '<LoadData><loadcurve id="1" type="linear"><point>0,0</point><point>0.5,1</point><point>1,1</point></loadcurve>'
          '<loadcurve id="2" type="linear"><point>0,0</point><point>0.5,0</point><point>1,1</point></loadcurve></LoadData>',
          '<Output><logfile><node_data data="Rx;Ry;Rz" file="react.txt" delim=",">' + ','.join(str(i + 1) for i in top) + '</node_data>'
          '<node_data data="ux;uy;uz" file="u.txt" delim=",">' + ','.join(str(i + 1) for i in top) + '</node_data></logfile></Output></febio_spec>']
    open(path, 'w').write('\n'.join(L))
    return top


def run(mu):
    d = os.path.join(OUT, f'mu{mu}'); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
    top = write(fp, mu)
    subprocess.run([FEBIO, '-i', 'case.feb', '-silent'], cwd=d, capture_output=True,
                   env=dict(os.environ, LD_LIBRARY_PATH=os.path.join(P, 'third_party/mkl/lib'), OMP_NUM_THREADS='1'))
    ok = 'N O R M A L   T E R M I N A T I O N' in open(os.path.join(d, 'case.log')).read()
    Rf = read_log(os.path.join(d, 'react.txt')) if os.path.exists(os.path.join(d, 'react.txt')) else {}
    m = feb.read(fp); M = mdl.build(m)
    s = slv.Solver(M, dict(verbose=False, tol_r=1e-6, tol_dx=1e-8, search_every=20))
    rows = []
    def cb(sol, row):
        r = sol.residual(sol.x).cpu().numpy()[top].sum(0)
        t = round(sol.t, 6); rf = Rf.get(t)
        rows.append(dict(t=t, gpu_F=r.tolist(), gpu_ratio=float(abs(r[0]) / max(abs(r[2]), 1e-12)),
                         febio_F=rf.sum(0).tolist() if rf is not None else None,
                         febio_ratio=float(abs(rf.sum(0)[0]) / max(abs(rf.sum(0)[2]), 1e-12)) if rf is not None else None,
                         stick_frac=float(np.mean([p.stick.float().mean().item() for p in sol.passes])),
                         iters=row['iters'], converged=row['converged']))
    s.run(on_increment=cb)
    slide = [r for r in rows if r['t'] >= 0.85]
    err = max(abs(r['gpu_ratio'] - mu) / mu for r in slide)
    return dict(mu=mu, febio_normal=ok, sliding_ratio_rel_err=err, passed=bool(err < 0.02 and all(r['converged'] for r in rows)), rows=rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    cases = [run(0.2), run(0.5)]
    rep = dict(gate='1c friction: sliding block vs Coulomb and FEBio', all_passed=all(c['passed'] for c in cases), cases=cases)
    json.dump(rep, open(os.path.join(OUT, 'gate1c_report.json'), 'w'), indent=1)
    for c in cases:
        print(f"mu {c['mu']}: sliding Fx/Fz rel err {c['sliding_ratio_rel_err']:.3e} FEBio normal {c['febio_normal']} {'PASS' if c['passed'] else 'FAIL'}")
        for r in c['rows'][::4] + [c['rows'][-1]]:
            print(f"   t {r['t']:.3f} GPU Fx/Fz {r['gpu_ratio']:.4f} Fz {r['gpu_F'][2]:9.3f} stick {r['stick_frac']:.2f} | FEBio {r['febio_ratio'] if r['febio_ratio'] is None else round(r['febio_ratio'], 4)} Fz {None if r['febio_F'] is None else round(r['febio_F'][2], 3)}  it {r['iters']}")
    print('ALL PASSED' if rep['all_passed'] else 'SOME FAILED')


if __name__ == '__main__':
    main()
