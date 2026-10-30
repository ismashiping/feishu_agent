# 科研方向检索证据追踪

2026-10-30。单任务：追查 QueryPlan 到 OpenAlex 检索、筛选、证据和分析节点的丢失点，并做最小修复。不改科研报告展示、飞书架构或 LangGraph 编排，不部署。

## 契约

标准化术语必须进入已有锚点的检索式，不能另起一个必须同时命中的新概念。`concept_mappings.english_terms` 和 `paper_target.normalized_terms` 只并入来源短语相同的概念；与锚点整词重叠的 `concept_groups` 同样并入。关系被分析焦点词滤空时，退回 `concept_groups`。论文身份、来源校验和无证据输出保持原规则，不为凑引用数加入论文。

诊断只记录阶段、失败种类和数量。不记录用户原文、检索式、题名、摘要或密钥。阶段为 compile、search、screen、select、analyze、fulltext、provider。

只命名研究主题或拟定课题，且没有要求定义、比较、解释某一篇论文或查找文献时，规划为 feasibility。显式定义、比较、论文解释和文献查找保持各自意图。不按验收题写死关键词或分支。

筛选和分析的结构化调用关闭提供商默认思考。报告复核不改。可行性分析仍使用摘要；请求分析时全文补强保持跳过，并记录 fulltext calls=0。

## 修复前

两条验收题都能从 OpenAlex 得到候选，但筛选调用全部失败，分析节点没有执行。

| 输入 | 意图 | OpenAlex 总量 | 记录 | 筛选失败 | 上下文预算外 | 命中 | 分析 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 肝脏亚区分割 | question_answer | 2231 | 38 | 11 | 24 | 0 | 未路由 |
| MedSAM 跨医院少样本医学图像分割 | question_answer | 187 | 24 | 9 | 15 | 0 | 未路由 |

筛选失败与此前规划失败相同：思考占用输出预算，正文为空，调用在进入候选判定前被拒绝。两条题都没有 `normalized_terms`，因此当时的零命中不是该字段未接线造成的。

## 修复后真实复验

输出预算与部署配置同为 4096。思考已关闭，`reasoning_tokens=0`。另用钙钛矿太阳能电池界面稳定性检查其他领域，用“什么是nnunet”检查定义不被改成可行性。

| 输入 | 意图 | 总量 | 记录 | 已筛选 | 筛选失败 | 无关 | 部分相关 | 无摘要 | 命中 | 分析 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 肝脏亚区分割 | feasibility | 17 | 16 | 13 | 1 | 4 | 3 | 2 | 5 | 已调用，输出被截断 |
| MedSAM 跨医院少样本医学图像分割 | feasibility | 75 | 20 | 14 | 1 | 3 | 6 | 5 | 5 | 已调用，输出被截断 |
| 钙钛矿太阳能电池界面稳定性 | feasibility | 850 | 29 | 24 | 1 | 7 | 1 | 4 | 5 | 已调用，输出被截断 |
| 什么是nnunet | definition | 11603 | 10 | 2 | 1 | 0 | 1 | 7 | 1 | 按定义不进入分析 |

肝脏和 MedSAM 的三次查询用途分别为 direct、direct、technical_route、bottlenecks。定义题的标准化术语进入了检索式，用途为 paper_identity。命中论文已交给分析节点。三次可行性分析的提供商结束原因都是 length，正文字符约 14887、15693、15452，推理 token 为 0。分析 JSON 没有写完，因此没有形成 AnalysisResult。这不是候选为零，也不是引用校验被放宽。

规划仍会偶发拒绝不合法关系。同一次复验之前，肝脏曾因 relation_anchor、MedSAM 曾因 expansion_not_anchor 停在 extraction_failed。上表是同一次四题都完成检索的结果。

## 测试

新增 tests/unit/test_evidence_retrieval_trace.py。离线命令 `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.pytest_evidence`：1460 passed，122 deselected，约 229 秒。`ruff check src tests` 与 `ruff format --check src tests` 通过。被排除项未计通过。临时复验脚本不保留。
