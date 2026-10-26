"""Red team r0001, F-0003: consequence of re-anchoring EVERY contact node at the start of each load increment
(scripts/7_evo/gpufe/newton.py:190-192, solver.py:356, contact.py:106-108) instead of keeping the stick point of a
sticking node (FEBio FESlidingElasticInterface.cpp:136 m_rsp = m_rs at step start, 880-881 m_rs = m_rsp while stuck).

1D replica of the same update rule: rigid block on a rigid plane, normal force N, tangential penalty k (N/mm),
shear T(t) = 0 -> T_max (< mu N, so it must STICK) -> 0, repeated n_cycles; n increments per half cycle.
  FEBio rule: anchor stays where the node stuck -> u = T / k, back to 0 after unloading.
  GPU rule  : anchor = position at increment start -> u_n = u_{n-1} + T_n / k ... permanent, grows with increments.
Also prints the surface pairs of the p062 cage contacts and an order-of-magnitude drift for the cage.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import re, numpy as np


def run(rule, k=1.0, N=100.0, mu=0.3, Tmax=10.0, n=20, cycles=3):
    a = 0.0; u = 0.0; hist = []
    for c in range(cycles):
        for T in np.r_[np.linspace(0, Tmax, n + 1)[1:], np.linspace(Tmax, 0, n + 1)[1:]]:
            if rule == 'gpu': a = u                       # re-anchor at increment start (tangential offset forgotten)
            u_trial = a + T / k                           # stick equilibrium: k (u - a) = T
            if abs(k * (u_trial - a)) > mu * N:           # slip (not reached here: Tmax < mu N)
                u_trial = a + np.sign(T) * mu * N / k + (u_trial - a - np.sign(T) * mu * N / k)
            u = u_trial; hist.append(u)
    return np.array(hist)


print('1D replica, k = 1 N/mm, T_max = 10 N < mu N = 30 N (must stick, elastic micro-slip 10 mm at peak in this unit system)')
for n in (10, 20, 40):
    f, g = run('febio', n=n), run('gpu', n=n)
    print(f'  increments per half cycle {n:3d}: residual drift after 3 cycles  FEBio rule {f[-1]:8.3f}   GPU rule {g[-1]:8.1f}  (= sum T_n / k, grows with n)')
# order of magnitude for the cage, p062: auto-penalty eps = penalty * E / (V/A); hex 0.2 mm thick layer
txt = open(os.path.join(_env.ROOT, 'human_study/al_v2/cases/p062_physio/case.feb')).read()
for m in re.finditer(r'<SurfacePair name="(cage_C[34])">(.{0,200})', txt): print('  ', m.group(1), re.sub(r'\s+', ' ', m.group(2))[:160])
A = 92.83; shear = 15.0                                 # footprint mm2 (case.json); peak face shear ~14 N (r0001_i001 p062)
for label, E, side in (('cage hard face E 649.5 MPa', 649.53, 0.2), ('cage soft face E 8.19 MPa', 8.194, 0.2), ('bone cortex E 12000 MPa (if bone is primary; element depth ~0.5 mm)', 12000.0, 0.5)):
    eps = 10.0 * E / side; K = eps * A
    per = shear / K
    print(f'  {label:65s}: eps {eps:9.0f} N/mm3, K {K:9.3g} N/mm, drift per increment {per:.2e} mm, x 6 dirs x 3 cycles x 20 increments = {per*360:.3f} mm')
