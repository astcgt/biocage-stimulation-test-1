"""Plot a cage mesh (npz from h12): top view of the footprint and a mid-sagittal (Y=0) and coronal (X=centre) section,
coloured by hard-material fraction (mix) or hard/soft line (interleave); biodisc in light blue."""
import sys, json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap
files = sys.argv[1:-1]; out = sys.argv[-1]
fig, axs = plt.subplots(len(files), 3, figsize=(16, 4.2 * len(files)), squeeze=False)
cmap = plt.get_cmap('viridis')
for row, f in zip(axs, files):
    z = np.load(f); Q, H, reg, phi, hard = z['Q'], z['hexes'], z['region'], z['phi'], z['hard']; info = json.loads(str(z['info']))
    val = np.where(reg == 1, np.nan, hard.astype(float) if info['fabrication'] == 'interleave' else phi)
    C = Q[H].mean(1)
    def draw(ax, sel, i0, i1, title):
        polys = [Q[h][[0, 1, 2, 3] if i1 == 1 else ([0, 1, 5, 4] if i0 == 0 else [1, 2, 6, 5])][:, [i0, i1]] for h in H[sel]]
        v = val[sel]; col = [(0.75, 0.87, 1.0, 1) if np.isnan(x) else cmap(x) for x in v]
        ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors='none'))
        ax.autoscale(); ax.set_aspect('equal'); ax.set_title(title, fontsize=10)
    k_mid = int(np.median(z['layer']))
    draw(row[0], z['layer'] == k_mid, 0, 1, f"{info['design']} {info['gradient']} {info['fabrication']}: top view, mid layer")
    row[0].set_xlabel('X anterior (mm)'); row[0].set_ylabel('Y left (mm)')
    y0 = np.round(C[:, 1] / 0.2) * 0.2; ysel = np.abs(C[:, 1] - 0.1) < 0.101
    draw(row[1], ysel, 0, 2, 'mid-sagittal section (Y ~ 0)'); row[1].set_xlabel('X anterior'); row[1].set_ylabel('Z (mm)')
    xc = np.median(C[:, 0]); xsel = np.abs(C[:, 0] - (np.round(xc / 0.2) * 0.2 + 0.1)) < 0.101
    polys = [Q[h][[1, 2, 6, 5]][:, [1, 2]] for h in H[xsel]]
    v = val[xsel]; col = [(0.75, 0.87, 1.0, 1) if np.isnan(x) else cmap(x) for x in v]
    row[2].add_collection(PolyCollection(polys, facecolors=col, edgecolors='none')); row[2].autoscale(); row[2].set_aspect('equal')
    row[2].set_title('coronal section (X ~ centre)', fontsize=10); row[2].set_xlabel('Y left'); row[2].set_ylabel('Z (mm)')
sm = plt.cm.ScalarMappable(cmap=cmap); sm.set_array([0, 1])
fig.colorbar(sm, ax=axs, shrink=0.6, label='hard (PLCL 85:15) fraction; light blue = biodisc')
fig.savefig(out, dpi=130, bbox_inches='tight')
