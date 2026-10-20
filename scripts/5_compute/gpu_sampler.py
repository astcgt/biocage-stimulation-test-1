"""Sample GPU utilisation / memory every 60 s; append to a CSV (time,index,util,mem_used,mem_total). usage: gpu_sampler.py <out.csv>"""
import sys, time, subprocess
out = sys.argv[1]
while True:
    r = subprocess.run(['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total',
                        '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout
    t = time.time()
    with open(out, 'a') as f:
        for line in r.strip().splitlines(): f.write(f'{t:.0f},{line.replace(" ", "")}\n')
    time.sleep(60)
