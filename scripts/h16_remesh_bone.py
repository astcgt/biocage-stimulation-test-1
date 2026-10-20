"""Local refinement of the C3 / C4 bone mesh at the C3-C4 endplates (DECISIONS: endplate 0.5 mm near the cage).

For one vertebra of the FSU (all its cortical + trabecular tets, potted ones included):
 1. surfaces: outer cortical boundary S_out and cortical/trabecular interface S_int (shared-node triangles)
 2. patch = S_out triangles whose nodes are all disc-attachment nodes (= the bony endplate); patch_int = S_int triangles
    whose centroid projects inside the disc outline (frame X-Y) and lies within 4 mm of the endplate
 3. red refinement of the patch triangles until every patch edge <= H_TARGET, with green closure in the neighbouring
    ring (all triangles stay conforming; original vertices keep their coordinates)
 4. gmsh 3D Delaunay mesh of the cortical shell (between S_out and S_int) and the trabecular core (inside S_int) on the
    fixed surface meshes, size field 0.5 mm within 3 mm of the endplate growing to 1.5 mm
Writes an npz: nodes, cortical tets, trabecular tets, the refined endplate triangles, and a map from original node ids to
new node indices for every original surface node (unchanged coordinates).
usage: python h16_remesh_bone.py <fsu.feb> <frame.json> <C3|C4> <out.npz> [h_target=0.5]
"""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cage_geom import Endplates
from shapely import vectorized

fsu, frame, V, out = sys.argv[1:5]; H_T = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
ep = Endplates(fsu, frame); X = ep.X
blk = ep.blocks
cort = np.vstack([blk[f'{V}_cortical'][2], blk[f'{V}_cortical_pot'][2]])
trab = np.vstack([blk[f'{V}_trabecular'][2], blk[f'{V}_trabecular_pot'][2]])
TF = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2))                     # outward faces of a positively oriented tet


def faces(T):
    F = np.concatenate([T[:, f] for f in TF])
    k = np.sort(F, 1); _, inv, cnt = np.unique(k, axis=0, return_inverse=True, return_counts=True)
    return F, k, inv.ravel(), cnt


Fc, kc, ic, cc = faces(cort); Ft, kt, it, ct = faces(trab)
S_out_c = Fc[cc[ic] == 1]                                            # boundary of cortical tets: outer + interface
set_t = {tuple(r) for r in np.sort(Ft[ct[it] == 1], 1)}
is_int = np.array([tuple(r) in set_t for r in np.sort(S_out_c, 1)])
S_int = S_out_c[is_int]; S_out = S_out_c[~is_int]
attach = set(ep.top_ids if V == 'C3' else ep.bot_ids)
patch = np.array([set(f) <= attach for f in S_out])
P_all = {i: X[i] for i in np.unique(np.r_[cort.ravel(), trab.ravel()])}
Ci = ep.F.to(np.array([np.mean([P_all[j] for j in f], 0) for f in S_int]))
zref = ep.z_top(Ci[:, 0], Ci[:, 1]) if V == 'C3' else ep.z_bot(Ci[:, 0], Ci[:, 1])
depth = (Ci[:, 2] - zref) if V == 'C3' else (zref - Ci[:, 2])
patch_int = vectorized.contains(ep.outline, Ci[:, 0], Ci[:, 1]) & (depth > -0.5) & (depth < 4.0)


def refine(tris, mark, coords, next_id, h):
    """Red refinement of marked triangles until all their edges <= h; green/blue closure so the mesh stays conforming.
    coords: dict id -> xyz (extended in place); returns new triangle list and next free id."""
    tris = [tuple(t) for t in tris]; mark = list(mark)
    for _ in range(6):
        long = lambda a, b: np.linalg.norm(coords[a] - coords[b]) > h
        split = set()
        for t, m in zip(tris, mark):
            if m and any(long(t[i], t[(i + 1) % 3]) for i in range(3)):
                for i in range(3): split.add(tuple(sorted((t[i], t[(i + 1) % 3]))))
        if not split: break
        # closure: a triangle with 2 split edges gets the third split too (avoids bad slivers) -> red
        changed = True
        while changed:
            changed = False
            for t in tris:
                e = [tuple(sorted((t[i], t[(i + 1) % 3]))) for i in range(3)]
                if sum(x in split for x in e) == 2:
                    split |= set(e); changed = True
        mid = {}
        for e in split:
            mid[e] = next_id; coords[next_id] = 0.5 * (coords[e[0]] + coords[e[1]]); next_id += 1
        nt, nm = [], []
        for t, m in zip(tris, mark):
            a, b, c = t; ab, bc, ca = (mid.get(tuple(sorted(x))) for x in ((a, b), (b, c), (c, a)))
            n = sum(x is not None for x in (ab, bc, ca))
            if n == 3:
                nt += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]; nm += [m] * 4
            elif n == 1:                                     # green: bisect towards the opposite vertex
                if ab is not None: nt += [(a, ab, c), (ab, b, c)]
                elif bc is not None: nt += [(a, b, bc), (a, bc, c)]
                else: nt += [(a, b, ca), (ca, b, c)]
                nm += [False, False]
            else:
                nt.append(t); nm.append(m)
        tris, mark = nt, nm
    return np.array(tris), next_id


coords = {i: np.array(p, float) for i, p in P_all.items()}
nid = max(X) + 1
# refine the outer surface and the interface; both share no edges with each other (interface is internal)
S_out_r, nid = refine(S_out, patch, coords, nid, H_T)
S_int_r, nid = refine(S_int, patch_int, coords, nid, H_T)
print(f'{V}: outer {len(S_out)} -> {len(S_out_r)} triangles, interface {len(S_int)} -> {len(S_int_r)}', flush=True)

# --- gmsh volume meshing on the fixed surface meshes
import gmsh
gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0); gmsh.model.add(V)
ids_used = np.unique(np.r_[S_out_r.ravel(), S_int_r.ravel()])
tagof = {int(i): k + 1 for k, i in enumerate(ids_used)}
for s, (tag, T) in enumerate(((1, S_out_r), (2, S_int_r))):
    gmsh.model.addDiscreteEntity(2, tag)
nodes_xyz = np.array([coords[int(i)] for i in ids_used]).ravel()
gmsh.model.mesh.addNodes(2, 1, [tagof[int(i)] for i in ids_used], nodes_xyz)
gmsh.model.mesh.addElementsByType(1, 2, [], [tagof[int(i)] for i in S_out_r.ravel()])
gmsh.model.mesh.addElementsByType(2, 2, [], [tagof[int(i)] for i in S_int_r.ravel()])
gmsh.model.geo.addSurfaceLoop([1], 11); gmsh.model.geo.addSurfaceLoop([2], 12)
gmsh.model.geo.addVolume([11, 12], 21)          # cortical shell
gmsh.model.geo.addVolume([12], 22)              # trabecular core
gmsh.model.geo.synchronize()
# size field: distance to the refined endplate nodes
epn = [tagof[int(i)] for i in np.unique(S_out_r[np.array([all(np.linalg.norm(coords[j] - coords[j]) == 0 for j in t) for t in S_out_r])].ravel())]
ep_nodes = [tagof[int(i)] for i in np.unique(S_out_r.ravel()) if int(i) >= max(X) + 1 or int(i) in attach]
f = gmsh.model.mesh.field
f.add('Distance', 1); f.setNumbers(1, 'PointsList', [])
pts = []
for k, n in enumerate(ep_nodes[::1]):
    p = gmsh.model.geo.addPoint(*coords[ids_used[n - 1]], meshSize=H_T); pts.append(p)
gmsh.model.geo.synchronize()
f.setNumbers(1, 'PointsList', pts)
f.add('Threshold', 2); f.setNumber(2, 'InField', 1); f.setNumber(2, 'SizeMin', H_T); f.setNumber(2, 'SizeMax', 1.5)
f.setNumber(2, 'DistMin', 3.0); f.setNumber(2, 'DistMax', 8.0)
f.setAsBackgroundMesh(2)
gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
gmsh.option.setNumber('Mesh.Algorithm3D', 1); gmsh.option.setNumber('Mesh.Optimize', 1); gmsh.option.setNumber('Mesh.OptimizeNetgen', 1)
gmsh.model.mesh.generate(3)
nt, nc, _ = gmsh.model.mesh.getNodes()
P = nc.reshape(-1, 3); tag2row = {int(t): k for k, t in enumerate(nt)}
tets = {}
for vol in (21, 22):
    et, etags, en = gmsh.model.mesh.getElements(3, vol)
    T = np.array([tag2row[int(x)] for x in en[0]]).reshape(-1, 4); tets[vol] = T
q = gmsh.model.mesh.getElementQualities([int(x) for v in (21, 22) for x in gmsh.model.mesh.getElements(3, v)[1][0]], 'minSICN')
gmsh.finalize()
# drop nodes not used by any tet: the size-field points are meshed as isolated 0-D nodes that coincide with surface nodes
# and would otherwise capture the coordinate matching below (bug found 2026-10-20)
keep = np.unique(np.r_[tets[21].ravel(), tets[22].ravel()]); new = -np.ones(len(P), int); new[keep] = np.arange(len(keep))
P = P[keep]; tets = {v: new[T] for v, T in tets.items()}
# map surface nodes to rows of P by coordinates (gmsh renumbers nodes; surface coordinates are unchanged)
from scipy.spatial import cKDTree
tree = cKDTree(P)
def row(i):
    dd, r = tree.query(coords[int(i)]); assert dd < 1e-6, (i, dd); return int(r)
orig_map = {int(i): row(i) for i in ids_used if int(i) <= max(X)}
ep_tris = np.array([[row(i) for i in t] for t in S_out_r if all((int(i) in attach) or int(i) > max(X) for i in t)])
np.savez_compressed(out, P=P, cort=tets[21], trab=tets[22], endplate_tris=ep_tris,
                    orig_ids=np.array(list(orig_map.keys())), orig_rows=np.array(list(orig_map.values())))
print(json.dumps(dict(vertebra=V, nodes=len(P), cortical=len(tets[21]), trabecular=len(tets[22]),
                      min_quality=float(np.min(q)), q_lt_0p1=int((np.array(q) < 0.1).sum()), endplate_tris=len(ep_tris))))
