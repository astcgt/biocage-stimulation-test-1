"""Verifier r0001, V03: which material branches does gate 1 actually exercise?
- fiber stretch In = a0.C.a0 of both annulus fibers in hm_fiber_hex (is the compression branch In < 1 tested?)
- volume ratio J and rotation angle of the gate-1 deformation gradient (near-incompressibility / large rotation coverage)
- Gent locking margin (I1~ - 3) / Jm in gent_prestrain_hex
usage: python -I human_study/evo/roles/verifier/v03_gate1_coverage.py
"""
import os, sys, site, json
sys.path.append(site.getusersitepackages())
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(P, 'scripts/7_evo/gpufe'))
import feb, mech, model as mdl
from gate1_patch import Fdef

out = {}
J = float(np.linalg.det(Fdef)); Rm = np.linalg.svd(Fdef); R = Rm[0] @ Rm[2]
out['F'] = dict(J=J, rotation_deg=float(np.degrees(np.arccos((np.trace(R) - 1) / 2))))
fp = os.path.join(P, 'human_study/evo/gpufe_verify/gate1/hm_fiber_hex/case.feb'); m = feb.read(fp)
b = m['blocks'][0]; mt = m['mats'][b['mat']]; X = m['X']
# gate 1 rotates the mesh X -> X rot^T and applies the same Fdef in global axes
axes = mech.local_axes_nodes(X[b['conn']], mt['axis'][1])
C = Fdef.T @ Fdef
for k, f in enumerate(mt['solids'][1:]):
    a = mdl._fiber_dirs(axes, f['theta'], f['phi'])
    In = np.einsum('ei,ij,ej->e', a, C, a)
    out[f'fiber{k}_In'] = dict(min=float(In.min()), max=float(In.max()), compressed=bool((In < 1).any()), stretched=bool((In > 1).any()))
# Gent locking margin
g = m = feb.read(os.path.join(P, 'human_study/evo/gpufe_verify/gate1/gent_prestrain_hex/case.feb'))
mt = [v for v in g['mats'].values()][0]; Jm = mt['elastic']['Jm']
lc = g['lcs'][2]; worst = 0
for t in (0.5, 1.0):
    r = mt['ramp'][1] * lc(t); Fp = np.eye(3) * (1 - r) + mt['F0'] * r; Fh = Fdef @ Fp
    Jh = np.linalg.det(Fh); I1t = Jh**(-2 / 3) * np.trace(Fh.T @ Fh)
    out[f'gent_t{t}'] = dict(ramp=r, I1t_minus3_over_Jm=float((I1t - 3) / Jm))
json.dump(out, open(os.path.join(HERE, 'v03_gate1_coverage.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
