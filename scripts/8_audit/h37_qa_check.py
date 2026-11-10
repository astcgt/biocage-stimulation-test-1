"""QA regression checks: does the platform still do what the decision log says it does? (PI 2026-11-04: a QA agent must check
periodically that the code matches the agreed method and the capability labels, so that drift does not produce wrong numbers.)

Layer A of human_study/qa/QA_SYSTEM.md: deterministic checks, each one born from a real error of 2026-10-31 .. 11-04. They
REPORT only; nothing here edits DECISIONS, labels or results. Layer B (judgement: does the code implement the meaning of a
decision?) is the qa-auditor agent, which fills human_study/qa/QA_SPEC.json; this script only tells when that audit is due.

usage: python scripts/8_audit/h37_qa_check.py            # full: all checks, writes human_study/qa/QA_STATUS.{json,md}, exit 1 on FAIL
       python scripts/8_audit/h37_qa_check.py --quick    # no rebuild / no face recount (seconds); same outputs
       python scripts/8_audit/h37_qa_check.py launch <case_dir> [...]   # launch gate for h24: pilot keys + material blocks of that case
       python scripts/8_audit/h37_qa_check.py --daemon [hours]          # full check every N h (default 6), log human_study/qa/qa.log (tmux biocage_qa)
"""
import os, sys, re, json, glob, csv, time, hashlib, subprocess, tempfile, collections
import xml.etree.ElementTree as ET
import numpy as np

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EV = os.path.normpath(os.path.join(P, '..', 'biocage-evo'))
QA = os.path.join(P, 'human_study/qa'); os.makedirs(QA, exist_ok=True)
SETTINGS = os.path.join(P, 'human_study/current_settings.json')
H14 = os.path.join(P, 'scripts/3_cage_case/h14_build_case.py')
GOLDEN = dict(params='human_study/al_v2/physio_fric3/p062_params.json', md5='4f3208b5e014c353f0f0e3683c1679ed',
              note='production p062 physio_fric3 case.feb, DECISIONS 2026-11-03 14:30 / 22:30')
# pilot-only options: never in a production class or case (DECISIONS 2026-11-03 22:30: all default off, production byte-identical)
PILOT_KEYS = ('dynamic_from_release', 'c3_release_ramp', 'sliding_off_after_tie', 'tied_init_converged', 'test_dynamic', 'only_distract', 'physio_hold', 'cage_laugon', 'cage_stick_memory', 'min_residual', 'window_static', 'window_dt', 'release_all_dofs', 'physio_static_until_windows', 'all_dynamic', 'follower_in_release', 'physio_dt0')   # QA audit 2026-11-10 不符 #6: the two fix-3 keys are pilot keys; the one production class that carries them (physio_fric3p, 11-03 fix 3, 12/12 failed) is allow-listed below
# 2026-11-09 (PI decision 1): restart_env + window_min_residual left the pilot list - they ARE the production friction law of physio_fric5 (R15 pins their values)
FRIC5 = dict(cls='human_study/al_v2/physio_fric5/', restart_env={'BIOCAGE_STICK_MEMORY': '1'}, window_min_residual=1e-4,
             lib_sha256='be7b357f71f155e462e1c3e3ca60d60b7bd9308d35d79b5cef5805ca149b2f89')   # patch 8 (FEBioXML rigid_moment load_type) lives in libfebioxml.so sha256 eb4b36e4b0610e092a05... (not in launch records; README item 8)   # validated cbuild_fric libfebiomech.so (patch 6 + 7 + 7b evidence line, built 2026-11-09 06:13)   # 'test' is the protocol name, not an option
REQ = ('flexion', 'extension')
FACES = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
R = []     # (check id, status PASS/FAIL/WARN/SKIP, message)


def rep(cid, ok, msg, warn=False): R.append((cid, 'PASS' if ok else ('WARN' if warn else 'FAIL'), msg))


def md5(path): return hashlib.md5(open(path, 'rb').read()).hexdigest()


def ended(log):
    if not os.path.exists(log): return None
    tail = open(log, errors='ignore').read()[-4000:]
    return 'NORMAL' if 'N O R M A L' in tail else ('ERROR' if 'E R R O R' in tail else None)


# PI 2026-11-10 (issue 2 option a): process G is the PRODUCTION insertion of the designs whose production insertion stopped - its options are
# allowed in exactly this class and its cases; everywhere else they stay pilot-only (DECISIONS 2026-11-10 14:xx)
PRODUCTION_OPTIONS = {'human_study/al_v2/physio_relG/': ('release_all_dofs', 'all_dynamic', 'min_residual', 'follower_in_release'),   # process G (PI 2026-11-10 option a)
                      'human_study/al_v2/physio_relG_pl/': ('release_all_dofs', 'all_dynamic', 'min_residual', 'follower_in_release'),   # its production-law fallback windows (same deck, restart_env 0; R17)
                      'human_study/al_v2/physio_fric3p/': ('follower_in_release', 'physio_dt0')}   # 2026-11-03 fix-3 set (production name, 12/12 failed, not in any verdict SETS); allow-listed, not renamed (run dirs, FILE_INDEX, NAS)
LAW_CLASSES = ('human_study/al_v2/physio_fric5/', 'human_study/al_v2/physio_relG/')
FALLBACK_CLASSES = {'human_study/al_v2/physio_relG_pl/': 'human_study/al_v2/physio_relG/'}   # fallback class -> its stick-law class: the same deck and checkpoint, production law (restart_env 0); a fallback SOURCE only (PI 2026-11-10 item 1 extended to process G, DECISIONS 2026-11-10 14:45; R17)   # the two production classes that carry the reference friction law (PI 2026-11-09 decision 1; PI 2026-11-10 option a); R15 / R16 pin their values
def pilot_keys_in(prm, allowed=()): return [k for k in PILOT_KEYS if prm.get(k) and k not in allowed]


# ---------------------------------------------------------------- R1 run dir resolved (error 2026-11-04: p110 build dir vs p110_gpu3)
def r1_case_dirs():
    rows = [r for r in json.load(open(os.path.join(EV, 'results/method/fric/compare.json'))) if 'note' not in r]
    bad, amb = [], []
    for r in rows:
        d = os.path.join(P, 'human_study/al_v2', r['set'], r['case_dir'], 'w_' + r['window'])
        if not (ended(d + '/case.log') and os.path.exists(d + '/case.xplt')): bad.append(f"{r['set']}/{r['case_dir']}/w_{r['window']}")
        sib = [s for s in glob.glob(os.path.join(P, 'human_study/al_v2', r['set'], r['design'] + '*')) if os.path.isdir(s) and ended(s + '/case.log')]
        if len(sib) > 1: amb.append(f"{r['set']}/{r['design']}: {len(sib)} run dirs with a log")
    rep('R1-case-dir', not bad, f'{len(rows)} friction rows; windows without finished log + xplt: {len(bad)} {bad[:5]}')
    rep('R1-ambiguous', not amb, f'designs with several run dirs in one set: {len(set(amb))} {sorted(set(amb))[:5]}', warn=True)


# ---------------------------------------------------------------- R2 no pass by absence (error 2026-11-04: p072 extension dropped)
def r2_no_pass_by_absence():
    v = json.load(open(os.path.join(EV, 'results/method/fric/verdicts.json')))
    bad = [p for p, d in v.items() if not p.startswith('_') and d.get('verdict') == 'pass' and not all(w in d.get('windows', {}) and d['windows'][w].get('usable') for w in REQ)]
    rep('R2-gate4', not bad, f'gate 4 passes without both usable windows: {bad}')
    e = json.load(open(os.path.join(EV, 'results/method/fric/e07_verdicts.json')))['designs']
    bad = [p for p, d in e.items() if d.get('verdict') == 'pass' and not all(w in d.get('windows', {}) for w in REQ)]
    rep('R2-shear', not bad, f'interface-shear passes without both windows: {bad}')
    m = json.load(open(os.path.join(EV, 'results/method/split/comp_by_design_merged.json')))
    bad = [p for p, d in m.items() if d.get('verdict') == 'pass' and any(g.get('verdict') not in ('pass',) for k, g in d.get('gates', {}).items() if g.get('verdict') not in ('excluded',) and k != 'dislocation_friction')]   # PI 2026-11-07: the friction dislocation record is a check, not a gate
    bad2 = [p for p, d in m.items() if d.get('verdict') == 'pass' and 'gates' not in d]
    rep('R2-merged', not (bad or bad2), f'merged passes with a non-pass gate: {bad}; without gate record: {bad2}')


# ---------------------------------------------------------------- R3 interface faces recount (error 2026-11-04: mesh flag used as material)
def recount_faces(cd):
    cj = json.load(open(os.path.join(cd, 'case.json'))); m = np.load(os.path.join(P, cj['params']['cage_npz']))
    ce = np.load(os.path.join(cd, 'cage_elems.npz'), allow_pickle=True); hexes = m['hexes']
    mat = {int(h): str(b) for h, b in zip(ce['npz_index'], ce['block'])}
    fmap = {}
    for h in ce['npz_index']:
        for f in FACES: fmap.setdefault(tuple(sorted(hexes[h][list(f)])), []).append(int(h))
    n = sum(1 for v in fmap.values() if len(v) == 2 and mat[v[0]] != mat[v[1]])
    return n, len(set(mat.values()))


def r3_faces(quick):
    files = sorted(glob.glob(os.path.join(EV, 'results/method/fric/e07/*.json')))
    if quick: rep('R3-faces', True, f'skipped (--quick); {len(files)} e07 window files', warn=True); return
    # 2026-11-09: e07 files of sets other than physio_fric3 carry the set as a prefix (<set>__<case_dir>__<window>); a bare
    # <case_dir>__<window> tag is a physio_fric3 window. Rows are keyed per set because fric3 and fric5 reuse the bare case names.
    rows = {}
    for r in json.load(open(os.path.join(EV, 'results/method/fric/compare.json'))):
        if 'note' not in r: rows[(r['set'], r['case_dir'], r['window'])] = r
    by_cw = {}
    for (s_, cd, wn), r in rows.items(): by_cw.setdefault((cd, wn), []).append(r)
    cache, bad, ins = {}, [], []
    for f in files:
        tag = os.path.basename(f)[:-5]; parts = tag.split('__')
        if len(parts) == 3: s_, cd, wn = parts; r = rows.get((s_, cd, wn))
        else:
            cd, wn = parts; cands = by_cw.get((cd, wn), []); r = next((x for x in cands if x['set'] == 'physio_fric3'), cands[0] if cands else None)
        if not r: continue
        j = json.load(open(f)); wd = os.path.join(P, 'human_study/al_v2', r['set'], cd, 'w_' + wn); ck = (r['set'], cd)
        if ck not in cache:
            try: cache[ck] = recount_faces(wd)
            except Exception as ex: cache[ck] = (None, str(ex))
        n, nb = cache[ck]
        if n is None or n != j.get('n_faces'): bad.append(f'{tag}: e07 {j.get("n_faces")} vs recount {n} ({nb} blocks)')
        if j.get('states'):
            t = np.array([s['time'] for s in j['states']]); dt = abs(t[np.argmin(abs(t - 3.5))] - 3.5)
            if dt > 0.05: ins.append(f'{tag}: nearest state to t 3.5 is {dt:.2f} away')
    rep('R3-faces', not bad, f'{len(files)} windows, {len(cache)} cases recounted; mismatches {len(bad)} {bad[:4]}')
    rep('R4-insertion-state', not ins, f'insertion value state within 0.05 of t 3.5; violations {len(ins)} {ins[:4]}')   # error 2026-11-04: t 0 used


# ---------------------------------------------------------------- R5 counts in documents vs merged result (error: 26/17/13/15 and 72/14 vs 73/15)
def r5_counts():
    C = json.load(open(os.path.join(EV, 'results/method/split/verdict_classes_merged.json')))['classes']
    m = json.load(open(os.path.join(EV, 'results/method/split/comp_by_design_merged.json')))
    tied = {p for p, d in m.items() if (d.get('gates') or {}).get('tied_screening', {}).get('verdict') == 'pass'}
    cls = {'friction-check-exceeded': '__friction_check_exceeded__', 'interface-shear': 'DESIGN/interface-shear-provisional',   # PI 2026-11-07: dislocation-friction class replaced by the check list
           'radial-mix': 'DESIGN/radial-mix-excluded', 'friction-computability': '[多元]/friction-computability'}
    CJ = json.load(open(os.path.join(EV, 'results/method/split/verdict_classes_merged.json'))); C['__friction_check_exceeded__'] = CJ.get('friction_check_exceeded', [])
    truth = {k: (len(C.get(v, [])), len(set(C.get(v, [])) & tied)) for k, v in cls.items()}
    docs = ['human_study/DECISIONS.md', 'human_study/CAPABILITY_SCORECARD.md', os.path.join(EV, 'docs/DECISIONS.md'), os.path.join(EV, 'docs/PLAN.md')]
    stale = []
    for doc in docs:
        path = doc if os.path.isabs(doc) else os.path.join(P, doc)
        if not os.path.exists(path): continue
        txt = open(path, errors='ignore').read()
        for k, (n_all, n_tied) in truth.items():
            hits = re.findall(k + r'(?:-provisional|-excluded)?\s+(\d+)\b', txt)
            if hits and int(hits[-1]) not in (n_all, n_tied): stale.append(f'{os.path.relpath(path, P)}: last "{k} {hits[-1]}" vs result {n_all} (tied passes {n_tied})')
    rep('R5-counts', not stale, f'classes {truth} (all / among tied passes); stale document counts: {stale}')
    return dict(classes=truth, tied_passes=len(tied), designs=len(m))


# ---------------------------------------------------------------- R6 retracted claims still in current documents
def r6_retracted():
    reg = json.load(open(os.path.join(QA, 'RETRACTED.json')))['items']
    docs = ['human_study/platform_capabilities.json', 'human_study/CAPABILITY_SCORECARD.md', 'human_study/PLATFORM_CAPABILITIES.md', os.path.join(EV, 'docs/PLAN.md')]
    hits = []
    for doc in docs:
        path = doc if os.path.isabs(doc) else os.path.join(P, doc)
        if not os.path.exists(path): continue
        txt = open(path, errors='ignore').read()
        for it in reg:
            for ph in it['phrases']:
                if ph in txt: hits.append(f'{os.path.relpath(path, P)}: "{ph}" ({it["id"]}, retracted {it["retracted_on"]})')
    rep('R6-retracted', not hits, f'{len(reg)} retracted claims checked in {len(docs)} current documents; hits: {hits}')


# ---------------------------------------------------------------- R7 pilot options never in production
def r7_pilot_keys(case_dirs=None):
    S = json.load(open(SETTINGS)); bad = []
    for cls, v in S['classes'].items():
        if 'pilot' not in cls and pilot_keys_in(v, PRODUCTION_OPTIONS.get(cls, ())): bad.append(f'class {cls}: {pilot_keys_in(v, PRODUCTION_OPTIONS.get(cls, ()))}')
    if any(S['common'].get(k) for k in PILOT_KEYS): bad.append('common: ' + str(pilot_keys_in(S['common'])))
    src = open(H14).read()
    for k in PILOT_KEYS:
        if k not in src: continue
        if re.search(r"prm\.get\('%s',\s*(?!None|False|0\b|''|\"\"|\[\]|\{\})" % k, src):
            bad.append(f'h14 reads {k} with a non-off default')
        for mm in re.finditer(r"prm\['%s'\]" % k, src):      # direct read must sit inside an 'if prm.get(k)' guard (same or earlier lines)
            if not re.search(r"if prm\.get\('%s'\)" % k, src[max(0, mm.start() - 2500):mm.start()]): bad.append(f'h14 reads {k} unguarded')
    cases = case_dirs or [d for s in ('physio_fric3', 'physio_fric5', 'physio_relG', 'physio_relG_pl', 'physio_rot', 'physio_rot_r2', 'physio_rot_dyn', 'physio_rot_split2', 'physio_rot_split3', 'physio_rot_split4')
                          for d in glob.glob(os.path.join(P, 'human_study/al_v2', s, 'p*')) if os.path.isdir(d) and os.path.exists(d + '/case.json')]
    leak = []; ref = {}
    for d in cases:
        rel = os.path.relpath(d, P); is_pilot = any(rel.startswith(c.rstrip('/')) and 'pilot' in c for c in S['classes'])
        try: prm = json.load(open(d + '/case.json')).get('params', {})
        except Exception: continue
        if is_pilot: continue                                   # pilot classes carry their options by design; h24 compares them with the class settings
        allowed = next((v for c, v in PRODUCTION_OPTIONS.items() if rel.startswith(c.rstrip('/'))), ())
        if pilot_keys_in(prm, allowed): leak.append(f'{rel}: {pilot_keys_in(prm, allowed)}')
        # all production cases of one set must share one key set (QA audit 2026-11-04: a fixed pilot-key list misses options)
        st = os.path.basename(os.path.dirname(d)); ks = frozenset(prm)
        if st not in ref: ref[st] = ks
        elif ks != ref[st]: leak.append(f'{rel}: key set differs from the first case of {st}: {sorted(ks ^ ref[st])}')
    rep('R7-pilot-keys', not (bad or leak), f'settings/h14: {bad}; production cases scanned {len(cases)}, with pilot options / extra keys: {leak[:5]}')


# ---------------------------------------------------------------- R11 constants defined in several files must agree (audit 2026-11-04: ROM rad in 3 places)
def r11_constants():
    files = ['scripts/3_cage_case/h14_build_case.py', 'scripts/6_active_learning/h28_physio_prerun.py', '../biocage-evo/ops/fric_compare.py']
    vals = {}
    for f in files:
        txt = open(os.path.normpath(os.path.join(P, f))).read()
        m = re.search(r'flexion=([0-9.]+),\s*extension=([0-9.]+),\s*LB_right=([0-9.]+),\s*LB_left=([0-9.]+),\s*AR_left=([0-9.]+),\s*AR_right=([0-9.]+)', txt)
        vals[f] = tuple(float(x) for x in m.groups()) if m else None
    distinct = {v for v in vals.values() if v}
    rep('R11-constants', len(distinct) == 1 and all(vals.values()), f'intact ROM constants: {vals}')


# ---------------------------------------------------------------- R14 patch-7 switches never in production (2026-11-08)
def r14_patch7_logs():
    """A production friction window must not have run with the env-switched friction treatments (BIOCAGE_STICK_MEMORY / BIOCAGE_CAGE_LAUGON,
    FEBio patch 7, cbuild_fric) and must not have dropped stiffness entries (FECore guard). Both write their own evidence lines."""
    hits = []
    for s in ('physio_fric3', 'physio_fric4', 'physio_rot', 'physio_rot_split2', 'physio_rot_split3', 'physio_rot_split4'):
        for lg in glob.glob(os.path.join(P, 'human_study/al_v2', s, 'p*_gpu*', 'w_*', 'case.log')) + glob.glob(os.path.join(P, 'human_study/al_v2', s, 'p*', 'case.log')):
            try: txt = open(lg, errors='ignore').read()
            except OSError: continue
            if 'BIOCAGE patch 7' in txt: hits.append(os.path.relpath(lg, P) + ': patch-7 switch')
            se = os.path.join(os.path.dirname(lg), 'stderr.log')
            if os.path.exists(se) and 'CRSSparseMatrix::add' in open(se, errors='ignore').read(): hits.append(os.path.relpath(se, P) + ': dropped stiffness entries')
    rep('R14-patch7-logs', not hits, f'production logs scanned for the patch-7 env switches and the FECore profile guard; hits: {hits[:10]}')

# ---------------------------------------------------------------- R12 file index: every repo path named in human_study/FILE_INDEX.md exists (PI 2026-11-05: files are scattered)
def r15_fric5():
    """physio_fric5 (PI 2026-11-09 decision 1): the settings class carries exactly the reference friction law (stick memory env + window
    residual floor 1e-4) and no superseded set carries it; every finished window log has the patch-7 evidence line with stick_memory = 1,
    no dropped stiffness entries (FECore guard, per-window stderr), and the launch record names the validated cbuild_fric library."""
    S = json.load(open(SETTINGS)); v = S['classes'].get(FRIC5['cls'], {}); bad = []
    if v.get('restart_env') != FRIC5['restart_env'] or v.get('window_min_residual') != FRIC5['window_min_residual']: bad.append(f"class {FRIC5['cls']}: restart_env {v.get('restart_env')}, window_min_residual {v.get('window_min_residual')}")
    for s3 in S['classes']:
        if s3 not in LAW_CLASSES and s3 not in FALLBACK_CLASSES and 'pilot' not in s3 and (S['classes'][s3].get('restart_env') or S['classes'][s3].get('window_min_residual')): bad.append(f'class {s3} carries restart_env / window_min_residual')
    for s3 in ('physio_fric3', 'physio_fric4'):
        for pj in glob.glob(os.path.join(P, 'human_study/al_v2', s3, 'p*_params.json')):
            prm = json.load(open(pj))
            if prm.get('restart_env') or prm.get('window_min_residual'): bad.append('law keys in a superseded set: ' + os.path.relpath(pj, P))
    n = 0
    for lg in sorted(glob.glob(os.path.join(P, FRIC5['cls'], 'p*', 'w_*', 'case.log'))):
        txt = open(lg, errors='ignore').read()
        if not any(k in txt[-4000:] for k in ('N O R M A L', 'E R R O R')): continue
        n += 1; rel = os.path.relpath(lg, P); wn = os.path.basename(os.path.dirname(lg))[2:]; cd = os.path.dirname(os.path.dirname(lg)); sfx = '' if wn == 'extension' else '_' + wn
        if not any('BIOCAGE patch 7' in l and 'stick_memory = 1' in l for l in txt.splitlines()): bad.append(rel + ': no stick-memory evidence line')
        se = os.path.join(cd, 'stderr' + sfx + '.log')
        if os.path.exists(se) and 'CRSSparseMatrix::add' in open(se, errors='ignore').read(): bad.append(rel + ': dropped stiffness entries')
        lj = os.path.join(cd, 'launch' + sfx + '.json'); h = json.load(open(lj)).get('lib_sha256') if os.path.exists(lj) else None
        if h != FRIC5['lib_sha256']: bad.append(f'{rel}: lib {str(h)[:8]} != validated {FRIC5["lib_sha256"][:8]}')
    rep('R15-fric5-law', not bad, f'physio_fric5 class pinned, superseded sets clean; {n} finished window logs checked; problems: {bad[:8]}')
    # physio_relG (PI 2026-11-10 option a): same law (restart_env + window_min_residual) in the class; h18/h31 runs have ONE launch.json (env + lib) per run dir
    v = S['classes'].get('human_study/al_v2/physio_relG/', {}); bad = []; n = 0
    if v and (v.get('restart_env') != FRIC5['restart_env'] or v.get('window_min_residual') != FRIC5['window_min_residual']): bad.append('class physio_relG: law keys differ from physio_fric5')
    for rd in sorted(glob.glob(os.path.join(P, 'human_study/al_v2/physio_relG', 'p*_gpu*'))):
        lg = os.path.join(rd, 'case.log')
        if not os.path.exists(lg): continue
        txt = open(lg, errors='ignore').read()
        if not any(k in txt[-4000:] for k in ('N O R M A L', 'E R R O R')): continue
        n += 1; rel = os.path.relpath(rd, P)
        if not any('BIOCAGE patch 7' in l and 'stick_memory = 1' in l for l in txt.splitlines()): bad.append(rel + ': insertion log without the stick-memory evidence line')
        for wl in glob.glob(os.path.join(rd, 'w_*', 'case.log')):
            wt = open(wl, errors='ignore').read()
            if any(k in wt[-4000:] for k in ('N O R M A L', 'E R R O R')) and not any('BIOCAGE patch 7' in l and 'stick_memory = 1' in l for l in wt.splitlines()): bad.append(os.path.relpath(wl, P) + ': no evidence line')
        lj = os.path.join(rd, 'launch.json'); j = json.load(open(lj)) if os.path.exists(lj) else {}
        if j.get('lib_sha256') != FRIC5['lib_sha256'] or (j.get('env') or {}).get('BIOCAGE_STICK_MEMORY') != '1': bad.append(f"{rel}: launch lib {str(j.get('lib_sha256'))[:8]} / env {(j.get('env') or {}).get('BIOCAGE_STICK_MEMORY')}")
        se = os.path.join(rd, 'stderr.log')
        if os.path.exists(se) and 'CRSSparseMatrix::add' in open(se, errors='ignore').read(): bad.append(rel + ': dropped stiffness entries')
    rep('R16-relG-law', not bad, f'physio_relG: class law = fric5 law; {n} finished run dirs checked (insertion + window evidence lines, launch env/lib, stderr); problems: {bad[:8]}')

def r12_file_index():
    idx = os.path.join(P, 'human_study/FILE_INDEX.md')
    if not os.path.exists(idx): rep('R12-file-index', False, 'human_study/FILE_INDEX.md missing'); return
    paths = re.findall(r'`([^`\n]+)`', open(idx).read()); missing = []
    for q in paths:
        if q.startswith('/') or ' ' in q or q.startswith('h') and q[1:3].isdigit() and ' ' in q: continue
        if not (q.startswith('human_study/') or q.startswith('scripts/') or q.startswith('../biocage-evo/') or q.startswith('.claude/') or q.startswith('febio')): continue
        full = os.path.normpath(os.path.join(P, q))
        if not (os.path.exists(full) or glob.glob(full)): missing.append(q)
    rep('R12-file-index', not missing, f'{len(paths)} paths in FILE_INDEX.md; missing {missing}')


# ---------------------------------------------------------------- R13 window amplitude = case params (launch; stale split build p139 2026-11-05)
def r13_window_amplitude(case_dirs):
    bad = []
    for d in case_dirs:
        base = re.sub(r'_gpu\d+$', '', d.rstrip('/')); pj = base + '_params.json'      # the launch truth is the params file (h28 / h22), not the
        if not os.path.exists(pj): bad.append(f'{os.path.relpath(d, P)}: no params file {os.path.basename(pj)} (amplitude unverifiable)'); continue   # 2026-11-05 S5: never a silent pass
        want = dict((json.load(open(pj)).get('physio_rot_rad') or {}))
        S = json.load(open(os.path.join(P, 'human_study/current_settings.json'))); rel = os.path.relpath(base, P) + '/'
        for prefix, v in S['classes'].items():
            if rel.startswith(prefix) and v.get('physio_rot_rad'): want.update(v['physio_rot_rad'])     # class setting wins
        if not want: continue
        for w in sorted(glob.glob(os.path.join(d, 'w_*'))):
            sf = os.path.join(w, 'physio_schedule.json')
            if not os.path.exists(sf): continue
            got = json.load(open(sf)).get('rot_rad') or {}
            for k, v in want.items():
                if k in got and abs(got[k] - v) > 1e-9: bad.append(f'{os.path.relpath(w, P)} {k} {got[k]} != params/settings {v}')
    rep('R13-window-amplitude', not bad, f'window schedules vs case params: {bad[:6]}')


# ---------------------------------------------------------------- R8 golden rebuild (h14 drift without a launch)
def r8_golden():
    pj = os.path.join(P, GOLDEN['params'])
    with tempfile.TemporaryDirectory() as td:
        t0 = time.time(); r = subprocess.run([sys.executable, H14, pj, td], cwd=P, capture_output=True, text=True)
        if r.returncode: rep('R8-golden-rebuild', False, 'h14 failed: ' + r.stderr.strip()[-300:]); return
        h = md5(os.path.join(td, 'case.feb'))
        rep('R8-golden-rebuild', h == GOLDEN['md5'], f'p062 physio_fric3 rebuild md5 {h[:8]} vs recorded {GOLDEN["md5"][:8]} ({time.time() - t0:.0f} s)')
        r9_blocks([td], label='golden rebuild')


# ---------------------------------------------------------------- R9 material map not homogenised (standing rule)
def r9_blocks(case_dirs, label='production'):
    bad, info = [], []
    for cd in case_dirs:
        try:
            ce = np.load(os.path.join(cd, 'cage_elems.npz'), allow_pickle=True); blocks = set(str(b) for b in ce['block'])
            names = [eb.get('name') for eb in ET.parse(os.path.join(cd, 'case.feb')).getroot().find('Geometry').findall('Elements')]
            cage = [n for n in names if n and n.startswith('cage_') and not n.startswith('cage_biodisc')]
            miss = blocks - set(names)
            if miss or len(cage) < len(blocks): bad.append(f'{os.path.basename(cd)}: npz blocks {sorted(blocks)} vs feb cage blocks {cage}')
            info.append(f'{os.path.basename(cd)}:{len(blocks)}')
        except Exception as ex: bad.append(f'{os.path.basename(cd)}: {ex}')
    rep('R9-material-blocks', not bad, f'{label}: one FEBio block per cage material in {len(case_dirs)} cases ({", ".join(info[:6])}); problems: {bad[:4]}')


def production_samples():
    """one axial mix, one radial mix, one interleave production case (by cage_elems block names)"""
    out = {}
    for d in sorted(glob.glob(os.path.join(P, 'human_study/al_v2/physio_fric3/p*'))):
        if not os.path.exists(d + '/cage_elems.npz'): continue
        try: cj = json.load(open(d + '/case.json')); cg = cj.get('cage') or {}; mm = re.search(r'cage_([A-Z])_(\w+?)_(\w+?)_d', cj['params'].get('cage_npz', ''))
        except Exception: continue
        key = (cg.get('gradient') or (mm and mm.group(2)), cg.get('fabrication') or (mm and mm.group(3)))
        out.setdefault(key, d)
        if len(out) >= 4: break
    return list(out.values())


# ---------------------------------------------------------------- R10 register and audit staleness
def r10_register():
    spec = json.load(open(os.path.join(QA, 'QA_SPEC.json'))); meta = spec['meta']; items = spec.get('items', [])
    last = meta.get('last_llm_audit')
    unmapped = [i['id'] for i in items if i.get('status') == 'unmapped']
    mismatch = [i['id'] for i in items if i.get('status') == '不符']
    stale_files = []
    if last:
        t_last = time.mktime(time.strptime(last[:16], '%Y-%m-%d %H:%M'))
        for f in meta.get('gate_files', []):
            path = os.path.normpath(os.path.join(P, f))
            if os.path.exists(path) and os.path.getmtime(path) > t_last: stale_files.append(f)
    # PI decision entries newer than the last audit
    txt = open(os.path.join(P, 'human_study/DECISIONS.md'), errors='ignore').read()
    heads = re.findall(r'^## (\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)[^\n]*(?:PI DECISION|PI decisions|decision)[^\n]*$', txt, flags=re.M | re.I)
    new_dec = [h for h in heads if not last or h > last[:len(h)]]
    hook = '--hook' in sys.argv            # 2026-11-05 pre-commit mode: register findings need a human (LLM audit); the hook enforces R1-R9, R11, R12
    rep('R10-register', not (unmapped or mismatch) or hook, f'{len(items)} register items; unmapped {unmapped}; 不符 {mismatch}' + (' (hook mode: reported, not blocking)' if hook and (unmapped or mismatch) else ''), warn=hook)
    due = (not last) or stale_files or new_dec
    rep('R10-llm-audit-due', not due, ('LLM audit required: ' if due else 'LLM audit current: ') + f'last {last}; gate files changed since: {stale_files}; decision entries since: {new_dec}', warn=True)
    return dict(last_llm_audit=last, n_items=len(items), unmapped=unmapped, mismatch=mismatch, gate_files_changed=stale_files, new_decisions=new_dec)


def write_status(extra):
    worst = 'FAIL' if any(s == 'FAIL' for _, s, _ in R) else ('WARN' if any(s == 'WARN' for _, s, _ in R) else 'PASS')
    st = dict(time=time.strftime('%Y-%m-%d %H:%M'), overall=worst, checks=[dict(id=c, status=s, message=m) for c, s, m in R], **extra)
    json.dump(st, open(os.path.join(QA, 'QA_STATUS.json'), 'w'), indent=1, ensure_ascii=False)
    with open(os.path.join(QA, 'QA_STATUS.md'), 'w') as f:
        f.write(f"# QA status {st['time']} — {worst}\n\nh37_qa_check.py (layer A, deterministic). PASS = check held; FAIL = drift found, fix before any number is reported; "
                f"WARN = information or an audit is due. Layer B (meaning of the decisions) = qa-auditor agent, register human_study/qa/QA_SPEC.json.\n\n| check | status | detail |\n|---|---|---|\n")
        for c, s, m in R: f.write(f'| {c} | {s} | {m.replace("|", "/")} |\n')
    return worst

# ---------------------------------------------------------------- R17 production-law fallback windows of the process-G set (PI 2026-11-10 item 1; DECISIONS 2026-11-10 14:45, 17:xx)
def r17_relG_fallback():
    """physio_relG_pl = physio_relG windows restarted from the SAME process-G t 3.5 checkpoint with the production friction law
    (BIOCAGE_STICK_MEMORY=0; h51 -> h47). Fallback SOURCE only. Checks: the class equals its stick-law class except restart_env 0; every case
    names a finished physio_relG source run, differs from it only in restart_env / restart_source and carries the same deck hash; every finished
    window logs 'stick_memory = 0' only, was launched with env 0 and the validated library and dropped no stiffness entries; in the verdicts a
    physio_relG_pl window appears only as a flagged fallback of an unusable physio_relG window that did not fold in the first increments."""
    S = json.load(open(SETTINGS)); bad = []; n = nw = nf = 0
    for fc, lc in FALLBACK_CLASSES.items():
        v = S['classes'].get(fc)
        if v is None: continue
        base = dict(S['classes'][lc], restart_env={'BIOCAGE_STICK_MEMORY': '0'})
        if v != base: bad.append(f'class {fc} != {lc} + restart_env 0: {sorted(k for k in set(v) | set(base) if v.get(k) != base.get(k))}')
        for pj in sorted(glob.glob(os.path.join(P, fc, 'p*_params.json'))):
            n += 1; prm = json.load(open(pj)); cd = pj[:-len('_params.json')]; rel = os.path.relpath(cd, P); src = prm.get('restart_source') or ''; sp = os.path.join(P, src)
            if not src.startswith(lc) or not os.path.exists(os.path.join(sp, 'resources.json')): bad.append(f'{rel}: restart_source {src!r} is not a finished {lc} run'); continue
            spj = os.path.join(P, lc, os.path.basename(cd) + '_params.json'); sprm = json.load(open(spj)) if os.path.exists(spj) else {}
            diff = sorted(k for k in set(prm) | set(sprm) if k not in ('restart_env', 'restart_source') and prm.get(k) != sprm.get(k))
            if diff or prm.get('restart_env') != {'BIOCAGE_STICK_MEMORY': '0'}: bad.append(f'{rel}: params differ from the source beyond restart_env 0: {diff}')
            a, b = os.path.join(cd, 'launched_feb.sha256'), os.path.join(sp, 'launched_feb.sha256')
            if not (os.path.exists(a) and os.path.exists(b) and open(a).read().split()[:1] == open(b).read().split()[:1]): bad.append(f'{rel}: deck hash differs from the source run')
            for wl in sorted(glob.glob(os.path.join(cd, 'w_*', 'case.log'))):
                wt = open(wl, errors='ignore').read()
                if not any(k in wt[-4000:] for k in ('N O R M A L', 'E R R O R')): continue
                nw += 1; wn = os.path.basename(os.path.dirname(wl))[2:]; sfx = '' if wn == 'extension' else '_' + wn; wrel = os.path.relpath(wl, P)
                ev = [l for l in wt.splitlines() if 'BIOCAGE patch 7' in l]
                if not ev or not all('stick_memory = 0' in l for l in ev): bad.append(wrel + ': evidence lines are not stick_memory = 0')
                lj = os.path.join(cd, 'launch' + sfx + '.json'); j = json.load(open(lj)) if os.path.exists(lj) else {}
                if j.get('lib_sha256') != FRIC5['lib_sha256'] or (j.get('env') or {}).get('BIOCAGE_STICK_MEMORY') != '0': bad.append(f"{wrel}: launch lib {str(j.get('lib_sha256'))[:8]} / env {(j.get('env') or {}).get('BIOCAGE_STICK_MEMORY')}")
                se = os.path.join(cd, 'stderr' + sfx + '.log')
                if os.path.exists(se) and 'CRSSparseMatrix::add' in open(se, errors='ignore').read(): bad.append(wrel + ': dropped stiffness entries')
    vj = os.path.join(EV, 'results/method/fric/verdicts.json')
    if os.path.exists(vj):
        for p, v in json.load(open(vj)).items():
            if p.startswith('_'): continue
            for w, x in (v.get('windows') or {}).items():
                if x.get('set') not in FALLBACK_CLASSES_SETS: continue
                nf += 1; fb = x.get('fallback') or {}; sup = fb.get('superseded') or {}
                if not fb or sup.get('set') != 'physio_relG' or x.get('window_law') != 'production (fallback)': bad.append(f'verdict {p} {w}: fallback-source window used without the fallback flag / provenance')
                if w in (v.get('soft_face_locking') or []) or (sup.get('t_last') is not None and sup['t_last'] < 3.52): bad.append(f'verdict {p} {w}: fallback applied to a window that folded in the first increments (t_last {sup.get("t_last")})')
    rep('R17-relG-fallback', not bad, f'{n} physio_relG_pl cases, {nw} finished windows checked; {nf} fallback windows in the verdicts; problems: {bad[:8]}')
FALLBACK_CLASSES_SETS = tuple(c.rstrip('/').split('/')[-1] for c in FALLBACK_CLASSES)   # 'physio_relG_pl'


if __name__ == '__main__':
    if '--daemon' in sys.argv:
        hours = float(sys.argv[sys.argv.index('--daemon') + 1]) if len(sys.argv) > sys.argv.index('--daemon') + 1 else 6.0
        while True:
            r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=P, capture_output=True, text=True)
            with open(os.path.join(QA, 'qa.log'), 'a') as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M')} {(r.stdout.strip().splitlines() or ['?'])[-1]}\n")
            time.sleep(hours * 3600)
    if len(sys.argv) > 1 and sys.argv[1] == 'launch':
        dirs = [os.path.abspath(d) for d in sys.argv[2:]]
        r7_pilot_keys(dirs); r9_blocks(dirs, label='launch'); r13_window_amplitude(dirs)
        for c, s, m in R: print(f'{s:4s} {c}: {m}')
        sys.exit(1 if any(s == 'FAIL' for _, s, _ in R) else 0)
    quick = '--quick' in sys.argv
    r1_case_dirs(); r2_no_pass_by_absence(); r3_faces(quick); counts = r5_counts(); r6_retracted(); r7_pilot_keys()
    if not quick: r8_golden()
    r9_blocks(production_samples()); r11_constants(); r12_file_index(); r14_patch7_logs(); r15_fric5(); r17_relG_fallback()
    reg = r10_register()
    worst = write_status(dict(counts=counts, register=reg, mode='quick' if quick else 'full'))
    for c, s, m in R: print(f'{s:4s} {c}: {m[:300]}')
    print('overall', worst, '-> human_study/qa/QA_STATUS.md')
    sys.exit(1 if worst == 'FAIL' else 0)
