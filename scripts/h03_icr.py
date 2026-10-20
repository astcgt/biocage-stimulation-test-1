"""Locate the C3-C4 instantaneous centre of rotation (ICR) on the C4 model.

Anderst et al. 2013 (Spine 38:E594, Table 2, asymptomatic n=20): C3-C4 mean ICR = +1.5 mm superior, -1.8 mm anterior
(i.e. 1.8 mm posterior) of the C4 anatomic origin, origin = mean of the most anterior and most posterior points of the
C4 superior and inferior endplates (mid-sagittal). Cross-check: Amevo et al. 1991 (Clin Biomech 6:111, Table 2):
normalised X = 0.32 of body width from the posterior border, Y = 0.52 of body height from the inferior border.
usage: python h03_icr.py <C4.stl> <C3.stl> <out.json> <out.png>
"""
import sys, json, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

c4 = trimesh.load(sys.argv[1]); c3 = trimesh.load(sys.argv[2])
sec = c4.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])          # mid-sagittal (model is L/R symmetric, y = 0)
# outer contour of the vertebral body only: the bone STL also carries the inner trabecular surface (cortex offset 1 mm),
# so keep the loop with the largest enclosed area among loops in the anterior (body) region
def area(L): x, z = L[:, 0], L[:, 2]; return 0.5 * abs(np.dot(x, np.roll(z, 1)) - np.dot(z, np.roll(x, 1)))
loops = [L for L in sec.discrete if L[:, 0].mean() > np.percentile(np.vstack(sec.discrete)[:, 0], 60)]
body = max(loops, key=area)[:, [0, 2]]
# corners of the (quadrilateral-like) body outline: extreme points along the diagonals of the endplate frame;
# start from the horizontal frame and refine the frame from the corners twice
ap = np.array([1.0, 0.0])
for _ in range(3):
    si = np.array([-ap[1], ap[0]])
    u, v = body @ ap, body @ si
    sa, sp, ia, ip = (body[np.argmax(u + v)], body[np.argmax(-u + v)], body[np.argmax(u - v)], body[np.argmax(-u - v)])
    ap = (sa - sp) + (ia - ip); ap /= np.linalg.norm(ap)
si = np.array([-ap[1], ap[0]]); si *= np.sign(si[1])
origin = (sa + sp + ia + ip) / 4
icr_anderst = origin + 1.5 * si - 1.8 * ap
# Amevo trapezoid: width = AP depth, height = SI height of body (mid-body), origin at postero-inferior corner
width = np.dot((sa + ia) / 2 - (sp + ip) / 2, ap); height = np.dot((sa + sp) / 2 - (ia + ip) / 2, si)
icr_amevo = ip + 0.32 * width * ap + 0.52 * height * si
d = icr_amevo - icr_anderst
out = dict(origin_xz=origin.tolist(), ap_unit=ap.tolist(), si_unit=si.tolist(),
           C4_body_depth_mm=round(float(width), 2), C4_body_height_mm=round(float(height), 2),
           ICR_anderst_xyz=[round(float(icr_anderst[0]), 3), 0.0, round(float(icr_anderst[1]), 3)],
           ICR_amevo_xyz=[round(float(icr_amevo[0]), 3), 0.0, round(float(icr_amevo[1]), 3)],
           amevo_minus_anderst_AP_SI_mm=[round(float(np.dot(d, ap)), 2), round(float(np.dot(d, si)), 2)],
           endplate_points=dict(sup_ant=sa.tolist(), sup_post=sp.tolist(), inf_ant=ia.tolist(), inf_post=ip.tolist()))
json.dump(out, open(sys.argv[3], 'w'), indent=1); print(json.dumps(out, indent=1))
fig, ax = plt.subplots(figsize=(7, 6))
for m, c in [(c4, '#8a7650'), (c3, '#b9a77f')]:
    s = m.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    for e in s.discrete: ax.plot(e[:, 0], e[:, 2], color=c, lw=1)
for p in (sa, sp, ia, ip): ax.plot(*p, 'k+', ms=8)
ax.plot(*origin, 'ks', ms=5, label='C4 anatomic origin (Anderst)')
ax.plot(*icr_anderst, 'o', color='#d62728', ms=8, label='ICR, Anderst 2013 (used)')
ax.plot(*icr_amevo, 'o', color='#1f77b4', ms=7, mfc='none', label='ICR, Amevo 1991 (check)')
ax.set_aspect('equal'); ax.set_xlabel('x, anterior (mm)'); ax.set_ylabel('z, superior (mm)')
ax.set_title('C3-C4 instantaneous centre of rotation, mid-sagittal'); ax.legend(loc='upper left', fontsize=8)
ax.set_xlim(origin[0] - 25, origin[0] + 15); ax.set_ylim(origin[1] - 15, origin[1] + 25)
fig.tight_layout(); fig.savefig(sys.argv[4], dpi=150)
