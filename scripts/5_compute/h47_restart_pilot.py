"""Restart hold pilots (DECISIONS 2026-11-07): the extension hold window restarted from an EXISTING t 3.5 checkpoint of the
production friction model (pilot_holdA / pilot_holdE insertion runs, production binary), run with the patch-6/7 FEBio build
(third_party/FEBio/cbuild_fric) and the friction treatment switched for the window only by environment variables that the
patched binary reads (BIOCAGE_STICK_MEMORY, BIOCAGE_CAGE_LAUGON; params key 'restart_env'). The insertion state is therefore
byte-identical to the production-binary hold runs (same dump), so the hold drift isolates the friction treatment.

build: python h47_restart_pilot.py build <case_dir> <source_run_dir> [key=json ...]
         <case_dir>_params.json = <source run>'s params + the given keys; h14 rebuilds the deck (must be byte-identical to the
         source case.feb, else the checkpoint does not belong to it: h24 refuses); case.dmp hard-linked, case.xplt copied,
         launched_feb.sha256 copied; h24 preflight check must pass.
run:   python h47_restart_pilot.py run <case_dir> <gpu> <cores> [window=extension]
         runs w_<window>/restart.feb in place (like h31) on the given GPU (cuDSS plugin) with the restart_env variables;
         writes started_at, resources.json, done.
"""
import os, sys, json, glob, shutil, subprocess, time, fcntl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import cpu_busy, claimed_cores, P
import h24_preflight

FEBIO_FRIC = os.path.join(P, 'third_party/FEBio/cbuild_fric/bin/febio4')
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py')
CNF = os.path.join(P, 'febio_cudss/febio_cudss.xml')


def build(cd, src, extra):
    cd = os.path.normpath(cd); src = os.path.normpath(src)
    sp = src[:-len(src.split('_gpu')[-1]) - 4] + '_params.json' if '_gpu' in os.path.basename(src) else src + '_params.json'
    prm = json.load(open(sp))
    for kv in extra:
        k, v = kv.split('=', 1); prm[k] = json.loads(v)
    prm['restart_source'] = os.path.relpath(src, P)
    os.makedirs(os.path.dirname(cd), exist_ok=True)
    json.dump(prm, open(cd + '_params.json', 'w'), indent=1)
    if os.path.exists(cd): shutil.rmtree(cd)
    subprocess.run([sys.executable, H14, cd + '_params.json', cd], check=True, cwd=P, stdout=subprocess.DEVNULL)
    a, b = h24_preflight.sha(os.path.join(src, 'case.feb')), h24_preflight.sha(os.path.join(cd, 'case.feb'))
    if a != b: sys.exit(f'{cd}: rebuilt case.feb differs from the source run {src} (the checkpoint does not belong to this deck)')
    os.link(os.path.join(src, 'case.dmp'), os.path.join(cd, 'case.dmp'))   # hard link: run() passes NO -dump flag, so the source checkpoint is never rewritten; keep it that way
    shutil.copy2(os.path.join(src, 'case.xplt'), os.path.join(cd, 'case.xplt'))
    shutil.copy2(os.path.join(src, 'launched_feb.sha256'), os.path.join(cd, 'launched_feb.sha256'))
    r = h24_preflight.check(cd)
    print(os.path.relpath(cd, P), 'preflight', 'OK' if r['ok'] else 'FAIL', r['errors'], r['warnings'])
    if not r['ok']: sys.exit(2)


def run(cd, gpu, ncores, window='extension'):
    cd = os.path.normpath(cd); prm = json.load(open(cd + '_params.json')); wd = os.path.join(cd, 'w_' + window); sfx = '' if window == 'extension' else '_' + window
    if not h24_preflight.valid(cd): sys.exit(f'{cd}: no valid preflight (h24)')
    lock = open(os.path.join(P, 'human_study', '.cpu_launch.lock'), 'w'); fcntl.flock(lock, fcntl.LOCK_EX)
    busy = cpu_busy(); usable = [c for c in sorted(busy, key=busy.get) if busy[c] < 0.10 and c not in claimed_cores()]
    if len(usable) < ncores: sys.exit(f'only {len(usable)} idle cores')
    cores = sorted(usable[:ncores])
    libs = ':'.join([os.path.join(P, 'third_party/mkl/lib'), os.path.join(P, 'third_party/cuda/lib')])
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS=str(ncores), MKL_NUM_THREADS=str(ncores),
               LD_LIBRARY_PATH=libs, KMP_STACKSIZE='1G', OMP_STACKSIZE='1G', **{k: str(v) for k, v in (prm.get('restart_env') or {}).items()})
    shutil.copy(os.path.join(cd, 'case.xplt'), wd)            # the restart reopens (appends to) the plot file named in the archive
    cmd = ['prlimit', '--stack=unlimited', 'taskset', '-c', ','.join(map(str, cores)), FEBIO_FRIC, '-r', 'restart.feb', '-o', 'case.log',
           '-silent', '-output_negative_jacobians=50', '-cnf', CNF]
    t0 = time.time(); open(os.path.join(cd, 'started_at' + sfx), 'w').write(str(t0))
    json.dump(dict(cmd=cmd, env={k: env[k] for k in env if k.startswith(('BIOCAGE_', 'CUDA_', 'OMP_'))}, febio=FEBIO_FRIC,
                   febio_sha256=h24_preflight.sha(FEBIO_FRIC), lib_sha256=h24_preflight.sha(os.path.join(P, 'third_party/FEBio/cbuild_fric/lib/libfebiomech.so')), window=window),
              open(os.path.join(cd, 'launch' + sfx + '.json'), 'w'), indent=1)   # lib_sha256: the patched code lives in libfebiomech.so, the binary hash does not change between rebuilds
    p = subprocess.Popen(cmd, cwd=wd, env=env, stdout=subprocess.DEVNULL, stderr=open(os.path.join(cd, 'stderr.log'), 'w'))
    print(f'started {os.path.relpath(cd, P)} on GPU {gpu}, cores {cores[0]}..{cores[-1]}, env {prm.get("restart_env")}', flush=True)
    time.sleep(3); fcntl.flock(lock, fcntl.LOCK_UN)
    p.wait(); wall = time.time() - t0
    txt = open(os.path.join(wd, 'case.log'), errors='ignore').read()
    err = open(os.path.join(cd, 'stderr.log'), errors='ignore').read()
    drops = err.count('CRSSparseMatrix::add')     # patch-7 FECore guard: stiffness entries outside the sparse profile were DROPPED -> the window is invalid
    res = dict(exit=p.returncode, normal='N O R M A L' in txt[-4000:], wall_s=round(wall, 1), gpu=gpu, cores=ncores,
               core_h=round(ncores * wall / 3600, 3), gpu_h=round(wall / 3600, 3), profile_drops=drops, valid=(drops == 0),
               env_lines=[l.strip() for l in txt.splitlines() if 'BIOCAGE patch 7' in l][:6])
    if drops: print(f'INVALID: {drops} stiffness entries outside the matrix profile were dropped (see stderr.log)', flush=True)
    json.dump(res, open(os.path.join(cd, 'resources' + sfx + '.json'), 'w'), indent=1); print(os.path.relpath(cd, P), window, res, flush=True)
    open(os.path.join(cd, 'done' + sfx), 'w').write(str(time.time()))


if __name__ == '__main__':
    if sys.argv[1] == 'build': build(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif sys.argv[1] == 'run': run(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), *(sys.argv[5:6]))
    else: sys.exit(__doc__)
