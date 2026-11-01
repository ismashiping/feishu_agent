# 分析节点输出预算与截断

2026-10-30。单任务：只调整分析调用的完成预算、截断分类和一次有界重试。不改检索、报告展示、飞书或 LangGraph 编排，不部署。

## 配置

本地实际模型名为 `deepseek-v4-pro`，由进程环境注入，应用不自动读取 `.env`。

提供商 Chat Completions 的 `max_tokens` 上限是 393216（384K）。这是单次生成上限，不是 1M 上下文窗口，也不作为本项目推荐值。

原先 4096 来自两处项目配置，不是模型上限：

- `LLMSettings.max_tokens` 合法范围 1–4096，代码默认 1500。
- Compose 的 `LLM_MAX_TOKENS` 默认 4096，并写入 `extra_body.max_tokens`，对该客户端的每次调用生效。

分析节点此前没有单独预算，所以可行性 JSON 在约 1.5 万字符处以 `finish_reason=length` 结束。思考已关闭，推理 token 为 0。

现在：

| 调用 | 预算 |
| --- | --- |
| 规划、筛选、普通回答 | 仍用 `LLM_MAX_TOKENS`，默认 1500，上限 4096 |
| 报告复核 | 不改 |
| 可行性分析首次 | `LLM_ANALYSIS_MAX_TOKENS`，默认 16384 |
| 仅在首次截断时重试一次 | `LLM_ANALYSIS_RETRY_MAX_TOKENS`，默认 32768，且不得小于首次预算 |

两个分析预算都必须大于 4096，并且不得超过 393216。分析调用仍关闭思考。请求剩余时间不够时不重试，也不把截断记成证据不足。

`finish_reason=length` 且本次请求的 `max_tokens` 大于共享上限时，错误码为 `analysis_output_truncated`。HTTP 状态与 `model_output_invalid` 同为 502。不补括号，不删字段，不把截断正文当成 `AnalysisResult`。规划、筛选和定义问答的 `length` 仍是 `model_output_invalid`。

用量字段缺失时记 `unknown`，不记成 0。日志只含阶段、数量、模型标识和请求 ID。

响应字节上限从 128000 调到 262144，以便 32768 token 的完成结果不被传输层提前拒绝。分析校验使用同一字节上限；其他调用的 `max_output_bytes` 默认仍是 32000。Schema 的研究重合度、技术路线、可行性和引用指针没有删减。

## 真实复验

续费前，共享预算保持 4096 时，提供商返回 HTTP 402，四题都停在规划阶段的 `generation_failed`。这不是证据不足。

续费后的复验仍使用共享预算 4096、分析首次 16384、截断重试 32768。没有再出现 402，也没有出现 `analysis_output_truncated`。三道方向题都还没有 AnalysisResult。

| 题 | 意图 | 检索 | 分析 |
| --- | --- | --- | --- |
| 肝脏亚区分割 | 未进入检索 | 规划 `extraction_failed`，规则 `relation_anchor`，字段 `concept_relations.concept_id` | 未调用 |
| 同上再跑一次 | 未进入检索 | 同一规则，响应哈希不同 | 未调用 |
| MedSAM 跨医院少样本 | feasibility | 命中 5；筛选 `screened=16,screening_failed=0,eligible=7` | `model_output_invalid` |
| 钙钛矿界面稳定性 | feasibility | 命中 5；`screened=24,screening_failed=1,screening_budget=1,eligible=21` | `model_output_invalid` |
| 什么是 nnunet | definition | 命中 1 | `not_routed` |

MedSAM 与钙钛矿的分析日志都是 `max_output=16384`、`retries=0`、`schema=rejected`、`failure_kind=analysis_rejected`。用量和正文字数都是 `unknown`，字段路径为空。这说明完成结果通过了传输层，没有因 `length` 进入 32768 重试；拒绝来自本地 `ValueError`，且该异常不是带字段位置的 Schema 校验错误。定义题没有被改成可行性分析。

更早一次把共享预算误设为 1500 的运行不作为本次结论：那次 `length` 出现在筛选阶段。

## 测试

tests/unit/test_analysis_output_budget.py 与 tests/integration/test_llm.py 覆盖独立预算、截断拒绝、非法 JSON、Schema 拒绝，以及次数和时间限制下的一次重试。离线命令 `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.pytest_evidence`：1464 passed，122 deselected，无 failed。`ruff check src tests` 与 `ruff format --check src tests` 通过。被排除项未计通过。
