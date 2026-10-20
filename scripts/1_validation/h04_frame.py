"""Disc mid-plane loading frame for the C3-C4 segment.
Z = normal to the bisector of the C3 inferior and C4 superior endplates (superior), X = anterior in that plane,
Y = left (ISO 18192-1), origin = ICR from h03 (Anderst 2013). Endplate directions from the mid-sagittal body corners.
usage: python h04_frame.py <C3.stl> <C4.stl> <icr.json> <out.json>
"""
import sys, json, numpy as np, trimesh

def corners(mesh):
    sec = mesh.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    allp = np.vstack(sec.discrete)
    def area(L): x, z = L[:, 0], L[:, 2]; return 0.5 * abs(np.dot(x, np.roll(z, 1)) - np.dot(z, np.roll(x, 1)))
    body = max([L for L in sec.discrete if L[:, 0].mean() > np.percentile(allp[:, 0], 60)], key=area)[:, [0, 2]]
    ap = np.array([1.0, 0.0])
    for _ in range(3):
        si = np.array([-ap[1], ap[0]]); u, v = body @ ap, body @ si
        sa, sp, ia, ip = body[np.argmax(u + v)], body[np.argmax(-u + v)], body[np.argmax(u - v)], body[np.argmax(-u - v)]
        ap = (sa - sp) + (ia - ip); ap /= np.linalg.norm(ap)
    return sa, sp, ia, ip

c3 = trimesh.load(sys.argv[1]); c4 = trimesh.load(sys.argv[2]); icr = json.load(open(sys.argv[3]))['ICR_anderst_xyz']
_, _, c3ia, c3ip = corners(c3)                     # C3 inferior endplate
c4sa, c4sp, _, _ = corners(c4)                     # C4 superior endplate
d3 = (c3ia - c3ip) / np.linalg.norm(c3ia - c3ip); d4 = (c4sa - c4sp) / np.linalg.norm(c4sa - c4sp)
xb = d3 + d4; xb /= np.linalg.norm(xb)             # bisector direction in the sagittal plane (anterior)
X = np.array([xb[0], 0.0, xb[1]]); Y = np.array([0.0, 1.0, 0.0])
Z = np.cross(X, Y); Z *= np.sign(Z[2])
Y = np.cross(Z, X)                                  # right-handed X (ant), Y (left), Z (sup)
ang = lambda d: np.degrees(np.arctan2(d[1], d[0]))
out = dict(origin_ICR=icr, X_anterior=X.round(5).tolist(), Y_left=Y.round(5).tolist(), Z_superior=Z.round(5).tolist(),
           C3_inferior_endplate_tilt_deg=round(float(ang(d3)), 2), C4_superior_endplate_tilt_deg=round(float(ang(d4)), 2),
           endplate_wedge_deg=round(float(ang(d4) - ang(d3)), 2), midplane_tilt_deg=round(float(ang(xb)), 2),
           note='tilts are in the CT (C34.feb) x-z plane; positive = anterior end higher; wedge = C4 sup minus C3 inf')
json.dump(out, open(sys.argv[4], 'w'), indent=1); print(json.dumps(out, indent=1))
