"""Split a built physio_rot case into one insertion run + 6 independent window runs (PI 2026-10-31).

The sequential run loses every later window when one window fails, and the windows do not interact in the tied, elastic
screening model. Called by h14 when param physio_split is set. From <case>/case.feb (h14, test physio_rot) this writes
  <case>/case.feb            REPLACED by the insertion run: distraction, insertion, release, follower step only (run with
                               -dump=2: FEBio dumps the end state, t 3.5, to case.dmp; plot file with the step-end states only, copied
                               into each window dir before its restart); split.json lists the windows
  <case>/w_<name>/restart.feb  FEBio restart input (febio_restart 2.0): archive ../case.dmp + the one window step
                               (run stops at the peak, t 4.0). Every window's rotation load curve is moved to t 3.5 -> 4.0 -> 4.5
                               in the insertion run itself, so the dump already holds it: a restart LoadData redefinition
                               addresses curves by load-controller index, not by file id, and left the rotation unapplied
                               in every window except flexion (whose curve already sat at 3.5-4.5; found 2026-10-31)
  <case>/w_<name>/case.feb   geometry / step copy for post-processing only (e03 / e04 read case.feb), physio_schedule.json
                               with the one window (joint id 1 in drive.txt), cage_elems.npz, case.json
usage: python h30_split_windows.py <case_dir>   (normally run by h14)
"""
import os, glob, sys, json, copy, shutil, xml.etree.ElementTree as ET
cd = sys.argv[1]; T0 = 3.5
tree = ET.parse(os.path.join(cd, 'case.feb')); root = tree.getroot()
sch = json.load(open(os.path.join(cd, 'physio_schedule.json')))
steps = root.findall('Step'); win = {s.get('name')[len('physio_'):]: s for s in steps if s.get('name') in ['physio_' + w['name'] for w in sch['windows']]}
lcs = {lc.get('id'): lc for lc in root.find('LoadData')}
HOLD = sch.get('physio_hold')
for w in sch['windows']:                 # all window rotation curves at 3.5-4.0-4.5, before the insertion run is written
    lid = win[w['name']].find('Constraints/constraint').find('prescribe_' + w['dof']).get('lc')
    lc = lcs[lid]; [lc.remove(p) for p in list(lc)]
    # 2026-11-05 pilot (V17, gpufe plan): physio_hold {ramp, frac, T} follows the production ramp rate to frac of the amplitude, then holds the angle for T
    for t, v in (((T0, 0.0), (T0 + HOLD['ramp'], HOLD['frac']), (T0 + HOLD['ramp'] + HOLD['T'], HOLD['frac'])) if HOLD else ((T0, 0.0), (T0 + 0.5, 1.0), (T0 + 1.0, 0.0))): ET.SubElement(lc, 'point').text = f'{t},{v}'
base = copy.deepcopy(root)
for s in base.findall('Step'):
    if s.get('name')[len('physio_'):] in win: base.remove(s)
    else:      # each window restart needs its own copy of the plot file (FEBio appends to it): keep only step-end states
        ET.SubElement(s.find('Control'), 'plot_level').text = 'PLOT_STEP_FINAL'
for w in sch['windows']:
    st = copy.deepcopy(win[w['name']]); wd = os.path.join(cd, 'w_' + w['name']); os.makedirs(wd, exist_ok=True)
    if sch.get('window_min_residual') is not None and st.find('Control/min_residual') is None:   # 2026-11-07 pilot (restart hold arms, h14 key window_min_residual): |R|^2 floor in the window Control only
        ET.SubElement(st.find('Control'), 'min_residual').text = str(sch['window_min_residual'])
    if sch.get('window_static') and st.find('Control/analysis') is not None:   # 2026-11-08 pilot (h14 key window_static): static window step, dynamics removed
        st.find('Control/analysis').set('type', 'static'); [st.find('Control').remove(x) for x in st.findall('Control/rhoi')]
    if sch.get('window_dt'):                        # 2026-11-08 pilot (h14 key window_dt): window step size / dtmax only (insertion deck unchanged) - half-step arms of the hold criterion
        dt = float(sch['window_dt']); st.find('Control/step_size').text = str(dt); st.find('Control/time_stepper/dtmax').text = str(dt); st.find('Control/time_stepper/dtmin').text = str(dt / 100)
    ts = st.find('Control/time_steps'); ts.text = str(int(round((HOLD['ramp'] + HOLD['T']) / float(st.find('Control/step_size').text))) if HOLD else int(ts.text) // 2)   # independent windows stop at the peak: no unload (near-zero-load tail fails the relative energy norm)
    if sch.get('window_dt0'):                       # 2026-11-11 pilot (h14 key window_dt0): small FIRST window increment only - the restart transient (the rigid-joint drive
        dt0 = float(sch['window_dt0']); dur = int(ts.text) * float(st.find('Control/step_size').text)   # switched on at t 3.5) failed all 10 retries (dt down to 0.05/11) for p050/p084/p109/p115/p127
        st.find('Control/step_size').text = str(dt0); ts.text = str(int(round(dur / dt0))); st.find('Control/time_stepper/dtmin').text = str(dt0 / 100)   # dtmax and the end time unchanged
    if sch.get('window_null'):                      # 2026-11-11 pilot (h14 key window_null): NULL restart - zero rotation drive (prescribed value 0, load curve kept), 0.2 s window,
        for pr in st.findall('Constraints/constraint/*'):   # follower load unchanged; restart file only (case.feb identical): does the restart itself diverge?
            if pr.tag.startswith('prescribe_'): pr.text = '0'
        ts.text = str(int(round(0.2 / float(st.find('Control/step_size').text))))
        if sch['window_null'] == 'nojoint':           # variant: the rigid-joint drive is not declared at all (follower load only) - is the joint activation the shock?
            [st.remove(c) for c in st.findall('Constraints')]
    rs = ET.Element('febio_restart', version='2.0'); ET.SubElement(rs, 'Archive').text = '../case.dmp'
    if sch.get('window_joint'):                     # 2026-11-11 pilot (h14 key window_joint {laugon, penalty[, tolerance]}): enforcement method of the rigid-joint drive in the restart step only
        wj = sch['window_joint']                      # (LAGMULT = laugon 2 is the production setting; the first-increment shock does not depend on the prescribed value, see DECISIONS 01:0x)
        for cst in st.findall('Constraints/constraint'):
            cst.find('laugon').text = str(wj['laugon'])
            for k in ('penalty', 'tolerance'):
                if k in wj:
                    el = cst.find(k) if cst.find(k) is not None else ET.SubElement(cst, k); el.text = str(wj[k])
        json.dump(dict(window_joint=wj), open(os.path.join(wd, 'window_joint.json'), 'w'), indent=1)
    if sch.get('window_lc_redefine'):               # 2026-11-11 diagnostic (h14 key window_lc_redefine {lc_id: [[t, v], ...]}): redefine load curves in the restart file only
        ld2 = rs.find('LoadData') if rs.find('LoadData') is not None else ET.Element('LoadData')
        if rs.find('LoadData') is None: rs.insert(1, ld2)
        for lid, pts in sch['window_lc_redefine'].items():
            new = ET.SubElement(ld2, 'loadcurve', id=str(lid), type='linear')
            for t, v in pts: ET.SubElement(new, 'point').text = f'{float(t)},{float(v)!r}'
    if sch.get('window_drive_mode') == 'rigid_relative':   # 2026-11-11 (DECISIONS 01:36 route E): the window drive is a RELATIVE prescribed rotation of the C3 pot rigid body
        # (FEBio 2.5 reader: <rigid_body><prescribed bc=.. lc=.. type="relative">, FERigidPrescribedBC m_ref = rotation at activation) instead of the generic rigid joint
        # (Lagrange multipliers, absolute angle from t=0 -> ill-conditioned first iteration + activation snap). Same load curve and amplitude (sign kept); no joint.
        bnd = st.find('Boundary') if st.find('Boundary') is not None else ET.SubElement(st, 'Boundary'); moved = []
        for cst in st.findall('Constraints/constraint'):
            for pr in list(cst):
                if pr.tag.startswith('prescribe_'):
                    rb = ET.SubElement(bnd, 'rigid_body', mat=cst.find('body_b').text); pd = ET.SubElement(rb, 'prescribed', bc=pr.tag[len('prescribe_'):], lc=pr.get('lc'), type='relative'); pd.text = pr.text
                    for other in ('Rx', 'Ry', 'Rz'):               # FEBio: 'Rigid body rotations cannot mix prescribed and free components' -> the two other rotations are fixed
                        if other != pr.tag[len('prescribe_'):]: ET.SubElement(rb, 'prescribed', bc=other, lc=pr.get('lc'), type='relative').text = '0'   # 'all or none rigid rotations must have the relative flag': relative 0 = held at the activation angle (the joint drive left them free; coupled rotations were 1e-5..1e-3 rad)
                    moved.append(dict(dof=pr.tag[len('prescribe_'):], lc=pr.get('lc'), value=pr.text, rigid_body_mat=cst.find('body_b').text))
        [st.remove(c) for c in st.findall('Constraints')]
        json.dump(dict(window_drive_mode='rigid_relative', prescribed=moved), open(os.path.join(wd, 'window_drive.json'), 'w'), indent=1)
    rs.append(st)
    if sch.get('window_drive_thy_rad') is not None:    # 2026-11-11 (DECISIONS 01:00, root cause of the window first-increment failures): the generic rigid joint measures the
        # relative rotation of C3 pot (body 2) vs C4 pot (body 1) from the t=0 orientations, so a drive starting at 0 snaps C3 back by the rotation it acquired during
        # insertion (C3pot.txt thy at t 3.5). The restart LoadData section redefines the drive curve (FERestartImport redefine flag): value*lc = thy + amp*ramp.
        # The value comes from the params (h47 build reads the source run's C3pot.txt; pilot key window_drive 'from_state'); case.feb is untouched, preflight rebuild reproduces it.
        thy = float(sch['window_drive_thy_rad']); ld = ET.Element('LoadData'); rs.insert(1, ld); done = []   # before the Step (normal FEBio section order: LoadData precedes Step)
        for pr in st.findall('Constraints/constraint/*'):
            if not pr.tag.startswith('prescribe_'): continue
            lid, amp = pr.get('lc'), float(pr.text); new = ET.SubElement(ld, 'loadcurve', id=lid, type=lcs[lid].get('type', 'linear'))
            for p in lcs[lid].findall('point'): t, v = p.text.split(','); ET.SubElement(new, 'point').text = f'{float(t)},{float(v) + thy / amp!r}'
            done.append(dict(dof=pr.tag, lc=lid, amp_rad=amp))
        json.dump(dict(window_drive='from_state', thy_rad=thy, redefined=done), open(os.path.join(wd, 'window_drive.json'), 'w'), indent=1)
    ET.ElementTree(rs).write(os.path.join(wd, 'restart.feb'), encoding='ISO-8859-1', xml_declaration=True)
    full = copy.deepcopy(base); full.append(copy.deepcopy(st))                     # post-processing copy (not run)
    ET.ElementTree(full).write(os.path.join(wd, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
    s1 = dict(sch); s1['windows'] = [dict(w, t0=T0, t_peak=T0 + (HOLD['ramp'] + HOLD['T'] if HOLD else 0.5), t1=T0 + (HOLD['ramp'] + HOLD['T'] if HOLD else 0.5))]; s1['split'] = True
    json.dump(s1, open(os.path.join(wd, 'physio_schedule.json'), 'w'), indent=1)
    for f in ('cage_elems.npz', 'case.json'): shutil.copy(os.path.join(cd, f), os.path.join(wd, f))
ET.ElementTree(base).write(os.path.join(cd, 'case.feb'), encoding='ISO-8859-1', xml_declaration=True)
json.dump(dict(windows=[w['name'] for w in sch['windows']]), open(os.path.join(cd, 'split.json'), 'w'))
