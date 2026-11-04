# 檔案索引（FILE_INDEX）— 每個重要檔案在哪、是什麼、誰改它
建立 2026-11-05 02:55。路徑以舊 repo 根目錄為準；`../biocage-evo/` 是 evo repo。
規則：新增或搬動任何「決策／設定／判定程式／結果檔」時同步改這份索引；h37 的 R12 會檢查這裡列出的路徑都存在。
縮寫：hNN = `scripts/` 下編號腳本；eNN = evo repo `methods/` 下的量測方法；PI = 你。

## 1. 決策與匯報（先讀這些）
| 檔案 | 內容 | 更新者 |
|---|---|---|
| `human_study/DECISIONS.md` | 所有決策與工作紀錄，依時間附加；PI 決策標「PI DECISION」 | Claude 記錄、PI 決策 |
| `human_study/PI_PENDING_DECISIONS.md` | 等 PI 決定的事項：白話問題／選項／影響；決定後移到 DECISIONS | Claude |
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
| `scripts/8_audit/h37_qa_check.py` | QA A 層：R1–R12 機械檢查；`--quick` / `launch <dir>` / `--daemon 6`；tmux `biocage_qa` |
| `scripts/common/xplt.py`, `scripts/common/cage_geom.py` | 讀 FEBio xplt、cage 幾何 |

## 4. 判定程式（evo repo，決定誰 pass／fail）
| 檔案 | 做什麼 |
|---|---|
| `../biocage-evo/methods/e03_mu_req.py` | 每個狀態是否有效（兩層狀態過濾 NUM-14）、目標括號 |
| `../biocage-evo/methods/e04_dislocation.py` | cage 相對 C4 的剛體位移（滑出指標） |
| `../biocage-evo/methods/e05_compression.py` | 軟層壓縮量 |
| `../biocage-evo/methods/e07_interface_shear.py` | 硬／軟介面剪力（p99、軟側） |
| `../biocage-evo/ops/fric_compare.py` | 摩擦視窗：1.5 N·m 點與 intact ROM 點的位移 → `verdicts.json`（閘 4） |
| `../biocage-evo/ops/e07_batch.py` | 介面剪力批次＋3 MPa 判定 → `e07_verdicts.json` |
| `../biocage-evo/ops/collect_split.py` | 合併所有閘：tied 篩選 → 滑出 → 剪力 → radial-mix 排除 → `split/*_merged.json` |
| `../biocage-evo/ops/numconv_compare.py`, `../biocage-evo/ops/degr_compare.py` | 數值收斂、退化敏感度比較 |

## 5. 結果檔（匯報的數字只能從這裡引）
| 檔案 | 內容 |
|---|---|
| `../biocage-evo/results/method/split/best_by_design_merged.json` | 每設計每視窗最佳 tied 結果 |
| `../biocage-evo/results/method/split/comp_by_design_merged.json` | 壓縮測試合併 |
| `../biocage-evo/results/method/split/manual_overrides.json` | 人工覆寫（須有 DECISIONS 依據） |
| `../biocage-evo/results/method/fric/compare.json` | 每個摩擦視窗：reached 旗標、t_rom、u_h、posterior |
| `../biocage-evo/results/method/fric/verdicts.json` | 閘 4 滑出判定（fail／pass／open＋理由） |
| `../biocage-evo/results/method/fric/e07_summary.csv`, `../biocage-evo/results/method/fric/e07_verdicts.json` | 介面剪力值與判定 |
| `../biocage-evo/results/method/fric/eval_point_sensitivity.json` | 評估點（1.5 N·m vs ROM）敏感度 |
| `../biocage-evo/results/method/fric/c3_reactions_t3.json` | C3 在 t 3 的反力（漸放用） |
| `../biocage-evo/results/method/fric/static_release_stops_lastJ.json` | 6 個 t<3 停算 run 末態軟層壓縮（T05 檢查，≤2 %） |
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
| `human_study/qa/QA_STATUS.json`, `human_study/qa/QA_STATUS.md` | h37 最新結果（匯報前先看） |
| `human_study/qa/RETRACTED.json` | 已撤回的說法（出現在文件中即 FAIL） |
| `human_study/qa/audits/` | B 層稽核報告（`QA_AUDIT_2026-11-04.md`） |
| `human_study/qa/qa.log` | h37 daemon 日誌 |
| `.claude/agents/qa-auditor.md`, `.claude/skills/qa-audit/` | B 層 agent 與 `/qa-audit` |
| `.claude/agents/pi-report.md` | 匯報 agent（先讀 QA 狀態、數字只引結果檔） |

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
