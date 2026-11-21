"""2026-11-21 (授權自行決定, completes PI decision 9 'mu 0.3 official'): decks of the designs still judged at mu 0.35 only
(their 0.35 read-out is far from the lines, but the tied-shortcut consistency PHY-05 needs every design at one mu).
pilot_mu03/<p> = physio_fric3 params + mu 0.3; pilot_mu03G/<p> = physio_relG params + mu 0.3; h24 must pass.
p117 is not here (its mu 0.3 windows exist, full-Newton retry pending); p048 / p074 / p115 are not computable at mu 0.35 either."""
import json, subprocess, sys, os
sys.path.insert(0, 'scripts/5_compute'); import h24_preflight
A = 'human_study/al_v2/'
F = "p036 p066 p067 p094 p124 p146".split(); G = "p039 p050 p064 p068 p071 p082 p084 p088 p097 p101 p109 p116 p121 p127 p130 p140 p149".split()
for ids, src, dst in ((F, 'physio_fric3', 'pilot_mu03'), (G, 'physio_relG', 'pilot_mu03G')):
    for p in ids:
        out = A + f'{dst}/{p}'
        if os.path.exists(out) or any(os.path.isdir(out + f'_gpu{g}') for g in range(8)): print('exists', out); continue
        prm = json.load(open(A + f'{src}/{p}_params.json')); assert prm['mu'] == 0.35; prm['mu'] = 0.3
        json.dump(prm, open(out + '_params.json', 'w'), indent=1)
        subprocess.run([sys.executable, 'scripts/3_cage_case/h14_build_case.py', out + '_params.json', out], check=True, stdout=subprocess.DEVNULL)
        r = h24_preflight.check(out); print(p, dst, 'h24', r['ok'], r['errors'][:2], flush=True)
