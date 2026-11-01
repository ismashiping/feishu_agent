# 从需求到证据分析

## 是什么与为什么

Agent在这里按任务调度已有工具；RAG将真实来源片段交给模型。检索结果不是研究结论。方向评估要知道用户想判断什么、证据能支持什么、未知条件如何验证。

## 原理与最小Demo

PicoPlanner一次调用生成QueryPlan：task_intent决定任务，research_intent用于检索语义，paper_target锚定用户给出的论文或方法。respond在同一图运行内选择回答或报告，反馈不会重新规划。

运行README中的合成测试Demo，查看test_intent_routing.Extractor返回的JSON，修改task_intent后观察测试断言所期待的输出类型。测试不是模型准确率。

AnalysisItem用exact quote和chunk_id关联来源；reported_fact要求原文，推断需要verification_needed。四维可行性不打总分；unknown表示条件尚待确认。论文中的算力限制不等于用户的限制。

## 工程取舍

复用现有图和审核器，不再添加路由LLM。共享deadline限制整次请求，四HTTP/两筛选约束检索成本。引用校验解决来源关联，不能替代语义和医学复核。默认报告只展示可读内容，审计记录保存定位信息。
