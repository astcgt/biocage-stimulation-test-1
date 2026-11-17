# 代理設定原始檔（核心／補丁）

PI 2026-11-11 指示：代理指示分兩層，只維護一份核心。

- `core.md` — 所有模型都適用：**最終目標**＋**必守規則**＋範圍、資料來源、輸出合約。只放只有我們知道的事（決策、路徑、合約、過去錯誤留下的檢查項）。
- `patch-weak.md` — 較弱模型（Sonnet、Haiku 級）才需要的補丁：數字上限、逐步流程、範例、自我檢查清單。越強的模型越不需要；強模型（Fable、Opus）只用核心。
- `meta.json` — 每個變體的 name、model、description、要組合哪些段落。

產生方式：`python scripts/8_audit/h52_agent_prompts.py` 寫出 `.claude/agents/<name>.md`（不寫 model 欄位＝沿用工作階段的模型）與 `<name>-weak.md`（`model: sonnet`）。
**只改這個目錄，不要直接改 `.claude/agents/` 的產物**；h37 的 R18 會比對兩邊，不一致就 FAIL。改完原始檔後重跑 h52。
`.claude/` 不在 git 版本控制內（`.git/info/exclude`），新的 clone 要先跑一次 h52，R18 才會通過。

要新增等級時：加一個 `patch-<tier>.md`，在 `meta.json` 加一個 variant。
