"""Push-out windows restarted from a production friction insertion checkpoint (PI 2026-11-19 test-gap plan item 3; S9 posterior
push-out >= 135 N, PI 2026-10-26; style of the ASTM draft F04.25.02.02 expulsion test, which pushes posterior -> anterior to 3 mm).

The deck is NOT changed: h47 build rebuilds case.feb with the route-E window keys (byte-identical to the source run, h24 preflight),
then this script adds two restart windows next to w_flexion / w_extension, written from w_flexion/restart.feb:
  w_push_post  cage driven POSTERIORLY (toward the cord): the anterior-wall node set 'push_ant' (h14) prescribed -X
  w_push_ant   cage driven ANTERIORLY (ASTM direction):   the posterior-wall node set 'push_post' prescribed +X
Window step (t 3.5 -> 4.0, Control copied from the production window): 100 N follower held (lc 21); C3 pot held in place
(x, y, Rx, Ry, Rz prescribed relative 0 - the vertebrae are the test blocks, the 100 N preload of the ASTM-style test is the
follower); push nodes moved relative to their position at activation by MM along X on lc 22 (0 at t 3.5 -> 1 at t 4.0; load
curves cannot be redefined in a restart file, DECISIONS 2026-11-11 pilot_relGlc). No new output can be declared in a restart,
so the push force is post-processed from the cage element stresses (biocage-evo methods/e09_pushout.py).
usage: python h53_push_restart.py build <case_dir> <source_run_dir> [mm=3.0]
       python h53_push_restart.py add2 <case_dir> [mm=3.0] [dt0=0.005] [maxups=0]   carried-push windows w_push_post2 / w_push_ant2 (both walls prescribed;
                                                             dt0 = small first increment, maxups 0 = full Newton: the retry variant for runs that fail in the first step)
       then: python h47_restart_pilot.py run <case_dir> <gpu> <cores> push_post   (and push_ant)
"""
import os, sys, json, copy, shutil, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h47_restart_pilot as h47
ROUTE_E = ['restart_env={"BIOCAGE_STICK_MEMORY": "1"}', 'window_drive_mode="rigid_relative"', 'window_min_residual=0.0001']   # = physio_fric5r keys


def add_windows(cd, mm, both=False, dt0=None, max_ups=None):
    src = os.path.join(cd, 'w_flexion'); base = ET.parse(os.path.join(src, 'restart.feb')).getroot()
    # 2026-11-21 'carried' push (windows *2): BOTH wall node sets get the same prescribed X displacement, so the cage is carried as
    # a whole instead of being pushed through one wall. Reason: in 14 of 39 one-wall runs the pushed wall moved 2-3x farther than
    # the rest of the cage (free-node mean 0.9 mm at 2.6 mm push: the soft layers of the wall were being crushed) and the run
    # stopped on inverted elements before the interface force levelled off. The force read-out is unchanged (cage equilibrium:
    # minus the summed contact force of both faces, e09), so the two variants measure the same interface resistance.
    for name, nset, sgn in ((('push_post2', 'push_ant+push_post', -1.0), ('push_ant2', 'push_post+push_ant', 1.0)) if both else (('push_post', 'push_ant', -1.0), ('push_ant', 'push_post', 1.0))):
        wd = os.path.join(cd, 'w_' + name); os.makedirs(wd, exist_ok=True)
        rs = copy.deepcopy(base); st = rs.find('Step'); st.set('name', 'pushout_' + name)
        bnd = st.find('Boundary'); [bnd.remove(c) for c in list(bnd)]
        rb = ET.SubElement(bnd, 'rigid_body', mat='2'); ET.SubElement(rb, 'force', bc='z', lc='21').text = '-100'
        rb2 = ET.SubElement(bnd, 'rigid_body', mat='2')
        for dof in ('x', 'y', 'Rx', 'Ry', 'Rz'): ET.SubElement(rb2, 'prescribed', bc=dof, lc='22', type='relative').text = '0'
        if dt0:                                      # 2026-11-21 retry variant: small FIRST increment (the 0.05 default moves the walls 0.3 mm in one step; 4 of the
            ctl = st.find('Control'); dur = int(ctl.find('time_steps').text) * float(ctl.find('step_size').text)   # first 8 carried runs inverted elements in that step, incl. p075 whose replicate p051 ran)
            ctl.find('step_size').text = str(dt0); ctl.find('time_steps').text = str(int(round(dur / dt0))); ctl.find('time_stepper/dtmin').text = str(dt0 / 100)   # dtmax unchanged: the stepper grows the step again
        if max_ups is not None: st.find('Control/max_ups').text = str(int(max_ups))   # 0 = full Newton
        for one in nset.split('+'):
            p = ET.SubElement(bnd, 'prescribe', bc='x', node_set=one)         # FEBio 2.5 syntax, as h14's push tests
            ET.SubElement(p, 'scale', lc='22').text = str(mm * sgn); ET.SubElement(p, 'relative').text = '1'
        ET.ElementTree(rs).write(os.path.join(wd, 'restart.feb'), encoding='ISO-8859-1', xml_declaration=True)
        for f in ('case.feb', 'cage_elems.npz', 'case.json', 'physio_schedule.json'): shutil.copy(os.path.join(src, f), os.path.join(wd, f))
        json.dump(dict(test='pushout', direction=name, pushed_node_set=nset, mm=mm * sgn, axis='frame X (anterior +)', t=[3.5, 4.0], lc=22,
                       c3='held (x y Rx Ry Rz relative 0), follower 100 N', note='post-processing geometry copy case.feb is the flexion window deck'),
                  open(os.path.join(wd, 'push.json'), 'w'), indent=1)
    print('push windows written', cd)


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        cd, src = sys.argv[2], sys.argv[3]; mm = float(sys.argv[4].split('=')[1]) if len(sys.argv) > 4 else 3.0
        h47.build(cd, src, ROUTE_E); add_windows(os.path.normpath(cd), mm)
    elif sys.argv[1] == 'add2':                      # carried-push windows added to an EXISTING pilot_push case (deck and preflight untouched)
        kw = dict(a.split('=') for a in sys.argv[3:]); add_windows(os.path.normpath(sys.argv[2]), float(kw.get('mm', 3.0)), both=True, dt0=float(kw['dt0']) if 'dt0' in kw else None, max_ups=int(kw['maxups']) if 'maxups' in kw else None)
    else: sys.exit(__doc__)
