"""Project status page (PI 2026-11-18, topic A7): one plain-language page generated from result files only.

Every number is read from a result file and shown with that file's name and modification time; nothing is typed by hand
and nothing is estimated. The hand-written topic list (what waits for the PI, what is planned) stays in
human_study/PI_PENDING_DECISIONS.md; this page only says where things stand.
Read-only on every input. Output: human_study/PROJECT_STATUS.md.
usage: python scripts/8_audit/h38_project_status.py
"""
import os, json, glob, csv, time, subprocess, collections

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVO = os.path.join(os.path.dirname(P), 'biocage-evo'); HS = os.path.join(P, 'human_study'); HF = os.path.join(os.path.dirname(P), 'biocage_evo_hf')
mt = lambda f: time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(f)))
src = lambda f: f'來源：`{os.path.relpath(f, P)}`（{mt(f)}）'
sh = lambda cmd, cwd=P: subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True).stdout.strip()

CLASS_ZH = [('PASS', '通過'), ('GREY', '灰區（後方位移 0.45–0.55 毫米，只供分析）'), ('radial-mix-excluded', '徑向混合家族（排除）'),
            ('compression', '壓縮不過關'), ('unstable-window', '計算不穩定'), ('computability', '算不出來'), ('not-computable', '兩種摩擦算法都算不出來')]


FAMILY_ZH = dict(radial_interleave='徑向交錯', radial_mix='徑向混合', axial_interleave='軸向交錯', axial_mix='軸向混合', both_interleave='雙向交錯', both_mix='雙向混合')
CHECK_ZH = {'R20-replicate-agreement': '同一設計重跑兩次的結果是否一致', 'R10-llm-audit-due': '有新的決定或設定變更，還沒做語意稽核', 'R10-register': '稽核登記簿有不符項目',
            'R5-counts': '文件裡的分類計數與結果檔是否一致', 'R12-index': '檔案索引列出的路徑是否都存在'}


def zh_class(k):
    return next((z for key, z in CLASS_ZH if key in k), k)


out = [f'# 專案狀態頁（自動產生 {time.strftime("%Y-%m-%d %H:%M")}）', '',
       '由 `scripts/8_audit/h38_project_status.py` 從結果檔產生，**不要手改**。每個數字後面都附來源檔與該檔的時間。',
       '等您決定與規劃中的事項另見 `human_study/PI_PENDING_DECISIONS.md` 最上方的議題總表。', '']

# 1. designs
f = os.path.join(EVO, 'results/method/split/verdict_classes_merged.json'); d = json.load(open(f)); cnt = collections.Counter()
for k, v in d['classes'].items(): cnt[zh_class(k)] += len(v)
out += ['## 一、設計目前的分類', '', '| 分類 | 設計數 |', '|---|---|'] + [f'| {k} | {n} |' for k, n in cnt.most_common()] + [f'| 合計 | {sum(cnt.values())} |', '',
        f'- 帶「介面剪力超過暫定 3 MPa」旗標的設計：{len(d["shear_check_exceeded"])} 個（只是旗標，不淘汰）。', f'- {src(f)}', '']
f = os.path.join(EVO, 'results/method/fric/verdicts.json'); v = {k: x for k, x in json.load(open(f)).items() if k != '_meta'}
c = collections.Counter(x['verdict'] for x in v.values()); zh = dict(**{'pass': '通過', 'grey': '灰區', 'open': '還沒有結論', 'fail': '不通過'})
out += ['## 二、真實摩擦檢驗', '', f'- 做過真實摩擦計算的設計 {len(v)} 個：' + '、'.join(f'{zh.get(k, k)} {n}' for k, n in c.most_common()) + '。', f'- {src(f)}', '']

# 2. estimator
fs = sorted(glob.glob(os.path.join(EVO, 'results/surrogate/validation_????-??-??.json')))
if fs:
    f = fs[-1]; o = json.load(open(f)); name = dict(post_ext='後伸的後方位移（毫米）', uh_flex='屈曲的位移（毫米）', y2='所需摩擦係數', y3='所需介面剪力（MPa）')
    out += ['## 三、快速估算器的驗證（只用來挑下一批要模擬的設計，不進入判定）', '', f'名目涵蓋率 {int(o["nominal_coverage"] * 100)} %；同一設計的所有計算整組留出。', '',
            '| 預測目標 | 筆數／組數 | 校正後實際涵蓋率 | 區間寬度（中位數） | 平均絕對誤差 | 比「猜家族平均」準多少 | 可否用來導向 | 涵蓋不足的家族 |', '|---|---|---|---|---|---|---|---|']
    for t, z in name.items():
        r = o['targets'][t]['G/leave-one-group-out']; under = [FAMILY_ZH.get(k, k) for k, x in r['per_family'].items() if x.get('under_covered')]
        out.append(f"| {z} | {r['n_rows']}／{r['n_groups']} | {r['conformal']['empirical_coverage']:.2f} | {r['conformal']['width_median']:.3g} | {r['mae']:.3g} | "
                   f"{'%d %%' % round(100 * r['skill']) if r['skill'] > 0 else '更差'} | {'可' if r['steer_conformal'] else '不可（只做探索）'} | {'、'.join(under) or '無'} |")
    r = o['targets']['uh_flex']['D/leave-one-family-out']
    out += ['', f"- 沒看過的家族（整個家族留出）：屈曲位移的涵蓋率 {r['empirical_coverage']:.2f}，等於不可預測；新形狀一律直接模擬。", f'- {src(f)}', '']

# 3. QA + scorecard
f = os.path.join(HS, 'qa/QA_STATUS.json'); q = json.load(open(f)); bad = [x for x in q['checks'] if x['status'] != 'PASS']
out += ['## 四、品質保證', '', f"- 自動檢查整體：{q['overall']}（{q['time']}）；共 {len(q['checks'])} 項，未通過或警告 {len(bad)} 項。"]
out += [f"  - {'警告' if x['status'] == 'WARN' else '未通過'}｜{CHECK_ZH.get(x['id'], x['id'])}（{x['id']}）" for x in bad] + [f'- {src(f)}', '']
f = os.path.join(HS, 'CAPABILITY_SCORECARD.md'); st = collections.Counter(); seen = set()
for line in open(f):
    p = [x.strip() for x in line.split('|')]
    if len(p) >= 6 and p[3] in ('TIED', 'FRIC', 'GPUFE') and p[1][:3] in ('PHY', 'NUM', 'SPD', 'OBS', 'DIV', 'GEN', 'TIM') and (p[1], p[3]) not in seen:
        seen.add((p[1], p[3])); st[p[4]] += 1
out += ['## 五、平台能力計分表', '', '- 檢查項 × 平台配置共 %d 列：' % sum(st.values()) + '、'.join(f'{k} {n}' for k, n in st.most_common()) + '。',
        '- 「未評」多數是程式改過後需要重新評分，不等於失敗；「不合格」才是已知未達標。', f'- {src(f)}', '']

# 4. machines and repositories
gpu = sh('nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader,nounits').splitlines()
nq = len(glob.glob(os.path.join(HS, 'queue/*.job'))); nr = len(glob.glob(os.path.join(HS, 'queue/running/*.job')))
out += ['## 六、機器與排程（產生這一頁當下）', '', f'- 排程佇列：等待 {nq} 個、執行中 {nr} 個。',
        '- 圖形處理器使用率（含其他使用者）：' + '；'.join(f'{a.split(",")[0].strip()} 號 {a.split(",")[1].strip()} %' for a in gpu) + '。', '']
rows = []
for name, d_ in (('模擬平台（GitHub）', P), ('演化研究（GitHub）', EVO), ('公開資料（Hugging Face）', HF)):
    if not os.path.isdir(os.path.join(d_, '.git')): continue
    ahead = sh('git rev-list --count @{u}..HEAD 2>/dev/null', d_) or '?'; dirty = len([x for x in sh('git status --porcelain', d_).splitlines() if not x.startswith('??')])
    last = sh('git log -1 --format=%h', d_); when = sh("git log -1 --format=%cd --date=format:'%m-%d %H:%M'", d_)
    rows.append(f"| {name} | {last}（{when}） | {ahead} | {dirty} |")
out += ['## 七、倉庫同步狀況', '', '| 倉庫 | 最新提交 | 尚未推送的提交數 | 已修改但未提交的檔案數 |', '|---|---|---|---|'] + rows + ['']
open(os.path.join(HS, 'PROJECT_STATUS.md'), 'w').write('\n'.join(out) + '\n')
print('wrote human_study/PROJECT_STATUS.md,', len(out), 'lines')
