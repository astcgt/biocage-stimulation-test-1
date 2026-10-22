"""Gap library: the REAL distracted endplate positions as a function of the distraction d (PI 2026-10-22, auto (no reply):
cage height = the actual gap after distraction, as a surgeon sizes the cage with trial spacers after distracting).

During distraction the stretched annulus / ligaments pull both endplates towards each other (C4 rises up to ~0.3 mm at
d 1.5), so a cage built on the undeformed endplates + d is oversized by a d-dependent press fit. The distraction step does
not involve the cage (no contact, cage fixed), so the deformed endplates depend on d only: one distraction-only FEBio run
per d on a grid, then h12 interpolates the endplate displacements linearly in d.

usage: python h25_gap_library.py build     # cases in human_study/gaplib/d*/ (distraction only, fine steps)
       python h25_gap_library.py run       # start them in tmux (biocage_gaplib_*), after a preflight check
       python h25_gap_library.py collect   # -> human_study/gaplib/gaplib.npz (d, ids_top/bot, U_top/bot [nd, n, 3])
"""
import os, sys, json, subprocess, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(P, 'human_study', 'gaplib'); D_GRID = np.round(np.arange(0.5, 1.501, 0.1), 2)
TEMPLATE = os.path.join(P, 'human_study', 'cage_test', 'params_A_iso_tied2.json')


def case_dir(d): return os.path.join(OUT, f'd{d:.2f}')


def build():
    os.makedirs(OUT, exist_ok=True); tmpl = json.load(open(TEMPLATE))
    for d in D_GRID:
        cd = case_dir(d); mesh = cd + '_cage.npz'
        if not os.path.exists(mesh):       # any cage works: it is fixed and out of contact during distraction
            subprocess.run(['python', os.path.join(HERE, 'h12_cage_mesh.py'), tmpl['fsu'], tmpl['frame'], 'A', f'{d:.3f}', 'axial', 'mix',
                            mesh], cwd=P, check=True, stdout=subprocess.DEVNULL)
        prm = dict(tmpl); prm.update(cage_npz=os.path.relpath(mesh, P), test='compress', d=float(d), E_hard=400.0, E_soft=4.0,
                                     theta=0.3, sig_hard=15.0, sig_soft=3.0, mu=0.35, iso_max_level=3.0, iso_cycles=1,
                                     biodisc=False, only_distract=True, distract_dt=0.025)
        json.dump(prm, open(cd + '_params.json', 'w'), indent=1)
        subprocess.run(['python', os.path.join(HERE, 'h14_build_case.py'), cd + '_params.json', cd], cwd=P, check=True,
                       stdout=subprocess.DEVNULL)
        print('built', os.path.relpath(cd, P))


def run():
    sys.path.insert(0, os.path.join(P, 'scripts/5_compute')); import h24_preflight as pf
    for d in D_GRID:
        cd = case_dir(d); r = pf.check(cd)
        if not r['ok']: print('preflight FAILED', cd, r['errors']); continue
        sh = (f"cd '{cd}' && sha256sum case.feb | cut -d' ' -f1 > launched_feb.sha256 && OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 "
              f"LD_LIBRARY_PATH='{P}/third_party/mkl/lib' KMP_STACKSIZE=1G prlimit --stack=unlimited "
              f"'{P}/third_party/FEBio/cbuild/bin/febio4' -i case.feb -silent -output_negative_jacobians=30 > stdout.txt 2>&1")
        subprocess.run(['tmux', 'new-session', '-d', '-s', f'biocage_gaplib_{d:.2f}', sh]); print('started', d)


def read_log(fn):
    out, t, rows = {}, None, []
    for l in open(fn):
        if l.startswith('*Time'):
            if t is not None and rows: out[t] = np.array(rows)
            t = float(l.split('=')[1]); rows = []
        elif l[:1].isdigit(): rows.append([float(v) for v in l.split(',')])
    if t is not None and rows: out[t] = np.array(rows)
    return out


def collect():
    U = {'top': [], 'bot': []}; ids = {}
    for d in D_GRID:
        cd = case_dir(d)
        assert 'N O R M A L' in open(os.path.join(cd, 'case.log'), errors='ignore').read()[-4000:], f'{cd} did not finish normally'
        for s, fn in (('top', 'C3_endplate_nodes.txt'), ('bot', 'C4_endplate_nodes.txt')):
            L = read_log(os.path.join(cd, fn)); a = L[max(L)]
            assert abs(max(L) - 1.0) < 1e-6
            ids[s] = a[:, 0].astype(int); U[s].append(a[:, 1:4])
    np.savez(os.path.join(OUT, 'gaplib.npz'), d=D_GRID, ids_top=ids['top'], ids_bot=ids['bot'],
             U_top=np.array(U['top']), U_bot=np.array(U['bot']))
    for k, d in enumerate(D_GRID):
        print(f"d {d:.2f}: C3 endplate uz mean {U['top'][k][:, 2].mean():+.3f} (lift {d:.2f}), C4 uz max {U['bot'][k][:, 2].max():+.3f}")


if __name__ == '__main__':
    {'build': build, 'run': run, 'collect': collect}[sys.argv[1]]()
