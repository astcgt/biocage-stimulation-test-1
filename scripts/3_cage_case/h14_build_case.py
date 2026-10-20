"""Assemble an FEBio run of the ACDR BIOCAGE C3-C4 model (FEBio 2.5 dialect, run with FEBio 4.13).

Model: intact deformable-bone FSU (h08, or h17 with refined endplates + tied disc) rotated into the disc mid-plane frame (X anterior, Y left, Z disc normal,
origin = C3-C4 ICR), so rigid-body DOFs of the C3 pot are the ISO axes and its reference point (centre_of_mass) is the ICR.
Cortical bone keeps its original (CT-frame) orthotropy through an explicit mat_axis.
ACDR surgery (DECISIONS.md): disc hexes whose centroid lies inside the design-A footprint (same surgery for A and B) or in
the anterior 120 deg sector are removed; ALL 34 and PLL 34 springs removed; nucleus pre-pressure removed; nodes left
unconnected are fixed. Cage + biodisc (h12 npz, distracted configuration) added; materials per hard fraction.
Steps: 1 distract (t 0-1: C3 pot +d along Z, all other C3 DOFs fixed, cage fixed, no cage contact)
       2 insert + seat (t 1-2: contacts on, cage pinned statically determinate, C3 pot lowered 0.1 mm so both faces engage)
       2b release (t 2-3; cage-endplate contacts with friction mu, cage-annulus contact, C3 pot free; two cage
         bottom nodes held in X-Y to remove the cage's in-plane rigid modes before contact pressure exists); the C3-pot
         axial (Z) reaction ramps linearly to zero over the step (FEBio 'ramp' rigid force); X, Y, rotations stay fixed -> clamp
       3 test (t 3-): 'compress' | 'iso' | 'push_ant' | 'push_post'
Cage contacts (default 'global' mode, 2026-10-20): one persistent contact pair per endplate declared at model level, its
penalty switched off / ramped / held by a load curve and friction enabled from release on (see 'contact_mode'); the old
'per_step' mode re-declared them in every step after insertion. The facet-joint contacts are global as in Herron's model. FEBio writes plot data only for the first set of contact surfaces,
so the cage axial force in later steps is computed from cage element stresses (h15).

usage: python h14_build_case.py <params.json> <out_dir>
params: fsu, fsu_info, frame, cage_npz, test, d, E_hard, E_soft, sig_hard, sig_soft, theta, mu, (iso_max_level, iso_cycles)
"""
import sys, os, json, copy, xml.etree.ElementTree as ET
import numpy as np
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common')]
from cage_geom import Endplates, Frame
import shapely.geometry as sg
from shapely import vectorized

prm = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
NU_HARD, NU_SOFT, E_BIODISC, NU_BIODISC, W_SIG = 0.35, 0.45, 0.03, 0.45, 0.02
NU_SOFT = prm.get('nu_soft', 0.45)                 # Q42 tried 0.49; reverted to 0.45 (Q44, PI 2026-10-21): <0.2 % effect, 0.49 harder to converge
CONTACT_MODE = prm.get('contact_mode', 'global')     # 'global' (default since 2026-10-20) | 'per_step' (old cases)
PENALTY = prm.get('penalty', 10.0 if CONTACT_MODE == 'global' else 1.0)
CAGE_MAT = prm.get('cage_mat', 'gent')               # 'gent' (default, Q45) | 'uncoupled' (Mooney-Rivlin c2=0) | 'coupled' neo-Hookean
CONTACT_TYPE = prm.get('contact_type', 'elastic')     # 'elastic' | 'node' (regularised friction) | 'tied' (screening: bonded from release, friction demand post-processed)
GENT_JM = prm.get('gent_Jm', 0.7)                   # Q45 (PI 2026-10-21): locking near ~40 % uniaxial compression (screening)


def E_of_phi(phi):
    """Duan-2021-shaped jump: log-modulus follows a logistic in phi centred at the threshold theta."""
    s = lambda p: 1 / (1 + np.exp(-(p - prm['theta']) / W_SIG))
    S = (s(phi) - s(0.0)) / (s(1.0) - s(0.0))
    return prm['E_soft'] * (prm['E_hard'] / prm['E_soft']) ** S


def sig_of_phi(phi): return prm['sig_soft'] + phi * (prm['sig_hard'] - prm['sig_soft'])
def nu_of_phi(phi): return NU_SOFT + phi * (NU_HARD - NU_SOFT)


# ---------------------------------------------------------------- base model
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '1_validation', 'h05_prepare_c0c7.py')).read()
ns = {'ET': ET, 'np': np}; exec(src[src.index('def convert'):src.index('def vertebra_nodes')], ns)
root = ET.parse(prm['fsu']).getroot()
info = json.load(open(prm['fsu_info'])); REFINED = bool(info.get('refined'))
ns['convert'](root, info['herron_ref_length_mm'])
for sr in root.iter('search_radius'): sr.attrib.pop('converted', None)
ep = Endplates(prm['fsu'], prm['frame']); F = ep.F
geo = root.find('Geometry'); nodes_el = geo.find('Nodes')
X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in nodes_el}
for n in nodes_el:
    n.text = ','.join(f'{v:.6f}' for v in F.to(X[int(n.get('id'))])[0])
mats = root.find('Material')
for m in mats:
    if m.get('name') == 'Cortical':                    # keep CT-frame orthotropy after rotating the geometry
        ma = ET.Element('mat_axis', type='vector')
        ET.SubElement(ma, 'a').text = ','.join(f'{v:.6f}' for v in F.R @ np.array([1.0, 0, 0]))
        ET.SubElement(ma, 'd').text = ','.join(f'{v:.6f}' for v in F.R @ np.array([0, 1.0, 0]))
        m.insert(0, ma)
    if m.get('id') == '1':
        com = m.find('center_of_mass'); com.text = ','.join(f'{v:.6f}' for v in F.to(np.array([float(v) for v in com.text.split(',')]))[0])
    if m.get('id') == '2':
        m.find('center_of_mass').text = '0,0,0'        # C3 pot reference point = ICR (rotations about the ICR)

# ---------------------------------------------------------------- ACDR surgery
fp_A = ep.footprint
cx, cy = ep.outline.centroid.x, ep.outline.centroid.y
removed = 0
for eb in list(geo.findall('Elements')):
    if not (eb.get('name', '').startswith('disc_or_facet') and eb.get('name') != 'disc_or_facet_mat5'):
        continue
    for e in list(eb):
        ids = [int(v) for v in e.text.split(',')]
        P_e = F.to(np.array([X[i] for i in ids])); c = P_e.mean(0)
        ang = np.degrees(np.arctan2(c[1] - cy, c[0] - cx))
        if fp_A.contains(sg.Point(c[0], c[1])) or abs(ang) <= 60.0:
            eb.remove(e); removed += 1
    if len(eb) == 0: geo.remove(eb)
for s in [s for s in geo.findall('Surface') if s.get('name', '').startswith('Nucleus')]: geo.remove(s)
loads = root.find('Loads')
if loads is not None: root.remove(loads)
for d in [d for d in geo.findall('DiscreteSet') if d.get('name') in ('ALL 34', 'PLL 34')]: geo.remove(d)
disc = root.find('Discrete')
gone = {d.get('id') for d in disc.findall('discrete_material') if d.get('name') in ('ALL 34', 'PLL 34')}
for ch in list(disc):
    if (ch.tag == 'discrete_material' and ch.get('id') in gone) or (ch.tag == 'discrete' and ch.get('discrete_set') in ('ALL 34', 'PLL 34')):
        disc.remove(ch)
keep = [d for d in disc.findall('discrete_material')]; remap = {}
for k, d in enumerate(keep): remap[d.get('id')] = str(k + 1); d.set('id', str(k + 1))
for d in disc.findall('discrete'): d.set('dmat', remap[d.get('dmat')])
used = set()
for eb in geo.findall('Elements'):
    for e in eb: used |= set(int(v) for v in e.text.split(','))
for d in geo.findall('DiscreteSet'):
    for e in d: used |= set(int(v) for v in e.text.split(','))
orphans = sorted(set(X) - used)
if REFINED:
    # refined bone (h17, PI 2026-10-20): the disc remnant stays tied to the refined endplates; rebuild the tie's disc-side
    # surfaces from the remaining disc hexes only (faces whose 4 nodes are former disc-attachment nodes)
    for V in ('C3', 'C4'):
        att = set(info['disc_attach_ids'][V]); old = [s_ for s_ in geo.findall('Surface') if s_.get('name') == f'disc_on_{V}']
        for s_ in old: geo.remove(s_)
        q = ET.SubElement(geo, 'Surface', name=f'disc_on_{V}'); j = 0
        for eb in geo.findall('Elements'):
            if not (eb.get('name', '').startswith('disc_or_facet') and eb.get('name') != 'disc_or_facet_mat5'): continue
            for e in eb:
                t = [int(v) for v in e.text.split(',')]
                for fc in ([0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
                    quad = [t[i] for i in fc]
                    if set(quad) <= att: j += 1; ET.SubElement(q, 'quad4', id=str(j)).text = ','.join(map(str, quad))

# ---------------------------------------------------------------- cage
cz = np.load(prm['cage_npz']); Q, H, reg, phi, hard = cz['Q'], cz['hexes'], cz['region'], cz['phi'], cz['hard']
cinfo = json.loads(str(cz['info']))
n0 = max(X) + 1
cage_ids = np.arange(n0, n0 + len(Q))
for k, q in enumerate(Q):
    ET.SubElement(nodes_el, 'node', id=str(cage_ids[k])).text = ','.join(f'{v:.6f}' for v in q)
# statically determinate cage pin for seating (3 bottom nodes): n1 x,y,z; n2 y,z; n3 z  (only removes rigid modes)
bnodes = np.unique(cz['bot'].ravel()); bq = Q[bnodes]; ctr = bq[:, :2].mean(0)
pick = lambda off: int(cage_ids[bnodes[np.argmin(np.linalg.norm(bq[:, :2] - (ctr + np.array(off)), axis=1))]])
pin1, pin2, pin3 = pick([-1.0, 0]), pick([1.0, 0]), pick([0, 1.0])
hold = [pin1, pin2]
mid_max = max(int(m.get('id')) for m in mats)
next_eid = max(int(e.get('id')) for eb in geo.findall('Elements') for e in eb) + 1      # FEBio 2.5: consecutive element ids
fab = cinfo['fabrication']
groups = {}
for e, r in enumerate(reg):
    key = ('biodisc',) if r == 1 else (('hard', 1.0) if hard[e] else ('soft', 0.0)) if fab == 'interleave' else ('mix', float(phi[e]))
    groups.setdefault(key, []).append(e)
mat_table = {}; cage_order = []
for key in sorted(groups, key=str):
    mid_max += 1
    if key[0] == 'biodisc':
        E, nu, sig, f = E_BIODISC, NU_BIODISC, None, None
    else:
        f = key[1]; E, nu, sig = float(E_of_phi(f)), float(nu_of_phi(f)), float(sig_of_phi(f))
    if CAGE_MAT == 'gent' and key[0] != 'biodisc':
        # Gent (uncoupled, three-field hex): same initial shear modulus as neo-Hookean, stiffens sharply as I1-3 -> Jm, i.e. the
        # soft PLCL layers cannot be squashed much beyond ~40 % (screening simplification against element inversion, Q45)
        mu_, K_ = E / (2 * (1 + nu)), E / (3 * (1 - 2 * nu))
        m = ET.SubElement(mats, 'material', id=str(mid_max), name=f'cage_{key[0]}_{key[-1]}', type='Gent')
        ET.SubElement(m, 'density').text = '1'; ET.SubElement(m, 'G').text = f'{mu_:.6g}'
        ET.SubElement(m, 'Jm').text = f'{GENT_JM:g}'; ET.SubElement(m, 'k').text = f'{K_:.6g}'
    elif CAGE_MAT in ('uncoupled', 'gent'):
        # uncoupled neo-Hookean (Mooney-Rivlin, c2 = 0) with the same shear / bulk moduli; lets FEBio use the three-field
        # hex formulation for the soft, nearly incompressible PLCL layers (large compressive strains under the clamp)
        mu_, K_ = E / (2 * (1 + nu)), E / (3 * (1 - 2 * nu))
        m = ET.SubElement(mats, 'material', id=str(mid_max), name=f'cage_{key[0]}_{key[-1]}', type='Mooney-Rivlin')
        ET.SubElement(m, 'density').text = '1'; ET.SubElement(m, 'c1').text = f'{mu_ / 2:.6g}'
        ET.SubElement(m, 'c2').text = '0'; ET.SubElement(m, 'k').text = f'{K_:.6g}'
    else:
        m = ET.SubElement(mats, 'material', id=str(mid_max), name=f'cage_{key[0]}_{key[-1]}', type='neo-Hookean')
        ET.SubElement(m, 'density').text = '1'; ET.SubElement(m, 'E').text = f'{E:.6g}'; ET.SubElement(m, 'v').text = f'{nu:.4g}'
    mat_table[str(mid_max)] = dict(group=list(map(str, key)), E=E, nu=nu, strength=sig, phi=f, n_elem=len(groups[key]))
    cage_order += [(f'cage_{key[0]}_{key[-1]}', e) for e in groups[key]]
    eb = ET.SubElement(geo, 'Elements', type='hex8', mat=str(mid_max), name=f'cage_{key[0]}_{key[-1]}')
    for k, e in enumerate(groups[key]):
        ET.SubElement(eb, 'elem', id=str(next_eid)).text = ','.join(str(cage_ids[i]) for i in H[e]); next_eid += 1

# ---------------------------------------------------------------- surfaces
def surf(name, faces, ftype):
    s = ET.SubElement(geo, 'Surface', name=name)
    for k, f in enumerate(faces): ET.SubElement(s, ftype, id=str(k + 1)).text = ','.join(map(str, f))
surf('cage_top', [[cage_ids[i] for i in f] for f in cz['top']], 'quad4')
surf('cage_bot', [[cage_ids[i] for i in f] for f in cz['bot']], 'quad4')
# cage outer wall: side faces of cells with no neighbour outward
HC = cinfo.get('H_mm', 0.2)
cell = {tuple(np.round(Q[h].mean(0)[:2] / HC - 0.5).astype(int)) for h in H}
wall = []
for h in H:
    c = tuple(np.round(Q[h].mean(0)[:2] / HC - 0.5).astype(int))
    for (di, dj), f in (((1, 0), [1, 2, 6, 5]), ((-1, 0), [0, 4, 7, 3]), ((0, 1), [2, 3, 7, 6]), ((0, -1), [0, 1, 5, 4])):
        if (c[0] + di, c[1] + dj) not in cell: wall.append([cage_ids[h[i]] for i in f])
surf('cage_wall', wall, 'quad4')
# bony endplates = outer faces of C3 / C4 cortex whose nodes are the former disc attachment nodes
def bone_faces(prefix, attach):
    attach = set(attach); faces = {}
    for eb in geo.findall('Elements'):
        if not eb.get('name', '').startswith(prefix + '_cortical') or eb.get('name', '').endswith('_pot'): continue
        for e in eb:
            t = [int(v) for v in e.text.split(',')]
            for f in ((t[0], t[2], t[1]), (t[0], t[1], t[3]), (t[1], t[2], t[3]), (t[0], t[3], t[2])):
                key = tuple(sorted(f)); faces[key] = None if key in faces else f
    return [f for f in faces.values() if f is not None and set(f) <= attach]
if REFINED:                                         # refined endplate triangles (h16/h17, edges <= 0.5 mm)
    surf('C3_endplate', info['endplate_tris']['C3'], 'tri3'); surf('C4_endplate', info['endplate_tris']['C4'], 'tri3')
else:
    surf('C3_endplate', bone_faces('C3', ep.top_ids), 'tri3'); surf('C4_endplate', bone_faces('C4', ep.bot_ids), 'tri3')
# annulus remnant inner faces (all boundary quads of the remaining disc hexes not lying on a bony endplate)
qf = {}
for eb in geo.findall('Elements'):
    if not (eb.get('name', '').startswith('disc_or_facet') and eb.get('name') != 'disc_or_facet_mat5'): continue
    for e in eb:
        t = [int(v) for v in e.text.split(',')]
        for f in ([0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
            q = [t[i] for i in f]; key = tuple(sorted(q)); qf[key] = None if key in qf else q
bone_attach = set(ep.top_ids) | set(ep.bot_ids)
surf('annulus_rim', [q for q in qf.values() if q is not None and not set(q) <= bone_attach], 'quad4')
for name, a, b in (('cage_C3', 'cage_top', 'C3_endplate'), ('cage_C4', 'cage_bot', 'C4_endplate'), ('cage_rim', 'cage_wall', 'annulus_rim')):
    sp = ET.SubElement(geo, 'SurfacePair', name=name)
    ET.SubElement(sp, 'master', surface=b); ET.SubElement(sp, 'slave', surface=a)
ns_el = ET.SubElement(geo, 'NodeSet', name='cage_nodes'); ns_el.text = None
for i in cage_ids: ET.SubElement(ns_el, 'node', id=str(i))
for name, ids in (('orphans', orphans), ('cage_hold', hold), ('pin1', [pin1]), ('pin2', [pin2]), ('pin3', [pin3]),
                  ('push_post', cage_ids[cz['post']]), ('push_ant', cage_ids[cz['ant']])):
    s = ET.SubElement(geo, 'NodeSet', name=name)
    for i in ids: ET.SubElement(s, 'node', id=str(int(i)))
# Geometry section order as in Herron's files: Nodes, Elements, NodeSet, Surface, SurfacePair, DiscreteSet
order = {'Nodes': 0, 'Elements': 1, 'NodeSet': 2, 'Surface': 3, 'SurfacePair': 4, 'DiscreteSet': 5}
kids = sorted(list(geo), key=lambda c: order.get(c.tag, 9))
for c in list(geo): geo.remove(c)
for c in kids: geo.append(c)
# renumber all elements consecutively in final order
k = 1
for eb in geo.findall('Elements'):
    for e in eb: e.set('id', str(k)); k += 1

# ---------------------------------------------------------------- global BCs, load curves, output
for tag in ('Boundary', 'Control', 'Step'):
    for el in root.findall(tag): root.remove(el)
# root <Contact> is KEPT: it holds Herron's C3-C4 facet-joint contacts (active in every step)
# keep Herron's load curves (ligament force-elongation curves are referenced by the springs); ours are appended
LD = root.find('LoadData'); root.remove(LD); lc_base = max(int(c.get('id')) for c in LD)
bnd = ET.Element('Boundary')
rb = ET.SubElement(bnd, 'rigid_body', mat='1')
for dof in ('x', 'y', 'z', 'Rx', 'Ry', 'Rz'): ET.SubElement(rb, 'fixed', bc=dof)
if orphans: ET.SubElement(bnd, 'fix', bc='x,y,z', node_set='orphans')
root.insert(list(root).index(geo) + 1, bnd)
root.append(LD); lcs = {}
def lc(name, pts, kind='linear'):
    i = str(lc_base + len(lcs) + 1); lcs[name] = i
    c = ET.SubElement(LD, 'loadcurve', id=i, type=kind)
    for t, v in pts: ET.SubElement(c, 'point').text = f'{t:.6g},{v:.6g}'
    return i
d = prm['d']
lc('distract', [(0, 0), (1, 1), (100, 1)])
contact_xml = []
def contacts(parent, pen_lc=None, mu_lc=None):
    C = parent.find('Contact') if parent.find('Contact') is not None else ET.SubElement(parent, 'Contact')
    # no cage-wall / annulus-remnant contact: the centroid-based remnant overlaps the cage wall by up to ~0.5 mm, and a
    # stricter cut leaves disconnected annulus fragments; omitting it ignores the rim's resistance to lateral/posterior
    # cage motion (conservative for slip; the anterior side has no rim). Accepted by PI 2026-10-20 (Q39).
    for name, mu in (('cage_C3', prm['mu']), ('cage_C4', prm['mu'])):
        if CONTACT_TYPE == 'node':
            # sliding-node-on-facet: regularised Coulomb friction with its own tangential (stick) penalty 'fric_penalty'
            # -> smooth stick/slip transition (elastic micro-slip before sliding); used against stick-slip stalls (2026-10-21)
            c = ET.SubElement(C, 'contact', type='sliding-node-on-facet', name=f'{name}', surface_pair=name)
            items = (('laugon', 0), ('penalty', PENALTY), ('auto_penalty', 1), ('two_pass', 0), ('search_tol', 0.01),
                     ('search_radius', 1.0), ('fric_coeff', mu), ('fric_penalty', prm.get('fric_penalty', 10.0)), ('ktmult', 1), ('knmult', 1))
        else:
            c = ET.SubElement(C, 'contact', type='sliding-elastic', name=f'{name}', surface_pair=name)
            items = (('laugon', 0), ('penalty', PENALTY), ('auto_penalty', 1), ('two_pass', 0), ('search_tol', 0.01),
                     ('search_radius', 1.0), ('symmetric_stiffness', 0), ('tension', 0), ('fric_coeff', mu), ('knmult', 0))
        for k, v in items:
            e = ET.SubElement(c, k); e.text = str(v)
            if k == 'penalty' and pen_lc: e.set('lc', pen_lc)
            if k == 'fric_coeff' and mu_lc: e.set('lc', mu_lc)
def tied(parent):
    C = parent.find('Contact') if parent.find('Contact') is not None else ET.SubElement(parent, 'Contact')
    for name in ('cage_C3', 'cage_C4'):
        c = ET.SubElement(C, 'contact', type='tied-elastic', name=f'tie_{name}', surface_pair=name)
        # persistent tie formed at t = 2 (start of release) in the seated configuration (FEBio patch 3: 'init_time')
        for k, v in (('laugon', 0), ('penalty', PENALTY), ('auto_penalty', 1), ('two_pass', 0), ('search_tol', 0.01),
                     ('search_radius', 1.0), ('symmetric_stiffness', 0), ('knmult', 1), ('init_time', 2.0)):
            ET.SubElement(c, k).text = str(v)
def control(parent, steps, dt, dtmax, must=None):
    c = ET.SubElement(parent, 'Control')
    for k, v in (('time_steps', steps), ('step_size', dt), ('max_refs', 25), ('max_ups', 10), ('dtol', 0.001),
                 ('etol', 0.01), ('rtol', 0), ('lstol', 0.9), ('ls_check_jacobians', 1)):
        ET.SubElement(c, k).text = str(v)
    ts = ET.SubElement(c, 'time_stepper')
    for k, v in (('dtmin', dt / 100), ('dtmax', dtmax), ('max_retries', 10), ('opt_iter', 15)):
        ET.SubElement(ts, k).text = str(v)
    if must: ET.SubElement(ts, 'dtmax', lc=must).text = '1'
    ET.SubElement(c, 'analysis', type='static')
def rigid(parent, presc=(), fixed=(), force=()):
    r = ET.SubElement(parent.find('Boundary') if parent.find('Boundary') is not None else ET.SubElement(parent, 'Boundary'), 'rigid_body', mat='2')
    for dof, curve, val, *rel in presc:
        e = ET.SubElement(r, 'prescribed', bc=dof, lc=curve); e.text = f'{val:.6g}'
        if rel and rel[0]: e.set('type', 'relative')           # displacement relative to the state at step start
    for dof in fixed: ET.SubElement(r, 'fixed', bc=dof)
    for dof, curve, val in force: ET.SubElement(r, 'force', bc=dof, lc=curve).text = f'{val:.6g}'

# step 1: distract
if CONTACT_MODE == 'global':
    # one persistent cage-endplate contact for all steps (step-level contacts are re-created each step in FEBio, losing the
    # stick/slip state and causing a residual jump at every step start with stiff penalties). Penalty x lc: 0 while the cage
    # sits in the undistracted gap (distraction), log-like ramp during seating (press fit: the endplates separate by less than
    # d under the distraction force), full from t = 2. Friction 0 during seating (cage pinned in X-Y), mu from release on.
    lc('pen_ramp', [(0, 0), (1, 0), (1.001, 1e-3), (1.3, 1e-2), (1.6, 1e-1), (2, 1), (1e3, 1)])
    MU_RAMP = prm.get('mu_ramp', 0.3)               # friction switched on smoothly over the first part of release
    lc('mu_on', [(0, 0), (2, 0), (2 + MU_RAMP, 1), (1e3, 1)])
    if CONTACT_TYPE == 'tied':
        # screening option (2026-10-21): frictionless global contact carries the normal (compressive) load; the cage-endplate
        # interface is bonded tangentially from the start of release by per-step tied-elastic contacts (friction demand is
        # evaluated in post-processing instead of simulating stick/slip)
        prm['mu_true'] = prm['mu']; prm['mu'] = 0.0; contacts(root, lcs['pen_ramp'], None); tied(root)
    else:
        contacts(root, lcs['pen_ramp'], lcs['mu_on'])
s1 = ET.SubElement(root, 'Step', name='distract'); control(s1, 10, 0.1, 0.1)
rigid(s1, presc=[('z', lcs['distract'], d)], fixed=('x', 'y', 'Rx', 'Ry', 'Rz'))
ET.SubElement(s1.find('Boundary'), 'fix', bc='x,y,z', node_set='cage_nodes')
# step 2: insert + seat (t 1..2): cage pinned (statically determinate), contacts on, C3 pot lowered by SEAT mm
SEAT = prm.get('seat_mm', 0.02 if CONTACT_MODE == 'global' else 0.1)      # C3 lowering during seating; small (0.02) for stiff contact penalties
lc('seat', [(1, 0), (2, 1), (100, 1)])
s2 = ET.SubElement(root, 'Step', name='insert_seat'); control(s2, 10, 0.1, 0.1)
if CONTACT_MODE == 'per_step': contacts(s2)
b2 = ET.SubElement(s2, 'Boundary')
ET.SubElement(b2, 'fix', bc='x,y,z', node_set='pin1'); ET.SubElement(b2, 'fix', bc='y,z', node_set='pin2')
ET.SubElement(b2, 'fix', bc='z', node_set='pin3')
lc('seat_z', [(1, d), (2, d - SEAT), (100, d - SEAT)])
rigid(s2, presc=[('z', lcs['seat_z'], 1.0)], fixed=('x', 'y', 'Rx', 'Ry', 'Rz'))
# step 2b: release (t 2..3): cage z free, cage in-plane hold kept; all C3-pot reactions ramp to zero
# only Z is released: every test protocol keeps the C3 pot's X, Y and rotations prescribed/fixed, and releasing them makes
# the segment a mechanism before the cage carries load (zero shear stiffness)
s2b = ET.SubElement(root, 'Step', name='release'); control(s2b, 100, 0.01, 0.02)
if CONTACT_MODE == 'per_step': contacts(s2b)
b2b = ET.SubElement(s2b, 'Boundary'); ET.SubElement(b2b, 'fix', bc='x,y', node_set='cage_hold')
r2 = ET.SubElement(b2b, 'rigid_body', mat='2')
ET.SubElement(r2, 'force', bc='z', type='ramp').text = '0'
for dof in ('x', 'y', 'Rx', 'Ry', 'Rz'): ET.SubElement(r2, 'fixed', bc=dof)
# step 3: test (t 3..)
test = prm['test']; s3 = ET.SubElement(root, 'Step', name=test)
if CONTACT_MODE == 'per_step': contacts(s3)
ET.SubElement(s3, 'Boundary')
if test == 'compress':
    dz = prm.get('compress_mm', 3.0)
    lc('compress', [(3, 0), (4, 1)])
    control(s3, 200, 0.005, 0.01)
    rigid(s3, presc=[('z', lcs['compress'], -dz, True)], fixed=('x', 'y', 'Rx', 'Ry', 'Rz'))
elif test == 'iso':
    # ISO 18192-1 cervical: FE 7.5 sin, LB 6 cos, AR -4 cos (deg), axial 100 + 50 sin (N); levels x1.00..x3.00 step 0.25,
    # 3 cycles each; moving-frame Euler sequence LB (about X) -> FE (about Y) -> AR (about Z); C3 x, y translations fixed
    from scipy.spatial.transform import Rotation
    levels = np.arange(1.0, prm.get('iso_max_level', 3.0) + 1e-9, 0.25); ncyc = prm.get('iso_cycles', 3); npc = 24
    t, rx, ry, rz, fz = [3.0], [0.0], [0.0], [0.0], [0.0]
    T = 3.0
    for L in levels:
        for c in range(ncyc):
            for k in range(1, npc + 1):
                s = k / npc; T += 1.0 / npc
                fe, lb, ar = L * 7.5 * np.sin(2 * np.pi * s), L * 6 * np.cos(2 * np.pi * s), -L * 4 * np.cos(2 * np.pi * s)
                R = Rotation.from_euler('XYZ', [lb, fe, ar], degrees=True).as_rotvec()   # intrinsic: LB, then FE, then AR
                t.append(T); rx.append(R[0]); ry.append(R[1]); rz.append(R[2]); fz.append(-(100 + 50 * np.sin(2 * np.pi * s)))
    # the cycle starts at LB = 6, AR = -4 (cos = 1): reach that pose with a 1 s ramp before the cycles
    t = [3.0] + [4.0 + (x - 3.0) for x in t[1:]]
    R0 = Rotation.from_euler('XYZ', [6, 0, -4], degrees=True).as_rotvec()
    for name, arr, r0 in (('Rx', rx, R0[0]), ('Ry', ry, R0[1]), ('Rz', rz, R0[2])):
        pts = [(3.0, 0.0), (4.0, r0)] + list(zip(t[1:], arr[1:])); lc(name, pts)
    lc('Fz', [(3.0, 0.0), (4.0, -100.0)] + list(zip(t[1:], fz[1:])))
    control(s3, int((t[-1] - 3.0) * npc), 1.0 / npc, 1.0 / npc)
    rigid(s3, presc=[('Rx', lcs['Rx'], 1.0), ('Ry', lcs['Ry'], 1.0), ('Rz', lcs['Rz'], 1.0)], fixed=('x', 'y'),
          force=[('z', lcs['Fz'], 1.0)])
    json.dump(dict(levels=levels.tolist(), cycles=ncyc, points_per_cycle=npc, t_level_start=[4.0 + i * ncyc for i in range(len(levels))]),
              open(os.path.join(out, 'iso_schedule.json'), 'w'))
else:
    # push-out (ASTM draft F04.25.02.02 style): 100 N axial preload on C3 (z force), C3 other DOFs fixed; cage pushed
    # through its posterior (push_ant: towards anterior) or anterior (push_post: towards posterior) wall nodes, 3 mm
    lc('preload', [(3, 0), (3.2, 1), (100, 1)]); lc('push', [(3.2, 0), (4.2, 1)])
    control(s3, 120, 0.01, 0.01)
    rigid(s3, force=[('z', lcs['preload'], -100.0)], fixed=('x', 'y', 'Rx', 'Ry', 'Rz'))
    nset, sgn = ('push_post', 1.0) if test == 'push_ant' else ('push_ant', -1.0)
    p = ET.SubElement(s3.find('Boundary'), 'prescribe', bc='x', node_set=nset)          # FEBio 2.5 syntax
    ET.SubElement(p, 'scale', lc=lcs['push']).text = str(3.0 * sgn); ET.SubElement(p, 'relative').text = '1'

# output: plot file + log files used by post-processing
o = root.find('Output'); o.clear()
pf = ET.SubElement(o, 'plotfile', type='febio')
for v in ('displacement', 'stress', 'Lagrange strain', 'contact pressure', 'contact force', 'contact gap', 'contact traction', 'rigid force', 'rigid torque'):
    ET.SubElement(pf, 'var', type=v)
lf = ET.SubElement(o, 'logfile')
ET.SubElement(lf, 'rigid_body_data', data='x;y;z;thx;thy;thz;Fx;Fy;Fz;Mx;My;Mz', file='C3pot.txt', delim=',').text = '2'
ET.SubElement(lf, 'node_data', data='ux;uy;uz', file='cage_nodes.txt', delim=',').text = ','.join(
    str(cage_ids[i]) for i in np.unique(np.r_[cz['top'].ravel(), cz['bot'].ravel()])[::7])
ET.SubElement(lf, 'node_data', data='ux;uy;uz', file='C4_endplate_nodes.txt', delim=',').text = ','.join(map(str, ep.bot_ids))
ET.SubElement(lf, 'node_data', data='Rx;Ry;Rz', file='push_reaction.txt', delim=',').text = ','.join(
    str(cage_ids[i]) for i in (cz['post'] if test == 'push_ant' else cz['ant'] if test == 'push_post' else cz['post'][:5]))
ET.ElementTree(root).write(os.path.join(out, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
# cage element bookkeeping for post-processing: block name, npz element index, layer, column-centre XY, element top-face area
lay = cz['layer']; P8 = Q[H]
area = 0.5 * np.linalg.norm(np.cross(P8[:, 6] - P8[:, 4], P8[:, 7] - P8[:, 5]), axis=1)
np.savez_compressed(os.path.join(out, 'cage_elems.npz'), block=np.array([b for b, _ in cage_order]), npz_index=np.array([e for _, e in cage_order]),
                    layer=lay[[e for _, e in cage_order]], area=area[[e for _, e in cage_order]], K=int(cinfo['K_layers']))
json.dump(dict(params=prm, cage=cinfo, materials=mat_table, removed_disc_elements=removed, orphans=len(orphans),
               cage_node_id_offset=int(n0), release_hold_nodes=hold),
          open(os.path.join(out, 'case.json'), 'w'), indent=1)
print(json.dumps(dict(removed_disc_elements=removed, orphans=len(orphans), materials=len(mat_table)), indent=1))
