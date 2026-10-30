# 分析事实与推断契约

2026-10-30。单任务：让分析生成区分逐字事实和需要验证的推断。不改检索、规划路由、LangGraph、Token 预算或校验强度，不部署。

## 契约

`AnalysisItem` 已有三种认识状态，校验器没有放宽：

- `reported_fact`：`basis=text`，`value` 必须与某一条 `evidence.quote` 逐字相同，`verification_needed` 为空。引文还必须是该来源片段的子串。
- `model_inference` 或 `unverified_hypothesis`：`basis=model_inference`，并且必须填写 `verification_needed`。值可以是分析性表述，引文仍须逐字来自证据。
- 缺失：`value` 为空，`evidence` 为空，`basis` 为 `not_reported` 或 `unknown`。

`reported_fact_quote` 在值不是引文原文，或依据不是 `text` 时触发。`inference_requires_verification` 在非事实值缺少验证说明或推断依据时触发。

单篇研究字段只能引用该论文自己的片段。比较、差距和可行性可以跨论文，但不能写成单篇事实。来源的 `content_scope` 和证据位置来自检索结果，模型不能把摘要改成全文。

## 生成

原先的说明同时要求“事实必须是原文”和“用用户语言输出”。中文改写因此进入了要求逐字匹配的 `value`。说明改为：事实值与引文保持文献语言并逐字复制；用户语言只用于推断值、相似度理由、比较理由、差距说明和下一步核查。每篇研究必须带齐方法字段，每条相似度必须带齐五个维度。

只改说明后，三题仍返回完整 JSON，但业务规则失败。因此在业务规则失败时增加一次修正：把规则码和字段路径发回同一批证据，不重检索，不提高 Token 预算，不放宽校验。证据指针失败不进入这次修正。第二次仍失败就停止。

## 测试

`tests/unit/test_analysis_epistemic_contract.py` 用影像、临床预测、材料和计算能耗四类合成证据验证同一条路径。离线命令 `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.pytest_evidence`：1488 passed，122 deselected，无 failed，无 skipped。`ruff check src tests` 与 `ruff format --check src tests` 通过。被排除项未计通过。

## 真实复验

没有论文缓存，因此重新检索。三题都没有 `AnalysisResult`。

| 题 | 结果 |
| --- | --- |
| MedSAM 跨医院少样本 | feasibility，命中 2。修正一次后仍是 `reported_fact_quote,overall_relation`。路径含 `studies.0.fields.intervention`、`studies.1.fields.population`、`studies.1.fields.intervention`、`studies.1.fields.comparison`、`idea_similarities.0`。`finish_reason=stop`。 |
| 钙钛矿界面稳定性 | feasibility，命中 5。一次修正后为 `method_fields_required,overall_relation`。路径为 studies 0–4 和 idea_similarities 0–2。`finish_reason=stop`。 |
| 图神经网络用于分子性质预测 | 规划 `extraction_failed`，规则 `expansion_not_anchor`。未进入分析。 |
