# QueryPlan 可诊断性与确定性校验

2026-10-30。单任务：只改规划校验、脱敏诊断和旧计划兼容。不改论文检索、科研报告生成或 LangGraph 图结构，不部署，不处理科研方向报告的证据缺口。

## 契约

确定性校验使用固定规则码。规划失败日志只记录 stage、failure_kind、字段路径、rule_code、response_hash。不记录用户原文、模型响应正文、密钥或异常原文。外部错误码仍为 extraction_failed 或 extraction_timeout。

来源引用必须是用户原文的连续子串。标准化检索术语与原文引用分开，不把标准化写法写回用户原句，不自动补造研究约束，不对验收题写死替换。唯一一次出现的原文引用可以重算 source_span；多次出现、缺失或大小写/标点不同继续拒绝。该重算不依赖 research_constraints 是否存在。

ExtractionDraft 与历史 QueryPlan 的 task_intent 保持可选。自动路由缺少 task_intent 记录 task_intent_required 并返回 extraction_failed，不猜测意图。

## 测试

tests/unit/test_query_plan_diagnostics.py 覆盖 schema、plan、来源规则码、日志脱敏、span 重算和旧接口。既有意图路由与 PICO 回归保持外部错误码。

先用规则码确认真实规划失败，再只修被确认的冲突。真实复验只跑规划：U-Net 原论文解释、U-Net++ 论文解释，以及至少一条此前失败的原始输入。记录规则码、是否得到 QueryPlan，以及未解决项。不把未执行或被排除的测试计为通过。

## 确认结果与修复

修复前，生产提取器在默认思考开启时三次规划都停在 stage=provider、failure_kind=model_output_invalid，规则码为空。同一请求在 max_tokens 为 1500 和 4096 时 finish_reason 均为 length，content 为空，推理 token 用尽输出预算，来源规则没有执行。历史飞书日志里的一次 schema 与两次 plan 没有留下 failure_kind 和字段路径，因为这些值只放在被日志白名单丢弃的字典里。

关闭提取调用的思考后、尚未分离术语前，三条问题都能生成 QueryPlan，且 paper_target.source_text 已是用户原文子串。因此这次真实失败不是来源引用规则。随后仍把标准化术语放到 normalized_terms、english_term 或 english_terms，引用字段保持逐字原文；自动路由缺 task_intent 继续失败。唯一原文的错误 source_span 会重算，不再要求 research_constraints 存在。冻结响应 2 只有这类错误偏移且没有 research_constraints，修复后可通过，并断言重算后的区间等于原文；响应 1 仍被拒绝。

修复后经生产提取器复验，未记录模型正文：

| 输入 | 结果 | task_intent | 来源引用 | normalized_terms 数量 | 错误码 |
| --- | --- | --- | --- | --- | --- |
| unet原始论文解释一下 | planned | paper_explanation | 是 | 2 | 无 |
| U-Net++论文解释一下 | planned | paper_explanation | 是 | 3 | 无 |
| 什么是nnunet | planned | definition | 是 | 1 | 无 |

未跑检索、回答或飞书，未部署。normalized_terms 不进入现有检索编译。回答、筛选和报告仍使用提供商默认思考。

离线命令：`.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.pytest_plan_diag`，1454 passed，122 deselected，约 195 秒。被排除项未计通过。`ruff check src tests` 与 `ruff format --check src tests` 通过。
