"""State-validity scan of the friction windows that are verdict sources TODAY (2026-11-21; capability checks NUM-04 / NUM-14 FRIC).

h34_window_scan.py reads drive.txt and counts a state as 'dynamic residual' when the C3 rigid-body reaction moment exceeds 2 % of the
target - right for the joint-driven windows, wrong for route E (relative prescribed rotation: all three C3 rotations are prescribed,
the reaction moment IS the drive moment, so h34 flags every state). This scan asks the verdict code itself: for every window in
results/method/fric/verdicts.json (set / case_dir = the window the verdict was read from) e03.target_bracket returns the rows it
used and the rows it rejected (layer dt: step < 1e-4; jump: isolated moment spike; dyn: rigid-body moment residual, joint-driven
windows only; route E: none exists, the force residual is recorded). Reported per window: drive mode, rows, rejected rows by layer,
shortest valid step, largest force residual among the valid rows, whether a rejected row lies before the evaluation time.
usage: python h60_fric_winner_scan.py -> human_study/qa/fric_winner_scan.json
"""
import os, sys, json, time, collections
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); EV = os.path.normpath(os.path.join(P, '..', 'biocage-evo'))
sys.path[:0] = [os.path.join(EV, 'methods'), os.path.join(EV, 'common')]; import e03_mu_req as e3
R = os.path.join(P, 'human_study/al_v2'); v = json.load(open(os.path.join(EV, 'results/method/fric/verdicts.json'))); rows = []
for p, d in sorted(v.items()):
    if p.startswith('_'): continue
    for wn, x in (d.get('windows') or {}).items():
        if x.get('placeholder') or not x.get('set') or x.get('inherited_from'): continue
        cd = os.path.join(R, x['set'], x['case_dir'], 'w_' + wn); r = dict(design=p, window=wn, set=x['set'], case_dir=x['case_dir'], eval_point=x.get('eval_point'), usable=x.get('usable'))
        try:
            sch = json.load(open(os.path.join(cd, 'physio_schedule.json'))); b = e3.target_bracket(cd, sch)[wn]; c = b['check']; inv = b.get('invalid') or []
            lay = collections.Counter(i[3] for i in inv); t_ev = b['t'] if x.get('eval_point') == '1.5Nm' else None
            r.update(mode=e3.drive_mode(cd) or 'joint', n_rows=c['n_rows'], n_invalid=c['n_invalid'], invalid_by_layer=dict(lay), dt_min_valid=c['dt_min'], rb_fres_max_N=c.get('rb_fres_max'),
                     rb_res_max_Nmm=c.get('rb_res_max'), monotonic=c['monotonic'], complete=c['complete'], reached_1p5=b['reached'],
                     invalid_before_eval=sum(1 for i in inv if t_ev is not None and i[0] <= t_ev) if t_ev is not None else None)
        except Exception as ex: r['error'] = repr(ex)[:160]
        rows.append(r)
ok = [r for r in rows if 'error' not in r]; req = [r for r in ok if r['window'] in ('flexion', 'extension')]
S = lambda rs: dict(windows=len(rs), rows=sum(r['n_rows'] for r in rs), invalid_rows=sum(r['n_invalid'] for r in rs), windows_with_invalid=sum(1 for r in rs if r['n_invalid']),
                    by_layer=dict(sum((collections.Counter(r['invalid_by_layer']) for r in rs), collections.Counter())), by_mode=dict(collections.Counter(r['mode'] for r in rs)),
                    by_set=dict(collections.Counter(r['set'] for r in rs)), rb_fres_max_N=max((r['rb_fres_max_N'] or 0 for r in rs), default=None),
                    dt_min_valid=min((r['dt_min_valid'] for r in rs if r['dt_min_valid'] is not None), default=None))
out = dict(time=time.strftime('%Y-%m-%dT%H:%M'), rule='e03.target_bracket / filter_rows (the verdict code)', all_windows=S(ok), required_windows=S(req), errors=[r for r in rows if 'error' in r], windows=rows)
json.dump(out, open(os.path.join(P, 'human_study/qa/fric_winner_scan.json'), 'w'), indent=1)
print(json.dumps(dict(required=out['required_windows'], all=out['all_windows'], n_errors=len(out['errors'])), indent=1))
