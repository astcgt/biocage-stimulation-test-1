"""Red team r0001: gate 2 sanity - what load does the FEBio intact-FSU reference (flex_pos_y) apply, and what did FEBio
produce at t 0.1-0.3, vs the GPU record human_study/evo/gpufe_verify/gate2/flex_pos_y_gpu.json."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import re, json, xml.etree.ElementTree as ET
R = os.path.join(_env.ROOT, 'human_study/fsu/runs_refined/flex_pos_y')
root = ET.parse(os.path.join(R, 'fsu.feb')).getroot()
for tag in ('Boundary', 'Loads', 'Rigid', 'Control'):
    for el in root.iter(tag):
        s = re.sub(r'(<(?:NodeSet|Surface|elem|node)[^>]*>)[^<]{200,}', r'\1...', ET.tostring(el, encoding='unicode'))
        print('=====', tag); print(s[:2500])
for lc in root.iter():
    if lc.get('id') is not None and any(True for _ in lc.iter('point')) and lc.get('name') is None:
        print('LC', lc.get('id'), lc.attrib, [p.text for p in lc.iter('point')])
txt = open(os.path.join(R, 'C3pot_rigid.txt')).read().splitlines()
print('\n'.join(txt[:12])); print('...'); print('\n'.join(txt[-4:]))
gpu = json.load(open(os.path.join(_env.ROOT, 'human_study/evo/gpufe_verify/gate2/flex_pos_y_gpu.json')))
for r in gpu: print('GPU t', r['t'], 'Forced th', r['rigid']['2']['th'], 'Fixed M', r['rigid']['1']['M'], 'converged', r['converged'])
