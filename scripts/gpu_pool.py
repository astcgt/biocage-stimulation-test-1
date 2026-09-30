"""Independent-job GPU pool: one worker process per logical GPU.

Each FEM case is a single tightly coupled solve on ONE GPU; parallelism comes only from running independent cases
(designs / load levels / load directions) concurrently. No domain decomposition.

Device mapping: the parent is launched with e.g. CUDA_VISIBLE_DEVICES=3,4,7. Worker i uses logical device cuda:i
(torch.cuda.set_device(i) before any CUDA work) -> physical GPU = CUDA_VISIBLE_DEVICES[i]. No physical indices are used
inside workers. Right before launch, nvidia-smi + ps are queried and a logical device is used only if its physical GPU
has no compute process owned by another user.
"""
import os, subprocess, time, traceback, getpass, multiprocessing as mp


def visible_physical():
    v = os.environ.get('CUDA_VISIBLE_DEVICES')
    if not v: raise RuntimeError('set CUDA_VISIBLE_DEVICES (e.g. 3,4,7) to the GPUs you are permitted to use')
    return [int(x) for x in v.split(',') if x.strip()]


def _owner(pid):
    r = subprocess.run(['ps', '-o', 'user=', '-p', str(pid)], capture_output=True, text=True)
    return r.stdout.strip() or '?'


def free_logical(me=None):
    """Logical devices whose physical GPU is free or used only by processes of the current user."""
    me = me or getpass.getuser()
    q = lambda args: subprocess.run(['nvidia-smi'] + args, capture_output=True, text=True, check=True).stdout.strip().splitlines()
    uuid = {l.split(',')[1].strip(): int(l.split(',')[0]) for l in q(['--query-gpu=index,uuid', '--format=csv,noheader'])}
    foreign = set()
    for l in q(['--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader']):
        if not l.strip(): continue
        g, pid = l.split(',')[0].strip(), int(l.split(',')[1])
        if _owner(pid) != me: foreign.add(uuid[g])
    phys = visible_physical()
    return [(i, p) for i, p in enumerate(phys) if p not in foreign]


def _worker(logical, jobs, results, fn_module, fn_name):
    import importlib, sys, torch
    torch.cuda.set_device(logical)                       # before any CUDA allocation
    dev = f'cuda:{logical}'
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    fn = getattr(importlib.import_module(fn_module), fn_name)
    while True:
        job = jobs.get()
        if job is None: break
        t0 = time.time()
        try:
            torch.cuda.reset_peak_memory_stats(dev)
            out = fn(job, dev)
            results.put(dict(job=job, logical=logical, pid=os.getpid(), ok=True, out=out, wall=time.time() - t0,
                             peak_gb=torch.cuda.max_memory_allocated(dev) / 1e9))
        except Exception:
            results.put(dict(job=job, logical=logical, pid=os.getpid(), ok=False, out=traceback.format_exc(), wall=time.time() - t0))


def run_jobs(job_list, fn_module, fn_name, n_workers=None, log=print):
    avail = free_logical()
    if n_workers is not None: avail = avail[:n_workers]
    if not avail: raise RuntimeError('no free GPU among CUDA_VISIBLE_DEVICES')
    phys = dict(avail)
    log(f"[gpu_pool] {len(job_list)} jobs -> workers " + ', '.join(f'cuda:{l} (physical GPU {p})' for l, p in avail))
    ctx = mp.get_context('spawn')
    jobs, results = ctx.Queue(), ctx.Queue()
    for j in job_list: jobs.put(j)
    for _ in avail: jobs.put(None)
    procs = [ctx.Process(target=_worker, args=(l, jobs, results, fn_module, fn_name)) for l, _ in avail]
    for p in procs: p.start()
    out = []
    for _ in job_list:
        r = results.get(); r['physical'] = phys[r['logical']]; out.append(r)
        log(f"[gpu_pool] pid {r['pid']} cuda:{r['logical']}(GPU{r['physical']}) {'done' if r['ok'] else 'FAILED'} {r['job']} {r['wall']:.1f}s")
        if not r['ok']: log(r['out'])
    for p in procs: p.join()
    return out, avail
