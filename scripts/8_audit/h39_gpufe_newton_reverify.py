#!/usr/bin/env python3
"""h39: re-run the gpufe benchmarks on the CURRENT Newton solver (findings F-0014 / F-0026: gates 1b and 1c ran on the old dynamic-relaxation solver).

Does not run FEBio and does not write to ../biocage-evo/results: FEBio values are the ones stored in the gate reports.
  bend  gate 1b bars: resultant reaction vs stored FEBio; displacement vs the old solver (whose FEBio difference is stored)
  slide gate 1c blocks: Fx/Fz while sliding vs the Coulomb law, Fx and Fz vs stored FEBio; mu 0.35 (production value) has no stored FEBio run
  stick gate 1d: cyclic shear below the limit, tangential force at cycle ends
  hold  verifier V07 / NUM-13: constant force below the limit, creep during the hold (threshold 0.01 mm)
H39_RES_ABS overrides the solver's absolute convergence floor (default 0.05 N); outputs then get the suffix _strict.
usage: CUDA_VISIBLE_DEVICES=3 python h39_gpufe_newton_reverify.py [bend,slide,stick,hold]
"""
import os, sys, json, time, importlib.util, traceback, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVO = os.path.join(os.path.dirname(ROOT), 'biocage-evo')
OUT = os.path.join(ROOT, 'human_study/figures/gpu_solver_agreement/newton_reverify')
sys.path.insert(0, os.path.join(EVO, 'gpufe'))
sys.dont_write_bytecode = True
import feb, model as mdl, solver as slv, newton
import gate1b_equilibrium as g1b, gate1c_friction as g1c, gate1d_stick_memory as g1d
from gate1_patch import tets_from_hexes
VER = os.path.join(EVO, 'results/gpufe_verify')
RES = os.environ.get('H39_RES_ABS')
OPT = dict(verbose=False, log_every=0); OPT.update(dict(res_abs=float(RES)) if RES else {})
SUF = '_strict' if RES else ''


def save(name, obj): json.dump(obj, open(os.path.join(OUT, name + SUF + '.json'), 'w'), indent=1)


def bend():
    X, H = g1b.bar(); T = tets_from_hexes(X, H)
    neo = '<material id="1" name="m" type="neo-Hookean"><density>1</density><E>100</E><v>0.3</v></material>'
    gent = ('<material id="1" name="cage" type="uncoupled prestrain elastic"><elastic type="Gent"><density>1</density><G>105.984</G>'
            '<Jm>0.7</Jm><k>671.234</k></elastic><prestrain type="prestrain gradient"><ramp lc="1">0.5</ramp><F0>1,0,0,0,1,0,0,0,1.25</F0></prestrain></material>')
    orth = ('<material id="1" name="Cortical" type="orthotropic elastic"><mat_axis type="vector"><a>0.952720,0.000000,0.303840</a>'
            '<d>0.000000,1.000000,0.000000</d></mat_axis><density>1</density><E1>8000</E1><E2>8000</E2><E3>12000</E3><G12>2857</G12>'
            '<G23>3677</G23><G31>444</G31><v12>0.4</v12><v23>0.3</v23><v31>0.35</v31></material>')
    stored = {c['case']: c for c in json.load(open(f'{VER}/gate1b/gate1b_report.json'))['cases']}
    res = []
    for name, E, et, mat, lift in (('neo_hex_bend', H, 'hex8', neo, (0.3, 0, 1.0)), ('gent_prestrain_hex_bend', H, 'hex8', gent, (0.1, 0, 0.6)), ('ortho_tet_bend', T, 'tet4', orth, (0.02, 0, 0.1))):
        d = os.path.join(OUT, 'cases', name); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
        end = g1b.write(fp, X, E, et, mat, lift)
        rec = dict(case=name, per_time={})
        try:
            s = newton.NewtonSolver(mdl.build(feb.read(fp)), dict(OPT)); un = {}
            def cb(sol, row):
                t = round(sol.t, 6); r = sol.residual(sol.x).cpu().numpy()[end].sum(0); un[t] = sol.x.cpu().numpy().copy()
                rf = np.array(stored[name]['per_time'][str(t)]['R_sum_febio'])
                rec['per_time'][str(t)] = dict(R_gpu=r.tolist(), R_febio=rf.tolist(), R_rel_err=float(np.linalg.norm(r - rf) / np.linalg.norm(rf)), iters=row['iters'], converged=row['converged'])
            s.run(on_increment=cb)
            d0 = slv.Solver(mdl.build(feb.read(fp)), dict(verbose=False, tol_r=1e-7, tol_dx=1e-9)); ud = {}
            d0.run(on_increment=lambda sol, row: ud.__setitem__(round(sol.t, 6), (sol.x - sol.X0).cpu().numpy().copy()))
            X0 = d0.X0.cpu().numpy()
            for t, x in un.items():
                u = x - X0; rec['per_time'][str(t)]['u_vs_old_solver'] = float(np.abs(u - ud[t]).max() / np.abs(ud[t]).max())
                rec['per_time'][str(t)]['old_solver_u_vs_febio'] = stored[name]['per_time'][str(t)]['u_rel_err']
        except Exception as e:
            rec['error'] = repr(e)[:300]
        res.append(rec); save('bend', res); print(name, rec.get('error'), {t: round(v['R_rel_err'], 12) for t, v in rec['per_time'].items()}, flush=True)


def slide():
    stored = {c['mu']: {r['t']: r for r in c['rows']} for c in json.load(open(f'{VER}/gate1c/gate1c_report.json'))['cases']}
    res = []
    for mu in (0.2, 0.35, 0.5):
        d = os.path.join(OUT, 'cases', f'slide_mu{mu}'); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
        top = g1c.write(fp, mu); rows = []
        rec = dict(mu=mu, rows=rows); t0 = time.time()
        try:
            s = newton.NewtonSolver(mdl.build(feb.read(fp)), dict(OPT))
            def cb(sol, row):
                r = sol.residual(sol.x).cpu().numpy()[top].sum(0); t = round(sol.t, 6); p = sol.passes[0]; inc = p.force_n > 0
                q = stored.get(mu, {}).get(t)
                rows.append(dict(t=t, F=r.tolist(), ratio=float(abs(r[0]) / max(abs(r[2]), 1e-12)), stick=float(p.stick[inc].float().mean()) if bool(inc.any()) else 0.0,
                                 febio_F=q['febio_F'] if q else None, old_ratio=q['gpu_ratio'] if q else None, iters=row['iters'], converged=row['converged']))
            s.run(on_increment=cb)
            sl = [r for r in rows if r['t'] >= 0.85]
            rec.update(ratio_err_max=max(abs(r['ratio'] - mu) / mu for r in sl), ratio_mean=float(np.mean([r['ratio'] for r in sl])))
        except Exception as e:
            rec['error'] = repr(e)[:300]
        rec['seconds'] = time.time() - t0
        res.append(rec); save('slide', res); print('mu', mu, 'n', len(rows), rec.get('ratio_err_max'), rec.get('error'), round(rec['seconds']), flush=True)


def stick():
    g1d.OUT = os.path.join(OUT, 'cases', 'stick'); os.makedirs(g1d.OUT, exist_ok=True); res = []
    for n in (10, 20, 40):
        try:
            r = g1d.run(n, False); r.pop('rows', None)
        except Exception as e:
            r = dict(n=n, error=repr(e)[:300])
        res.append(r); save('stick', res); print(r, flush=True)


def hold():
    spec = importlib.util.spec_from_file_location('v07', f'{EVO}/work/agents/verifier/v07_stick_creep.py'); v07 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v07)
    res = []
    for ratio in (0.5, 0.9):
        v07.RATIO = ratio
        for n in (10, 20, 40):
            d = os.path.join(OUT, 'cases', f'hold_r{ratio}_n{n}'); os.makedirs(d, exist_ok=True); fp = os.path.join(d, 'case.feb')
            v07.write(fp, 10.0, n); rows = []; rec = dict(ratio=ratio, E=10.0, n=n)
            try:
                s = newton.NewtonSolver(mdl.build(feb.read(fp)), dict(OPT))
                s.run(on_increment=lambda sol, row: rows.append(dict(t=round(sol.t, 6), x=row['rigid'][3]['x'][0], conv=row['converged'])))
            except Exception as e:
                rec['error'] = repr(e)[:300]
            rec['last_t'] = rows[-1]['t'] if rows else None
            x05 = [r['x'] for r in rows if abs(r['t'] - 0.5) < 1e-6]
            if x05 and rows[-1]['t'] > 0.5: rec['creep_mm'] = rows[-1]['x'] - x05[0]; rec['x05'] = x05[0]
            res.append(rec); save('hold', res); print(rec, flush=True)


if __name__ == '__main__':
    which = (sys.argv[1] if len(sys.argv) > 1 else 'bend,slide,stick,hold').split(',')
    for w in which:
        try: globals()[w]()
        except Exception: traceback.print_exc()
