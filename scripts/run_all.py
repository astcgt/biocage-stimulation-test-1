"""Launch all FEM cases on the independent-job GPU pool.  Usage: CUDA_VISIBLE_DEVICES=3,4,7 python3 scripts/run_all.py [phase]"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpu_pool import run_jobs
from params import CYCLIC
from run_tests import MODES

DESIGNS = ('A_smooth', 'B_tread')


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if phase in ('all', '1'):
        jobs = [('static', d) for d in DESIGNS] + [('sixdof', d, mo) for mo in MODES for d in DESIGNS]
        run_jobs(jobs, 'run_tests', 'dispatch')

    if phase == 'rerun':   # v2: corrected cyclic ratcheting + shear modes extended to 5 mm
        jobs = [('sixdof', d, mo) for mo in MODES if mo.startswith('shear') for d in DESIGNS]
        for d in DESIGNS:
            s = json.load(open(f'results/test1_static/{d}/summary.json'))
            jobs = [('cyclic', d, lv, s['F_fail_N']) for lv in CYCLIC['levels']] + jobs
        run_jobs(jobs, 'run_tests', 'dispatch')

    if phase in ('all', '2'):
        jobs = []
        for d in DESIGNS:
            s = json.load(open(f'results/test1_static/{d}/summary.json'))
            jobs += [('cyclic', d, lv, s['F_fail_N']) for lv in CYCLIC['levels']]
        jobs.sort(key=lambda j: -j[2])          # highest levels first (shortest)... balanced by queue
        run_jobs(jobs, 'run_tests', 'dispatch')


if __name__ == '__main__':
    main()
