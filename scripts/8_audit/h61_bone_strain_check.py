"""usage: python h61_bone_strain_check.py <set/design/w_window> ...   -> human_study/qa/bone_strain_check.json
Bone deformation in the LAST CONVERGED state of stopped windows whose log reports inverted bone elements (PI question 2026-11-22:
is 'bone element inversion' a real overload or a numerical event?). For every tet4 bone element: volume ratio J = det F and the largest
absolute principal Green-Lagrange strain, from the nodal displacements of the last state in case.xplt; plus the Jacobian values the log
prints for the inverted bone elements in the failed trial iterations."""
import sys, os, re, json, numpy as np, xml.etree.ElementTree as ET
EV = '/raid/jupyter-alz.ee09/projects/claude-work/biocage-evo'; sys.path[:0] = [EV + '/common', EV + '/methods']; import xplt
R = '/raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026/human_study/al_v2/'
out = []
for wd in sys.argv[1:]:
    cd = R + wd; g = ET.parse(os.path.join(os.path.dirname(cd), 'case.feb') if not os.path.exists(cd + '/case.feb') else cd + '/case.feb').getroot().find('Geometry')
    X = {int(n.get('id')): [float(v) for v in n.text.split(',')] for n in g.find('Nodes')}; ids = np.array(sorted(X)); pos = {i: k for k, i in enumerate(ids)}; X0 = np.array([X[i] for i in ids])
    bone, rng, eid = [], {}, 0
    for eb in g.findall('Elements'):
        first = eid + 1
        for e in eb:
            eid = int(e.get('id'))
            if eb.get('type') == 'tet4' and ('cortical' in eb.get('name') or 'trabecular' in eb.get('name')): bone.append([pos[int(v)] for v in e.text.split(',')])
        rng[eb.get('name')] = (first, eid)
    T = np.array(bone); st = xplt.read(cd + '/case.xplt')['states'][-1]; U = next(iter(st['node']['displacement'].values()))
    def edges(P): return np.stack([P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]], P[T[:, 3]] - P[T[:, 0]]], axis=2)
    D0, D1 = edges(X0), edges(X0 + U[:len(X0)]); F = D1 @ np.linalg.inv(D0); J = np.linalg.det(F); E = 0.5 * (np.swapaxes(F, 1, 2) @ F - np.eye(3)); pe = np.abs(np.linalg.eigvalsh(E)).max(1)
    lg = open(cd + '/case.log', errors='ignore').read(); blk = lambda e: next((b for b, (a, z) in rng.items() if a <= e <= z), '?')
    nj = re.findall(r'Negative jacobian was detected at element (\d+) at gauss point \d+\s*\*?\s*\n\s*\*?\s*jacobian = ([-0-9.eE+]+)', lg)
    bj = [float(j) for e, j in nj if 'cortical' in blk(int(e)) or 'trabecular' in blk(int(e))]
    conv = re.findall(r'converged at time : ([0-9.eE+-]+)', lg)
    r = dict(window=wd, t_last_state=st['time'], t_last_converged=float(conv[-1]) if conv else None, n_bone_tets=len(T), J_min=float(J.min()), J_p01=float(np.percentile(J, 0.1)), J_max=float(J.max()),
             strain_max=float(pe.max()), strain_p999=float(np.percentile(pe, 99.9)), strain_median=float(np.median(pe)),
             log_bone_inversions=len(bj), log_bone_J_min=min(bj) if bj else None, log_bone_J_median=float(np.median(bj)) if bj else None, first_inverted_block=blk(int(nj[0][0])) if nj else None)
    out.append(r); print(json.dumps(r), flush=True)
json.dump(out, open('/raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026/human_study/qa/bone_strain_check.json', 'w'), indent=1)
