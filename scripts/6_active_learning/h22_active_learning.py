"""Active-learning screening of BIOCAGE designs (human C3-C4, bonded screening model; DECISIONS Q47-Q53).

Design variables : design A/B, gradient axial/radial/both, fabrication mix/interleave (12 combinations), distraction d 0.5-1.5 mm
Material inputs  : E_hard 250-900 MPa, E_soft 1.5-12 MPa (log scale), blend threshold theta 0.20-0.40 (uncertain -> robust)
Post-processing only (no extra runs): friction mu 0.2-0.5 -> worst case mu = 0.2; strengths -> lower bounds (hard 15, soft 3 MPa)

Each point = two FEBio cases built with h12 (cage mesh, cached) + h14 (bonded interface, Gent cage, 0.2 mm cage /
0.5 mm endplate meshes): 'iso' (ISO 18192-1 levels x1.00-x3.00, one cycle per level) and 'compress'.
Scores per point (from h15 summaries):
  dislocation y  = fraction of the ISO protocol (t 3 -> 13) completed before the first failure: anti-slip safety factor at
                   mu = 0.2 below 1, centre of pressure at / beyond the face edge (tipping), or functional failure (solver stop,
                   soft layer crushed). Designs completing the protocol get y = 1 + 0.5 tanh(min SF - 1) (margin bonus).
  capacity C     = force added beyond the release state at the first compression endpoint, or the Q40 lower bound.
Objective (Q48/Q49): maximise the worst-case (over the material range) dislocation score subject to C >= 150 N.
Surrogates: two mixed-categorical GPs (BoTorch). Next batch: candidates = 12 combinations x d grid; each scored by
min over a Sobol set of material samples of (mean + BETA*std) (optimistic-robust), feasibility by the same rule on log C;
the chosen designs are simulated at their worst predicted material sample (max-min robust search).
Initial batch: 48 Sobol points (each combination 4x). Stop: 150 points, or < 2 % improvement of the best feasible robust
score over 3 consecutive checkpoints taken every HIST_EVERY new results (the old "3 batches" at the batch-0 size).
Asynchronous (2026-10-22, after Alvi et al. 2019, PLAyBOOK): runtimes range from 2 h to > 16 h, so the loop no longer waits
for a whole batch. Whenever fewer than MIN_WAITING AL jobs are waiting in the queue it proposes enough points to fill the free
slots, with the points still running excluded from the proposal neighbourhood (local penalisation of busy locations).

usage: python h22_active_learning.py init         # create the initial batch, build and queue its cases
       python h22_active_learning.py collect      # post-process finished points
       python h22_active_learning.py next         # fit surrogates, propose / build / queue the next batch
       python h22_active_learning.py loop         # collect + next whenever the queue runs low (async; run in tmux)
       python h22_active_learning.py status
"""
import os, sys, json, time, glob, math, subprocess, itertools
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE))
AL = os.path.join(P, 'human_study', 'al_v2'); os.makedirs(AL, exist_ok=True)   # v2 screening model (2026-10-23); v1 kept in human_study/al
MESHES = os.path.join(P, 'human_study', 'al', 'meshes')                         # cage meshes are unchanged in v2 (nominal gap) -> shared cache
V2 = dict(insert_mode='expand', shrink=0.8, biodisc=False, release_dtmax=0.1, annulus_remnant=False)   # DECISIONS 2026-10-22/23
JOB = 'al_v2p'
STATE = os.path.join(AL, 'points.json'); LOG = os.path.join(AL, 'al.log')
QUEUE = os.path.join(P, 'human_study', 'queue')
JOB_CORES = 8   # FEBio here averages ~2.5 busy cores per run (measured 2026-10-22), so 16 pinned cores left most of them idle
TEMPLATE = os.path.join(P, 'human_study', 'cage_test', 'params_A_iso_tied2.json')

DESIGNS, GRADS, FABS = ('A', 'B'), ('axial', 'radial', 'both'), ('mix', 'interleave')
COMBOS = list(itertools.product(DESIGNS, GRADS, FABS))                                   # 12
BOUNDS = dict(d=(0.5, 1.5), logEh=(math.log(250), math.log(900)), logEs=(math.log(1.5), math.log(12)), theta=(0.20, 0.40))
CONT = ('d', 'logEh', 'logEs', 'theta')
MU_WORST, MU_SIM = 0.2, 0.35
SIG_HARD, SIG_SOFT = 15.0, 3.0                    # strength lower bounds (robust damage endpoint)
CAP_MIN = 150.0                                   # Q49
T_ISO0, T_ISO1 = 3.0, 13.0                        # ISO protocol window (ramp + 9 levels x 1 cycle)
N_INIT, N_MAX, BETA = 48, 150, 1.0
MIN_WAITING, HIST_EVERY = 2, 8                   # async proposal trigger; stop-criterion checkpoint spacing
HOLD = os.path.join(AL, 'HOLD_PROPOSALS')          # if this file exists: collect results but propose no new points (model change pending)


def log(msg):
    line = time.strftime('%m-%d %H:%M:%S ') + msg
    print(line, flush=True); open(LOG, 'a').write(line + '\n')


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else dict(points=[], batches=[])


def save(st):
    json.dump(st, open(STATE + '.tmp', 'w'), indent=1); os.replace(STATE + '.tmp', STATE)


# ------------------------------------------------------------------ building cases
def mesh_path(design, grad, fab, d):
    return os.path.join(MESHES, f'cage_{design}_{grad}_{fab}_d{d:.3f}.npz')


def build_point(pt):
    """Cage mesh (cached) + both cases + queue files. Runs in a worker process."""
    x = pt['x']; mp = mesh_path(x['design'], x['grad'], x['fab'], x['d'])
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    tmpl = json.load(open(os.path.join(P, TEMPLATE)))
    if not os.path.exists(mp):
        subprocess.run(['python', os.path.join(P, 'scripts/3_cage_case/h12_cage_mesh.py'), tmpl['fsu'], tmpl['frame'],
                        x['design'], f"{x['d']:.3f}", x['grad'], x['fab'], mp], cwd=P, check=True, stdout=subprocess.DEVNULL)
    out = {}
    for test in ('iso', 'compress'):
        prm = dict(tmpl); prm.update(cage_npz=os.path.relpath(mp, P), test=test, d=x['d'], E_hard=x['E_hard'], E_soft=x['E_soft'],
                                     theta=x['theta'], sig_hard=SIG_HARD, sig_soft=SIG_SOFT, mu=MU_SIM, iso_max_level=3.0, iso_cycles=1, **V2)
        cdir = os.path.join(AL, 'cases', f"p{pt['id']:03d}_{test}"); os.makedirs(os.path.dirname(cdir), exist_ok=True)
        pj = cdir + '_params.json'; json.dump(prm, open(pj, 'w'), indent=1)
        if not os.path.exists(os.path.join(cdir, 'case.feb')):
            subprocess.run(['python', os.path.join(P, 'scripts/3_cage_case/h14_build_case.py'), pj, cdir], cwd=P, check=True,
                           stdout=subprocess.DEVNULL)
        job = os.path.join(QUEUE, f"{JOB}{pt['id']:03d}_{test}.job")
        if not os.path.exists(job):
            json.dump(dict(case_dir=os.path.relpath(cdir, P), cores=JOB_CORES, mem_gb=8, host_mem_gb_gpu=4), open(job, 'w'))
        out[test] = os.path.relpath(cdir, P)
    return pt['id'], out


def build_and_queue(st, ids, workers=16):
    pts = {p['id']: p for p in st['points']}
    with ProcessPoolExecutor(workers) as ex:
        for pid, cases in ex.map(build_point, [pts[i] for i in ids]):
            pts[pid]['cases'] = cases; pts[pid]['status'] = 'queued'; save(st)
            log(f'built and queued point {pid}')


# ------------------------------------------------------------------ design points
def x_from_unit(combo, u):
    v = {k: BOUNDS[k][0] + ui * (BOUNDS[k][1] - BOUNDS[k][0]) for k, ui in zip(CONT, u)}
    return dict(design=combo[0], grad=combo[1], fab=combo[2], d=round(v['d'], 3), E_hard=round(math.exp(v['logEh']), 2),
                E_soft=round(math.exp(v['logEs']), 3), theta=round(v['theta'], 3))


def encode(x):
    """GP input: 3 categorical indices + 4 continuous in [0, 1]."""
    c = [DESIGNS.index(x['design']), GRADS.index(x['grad']), FABS.index(x['fab'])]
    v = dict(d=x['d'], logEh=math.log(x['E_hard']), logEs=math.log(x['E_soft']), theta=x['theta'])
    return c + [(v[k] - BOUNDS[k][0]) / (BOUNDS[k][1] - BOUNDS[k][0]) for k in CONT]


def cmd_init():
    st = load()
    if st['points']: log('init: points already exist, nothing to do'); return
    from scipy.stats import qmc
    U = qmc.Sobol(4, scramble=True, seed=20261021).random(N_INIT)
    for i, u in enumerate(U):
        st['points'].append(dict(id=i, batch=0, x=x_from_unit(COMBOS[i % len(COMBOS)], u), status='new'))
    st['batches'].append(dict(batch=0, ids=list(range(N_INIT)), created=time.strftime('%Y-%m-%d %H:%M')))
    save(st); log(f'init: {N_INIT} Sobol points'); build_and_queue(st, list(range(N_INIT)))


# ------------------------------------------------------------------ collecting results
def ended_dir(case):
    """Return the folder (case or its _gpuN copy) whose FEBio log has terminated, else None."""
    for d in [os.path.join(P, case)] + sorted(glob.glob(os.path.join(P, case) + '_gpu*')):
        lg = os.path.join(d, 'case.log')
        if os.path.exists(lg) and any(k in open(lg, errors='ignore').read()[-4000:] for k in ('N O R M A L', 'E R R O R')):
            return d
    return None


def score_iso(s, normal):
    fd = s.get('friction_demand') or []; mu = s.get('mu_used', MU_SIM); t_fail, why = None, None
    for r in fd:
        sf = min(r.get('top_safety_factor', 1e9), r.get('bot_safety_factor', 1e9)) * MU_WORST / mu
        ecc = max(r.get('top_cop_eccentricity', 0), r.get('bot_cop_eccentricity', 0))
        if sf < 1: t_fail, why = r['t'], 'slip'; break
        if ecc >= 1: t_fail, why = r['t'], 'tipping'; break
    if t_fail is None:
        if normal and s['completed_time'] >= T_ISO1 - 1e-6: t_fail, why = T_ISO1, None
        else: t_fail, why = s['completed_time'], 'functional failure'
    c = float(np.clip((t_fail - T_ISO0) / (T_ISO1 - T_ISO0), 0, 1))
    sfs = [min(r.get('top_safety_factor', 1e9), r.get('bot_safety_factor', 1e9)) * MU_WORST / mu for r in fd if r['t'] <= t_fail]
    min_sf = float(min(sfs)) if sfs else None
    y = c + (0.5 * math.tanh(min_sf - 1) if (c >= 1 and min_sf is not None) else 0.0)
    return dict(y=y, iso_completion=c, iso_failure=why, iso_t_fail=t_fail, min_sf_mu02=min_sf,
                max_tension=s.get('max_tension_area_frac'), max_cop=s.get('max_cop_eccentricity'))


def score_compress(s):
    C = s.get('capacity_N')
    if C is None: C = s.get('capacity_lower_bound_N')
    if C is None: C = s.get('max_force_N') or 0.0
    return dict(C=float(C), capacity_mode=s.get('failure_mode') or ('lower bound (Q40)' if s.get('functional_failure') else None),
                clamp_N=s.get('clamp_after_release_N'), retained_mm=s.get('retained_distraction_mm'))


def cmd_collect():
    st = load(); n = 0
    for p in st['points']:
        if p.get('status') != 'queued': continue
        dirs = {t: ended_dir(c) for t, c in p['cases'].items()}
        if not all(dirs.values()): continue
        res = {}
        for t, d in dirs.items():
            subprocess.run(['python', os.path.join(P, 'scripts/4_postprocess/h15_post_case.py'), d], cwd=P, stdout=subprocess.DEVNULL)
            s = json.load(open(os.path.join(d, 'summary.json')))
            normal = 'N O R M A L' in open(os.path.join(d, 'case.log'), errors='ignore').read()[-4000:]
            res.update(score_iso(s, normal) if t == 'iso' else score_compress(s))
        p.update(res=res, status='done', ran_in={t: os.path.relpath(d, P) for t, d in dirs.items()}); n += 1
        log(f"point {p['id']}: y {res['y']:.3f} ({res['iso_failure']}) C {res['C']:.0f} N")
    save(st); log(f'collect: {n} new results'); return n


# ------------------------------------------------------------------ surrogate + proposal
def fit_gp(X, y):
    import torch
    from botorch.models import MixedSingleTaskGP
    from botorch.fit import fit_gpytorch_mll
    from gpytorch.mlls import ExactMarginalLogLikelihood
    from botorch.models.transforms.outcome import Standardize
    Xt = torch.tensor(X, dtype=torch.double); yt = torch.tensor(y, dtype=torch.double).unsqueeze(-1)
    m = MixedSingleTaskGP(Xt, yt, cat_dims=[0, 1, 2], outcome_transform=Standardize(m=1))
    fit_gpytorch_mll(ExactMarginalLogLikelihood(m.likelihood, m)); return m


def predict(m, X):
    import torch
    with torch.no_grad():
        post = m.posterior(torch.tensor(X, dtype=torch.double))
        return post.mean.squeeze(-1).numpy(), post.variance.clamp_min(1e-12).sqrt().squeeze(-1).numpy()


def robust_table(my, mc, n_u=64):
    """For every candidate design: worst case over material samples of optimistic y and log C, plus the worst sample."""
    from scipy.stats import qmc
    U = qmc.Sobol(3, scramble=True, seed=7).random(n_u)                      # (logEh, logEs, theta) in [0, 1]
    dgrid = np.linspace(0, 1, 21); rows = []
    for ci, (dsg, gr, fb) in enumerate(COMBOS):
        for du in dgrid:
            X = np.array([[DESIGNS.index(dsg), GRADS.index(gr), FABS.index(fb), du, *u] for u in U])
            m_y, s_y = predict(my, X); m_c, s_c = predict(mc, X)
            rows.append(dict(combo=ci, du=du, ucb_y=float((m_y + BETA * s_y).min()), mean_y=float(m_y.min()),
                             ucb_logC=float((m_c + BETA * s_c).min()), mean_logC=float(m_c.min()),
                             worst_u=U[int(np.argmin(m_y))].tolist()))
    return rows


def batch_size():
    """Idle GPUs + CPU slots (JOB_CORES cores) within the memory cap, as two jobs per point (PI Q34)."""
    sys.path.insert(0, os.path.join(P, 'scripts/5_compute'))
    import h19_scheduler as h; from h06_run_cpu_batch import cpu_busy, claimed_cores
    g = sum(1 for s in h.gpu_state().values() if s['idle'])
    b = cpu_busy(); c = sum(1 for k, v in b.items() if v < 0.10 and k not in claimed_cores())
    slots = min(g + c // JOB_CORES, int(h.mem_free_gb() // 6))
    return max(1, slots // 2)


def waiting_jobs():
    """AL jobs queued but not yet started by the scheduler."""
    return len(glob.glob(os.path.join(QUEUE, JOB + '*.job')))


def cmd_next():
    st = load(); done = [p for p in st['points'] if p.get('status') == 'done']
    if st.get('next_after', 0) > time.time(): return True                  # last proposal found nothing new: wait
    if len(st['points']) >= N_MAX: log('next: point budget reached (150)'); return False
    if len(done) < 8: log('next: not enough results yet'); return False
    X = [encode(p['x']) for p in done]
    y = [p['res']['y'] for p in done]; lc = [math.log(max(p['res']['C'], 1.0)) for p in done]
    my, mc = fit_gp(X, y), fit_gp(X, lc)
    rows = robust_table(my, mc)
    feas = [r for r in rows if r['ucb_logC'] >= math.log(CAP_MIN)] or rows
    best = max((r['mean_y'] for r in rows if r['mean_logC'] >= math.log(CAP_MIN)), default=None)
    hist = st.setdefault('history', [])
    if not hist or len(done) >= hist[-1]['n_done'] + HIST_EVERY:
        hist.append(dict(n_done=len(done), best_robust_feasible_y=best, time=time.strftime('%Y-%m-%d %H:%M')))
    h = [x['best_robust_feasible_y'] for x in hist if x['best_robust_feasible_y'] is not None]
    if len(h) >= 4 and all(abs(h[-1] - v) <= 0.02 * max(abs(h[-1]), 1e-6) for v in h[-4:-1]):
        log(f'next: stop - best feasible robust score {h[-1]:.3f} changed < 2 % over 3 checkpoints'); save(st); return False
    q = min(batch_size(), N_MAX - len(st['points']))
    chosen = [dict(combo=COMBOS.index((p['x']['design'], p['x']['grad'], p['x']['fab'])), du=encode(p['x'])[3])
              for p in st['points'] if p.get('status') in ('new', 'queued')]          # busy locations
    n_busy = len(chosen)
    for r in sorted(feas, key=lambda r: -r['ucb_y']):                       # greedy, keep designs apart from chosen and busy ones
        if any(r['combo'] == c['combo'] and abs(r['du'] - c['du']) < 0.15 for c in chosen): continue
        chosen.append(r)
        if len(chosen) >= n_busy + q: break
    chosen = chosen[n_busy:]
    if not chosen:
        st['next_after'] = time.time() + 1800; save(st); log('next: every candidate is near a running point; retry in 30 min')
        return True
    bno = len(st['batches']); n0 = len(st['points']); ids = []
    for k, r in enumerate(chosen):
        u = [r['du']] + r['worst_u']
        st['points'].append(dict(id=n0 + k, batch=bno, x=x_from_unit(COMBOS[r['combo']], u), status='new',
                                 acq=dict(ucb_y=r['ucb_y'], mean_y=r['mean_y'], ucb_logC=r['ucb_logC'])))
        ids.append(n0 + k)
    st['batches'].append(dict(batch=bno, ids=ids, created=time.strftime('%Y-%m-%d %H:%M'), best_robust_feasible_y=best))
    save(st); log(f'next: batch {bno} with {len(ids)} points (best robust feasible y so far {best})')
    build_and_queue(st, ids); return True


def cmd_status():
    st = load(); ps = st['points']; by = {}
    for p in ps: by[p.get('status')] = by.get(p.get('status'), 0) + 1
    print(json.dumps(dict(points=len(ps), by_status=by, batches=len(st['batches']), history=st.get('history', [])[-3:]), indent=1))
    done = sorted([p for p in ps if p.get('status') == 'done'], key=lambda p: -p['res']['y'])[:5]
    for p in done: print(p['id'], p['x'], {k: p['res'][k] for k in ('y', 'iso_failure', 'C')})


def cmd_loop():
    log('loop start (asynchronous)'); stopped = False
    while True:
        try:
            cmd_collect(); st = load()
            pending = [p for p in st['points'] if p.get('status') in ('new', 'queued')]
            n_done = sum(p.get('status') == 'done' for p in st['points'])
            if not stopped and n_done >= 8 and waiting_jobs() < MIN_WAITING and not os.path.exists(HOLD):
                stopped = not cmd_next()
            if stopped and not pending: log('loop: finished (stop criterion or budget)'); break
        except Exception:
            import traceback; log('ERROR ' + traceback.format_exc().replace('\n', ' | '))
        time.sleep(300)


if __name__ == '__main__':
    {'init': cmd_init, 'collect': cmd_collect, 'next': cmd_next, 'loop': cmd_loop, 'status': cmd_status}[sys.argv[1]]()
