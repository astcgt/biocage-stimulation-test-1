"""Integrity scan of finished split physio_rot batches, from logs only (no xplt): the retroactive window_check for runs made
before h31 wrote one (2026-11-02; checks NUM-04, NUM-06, OBS-05, DIV-04 of platform_capabilities.json).

Per window w_<name>: termination banner, drive.txt rows in the up-ramp, rows dropped as micro-steps (dt < DT_MIN) or moment jumps
(> JUMP_MAX x once |M| > JUMP_FLOOR x target; same rule as biocage-evo e03.target_bracket), whether the target moment was reached
with raw vs filtered rows (a difference = a verdict that rested on a spurious state), shortest step, negative-Jacobian lines and
the blocks (domains) they fall in.  Per insertion run that ended in ERROR: last converged time and the negative-Jacobian elements
per block (bone vs cage vs facet) - bone inversions are a solver-robustness defect of the platform ([數值] NUM-06), never a design
verdict.  Design distribution of the non-computable insertion runs vs all designs of the batch (family, gradient, fabrication, d,
E_soft tercile) for DIV-04.
usage: python scripts/8_audit/h34_window_scan.py [set ...]      default: physio_rot_split2 split3 split4 physio_fric physio_degr050/020/010
writes human_study/window_scan.json and human_study/WINDOW_SCAN_<date>.md
"""
import os, sys, re, json, glob, time
from collections import Counter, defaultdict

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AL = os.path.join(P, 'human_study/al_v2')
SETS = sys.argv[1:] or ['physio_rot_split2', 'physio_rot_split3', 'physio_rot_split4', 'physio_fric', 'physio_degr050', 'physio_degr020', 'physio_degr010']
COL = dict(Rx=4, Ry=5, Rz=6)
EVO = os.path.join(os.path.dirname(P), 'biocage-evo/methods')                 # same filter as the verdict code (e03.filter_rows)
sys.path.insert(0, EVO)
from e03_mu_req import filter_rows, rb_rows, dyn_residuals, DT_MIN, JUMP_REL, JUMP_ABS, DYN_M, DYN_F
WIN = ('flexion', 'extension', 'LB_right', 'LB_left', 'AR_left', 'AR_right')


def banner(log):
    if not os.path.exists(log): return None
    tail = open(log, errors='ignore').read()[-4000:]
    return 'NORMAL' if 'N O R M A L' in tail else ('ERROR' if 'E R R O R' in tail else 'RUNNING')


def block_ranges(feb_path):
    """element-id range per <Elements> block of case.feb (ids are contiguous within a block)."""
    rng = {}
    with open(feb_path, errors='ignore') as f: feb = f.read()
    for m in re.finditer(r'<Elements type="(\w+)" mat="(\d+)" name="([^"]+)">(.*?)</Elements>', feb, re.S):
        first = re.search(r'<elem id="(\d+)"', m.group(4)); last = None
        for last in re.finditer(r'<elem id="(\d+)"', m.group(4)[-400:]): pass
        if first: rng[m.group(3)] = (int(first.group(1)), int(last.group(1)) if last else int(first.group(1)))
    return rng


def negjac_blocks(log, rng):
    """negative-Jacobian element ids in a log -> {block: count of distinct elements}, plus the number of lines."""
    ids = re.findall(r'Negative jacobian was detected at element (\d+)', open(log, errors='ignore').read())
    c = Counter()
    for e in set(int(i) for i in ids):
        c[next((b for b, (a, z) in rng.items() if a <= e <= z), 'unknown')] += 1
    return dict(c), len(ids)


def window_rows(wd):
    sch = json.load(open(os.path.join(wd, 'physio_schedule.json'))); w = sch['windows'][0]; Mt = sch['target_moment_Nmm']
    rows, t = [], None
    for line in open(os.path.join(wd, 'drive.txt')):
        if line.startswith('*Time'): t = float(line.split('=')[1])
        elif line.startswith('1,') and t is not None and w['t0'] + 1e-9 < t <= w['t_peak'] + 1e-9: rows.append((t, float(line.split(',')[COL[w['dof']]])))
    dyn, fz = dyn_residuals(rb_rows(wd), [t for t, _ in rows])          # NUM-14: rigid-body dynamic residual (C3pot.txt)
    valid, inv = filter_rows(rows, w['t0'], Mt, dyn, abs(fz) if fz else None)
    return dict(n_rows=len(rows), n_dt=sum(i[3] == 'dt' for i in inv), n_jump=sum(i[3] in ('jump', 'sign') for i in inv),
                n_dyn=sum(i[3] == 'dyn' for i in inv), rb_res_max=max((dyn[v[0]][0] for v in valid if v[0] in dyn), default=None) if dyn else None,
                dt_min=min((v[1] for v in valid), default=None), t_last=valid[-1][0] if valid else None,
                raw_reached=any(abs(m) >= Mt for _, m in rows), reached=any(abs(v[2]) >= Mt for v in valid),
                M_max=max((abs(v[2]) for v in valid), default=None), complete=bool(valid) and valid[-1][0] >= w['t_peak'] - 1e-6,
                invalid=[[round(i[0], 6), i[1], i[2], i[3]] + i[4:] for i in inv])


def design_info(params):
    pr = json.load(open(params)); m = re.search(r'cage_([AB])_(\w+?)_(mix|interleave)_d(\d+\.\d+)', pr.get('cage_npz', ''))
    return dict(family=m.group(1) if m else '?', gradient=m.group(2) if m else '?', fab=m.group(3) if m else '?', d=float(m.group(4)) if m else None, E_soft=pr.get('E_soft'))


def scan():
    out = dict(sets={}, windows=[], failed_insertions=[], generated=time.strftime('%Y-%m-%d %H:%M'))
    for s in SETS:
        sd = os.path.join(AL, s)
        if not os.path.isdir(sd): continue
        designs = sorted(set(re.match(r'(p\d{3})', os.path.basename(d)).group(1) for d in glob.glob(sd + '/p???_params.json')))
        info = {p: design_info(os.path.join(sd, p + '_params.json')) for p in designs}
        ins_state = {}
        for p in designs:
            runs = [d for d in sorted(glob.glob(f'{sd}/{p}_gpu*') + [f'{sd}/{p}']) if os.path.exists(os.path.join(d, 'case.log'))]
            if not runs: ins_state[p] = 'never run'; continue
            rd = runs[0]; b = banner(os.path.join(rd, 'case.log')); ins_state[p] = b or 'no log'
            if b == 'ERROR':
                lg = open(os.path.join(rd, 'case.log'), errors='ignore').read()
                conv = [float(v) for v in re.findall(r'converged at time : ([0-9.eE+-]+)', lg)]
                nb, nl = negjac_blocks(os.path.join(rd, 'case.log'), block_ranges(os.path.join(rd, 'case.feb')))
                bone = sum(v for k, v in nb.items() if 'cortical' in k or 'trabecular' in k)
                out['failed_insertions'].append(dict(set=s, design=p, run=os.path.relpath(rd, P), t_last=max(conv) if conv else None,
                                                     negjac_elements_by_block=nb, negjac_lines=nl, bone_elements=bone, **info[p]))
            for wd in sorted(glob.glob(os.path.join(rd, 'w_*'))):
                wn = os.path.basename(wd)[2:]; wb = banner(os.path.join(wd, 'case.log'))
                if wb is None or not os.path.exists(os.path.join(wd, 'drive.txt')):
                    out['windows'].append(dict(set=s, design=p, window=wn, banner=wb, n_rows=0)); continue
                r = window_rows(wd)
                nb, nl = negjac_blocks(os.path.join(wd, 'case.log'), block_ranges(os.path.join(rd, 'case.feb'))) if nl_hint(wd) else ({}, 0)
                out['windows'].append(dict(set=s, design=p, window=wn, banner=wb, static_retry=os.path.exists(os.path.join(wd, 'case_dyn_fail.log')),
                                           negjac_elements_by_block=nb, negjac_lines=nl, **r))
        # DIV-04: distribution of the non-computable designs vs all designs of the set
        fails = [f['design'] for f in out['failed_insertions'] if f['set'] == s]
        dist = {}
        for key in ('family', 'gradient', 'fab', 'd'):
            allc = Counter(str(info[p][key]) for p in designs); fc = Counter(str(info[p][key]) for p in fails)
            dist[key] = {k: dict(n=allc[k], failed=fc.get(k, 0), rate=round(fc.get(k, 0) / allc[k], 3)) for k in sorted(allc)}
        es = sorted(info[p]['E_soft'] for p in designs if info[p]['E_soft'] is not None)
        if es:
            cuts = (es[len(es) // 3], es[2 * len(es) // 3]); terc = lambda e: 'low' if e < cuts[0] else ('mid' if e < cuts[1] else 'high')
            allc = Counter(terc(info[p]['E_soft']) for p in designs if info[p]['E_soft'] is not None); fc = Counter(terc(info[p]['E_soft']) for p in fails)
            dist['E_soft_tercile'] = {k: dict(n=allc[k], failed=fc.get(k, 0), rate=round(fc.get(k, 0) / allc[k], 3), range=f'{"<" if k == "low" else ">=" } {cuts[0 if k != "high" else 1]:.2f} MPa') for k in ('low', 'mid', 'high') if k in allc}
        out['sets'][s] = dict(designs=len(designs), insertion=dict(Counter(ins_state.values())), failed=fails, distribution=dist,
                              overall_fail_rate=round(len(fails) / len(designs), 3) if designs else None)
    return out


def nl_hint(wd):
    """cheap pre-check so block_ranges (14 MB regex) runs only for logs that mention negative Jacobians."""
    return 'Negative jacobian' in open(os.path.join(wd, 'case.log'), errors='ignore').read()


def report(out):
    W = out['windows']; L = [f"# 視窗完整性掃描（{out['generated']}）", '', f"集合：{', '.join(SETS)}；視窗 {len(W)}；插入失敗 {len(out['failed_insertions'])}。", '',
         '## 1. [數值] NUM-04 微步與跳變（慢速動態的偽力矩）', '']
    micro = [w for w in W if w.get('n_dt')]; jump = [w for w in W if w.get('n_jump')]; dyn = [w for w in W if w.get('n_dyn')]
    flip = [w for w in W if w.get('raw_reached') and not w.get('reached')]
    n_dyn = sum(w.get('n_dyn', 0) for w in W); n_rows = sum(w.get('n_rows', 0) for w in W)
    L += [f"- 有微步（dt < {DT_MIN}）的視窗：{len(micro)} / {len(W)}", f"- 有孤立尖峰（偏離鄰點預測 > max({JUMP_ABS}×目標, {JUMP_REL}×預測)）的視窗：{len(jump)}",
          f"- 有剛體動態殘差狀態（C3pot.txt |M_rb| > {DYN_M:.0%} 目標；NUM-14）的視窗：{len(dyn)}；狀態 {n_dyn} / {n_rows}（重試步、接觸顫動、視窗起步暫態；力殘差只記錄不判定）",
          f"- **原本判「達標」、濾除後變「未達標」的視窗：{len(flip)}**（這些判定曾依賴垃圾狀態）", '']
    for w in flip: L.append(f"  - {w['set']}/{w['design']}/{w['window']}：無效狀態 {w['invalid']}；最大有效 |M| {w['M_max']:.0f} N·mm")
    for w in micro + jump + [w for w in dyn if w not in micro and w not in jump]:
        if w not in flip and any(i[3] != 'dyn' or abs(i[2]) >= 0.5 * 1500 for i in w['invalid']):   # dyn drops far below the target are noise, not listed
            L.append(f"  - （不影響判定）{w['set']}/{w['design']}/{w['window']}：{w['invalid']}")
    dts = sorted(w['dt_min'] for w in W if w.get('dt_min') is not None)
    if dts: L += ['', f"- 有效步長最小值分布：min {dts[0]:.4g}，中位數 {dts[len(dts) // 2]:.4g}，< 0.01 的視窗 {sum(d < 0.01 for d in dts)}"]
    L += ['', '## 2. [數值] NUM-06 元素翻轉落在哪個區塊', '', '### 2.1 插入 run 失敗（ERROR）', '', '| 集合 | 設計 | 停在 t | 骨元素 | 各區塊（相異元素數） | 家族/梯度/製法/d/E_soft |', '|---|---|---|---|---|---|']
    for f in out['failed_insertions']:
        L.append(f"| {f['set']} | {f['design']} | {f['t_last']} | **{f['bone_elements']}** | {', '.join(f'{k} {v}' for k, v in sorted(f['negjac_elements_by_block'].items(), key=lambda x: -x[1]))} | {f['family']}/{f['gradient']}/{f['fab']}/{f['d']}/{f['E_soft']} |")
    bone_fail = [f for f in out['failed_insertions'] if f['bone_elements']]
    L += ['', f"插入失敗 {len(out['failed_insertions'])} 個，其中 **{len(bone_fail)} 個含骨元素翻轉**（平台 [數值] 問題，不得歸咎設計）。", '', '### 2.2 視窗（含正常結束但曾翻轉重試的）', '']
    wj = [w for w in W if w.get('negjac_lines')]
    byb = Counter(); bone_win = []
    for w in wj:
        for k, v in w['negjac_elements_by_block'].items(): byb[k] += v
        if any('cortical' in k or 'trabecular' in k for k in w['negjac_elements_by_block']): bone_win.append(w)
    L += [f"- 有翻轉紀錄的視窗 {len(wj)}（其中結束 ERROR {sum(w['banner'] == 'ERROR' for w in wj)}，靜態重試 {sum(bool(w.get('static_retry')) for w in W)}）",
          f"- 翻轉元素所屬區塊合計：{', '.join(f'{k} {v}' for k, v in byb.most_common())}", f"- 含骨元素翻轉的視窗 {len(bone_win)}：" + ', '.join(f"{w['set']}/{w['design']}/{w['window']}({w['banner']})" for w in bone_win[:40])]
    L += ['', '## 3. [觀測] OBS-05 完整性', '']
    err = [w for w in W if w.get('banner') != 'NORMAL']; inc = [w for w in W if w.get('banner') == 'NORMAL' and not w.get('complete')]
    nor = [w for w in W if w.get('n_rows', 0) == 0 and w.get('banner')]
    L += [f"- 非 NORMAL 結束的視窗 {len(err)}：" + ', '.join(f"{w['set']}/{w['design']}/{w['window']}({w.get('banner')})" for w in err[:60]),
          f"- NORMAL 但 drive 沒走到 t_peak 的視窗 {len(inc)}", f"- 有 log 但 drive.txt 無上升段資料的視窗 {len(nor)}：" + ', '.join(f"{w['set']}/{w['design']}/{w['window']}" for w in nor[:30]),
          f"- 未達 1.5 N·m（濾除後）的 NORMAL 視窗 {sum(1 for w in W if w.get('banner') == 'NORMAL' and w.get('n_rows') and not w.get('reached'))}", '']
    L += ['## 4. [多元] DIV-04 不可計算設計的分布（插入 run 失敗 / 全部設計）', '']
    for s, v in out['sets'].items():
        L += [f"### {s}：{v['designs']} 設計，插入狀態 {v['insertion']}，失敗率 {v['overall_fail_rate']}", '']
        for key, dd in v['distribution'].items():
            L.append(f"- {key}：" + ', '.join(f"{k} {x['failed']}/{x['n']} ({x['rate']:.0%}{', ' + x['range'] if 'range' in x else ''})" for k, x in dd.items()))
        L.append('')
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    out = scan()
    json.dump(out, open(os.path.join(P, 'human_study/window_scan.json'), 'w'), indent=1)
    md = os.path.join(P, f"human_study/WINDOW_SCAN_{time.strftime('%Y-%m-%d')}.md"); open(md, 'w').write(report(out))
    print(f"{len(out['windows'])} windows, {len(out['failed_insertions'])} failed insertions -> {os.path.relpath(md, P)}")
