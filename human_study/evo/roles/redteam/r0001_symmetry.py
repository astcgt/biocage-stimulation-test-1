"""Red team r0001, I-001: is the p062 physio model (case.feb) left-right symmetric about Y = 0?
For every element block: mirror its nodes y -> -y and measure the distance to the nearest node of the same block.
Also: discrete springs (ligaments) and their mirror partners, cage nodes, facet contact surfaces.
usage: python -I r0001_symmetry.py [case_dir]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import json, numpy as np, xml.etree.ElementTree as ET
from scipy.spatial import cKDTree
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
cd = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else 'human_study/al_v2/cases/p062_physio')
root = ET.parse(os.path.join(cd, 'case.feb')).getroot(); g = root.find('Geometry')
X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
ids = np.array(sorted(X)); P = np.array([X[i] for i in ids]); idx = {i: k for k, i in enumerate(ids)}
print('nodes', len(ids), 'y range', P[:, 1].min(), P[:, 1].max(), 'mean y', P[:, 1].mean())


def mirror_stats(Q, name):
    if len(Q) == 0: return
    t = cKDTree(Q); M = Q * [1, -1, 1]; dist, _ = t.query(M)
    # centroid / first moments: a symmetric set has mean y = 0
    print(f'{name:28s} n={len(Q):6d} mean_y={Q[:,1].mean():+8.4f}  mirror-gap median={np.median(dist):.4f} p95={np.percentile(dist,95):.4f} max={dist.max():.4f} mm')
    return dict(n=len(Q), mean_y=float(Q[:, 1].mean()), med=float(np.median(dist)), p95=float(np.percentile(dist, 95)), max=float(dist.max()))


out = {}
for eb in g.findall('Elements'):
    nn = sorted({int(v) for e in eb for v in e.text.split(',')})
    out[eb.get('name')] = mirror_stats(np.array([X[i] for i in nn]), eb.get('name'))
# discrete springs
for ds in g.findall('DiscreteSet'):
    pairs = [tuple(int(v) for v in d.text.split(',')) for d in ds]
    Q = np.array([(X[a] + X[b]) / 2 for a, b in pairs])
    out['spring:' + ds.get('name')] = mirror_stats(Q, 'springs ' + ds.get('name'))
# surfaces
for s in g.findall('Surface'):
    nn = sorted({int(v) for e in s for v in e.text.split(',')})
    out['surf:' + s.get('name')] = mirror_stats(np.array([X[i] for i in nn]), 'surf ' + s.get('name'))
json.dump(out, open(os.path.join(os.path.dirname(__file__), 'r0001_symmetry_' + os.path.basename(cd) + '.json'), 'w'), indent=1)
