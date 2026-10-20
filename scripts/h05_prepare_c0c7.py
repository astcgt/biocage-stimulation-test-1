"""Prepare FEBio 4 runs of the Herron 2020 26yoF C0-C7 model for the validation load cases.

FEBio 2.5 -> 4.13 compatibility (verified on C34.feb: steps 1-15 match Herron's log to < 0.1 %):
  * fiber theta/phi wrapped in <fiber type="angles">, local mat_axis moved from the fibre to the solid mixture
  * contact "sliding-tension-compression" -> "sliding-elastic"; its search_radius was RELATIVE in FEBio <= 3
    (radius = search_radius x largest bounding-box side of the model, FEBio v3.0 FESlidingElasticInterface.cpp:468)
    but is an ABSOLUTE length in FEBio 4 that also discards penetrations deeper than it (v4.13 :627-629). Herron's
    0.01 is therefore converted to 0.01 x 145.71 mm (C0-C7 model) = 1.457 mm. Without this the facets never touch.
  With these two changes Herron's C34.feb reproduces his FEBio 2.x log exactly (all 25 step times identical, normal
  termination); no extra solver stabilisation is needed.
Load case: pure moment (1.5 N m, ramped t = 1..2 as in Herron) on the C0 rigid body about x, y or z, either sign.
Kinematics: displacement of N_TRACK random cortical nodes per vertebra C1..C6 logged every step, so each vertebra's
rigid rotation can be fitted afterwards (Kabsch); C0 rotation from the rigid body log.

usage: python h05_prepare_c0c7.py <C0C7.feb> <out_dir>
"""
import sys, os, json, xml.etree.ElementTree as ET
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

N_TRACK = 150
CASES = {'flex_pos_y': ('Ry', +1), 'flex_neg_y': ('Ry', -1), 'lb_pos_x': ('Rx', +1), 'lb_neg_x': ('Rx', -1),
         'ar_pos_z': ('Rz', +1), 'ar_neg_z': ('Rz', -1)}
MOMENT_NMM = 1500.0

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)


def convert(root, ref_len):
    """ref_len = largest bounding-box side (mm) of the ORIGINAL Herron model the contact parameters belong to."""
    for m in root.find('Material').findall('material'):
        if m.get('type') != 'solid mixture':
            continue
        axes = set()
        for s in m.findall('solid'):
            ma = s.find('mat_axis')
            if ma is not None:
                axes.add((ma.get('type'), ma.text)); s.remove(ma)
            th, ph = s.find('theta'), s.find('phi')
            if th is not None:
                f = ET.SubElement(s, 'fiber', type='angles')
                for e in (th, ph):
                    s.remove(e); f.append(e)
        if axes:
            assert len(axes) == 1, axes
            t, txt = axes.pop(); ma = ET.Element('mat_axis', type=t); ma.text = txt; m.insert(0, ma)
    for c in root.iter('contact'):
        if c.get('type') == 'sliding-tension-compression':
            c.set('type', 'sliding-elastic')
            sr = c.find('search_radius')
            if sr is not None and sr.get('converted') is None:
                sr.text = f'{float(sr.text) * ref_len:.6g}'; sr.set('converted', 'abs_mm')


def vertebra_nodes(root):
    g = root.find('Geometry')
    X = {}
    for nb in g.findall('Nodes'):
        for n in nb.findall('node'):
            X[int(n.get('id'))] = [float(v) for v in n.text.split(',')]
    eb = [e for e in g.findall('Elements') if e.get('name') == 'Part4'][0]          # cortical bone C1..C6
    E = np.array([[int(v) for v in e.text.split(',')] for e in eb.findall('elem')])
    u, inv = np.unique(E, return_inverse=True); inv = inv.reshape(E.shape)
    A = coo_matrix((np.ones(inv.size), (np.repeat(inv[:, 0], 4), inv.ravel())), shape=(len(u),) * 2)
    nc, lab = connected_components(A, directed=False)
    comps = sorted([u[lab == k] for k in range(nc)], key=lambda ids: -np.mean([X[i][2] for i in ids]))
    assert len(comps) == 6, len(comps)
    rng = np.random.default_rng(0)
    track = {f'C{k + 1}': np.sort(rng.choice(ids, N_TRACK, replace=False)).tolist() for k, ids in enumerate(comps)}
    ref = {k: [X[i] for i in v] for k, v in track.items()}
    return track, ref


base = ET.parse(src)
root = base.getroot()
_P = np.array([[float(v) for v in n.text.split(',')] for nb in root.find('Geometry').findall('Nodes') for n in nb])
REF_LEN = float((_P.max(0) - _P.min(0)).max())          # FEBio BOX::radius() = largest side
convert(root, REF_LEN)
for sr in root.iter('search_radius'):
    if sr.get('converted'): del sr.attrib['converted']
track, ref = vertebra_nodes(root)
json.dump(dict(track=track, ref=ref, moment_Nmm=MOMENT_NMM), open(os.path.join(out, 'tracking_nodes.json'), 'w'))

for name, (dof, sign) in CASES.items():
    r = ET.fromstring(ET.tostring(root))
    rb = [b for b in r.find('Boundary').findall('rigid_body') if b.get('mat') == '2'][0]
    for f in rb.findall('force'):
        rb.remove(f)
    f = ET.SubElement(rb, 'force', bc=dof, lc='1'); f.text = str(sign * MOMENT_NMM)
    o = r.find('Output')
    lf = ET.SubElement(o, 'logfile')
    for k, ids in track.items():
        nd = ET.SubElement(lf, 'node_data', data='ux;uy;uz', file=f'{k}.txt', delim=',')
        nd.text = ','.join(map(str, ids))
    rd = ET.SubElement(lf, 'rigid_body_data', data='x;y;z;thx;thy;thz;Mx;My;Mz', file='C0_rigid.txt', delim=',')
    rd.text = '2'
    d = os.path.join(out, name); os.makedirs(d, exist_ok=True)
    ET.ElementTree(r).write(os.path.join(d, 'C0C7.feb'), encoding='ISO-8859-1', xml_declaration=True)
print('wrote', list(CASES), 'to', out)
