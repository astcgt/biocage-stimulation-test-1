# 骨元素「負 Jacobian」失敗分析（2026-11-03）

對象：16 個插入 run ERROR（15 個 log 含 C3/C4 皮質骨元素翻轉）、192 個視窗含翻轉紀錄（WINDOW_SCAN_2026-11-02.md 第 2 節）。
資料：physio_rot_split2 / split3 / split4 / physio_fric / physio_degr* 的 case.feb、case.log、case.json、w_*/case.log，FEBio 4.13 原始碼（third_party/FEBio，含本平台三個補丁）。
分析腳本（可重跑）：`/tmp/claude-1024/-raid-jupyter-alz-ee09-projects-claude-work-biocage-simulation-test-oct2026/d99ba160-8118-43e3-9211-3a3e1396acb6/scratchpad/bone/`（negjac_timeline.py、bone_geom_quality.py、scan_all_runs.py、scan_windows.py、feb_structure.py）。
只讀分析，沒有啟動任何模擬，沒有改程式碼。

---

## 0. 一句話結論

**FEBio 沒有「算不動骨頭」。** 15 個 run 裡被回報翻轉的骨元素，初始形狀品質和整塊皮質骨一樣好，而且 log 裡的 Jacobian 值是 −2 到 −10¹³（體積比；物理上不可能），代表它們是 **Newton 迭代發散後的試探解** 裡被壓爛的，不是逐步被壓扁的。
真正的起點在 15/15 個 run 都一樣：**軟墊（cage_soft，Gent 材料，E_soft 1.5–4 MPa）先翻轉**，因為它在 100 N 追隨力下必須壓到 Gent 鎖死伸長（λ ≈ 0.60，Jm = 0.7 之極限）才撐得住 2.7–4.4 MPa 的名義應力；一到鎖死點，材料切線剛度趨近無限、Newton 發散，發散的位移增量在「剛體灌注層與可變形骨的交界」和「籠子足跡下的終板」把骨四面體翻掉。骨頭只是受害者，而且還因 FEBio 的輸出規則（每次更新只印第一個出事的 domain，皮質骨 domain 排第一）被高估。
p023 在 t = 2.0 失敗（軟墊脹到位＋tied contact 在同一步形成）、p053 在 t = 3.0 失敗（追隨力開始＋static→dynamic 切換；每個 run 在這一步殘差都跳 10⁵ 倍），兩者都是平台側的「事件集中在同一時刻」問題，可以用時間步策略和補丁順序修。

---

## 1. 問題：發生了什麼

### 1.1 四個失敗 run 的時間線（log 逐步解析）

| run | 家族/梯度/製法 | E_soft (MPa) | 第一次翻轉（任何元素） | 第一次骨翻轉 | 停在 t | 骨翻轉元素數 / 區塊 | 骨元素 J 值（中位數 / 最小） |
|---|---|---|---|---|---|---|---|
| split2/p023 | B/both/interleave | 1.502 | t 1.78，cage_soft（籠壁中段 102 個） | t 1.99909（t=2.0 這一步的第 1 次重試） | 1.99（t=2.0 步 10 次重試用盡） | 130 C4_cortical | −2.5 / −1103 |
| split2/p053 | A/both/interleave | 1.572 | t 1.89，cage_soft（籠頂附近 91 個） | t 3.05（第一個動態步） | 3.0105 | 141 C3_cortical | −28 / −2.0×10⁴ |
| split2/p011 | B/both/interleave | 2.002 | t 1.18，cage_soft（籠壁中段 99 個） | t 3.041 | 3.099 | 131 C3_cortical | −0.8 / −1.7×10⁵ |
| fric/p048 | A/radial/interleave（真摩擦 μ 0.35） | 1.674 | t 1.997，cage_soft（籠底 24 個） | t 2.722（release 步） | 3.009 | 502 C3_cortical + 87 C4_cortical + 1 trab. | −4.5 / −7×10¹³ |

Jacobian 在 FEBio 是 det F（目前體積 / 參考體積）。−1103 的意思是「這個四面體被翻到參考體積的一千倍」，這不是變形，是發散。

### 1.2 全部插入 run 的統計（split2/3/4 + fric，64 個 run）

- 15 個「含骨翻轉」的失敗 run，**15/15 籠子軟墊先翻轉**（first_cage 時間 ≤ first_bone 時間；p057 兩者在同一步 t=3.05）。
- 失敗 run 的重試位置：13/16 集中在 t = 3.0–3.4（追隨力 + 動態步開始），p023 在 t = 2.0，p115（fric）在 release 步 t 2.59（只有 cage_soft 翻轉，無骨）。
- 29 個 NORMAL run 裡有 13 個也曾出現 cage_soft 翻轉（1–300 筆），都被 line search 和重試吸收，**沒有一個 NORMAL run 出現骨翻轉**。
- 失敗與設計的關係（名義應力 = 100 N / 籠子實心面積；A 族實心 37.4 mm² → 2.67 MPa，B 族 22.5 mm² → 4.44 MPa）：

| 群 | σ_100N / E_soft | 插入結果 |
|---|---|---|
| B 族 interleave，E_soft 1.5–4.2 | 1.06–2.95 | 8/8 ERROR |
| B 族 mix p044，E_soft 4.79 | 0.93 | NORMAL（但 6 個視窗全 ERROR） |
| A 族 E_soft 1.57–1.67，both/axial 梯度 | 1.6–1.7 | 6/6 ERROR（p053 p055 p057 p058 p098 + fric p084） |
| A 族 E_soft 1.67–1.92，radial 或 mix | 1.4–1.6 | NORMAL（p064 p116 p097 p107 p068 p036；p048 在 split2 NORMAL、在 fric（真摩擦）ERROR） |
| A 族 E_soft ≥ 3.3 | ≤ 0.8 | 全部 NORMAL |

門檻很清楚：**σ_100N / E_soft 超過約 1.5–1.6 就不可計算**，這是材料（Gent 鎖死）而不是骨頭。

### 1.3 視窗 run（378 個有 log）

- 192 個有翻轉紀錄，其中 **188 個在某次 Newton 迭代的位移增量範數平方 > 10³（即一步 > 30 mm）**：視窗裡的翻轉同樣來自發散的試探解（h14 註解裡已知的「軟中性區 → 巨大 predictor」問題，動態視窗 + 剛體關節驅動）。
- 第一個翻的 domain：bone 123、facet/disc 48、cage 21。視窗裡骨確實常常「第一個被印出來」，但見 2.2 節：這是印出順序。
- 366/378 視窗 NORMAL：FEBio 的 line search 與重試把這些發散吸收掉了；只有 12 個（p044 的 6 個 B 族視窗、p015/extension、p027/AR_right、p041/flexion、fric 2 個…）用盡重試。

---

## 2. 原因

### 2.1 FEBio 的「Negative jacobian」到底是什麼（原始碼確認）

| 項目 | 事實（third_party/FEBio，4.13 + 本平台補丁） |
|---|---|
| 在哪裡丟出 | `FECore/FESolidDomain.cpp:543` 等：`defgrad()` 算出 det F ≤ 0 就 `throw NegativeJacobian(el, n, D)`。每次 **模型更新（Newton 試探解）** 都檢查，不是只在收斂後。 |
| 怎麼處理 | `FEBioMech/FEElasticSolidDomain.cpp:548-574`：整個 domain 跑完再丟 `NegativeJacobianDetected`；`FECore/FELineSearch.cpp:200-222`：因為平台設 `ls_check_jacobians = 1`，line search 會把步長砍半最多 5 次（s ≥ 1/32）再重丟；`FECore/FENewtonSolver.cpp:511`：任何 FEException → 這個時間步失敗；`FECore/FEAnalysis.cpp:516-531`：自動時間步 **重試**，用盡 `max_retries`（10）才 ERROR TERMINATION。 |
| 重試的步長 | `FECore/FETimeStepController.cpp:161-177`：`aggressiveness = 0`（平台預設）時 **線性遞減** dt − k·dt/11，所以 10 次重試只能把 0.01 降到 0.0009、把 0.05 降到 0.0045；`dtmin`（dt/100）根本碰不到。p023 的 10 次重試：0.00909 → 0.000909 全部失敗。 |
| 印出規則 | `FECore/FEException.cpp:156-164`：`-output_negative_jacobians=50` 是 **每個 domain 每次更新最多印 50 筆**；`FECore/FEMesh.cpp:1128-1135`：domain 依序更新，第一個丟例外的 domain 就中止整個更新 → **同一次更新裡只有「第一個出事的 domain」會被印出來**。本模型 domain 順序：C3_cortical（第 1）、…、C4_cortical（第 5）、…、cage_hard、cage_soft（最後）。 |
| 收斂狀態會不會有翻轉元素 | 不會。收斂的那一步一定通過了所有 domain 的更新（J > 0）。所以 log 裡的翻轉元素全是 **未收斂試探解** 的元素。 |

結論：「Negative jacobian」在 FEBio 4.13 是 **一個可恢復的警告**（line search 砍步、時間步重試），只有重試用盡才致命；log 裡出現幾千筆不代表模型裡真的有幾千個壞元素。

### 2.2 骨元素被高估：印出順序 + 50 筆上限

- p053 在 t 3.0156 / 3.0134 的紀錄是 **「C3_cortical：300，其它 0」**：= 6 次 line-search 嘗試 × 50 筆上限，且全部是 domain 1；同一次更新裡籠子有沒有翻轉 **根本沒被檢查**。
- 視窗掃描的「C3_cortical 14663 筆、cage_soft 2397 筆」因此不能拿來比大小；能用的只有「哪個 domain 在時間上最早出事」（1.2 節：插入 run 15/15 是 cage_soft 先）。

### 2.3 被翻轉的骨元素長什麼樣、在哪裡

初始幾何品質（case.feb 參考座標，與同一塊皮質骨的母體比較；骨是 **tet4 線性四面體**，不是六面體 — 任務說明裡的「thin hex layer」是錯的，refined 網格的皮質骨/鬆質骨都是 tet4，只有椎間盤/小面關節軟骨和籠子是 hex8）：

| run | 骨元素 | 體積中位（母體） mm³ | 最短邊中位 mm | 3r/R 品質中位（母體；1 = 正四面體） | 最小二面角中位（母體） | 位置 |
|---|---|---|---|---|---|---|
| p023 | 130 C4_cortical | 0.0049（0.0098） | 0.22 | 0.64（0.66） | 35°（39°） | **105/130 在 C4 終板表面、114/130 在籠子足跡內**，離最近籠節點 0.3–1.4 mm；0 個碰小面關節、0 個碰灌注層 |
| p053 | 141 C3_cortical | 0.34（0.011） | 1.18 | 0.82（0.68） | 45°（40°） | **141/141 與 C3 剛體灌注層共用節點**，離籠子 3–21 mm（中位 12.6）；0 個在終板 |
| p011 | 131 C3_cortical | 0.37 | 1.19 | 0.80 | 44° | **131/131 在灌注層交界**，離籠子中位 13.7 mm |
| fric/p048 | 590 | 0.012 | 0.36 | 0.70 | 41° | 兩類混合：199 在終板（214 在足跡內，最近籠節點 0.02–0.08 mm）＋150 在灌注層交界 |
| p015/w_extension（視窗，ERROR） | 389 C3_cortical | — | — | 0.73 | — | 266 在灌注層交界、56 在終板 |
| p027/w_extension（視窗，NORMAL） | 124 C3_cortical | — | — | 0.80 | — | 124/124 在灌注層交界 |

四個候選裡的判定：
- (a) **一開始就壞的元素：否。** 品質與母體相同甚至更好（灌注層交界的元素是 refined 之外的粗元素，3r/R 0.8）。
- (b) **籠子邊緣 / 接觸推擠：是，但只在 p023、p048 這種「插入末、籠子脹滿」的失敗**（終板 refined 區，皮質層厚度 ≈ 1.0 mm，以終板節點到最近鬆質骨節點的距離估計，p10–p90 = 1.00–1.06 mm）。
- (c) **小面關節接觸：否**（0 個元素碰 C34_L/R_FC 面）。
- (d) **剛體灌注交界：是，p053 / p011 / 所有視窗的主要位置。** 這一層是「一邊節點被剛體帶著走、另一邊節點自由」的單層四面體，Newton 發散時剛體自由度的巨大增量（p053 第一個動態步位移範數平方 780，正常靜態步 0.15；p015/w_extension 第 5 步 2.45×10⁴）直接把它們翻掉。
- 時間：全部出現在「重試中的試探解」，首次骨翻轉之前 **一定已經有 cage_soft 翻轉與 line-search 砍步**。

### 2.4 真正的起點：軟墊的 Gent 鎖死

籠子材料（h14_build_case.py 第 179-185 行，PI 2026-10-21 Q45）：`Gent`，G = E/(2(1+ν))，`Jm = 0.7`，k = E/(3(1−2ν))，包在 `uncoupled prestrain elastic` 裡做 'expand' 插入。Gent 應變能 W = −(G/2)·Jm·ln(1 − (I₁−3)/Jm)，**I₁−3 → Jm 時應力與切線剛度 → ∞**（FEBioMech/FEGentMaterial.cpp:57,156：W₁ = ½·G·Jm/(Jm−I₁+3)）。單軸壓縮下 I₁−3 = λ²+2/λ−3 = 0.7 的鎖死伸長是 **λ = 0.60（壓 40 %）**。

p023 的軟墊（E 1.502 MPa，G 0.518）在近似不可壓縮單軸壓縮下：

| λ | 0.80 | 0.70 | 0.65 | 0.62 | 0.61 | 0.605 | 0.60 |
|---|---|---|---|---|---|---|---|
| Cauchy 壓應力 (MPa) | 0.40 | 0.96 | 2.0 | 5.0 | 9.3 | 16.6 | ∞ |

需要承受的名義應力：A 族 2.67 MPa、B 族 4.44 MPa（整個實心面積都算進去，實際軟墊分到的更高，因為 interleave 的硬層只佔 18–53 %）。E_soft ≤ 1.7（A）或 ≤ 4.2（B）的設計必須壓到 λ ≈ 0.61–0.62，離奇異點只剩 0.01–0.02 的伸長：切線剛度在一個時間步內變化十倍以上、接觸壓力重分配、薄籠壁（0.8 mm，4 個 0.2 mm hex 橫跨）側向挫屈（p023、p011 第一批翻轉的 cage_soft 元素 60 %、49 % 在籠壁中段）。Newton 在這種硬化奇異點附近發散是教科書行為，與求解器品牌無關。

B 族（平面籠 + 軟墊）全滅，與 both 梯度、interleave、低 E_soft 的相關，全部可以由 σ_100N/E_soft 這一個比值解釋（1.2 節）。

### 2.5 失敗為什麼都擠在 t = 2.0 和 t = 3.0？（平台側的事件堆疊）

**t = 3.0（13/16 失敗）**：同一瞬間發生三件事 — (i) 分析從 static 切成 dynamic（密度 1e-6 t/mm³、rhoi 0），(ii) 追隨力 0 → −100 N 開始 ramp（0.5 s），(iii) 時間步從 release 的 dtmax 0.1 變成 0.05。**每一個 run**（含 NORMAL 的 p015、p060 等）第一個動態步的初始殘差都從靜態步的 ~2–4 跳到 10⁴–10⁶，位移增量範數平方從 ~0.04 跳到 10²–10³；硬籠子撐得住這一下，軟籠子撐不住。這個「切換衝擊」不是設計的物理，是平台的時間安排。

**t = 2.0（p023）**：同一步裡 (i) prestrain ramp 到 0（籠子脹到設計高度，壓力最大），(ii) `tied-elastic` 的 `init_time = 2.0`（本平台補丁，FETiedElasticInterface.cpp:551-557）在 **這一步的第一次 Newton 更新** 就用「未收斂的構形」建立綁定（`currentTime ≥ m_tinit` 在 t=2.0 這步的迭代中已成立），(iii) sliding-elastic 和 tied-elastic 同時作用在同一對面（兩個懲罰剛度相加，自動懲罰 = penalty × E/h，皮質骨 E 8000–12000 MPa、h ≈ 0.2–0.5 mm → 10⁵–10⁶ N/mm³）。另外補丁的 `m_binit` 沒有進 Serialize，**時間步重試還原狀態時綁定不會被解除**，之後的 10 次重試都帶著一個在壞構形上建立的綁定；這是 p023 在 t = 2.0 之後再也收斂不了的候選原因（p053、p011、p048 在 t=2.0 這步也都出現過翻轉或重試，但撐過去了）。

### 2.6 骨頭為什麼「看起來」這麼脆（次要因素，解釋受害者為什麼是它）

1. **單點積分線性四面體**（FEBio 預設 `FE_TET4G1`，FEBioXML/FEModelBuilder.cpp:57；log 裡骨元素永遠是 gauss point 1）：常應變、彎曲過硬、鬆質骨 ν 0.3 尚可，但在剛體交界的單層四面體上，任何大位移增量都會直接變成 det F < 0。
2. **皮質骨本構是 St.Venant–Kirchhoff 型 `orthotropic elastic`**（FEOrthoElastic.cpp:252-259，W 是 Lagrange 應變 E 的二次式）：這類材料 **對元素翻轉沒有能障**（J → 0 時應變能有限，不像 neo-Hookean 的 ln J → −∞），試探解一壞就翻。另外 Herron 模型的 G31 = 444 MPa（G12 2857、G23 3677）使 FEBio 的 Lamé 係數 μ₁ = G12 + G31 − G23 = **−376 MPa**（FEOrthoElastic.cpp:96）；Validate() 只檢查三個 Poisson 比，不檢查這個。小應變剛度仍是正定的，所以成功 run 沒事，但 G31 比另外兩個剪力模量小 8 倍是否為原始模型的筆誤，值得向 Herron 2020 原文核對一次（不是這次失敗的原因，所有成功 run 用同樣的骨）。
3. **灌注層設計**：C3 的 pot 區是剛體材料（mat 2）的 tet4，與可變形皮質骨直接共用節點，沒有過渡；剛體 z 自由度在 t ≥ 2 是力控制（release 後 C3 只靠籠子、小面關節、韌帶撐著）；軟籠子的切線剛度崩潰 = 剛體 z 方向近乎奇異 → 增量巨大。

### 2.7 針對 p023 / p053 的回答

- **p023（t 1.99，插入階段，還沒加追隨力）**：撐住籠子的不是追隨力而是 **分離 d = 1.013 mm 下籠子自身的脹回**。E_soft 1.5 MPa、B 族、both 梯度（上下都軟）：脹回時籠壁中段從 t 1.78 就開始挫屈翻轉（122 筆，line search 砍到 0.0015 才過），t 1.97 再 128 筆，t 2.0 這一步（脹滿 + tied 綁定在迭代中形成 + sliding 與 tied 懲罰相加）Newton 第一次迭代就把 251 個籠元素與 8 個 C4 終板元素翻掉，10 次線性遞減重試（最小 dt 0.0009）全失敗。骨元素是籠子足跡正下方的 refined 終板四面體（0.22 mm 邊、1 mm 皮質層）。
- **p053（t 3.0105）**：插入和 release 都過了（t 1.89 和 1.99 兩次籠翻轉被吸收），死在第一個動態步：初始殘差 5.8×10⁵、位移範數平方 780（靜態步 0.15），追隨力才 10 N 就要軟墊（E 1.57）從脹回狀態再壓向鎖死點；重試把 dt 砍到 0.0002 仍然殘差 4.9×10⁸（鎖死奇異點附近的應力）。141 個 C3 皮質骨元素全在灌注層交界，離籠子 3–21 mm，J 中位 −28 — 純粹是剛體增量的受害者。

---

## 3. 建議解法（依預期效果 / 成本 / 對其他能力的影響排序）

| # | 方案 | 預期效果 | 實作成本 | 對 [速度] [多元] [物理] 的影響 | 先導測試（一個設計） |
|---|---|---|---|---|---|
| 1 | **可計算性前置檢查（物理）**：建 case 前算 σ_demand/E_soft（含 interleave 硬層分擔）與 Gent 鎖死伸長；比值 > ~1.3 的設計標成「軟墊超載」直接不跑，或改為先驗證加載上限。 | 高：16 個失敗中 14 個可在啟動前判定；省 GPU 時數。 | 低（h14/h28 加一個判斷 + 記錄）。 | 速度↑；多元：不是砍設計，是把「物理上撐不住 100 N 的軟墊」正確標示為設計失敗而非平台失敗；物理不變。 | 不需跑；用 scan_all_runs.json 回測門檻即可。 |
| 2 | **時間步策略**：`aggressiveness = 1`（重試幾何砍半，10 次可到 dt/1000）、`dtmin` 配合；t = 3.0–3.1 與 t = 1.95–2.05 加 must-point 小步（dt 0.005）。 | 中：解決「事件堆疊步撐不過」，不解決鎖死本身；預期 p023 類（t=2）和臨界 A 族（p064/p048 這種邊緣）受益。 | 極低（h14 control() 兩行）。 | 速度：失敗 run 多跑幾分鐘，成功 run 幾乎不變；多元↑（臨界設計能算）；物理不變。 | p023 與 p053 各重跑插入段：0.1 + 0.3 GPU-h（插入 run 6–16 min/GPU）。 |
| 3 | **拆開 t = 3.0 的三合一事件**：追隨力在 release 末段靜態加上（或 2.5–3.0 ramp），動態切換單獨一步、或第一個動態步用 dt 0.005 起步再放大；必要時 rhoi 0.5 試一次。 | 中–高：所有 run 的 10⁵ 倍殘差跳躍消失，13/16 失敗落在這裡。 | 低–中（h14 步驟重排 + h28 預跑的 t 對應）。 | 速度：多 10–20 個小步（+1–2 min）；多元↑；物理：追隨力的加載歷史更接近「先壓好再轉」。 | p053 插入段 + 1 個視窗：≈0.6 GPU-h。 |
| 4 | **tied 補丁修正**：綁定改在 t = 2.0 **收斂後**（release 步 Activate 時用當時構形）形成；`m_binit` 與投影資料進 Serialize；綁定形成後把 sliding 懲罰的 lc 降為 0（避免同一面雙懲罰）。 | 中（直接對 p023 類；也降低 t=2 步所有 run 的翻轉/重試：p053 p011 p048 在這步都曾翻轉）。 | 低（FEBio 補丁 ~15 行 + h14 的 pen_ramp 曲線）。 | 速度↑（t=2 步少重試）；多元↑；物理：綁定在真正的坐定構形上形成，更合理。 | p023 插入段：0.1 GPU-h。 |
| 5 | **Jm 放寬**（例如 2–5，鎖死移到 λ 0.45–0.30）或改回 uncoupled neo-Hookean 做可計算性篩選，用後處理的最大壓應變判設計是否「壓爛」。 | 高（移除奇異點，Newton 不再發散），但改變 PI 2026-10-21 的 Q45 決定（Jm 0.7 代表 PLCL 軟層壓 40 % 就頂住）。 | 低（參數）。 | 速度↑；多元↑；物理：軟墊會被算成壓得更扁（需用後處理門檻補回「材料強度」的意義），必須 PI 同意。 | p053 插入段，Jm = 3：0.3 GPU-h。 |
| 6 | **骨元素型式**：tet4 → `ut4`（節點積分，同一網格）或 tet10（自由度 ×4–5）；灌注層交界加一層可變形過渡或把 pot 改成 tied 剛體面。 | 低–中：骨是受害者，改骨只讓它「晚一點被翻」；ut4 對剛體交界有幫助但會變軟（需重做 h08/h17 驗證）。 | 中（ut4：Control 加 elem_type；tet10：重網格 + 全部驗證）。 | 速度↓（tet10 約 3–5 倍）；物理：要重新驗證 FSU 剛度對 Herron。 | 一個已通過設計（p060）插入段比較 tet4 vs ut4 剛度與時間：0.5 GPU-h。不建議現在做。 |
| 7 | **掃描/報表修正**：window_scan 的「骨元素翻轉」改用「時間上第一個出事的 domain」與「收斂步是否存在翻轉」判定；`-output_negative_jacobians` 保持 50 即可（上限是每 domain）。 | 對正確歸因高，對可計算性無影響。 | 低（h33/掃描腳本）。 | 無。 | 不需跑。 |
| 8 | **B 族設計空間**：平面籠 + 軟墊 E_soft < ~5 MPa 在 100 N 下是物理性超載（名義應力 4.4 MPa），列為設計限制而非平台限制。 | — | — | 多元：B 族的可行區縮小到 E_soft ≥ 5 MPa（p044 證明可算）。 | — |

不建議：均質化籠子材料（PI 禁止，且無關）；把皮質骨換成殼或剛體（會改掉終板順應性，影響沉陷判定）；tied contact 改 augmented Lagrangian（變慢，對鎖死無效）；網格細化皮質層（元素品質不是問題）。

建議的先導順序：#4 + #2 一起跑 p023 插入段（0.1 GPU-h，看 t=2.0 能否過）→ #3 跑 p053 插入段 + extension 視窗（0.6 GPU-h）→ 若 p053 仍在鎖死點附近發散，才需要 PI 決定 #5。#1 與 #7 不需要 GPU，可立即做。

成本依據：插入 run 在 1 GPU + 4 核約 6 min（p023，到 t 2.0）到 15.5 min（p015，到 t 3.5）；視窗 6.5–36 min；一個設計全套 ≈ 1.5–2 GPU-h。

---

## 4. 參考資料

原始碼（third_party/FEBio，版本 4.13 + 本平台補丁）：
- 負 Jacobian 丟出：`FECore/FESolidDomain.cpp:543`（det F ≤ 0）；domain 層彙整：`FEBioMech/FEElasticSolidDomain.cpp:548-574`；印出上限：`FECore/FEException.cpp:156-164`（`m_maxout` 每 domain 每次更新）；domain 依序更新：`FECore/FEMesh.cpp:1128-1135`。
- line search 砍步：`FECore/FELineSearch.cpp:200-222`（`ls_check_jacobians`，最多 `m_LSiter` = 5 次）；例外 → 步失敗：`FECore/FENewtonSolver.cpp:506-517`；重試：`FECore/FEAnalysis.cpp:505-535`；重試步長：`FECore/FETimeStepController.cpp:161-177`（aggressiveness 0 = 線性遞減）。
- 預設 tet4 積分：`FEBioXML/FEModelBuilder.cpp:57`（FE_TET4G1）。Gent：`FEBioMech/FEGentMaterial.cpp:57,132,156`。正交異向性：`FEBioMech/FEOrthoElastic.cpp:54-121,252-259`。
- 本平台補丁：`FEBioMech/FETiedElasticInterface.cpp:51,402-409,551-557`（init_time）；`FEBioMech/FESolidSolver2.cpp:1112-1119`（零 line step 不算失敗）。
- 案例產生器：`scripts/3_cage_case/h14_build_case.py`（Gent Jm 第 48/179-185 行；expand 插入 第 153-202、355-363 行；tied 第 309-315 行；control 第 316-324 行；物理視窗/剛體關節 第 448-495 行；動態設定 第 538-550 行）；視窗啟動：`scripts/5_compute/h31_split_run.py`；`-output_negative_jacobians=50`：`scripts/5_compute/h06_run_cpu_batch.py:35-37`。

FEBio 文件與論壇（網路檢索，2026-11-03）：
- FEBio 使用手冊 Control 節（time_stepper：dtmin / dtmax / max_retries / aggressiveness / cutback；`ls_check_jacobians`；元素型式 tet4 / ut4 / tet10 / tet15 的 `elem_type`）與 Materials 節（Gent：G、Jm、k；orthotropic elastic 的 E/G/ν 限制）— 與上列原始碼一致。
- 論壇：max_retries 的步長計算與文件不符（開發者說明）：https://forums.febio.org/forum/febio-forums/developers-forum/18528-calculation-of-new-time-step-size-using-max_retries ；「negative jacobians but the elements look fine」（元素看起來正常卻翻轉 = 求解器側發散）：https://forums.febio.org/forum/febio-forums/users-forum/21728-negative-jacobians-but-the-elements-look-fine ；tied contact 在曲面上的可靠性：https://forums.febio.org/forum/febio-forums/users-forum/1620-cartilage-bone-tied-contact ；OpenKnee 排錯指引（output_negative_jacobians、max_retries、壞元素定位）：https://simtk.org/plugins/moinmoin/openknee/Specifications/ModelTroubleshooting 。
- Maas et al. 2016（FEBio 的 tet10 / tet15 接觸收斂比較；tet15 優於 tet10 與 hex8）：https://pmc.ncbi.nlm.nih.gov/articles/PMC4801678 。
- Zimmerman & Ateshian 2018（FEBio 接觸：penalty + augmented Lagrangian 的病態條件說明）：https://pmc.ncbi.nlm.nih.gov/articles/PMC6056201 。
- Gent 模型（應變能在 I₁−3 → Jm 奇異；橡膠的 Jm 典型 30–100，本平台 0.7 是刻意的鎖死篩選值）：Sandia Sierra/SM 手冊 https://www.sandia.gov/files/sierra/SM_LAME_5_30/main/models/gent.html 。

中間結果：`scratchpad/bone/scan_all_runs.json`（64 個插入 run 的狀態、參數、翻轉計數、重試位置、動態步殘差）、`events_*.json`（逐筆翻轉紀錄）、`bonegeom_*.json`（翻轉骨元素的幾何與位置）。
