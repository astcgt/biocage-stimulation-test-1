# QA 系統：讓「程式做的事」持續對得上「我們決定的事」

PI 2026-11-04 指示：要有保證測試品質的 agent 定期檢查模擬方式與判定標準的程式是否符合目前方案與平台能力標籤，避免程式與實際目的不合而產生錯誤結果。

## 比喻
決策紀錄（DECISIONS.md）是「食譜」，程式是「廚房」，能力標籤（platform_capabilities.json）是「菜單上的保證」。
本週的錯誤全是三者脫節：廚房照舊食譜做（評估點用 ROM）、菜單還寫著已撤回的保證（「通過網格收斂」）、
算錯介面卻沒人對照。QA 系統就是一位每天對照三者的「稽核員」，分兩層：

| 層 | 做什麼 | 誰做 | 多快 | 失敗時 |
|---|---|---|---|---|
| A 機械檢查 `scripts/8_audit/h37_qa_check.py` | 可以用程式判斷的「回歸測試」：每條都來自本週一個真實錯誤 | 腳本（tmux `biocage_qa` 每 6 h；每個 run 起跑前 h24 呼叫 `launch` 子命令） | 秒～十幾秒 | 寫 `qa/QA_STATUS.{json,md}`；起跑門 FAIL 則該 case 不得啟動 |
| B 語意稽核 `.claude/agents/qa-auditor.md` | 「程式有沒有做到決策的意思」：需要讀決策原文和程式、下判斷 | LLM agent（可由 `/qa-audit` 叫出） | 20–40 min | 填 `qa/QA_SPEC.json` 登記表；「不符」要進 DECISIONS 並改標籤狀態 |

## A 層檢查清單（每條對應的真實錯誤）

| 檢查 | 當初的錯誤 |
|---|---|
| R1 case-dir：verdict 用的每個 run 目錄都有跑完的 case.log 與 case.xplt；同一設計不得有兩個帶 log 的 run 目錄 | 判定抓到沒跑過的 build 目錄（p110 vs p110_gpu3）→ 空洞的「通過」 |
| R2 no-pass-by-absence：gate 4、介面剪力、合併結果中每個「pass」都有 flexion＋extension 兩個可用窗口 | p072 的 extension 被丟掉後變「通過」 |
| R3 faces：每個 e07 結果的介面面數等於從 cage_elems.npz 的 FEBio block 獨立重算的面數 | e07 用網格旗標 `hard` 當材料介面，mix 設計全算在非介面上 |
| R4 insertion-state：插入值取的狀態離 t 3.5 不超過 0.05 | 取到 t 0 的狀態 |
| R5 counts：四類設計數在 DECISIONS／PLAN／scorecard 最後一次出現的數字＝重算的結果 | 26/17/13/15 過期；72/14 口頭與檔案 73/15 不一致 |
| R6 retracted：`qa/RETRACTED.json` 登記的已撤回說法不得出現在現行文件（標籤、scorecard、PLAN） | 「通過網格收斂」「≤20 %」 |
| R7 pilot-keys：production 類別與 722 個 production case 不含 pilot 選項；h14 讀取 pilot 選項時預設關閉且有 guard | pilot 選項若外洩到 production，結果不可比 |
| R8 golden-rebuild：用現行 h14 重建 p062 fric3，md5 必須等於 4f3208b5 | h14 改動是否影響 production（不等起跑才發現） |
| R9 material-blocks：cage 每種材料一個 FEBio block（production 三型抽樣＋golden） | 標準規則：材料圖不得均質化 |
| R10 register：登記表無 unmapped／不符；gate 檔案有改動或 DECISIONS 有新的 PI 決策條目 → 標「LLM audit required」 | 決策寫了、程式沒跟（評估點） |
| R18 agent-prompts：`.claude/agents/*.md` 必須等於 h52 從 `human_study/agent_prompts/`（核心＋補丁）產生的內容 | 代理設定寫死過時範圍、各檔各自漂移（2026-11-11 提示詞稽核） |

A 層只報告，不改 DECISIONS、標籤或結果檔。

## B 層：qa-auditor agent 怎麼做
1. 讀 DECISIONS.md 自上次稽核以來的條目（含 PI 原話）與 `qa/QA_SPEC.json`。
2. 對每條決策找到實作的程式行，判定 狀態 ∈ {符合, 不符, 未實作, 實作時自選（決策文沒寫，需 PI 簽核）, PI待決}。不信 docstring，只信程式路徑與結果檔。
3. 寫回 `qa/QA_SPEC.json`（每條：id、DECISIONS 行號＋原文、file:line、狀態、證據），更新 `meta.last_llm_audit`；報告存 `qa/audits/QA_AUDIT_<日期>.md`。
4. 「不符」→ 寫 DECISIONS 條目，並把相關能力標籤改為 fail／stale（platform_capabilities.json），重跑 h33。
5. 「實作時自選」→ 列成 PI 簽核清單，放進下一份匯報。

觸發時機：(a) DECISIONS 新增 PI 決策；(b) gate 檔案（以 `qa/QA_SPEC.json` 的 `meta.gate_files` 為準）有改動；(c) 任何向 PI 匯報數字之前；(d) 無事件時每週一次。R10 會把 (a)(b) 標成 WARN 提醒。

## 匯報守門
`pi-report` agent 先讀 `qa/QA_STATUS.json`：overall FAIL 或 R10 顯示稽核過期 → 匯報開頭必須寫「QA 未通過／稽核過期：以下數字未經核對」；數字一律引用結果檔與 QA_STATUS 的重算值，不用記憶中的數字。每份匯報結尾帶一行 QA 戳記（日期、overall、未過項）。

## 已安裝 / 待 PI 決定
- 已安裝：h37 腳本；h24 起跑門（OBS-08 已 reconfirmed）；tmux `biocage_qa` 每 6 h 全檢；qa-auditor agent；`/qa-audit` skill；pi-report 守門規則；RETRACTED.json；QA_SPEC.json（登記表由首次稽核填入）。
- 待 PI 決定：git pre-commit hook 跑 h37 --quick（改 repo 設定）；crontab（本帳號無權限，故用 tmux）。


## 2026-11-05 additions
- h24 step 2 compares the window restart files (w_*/restart.feb, restart_static.feb, physio_schedule.json) with the rebuild, not only case.feb (gap: stale split build with the wrong drive amplitude, p139 pilots).
- h37 R12 file index (paths listed in human_study/FILE_INDEX.md exist); R13 launch gate: window schedule rot_rad = params file / class setting.
- h37 --hook mode (pre-commit in both repos): R10 register findings reported as WARN, everything else blocking.
