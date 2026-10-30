"""Split a built physio_rot case into one insertion run + 6 independent window runs (PI 2026-10-31).

The sequential run loses every later window when one window fails, and the windows do not interact in the tied, elastic
screening model. Called by h14 when param physio_split is set. From <case>/case.feb (h14, test physio_rot) this writes
  <case>/case.feb            REPLACED by the insertion run: distraction, insertion, release, follower step only (run with
                               -dump=2: FEBio dumps the end state, t 3.5, to case.dmp; plot file with the step-end states only, copied
                               into each window dir before its restart); split.json lists the windows
  <case>/w_<name>/restart.feb  FEBio restart input (febio_restart 2.0): archive ../case.dmp + the one window step,
                               its rotation load curve moved to t 3.5 -> 4.0 -> 4.5
  <case>/w_<name>/case.feb   geometry / step copy for post-processing only (e03 / e04 read case.feb), physio_schedule.json
                               with the one window (joint id 1 in drive.txt), cage_elems.npz, case.json
usage: python h30_split_windows.py <case_dir>   (normally run by h14)
"""
import os, sys, json, copy, shutil, xml.etree.ElementTree as ET
cd = sys.argv[1]; T0 = 3.5
tree = ET.parse(os.path.join(cd, 'case.feb')); root = tree.getroot()
sch = json.load(open(os.path.join(cd, 'physio_schedule.json')))
steps = root.findall('Step'); win = {s.get('name')[len('physio_'):]: s for s in steps if s.get('name') in ['physio_' + w['name'] for w in sch['windows']]}
lcs = {lc.get('id'): lc for lc in root.find('LoadData')}
base = copy.deepcopy(root)
for s in base.findall('Step'):
    if s.get('name')[len('physio_'):] in win: base.remove(s)
    else:      # each window restart needs its own copy of the plot file (FEBio appends to it): keep only step-end states
        ET.SubElement(s.find('Control'), 'plot_level').text = 'PLOT_STEP_FINAL'
for w in sch['windows']:
    st = copy.deepcopy(win[w['name']]); wd = os.path.join(cd, 'w_' + w['name']); os.makedirs(wd, exist_ok=True)
    lid = st.find('Constraints/constraint').find('prescribe_' + w['dof']).get('lc')
    lc = copy.deepcopy(lcs[lid]); [lc.remove(p) for p in list(lc)]
    for t, v in ((T0, 0.0), (T0 + 0.5, 1.0), (T0 + 1.0, 0.0)): ET.SubElement(lc, 'point').text = f'{t},{v}'
    rs = ET.Element('febio_restart', version='2.0'); ET.SubElement(rs, 'Archive').text = '../case.dmp'
    ld = ET.SubElement(rs, 'LoadData'); ld.append(lc); rs.append(st)
    ET.ElementTree(rs).write(os.path.join(wd, 'restart.feb'), encoding='ISO-8859-1', xml_declaration=True)
    full = copy.deepcopy(base); full.append(copy.deepcopy(st))                     # post-processing copy (not run)
    fl = next(x for x in full.find('LoadData') if x.get('id') == lid); full.find('LoadData').remove(fl); full.find('LoadData').append(copy.deepcopy(lc))
    ET.ElementTree(full).write(os.path.join(wd, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
    s1 = dict(sch); s1['windows'] = [dict(w, t0=T0, t_peak=T0 + 0.5, t1=T0 + 1.0)]; s1['split'] = True
    json.dump(s1, open(os.path.join(wd, 'physio_schedule.json'), 'w'), indent=1)
    for f in ('cage_elems.npz', 'case.json'): shutil.copy(os.path.join(cd, f), os.path.join(wd, f))
ET.ElementTree(base).write(os.path.join(cd, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
json.dump(dict(windows=[w['name'] for w in sch['windows']]), open(os.path.join(cd, 'split.json'), 'w'))
