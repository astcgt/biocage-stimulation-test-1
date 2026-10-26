"""Credibility gate 1 (code verification): homogeneous-deformation patch tests, GPU solver vs FEBio 4 on identical input.

Every node of a small block gets the same affine displacement u = (F - I) X * lc(t) (general F with shear), so each
material / element / prestrain formula is checked exactly: element Cauchy stress and nodal reaction forces.
Cases: neo-Hookean (hex8, tet4), orthotropic cortex with the study's vector axis (tet4), Holmes-Mow + 2 fiber-exp-pow with
'local' axes (hex8, annulus), uncoupled prestrain Gent (hex8, three-field, ramped F0 as the cage insertion), nonlinear
spring with a 'smooth' ligament load curve.
Pass: max relative difference < 1e-3 (stress normalised by the largest stress component).
usage: python gate1_patch.py [outdir]
"""
import os, sys, json, subprocess, numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feb, model as mdl, solver as slv

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FEBIO = os.path.join(P, 'third_party/FEBio/cbuild/bin/febio4')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(P, 'human_study/evo/gpufe_verify/gate1')
Fdef = np.array([[1.06, 0.03, 0.02], [0.01, 0.95, 0.04], [0.02, -0.03, 1.09]])
LIG_LC = os.path.join(P, 'human_study/fsu/C34_fsu_refined.feb')

HEX_NODES = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float)
TET_SPLIT = [[0, 1, 3, 4], [1, 2, 3, 6], [1, 3, 4, 6], [3, 4, 6, 7], [1, 4, 5, 6]]   # 5-tet split of the cube (positive volume ordering fixed below)


def grid(n=2, size=2.0):
    g = np.linspace(0, size, n + 1); X = np.array([[x, y, z] for z in g for y in g for x in g])
    idx = lambda i, j, k: k * (n + 1)**2 + j * (n + 1) + i
    hexes = []
    for k in range(n):
        for j in range(n):
            for i in range(n):
                hexes.append([idx(i, j, k), idx(i + 1, j, k), idx(i + 1, j + 1, k), idx(i, j + 1, k),
                              idx(i, j, k + 1), idx(i + 1, j, k + 1), idx(i + 1, j + 1, k + 1), idx(i, j + 1, k + 1)])
    return X, np.array(hexes)


def tets_from_hexes(X, H):
    T = []
    for h in H:
        for t in TET_SPLIT:
            tt = [h[i] for i in t]
            P_ = X[tt]
            if np.linalg.det(np.c_[P_[1] - P_[0], P_[2] - P_[0], P_[3] - P_[0]]) < 0: tt[1], tt[2] = tt[2], tt[1]
            T.append(tt)
    return np.array(T)


def write_feb(path, X, elems, etype, mat_xml, lc_extra='', springs=None, rot=None):
    if rot is not None: X = X @ rot.T
    U = X @ (Fdef - np.eye(3)).T
    L = ['<?xml version="1.0" encoding="ISO-8859-1"?>', '<febio_spec version="2.5">', '<Module type="solid"/>',
         '<Control><time_steps>2</time_steps><step_size>0.5</step_size><max_refs>15</max_refs><max_ups>0</max_ups>'
         '<dtol>1e-6</dtol><etol>1e-8</etol><rtol>0</rtol><lstol>0.9</lstol><time_stepper><dtmin>0.01</dtmin><dtmax>0.5</dtmax>'
         '<max_retries>5</max_retries><opt_iter>10</opt_iter></time_stepper><analysis type="static"/></Control>',
         '<Material>' + mat_xml + '</Material>', '<Geometry><Nodes>']
    L += [f'<node id="{i + 1}">{x[0]:.12g},{x[1]:.12g},{x[2]:.12g}</node>' for i, x in enumerate(X)]
    L.append('</Nodes>')
    if len(elems):
        L.append(f'<Elements type="{etype}" mat="1" name="part">')
        L += [f'<elem id="{i + 1}">' + ','.join(str(v + 1) for v in e) + '</elem>' for i, e in enumerate(elems)]
        L.append('</Elements>')
    if springs is not None:
        L.append('<DiscreteSet name="spr">' + ''.join(f'<delem>{a + 1},{b + 1}</delem>' for a, b in springs) + '</DiscreteSet>')
    L += [f'<NodeSet name="n{i + 1}"><node id="{i + 1}"/></NodeSet>' for i in range(len(X))]
    L.append('</Geometry><Boundary>')
    for i in range(len(X)):
        for d, c in enumerate('xyz'):
            L.append(f'<prescribe bc="{c}" node_set="n{i + 1}"><scale lc="1">{U[i, d]:.12g}</scale><relative>0</relative></prescribe>')
    L.append('</Boundary>')
    if springs is not None:
        L.append('<Discrete><discrete_material id="1" name="spr" type="nonlinear spring"><force lc="2">0.2</force></discrete_material>'
                 '<discrete discrete_set="spr" dmat="1"/></Discrete>')
    L.append('<LoadData><loadcurve id="1" type="linear"><point>0,0</point><point>1,1</point></loadcurve>' + lc_extra + '</LoadData>')
    L.append('<Output><logfile>'
             + (f'<element_data data="sx;sy;sz;sxy;syz;sxz" file="stress.txt" delim=",">' + ','.join(str(i + 1) for i in range(len(elems))) + '</element_data>' if len(elems) else '')
             + f'<node_data data="Rx;Ry;Rz" file="react.txt" delim=",">' + ','.join(str(i + 1) for i in range(len(X))) + '</node_data>'
             + '</logfile></Output></febio_spec>')
    open(path, 'w').write('\n'.join(L))


def read_log(path):
    blocks, t = {}, None
    for line in open(path):
        if line.startswith('*Time'): t = round(float(line.split('=')[1]), 6); blocks[t] = []
        elif line[:1].isdigit(): blocks[t].append([float(v) for v in line.split(',')[1:]])
    return {k: np.array(v) for k, v in blocks.items()}


def run_case(name, X, elems, etype, mat_xml, lc_extra='', springs=None, rot=None):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
    write_feb(fp, X, elems, etype, mat_xml, lc_extra, springs, rot)
    r = subprocess.run([FEBIO, '-i', 'case.feb', '-silent'], cwd=d, capture_output=True, text=True,
                       env=dict(os.environ, LD_LIBRARY_PATH=os.path.join(P, 'third_party/mkl/lib'), OMP_NUM_THREADS='1'))
    ok_febio = 'N O R M A L   T E R M I N A T I O N' in open(os.path.join(d, 'case.log')).read()
    S_fe = read_log(os.path.join(d, 'stress.txt')) if len(elems) else {}
    R_fe = read_log(os.path.join(d, 'react.txt'))
    m = feb.read(fp); M = mdl.build(m)
    s = slv.Solver(M, dict(verbose=False, min_iter=1, max_iter=5))
    res = {}
    for st in m['steps']:
        n = st['control']['time_steps']; h = st['control']['step_size']
        s._step_setup(st, 0.0, n * h)
        for k in range(1, n + 1):
            s.t = k * h; s._update_fixed_val(); x = s.fixed_val.clone()
            f, sig = s.internal(x, want_stress=True)
            s.springs_f(x, f.neg_())                               # f = -(internal force incl. springs) = FEBio reaction sign
            t = round(s.t, 6)
            out = dict()
            if len(elems):
                Sg = list(sig.values())[0].cpu().numpy(); Sv = np.c_[Sg[:, 0, 0], Sg[:, 1, 1], Sg[:, 2, 2], Sg[:, 0, 1], Sg[:, 1, 2], Sg[:, 0, 2]]
                Sf = S_fe[t]; sc = max(np.abs(Sf).max(), 1e-12)
                out['stress_rel_err'] = float(np.abs(Sv - Sf).max() / sc); out['stress_scale'] = float(sc)
            Rg = f.cpu().numpy(); Rf = R_fe[t]; sc = max(np.abs(Rf).max(), 1e-12)
            out['reaction_rel_err'] = float(np.abs(Rg - Rf).max() / sc); out['reaction_scale'] = float(sc)
            res[t] = out
    worst = max(max(v.values() if False else [v.get('stress_rel_err', 0), v['reaction_rel_err']]) for v in res.values())
    return dict(case=name, febio_normal=ok_febio, worst_rel_err=worst, passed=bool(ok_febio and worst < 1e-3), per_time=res)


def main():
    os.makedirs(OUT, exist_ok=True)
    X, H = grid(2, 2.0); T = tets_from_hexes(X, H)
    rot = np.linalg.qr(np.array([[0.9, 0.2, 0.1], [-0.3, 0.8, 0.4], [0.1, -0.5, 0.9]]))[0]
    cases = []
    neo = '<material id="1" name="m" type="neo-Hookean"><density>1</density><E>100</E><v>0.3</v></material>'
    cases.append(run_case('neo_hex', X, H, 'hex8', neo))
    cases.append(run_case('neo_tet', X, T, 'tet4', neo, rot=rot))
    orth = ('<material id="1" name="Cortical" type="orthotropic elastic"><mat_axis type="vector"><a>0.952720,0.000000,0.303840</a>'
            '<d>0.000000,1.000000,0.000000</d></mat_axis><density>1</density><E1>8000</E1><E2>8000</E2><E3>12000</E3><G12>2857</G12>'
            '<G23>3677</G23><G31>444</G31><v12>0.4</v12><v23>0.3</v23><v31>0.35</v31></material>')
    cases.append(run_case('ortho_tet', X, T, 'tet4', orth))
    mix = ('<material id="1" name="ann" type="solid mixture"><mat_axis type="local">4,8,3</mat_axis>'
           '<solid type="Holmes-Mow"><density>1</density><E>5.0</E><v>0.4</v><beta>3.4</beta></solid>'
           '<solid type="fiber-exp-pow"><alpha>65</alpha><beta>2</beta><ksi>0.296</ksi><fiber type="angles"><theta>0</theta><phi>45</phi></fiber></solid>'
           '<solid type="fiber-exp-pow"><alpha>65</alpha><beta>2</beta><ksi>0.296</ksi><fiber type="angles"><theta>0</theta><phi>135</phi></fiber></solid></material>')
    cases.append(run_case('hm_fiber_hex', X, H, 'hex8', mix, rot=rot))
    gent = ('<material id="1" name="cage" type="uncoupled prestrain elastic"><elastic type="Gent"><density>1</density><G>105.984</G>'
            '<Jm>0.7</Jm><k>671.234</k></elastic><prestrain type="prestrain gradient"><ramp lc="2">1</ramp><F0>1,0,0,0,1,0,0,0,1.25</F0></prestrain></material>')
    cases.append(run_case('gent_prestrain_hex', X, H, 'hex8', gent,
                          lc_extra='<loadcurve id="2" type="linear"><point>0,0</point><point>0.5,1</point><point>1,0.3</point></loadcurve>'))
    # spring: ligament curve (smooth), two nodes stretched by the affine map
    root = __import__('xml.etree.ElementTree', fromlist=['x']).parse(LIG_LC).getroot()
    lc9 = [lc for lc in root.find('LoadData') if lc.get('id') == '9'][0]
    pts = ''.join(f'<point>{p.text}</point>' for p in lc9.findall('point'))
    Xs = np.array([[0, 0, 0], [3.0, 1.0, 12.0], [1.0, -2.0, 0.5], [4.0, 0.0, 9.0]])
    cases.append(run_case('spring_smooth', Xs, np.zeros((0, 4), int), 'tet4', neo,
                          lc_extra=f'<loadcurve id="2" type="smooth">{pts}</loadcurve>', springs=[(0, 1), (2, 3)]))
    rep = dict(gate='1 patch tests (GPU vs FEBio 4, identical input)', all_passed=all(c['passed'] for c in cases), cases=cases)
    json.dump(rep, open(os.path.join(OUT, 'gate1_report.json'), 'w'), indent=1)
    for c in cases: print(f"{c['case']:22s} FEBio normal {c['febio_normal']}  worst rel err {c['worst_rel_err']:.2e}  {'PASS' if c['passed'] else 'FAIL'}")
    print('ALL PASSED' if rep['all_passed'] else 'SOME FAILED')


if __name__ == '__main__':
    main()
