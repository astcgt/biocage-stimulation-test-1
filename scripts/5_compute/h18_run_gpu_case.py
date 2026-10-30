"""Run one FEBio case on one GPU (cuDSS linear solver) + CORES idle CPU cores, in a copy of the case directory.

The copy (<case>_gpu<g>) lets a GPU run race a CPU run of the same case without sharing output files.
Cores are chosen like h06 (idle, not pinned to my other FEBio runs, no reserve); launches are serialised
with the same lock file. Writes started_at and, when done, resources.json in the copy.
usage: python h18_run_gpu_case.py <gpu_index> <case_dir> [cores=16]
"""
import sys, os, time, json, glob, shutil, subprocess, fcntl
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
from h06_run_cpu_batch import cpu_busy, claimed_cores, P, FEBIO, RESERVE, febio_args, record_launch

gpu, src = int(sys.argv[1]), sys.argv[2].rstrip('/'); ncores = int(sys.argv[3]) if len(sys.argv) > 3 else 16
dst = f'{src}_gpu{gpu}'
os.makedirs(dst, exist_ok=True)
for f in glob.glob(os.path.join(src, '*')):                  # inputs only: feb, schedules, element tables
    if f.endswith(('.feb', '.json', '.npz')) and os.path.isfile(f): shutil.copy2(f, dst)
for w in glob.glob(os.path.join(src, 'w_*')):                # h30 split case: the window restart inputs
    os.makedirs(os.path.join(dst, os.path.basename(w)), exist_ok=True)
    for f in glob.glob(os.path.join(w, '*')):
        if f.endswith(('.feb', '.json', '.npz')): shutil.copy2(f, os.path.join(dst, os.path.basename(w)))
lock = open(os.path.join(P, 'human_study', '.cpu_launch.lock'), 'w'); fcntl.flock(lock, fcntl.LOCK_EX)
busy = cpu_busy(); idle = sorted(busy, key=busy.get)
usable = [c for c in idle[:len(idle) - RESERVE] if busy[c] < 0.10 and c not in claimed_cores()]
if len(usable) < ncores:                                    # exit 3 = not launched; h19 puts the job back in the queue
    print(f'only {len(usable)} idle cores'); sys.exit(3)
cores = sorted(usable[:ncores])
libs = ':'.join([os.path.join(P, 'third_party/mkl/lib'), os.path.join(P, 'third_party/cuda/lib')])
env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS=str(ncores), MKL_NUM_THREADS=str(ncores),
           LD_LIBRARY_PATH=libs, KMP_STACKSIZE='1G', OMP_STACKSIZE='1G')
feb = os.path.basename(glob.glob(os.path.join(dst, '*.feb'))[0])
fargs, resumed = febio_args(dst, feb)     # resume from the checkpoint (<case>.dmp) if a previous run was interrupted
if not resumed: record_launch(dst, feb)
cmd = ['prlimit', '--stack=unlimited', 'taskset', '-c', ','.join(map(str, cores)), FEBIO] + fargs + \
      ['-cnf', os.path.join(P, 'febio_cudss/febio_cudss.xml')]
if os.path.exists(os.path.join(dst, 'split.json')):          # h30 split case: insertion run + independent window restarts
    cmd = cmd[:5] + [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'h31_split_run.py'), os.path.abspath(dst),
                     '-cnf', os.path.join(P, 'febio_cudss/febio_cudss.xml')]
t0 = time.time()
if not os.path.exists(os.path.join(dst, 'started_at')) or not resumed: open(os.path.join(dst, 'started_at'), 'w').write(str(t0))
p = subprocess.Popen(cmd, cwd=dst, env=env, stdout=subprocess.DEVNULL, stderr=open(os.path.join(dst, 'stderr.log'), 'w'))
print(f'{"resumed" if resumed else "started"} {dst} on GPU {gpu}, cores {cores[0]}..{cores[-1]}', flush=True)
time.sleep(2); fcntl.flock(lock, fcntl.LOCK_UN)
p.wait(); wall = time.time() - t0
txt = open(glob.glob(os.path.join(dst, '*.log'))[0]).read()
res = dict(exit=p.returncode, normal='N O R M A L' in txt, wall_s=round(wall, 1), gpu=gpu, cores=ncores,
           core_h=round(ncores * wall / 3600, 3), gpu_h=round(wall / 3600, 3))
json.dump(res, open(os.path.join(dst, 'resources.json'), 'w'), indent=1); print(res, flush=True)
