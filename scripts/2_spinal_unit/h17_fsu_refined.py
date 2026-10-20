"""Build an FSU .feb with the locally refined C3 / C4 meshes (h16) in place of the original bone tets.

Original bone SURFACE nodes keep their ids and coordinates (so the disc / annulus, facet cartilage and ligament springs
remain attached at the original vertices); refined / interior nodes get new ids. The disc's bone-side faces are tied
to the refined endplate triangles with FEBio 'tied-elastic' contact, so the new mid-edge endplate nodes are connected
too. Potting as in h08 (bone > 5 mm from the disc along the disc-normal axis = rigid).
Writes <out.feb> and <out.json> (incl. refined endplate triangles by node id, for h14 contact surfaces).
usage: python h17_fsu_refined.py <fsu.feb> <fsu.json> <frame.json> <C3.npz> <C4.npz> <out.feb>
"""
import sys, os, json, copy, xml.etree.ElementTree as ET, numpy as np
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
from cage_geom import Frame

fsu, fsu_info, frame, c3n, c4n, out = sys.argv[1:7]
POT_MM = 5.0
root = ET.parse(fsu).getroot(); g = root.find('Geometry'); F = Frame(frame)
X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
blocks = {eb.get('name'): eb for eb in g.findall('Elements')}
bone_names = [f'{v}_{k}{p}' for v in ('C3', 'C4') for k in ('cortical', 'trabecular') for p in ('', '_pot')]
old_bone = set()
for n in bone_names:
    for e in blocks[n]: old_bone |= set(int(x) for x in e.text.split(','))
other = set()
for eb in g.findall('Elements'):
    if eb.get('name') in bone_names: continue
    for e in eb: other |= set(int(x) for x in e.text.split(','))
for d in g.findall('DiscreteSet'):
    for e in d: other |= set(int(x) for x in e.text.split(','))
for s in g.findall('Surface'):
    for f in s: other |= set(int(x) for x in f.text.split(','))
info = json.load(open(fsu_info))
# disc zone in the frame for potting
disc_nodes = set()
for eb in g.findall('Elements'):
    if eb.get('name', '').startswith('disc_or_facet') and eb.get('name') != 'disc_or_facet_mat5':
        for e in eb: disc_nodes |= set(int(x) for x in e.text.split(','))
dz = F.to(np.array([X[i] for i in disc_nodes]))[:, 2]; z_top, z_bot = dz.max(), dz.min()

next_id = max(X) + 1; newX = {i: X[i] for i in X if i not in old_bone or i in other}
res = {}
for V, path in (('C3', c3n), ('C4', c4n)):
    z = np.load(path); P = z['P']
    row2id = {int(r): int(i) for i, r in zip(z['orig_ids'], z['orig_rows'])}
    for r in range(len(P)):
        if r not in row2id: row2id[r] = next_id; next_id += 1
        newX[row2id[r]] = P[r]
    for kind, T in (('cortical', z['cort']), ('trabecular', z['trab'])):
        ids = np.vectorize(row2id.get)(T)
        zc = F.to(P[T].mean(1))[:, 2]
        pot = (zc > z_top + POT_MM) if V == 'C3' else (zc < z_bot - POT_MM)
        res[(V, kind, '')] = ids[~pot]; res[(V, kind, '_pot')] = ids[pot]
    res[(V, 'endplate')] = np.vectorize(row2id.get)(z['endplate_tris'])
# orphans check: every old bone node referenced by other components must still exist
missing = [i for i in other if i not in newX]
assert not missing, f'{len(missing)} attachment nodes lost'
# rewrite nodes (consecutive ids required by FEBio 2.5)
ids_sorted = sorted(newX); ren = {i: k + 1 for k, i in enumerate(ids_sorted)}
nodes = g.find('Nodes'); nodes.clear(); nodes.set('name', 'FSU')
for i in ids_sorted: ET.SubElement(nodes, 'node', id=str(ren[i])).text = ','.join(f'{v:.6g}' for v in newX[i])
remap = lambda txt: ','.join(str(ren[int(v)]) for v in txt.split(','))
for eb in g.findall('Elements'):
    if eb.get('name') in bone_names:
        V, kind = eb.get('name').split('_')[:2]; pot = '_pot' if eb.get('name').endswith('_pot') else ''
        for e in list(eb): eb.remove(e)
        for tet in res[(V, kind, pot)]: ET.SubElement(eb, 'elem', id='0').text = ','.join(str(ren[int(i)]) for i in tet)
    else:
        for e in eb: e.text = remap(e.text)
for s in g.findall('Surface'):
    for f in s: f.text = remap(f.text)
for d in g.findall('DiscreteSet'):
    for e in d: e.text = remap(e.text)
k = 1
for eb in g.findall('Elements'):
    for e in eb: e.set('id', str(k)); k += 1
# tie: disc bone-side faces (all 4 nodes on the original endplate attachment set) -> refined endplate triangles
attach = {'C3': set(), 'C4': set()}
for V in ('C3', 'C4'):
    attach[V] = set(int(i) for i in np.unique(res[(V, 'endplate')]) if int(i) <= max(X))
for V in ('C3', 'C4'):
    s = ET.SubElement(g, 'Surface', name=f'{V}_endplate_refined')
    for j, t in enumerate(res[(V, 'endplate')]): ET.SubElement(s, 'tri3', id=str(j + 1)).text = ','.join(str(ren[int(i)]) for i in t)
    q = ET.SubElement(g, 'Surface', name=f'disc_on_{V}')
    j = 0
    for eb in g.findall('Elements'):
        if not (eb.get('name', '').startswith('disc_or_facet') and eb.get('name') != 'disc_or_facet_mat5'): continue
        for e in eb:
            tt = [int(v) for v in e.text.split(',')]
            for fc in ([0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
                quad = [tt[i] for i in fc]
                if all(ids_sorted[x - 1] in attach[V] for x in quad):
                    j += 1; ET.SubElement(q, 'quad4', id=str(j), elem=e.get('id')).text = ','.join(map(str, quad))
    sp = ET.SubElement(g, 'SurfacePair', name=f'tie_disc_{V}')
    ET.SubElement(sp, 'master', surface=f'{V}_endplate_refined'); ET.SubElement(sp, 'slave', surface=f'disc_on_{V}')
    c = ET.SubElement(root.find('Contact'), 'contact', type='tied-elastic', name=f'tie_disc_{V}', surface_pair=f'tie_disc_{V}')
    for kk, v in (('laugon', 0), ('penalty', 1), ('auto_penalty', 1), ('tolerance', 0.01), ('search_tol', 0.01)):
        ET.SubElement(c, kk).text = str(v)
# geometry section order
order = {'Nodes': 0, 'Elements': 1, 'NodeSet': 2, 'Surface': 3, 'SurfacePair': 4, 'DiscreteSet': 5}
kids = sorted(list(g), key=lambda c: order.get(c.tag, 9))
for c in list(g): g.remove(c)
for c in kids: g.append(c)
ET.ElementTree(root).write(out, encoding='ISO-8859-1', xml_declaration=True)
oi = dict(info); oi.update(refined=True, n_nodes=len(ids_sorted), n_elements=k - 1,
                           endplate_tris={V: [[ren[int(i)] for i in t] for t in res[(V, 'endplate')]] for V in ('C3', 'C4')},
                           disc_attach_ids={V: sorted(ren[i] for i in attach[V]) for V in ('C3', 'C4')})
json.dump(oi, open(out.replace('.feb', '.json'), 'w'))
print(json.dumps(dict(nodes=len(ids_sorted), elements=k - 1), indent=1))
