"""Red team r0001: look at e02 output structure and the I-001 twist numbers."""
import json, glob, os, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
M = os.path.join(ROOT, 'human_study/evo/method')
d = json.load(open(os.path.join(M, 'fl_p062_physio.json')))
print(d.keys(), d['case'])
print(json.dumps(d['windows'], indent=0))
print(len(d['states'])); print(json.dumps(d['states'][0]))
print(open(os.path.join(M, 'e02.err')).read()[-1500:])
