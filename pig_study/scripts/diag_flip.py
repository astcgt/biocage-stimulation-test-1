import sys, numpy as np, torch
sys.path.insert(0, 'scripts')
from params import MAT, CONTACT
from fem_core import VoxelContactModel
M = np.load('design/model_A_smooth.npz'); L = M['L']
m = VoxelContactModel(L, float(M['h']), (float(M['x0']), float(M['y0']), float(M['z0'])), M['ref'], MAT, CONTACT)
pn = m.pn.cpu().numpy(); nx, ny, nz = L.shape
# material of cage-body voxels around each pair node
adj_plcl = np.zeros(len(pn), bool); adj_bio = np.zeros(len(pn), bool)
for a in (0, 1):
    for b in (0, 1):
        for c in (0, 1):
            i = np.clip(pn[:, 0] - a, 0, nx - 1); j = np.clip(pn[:, 1] - b, 0, ny - 1); k = np.clip(pn[:, 2] - c, 0, nz - 1)
            adj_plcl |= L[i, j, k] == 5; adj_bio |= L[i, j, k] == 6
bio_only = adj_bio & ~adj_plcl
nzc = np.abs(m.pnrm[:, 2].cpu().numpy())
print('pairs', len(pn), 'biodisc-only', bio_only.sum(), 'PLCL', adj_plcl.sum(), '|n_z|<0.7', (nzc < 0.7).sum())
hist = []
m.free_mask[-6:] = torch.tensor([1, 1, 0, 1, 1, 1.], dtype=torch.float64, device='cuda')
import types
st_prev = None; flips = np.zeros(len(pn), int)
orig = m.update_contact
def wrapped(x):
    global st_prev
    r = orig(x); st = r[0].cpu().numpy()
    if st_prev is not None: flips[:] += st != st_prev
    st_prev = st; return r
m.update_contact = wrapped
m.solve_increment({2: -0.01}, np.zeros(6), max_outer=8)
st = m.status.cpu().numpy()
for nm, msk in [('biodisc-only', bio_only), ('PLCL', adj_plcl), ('side (|nz|<0.7)', nzc < 0.7), ('flat (|nz|>=0.7)', nzc >= 0.7)]:
    print(f'{nm:18s} n={msk.sum():6d} flips/pair={flips[msk].mean():.2f}  open={np.mean(st[msk]==0):.2f} slip={np.mean(st[msk]==2):.2f}')
fl = flips > 3
print('frequent flippers', fl.sum(), 'of which biodisc-only', (fl & bio_only).sum(), 'side', (fl & (nzc < 0.7)).sum())
