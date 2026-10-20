"""Extract C3 / C4 bone surfaces and the C3-C4 disc from the FEBio 26yoF C34.feb model
(Herron et al., J Biomech 2020; SimTK febiocervical) and write STLs to 'human bone/'.

usage: python h01_extract_febio.py <path/to/C34.feb> <out_dir>
"""
import sys, json, xml.etree.ElementTree as ET
import numpy as np, trimesh

feb, out = sys.argv[1], sys.argv[2]
root = ET.parse(feb).getroot()
geo = root.find('Geometry')

nodes = {}
for nb in geo.findall('Nodes'):
    for n in nb.findall('node'):
        nodes[int(n.get('id'))] = [float(v) for v in n.text.split(',')]
ids = np.array(sorted(nodes)); X = np.array([nodes[i] for i in ids])
idx = {i: k for k, i in enumerate(ids)}

mats = {m.get('id'): m.get('name') for m in root.find('Material').findall('material')}

TET_F = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2)]
HEX_F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def boundary(conn, faces):
    """Faces used by exactly one element = outer surface (orientation from element)."""
    F = np.concatenate([conn[:, f] for f in faces])
    key = np.sort(F, axis=1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return F[cnt[inv.ravel()] == 1]


def to_mesh(F):
    if F.shape[1] == 4:
        F = np.concatenate([F[:, [0, 1, 2]], F[:, [0, 2, 3]]])
    m = trimesh.Trimesh(X, np.vectorize(idx.get)(F), process=True)
    m.remove_unreferenced_vertices()
    # cortical and trabecular regions are meshed with duplicated interface nodes, so the boundary also contains the
    # inner (cortex-trabecular) shell; keep only the outer shell = component with the largest enclosed volume
    parts = m.split(only_watertight=False)
    m = max(parts, key=lambda c: abs(c.volume) if c.is_watertight else c.convex_hull.volume)
    m.fix_normals()
    return m


groups = {}
for eb in geo.findall('Elements'):
    conn = np.array([[int(v) for v in e.text.split(',')] for e in eb.findall('elem')])
    groups.setdefault((eb.get('type'), mats[eb.get('mat')]), []).append(conn)

info = {}
parts = {}
for (etype, mname), cl in groups.items():
    conn = np.concatenate(cl)
    if etype == 'tet4':
        parts[mname] = to_mesh(boundary(conn, TET_F))
    elif etype == 'hex8':
        tag = 'nucleus' if mname == 'Nucleus' else ('facet_cartilage' if mname == 'FC' else 'annulus')
        parts.setdefault('_hex_' + tag, []).append(conn)

# rigid 'Forced' = superior (C3), 'Fixed' = inferior (C4); check by z
named = {}
for k, v in [('Forced', 'C3'), ('Fixed', 'C4')]:
    named[v] = parts[k]
assert named['C3'].centroid[2] > named['C4'].centroid[2], 'C3 should be above C4'
disc_conn = np.concatenate(parts['_hex_annulus'] + parts['_hex_nucleus'])
named['C3C4_disc'] = to_mesh(boundary(disc_conn, HEX_F))
named['C3C4_nucleus'] = to_mesh(boundary(np.concatenate(parts['_hex_nucleus']), HEX_F))

for k, m in named.items():
    m.export(f'{out}/{k}.stl')
    e = m.edges_unique_length
    info[k] = dict(n_vert=len(m.vertices), n_face=len(m.faces), watertight=bool(m.is_watertight),
                   extents_mm=np.round(m.extents, 2).tolist(), bounds_mm=np.round(m.bounds, 2).tolist(),
                   edge_mean_mm=round(float(e.mean()), 3), edge_max_mm=round(float(e.max()), 3))
both = trimesh.util.concatenate([named['C3'], named['C4']])
both.export(f'{out}/C3C4_bones.stl')
info['source'] = 'FEBio cervical spine model, 26 y.o. female, C34.feb (Herron MR et al., J Biomech 2020; simtk.org/projects/febiocervical)'
info['materials_in_feb'] = mats
json.dump(info, open(f'{out}/extract_info.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in info.items() if k != 'materials_in_feb'}, indent=1))
