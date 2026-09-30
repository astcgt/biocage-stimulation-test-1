"""Lightweight per-case / per-worker progress reporting.

Line format:
  GPU 3 | pid 12345 | case 7/18 cyclic/B_tread_L0500 | step 42/60 | 42.0% | elapsed 18m | ETA 25m | phase: cycle block (N=1.2e5)

* one log per case  : logs/progress/<case_id>.log
* one log per worker: logs/progress/worker_gpu<GPU>.log (a worker runs its cases sequentially -> no interleaving)
* files are opened line-buffered and flushed; a line is written at most every `min_interval` s unless progress advanced
  by >= `min_pct` % or the phase changed (negligible overhead: a few hundred short writes per case).
"""
import os, time

CTX = dict(gpu='?', case_no=0, n_cases=0)          # set by the worker (gpu_pool) before each case
LOGDIR = 'logs/progress'


def set_context(gpu, case_no, n_cases):
    CTX.update(gpu=gpu, case_no=case_no, n_cases=n_cases)


def _fmt(sec):
    if sec is None or sec != sec or sec == float('inf'): return '--'
    sec = int(sec)
    if sec < 3600: return f'{sec // 60}m{sec % 60:02d}s'
    return f'{sec // 3600}h{(sec % 3600) // 60:02d}m'


class Progress:
    def __init__(self, case_id, total_steps, min_interval=30.0, min_pct=2.0):
        os.makedirs(LOGDIR, exist_ok=True)
        self.case_id, self.total = case_id, total_steps
        self.t0 = time.time(); self.last_t = 0.0; self.last_pct = -100.0; self.last_phase = None
        self.min_interval, self.min_pct = min_interval, min_pct
        self.step, self.frac, self.phase = 0, 0.0, 'start'
        name = case_id.replace('/', '_')
        self.f_case = open(f'{LOGDIR}/{name}.log', 'a', buffering=1)
        self.f_worker = open(f'{LOGDIR}/worker_gpu{CTX["gpu"]}.log', 'a', buffering=1)
        self.update(0, phase='start', force=True)

    def update(self, step=None, frac=None, phase=None, total=None, extra='', force=False, minor=False):
        """step: current step; frac: fraction complete in [0,1] (default step/total); phase: current major phase.
        minor=True: phase text is updated but only written on the time/percent triggers (sub-steps, solver passes)."""
        if step is not None: self.step = step
        if total is not None: self.total = total
        if frac is None and step is not None and self.total: frac = step / self.total
        if frac is not None: self.frac = min(max(frac, self.frac), 1.0)    # monotone
        if phase is not None: self.phase = phase
        now = time.time(); pct = 100 * self.frac
        if not (force or (self.phase != self.last_phase and not minor) or now - self.last_t >= self.min_interval or pct - self.last_pct >= self.min_pct):
            return
        el = now - self.t0
        eta = el * (1 - self.frac) / self.frac if self.frac > 1e-3 else None
        line = (f"GPU {CTX['gpu']} | pid {os.getpid()} | case {CTX['case_no']}/{CTX['n_cases']} {self.case_id} | "
                f"step {self.step}/{self.total} | {pct:5.1f}% | elapsed {_fmt(el)} | ETA {_fmt(eta)} | phase: {self.phase}"
                + (f' ({extra})' if extra else ''))
        stamp = time.strftime('%H:%M:%S ')
        for f in (self.f_case, self.f_worker):
            f.write(stamp + line + '\n'); f.flush()
        print(line, flush=True)
        self.last_t, self.last_pct, self.last_phase = now, pct, self.phase

    def done(self, note=''):
        self.frac = 1.0
        self.update(phase='done' + (f': {note}' if note else ''), force=True)
        self.f_case.close(); self.f_worker.close()
