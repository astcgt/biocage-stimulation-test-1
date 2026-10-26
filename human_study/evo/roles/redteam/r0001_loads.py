"""Red team r0001: print the boundary / load / step / load-curve definitions of a case.feb (long lines cut) and evaluate
the moment curves on the physio windows. usage: python -I r0001_loads.py [case_dir]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _env
import re, json, xml.etree.ElementTree as ET
cd = os.path.join(_env.ROOT, sys.argv[1] if len(sys.argv) > 1 else 'human_study/al_v2/cases/p062_physio')
root = ET.parse(os.path.join(cd, 'case.feb')).getroot()
for tag in ('Control', 'Boundary', 'Rigid', 'Loads', 'Step', 'Constraints', 'Discrete', 'Contact'):
    for el in root.iter(tag):
        s = ET.tostring(el, encoding='unicode')
        s = re.sub(r'(<(?:NodeSet|Surface|elem|node|delem)[^>]*>)[^<]{200,}', r'\1...', s)
        print('=====', tag); print(s[:6000])
for lc in root.iter():
    if lc.get('id') is None or not any(True for _ in lc.iter('point')): continue
    pts = [p.text for p in lc.iter('point')]
    print('LC', lc.tag, lc.get('id'), lc.attrib, 'n', len(pts), pts if len(pts) < 30 else pts[:5] + ['...'] + pts[-5:])
