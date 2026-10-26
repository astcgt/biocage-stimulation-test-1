"""Reader for the FEBio 2.5 input files used in this study (h05 / h10 / h14 outputs).

Only the features these models use are read; anything else raises, so a silently ignored keyword cannot change a result.
Ids are converted to 0-based indices; element blocks keep their FEBio material id.
"""
import re, numpy as np, xml.etree.ElementTree as ET

SUPPORTED_MATS = {'rigid body', 'orthotropic elastic', 'neo-Hookean', 'solid mixture', 'uncoupled prestrain elastic', 'Gent',
                  'Holmes-Mow', 'fiber-exp-pow', 'Mooney-Rivlin'}


def _num(e, tag, default=None):
    c = e.find(tag)
    return default if c is None else float(c.text)


def _vec(txt): return np.array([float(v) for v in txt.split(',')])


class LoadCurve:
    """FEBio load curve: 'linear', 'step' or 'smooth' (cubic Hermite with finite-difference tangents, FEBio 'smooth');
    extend 'constant' (default) outside the points."""
    def __init__(self, el):
        self.type = el.get('type', 'linear'); self.extend = el.get('extend', 'constant')
        P = np.array([[float(v) for v in p.text.split(',')] for p in el.findall('point')])
        self.x, self.y = P[:, 0], P[:, 1]
        if self.extend not in ('constant', 'extrapolate'): raise NotImplementedError(f'load curve extend {self.extend}')

    def __call__(self, t):
        shape = np.shape(t); v = self._eval(np.atleast_1d(np.asarray(t, float)))
        return v.reshape(shape) if shape else float(v[0])

    def _eval(self, t):
        x, y = self.x, self.y
        if self.extend == 'extrapolate' and len(x) > 1:
            lo = y[0] + (t - x[0]) * (y[1] - y[0]) / (x[1] - x[0]); hi = y[-1] + (t - x[-1]) * (y[-1] - y[-2]) / (x[-1] - x[-2])
        else:
            lo, hi = np.full_like(t, y[0]), np.full_like(t, y[-1])
        if self.type == 'step':
            k = np.clip(np.searchsorted(x, t, side='right') - 1, 0, len(x) - 1); v = y[k]
        elif self.type == 'smooth' and len(x) > 2:
            v = _hermite(x, y, t)
        else:
            v = np.interp(t, x, y)
        return np.where(t < x[0], lo, np.where(t > x[-1], hi, v))

    def slope_max(self):
        return float(np.max(np.abs(np.diff(self.y) / np.maximum(np.diff(self.x), 1e-30))))


def _qerp(t, t0, f0, t1, f1, t2, f2):
    return (f0 * (t - t1) * (t - t2) / ((t0 - t1) * (t0 - t2)) + f1 * (t - t0) * (t - t2) / ((t1 - t0) * (t1 - t2))
            + f2 * (t - t0) * (t - t1) / ((t2 - t0) * (t2 - t1)))


def _hermite(x, y, t):
    """FEBio PointCurve SMOOTH (FECore/PointCurve.cpp): quadratic through 3 points at the ends, inside the linear blend of the
    two overlapping quadratics."""
    N = len(x)
    if N == 3: return _qerp(t, x[0], y[0], x[1], y[1], x[2], y[2])
    n = np.clip(np.searchsorted(x, t, side='right'), 1, N - 1)          # x[n-1] <= t < x[n]
    out = np.empty_like(t)
    a = n == 1; b = n == N - 1; c = ~(a | b)
    out[a] = _qerp(t[a], x[0], y[0], x[1], y[1], x[2], y[2])
    out[b] = _qerp(t[b], x[N - 3], y[N - 3], x[N - 2], y[N - 2], x[N - 1], y[N - 1])
    k = n[c]; tc = t[c]
    q1 = _qerp(tc, x[k - 2], y[k - 2], x[k - 1], y[k - 1], x[k], y[k])
    q2 = _qerp(tc, x[k - 1], y[k - 1], x[k], y[k], x[k + 1], y[k + 1])
    out[c] = q1 + (q2 - q1) * (tc - x[k - 1]) / (x[k] - x[k - 1])
    return out


def _material(m):
    d = dict(id=int(m.get('id')) if m.get('id') else None, name=m.get('name'), type=m.get('type'))
    if d['type'] not in SUPPORTED_MATS: raise NotImplementedError(f"material {d['type']}")
    ax = m.find('mat_axis')
    if ax is not None:
        if ax.get('type') == 'vector': d['axis'] = ('vector', _vec(ax.find('a').text), _vec(ax.find('d').text))
        elif ax.get('type') == 'local': d['axis'] = ('local', [int(v) for v in ax.text.split(',')])
        else: raise NotImplementedError(f"mat_axis {ax.get('type')}")
    t = d['type']
    if t == 'rigid body':
        c = m.find('center_of_mass'); d['com'] = _vec(c.text) if c is not None else None
    elif t == 'orthotropic elastic':
        for k in ('E1', 'E2', 'E3', 'G12', 'G23', 'G31', 'v12', 'v23', 'v31'): d[k] = _num(m, k)
    elif t == 'neo-Hookean':
        d['E'], d['v'] = _num(m, 'E'), _num(m, 'v')
    elif t == 'Mooney-Rivlin':
        d['c1'], d['c2'], d['k'] = _num(m, 'c1'), _num(m, 'c2', 0.0), _num(m, 'k')
    elif t == 'Holmes-Mow':
        d['E'], d['v'], d['beta'] = _num(m, 'E'), _num(m, 'v'), _num(m, 'beta')
    elif t == 'fiber-exp-pow':
        d['alpha'], d['beta'], d['ksi'] = _num(m, 'alpha'), _num(m, 'beta'), _num(m, 'ksi')
        f = m.find('fiber')
        src = f if f is not None else m
        d['theta'], d['phi'] = _num(src, 'theta', 0.0), _num(src, 'phi', 90.0)
        if f is not None and f.get('type') not in (None, 'angles'): raise NotImplementedError('fiber type')
    elif t == 'Gent':
        d['G'], d['Jm'], d['k'] = _num(m, 'G'), _num(m, 'Jm'), _num(m, 'k')
    elif t == 'solid mixture':
        d['solids'] = [_material(s) for s in m.findall('solid')]
    elif t == 'uncoupled prestrain elastic':
        d['elastic'] = _material(m.find('elastic'))
        p = m.find('prestrain')
        if p.get('type') != 'prestrain gradient': raise NotImplementedError(p.get('type'))
        r = p.find('ramp'); d['ramp'] = (int(r.get('lc')) if r.get('lc') else None, float(r.text))
        d['F0'] = _vec(p.find('F0').text).reshape(3, 3)
    return d


def _bc_list(el):
    """Boundary block -> list of dicts (node fixes, rigid fixes / prescribed / forces)."""
    out = []
    if el is None: return out
    for b in el:
        if b.tag == 'fix':
            out.append(dict(kind='fix', bc=b.get('bc').split(','), node_set=b.get('node_set')))
        elif b.tag == 'prescribe':
            sc = b.find('scale'); rel = b.find('relative')
            if b.get('node_set') is None or (rel is not None and rel.text.strip() not in ('0', 'false')): raise NotImplementedError('prescribe form')
            out.append(dict(kind='prescribe', bc=b.get('bc'), node_set=b.get('node_set'), lc=int(sc.get('lc')), scale=float(sc.text)))
        elif b.tag == 'rigid_body':
            mat = int(b.get('mat'))
            for c in b:
                if c.tag == 'fixed': out.append(dict(kind='rigid_fixed', mat=mat, bc=c.get('bc')))
                elif c.tag == 'prescribed': out.append(dict(kind='rigid_prescribed', mat=mat, bc=c.get('bc'), lc=int(c.get('lc')), scale=float(c.text)))
                elif c.tag == 'force':
                    out.append(dict(kind='rigid_force', mat=mat, bc=c.get('bc'), lc=int(c.get('lc')) if c.get('lc') else None,
                                    scale=float(c.text), ramp=c.get('type') == 'ramp'))
                else: raise NotImplementedError(f'rigid_body {c.tag}')
        else:
            raise NotImplementedError(f'boundary {b.tag}')
    return out


def _control(el):
    if el is None: return None
    ts = el.find('time_stepper')
    return dict(time_steps=int(el.find('time_steps').text), step_size=float(el.find('step_size').text),
                dtmax=_num(ts, 'dtmax') if ts is not None else None)


def _loads(el):
    out = []
    if el is None: return out
    for s in el:
        if s.tag == 'surface_load' and s.get('type') == 'pressure':
            p = s.find('pressure'); out.append(dict(kind='pressure', surface=s.get('surface'), lc=int(p.get('lc')), scale=float(p.text)))
        else:
            raise NotImplementedError(f'load {s.tag} {s.get("type")}')
    return out


def _contact(c):
    d = dict(type=c.get('type'), name=c.get('name'), pair=c.get('surface_pair'))
    for k in c:
        if k.tag == 'penalty': d['penalty'] = float(k.text); d['penalty_lc'] = int(k.get('lc')) if k.get('lc') else None
        else:
            try: d[k.tag] = float(k.text)
            except (TypeError, ValueError): d[k.tag] = k.text
    if d['type'] not in ('sliding-elastic', 'tied-elastic', 'sliding-tension-compression', 'sliding-node-on-facet'):
        raise NotImplementedError(d['type'])
    return d


def read(path):
    r = ET.parse(path).getroot()
    if r.get('version') != '2.5': raise NotImplementedError('febio_spec ' + str(r.get('version')))
    g = r.find('Geometry')
    ids, xyz = [], []
    for ns in g.findall('Nodes'):
        for n in ns: ids.append(int(n.get('id'))); xyz.append(_vec(n.text))
    ids = np.array(ids); order = np.argsort(ids); ids = ids[order]; X = np.array(xyz)[order]
    if not np.array_equal(ids, np.arange(1, len(ids) + 1)): raise ValueError('node ids must be 1..N')
    blocks = []
    for eb in g.findall('Elements'):
        conn = np.array([[int(v) for v in e.text.split(',')] for e in eb]) - 1
        eid = np.array([int(e.get('id')) for e in eb])
        blocks.append(dict(name=eb.get('name'), etype=eb.get('type'), mat=int(eb.get('mat')), conn=conn, eid=eid))
    nodesets, surfaces, pairs, dsets = {}, {}, {}, {}
    for e in g:
        if e.tag == 'NodeSet': nodesets[e.get('name')] = np.array([int(n.get('id')) for n in e]) - 1
        elif e.tag == 'Surface': surfaces[e.get('name')] = [np.array([int(v) for v in f.text.split(',')]) - 1 for f in e]
        elif e.tag == 'SurfacePair': pairs[e.get('name')] = (e.find('master').get('surface'), e.find('slave').get('surface'))
        elif e.tag == 'DiscreteSet': dsets[e.get('name')] = np.array([[int(v) for v in d.text.split(',')] for d in e]) - 1
    mats = {}
    for m in r.find('Material'):
        d = _material(m); mats[d['id']] = d
    lcs = {int(lc.get('id')): LoadCurve(lc) for lc in r.find('LoadData')} if r.find('LoadData') is not None else {}
    discrete = []
    D = r.find('Discrete')
    if D is not None:
        dm = {}
        for c in D:
            if c.tag == 'discrete_material':
                if c.get('type') != 'nonlinear spring': raise NotImplementedError(c.get('type'))
                f = c.find('force'); dm[int(c.get('id'))] = dict(name=c.get('name'), lc=int(f.get('lc')), scale=float(f.text))
            elif c.tag == 'discrete':
                discrete.append(dict(set=c.get('discrete_set'), **dm[int(c.get('dmat'))]))
    contacts = [_contact(c) for c in r.find('Contact')] if r.find('Contact') is not None else []
    steps = []
    if r.findall('Step'):
        for s in r.findall('Step'):
            steps.append(dict(name=s.get('name'), control=_control(s.find('Control')), bcs=_bc_list(s.find('Boundary')), loads=_loads(s.find('Loads'))))
    else:
        steps.append(dict(name='step', control=_control(r.find('Control')), bcs=[], loads=[]))
    out = r.find('Output'); logs = []
    if out is not None and out.find('logfile') is not None:
        for l in out.find('logfile'):
            logs.append(dict(kind=l.tag, data=l.get('data'), file=l.get('file'), ids=[int(v) for v in (l.text or '').replace(' ', '').split(',') if v]))
    return dict(path=path, X=X, blocks=blocks, nodesets=nodesets, surfaces=surfaces, pairs=pairs, discrete_sets=dsets, mats=mats,
                lcs=lcs, discrete=discrete, contacts=contacts, global_bcs=_bc_list(r.find('Boundary')), global_loads=_loads(r.find('Loads')),
                steps=steps, logs=logs)
