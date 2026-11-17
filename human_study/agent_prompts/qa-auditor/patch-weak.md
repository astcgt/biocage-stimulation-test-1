## 較弱模型補丁（Sonnet、Haiku 級才需要）
- 語意稽核建議用強模型；用較弱模型時，主工作階段要逐條複核每個「不符」與「符合」的 file:line。
- 一次只處理一條決策：讀原文 → 在程式中找到實作行 → 讀該行與前後的實際值 → 判狀態 → 寫進 QA_SPEC → 才換下一條。不要先列完所有決策再一起判。
- 第一次執行（QA_SPEC.json 的 items 為空、沒有 meta.last_llm_audit）時，處理 2026-11-03 起的全部 PI 決策條目。
- 判不出來時用「PI待決」或「實作時自選」並寫明缺什麼證據，不要猜「符合」。
- QA_SPEC 條目範例（僅示範格式，內容是虛構的）：
  `{"id": "D-20261105-2", "decisions_line": 812, "quote": "評估點改為 t 3.5", "code": ["scripts/3_cage_case/h14_build_case.py:640"], "status": "符合", "evidence": "h14:640 eval_t = 3.5", "checked": "2026-11-05 04:20"}`
