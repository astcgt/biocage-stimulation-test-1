"""Run a split physio_rot case (h30): the insertion run (case.feb, dumped at the end of each analysis step), then each
window as an independent FEBio restart from that end state (w_<name>/restart.feb), one after the other on the same cores.
A window that already terminated is skipped (resume after an interruption); a failed window does not stop the others.
Called by h06 / h18 (inside their taskset / GPU environment) when the case dir has split.json.
usage: python h31_split_run.py <case_dir> [extra FEBio args, e.g. -cnf <cudss.xml>]
A restart needs the same -cnf as the insertion run (the archive refers to the cuDSS solver plugin).
"""
import os, sys, json, glob, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h06_run_cpu_batch import FEBIO, febio_args

d, extra = sys.argv[1], sys.argv[2:]
ended = lambda log: os.path.exists(log) and any(k in open(log, errors='ignore').read()[-4000:] for k in ('N O R M A L', 'E R R O R'))
if not ended(os.path.join(d, 'case.log')):
    fargs, _ = febio_args(d, 'case.feb')
    subprocess.run([FEBIO] + fargs + extra, cwd=d, stdout=subprocess.DEVNULL)
if 'N O R M A L' not in open(os.path.join(d, 'case.log'), errors='ignore').read()[-4000:]: sys.exit(1)   # insertion failed
for w in json.load(open(os.path.join(d, 'split.json')))['windows']:
    wd = os.path.join(d, 'w_' + w)
    if ended(os.path.join(wd, 'case.log')): continue
    for f in os.listdir(wd):                                # outputs of an interrupted attempt (FEBio appends to them)
        if not f.endswith(('.feb', '.json', '.npz')): os.remove(os.path.join(wd, f))
    shutil.copy(os.path.join(d, 'case.xplt'), wd)           # the restart reopens the plot file named in the archive
    subprocess.run([FEBIO, '-r', 'restart.feb', '-o', 'case.log', '-silent', '-output_negative_jacobians=50'] + extra,
                   cwd=wd, stdout=subprocess.DEVNULL)
