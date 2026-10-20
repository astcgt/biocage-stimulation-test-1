"""Build intact C3-C4 FSU load cases for the FSU-vs-full-model check: 1.5 N m pure moment on the C3 pot about global
x / y / z, both signs, same nucleus pre-pressure and time course as Herron. Logs C3 / C4 tracked cortical nodes (the
same nodes as the C0-C7 validation) so C3-C4 rotation is computed identically.

usage: python h10_fsu_cases.py <fsu.feb> <fsu.json> <c0c7 tracking_nodes.json> <out_dir> [threads-benchmark]
"""
import sys, os, json, xml.etree.ElementTree as ET, numpy as np
from scipy.spatial import cKDTree

fsu, fsu_info, trk_json, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'h05_prepare_c0c7.py')).read()
ns = {'ET': ET, 'np': np}; exec(src[src.index('def convert'):src.index('def vertebra_nodes')], ns)
REF = json.load(open(fsu_info))['herron_ref_length_mm']
trk = json.load(open(trk_json))
CASES = {'flex_pos_y': ('Ry', 1), 'flex_neg_y': ('Ry', -1), 'lb_pos_x': ('Rx', 1), 'lb_neg_x': ('Rx', -1),
         'ar_pos_z': ('Rz', 1), 'ar_neg_z': ('Rz', -1)}

base = ET.parse(fsu).getroot()
ns['convert'](base, REF)
for sr in base.iter('search_radius'): sr.attrib.pop('converted', None)
nodes = base.find('Geometry/Nodes')
ids = np.array([int(n.get('id')) for n in nodes]); P = np.array([[float(v) for v in n.text.split(',')] for n in nodes])
tree = cKDTree(P)
track, ref = {}, {}
for v in ('C3', 'C4'):
    R = np.array(trk['ref'][v]); d, j = tree.query(R); ok = d < 1e-3          # refined meshes keep only surface nodes
    assert ok.sum() >= 30, (v, ok.sum())
    track[v] = ids[j[ok]].tolist(); ref[v] = R[ok].tolist()
json.dump(dict(track=track, ref=ref), open(os.path.join(out, 'tracking_nodes.json'), 'w'))
for name, (dof, s) in CASES.items():
    r = ET.fromstring(ET.tostring(base))
    rb = [b for b in r.find('Boundary').findall('rigid_body') if b.get('mat') == '2'][0]
    ET.SubElement(rb, 'force', bc=dof, lc='1').text = str(1500.0 * s)
    lf = ET.SubElement(r.find('Output'), 'logfile')
    for v, nid in track.items():
        ET.SubElement(lf, 'node_data', data='ux;uy;uz', file=f'{v}.txt', delim=',').text = ','.join(map(str, nid))
    ET.SubElement(lf, 'rigid_body_data', data='x;y;z;thx;thy;thz;Mx;My;Mz', file='C3pot_rigid.txt', delim=',').text = '2'
    d = os.path.join(out, name); os.makedirs(d, exist_ok=True)
    ET.ElementTree(r).write(os.path.join(d, 'fsu.feb'), encoding='ISO-8859-1', xml_declaration=True)
print('wrote', list(CASES), 'ref_len', REF)
