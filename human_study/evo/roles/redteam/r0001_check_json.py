"""Red team: schema check of my findings and verdict."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import json, glob
need = {'id', 'round', 'target', 'severity', 'claim', 'evidence', 'how_to_reproduce', 'fix_options', 'summary_zh'}
for f in sorted(glob.glob(os.path.join(_env.ROOT, 'human_study/evo/findings/F-*.json'))):
    d = json.load(open(f)); miss = need - set(d)
    print(os.path.basename(f), d['severity'], 'missing' if miss else 'ok', miss or '', len(d['fix_options']))
v = json.load(open(os.path.join(_env.ROOT, 'human_study/evo/board/r0001/redteam.json')))
print('verdict ok', {'role', 'round', 'findings', 'top3', 'summary_zh'} <= set(v), len(v['findings']))
