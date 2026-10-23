"""Preflight check: a case may only run when its model is built by the CURRENT code with the CURRENT study settings
(PI 2026-10-22: "check the model and run conditions before simulating, never find out half-way that it is the wrong version").

Checks for <case_dir> (inputs in <case_dir>_params.json, as written by h22 / the test builders):
  1. settings  - the params match human_study/current_settings.json ('common' + the class matching the case path)
  2. rebuild   - h14 run now on the same params gives a byte-identical case.feb (catches stale builds after any h14 change);
                 the cage mesh npz must be newer than h12
  3. structure - no biodisc elements when biodisc = False; seating pins are cage nodes, not biodisc (window filler) nodes (error in 'expand' mode, warning otherwise);
                 'expand': every cage material in a prestrain wrapper with F0_zz = 1/shrink, ramp 0 -> 1 -> 0 over t 0-1-2,
                 distraction pins instead of a fixed cage
  4. FEBio     - 'expand' needs patch 5 (volumetric prestrain): one-hex test must shrink to z 0.800 with x = y = 1.000
  5. restart   - a checkpoint (.dmp) in the case dir or a _gpu copy must come from this exact case.feb (sha recorded at
                 launch in launched_feb.sha256), else resuming would silently run the old model
Writes <case_dir>/preflight.json; valid() also requires unchanged case.feb / h12 / h14 / settings / FEBio library.
usage: python h24_preflight.py <case_dir> [...]     # check and print
       python h24_preflight.py --daemon             # every 2 min: check queued jobs; failures go to queue/failed/
"""
import os, sys, json, glob, time, hashlib, shutil, subprocess, tempfile, re
import numpy as np
import xml.etree.ElementTree as ET

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS = os.path.join(P, 'human_study/current_settings.json')
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py'); H12 = os.path.join(P, 'scripts/3_cage_case/h12_cage_mesh.py')
FEBIO = os.path.join(P, 'third_party/FEBio/cbuild/bin/febio4'); LIB = os.path.join(P, 'third_party/FEBio/cbuild/lib/libfebiomech.so')
Q = os.path.join(P, 'human_study/queue'); FAILED = os.path.join(Q, 'failed'); LOG = os.path.join(P, 'human_study/preflight.log')
CUBE_CACHE = os.path.join(P, 'human_study/.preflight_febio_cube.json')


_SHA = {}


def sha(path):
    st = os.stat(path); key = (path, st.st_mtime_ns, st.st_size)        # cached: the scheduler asks every minute
    if key in _SHA: return _SHA[key]
    _SHA[key] = _sha(path); return _SHA[key]


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def fingerprint(cd):
    return dict(feb=sha(os.path.join(cd, 'case.feb')), h14=sha(H14), h12=sha(H12), settings=sha(SETTINGS), lib=sha(LIB))


def log(msg):
    with open(LOG, 'a') as f: f.write(time.strftime('%m-%d %H:%M:%S ') + msg + '\n')


def cube_ok():
    """Patch-5 functional test of the installed FEBio (cached per library hash)."""
    lib = sha(LIB)
    try:
        c = json.load(open(CUBE_CACHE))
        if c['lib'] == lib: return c['ok'], c['msg']
    except (OSError, ValueError, KeyError):
        pass
    feb = '''<?xml version="1.0" encoding="ISO-8859-1"?><febio_spec version="2.5"><Module type="solid"/>
<Control><time_steps>10</time_steps><step_size>0.1</step_size><analysis type="static"/></Control>
<Material><material id="1" name="m" type="uncoupled prestrain elastic"><k>100</k><elastic type="Gent"><density>1</density>
<G>10</G><Jm>0.7</Jm></elastic><prestrain type="prestrain gradient"><ramp lc="1">1</ramp><F0>1,0,0,0,1,0,0,0,1.25</F0>
</prestrain></material></Material><Geometry><Nodes><node id="1">0,0,0</node><node id="2">1,0,0</node><node id="3">1,1,0</node>
<node id="4">0,1,0</node><node id="5">0,0,1</node><node id="6">1,0,1</node><node id="7">1,1,1</node><node id="8">0,1,1</node>
</Nodes><Elements type="hex8" mat="1" name="P"><elem id="1">1,2,3,4,5,6,7,8</elem></Elements><NodeSet name="a"><node id="1"/>
</NodeSet><NodeSet name="b"><node id="2"/></NodeSet><NodeSet name="c"><node id="4"/></NodeSet></Geometry><Boundary>
<fix bc="x,y,z" node_set="a"/><fix bc="y,z" node_set="b"/><fix bc="x,z" node_set="c"/></Boundary><LoadData>
<loadcurve id="1" type="linear"><point>0,0</point><point>1,1</point></loadcurve></LoadData><Output><logfile>
<node_data data="x;y;z" file="n.txt"/></logfile></Output></febio_spec>'''
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, 'c.feb'), 'w').write(feb)
        subprocess.run([FEBIO, '-i', 'c.feb', '-silent'], cwd=td, capture_output=True,
                       env=dict(os.environ, OMP_NUM_THREADS='1', LD_LIBRARY_PATH=os.path.join(P, 'third_party/mkl/lib')))
        try:
            last = [l for l in open(os.path.join(td, 'n.txt')) if l.startswith('7 ')][-1].split()
            x, y, z = map(float, last[1:4]); ok = abs(x - 1) < 1e-3 and abs(y - 1) < 1e-3 and abs(z - 0.8) < 1e-3
            msg = f'one-hex prestrain test x {x:.4f} y {y:.4f} z {z:.4f}'
        except (OSError, IndexError, ValueError):
            ok, msg = False, 'one-hex prestrain test did not run'
    json.dump(dict(lib=lib, ok=ok, msg=msg), open(CUBE_CACHE, 'w')); return ok, msg


def mesh_current(npz, prm):
    """Regenerate the cage mesh with the current h12 from the parameters stored in it and compare the arrays."""
    z = np.load(npz); info = json.loads(str(z['info']))
    args = [prm['fsu'], prm['frame'], info['design'], f"{info['d_mm']:.3f}", info['gradient'], info['fabrication']]
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'm.npz')
        extra = [str(info.get('H_mm', 0.2)), str(info.get('HZ_mm', info.get('H_mm', 0.2)))] + ([info['gaplib']] if info.get('gaplib') else [])
        r = subprocess.run(['python', H12] + args + [out] + extra, cwd=P, capture_output=True)
        if r.returncode: return False
        n = np.load(out)
        return all(np.array_equal(z[k], n[k], equal_nan=z[k].dtype.kind == 'f') for k in ('Q', 'hexes', 'region', 'phi', 'hard', 'top', 'bot'))


def check(cd):
    cd = os.path.normpath(cd); rel = os.path.relpath(os.path.abspath(cd), P)
    err, warn = [], []
    pj = cd + '_params.json'
    if not os.path.exists(pj): return dict(ok=False, errors=[f'no params file {os.path.relpath(pj, P)}'], warnings=[])
    prm = json.load(open(pj)); S = json.load(open(SETTINGS))
    want = dict(S['common'])
    for prefix, v in S['classes'].items():
        if rel.startswith(prefix): want.update(v)
    defaults = dict(insert_mode='overlap', biodisc=True, annulus_remnant=True)
    for k, v in want.items():
        got = prm.get(k, defaults.get(k))
        if got != v: err.append(f'setting {k} = {got!r}, current setting {v!r}')
    if 'cage_gaplib' in want and os.path.exists(os.path.join(P, prm['cage_npz'])):
        gl = json.loads(str(np.load(os.path.join(P, prm['cage_npz']))['info'])).get('gaplib')
        if gl != want['cage_gaplib']: err.append(f'cage mesh built with gaplib {gl!r}, current setting {want["cage_gaplib"]!r}')
    # 2. rebuild with current code
    npz = os.path.join(P, prm['cage_npz'])
    if not os.path.exists(npz): err.append('cage mesh missing')
    elif not mesh_current(npz, prm): err.append('cage mesh differs from a rebuild with the current h12 (rebuild the mesh)')
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(['python', H14, pj, td], cwd=P, capture_output=True, text=True)
        if r.returncode: err.append('h14 failed: ' + r.stderr.strip()[-300:])
        elif sha(os.path.join(td, 'case.feb')) != sha(os.path.join(cd, 'case.feb')):
            err.append('case.feb differs from a rebuild with the current h14 (stale build: rebuild the case)')
    # 3. structure
    root = ET.parse(os.path.join(cd, 'case.feb')).getroot(); geo = root.find('Geometry')
    nodeset = {ns.get('name'): [int(n.get('id')) for n in ns] for ns in geo.findall('NodeSet')}
    bio = set()
    for eb in geo.findall('Elements'):
        if eb.get('name', '').startswith('cage_biodisc'):
            for e in eb: bio |= set(int(v) for v in e.text.split(','))
    cage = set()
    for eb in geo.findall('Elements'):
        if eb.get('name', '').startswith('cage_') and not eb.get('name', '').startswith('cage_biodisc'):
            for e in eb: cage |= set(int(v) for v in e.text.split(','))
    for pn in ('pin1', 'pin2', 'pin3'):
        ids = nodeset.get(pn, [])
        if not ids or ids[0] not in cage:
            (err if prm.get('insert_mode') == 'expand' else warn).append(f'{pn} is not a cage node (biodisc / jelly pin)')
    if prm.get('biodisc', True) is False and any(eb.get('name', '').startswith('cage_biodisc') for eb in geo.findall('Elements')):
        err.append('biodisc elements present although biodisc = False')
    if prm.get('insert_mode') == 'expand':
        mats = root.find('Material')
        cm = [m for m in mats if (m.get('name') or '').startswith('cage_')]
        F0 = f'1,0,0,0,1,0,0,0,{1 / prm.get("shrink", 0.8):.6g}'
        for m in cm:
            ps = m.find('prestrain')
            if 'prestrain' not in m.get('type', '') or ps is None or ps.findtext('F0') != F0:
                err.append(f'material {m.get("name")} lacks the expected prestrain (F0 {F0})'); break
        lcid = cm[0].find('prestrain/ramp').get('lc') if cm and cm[0].find('prestrain/ramp') is not None else None
        curve = root.find(f".//loadcurve[@id='{lcid}']")
        pts = [tuple(map(float, p.text.split(','))) for p in curve] if curve is not None else []
        if pts[:3] != [(0, 0), (1, 1), (2, 0)]: err.append(f'shrink ramp curve {pts[:3]} != (0,0),(1,1),(2,0)')
        d1 = root.find("Step[@name='distract']/Boundary")
        if d1 is None or any(f.get('node_set') == 'cage_nodes' for f in d1.findall('fix')):
            err.append('distraction fixes the whole cage (must use the 3 pins so it can shrink)')
        ok, msg = cube_ok()
        if not ok: err.append('FEBio lacks patch 5: ' + msg)
    # 5. checkpoints
    feb_sha = sha(os.path.join(cd, 'case.feb'))
    for d in [cd] + sorted(g for g in glob.glob(cd + '_gpu*') if re.search(r'_gpu\d+$', g)):
        if not glob.glob(os.path.join(d, '*.dmp')): continue
        lf = os.path.join(d, 'launched_feb.sha256')
        if not os.path.exists(lf): warn.append(f'{os.path.basename(d)}: checkpoint of unknown build (pre-preflight run)')
        elif open(lf).read().strip() != feb_sha:
            err.append(f'{os.path.basename(d)}: checkpoint is from a different case.feb (delete it before resuming)')
    res = dict(ok=not err, errors=err, warnings=warn, checked=time.strftime('%Y-%m-%d %H:%M:%S'), fp=fingerprint(cd))
    json.dump(res, open(os.path.join(cd, 'preflight.json'), 'w'), indent=1)
    return res


def valid(cd):
    """True when a passing preflight.json exists and nothing it depends on has changed since."""
    try:
        r = json.load(open(os.path.join(cd, 'preflight.json')))
        return r['ok'] and r['fp'] == fingerprint(cd)
    except (OSError, ValueError, KeyError):
        return False


def daemon():
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(FAILED, exist_ok=True); log('preflight daemon start')
    while True:
        try:
            todo = []
            for j in sorted(glob.glob(os.path.join(Q, '*.job')), key=os.path.getmtime):
                cd = os.path.join(P, json.load(open(j))['case_dir'])
                if not valid(cd): todo.append((j, cd))
            with ThreadPoolExecutor(12) as ex:
                for (j, cd), r in zip(todo, ex.map(lambda t: check(t[1]), todo)):
                    name = os.path.basename(j)[:-4]
                    if r['ok']: log(f'{name}: OK' + (f" (warnings: {'; '.join(r['warnings'])})" if r['warnings'] else ''))
                    elif os.path.exists(j):
                        shutil.move(j, os.path.join(FAILED, name + '.job')); log(f"{name}: FAILED -> queue/failed: {'; '.join(r['errors'])}")
        except Exception:
            import traceback; log('ERROR ' + traceback.format_exc().replace('\n', ' | '))
        time.sleep(120)


if __name__ == '__main__':
    if sys.argv[1] == '--daemon': daemon()
    for cd in sys.argv[1:]:
        r = check(cd); print(os.path.relpath(os.path.abspath(cd), P), 'OK' if r['ok'] else 'FAIL', r['errors'], r['warnings'])
