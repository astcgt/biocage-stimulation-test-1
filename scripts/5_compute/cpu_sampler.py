"""Sample instantaneous CPU usage (cores busy) of each running FEBio process every DT s until none remain.
Writes CSV: time, case_dir, cores_busy.   usage: python cpu_sampler.py <out.csv> [dt]
"""
import os, sys, time, glob
out, dt = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
HZ = os.sysconf('SC_CLK_TCK'); uid = os.getuid()
def febio():
    r = {}
    for p in glob.glob('/proc/[0-9]*'):
        try:
            if os.stat(p).st_uid != uid: continue
            if 'febio4' not in open(f'{p}/cmdline').read(): continue
            f = open(f'{p}/stat').read().rsplit(')', 1)[1].split()
            r[int(p[6:])] = (int(f[11]) + int(f[12]), os.readlink(f'{p}/cwd'))
        except OSError:
            pass
    return r
with open(out, 'a') as fh:
    prev = febio(); t0 = time.time()
    while prev:
        time.sleep(dt); cur = febio(); now = time.time()
        for pid, (ticks, cwd) in cur.items():
            if pid in prev:
                fh.write(f'{now:.0f},{cwd.split("human_study/")[-1]},{(ticks - prev[pid][0]) / HZ / dt:.2f}\n')
        fh.flush(); prev = cur
