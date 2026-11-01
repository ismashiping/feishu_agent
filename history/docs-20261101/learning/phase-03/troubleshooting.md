# 运行与排错

extraction_failed：检查固定测试响应是否符合 ExtractionDraft；user_text 必须与 original_question 的精确切片一致，不能按字节或规范化前后混用区间。多余键、Markdown 围栏、重复 JSON 键或候选词冒充 PICO 原文都会被拒绝。公开日志不打印原始模型异常或完整问题。

extraction_timeout：默认规划上限 20 秒，并受研究剩余预算约束。底层 HTTPX 同时有各传输步骤预算；同步操作不能被强杀。不要靠无限重试解决。

needs_clarification：查看 query_plan.structured_question.ambiguities，补充具体问题重新提交。无持久会话记忆；不要误认为 Phase 2 任务状态。

缺 comparison：通常为合法 partial，不补造 placebo。完整原问题在 preserved_constraints 中，但限制条件是否真正可过滤由未来检索能力决定。

真实模型 smoke 失败：保留逐样例输出和失败，不改变标签或用 Fake 冒充通过。无 LLM_* 时为未验收；现有模型接口迁移的历史结果不自动证明本次 PICO。Phase 1 医学人工签署缺口继续保留。

默认离线测试排除 external/database/redis/performance，这些排除项均不计通过。没有改变数据库 schema 或 Redis 行为，不为本阶段重建服务。当前仍只检索本地已入库文献，不能声称覆盖最新医学研究。
