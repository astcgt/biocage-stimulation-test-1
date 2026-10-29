"""Chain the physio_rot passes without a person in the loop (2026-10-30: the queue sat empty twice after a pass ended).
When no job with the prefix of pass k is queued or running: run the e04 slip-out screen (biocage-evo) on the finished runs
of pass k, then queue pass k+1 (h28, previous = pass k) for the designs whose windows stayed below the target moment.
Idempotent; re-run it any time (resume_all.sh). usage: python h29_rot_chain.py  [loops every 5 min until the last pass]
"""
import os, sys, json, glob, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(os.path.dirname(HERE)); Q = os.path.join(P, 'human_study/queue')
EVO = os.path.join(os.path.dirname(P), 'biocage-evo'); AL = os.path.join(P, 'human_study/al_v2')
DYN = '{"physio_dynamic": {"density": 1e-6, "rhoi": 0.0}}'
PASSES = [('physrotD_', 'physio_rot_dyn'), ('physrotD2_', 'physio_rot_dyn2')]      # slow dynamic, PI 2026-10-30
W = ['flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right']
LOG = os.path.join(P, 'human_study/rot_chain.log')


def log(m):
    with open(LOG, 'a') as f: f.write(time.strftime('%m-%d %H:%M:%S ') + m + '\n')


def busy(prefix):
    return any(os.path.basename(f).startswith(prefix) for d in ('', 'running') for f in glob.glob(os.path.join(Q, d, '*.job')))


def screen(sub):
    """e04 on every finished run of a pass -> designs with a window below the target."""
    low = set()
    for d in sorted(glob.glob(os.path.join(AL, sub, 'p*_gpu*'))):
        lg = os.path.join(d, 'case.log')
        if not os.path.exists(lg) or 'N O R M A L' not in open(lg, errors='ignore').read(): continue
        o = os.path.join(EVO, 'results/method/e04_rot', f'{sub}__{os.path.basename(d)}.json')
        if not os.path.exists(o):
            subprocess.run(['timeout', '1500', 'python', 'methods/e04_dislocation.py', d, o], cwd=EVO, capture_output=True)
        if os.path.exists(o):
            w = json.load(open(o))['windows']
            if not all(not isinstance(w[k], str) and w[k]['target_reached'] for k in W): low.add(os.path.basename(d)[:4])
    return sorted(low)


def main():
    while True:
        for k, (pre, sub) in enumerate(PASSES[:-1]):
            nxt_pre, nxt_sub = PASSES[k + 1]
            if busy(pre) or os.path.exists(os.path.join(AL, nxt_sub + '.queued')): continue
            low = screen(sub); log(f'{sub} finished: {len(low)} designs below target -> {nxt_sub}')
            if low:
                r = subprocess.run(['python', os.path.join(HERE, 'h28_physio_prerun.py'), '8', 'physio_rot', 'al_v2/' + nxt_sub, nxt_pre,
                                    ','.join(low), 'al_v2/' + sub, DYN], cwd=P, capture_output=True, text=True)
                log(r.stdout[-2000:] + r.stderr[-500:])
            open(os.path.join(AL, nxt_sub + '.queued'), 'w').write(','.join(low))
        pre, sub = PASSES[-1]
        if os.path.exists(os.path.join(AL, sub + '.queued')) and not busy(pre):
            low = screen(sub); log(f'{sub} (last pass) finished: {len(low)} designs still below target: {low}'); return
        time.sleep(300)


if __name__ == '__main__':
    main()
