"""Weak-spot register of every stopped run (PI 2026-11-22: 「標籤明確詳細一點以供以後分析，並且位置也可以記錄，當作弱點」).

A run that FEBio stopped (E R R O R banner) is never a design verdict (usage limit R18). It is still information: WHERE the model
gave way first. For every stopped insertion run and window of the listed sets this script records
  what      the first inverted element of the log, the first inverted CAGE element and the first inverted BONE element
            (FEBio prints only the first failing block of an update and checks the bone blocks first, so the first printed element
            is often bone although the cage gave way in the same trial step - both are kept), the Jacobian value printed, the
            number of inversion lines per block, and the end type (inverted elements / watchdog stall / other)
  where     cage element: material phi, layer index of K (0 = C4-side face, K-1 = C3-side face), relative height, the face it
            is next to (C4 face / mid-height / C3 face), in-plane sector around the cage centre (anterior / posterior / left /
            right), reference coordinates in the segment frame (X anterior, Y left, Z superior);
            bone element: vertebra, tissue, and whether it sits under the cage footprint (<= 2.5 mm from a cage node), on the
            boundary of the rigid pot (shares a node with a *_pot element), or elsewhere
  when      set, design, insertion or window name, last converged time, converged steps, C3 rotation at the stop (windows)
  label     one explicit text label per stop, e.g. 「後伸 2.1° 停算｜先讓步：籠體軟相 phi 0｜貼 C3 面（第 22/24 層）｜後方」
The inverted elements belong to REJECTED trial iterations (no accepted state contains one; h61 shows the bone is nearly
undeformed in the last converged state), so 'bone' entries are numerical victims; the cage entries mark the weak spot.
usage: python h62_weak_spots.py [workers=3]  -> human_study/qa/weak_spots.json, human_study/WEAK_SPOTS.md
"""
import os, sys, re, json, glob, time, collections, numpy as np, xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); A = os.path.join(P, 'human_study/al_v2')
SETS = dict(tied=('physio_rot_split2', 'physio_rot_split3', 'physio_rot_split4'),
            friction=('physio_fric3', 'physio_fric5', 'physio_fric5r', 'physio_relG', 'physio_relGr', 'physio_relG_pl', 'pilot_mu03', 'pilot_mu03G', 'pilot_mu03r', 'pilot_mu03Gr', 'pilot_mu03rN', 'pilot_mu03GrN'),
            test=('pilot_push', 'pilot_pushG', 'pilot_cyc3v', 'pilot_cyc3vr', 'pilot_cyc3vG', 'pilot_cyc3vrN', 'pilot_cyc3vGN'))
WIN_ZH = dict(flexion='前屈', extension='後伸', LB_right='右側彎', LB_left='左側彎', AR_left='左軸轉', AR_right='右軸轉', push_post='往後推（單牆）', push_post2='往後推（整顆）', push_ant='往前推（單牆）')
INTACT = dict(flexion=0.1009, extension=0.1286, LB_right=0.0713, LB_left=0.0717, AR_left=0.0905, AR_right=0.0907)   # intact-segment rotation at 1.5 N m, rad (h14 TH)
SECT_ZH = dict(anterior='前方', posterior='後方', left='左側', right='右側')


def tail_banner(log):
    try:
        with open(log, 'rb') as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 4000)); t = f.read().decode(errors='ignore')
    except OSError: return None, ''
    return ('NORMAL' if 'N O R M A L' in t else ('ERROR' if 'E R R O R' in t else None)), t


def geometry(feb):
    g = ET.parse(feb).getroot().find('Geometry')
    X = {int(n.get('id')): np.array([float(v) for v in n.text.split(',')]) for n in g.find('Nodes')}
    rng, conn, cage_order, pot_nodes, cage_nodes = [], {}, [], set(), set()
    for eb in g.findall('Elements'):
        name = eb.get('name') or ''; first = last = None
        for e in eb:
            i = int(e.get('id')); first = i if first is None else first; last = i; nd = [int(v) for v in e.text.split(',')]; conn[i] = nd
            if name.endswith('_pot'): pot_nodes.update(nd)
            if name.startswith('cage_') and 'biodisc' not in name: cage_order.append(i); cage_nodes.update(nd)
        if first is not None: rng.append((first, last, name))
    return dict(X=X, rng=rng, conn=conn, cage_index={e: k for k, e in enumerate(cage_order)}, pot_nodes=pot_nodes,
                cage_xyz=np.array([X[i] for i in sorted(cage_nodes)]))


def locate(e, G, ce):
    blk = next((b for a, z, b in G['rng'] if a <= e <= z), 'unknown'); c = np.mean([G['X'][n] for n in G['conn'][e]], axis=0) if e in G['conn'] else None
    r = dict(element=e, block=blk, xyz_mm=[round(float(v), 2) for v in c] if c is not None else None)
    if blk.startswith('cage_') and e in G['cage_index'] and ce is not None:
        k = G['cage_index'][e]; K = int(ce['K']); lay = int(ce['layer'][k]); h = (lay + 0.5) / K; ctr = G['cage_xyz'].mean(0); d = c[:2] - ctr[:2]; ang = np.degrees(np.arctan2(d[1], d[0]))
        m = re.search(r'_(\d+(?:\.\d+)?)$', blk)
        r.update(group='cage', phi=float(m.group(1)) if m else None, layer=lay, K=K, rel_height=round(h, 3), layers_from_nearest_face=int(min(lay, K - 1 - lay)),
                 face='C4 face' if h < 1 / 3 else ('C3 face' if h > 2 / 3 else 'mid-height'),
                 sector='anterior' if -45 <= ang <= 45 else ('posterior' if abs(ang) >= 135 else ('left' if ang > 0 else 'right')), radius_mm=round(float(np.hypot(*d)), 2))
    elif 'cortical' in blk or 'trabecular' in blk:
        nd = G['conn'].get(e, []); dmin = float(np.min(np.linalg.norm(G['cage_xyz'] - c, axis=1))) if c is not None else None
        r.update(group='bone', vertebra=blk[:2], tissue='cortical' if 'cortical' in blk else 'trabecular',
                 place='rigid-pot boundary' if any(n in G['pot_nodes'] for n in nd) else ('under the cage footprint' if dmin is not None and dmin <= 2.5 else 'elsewhere'),
                 dist_to_cage_mm=round(dmin, 2) if dmin is not None else None)
    else: r['group'] = 'other'
    return r


def one(job):
    cls, set_, design, kind, log, feb, cef, c3 = job; rec = dict(config=cls, set=set_, design=design, kind=kind, log=os.path.relpath(log, P))
    try:
        txt = open(log, errors='ignore').read(); conv = re.findall(r'converged at time : ([0-9.eE+-]+)', txt)
        nj = [(int(e), float(j)) for e, j in re.findall(r'Negative jacobian was detected at element (\d+) at gauss point \d+\s*\*?\s*\n\s*\*?\s*jacobian = ([-0-9.eE+]+)', txt)]
        rec.update(t_last_converged=float(conv[-1]) if conv else None, n_converged=len(conv), n_inversion_lines=len(nj),
                   end='watchdog stall' if 'watchdog: stalled' in txt[-600:] else ('inverted elements' if nj else 'other'))
        if c3 and os.path.exists(c3):
            last = [l for l in open(c3, errors='ignore').read().splitlines() if l[:1].isdigit()]
            if last: v = [float(a) for a in last[-1].split(',')]; rec['rotation_at_stop_deg'] = round(float(np.degrees(np.linalg.norm(v[4:7]))), 2)
            wn_ = kind.split(':')[1] if ':' in kind else None
            if rec.get('rotation_at_stop_deg') is not None and wn_ in INTACT: rec['past_intact_rom'] = bool(rec['rotation_at_stop_deg'] >= np.degrees(INTACT[wn_]) - 0.05)   # the verdict read-out (intact ROM or 1.5 N m) lies before this stop
        if nj:
            G = geometry(feb); ce = np.load(cef, allow_pickle=True) if cef and os.path.exists(cef) else None
            blk = lambda e: next((b for a, z, b in G['rng'] if a <= e <= z), 'unknown')
            rec['inversion_lines_by_block'] = dict(collections.Counter(blk(e) for e, _ in nj))
            f0 = nj[0]; fc = next((x for x in nj if blk(x[0]).startswith('cage_')), None); fb = next((x for x in nj if 'cortical' in blk(x[0]) or 'trabecular' in blk(x[0])), None)
            rec['first_inverted'] = dict(locate(f0[0], G, ce), jacobian=f0[1])
            rec['first_cage_inverted'] = dict(locate(fc[0], G, ce), jacobian=fc[1]) if fc else None
            rec['first_bone_inverted'] = dict(locate(fb[0], G, ce), jacobian=fb[1]) if fb else None
            cg = [locate(e, G, ce) for e in list(dict.fromkeys(e for e, _ in nj if blk(e).startswith('cage_')))[:50]]   # the first 50 distinct cage elements = the cage weak zone
            if cg:
                rec['cage_weak_zone'] = dict(n=len(cg), face=dict(collections.Counter(x.get('face') for x in cg)), sector=dict(collections.Counter(x.get('sector') for x in cg)),
                                             phi=dict(collections.Counter(str(x.get('phi')) for x in cg)), layer_min=min(x['layer'] for x in cg), layer_max=max(x['layer'] for x in cg), K=cg[0]['K'])
                mf = max(rec['cage_weak_zone']['face'], key=rec['cage_weak_zone']['face'].get); ml = [x['layer'] for x in cg if x.get('face') == mf]
                rec['cage_weak_zone'].update(main_face=mf, main_face_share=round(len(ml) / len(cg), 2), main_face_layers=[min(ml), max(ml)],
                                             centroid_mm=[round(float(v), 2) for v in np.mean([x['xyz_mm'] for x in cg if x.get('face') == mf], axis=0)])
    except Exception as ex: rec['error'] = repr(ex)[:200]
    # explicit label
    w = kind.split(':')[1] if ':' in kind else None; head = (WIN_ZH.get(w, w) if w else '插入段')
    if rec.get('rotation_at_stop_deg') is not None and w in ('flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right'): head += f" {rec['rotation_at_stop_deg']:.1f}° 停算" + ('（已過正常活動範圍，判定讀值不受影響）' if rec.get('past_intact_rom') else '（在正常活動範圍之前）')
    else: head += f" t {rec.get('t_last_converged')} 停算"
    parts = [head]
    z, fcg, fbn = rec.get('cage_weak_zone'), rec.get('first_cage_inverted'), rec.get('first_bone_inverted')
    if rec.get('end') == 'watchdog stall': parts.append('看門狗判定停滯（無進度），非元素翻轉')
    elif fcg:
        face = max(z['face'], key=z['face'].get); sect = max(z['sector'], key=z['sector'].get); ph = max(z['phi'], key=z['phi'].get)
        mat = '軟相' if ph in ('0.0', '0') else ('硬相' if ph in ('1.0', '1') else '混合相')
        parts += [f"先讓步的籠體：{mat}（硬相比例 {ph}）", {'C3 face': '貼 C3 面', 'C4 face': '貼 C4 面', 'mid-height': '中段'}[face] + f"（第 {z['main_face_layers'][0]}–{z['main_face_layers'][1]} 層／共 {z['K']} 層，佔先翻轉籠體元素的 {z['main_face_share']:.0%}）", SECT_ZH.get(sect, sect)]
        if fbn: parts.append(f"同一批試探步波及骨頭：{fbn['vertebra']} {('皮質骨' if fbn['tissue'] == 'cortical' else '鬆質骨')}（{ {'rigid-pot boundary': '剛體灌注層交界', 'under the cage footprint': '籠體足跡下的終板', 'elsewhere': '其他位置'}[fbn['place']] }）")
    elif fbn: parts.append(f"紀錄只印出骨頭：{fbn['vertebra']} {('皮質骨' if fbn['tissue'] == 'cortical' else '鬆質骨')}（{ {'rigid-pot boundary': '剛體灌注層交界', 'under the cage footprint': '籠體足跡下的終板', 'elsewhere': '其他位置'}[fbn['place']] }）；籠體是否同時讓步未被印出")
    elif rec.get('end') == 'other': parts.append('無元素翻轉紀錄（收斂失敗）')
    rec['label'] = '｜'.join(parts); return rec


def jobs():
    out = []
    for cls, sets in SETS.items():
        for s in sets:
            for pj in sorted(glob.glob(os.path.join(A, s, 'p???_params.json'))):
                p = os.path.basename(pj)[:4]
                for rd in sorted(glob.glob(os.path.join(A, s, p + '_gpu*'))) + [os.path.join(A, s, p)]:
                    if not os.path.isdir(rd): continue
                    feb, cef = os.path.join(rd, 'case.feb'), os.path.join(rd, 'cage_elems.npz')
                    if not os.path.exists(feb): continue
                    lg = os.path.join(rd, 'case.log')
                    if os.path.exists(lg) and tail_banner(lg)[0] == 'ERROR': out.append((cls, s, p, 'insertion', lg, feb, cef, None))
                    for wd in sorted(glob.glob(os.path.join(rd, 'w_*'))):
                        wl = os.path.join(wd, 'case.log')
                        if os.path.exists(wl) and tail_banner(wl)[0] == 'ERROR': out.append((cls, s, p, 'window:' + os.path.basename(wd)[2:], wl, feb, cef, os.path.join(wd, 'C3pot.txt')))
    return out


if __name__ == '__main__':
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 3; J = jobs()
    with ProcessPoolExecutor(nw) as ex: R = list(ex.map(one, J, chunksize=2))
    def zone(r):
        z = r.get('cage_weak_zone')
        if r.get('end') == 'watchdog stall': return 'watchdog stall'
        if not z: return 'bone only printed' if r.get('first_bone_inverted') else ('no inversion' if not r.get('error') else 'error')
        ph = max(z['phi'], key=z['phi'].get); return f"cage {'soft' if ph in ('0.0', '0') else ('hard' if ph in ('1.0', '1') else 'mix ' + ph)} / {max(z['face'], key=z['face'].get)} / {max(z['sector'], key=z['sector'].get)}"
    for r in R: r['category'] = zone(r)
    by_design = collections.defaultdict(list)
    for r in R: by_design[r['design']].append(dict(config=r['config'], set=r['set'], kind=r['kind'], category=r['category'], label=r['label']))
    summ = dict(by_config=dict(collections.Counter(r['config'] for r in R)), stop_vs_intact_rom=dict(collections.Counter('after the intact ROM (read-out unaffected)' if r.get('past_intact_rom') else ('before the intact ROM' if 'past_intact_rom' in r else 'insertion / push / no rotation') for r in R)), by_category=dict(collections.Counter(r['category'] for r in R).most_common()),
                first_printed_group=dict(collections.Counter((r.get('first_inverted') or {}).get('group', 'none') for r in R)),
                bone_place=dict(collections.Counter((r.get('first_bone_inverted') or {}).get('place', 'none') for r in R)),
                cage_face=dict(collections.Counter(max(r['cage_weak_zone']['face'], key=r['cage_weak_zone']['face'].get) for r in R if r.get('cage_weak_zone'))),
                cage_sector=dict(collections.Counter(max(r['cage_weak_zone']['sector'], key=r['cage_weak_zone']['sector'].get) for r in R if r.get('cage_weak_zone'))),
                cage_phi=dict(collections.Counter(max(r['cage_weak_zone']['phi'], key=r['cage_weak_zone']['phi'].get) for r in R if r.get('cage_weak_zone'))))
    json.dump(dict(time=time.strftime('%Y-%m-%dT%H:%M'), rule='usage limit R18: a stopped run is never a design verdict; its weak spot is recorded here', sets=SETS, n_stopped=len(R), summary=summ,
                   by_design=by_design, records=R), open(os.path.join(P, 'human_study/qa/weak_spots.json'), 'w'), indent=1, ensure_ascii=False)
    L = ['# 弱點登記表（停算的運算在哪裡先讓步）', '', f"自動產生 {time.strftime('%Y-%m-%d %H:%M')}，`scripts/8_audit/h62_weak_spots.py`；完整欄位在 `human_study/qa/weak_spots.json`。",
         '停算的運算不當設計判定（使用限制 R18）。紀錄檔裡的元素翻轉都發生在被求解器退回的試探步，骨頭的翻轉是被波及；籠體先讓步的位置才是弱點。', '',
         f"共 {len(R)} 次停算：" + '、'.join(f'{k} {v}' for k, v in summ['by_config'].items()), '', '## 弱點類別（次數）', '', '| 類別（材料／貼哪一面／方位） | 次數 |', '|---|---|']
    L += [f'| {k} | {v} |' for k, v in summ['by_category'].items()]
    L += ['', '## 各設計', '', '| 設計 | 配置 | 集合 | 標籤 |', '|---|---|---|---|']
    for p in sorted(by_design):
        for x in by_design[p]: L.append(f"| {p} | {x['config']} | {x['set']} | {x['label']} |")
    open(os.path.join(P, 'human_study/WEAK_SPOTS.md'), 'w').write('\n'.join(L) + '\n')
    print(json.dumps(dict(n_stopped=len(R), **summ, errors=sum(1 for r in R if r.get('error'))), indent=1, ensure_ascii=False))
