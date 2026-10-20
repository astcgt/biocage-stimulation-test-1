"""Render an FSU .feb (element blocks coloured by role) to PNG: sagittal and posterior-oblique views."""
import sys, xml.etree.ElementTree as ET, numpy as np, pyvista as pv
pv.OFF_SCREEN = True
r = ET.parse(sys.argv[1]).getroot(); g = r.find('Geometry')
X = {int(n.get('id')): [float(v) for v in n.text.split(',')] for n in g.find('Nodes')}
ids = sorted(X); idx = {i: k for k, i in enumerate(ids)}; P = np.array([X[i] for i in ids])
col = {'pot': '#7f7f7f', 'cortical': '#d9c7a3', 'trabecular': '#e8dcc0', 'mat8': '#e06666', 'mat5': '#6aa84f'}
def color(name):
    if name.endswith('_pot'): return col['pot']
    for k, c in col.items():
        if k in name: return c
    return '#6fa8dc'                                     # annulus
p = pv.Plotter(shape=(1, 2), window_size=(1800, 800))
for s, view in enumerate(['xz', 'iso']):
    p.subplot(0, s)
    for eb in g.findall('Elements'):
        E = np.array([[idx[int(v)] for v in e.text.split(',')] for e in eb])
        if len(E) == 0: continue
        ct = pv.CellType.TETRA if eb.get('type') == 'tet4' else pv.CellType.HEXAHEDRON
        grid = pv.UnstructuredGrid({ct: E}, P)
        clip = grid.clip(normal='y', origin=(0, 0, 0)) if view == 'xz' else grid
        p.add_mesh(clip.extract_surface(), color=color(eb.get('name')), show_edges=False, smooth_shading=False)
    if view == 'xz': p.view_xz()
    else: p.view_vector((-1, -1.2, 0.6)); 
    p.add_text(['mid-sagittal cut (grey = potted rigid)', 'posterior-oblique'][s], font_size=10)
p.screenshot(sys.argv[2])
