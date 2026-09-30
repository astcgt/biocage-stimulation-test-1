"""Small independent test cases for the GPU pool: one linear (all-stick) compression solve per job."""
import sys, os, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def linear_case(job, dev):
    import torch
    from params import MAT, CONTACT
    from fem_core import VoxelContactModel
    design, uz = job
    M = np.load(f'design/model_{design}.npz')
    m = VoxelContactModel(M['L'], float(M['h']), (float(M['x0']), float(M['y0']), float(M['z0'])), M['ref'], MAT, CONTACT,
                          dev=dev, log=lambda *a: None)
    m.status[:] = 1
    m.free_mask[-6:] = torch.tensor([1, 1, 0, 1, 1, 1.], dtype=torch.float64, device=dev)
    xp = torch.zeros(m.N, dtype=torch.float64, device=dev); xp[-4] = -uz
    b = (m.rhs_contact() - m.apply_full_presc(xp)) * m.free_mask
    dx, it, res = m.pcg(b, torch.zeros_like(b), tol=1e-8, maxit=8000)
    m.x = dx * m.free_mask + xp
    vm = m.cage_stress()[0]
    return dict(Fz=float(m.reaction()[2]), max_vm=float(vm[m.is_plcl].max()), pcg_it=it, device=str(torch.cuda.current_device()))


if __name__ == '__main__':
    from gpu_pool import run_jobs
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    jobs = [(d, u) for d in ('A_smooth', 'B_tread') for u in (0.01, 0.02, 0.03)]
    t0 = time.time()
    res, used = run_jobs(jobs, 'bench_jobs', 'linear_case', n_workers=n)
    wall = time.time() - t0
    out = dict(workers=[dict(logical=l, physical=p) for l, p in used], wall_s=wall,
               cases=[dict(job=r['job'], pid=r['pid'], physical=r['physical'], wall=r['wall'], peak_gb=r.get('peak_gb'), **(r['out'] if r['ok'] else {})) for r in res])
    tag = f'{len(used)}gpu'
    json.dump(out, open(f'logs/bench_{tag}.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))
