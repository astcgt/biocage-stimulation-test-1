"""Assemble REPORT.md (Traditional Chinese) from design + simulation summaries."""
import json, glob, os, math, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import MAT, CONTACT, ENDPOINTS, CYCLIC, SIXDOF, PRINT, DESIGN

J = lambda f: json.load(open(f))
L = []
w = L.append
ds = J('design/design_summary.json')

w('# Biocage 模擬測試 1：豬 C3/C4 PLCL cage 設計與有限元素模擬\n')
w('> 自動產生（scripts/06_report.py）。材料數值中標示「估計」者為文獻範圍內的估計值，取得 PLC 8516 原廠 datasheet 後應更新 `scripts/params.py` 並重跑。\n')
w('## 1. 背景與設計目標\n')
w('- 依據 Lintz 2021（Cornell）第 4 章：3D 列印 PLA cage 在迷你豬頸椎 4 週內全部於**後方**破壞，原因是椎體終板後外側的骨突（非材料強度）。')
w('- 本設計對策：cage 上下表面**直接貼合** STL 的 C3 尾側 / C4 頭側終板輪廓（零初始間隙，無點狀接觸），外緣內縮 1 mm 並沿後方凹口與後外側鉤突區走，中央 ~60 % 為 biodisc 窗口。')
w('- 兩種設計：**A 光滑面**；**B 鞋底防滑花紋**（人字形凸紋，嵌入骨面 — 視為植入後已壓合就位）。\n')
w('## 2. Cage 形狀與設計參數\n')
w(open('design/design_parameters.md').read())
w('\n![design](design/design_overview.png)\n\n![3d](design/cages_3d.png)\n')
w('列印檔：`design/cage_A_smooth.stl`、`design/cage_B_tread.stl`。\n')
w('## 3. 材料與接觸參數\n')
w('| 材料 | E (MPa) | ν | 其他 |\n|---|---|---|---|')
w(f"| {MAT['PLCL']['name']} | {MAT['PLCL']['E']:.0f}（估計） | {MAT['PLCL']['nu']} | 破損門檻 σ_vM ≥ {MAT['PLCL']['sigma_vm_fail']} MPa 或 σ1 ≥ {MAT['PLCL']['sigma_1_fail']} MPa（估計）；疲勞 Basquin b = {MAT['PLCL']['basquin_b']}, σf' = {MAT['PLCL']['basquin_sf']} MPa（估計） |")
for k in ('cortical', 'cancellous', 'biodisc'):
    w(f"| {MAT[k]['name']} | {MAT[k]['E']} | {MAT[k]['nu']} | |")
w(f"\n- cage–椎骨介面：**只有接觸壓力 + Coulomb 摩擦**，μ = {CONTACT['mu']}（FEA 文獻：光滑 PEEK 0.2、頸椎 cage 0.5）。")
w(f"- 列印：{PRINT['process']}；噴嘴 {PRINT['nozzle_diameter_mm']} mm、層高 {PRINT['layer_height_mm']} mm、線寬 {PRINT['line_width_mm']} mm、100 % 填充。FE 體素 0.2 mm = 1 層 = 半線寬，最小壁 1.5 mm ≈ 4 條線，花紋 0.8 × 0.4 mm = 2 線 × 2 層。\n")
w('## 4. 模擬方法\n')
w('![setup](figures/method_model_setup.png)\n\n![flow](figures/method_flowchart.png)\n')
w('- 網格：0.2 mm 結構化 8 節點六面體，約 240 萬自由度；骨（C3+C4 各約 5 mm 椎體骨塊，皮質終板 0.4 mm + 側殼 0.6 mm）與 cage（含 biodisc）為兩個獨立物體，介面節點重複、僅以接觸相連。')
w('- 施力：C4 底面固定；C3 頂面綁定到位於 cage 中心的剛體參考點（6 自由度）— 即以 C3–C4 為施力來源。')
w('- 求解：A100 GPU、fp64、無矩陣 Jacobi-PCG；接觸為節點對節點罰函數，法向 + 切向（kT = 0.1 kN）Coulomb 返回映射（stick/slip，含滑移歷史），主動集迭代至收斂。')
w('- 破損：PLCL 元素超過門檻即刪除（剛度 ×1e-3），同一載荷下重覆平衡直到不再產生新破損（漸進破壞）。')
w(f"- 終點：破損 PLCL 體積 ≥ {int(ENDPOINTS['damage_frac'] * 100)} %（同時報告 10 / 15 / 20 %），或 cage 相對 C3 / C4 平均滑移 ≥ {ENDPOINTS['slip_mm']} mm。")
w('- GPU 平行化：各模擬案例彼此獨立，以一個 worker 一張 GPU 的方式分派（GPU 3 / 4 / 7；0、1、2、5、6 為其他使用者佔用未使用）。單一 FEM 求解本身不跨 GPU。基準測試見 `logs/benchmark.md`。\n')

# ---------------- Test 1
w('## 5. 測試一：垂直壓力測試\n')
w('位移控制 C3 軸向下壓（其餘 5 自由度自由 = 球窩），每步 0.01 mm，接近破損後 0.005 mm。\n')
w('| 設計 | 初始剛度 (N/mm) | 首次破損 (N) | 最大荷重 = 結構破壞 (N) | 10 % 破損時 Uz (mm) | 15 % 破損時 Uz (mm) | 最大滑移 (mm) | 停止原因 |\n|---|---|---|---|---|---|---|---|')
for d in ('A_smooth', 'B_tread'):
    f = f'results/test1_static/{d}/summary.json'
    if not os.path.exists(f): w(f'| {d} | （未完成） |||||||'); continue
    s = J(f); c = s['damage_crossings']
    g = lambda k: '-' if c.get(k) is None else f"{c[k]['uz_imposed']:.3f}"
    w(f"| {d} | {s['stiffness_N_per_mm']:.0f} | {('%.0f' % s['first_damage']['Fz']) if s['first_damage'] else '-'} | {s['peak_Fz_N']:.0f} | {g('0.1')} | {g('0.15')} | {s['max_slip_mm']:.4f} | {s['stop_reason']} |")
for d in ('A_smooth', 'B_tread'):
    if os.path.exists(f'results/test1_static/{d}/curves.png'):
        w(f'\n**{d}**\n\n![c](results/test1_static/{d}/curves.png)\n\n![s](results/test1_static/{d}/final_state.png)\n\n![sl](results/test1_static/{d}/internal_stress_slices.png)\n\n動畫：`results/test1_static/{d}/stress_evolution.gif`；互動 3D：`results/test1_static/{d}/interactive_3d.html`\n')

# ---------------- Test 2
w('## 6. 測試二：標準循環負荷測試（ASTM F2077 式）\n')
w(f"正弦軸向壓縮 {CYCLIC['freq_hz']} Hz、R = {CYCLIC['R']}（Fmin = Fmax/10）、上限 {CYCLIC['runout']:,} 次（runout）；Fmax = 測試一最大荷重 × {', '.join(f'{x:.3g}' for x in CYCLIC['levels'])}。"
  '每個 block 明確模擬 2 個循環（取應力幅與介面棘輪滑移），再以 Basquin + Goodman + Miner 損傷率跳躍週期（每跳最大 ΔD = 0.1），損傷達 1 的元素刪除後重新平衡。\n')
w('| 設計 | 等級 | Fmax (N) | 到終點循環數 | 終點類型 | 10 % / 15 % / 20 % 破損循環數 | 最終破損 % | 最終滑移 (mm) | runout |\n|---|---|---|---|---|---|---|---|---|')
for f in sorted(glob.glob('results/test2_cyclic/*/summary.json')):
    s = J(f); c = s['damage_crossings']
    g = lambda k: '-' if c.get(k) is None else f"{c[k]['N']:.3g}"
    w(f"| {s['design']} | {s['level']:.3g} | {s['Fmax']:.0f} | {'-' if s['cycles_to_endpoint'] is None else ('%.3g' % s['cycles_to_endpoint'])} | {s['endpoint_type'] or '-'} | {g('0.1')} / {g('0.15')} / {g('0.2')} | {100 * s['final_damage']:.2f} | {s['final_slip_mm']:.4f} | {'是' if s['runout'] else '否'} |")
if os.path.exists('figures/test2_load_vs_cycles.png'): w('\n![sn](figures/test2_load_vs_cycles.png)\n')

# ---------------- Test 3
w('## 7. 測試三：六自由度測試\n')
w(f"先以 {SIXDOF['preload_N']:.0f} N 軸向預載（力控制維持），再對受測自由度逐步施加位移 / 角度（旋轉每步 0.25°、至 10°；平移每步 0.05 mm、至 3 mm），其餘自由度自由。"
  '沒有韌帶 / 小面關節時，純力控制 ±1.5 Nm 會使 C3 翻倒（屈伸極限 ≈ 0.87 Nm），故經使用者同意改為位移控制並記錄對應力矩 / 剪力。\n')
w('| 設計 | 模式 | 最大力矩或剪力 | 終點時角度 / 位移 | 最終破損 % | 最終滑移 (mm) | 最大 σ_vM (MPa) | 停止原因 |\n|---|---|---|---|---|---|---|---|')
for f in sorted(glob.glob('results/test3_6dof/*/summary.json')):
    s = J(f)
    rot = s['dof'] > 2
    mx = f"{s['max_load'] / 1000:.2f} Nm" if rot else f"{s['max_load']:.1f} N"
    im = f"{math.degrees(abs(s['max_imposed'])):.2f}°" if rot else f"{abs(s['max_imposed']):.2f} mm"
    w(f"| {s['design']} | {s['mode']} | {mx} | {im} | {100 * s['final_damage']:.2f} | {s['final_slip']:.3f} | {s['max_vm']:.1f} | {s['stop_reason']} |")
if os.path.exists('figures/test3_summary.png'): w('\n![6dof](figures/test3_summary.png)\n')

w('## 8. 限制\n')
for t in ['PLC 8516 的 E、強度、疲勞參數為文獻範圍估計值；原廠數據應替換後重跑（改 `scripts/params.py`）。',
          '線彈性 + 元素刪除：PLCL 為延性聚合物，壓縮區「破損」後在真實材料中仍會以塑性流動承載，因此破損後的荷重下降可能被高估（偏保守）。未含黏彈性 / 潛變與水解降解。',
          '節點對節點接觸為小滑移假設：滑移超過約一個體素（0.2 mm）後介面配對不更新；以 2 mm 為終點時，大滑移階段為近似。',
          '骨只取終板附近約 5 mm 骨塊；無韌帶、小面關節、外層纖維環（依設定，cage 與椎骨間只有壓力與摩擦）。C3 後唇與 cage 後壁之間沒有接觸配對。',
          '花紋凸紋視為已完全嵌入骨面（植入壓合後狀態）。',
          '疲勞以 Basquin + Goodman + Miner 與週期跳躍估算，並非逐週期模擬；滑移棘輪由每個 block 的 2 個明確循環外推。']:
    w(f'- {t}')
open('REPORT.md', 'w').write('\n'.join(L) + '\n')
print('REPORT.md written')
