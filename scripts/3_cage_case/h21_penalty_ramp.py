"""Ramp the cage-endplate contact penalty during the insert/seat step (t 1-2) of an h14 case, for stiff penalties.

Why: the cage is sized for the nominal distraction d, but the endplates separate by less than d under the ~1 kN distraction
force (bone compliance), so contact starts with interference (a physical press fit). A stiff penalty applied at once turns
that overlap into a huge force and inverts the 0.2 mm soft surface layer; ramping it lets the overlap become deformation.
The seat-step cage contacts are frictionless (cage pinned in X-Y; friction from release on) and get penalty x lc(t), lc: 1e-3 at t=1, 1e-2 at 1.3, 1e-1 at 1.6, 1 at t>=2 (log-like ramp).
usage: python h21_penalty_ramp.py <in.feb> <out.feb> [penalty] [seat_mm]
"""
import sys, xml.etree.ElementTree as ET
src, dst = sys.argv[1:3]; pen = sys.argv[3] if len(sys.argv) > 3 else None; seat = float(sys.argv[4]) if len(sys.argv) > 4 else None
t = ET.parse(src); r = t.getroot(); LD = r.find('LoadData')
lid = str(max(int(c.get('id')) for c in LD) + 1)
c = ET.SubElement(LD, 'loadcurve', id=lid, type='linear')
for tt, v in ((0, 1e-3), (1, 1e-3), (1.3, 1e-2), (1.6, 1e-1), (2, 1), (100, 1)): ET.SubElement(c, 'point').text = f'{tt},{v}'
seat_step = next(s for s in r.findall('Step') if s.get('name') == 'insert_seat')
n = 0
for s in r.findall('Step'):
    for ct in s.iter('contact'):
        if ct.get('name') not in ('cage_C3', 'cage_C4'): continue
        if pen is not None: ct.find('penalty').text = pen
        if s is seat_step:
            ct.find('penalty').set('lc', lid); n += 1
            ct.find('fric_coeff').text = '0'          # frictionless seating (cage pinned in X-Y; avoids stick-slip stall)
if seat is not None:                                   # C3 lowering during seating: the curve of the seat step's rigid z prescription
    zid = next(e.get('lc') for e in seat_step.iter('prescribed') if e.get('bc') == 'z')
    lc = next(c for c in LD if c.get('id') == zid); p = list(lc)
    d0 = float(p[0].text.split(',')[1]); p[1].text = f'2,{d0 - seat:g}'; p[2].text = f'100,{d0 - seat:g}'
t.write(dst, encoding='ISO-8859-1', xml_declaration=True)
print(f'{dst}: ramp lc {lid} on {n} seat contacts, penalty {pen}, seat {seat}')
