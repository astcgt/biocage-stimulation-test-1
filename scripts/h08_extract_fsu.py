"""Cut a deformable-bone C3-C4 functional spinal unit out of the Herron 2020 26yoF C0-C7 FEBio model.

Kept from C0C7.feb (same mesh and materials Herron validated): C3 and C4 cortical + trabecular tets, the C3-C4 disc
(annulus fibre-reinforced hexes + nucleus), the C3-C4 facet cartilages with their sliding contacts, and the C3-C4
ligament springs (ALL, PLL, FCC, LF, ISL). Boundary conditions mimic in-vitro potting: bone elements whose centroid
lies more than POT_MM below the disc (along the disc-normal axis Z of h04_frame) are a fixed rigid body (C4 pot); those
more than POT_MM above the disc a loaded rigid body (C3 pot). Endplates, subchondral bone and facets stay deformable. Output is an FEBio 2.5 file (same dialect as Herron's) plus a JSON description.

usage: python h08_extract_fsu.py <C0C7.feb> <out.feb> <frame_c3c4.json>
"""
import sys, json, copy, xml.etree.ElementTree as ET
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

POT_MM = 5.0          # potting depth measured from the disc along the disc-normal axis Z (h04 frame)
FRAME = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
src, dst = sys.argv[1], sys.argv[2]
tree = ET.parse(src); root = tree.getroot(); geo = root.find('Geometry')

X = {}
for nb in geo.findall('Nodes'):
    for n in nb.findall('node'):
        X[int(n.get('id'))] = np.array([float(v) for v in n.text.split(',')])
mats = {m.get('id'): m for m in root.find('Material').findall('material')}


def elems(eb):
    return np.array([[int(v) for v in e.text.split(',')] for e in eb.findall('elem')]), [int(e.get('id')) for e in eb.findall('elem')]


def components(E):
    u, inv = np.unique(E, return_inverse=True); inv = inv.reshape(E.shape)
    k = E.shape[1]
    A = coo_matrix((np.ones(inv.size), (np.repeat(inv[:, 0], k), inv.ravel())), shape=(len(u),) * 2)
    _, lab = connected_components(A, directed=False)
    elab = lab[inv[:, 0]]
    return elab


# ---- bones: cortical (mat 3) components ordered top->bottom are C1..C6 (C3 = 2, C4 = 3); trabecular (mat 4) pieces
# (8 pieces: some vertebrae have two) are assigned to the vertebra of their nearest cortical nodes
from scipy.spatial import cKDTree
bone_blocks = {'3': {}, '4': {}}
blk = {eb.get('mat'): eb for eb in geo.findall('Elements') if eb.get('type') == 'tet4' and eb.get('mat') in ('3', '4')}
E, ids = elems(blk['3']); lab = components(E)
zc = {l: np.mean([X[i][2] for i in np.unique(E[lab == l])]) for l in np.unique(lab)}
order = sorted(zc, key=lambda l: -zc[l]); assert len(order) == 6
vert_of = {l: f'C{k + 1}' for k, l in enumerate(order)}
for lvl in ('C3', 'C4'):
    sel = np.array([vert_of[l] == lvl for l in lab])
    bone_blocks['3'][lvl] = (E[sel], [ids[j] for j in np.where(sel)[0]])
cort_nodes = np.unique(E); node_vert = {}
for l in np.unique(lab):
    for i in np.unique(E[lab == l]): node_vert[i] = vert_of[l]
tree_c = cKDTree(np.array([X[i] for i in cort_nodes]))
E, ids = elems(blk['4']); lab = components(E)
assign = {}
for l in np.unique(lab):
    nn = np.unique(E[lab == l]); _, j = tree_c.query(np.array([X[i] for i in nn]))
    vs = [node_vert[cort_nodes[k]] for k in j]; assign[l] = max(set(vs), key=vs.count)
for lvl in ('C3', 'C4'):
    sel = np.array([assign[l] == lvl for l in lab])
    bone_blocks['4'][lvl] = (E[sel], [ids[j] for j in np.where(sel)[0]])
bone_nodes = {lvl: set(np.unique(np.vstack([bone_blocks[m][lvl][0] for m in ('3', '4')]))) for lvl in ('C3', 'C4')}

# ---- C3-C4 disc: hex components (annulus + nucleus share nodes) touching both C3 and C4 bone nodes
hexE, hexMat, hexId, hexName = [], [], [], []
for eb in geo.findall('Elements'):
    if eb.get('type') == 'hex8':
        E, ids = elems(eb); hexE.append(E); hexMat += [eb.get('mat')] * len(E); hexId += ids; hexName += [eb.get('name')] * len(E)
hexE = np.vstack(hexE); hexMat = np.array(hexMat); hexId = np.array(hexId)
lab = components(hexE)
keep_hex = np.zeros(len(hexE), bool)
for l in np.unique(lab):
    nodes = set(np.unique(hexE[lab == l]))
    if nodes & bone_nodes['C3'] and nodes & bone_nodes['C4'] and mats[hexMat[lab == l][0]].get('name') != 'FC':
        keep_hex |= lab == l
# facet cartilage (mat FC) components that touch C3 or C4 and sit between them
fc_ids = [k for k, m in mats.items() if m.get('name') == 'FC']
isfc = np.isin(hexMat, fc_ids)
for l in np.unique(lab[isfc]):
    nodes = set(np.unique(hexE[lab == l]))
    if nodes & (bone_nodes['C3'] | bone_nodes['C4']):
        # cartilage layers belonging to the C3-C4 facet joints (C3 inferior or C4 superior facets)
        z = np.mean([X[i][2] for i in nodes])
        zc3 = np.mean([X[i][2] for i in bone_nodes['C3']]); zc4 = np.mean([X[i][2] for i in bone_nodes['C4']])
        if zc4 - 3 < z < zc3 + 3:
            keep_hex |= (lab == l) & isfc

# ---- surfaces / contacts / discrete sets of the C3-C4 level
surf_keep = {s.get('name'): s for s in geo.findall('Surface') if s.get('name').startswith('C34_')}
pair_keep = [p for p in geo.findall('SurfacePair') if p.get('name', '').startswith('C34_')]
dset_keep = [d for d in geo.findall('DiscreteSet') if d.get('name', '').endswith(' 34')]

used = set(bone_nodes['C3']) | set(bone_nodes['C4']) | set(np.unique(hexE[keep_hex]))
for s in surf_keep.values():
    for f in s:
        used |= set(int(v) for v in f.text.split(','))
for d in dset_keep:
    for e in d:
        used |= set(int(v) for v in e.text.split(','))
# nucleus pressure surfaces: keep faces whose nodes are all in this disc
disc_nodes = set(np.unique(hexE[keep_hex]))

# ---- potting: rigid caps
def centroid(E): return np.array([np.mean([X[i] for i in e], 0) for e in E])
Zhat = np.array(FRAME['Z_superior']); O = np.array(FRAME['origin_ICR'])
zf = lambda P: (np.atleast_2d(P) - O) @ Zhat
disc_z = zf(np.array([X[i] for i in np.unique(hexE[keep_hex & ~isfc])]))
z_disc_top, z_disc_bot = disc_z.max(), disc_z.min()

# ---- build new file
out = copy.deepcopy(root)
og = out.find('Geometry')
for ch in list(og):
    og.remove(ch)
nodes_el = ET.SubElement(og, 'Nodes', name='FSU')
for i in sorted(used):
    ET.SubElement(nodes_el, 'node', id=str(i)).text = ','.join(f'{v:.6g}' for v in X[i])
eid = 0
def add_block(name, mat, etype, E):
    global eid
    eb = ET.SubElement(og, 'Elements', type=etype, mat=str(mat), name=name)
    for e in E:
        eid += 1; ET.SubElement(eb, 'elem', id=str(eid)).text = ','.join(map(str, e))
info = dict(pot_mm=POT_MM, blocks={})
# materials: keep originals, rigid 'Fixed' (1) = C4 pot, rigid 'Forced' (2) = C3 pot
for lvl, rigid in (('C3', '2'), ('C4', '1')):
    for m in ('3', '4'):
        E = bone_blocks[m][lvl][0]; c = centroid(E)
        pot = (zf(c) > z_disc_top + POT_MM) if lvl == 'C3' else (zf(c) < z_disc_bot - POT_MM)
        add_block(f'{lvl}_{"cortical" if m == "3" else "trabecular"}', m, 'tet4', E[~pot])
        add_block(f'{lvl}_{"cortical" if m == "3" else "trabecular"}_pot', rigid, 'tet4', E[pot])
        info['blocks'][f'{lvl}_{m}'] = dict(deformable=int((~pot).sum()), potted=int(pot.sum()))
for mid in np.unique(hexMat[keep_hex]):
    sel = keep_hex & (hexMat == mid)
    add_block(f'disc_or_facet_mat{mid}', mid, 'hex8', hexE[sel])
    info['blocks'][f'hex_mat{mid}'] = int(sel.sum())
for s in geo.findall('Surface'):
    if s.get('name') in surf_keep:
        og.append(copy.deepcopy(s))
    elif s.get('name', '').startswith('Nucleus'):
        ns = ET.SubElement(og, 'Surface', name=s.get('name'))
        for f in s:
            if set(int(v) for v in f.text.split(',')) <= disc_nodes:
                ns.append(copy.deepcopy(f))
for p in pair_keep: og.append(copy.deepcopy(p))
for d in dset_keep: og.append(copy.deepcopy(d))

# boundary: only the two rigid bodies (C4 pot fixed; C3 pot free, loads added by the case builder)
b = out.find('Boundary')
for ch in list(b): b.remove(ch)
rb = ET.SubElement(b, 'rigid_body', mat='1')
for dof in ('x', 'y', 'z', 'Rx', 'Ry', 'Rz'): ET.SubElement(rb, 'fixed', bc=dof)
ET.SubElement(b, 'rigid_body', mat='2')
# contacts / discrete: keep only C3-C4 ones
c = out.find('Contact')
for ch in list(c):
    if not ch.get('surface_pair', '').startswith('C34_'): c.remove(ch)
dsc = out.find('Discrete')
keep_names = {d.get('name') for d in dset_keep}
keep_dmat = set()
for ch in list(dsc):
    if ch.tag == 'discrete' and ch.get('discrete_set') not in keep_names: dsc.remove(ch)
    elif ch.tag == 'discrete': keep_dmat.add(ch.get('dmat'))
# renumber discrete materials referenced
dms = [ch for ch in dsc if ch.tag == 'discrete_material']
newid = {}
for ch in dms:
    if ch.get('id') not in keep_dmat: dsc.remove(ch)
for k, ch in enumerate([ch for ch in dsc if ch.tag == 'discrete_material']):
    newid[ch.get('id')] = str(k + 1); ch.set('id', str(k + 1))
for ch in dsc:
    if ch.tag == 'discrete': ch.set('dmat', newid[ch.get('dmat')])
# rigid centres of mass (required by FEBio 2.5 rigid bodies) at pot centroids
for mid, lvl in (('2', 'C3'), ('1', 'C4')):
    m = out.find(f"Material/material[@id='{mid}']")
    E = [e for eb in og.findall('Elements') if eb.get('mat') == mid for e in eb]
    pts = np.array([X[int(i)] for e in E for i in e.text.split(',')])
    com = m.find('center_of_mass'); com.text = ','.join(f'{v:.4f}' for v in pts.mean(0))
    info[f'{lvl}_pot_com'] = pts.mean(0).round(3).tolist()
# drop the C0/TM/TL related loads, keep nucleus pressure
out.find('Output').clear(); ET.SubElement(out.find('Output'), 'plotfile', type='febio')
for v in ('displacement', 'stress', 'contact force', 'contact pressure', 'rigid force', 'rigid torque'):
    ET.SubElement(out.find('Output/plotfile'), 'var', type=v)
# MeshData only holds shell thicknesses of TM/TL/C0 (not in the FSU)
md = out.find('MeshData')
if md is not None: out.remove(md)
# renumber nodes consecutively (FEBio 2.5 expects ids 1..N) in nodes, elements, surfaces and discrete sets
new = {old: k + 1 for k, old in enumerate(sorted(used))}
remap = lambda txt: ','.join(str(new[int(v)]) for v in txt.split(','))
for n in og.find('Nodes'): n.set('id', str(new[int(n.get('id'))]))
for eb in og.findall('Elements'):
    for e in eb: e.text = remap(e.text)
for s in og.findall('Surface'):
    for f in s: f.text = remap(f.text)
for d in og.findall('DiscreteSet'):
    for e in d: e.text = remap(e.text)
info['node_id_map'] = 'old C0C7 ids renumbered consecutively in sorted order'
ET.ElementTree(out).write(dst, encoding='ISO-8859-1', xml_declaration=True)
info.update(herron_ref_length_mm=float(max(np.ptp(np.array(list(X.values())), 0))), nodes=len(used), elements=eid, discrete_sets=sorted(keep_names), contacts=[p.get('name') for p in pair_keep])
json.dump(info, open(dst.replace('.feb', '.json'), 'w'), indent=1)
print(json.dumps(info, indent=1))
