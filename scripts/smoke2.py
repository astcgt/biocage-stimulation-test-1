import sys, time, numpy as np, torch
sys.path.insert(0, 'scripts')
from params import MAT, CONTACT
from fem_core import VoxelContactModel
M = np.load('design/model_A_smooth.npz')
t = time.time()
m = VoxelContactModel(M['L'], float(M['h']), (float(M['x0']), float(M['y0']), float(M['z0'])), M['ref'], MAT, CONTACT)
print('build', time.time() - t, flush=True)
m.status[:] = 1
x = torch.randn(m.N, dtype=torch.float64, device='cuda')
torch.cuda.synchronize(); t = time.time()
for _ in range(20): y = m.apply(x)
torch.cuda.synchronize(); print('matvec ms', (time.time() - t) / 20 * 1e3, flush=True)
m.free_mask[-6:] = torch.tensor([1, 1, 0, 1, 1, 1.], dtype=torch.float64, device='cuda')
xp = torch.zeros(m.N, dtype=torch.float64, device='cuda'); xp[-4] = -0.01
b = (m.rhs_contact() - m.apply_full_presc(xp)) * m.free_mask
Minv = m.free_mask / m.diag(); xx = torch.zeros_like(b); r = b.clone(); z = Minv * r; p = z.clone(); rz = (r * z).sum(); bn = torch.linalg.norm(b)
t = time.time()
for it in range(8000):
    Ap = m.apply(p); al = rz / (p * Ap).sum(); xx += al * p; r -= al * Ap
    if it % 250 == 0: print(it, float(torch.linalg.norm(r) / bn), 'q', (xx + xp)[-6:].cpu().numpy().round(6), f'{time.time() - t:.1f}s', flush=True)
    z = Minv * r; rzn = (r * z).sum(); p = z + rzn / rz * p; rz = rzn
