# 运行与排错

先确认现有数据库迁移到 p501_0003、本地 E5 模型路径，以及 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL；不要打印密钥。普通 Demo 不需要这些依赖。

model_output_invalid：检查模型 JSON 是否严格匹配 schema，是否缺必需字段、伪造引文/用户原文、把假设标事实、把相同研究当双侧来源。日志只记录错误码，不倾倒用户想法和全文。

context_limit：输入快照与 schema 超出 ResearchLimits.max_context_characters，缩小实际检索 top_k/片段范围，并保留覆盖限制。generation_timeout 或 research_timeout：分别是模型/总期限；不自动无限重试。insufficient_evidence 是成功空检索，检索故障仍抛原错误。

not_evaluated：没有可用的非撤回来源。partial 常见于仅摘要、字段缺失、未知相似维度或检索 partial。检查 sources 的 content_scope、notices 和 retrieval.search_provenance；不要将摘要升级成全文证据。
