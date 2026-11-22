# 檔案索引（FILE_INDEX）— 每個重要檔案在哪、是什麼、誰改它
建立 2026-11-05 02:55。路徑以舊 repo 根目錄為準；`../biocage-evo/` 是 evo repo。
規則：新增或搬動任何「決策／設定／判定程式／結果檔」時同步改這份索引；h37 的 R12 會檢查這裡列出的路徑都存在。
縮寫：hNN = `scripts/` 下編號腳本；eNN = evo repo `methods/` 下的量測方法；PI = 你。

## 1. 決策與匯報（先讀這些）
| 檔案 | 內容 | 更新者 |
|---|---|---|
| `human_study/DECISIONS.md` | 所有決策與工作紀錄，依時間附加；PI 決策標「PI DECISION」 | Claude 記錄、PI 決策 |
| `human_study/PI_PENDING_DECISIONS.md` | 等 PI 決定的事項：白話問題／選項／影響；決定後移到 DECISIONS | Claude |
| `human_study/PI_REPORT_2026-11-10.md` | 2026-11-10 進度與議題清單（決策優先：議題二流程選擇、軟面鎖死窗口、0.5 mm 灰區、捷徑容差；結果、進行中、失誤紀錄、參考檔案） |
| `human_study/PI_REPORT_2026-11-11.md` | 給老闆的進度報告（2026-11-11 00:3x，流程 G 批次完成後）：待決 5 項、主要發現（窗口算不出 = 重啟瞬態的跨次執行數值變異，複本 p050/p068/p084/p127 證據）、批次數字、進行中試跑、QA 戳記、失誤紀錄 | Claude |
| `human_study/PI_REPORT_2026-11-18_direction.md` | 下一輪方向選項報告（代理模型主動學習／新手導師發想／原則萃取；剪力欄位；數值項；mod 調查；homerepo） | 2026-11-18 |
| `human_study/PI_REPORT_2026-11-18_failing_labels.md` | 不合格能力標籤處理報告（12 → 6 列；三個創新方向；待決 5 項） | 2026-11-18 |
| `human_study/DESIGN_REVIEW_elastic_fingers_2026-11-20.md` | 審視 PI 2026-11-20 提案「嵌入式彈性抗遷移指狀結構」（3 幾何 × 2 整合）：手算每根力與自鎖角、與現行規則的衝突、平台限制、分級測試模型清單、PI 待答 6 問 | 2026-11-20 |
| `human_study/PI_REPORT_2026-11-20_tangou.md` | 彈勾階段 1／1b 試跑報告（每根力量、預壓力是內力、斜坡 tan(α＋φ)、C4 側籠面張開量、終板邊緣斜率；待決 4 項） | 2026-11-20 |
| `human_study/FRICTION_DEMAND_2026-11-20.md` | 籠體－終板介面需要的抓力量級（滑動 0.05–0.45 MPa、翻轉拉力 6–15 MPa）與生物膠文獻對照（PI 2026-11-20 實驗需求） | 2026-11-20 |
| `scripts/3_cage_case/h56_tangou_unit.py` | 階段 1 單根彈勾對剛性終板板的子模型（4 幾何 × 外掛／口袋；壓入、外滑、內滑、過壓三組 deck；讀夾持力、法向力、根部應變）；結果在 `human_study/al_v2/pilot_tangou/`（batch1.json 972 案例、summary.json、batch1.log） | 2026-11-20 |
| `scripts/4_postprocess/h57_face_liftoff.py` | 籠面卸載讀值：物理窗口尖峰時上下籠面前／中／後三分之一無法向應力的面積比例（結果 face_liftoff.json 在各窗口目錄） | 2026-11-20 |
| `human_study/al_v2/pilot_tangou/STAGE1_RESULTS.md` | 彈勾階段 1／1b 結果摘要（batch1_table.csv、stage1b/）與解讀 | 2026-11-20 |
| `../biocage_home/` (CLAUDE.md, README.zh-TW.md, links/, skills/, agents/, agent_prompts) | 總部目錄（homerepo 輕量版，PI 2026-11-18）：專案地圖、長期規則、連到兩倉庫與決定／索引／QA 的符號連結；不含程式與資料 | 2026-11-18 |
| `../biocage-evo/docs/ROUND2_ARCHITECTURE.md` | 下一輪演化構造細節 rev 2（代理模型主動學習 A＋分組驗證 90 %、新手／學長／導師＋設計文法＋幾何編譯器 B、原則萃取與新參數 C、多代理分工 D、創意對照評估 E；QA R21–R25 提案） | 2026-11-18 |
| `../biocage-evo/ops/descriptors.py` | 由模型檔（h12 網格 npz）計算 12 個幾何描述量（任何材料分布圖都算得出；估算器與原則萃取共用） | 2026-11-18 |
| `../biocage-evo/ops/geom_compile.py`, `../biocage-evo/ops/geom_compile_test.py`, `../biocage-evo/docs/DESIGN_GRAMMAR.md`, `../biocage-evo/results/grammar/acceptance_2026-11-18.json` | 設計文法與幾何編譯器 v0：在既有格子上重新標記實心與材料（不改 h12／h14）；驗收：78 個 A 型模型檔逐元素重現 | 2026-11-18 |
| `../biocage-evo/ops/propose_round.py`, `../biocage-evo/results/round2/dryrun_2026-11-18/proposals.json` | 估算器組挑設計程式與試跑名單（未啟動）；權重 固定餘裕 80：空間 20 | 2026-11-18 |
| `../biocage-evo/ops/principles.py`, `../biocage-evo/docs/DESIGN_PRINCIPLES.md`, `../biocage-evo/results/principles/features_2026-11-18.json` | 原則萃取：27 個特徵與各目標的家族內相關、新特徵留用檢驗（事前宣告） | 2026-11-18 |
| `../biocage-evo/results/round2/prereg.json`, `../biocage-evo/ops/grammar_random.py` | 第二輪事前鎖定的評估指標（各組、基準、新穎距離門檻、檢定、可偵測差距）與亂數對照組抽樣器 | 2026-11-18 |
| `../biocage-evo/roles/prompts/naive.md`, `tagger.md`, `senior.md`, `mentor.md` | 創意組四個角色的任務說明（尚未執行） | 2026-11-18 |
| `../biocage-evo/ops/surrogate_fit.py` | 估算器驗證門：高斯過程、名目涵蓋率 90 %、依設計分組留出與整個家族留出、交叉保形校正；只讀判定檔 | 2026-11-18 |
| `../biocage-evo/results/surrogate/validation_2026-11-18.json`、`loo_predictions_2026-11-18.csv`、`posthoc_2026-11-18_mu_req_pass_type.json`（事後檢驗：篩選算法類型當輸入）（`*_run1_superseded.*` = 目標標錯的第一次執行；`*_run2_preaudit.*` = 稽核前的第二次執行；皆已取代） | 估算器分組驗證報告（實際涵蓋率、區間寬度、平均絕對誤差／均方根誤差、各家族、新家族）與逐筆預測 | 2026-11-18 |
| `human_study/FILE_INDEX.md` | 本檔 | Claude |
| `human_study/PROGRESS_REPORT_2026-10-31.md` | 上一份進度報告（人體模型轉向後） | Claude |
| `human_study/README.md` | human_study 總說明 | Claude |
| `human_study/CAPABILITY_SCORECARD.md` | 能力標籤計分表（h33 由 platform_capabilities.json 產生，不手改） | h33 |
| `human_study/platform_capabilities.json` | 能力標籤的真實來源：checks（PHY/NUM/OBS/DIV…）、restrictions（R01–R11）、components、status | Claude（h33 讀） |
| `human_study/PLATFORM_CAPABILITIES.md` | 標籤制度說明 | Claude |
| `human_study/CAPABILITY_GAPS_2026-11-02.md`, `human_study/AUDIT_TODO_2026-11-01.md` | 歷史稽核清單 | 歷史 |
| `human_study/BONE_INVERSION_ANALYSIS_2026-11-03.md` | 骨元素翻轉分析 | Claude |
| `human_study/WINDOW_SCAN_2026-11-03.md`, `human_study/window_scan.json` | h34 視窗掃描結果 | h34 |

## 2. 設定（決定模擬怎麼建）
| 檔案 | 內容 |
|---|---|
| `human_study/current_settings.json` | 每個 case 類別（如 `human_study/al_v2/physio_fric3/`）鎖定的參數：接觸型式、mu、nonsym、physio_split、physio_dynamic（密度）、physio_rot_rad；pilot 類別也在此。h24 會比對 |
| `human_study/frame_c3c4.json`, `human_study/icr_c3c4.json` | C3-C4 座標系與瞬時轉軸 |
| `human_study/fsu/` | C3-C4 功能單元網格（`C34_fsu_refined.feb/.json`） |
| `human_study/scheduler_tuning.json`, `human_study/resources_ledger.json` | 排程器資源設定與帳 |

## 3. 建模與執行流程（scripts/）
| 腳本 | 做什麼 |
|---|---|
| `scripts/3_cage_case/h12_cage_mesh.py` | cage 網格（含材料分區 npz） |
| `scripts/3_cage_case/h14_build_case.py` | 由參數建 FEBio case（.feb）；所有物理假設在此 |
| `scripts/3_cage_case/h30_split_windows.py` | 把生理視窗拆成獨立 restart 子 run（w_flexion 等） |
| `scripts/5_compute/h24_preflight.py` | 起跑前檢查（設定一致、重建一致、h37 launch gate）；tmux `biocage_preflight` |
| `scripts/5_compute/h19_scheduler.py` | FIFO 排程（讀 `human_study/queue/` 下的 .job 檔）；tmux `biocage_sched` |
| `scripts/5_compute/h31_split_run.py` | job 內：主 run → 各視窗 |
| `scripts/5_compute/h23_watchdog.py` | 卡住／死掉偵測重啟；tmux `biocage_watchdog` |
| `scripts/5_compute/h18_run_gpu_case.py`, `scripts/5_compute/kill_febio.sh` | 單 case GPU 執行、殺 run |
| `scripts/5_compute/h36_nas_archive.sh` | 完成組搬 NAS 並留 symlink |
| `scripts/6_active_learning/h28_physio_prerun.py` | 批次建 case＋preflight＋排隊；用法 `h28 <workers> physio_rot al_v2/<class> <prefix> <ids> <prev|-> '<EXTRA json>'` |
| `scripts/6_active_learning/h22_active_learning.py` | 主動學習取樣（設計參數） |
| `scripts/8_audit/h33_capability_audit.py` | 由 platform_capabilities.json 產生計分表、過期判定 |
| `scripts/8_audit/h34_window_scan.py` | 視窗狀態掃描 |
| `scripts/8_audit/h45_mu_face_scan.py`, `scripts/8_audit/h46_mu_figs.py` | 黏死篩選摩擦下限：逐窗口單面需求與張力掃描（只讀結果）；poster 圖與不足圖 |
| `scripts/8_audit/h44_multiagent_loop_fig.py` | 多代理對抗迴圈 4:3 圖（角色間誰交什麼、誰挑戰誰、誰決定） |
| `scripts/8_audit/h42_cage_design_ideas_fig.py`, `scripts/8_audit/h43_methodology_fig.py` | cage 設計概念圖（12 類各一代表）、方法論圖（需求、流程、多代理、篩選） |
| `scripts/8_audit/h41_main_results_figs.py` | 主要成果兩張圖（模型驗證＋149 設計篩選；為何沒有設計全過），只讀結果檔 |
| `scripts/8_audit/h39_gpufe_newton_reverify.py` | gpufe 基準題用現行 Newton 求解器重跑（彎曲桿、滑動、黏著、定力保持）；不跑 FEBio，不寫 evo repo 的 results/ |
| `scripts/8_audit/h40_gpu_solver_fig.py` | GPU solver vs FEBio 白話版圖（只讀結果檔） |
| `scripts/8_audit/h38_febio_agreement_fig.py` | 平台 vs FEBio 貼合度圖與等效性檢定（只讀結果檔，不跑求解器）；`--rescan` 重掃相同輸入配對 |
| `scripts/8_audit/h37_qa_check.py` | QA A 層：R1–R18 機械檢查；`--quick` / `launch <dir>` / `--daemon 6`；tmux `biocage_qa` |
| `scripts/8_audit/h57_rebuild_sweep.py`, `human_study/qa/rebuild_sweep.json` | 重建比對：判定來源各集合抽樣，以現行 h14／h30／設定重建模型檔與窗口重啟檔，逐位元比對（能力標籤重評依據） |
| `scripts/8_audit/h58_metric_regression.py`, `human_study/qa/metric_regression.json` | 指標回歸：現行 e03／e04／e05 重算既存結果檔抽樣並逐項比對 |
| `scripts/8_audit/h59_design_field_check.py`, `human_study/qa/design_field_check.json` | 材料分佈自動比對（DIV-02）：每個籠體元素的材料區塊 = 0.2 mm 設計場值 |
| `scripts/8_audit/h60_fric_winner_scan.py`, `human_study/qa/fric_winner_scan.json` | 今日摩擦判定來源窗口的狀態有效性掃描（以判定程式本身；NUM-04／NUM-14 摩擦） |
| `human_study/qa/audits/QA_AUDIT_2026-11-21.md`, `human_study/qa/audits/QA_AUDIT_2026-11-21b.md`（複查）, `human_study/qa/h24_guard_test.json` | 2026-11-21 層 B 稽核報告（能力標籤重評、摩擦係數 0.3 實作）；h24 守門對值為 0 的試算選項的反向測試 |
| `scripts/8_audit/h61_bone_strain_check.py`, `human_study/qa/bone_strain_check.json` | 停算窗口最後一個收斂狀態的骨頭變形量（體積比、主應變）對照紀錄檔中的翻轉值（NUM-06；PI 2026-11-22 的提問） |
| `scripts/8_audit/h62_weak_spots.py`, `human_study/qa/weak_spots.json`, `human_study/WEAK_SPOTS.md` | 弱點登記表（PI 2026-11-22）：每次停算記錄先讓步的材料、位置（貼哪一面、第幾層、方位、座標）、動作與轉角、被波及的骨頭位置，附一行明確標籤；停算不作設計判定（使用限制 R18） |
| `scripts/5_compute/wait_quota.sh` | 等帳號 CPU 配額（32 核心）有空再啟動；各通道腳本在每次啟動前呼叫 |
| `human_study/WINDOW_SCAN_2026-11-21.md` | h34 重掃 916 窗口（含重啟集合） |
| `scripts/8_audit/h38_project_status.py`, `human_study/PROJECT_STATUS.md` | 專案狀態頁（PI 2026-11-18 議題 A7）：只從結果檔產生的白話一頁（設計分類、真實摩擦、估算器驗證、品質保證、計分表、機器、倉庫同步），每個數字附來源檔與時間 |
| `scripts/common/xplt.py`, `scripts/common/cage_geom.py` | 讀 FEBio xplt、cage 幾何 |

## 4. 判定程式（evo repo，決定誰 pass／fail）
| 檔案 | 做什麼 |
|---|---|
| `../biocage-evo/methods/e08_subsidence.py`, `../biocage-evo/ops/e08_batch.py`, `../biocage-evo/results/method/e08/` | 骨頭下陷起始讀值（PI 2026-11-19 補測試第 1 項；h15 終點 b：足印下 3 mm 海綿骨降伏體積 > 10 %，Morgan & Keaveny 2001）：43 個通過／灰區設計的黏死與摩擦判定狀態；summary.json；壓縮／拉伸分開 |
| `../biocage-evo/methods/e09_pushout.py`, `scripts/5_compute/h53_push_restart.py`, `human_study/al_v2/pilot_push/` | 推出試驗（PI 2026-11-19 補測試第 3 項；S9 往後 ≥ 135 N；仿 ASTM 草案 F04.25.02.02）：從正式摩擦插入存檔重啟、推前牆或後牆節點 3 mm；推力主值 = cage 整體受力平衡（上下兩面接觸力合力；2026-11-19 改，元素應力反算只有約 0.6–0.87 倍，留作下限）；試跑 p062 往後 96 N、往前 114 N |
| `../biocage-evo/methods/e10_cycles.py`, `human_study/al_v2/pilot_cyc3/`, `human_study/al_v2/pilot_cyc3r/` | 每方向 3 個循環（補測試第 4 項；S9 位移不能逐步累積）：h14/h30 的 window_cycles 鍵把屈曲窗口改成 n 個屈伸循環；e10 讀每次回中立位的 cage 位置（基準 = 繪圖檔 t 3.5）；cyc3 = 正式摩擦算法參考、cyc3r = 黏滯記憶（正式判定用法）；試跑 p062；2026-11-22 讀值改為「峰值時刻 ±0.25 秒內的極值」與「回中立內插」，雜訊下限 峰值 0.03／回中立 0.01 mm（p124 時間步對照實測），舊結果在 `../biocage-evo/results/method/e10/before_20261122_peakread/` |
| `scripts/3_cage_case/h55_astm_f2077.py`, `../biocage-evo/methods/e11_astm.py`, `human_study/al_v2/astm_f2077/` | ASTM F2077-24 式剛性夾板靜態測試（補測試第 2 項、PI 決定 6）：cage 單獨夾在兩塊剛體間，壓縮／45° 壓剪／扭轉（100 N 預壓）；報勁度與硬相應力替代降伏（不是標準的 2 % 偏移降伏）；batch.sh 跑 43 個設計 |
| `human_study/al_v2/astm_f2077_plastic/` | ASTM 夾板測試彈塑性版（PI 決定 8 乙）：h55 第 5 個參數 WE＝不降伏鍵比例（硬化斜率），反應式塑性、降伏 6/9/12/15 MPa 依硬相比例；先跑 p062 |
| `human_study/al_v2/astm_f2077_plastic_hard/`, `astm_f2077_plastic_perfect/`, `astm_f2077_mesh/` | ASTM 彈塑性正式版（只硬相降伏、硬化 2 %，全部設計；lane.sh）、p062 無硬化對照、p062 細網格敏感度（彈性＋彈塑性） |
| `human_study/al_v2/pilot_cyc3v/`, `pilot_cyc3vr/`, `pilot_cyc3vG/` | 三循環以正常活動範圍幅度（window_cycles scale 0.8，PI 決定 5）跑前 10 名＋p062；lanes.sh 每張 GPU 一條 |
| `human_study/al_v2/pilot_cyc3vdt/`, `pilot_cyc3vnum/`, `pilot_cyc3vpen/` | 三循環數值檢查（PI 決定 10）：同插入檢查點，只改窗口——時間步上限壓到 0.001 秒（window_dt 0.001，約原步數 3 倍；原 0.025 半步版效果太小已撤）／籠接觸罰則加倍（重啟檔重定義負載曲線 16）；p062、p124；run_one.sh、lanes.log |
| `human_study/al_v2/pilot_push/push2_lane.sh`, `pilot_push*/p*/w_push_post2/` | 推出試驗「整顆帶著走」版（h53 add2：前後牆同時給位移），修正單牆推法把牆推扁的問題；`push2_retry.sh` = 第一步就失敗者以小步長＋全牛頓法重試；彙整 `../biocage-evo/ops/push2_summary.py` → `results/method/e09/push2_summary.json` |
| `human_study/PI_REPORT_2026-11-21_labels_tests.md` | 給 PI 的報告：能力標籤修補結果、新測試可行性表、待決事項 11–17 |
| `human_study/al_v2/pilot_mu03rN/`, `pilot_mu03GrN/`, `pilot_mu03/drive_mu03rN.sh` | 全牛頓法試算：摩擦係數 0.3 下停算的 11 個窗口以 window_max_ups 0 從同一存檔重跑（非判定來源，供 PI 決定） |
| `human_study/al_v2/pilot_staticR/`, `pilot_staticR_run.sh` | NUM-08 摩擦：p062 路線 E 窗口靜態步對慢速動態 |
| `human_study/al_v2/pilot_cyc8v/`, `pilot_cyc8vrN/`, `pilot_cyc8vGN/`, `pilot_cyc8v/lanes8.sh` | 8 圈前屈－後伸試算（PI 決定 14：看是否達到穩定態）：p124、p036（正式插入＋路線 E 全牛頓窗口）、p140（流程 G）；讀值 e10 的 steady_state 分類 |
| `human_study/al_v2/pilot_mu03/drive_newton_confirm.sh` | 全牛頓法成為正式窗口設定（PI 決定 12）的確認：5 個已通過設計兩個窗口重算，與擬牛頓法讀值比對 |
| `human_study/al_v2/numconv_hz01/build16b.py`, `lane16b.sh`, `../biocage-evo/ops/num16_multi.py` | 介面剪力「0.5 mm 塊平均」定義的多設計細網格驗證（PI 決定 16(b)）：p036、p052、p060、p113＋既有 p062 → `results/method/numconv/num16_multi.json` |
| `human_study/al_v2/numconv_hz01/build16c.py`, `lane16c.sh`, `numconv_hz01/inplane/` | 第 16(b) 項第二輪（2026-11-22 更正）：交錯（interleave）籠體的平面方向加密（檢查垂直交界面）＋ p146 厚度方向加密；`build16c.py z`（列印層厚維持 0.2 mm 的厚度加密）被 h24 擋下，待 h12 加選項。比對程式 `num16_multi.py` 第二版：兩類交界面、面數防呆、兩種分塊（柱／0.5 mm 方塊） |
| `../biocage-evo/ops/precision_budget.py` → `results/method/fric/precision_budget.json` | PI 第 19 項：判定讀值（判定點的後方平移）的數值不確定度預算（GUM 合成、U95、ISO 5725 重複性限、JCGM 106 保護帶比較、距線 U 內的設計清單、排除項與理由、參考文獻） |
| `../biocage-evo/ops/resume_daemons.sh` | 重開機後帶回看門狗的啟動檔（2026-11-22 自 resume_all.sh 拆出；能力元件 OPS 的一部分） |
| `../biocage-evo/results/round2/prereg_amendment_2026-11-22a.json` | 第二輪演化事前鎖定設定的修訂：提案程式摩擦係數 0.35 → 0.3（PI 決定 17） |
| `human_study/al_v2/pilot_mu03/build_e.py`, `drive_mu03r_d.sh`, `drive_mu03r_e.sh` | 摩擦係數 0.3 補算：d = 可能跨線的 29 個設計（已完成）；e = 其餘仍為 0.35 的 23 個設計 |
| `human_study/al_v2/pilot_pushG/`, `pilot_push/push_batch.sh` | 推出試驗排名批次（PI 決定 4 = 乙）：流程 G 設計放 pilot_pushG；每個設計跑前才建案例 |
| `human_study/al_v2/pilot_mu03G/`, `pilot_mu03Gr/`, `pilot_mu03/drive_mu03r_b.sh`, `pilot_mu03/drive_mu03G.sh` | 摩擦係數 0.3 邊界設計重跑（PI 決定 7 = 甲′）：9 個一般設計＋p061（流程 G） |
| `human_study/al_v2/pilot_fl250/`, `pilot_fl250r/`, `pilot_lbar/`, `pilot_lbarr/` | 250 N 跟隨壓力、側彎與旋轉試跑（補測試第 5 項）；無 r 的兩組窗口誤用正式摩擦算法（h18→h31 不套 restart_env），r 版用 h51 以黏滯記憶從同一插入存檔重跑 |
| `human_study/al_v2/pilot_mu03/`, `pilot_mu03r/`, `pilot_mu03/drive_mu03r.sh` | 摩擦係數 0.3 抽 5 個設計重跑（PI 2026-11-19 選乙）：mu03 = 正式流程插入、mu03r = h51 黏滯記憶屈伸窗口；與 0.35 正式結果配對比較 |
| `../biocage-evo/methods/e03_mu_req.py` | 每個狀態是否有效（兩層狀態過濾 NUM-14）、目標括號 |
| `../biocage-evo/methods/e04_dislocation.py` | cage 相對 C4 的剛體位移（滑出指標） |
| `../biocage-evo/methods/e05_compression.py` | 軟層壓縮量 |
| `../biocage-evo/methods/e07_interface_shear.py` | 硬／軟介面剪力（p99、軟側） |
| `../biocage-evo/ops/fric_compare.py` | 摩擦視窗：1.5 N·m 點與 intact ROM 點的位移 → `verdicts.json`（閘 4）；2026-11-20 起摩擦係數 0.3 為正式值（pilot_mu03r／pilot_mu03Gr 優先，0.35 讀值留在 mu035 欄，邊界 ±0.005 mm 標示，PI 決定 9） |
| `../biocage-evo/ops/e07_batch.py` | 介面剪力批次＋3 MPa 判定 → `e07_verdicts.json` |
| `../biocage-evo/methods/e06_hard_stress.py` | 硬相持續應力讀值（e06，OBS-01；18 % × sig_hard 暫定門檻，只記錄不判定） |
| `../biocage-evo/ops/obs01_batch.py` | OBS-01 批次：T19（最後方點、硬體素剛體擬合，在 e04 內）＋ e06 跑遍黏死與摩擦勝出窗口 → `results/method/obs01/` |
| `../biocage-evo/ops/shortcut_consistency.py` | PHY-05 捷徑一致性：tied mu_req_max vs 摩擦後方位移（等級相關、線性殘差、灰帶）→ `shortcut_consistency.json` |
| `../biocage-evo/ops/num16_metric_check.py` | NUM-16：正式網格 vs 細網格的介面剪力統計量比較（逐面 p99 vs 0.5 mm 塊平均）→ `results/method/numconv/num16_metric_check.json` |
| `../biocage-evo/ops/collect_split.py` | 合併所有閘：tied 篩選 → 滑出 → 剪力 → radial-mix 排除 → `split/*_merged.json` |
| `../biocage-evo/ops/numconv_compare.py`, `../biocage-evo/ops/degr_compare.py` | 數值收斂、退化敏感度比較 |
| `../biocage-evo/docs/GPUFE_VERIFICATION_PLAN.md` | gpufe 驗證計畫：V1–V23、門檻、真相來源、文獻、停損點 |

## 5. 結果檔（匯報的數字只能從這裡引）
| 檔案 | 內容 |
|---|---|
| `../biocage-evo/results/method/split/best_by_design_merged.json` | 每設計每視窗最佳 tied 結果 |
| `../biocage-evo/results/method/split/comp_by_design_merged.json` | 壓縮測試合併 |
| `../biocage-evo/results/method/split/manual_overrides.json` | 人工覆寫（須有 DECISIONS 依據） |
| `../biocage-evo/results/method/fric/compare.json` | 每個摩擦視窗：reached 旗標、t_rom、u_h、posterior |
| `../biocage-evo/results/method/fric/verdicts.json` | 閘 4 滑出判定（fail／pass／open＋理由） |
| `../biocage-evo/results/method/fric/e07_summary.csv`, `../biocage-evo/results/method/fric/e07_verdicts.json` | 介面剪力值與判定 |
| `../biocage-evo/results/method/obs01/` | OBS-01 讀值：每勝出窗口的 T19 與 e06 json、`obs01_summary.json` |
| `../biocage-evo/results/method/obs01/e06_location_check.json` | e06 高應力元素是否在硬軟介面（三個窗口的檢查） |
| `../biocage-evo/results/method/numconv/num16_metric_check.json` | NUM-16 網格比較結果（p062 前屈） |
| `../biocage-evo/results/method/fric/shortcut_consistency.json` | PHY-05 捷徑一致性重算（73 設計，2026-11-18） |
| `../biocage-evo/results/method/split/div04_noncomputable_bias.json` | DIV-04：算不出設計在家族／梯度／製法／E_soft 分位的比例（149 設計） |
| `../biocage-evo/results/method/fric/eval_point_sensitivity.json` | 評估點（1.5 N·m vs ROM）敏感度 |
| `../biocage-evo/results/method/fric/c3_reactions_t3.json` | C3 在 t 3 的反力（漸放用） |
| `../biocage-evo/results/method/fric/static_release_stops_lastJ.json` | 6 個 t<3 停算 run 末態軟層壓縮（T05 檢查，≤2 %） |
| `human_study/figures/mu_requirement/` | h46 輸出：`fig_mu_poster`、`fig_mu_gaps`（pdf/png/svg）、`fig_mu_legends.md`、`mu_face_scan.json`（505 窗口）、`figure_numbers.json` |
| `human_study/figures/main_results/` | h41 輸出：`fig1_model_and_screen`、`fig2_why_none_pass`、`fig3_cage_design_ideas`、`fig4_methodology`、`fig5_multiagent_loop`（pdf/png/svg）、`figure_legends.md`、`fig3_fig4_legends.md`、`figure_numbers.json`、`fig3_representatives.json` |
| `human_study/figures/gpu_solver_agreement/` | h40 輸出：`fig_gpu_solver_vs_febio.pdf/.png/.svg`、`figure_legend.md`、`process_table.csv`、`group_tests.json`；`newton_reverify/`（h39 結果）、`gate2_fine/`（第 2 關細步長重跑） |
| `human_study/figures/febio_agreement/` | h38 輸出：`fig_febio_agreement.pdf/.png/.svg`、`figure_legend.md`、`equivalence_tests.csv`（每列檢定）、`figure_data.json`（配對與 gate 2 紀錄）、`same_input_scan.json`（輸入雜湊掃描）、`gate2_rerun_20261105/`（gpufe gate 2 今日重跑紀錄，未覆蓋 evo repo 的 results/） |
| `../biocage-evo/results/method/fric/retired_wrong_faces_20261104/` | 作廢的舊介面版 e07 輸出（勿引用） |

## 6. 模擬資料夾（human_study/al_v2/）
命名：`pNNN` 是未跑的建置副本，`pNNN_gpuK`（或無後綴但有 case.log）才是跑過的；視窗在其下 `w_flexion/`、`w_extension/`。
| 資料夾 | 內容 |
|---|---|
| `human_study/al_v2/physio_fric3/` | 生產（1e-6 版）：70 個通過 tied 的設計，摩擦前屈＋後伸；PI 2026-11-05 第 8 項後為「偏低 12–26 %」的歷史依據 |
| `human_study/al_v2/physio_fric4/`, `human_study/al_v2/physio_fric4dt/` | 新生產參考：真實密度 1e-9、不漸放（fric4dt = 時間步 0.025 收斂對照）；先 5 設計收斂，再全量 |
| `human_study/al_v2/physio_fric/`, `human_study/al_v2/physio_fric2/` | 早期摩擦 run（六向） |
| `human_study/al_v2/physio_rot_split2/`…`split4/` | tied 篩選主力（分視窗） |
| `human_study/al_v2/numconv_dt/`, `numconv_hz01/`, `numconv_pen05/`, `numconv_pen20/` | 數值收斂（時間步、網格、罰則） |
| `human_study/al_v2/physio_degr010/`, `physio_degr020/`, `physio_degr050/` | 退化敏感度（E_soft ×0.1/0.2/0.5） |
| `human_study/al_v2/pilot_c3rampR9/` | pilot：真實密度 1e-9＋C3 漸放（p061 p062 p083 p120 p129） |
| `human_study/al_v2/pilot_c3ramp2/` | pilot：生產密度 1e-6＋漸放（p062 重現生產；其餘在 t 3.05 停） |
| `human_study/al_v2/pilot_rho9/` | pilot：真實密度、不漸放（p048 p061 p068 p062） |
| `human_study/al_v2/pilot_c3rampS/` | pilot：純靜態＋漸放（已放棄） |
| `human_study/al_v2/pilot_dynrel/`, `pilot_static/`, `pilot_c3ramp/`, `pilot_tie/`, `pilot_tie3/` | 早期 pilot |
| `human_study/al_v2/*_invalid*/`, `human_study/al_v2/cases_invalid/` | 作廢 run（保留供追溯） |
| `human_study/queue/` | job 檔（待跑在根目錄，執行中 `human_study/queue/running/`，完成 `human_study/queue/done/`，失敗 `human_study/queue/failed/`） |
| `human_study/verify_patch/`, `human_study/verify_patch3/` | FEBio 補丁回歸測試案（NUM-10，2026-10-21 基準） |
| `human_study/verify_patch_20261105/` | NUM-10 重跑（2026-11-03 重編執行檔）：fsu 六向＋C0-C7 前屈／後伸，與 10-21 基準比對 |

## 7. QA 系統
| 檔案 | 內容 |
|---|---|
| `human_study/qa/QA_SYSTEM.md` | 兩層 QA 設計說明 |
| `human_study/qa/QA_SPEC.json` | B 層登記表：每條決策 ↔ 程式位置 ↔ 狀態（符合／不符／未實作／實作時自選／PI待決） |
| `human_study/qa/audits/QA_AUDIT_2026-11-13.md` | 層 B 稽核 2026-11-13 04:1x–04:4x（DECISIONS 2026-11-11 14:44 至 2026-11-13 04:07）：5 條不符（fric_compare 勝出規則未看是否到達評估點、繼承後頂層殘留鎖死欄位、DIV-03／OBS-10／NUM-17 標籤數字過期）→ 04:5x 修正；登記表 242 條 | qa-auditor |
| `human_study/qa/audits/QA_AUDIT_2026-11-17.md` | 層 B 稽核 2026-11-17 04:1x（路線 E 重跑後狀態）：7 條不符（第一增量 0→1、流程 G／生產分項計數、ROM 窗口數、window_drive 欄、DIV-03 TIED 數字、NUM-13 退回部分、窗口數文字）→ 同日修正；新待決：PASS 類是否排除摩擦 fail | qa-auditor |
| `human_study/qa/audits/QA_AUDIT_2026-11-17b.md` | 第 B 層稽核（2026-11-18 02:03）：邊界灰區規則、p102／p149 完成、簽結 S7/S8/26(c)；5 不符（p093 灰區清單假句、p149 步數敘述、「唯一窗口」聲稱、標籤規則欄位、DIV-03 TIED 數字）| 2026-11-18 |
| `human_study/qa/QA_STATUS.json`, `human_study/qa/QA_STATUS.md` | h37 最新結果（匯報前先看） |
| `human_study/qa/RETRACTED.json` | 已撤回的說法（出現在文件中即 FAIL） |
| `human_study/qa/audits/` | B 層稽核報告（`QA_AUDIT_2026-11-04.md`） |
| `human_study/qa/qa.log` | h37 daemon 日誌 |
| `.claude/agents/qa-auditor.md`, `.claude/agents/qa-auditor-weak.md`, `.claude/skills/qa-audit/` | B 層 agent（h52 產物；`-weak` 為 Sonnet 級變體）與 `/qa-audit` |
| `.claude/agents/pi-report.md`, `.claude/agents/pi-report-weak.md` | 匯報 agent（h52 產物；先讀 QA 狀態、數字只引結果檔） |
| `human_study/agent_prompts/` | 代理設定原始檔：每個代理的 `core.md`（所有模型：最終目標＋必守規則）、`patch-weak.md`（較弱模型補丁）、`meta.json`；只改這裡 |
| `scripts/8_audit/h52_agent_prompts.py` | 由原始檔產生 `.claude/agents/*.md`；`--check` 比對（h37 R18） |

## 8. FEBio
| 檔案 | 內容 |
|---|---|
| `febio_patches/` | 對 FEBio 4.13 的補丁 |
| `febio_cudss/` | cuDSS GPU 求解器整合 |
| `human_study/febio_rebuild_2026-11-03.log`, `human_study/febio_cmake_opts_2026-11-03.txt` | 最近一次重編 |

## 9. 暫存（session 結束可能消失；重要的要搬進 repo）
scratchpad `/tmp/claude-1024/-raid-jupyter-alz-ee09-projects-claude-work-biocage-simulation-test-oct2026/d99ba160-8118-43e3-9211-3a3e1396acb6/scratchpad/`：
`p062_control_eval.py`（p062 對照評估；數字已抄進 DECISIONS 11-05 02:55）、`qa_sim/`、`qa_verdict/`、`qa_labels/`（三份稽核原稿）、
`current_settings.backup_1415.json`、`platform_capabilities.backup_1450.json`（11-04 修改前備份）。

## 10. 記憶（Claude 的跨 session 規則）
`/raid/jupyter-alz.ee09/.claude/projects/-raid-jupyter-alz-ee09-projects-claude-work-biocage-simulation-test-oct2026/memory/MEMORY.md`

## 2026-11-08 新增（重啟保持試算、FEBio 補丁 7）
| 檔案 | 內容 | 更新者 |
|---|---|---|
| `scripts/5_compute/h47_restart_pilot.py` | 重啟保持試算：從既有 t 3.5 存檔（pilot_holdA／holdE）重啟後伸窗口，用補丁版 FEBio 與環境變數切換摩擦修法（`restart_env`）；build 需 h14 重建與存檔 case.feb 逐位元相同並通過 h24 | Claude |
| `scripts/5_compute/h48_fric5_batch.py`, `human_study/al_v2/physio_fric5/` | 決定 1 重算：physio_fric3 有 t 3.5 存檔的 run 以 h47 重建為 `physio_fric5/pNNN`（裸名，案例目錄即 run 目錄，無 `_gpuK` 後綴；`pNNN_params.json` 在旁），兩個窗口以黏著記憶律重啟；`run_<window>.out`、`launch_<window>.json`、`resources_<window>.json`、`stderr_<window>.log` 為每窗紀錄（2026-11-09） | Claude |
| `human_study/al_v2/pilot_relE/` | 議題二試算：release_all_dofs（釋放步把 C3 固定端六個反力一起 ramp 到零）+ physio_static_until_windows（跟隨力步靜態、窗口動態），黏著記憶律；p068、p129（原本在 t 3.05 死）、p062、p094（存活者，等價性對照）（2026-11-09） | Claude |
| `human_study/al_v2/pilot_fric5ctl/` | 議題一對照診斷：fric5 批次 9 個 solver error（軟籠面元素負 Jacobian）的同窗口對照，與 physio_fric5 完全相同但 `BIOCAGE_STICK_MEMORY=0`（舊摩擦律 + 窗口 min_residual 1e-4），由 h47 自 fric3 存檔重建；p142 前屈先跑（DECISIONS 2026-11-09 18:10） |
| `human_study/al_v2/pilot_relF/` | 議題二流程 F 試算：流程 E + `follower_in_release [2.0, 2.5]`（釋放儲存力矩前先把 100 N 跟隨壓力加滿，C3 在受壓下被釋放）；p068 先跑（DECISIONS 2026-11-09 18:35） |
| `human_study/al_v2/pilot_relE2/` | 議題二流程 E + 主 deck `min_residual 1e-4`（靜態跟隨力步的靜止位移判準陷阱；DECISIONS 2026-11-09 19:10）；p062 先跑 |
| `human_study/al_v2/pilot_relE3/` | 議題二流程 E′：只改釋放步（release_all_dofs，力矩靜態 ramp 到零）＋主 deck min_residual；跟隨力步維持正式 run 的動態，窗口自動態狀態重啟（E2 的窗口在靜態→動態切換時 R0 1.8e4 發散；DECISIONS 2026-11-09 19:35） |
| `human_study/al_v2/pilot_relF2/` | 議題二流程 F‴：E′（靜態釋放力矩、動態跟隨力步）＋ `follower_in_release [2.0, 2.5]`（釋放時同步加壓，避免 C3 在零負載下擺動 −4…−7°）；p129、p068 先跑（DECISIONS 2026-11-09 21:10） |
| `human_study/al_v2/pilot_relG/` | 議題二流程 G：F‴ ＋ `all_dynamic`（從 t 0 全程動態，不再有靜態→動態切換；切換在 100 N 下會殺掉 d 1.5 radial 設計）；p068、p094 先跑（DECISIONS 2026-11-09 22:10） |
| `scripts/5_compute/h51_relG_fallback.py`, `human_study/al_v2/physio_relG_pl/` | 流程 G 窗口的舊法則替代讀值（PI 2026-11-10 第 1 項延伸到流程 G）：黏著記憶律下在評估點前中止就反轉（軟面鎖死）的 physio_relG 窗口，從同一個 t 3.5 存檔用舊法則（`BIOCAGE_STICK_MEMORY=0`）以 h47 重跑；只作為替代來源（fric_compare `FALLBACK_SRC`、h37 R17），`+pNNN:window` 為對照窗口（量測流程 G 存檔上的法則差異）；`run_batch.log` 為驅動程式紀錄 | Claude；2026-11-11：撤銷「第一增量否決」（複本 p050/p068/p084/p127 證明那是跨次執行的數值變異）、流程 G 替代餘量改用 0.0581 mm（max 規則）、日誌加印 FEBio normal、通用模式 H51_DST/H51_KEYS |
| `../biocage-evo/ops/relG_drive.py`, `../biocage-evo/ops/relG_drive_tuning.json`, `human_study/al_v2/physio_relG/drive.log` | physio_relG 批次第二驅動程式（工頭 2026-11-10 14:55）：每 60 s 一輪，最多 5 個 run × 6 核（32 核配額），GPU 4/1/3/2，中斷的 run 目錄在原 GPU 續跑；結束標記 RELG DRIVE DONE | Claude |
| `../biocage-evo/ops/law_shift.py`, `../biocage-evo/results/method/fric/relG_law_shift.json` | 兩種摩擦律在同一存檔上的讀值差異產生器：fric3→fric5（替代讀值餘量 abs_p90 0.0431 mm 的來源；percentile 取觀測值）與 relG_pl→relG（流程 G 存檔上的轉移檢查） | Claude |
| `../biocage-evo/ops/replicate_agreement.py`, `../biocage-evo/results/method/fric/replicate_agreement.json` | 複本一致性檢查（PI 2026-11-11 決定 4 的平台面驗收）：同模型（模型檔雜湊分組）的設計在指定窗口集（預設路線 E 的 physio_fric5r／physio_relGr）讀值差距；判準 = 同評估點且差 ≤ 0.005 mm（驗證試跑看到的讀值雜訊），超過者為 [數值] 項目而非設計結果 | Claude |
| `../biocage-evo/ops/newton_confirm.py`, `../biocage-evo/results/method/fric/newton_confirm.json`, `human_study/al_v2/pilot_mu03/drive_newton_confirm.sh`, `human_study/al_v2/pilot_mu03/fill_newton_e.sh` | 全牛頓法確認（PI 2026-11-22 第 12 項）：5 個已通過設計從同一存檔以擬牛頓法與全牛頓法各算一次，判定點讀值比對（10/10 ≤ 0.0009 mm，判準 0.005 mm）；fill_newton_e.sh＝批次 e 中擬牛頓法沒算到判定點的窗口以全牛頓法補算（pilot_mu03rN／pilot_mu03GrN，紀錄 fill_N_G.log） |
| `human_study/al_v2/pilot_relGdt0/`, `human_study/al_v2/pilot_relGdt0/run_batch.log` | 試跑類別 pilot_relGdt0（2026-11-11 00:08）：流程 G 檔點以黏著記憶律重啟、窗口第一個增量步長 0.005（h30 鍵 window_dt0；dtmax 0.05 與結束時間不變），對象 = 兩種摩擦律都在第一增量中止的 12 個窗口 + 2 個對照（p068 前屈、p039 後伸）；由 h51 通用模式驅動（H51_DST=pilot_relGdt0 H51_KEYS=window_dt0=0.005），結果在各 pNNN/resources*.json 與 w_*/case.log |
| `human_study/al_v2/pilot_relGnull/`, `human_study/al_v2/pilot_relGnull/run_batch.log` | 試跑類別 pilot_relGnull（2026-11-11 00:2x）「空重啟」：流程 G 檔點以黏著記憶律重啟、旋轉驅動為零（窗口專用鍵 window_null（h30：重啟檔的 prescribe 值設 0、0.2 s 窗口 4 步；physio_hold 會改主模型檔，h47 擋下）），跟隨壓力照常；若 p050/p084/p109/p127 仍在第一增量發散而 p068 不會，根因在重啟再平衡而非驅動；對象 = 4 個第一增量失敗窗口 + p048 前屈 + 對照 p068 前屈；h51 通用模式 H51_DST=pilot_relGnull | Claude |
| `human_study/al_v2/pilot_relGnull2/`, `human_study/al_v2/pilot_relGnull2/run_batch.log` | 試跑類別 pilot_relGnull2（2026-11-11 00:5x）「無關節重啟」：window_null = nojoint，重啟步不宣告剛性關節驅動（只保留跟隨壓力、0.2 s 窗口）；pilot_relGnull（關節在、驅動 0）六個窗口含對照 p068 全部第一增量中止，此變體切分「關節接上」與「存檔重載」兩個假說；對象 p050 前屈、p068 前屈、p084 後伸 | Claude |
| `human_study/al_v2/pilot_relGdrv/`, `human_study/al_v2/pilot_relGdrv/run_batch.log` | 試跑類別 pilot_relGdrv（2026-11-11 01:0x）「驅動從目前轉角起算」：window_drive = from_state；h47 build 讀來源插入段 C3pot.txt 的 thy(3.5)，呼叫 `h30 offset` 在各 w_*/restart.feb 重新定義驅動曲線（值×曲線 = thy + 振幅×爬坡），case.feb 不動；provenance 在 pNNN/window_drive.json 與 w_*/window_drive.json。對象 p050/p068/p048 前屈、p084/p039 後伸（p039/p068 為有讀值的對照） | Claude |
| `human_study/al_v2/pilot_relGpen/`, `human_study/al_v2/pilot_relGpen/run_batch.log` | 試跑類別 pilot_relGpen（2026-11-11 01:2x）「關節改罰函數」：window_joint = {laugon 0, penalty 1e6}，重啟步的剛性關節驅動由 Lagrange 乘子（laugon 2，正式設定）改為罰函數，其他不變；測試第一增量的衝擊是否來自乘子鞍點方程（偏移驅動曲線的 pilot_relGdrv 對第一次迭代範數完全沒影響）。對象 p050 前屈、p068 前屈、p084 後伸 | Claude |
| `human_study/al_v2/pilot_relGfix/`, `human_study/al_v2/pilot_relGfixA/`（各含 run_batch.log） | 試跑類別 pilot_relGfix（2026-11-11 01:2x）= 兩個修正合併：關節罰函數（window_joint laugon 0、penalty 1e6）＋驅動從目前轉角起算（window_drive from_state）；pilot_relGfixA 同但關節用增廣拉格朗日（laugon 1、penalty 1e6、tolerance 0.01）。依據：Lagrange 乘子版（正式 laugon 2）第一次迭代的解與驅動值無關（鞍點方程在 GPU 直接解法下給出垃圾步，位移範數 1e6），罰函數版第一次迭代殘差 1e9 = 接上瞬間 0.0202 rad 的拉回 × 1e6。對象 p050 前屈、p068 前屈、p084 後伸（fix 另加 p039 後伸對照） | Claude |
| `human_study/al_v2/pilot_relGlc/`（含 run_batch.log） | 診斷試跑 pilot_relGlc（2026-11-11 01:3x）：無關節重啟 ＋ 在重啟檔重新定義跟隨壓力曲線 lc 21 為 0（鍵 window_lc_redefine）；若 C3pot.txt 的 Fz 由 −100 N 變 0，表示 FEBio 重啟檔的 LoadData 重新定義有效（pilot_relGdrv／relGfix 的偏移曲線第一次迭代完全沒變，疑似未被採用；LoadData 現改放在 Step 之前） | Claude |
| `human_study/al_v2/pilot_relGrel/`（含 run_batch.log、pNNN/w_*/window_drive.json） | 試跑類別 pilot_relGrel（2026-11-11 01:4x，路線 E）：窗口驅動改為 C3 pot 剛體的「相對」指定轉角（FEBio 2.5 格式 `<rigid_body><prescribed bc="Ry" lc=22/23 type="relative">`，啟動時以當下轉角為參考），不再用通用剛性關節（Lagrange 乘子、相對 t=0 絕對角）；曲線與振幅不變；force/moment 讀值仍由 C3pot.txt。對象 p050/p068 前屈、p084/p039 後伸 | Claude |
| `human_study/al_v2/pilot_fric5rel/`（含 run_batch.log） | 路線 E 驗證試跑（PI 2026-11-11 決定 1a）：正式插入設計的檔點（physio_fric3 插入段 dump）以黏著記憶律＋C3 剛體相對指定轉角重啟（類別 = physio_fric5 + window_drive_mode rigid_relative；h51 以 H51_SRC=physio_fric3 建案）；對象 p002 兩向、p036 前屈、p100 後伸、p026 兩向；與 pilot_relGrel（流程 G 設計 p039/p068/p048/p109/p084）合計 8 設計 13 窗口，讀值與現行判定比較後決定正式化與 142 窗口重跑 | Claude |
| `human_study/al_v2/physio_fric5r/`, `human_study/al_v2/physio_relGr/`（各含 run_batch.log、pNNN/w_*/window_drive.json） | 正式集（PI 2026-11-11 決定 1a，路線 E，2026-11-13 啟動）：全部生理窗口以「C3 剛體相對指定轉角」驅動重跑——physio_fric5r = 43 個正式插入設計（檔點 physio_fric3 插入段 dump；類別 = physio_fric5 + window_drive_mode rigid_relative），physio_relGr = 27 個流程 G 設計（檔點 physio_relG；類別 = physio_relG + window_drive_mode）；共 140 個窗口，h51 通用模式驅動（H51_SRC/H51_DST/H51_KEYS）；fric_compare／e07 最高優先集，h37 R19 守門；路線 E 算不出的窗口由關節驅動結果（標 window_drive 絕對關節／拉回）接手 | Claude |
| `human_study/al_v2/physio_relG/gpu5_incident_20261110_p061_stderr.log` | 2026-11-10 14:36 GPU 5 被其他使用者佔滿（39.7/40 GB）、cuDSS status 4 立即失敗的證據；23 個 `_gpu5` 無效目錄已刪 | Claude |
| `../biocage-evo/ops/mu_req_field.py`, `../biocage-evo/results/method/mu_req_field.json`, `../biocage-evo/results/method/mu_req_field.csv` | mu_req 場：每個設計的超參數 → 六個窗口的 mu_req（tied 篩選 mu_squeeze）、governing window、over_max／lower_bound／computable 旗標、摩擦檢查結果；ML 演化 agent 的訓練表（PI 2026-11-09） | Claude |
| `../biocage-evo/results/method/mu_req_vs_fric5.json` | （另有同名 .csv）mu_req 捷徑（tied）對 physio_fric5 金標準的一致性（43 設計）：等級相關、線性對應殘差、0.5 mm 門檻對應的 mu_req；PI 待決第 3 項（容差）資料（DECISIONS 2026-11-09 18:18、18:26） |
| `../biocage-evo/results/method/fric/e07_fric3_vs_fric5_shear.json` | 同設計同窗口 ROM 時點軟側 p99 介面剪力，fric3 vs fric5（71 對；法則效應中位 +6 %） |
| `../biocage-evo/results/method/fric/fric3_to_fric5_shift.json` | 同設計同窗口讀值位移 fric3 → fric5（74 窗口；後伸 ROM 後方、前屈 1.5 N·m）；中位 0.011、p90 0.043、最大 0.200 mm（DECISIONS 2026-11-09 18:26） |
| `scripts/8_audit/h49_insertion_equiv.py` | 議題二等價性：兩個 run 在 t 3.5 的 cage 相對 C4 位置、C3 pot 姿態與反力比較（`h49 <A> <B>`） |
| `human_study/al_v2/pilot_holdH/`, `human_study/al_v2/pilot_holdHf/` | 重啟保持試算案例（H：粗步，holdA 存檔；Hf：細步，holdE 存檔）；`launch_wave*.sh`、`wave*.log` 為各波啟動紀錄（wave 5/6：flexion 窗口，輸出為 `*_flexion.json`、`done_flexion`）；失敗波的輸出在各案例 `_wave*_fail/` | Claude |
| `human_study/al_v2/pilot_holdR/` | 路線 E（相對驅動）之下的保持段漂移試算（holdA 存檔、黏著記憶、window_min_residual、window_drive_mode rigid_relative；p062／p139 兩方向）；`launch_wave1.sh`、`wave1.log`；讀取器 biocage-evo/gpufe/verify/v17g_hold_restart.py | 2026-11-18 NUM-13 補證據 |
| `human_study/al_v2/pilot_holdRh/` | 同 pilot_holdR 但保持段步長減半（window_dt 0.025）：NUM-13 第 2 款（步長／半步長差 ≤ 0.005 mm）在路線 E 之下的證據；`launch_wave1.sh`、`wave1.log` | 2026-11-18 |
| `human_study/al_v2/pilot_holdQ/`, `human_study/al_v2/pilot_holdQR/` | 真正半步長保持插入模型（保持段 dtmax 0.025，holdE 式曲線；生產二進位、關節窗口＝生產律半步對照）與其 t 3.5 存檔的路線 E 黏著記憶重啟（QR）：NUM-13 第 2 款在路線 E 之下的證據；Q：`launch.sh`、`launch.log`；QR：`launch_wave1.sh`、`wave1.log` | 2026-11-18 |
| `human_study/al_v2/pilot_rep3/` | C2 選項乙：兩組不一致複本（p093／p145 後伸、p051／p075 前屈）的第三次計算，設定同 physio_fric5r；`launch_wave1.sh`、`wave1.log` | 2026-11-18 |
| `human_study/al_v2/pilot_rep3G/` | 全牛頓法（restart Control max_ups 0）試跑：兩個算不出的摩擦窗口 p048 後伸、p115 前屈（流程 G 存檔、physio_relGr 設定）；`launch_fullnewton.sh`、`fullnewton.log` | 2026-11-18 |
| `febio_patches/febio-4.13-biocage-patch6-stick-memory.patch` | 補丁 6+7：黏著記憶／回映；`stick_memory` 改由環境變數 `BIOCAGE_STICK_MEMORY` 開啟（參數數量與正式版一致，存檔可互讀）、`BIOCAGE_CAGE_LAUGON` 增廣拉格朗日；凍結狀態不再換接觸元素；輪廓含錨點元素 | Claude |
| `../biocage-evo/gpufe/verify/v17g_hold_restart.py`, `../biocage-evo/results/gpufe_verify/v2/v17g_hold_restart.json` | 重啟保持試算的讀數腳本與結果（對照、增廣拉格朗日、黏著記憶；起終點差與 t 3.95–4.4 線性趨勢、振幅、升降步數） | Claude |
| `../biocage-evo/gpufe/verify/v17h_block_slip_onset.py`, `../biocage-evo/results/gpufe_verify/v2/v17h_block_slip_onset.json` | 區塊滑移起始測試：位移驅動平板，摩擦力平台／庫倫極限，生產 vs 黏著記憶、兩種步長（2026-11-08） | Claude |
| `../biocage-evo/ops/restart_daemon.sh` | 重啟 evo daemon（含 foreman 閒置暫停，PI 2026-11-07 決定 6a） | Claude |
