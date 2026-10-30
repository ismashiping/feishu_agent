# AnalysisResult 失败阶段

2026-10-30。单任务：让分析节点的结构化失败能区分 JSON、Schema、业务规则和证据校验。不改检索、筛选、意图路由、分析预算或 LangGraph，不部署。

## 调用链

`EvidenceAnalyzer.analyze` 调用 `analyze_evidence`，得到字符串。随后在同一次尝试里依次做：

1. 响应类型和字节上限。
2. `json.loads`。重复键和非 JSON 常量也算解码失败。
3. `AnalysisDraft.model_validate`。
4. 论文集合、可行性维度、引用指针和来源身份等分析后检查。

这些失败原先都是 `ValueError`。`JSONDecodeError` 和普通业务 `ValueError` 都不是 `ValidationError`，所以日志只有 `schema=rejected`、`failure_kind=analysis_rejected` 和空字段路径。对外错误码仍是 `model_output_invalid`。截断仍由提供商 `finish_reason=length` 记为 `analysis_output_truncated`，不进入上述分类。

## 诊断

日志阶段仍是 `analyze`。`failure_kind` 表示失败阶段：

| failure_kind | schema_status | 含义 |
| --- | --- | --- |
| response | not_run | 响应不是字符串，或超过字节上限 |
| json_decode | not_run | 规则码 `json_decode_failed`；可记 `json_pos` |
| schema_validation | rejected | Pydantic 字段或类型错误 |
| business_validation | accepted | Schema 已通过，跨字段规则失败 |
| evidence_validation | accepted | 引用指针、用户原句或来源身份失败 |
| unknown_failure | not_run | 未分类异常，对外仍是 `model_output_invalid` |

字段路径只保留分析模型的字段名和不超过 40 的列表下标。规则码来自 `PydanticCustomError` 类型或分析后检查的固定代码，不从异常字符串推断。用量缺失记 `unknown`。不记录问题原文、模型正文、标题、检索式、密钥或异常原文。

模型校验器的拒绝条件没有放宽，只是把原来的 `ValueError` 换成稳定规则码。

## 测试

`tests/unit/test_analysis_failure_stage.py` 覆盖合法 JSON、非法 JSON、错误字段类型、业务规则、虚假引用、截断分类、未知异常和日志脱敏。

离线命令 `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.pytest_evidence`：1473 passed，122 deselected，无 failed，无 skipped。`ruff check src tests` 与 `ruff format --check src tests` 通过。被排除项未计通过。

## 真实复验

仓库里没有可复用的论文证据缓存，因此重新检索。共享预算 4096，分析预算 16384。两题都是 feasibility，各命中 5 篇。JSON 已解析，Schema 已通过，没有 `AnalysisResult`。

| 题 | 检索 | 分析 |
| --- | --- | --- |
| MedSAM 跨医院少样本 | `screened=18,screening_failed=0,eligible=6,hits=5` | `business_validation` / `reported_fact_quote` |
| 钙钛矿界面稳定性 | `screened=24,screening_failed=1,eligible=16,hits=5` | `business_validation` / `reported_fact_quote,inference_requires_verification` |

MedSAM 的字段路径是 `feasibility.2.assessment`、`studies.0.fields.intervention`、`studies.0.fields.comparison`、`studies.1.fields.intervention`、`studies.1.fields.comparison`、`studies.1.fields.limitations`。完成原因是 `stop`，输出 7334 token、29442 字符，推理 token 为 `unknown`，没有重试。

钙钛矿的字段路径是 `studies.0.fields.intervention`、`studies.1.fields.intervention`、`studies.2.fields.intervention`。完成原因是 `stop`，输出 11342 token、43974 字符，推理 token 为 `unknown`。

`reported_fact_quote` 表示被标成事实的值不是证据引文的原文，或依据不是 `text`。`inference_requires_verification` 表示推断缺少验证说明或推断依据。这两条规则没有放宽。肝脏题的 `relation_anchor` 仍是独立问题，本次未改规划。
