# SPEC 05：关键词与向量混合检索

版本：0.3；日期：2026-10-28；状态：P5-01核心范围验收完成，详细契约见 [任务 SPEC](tasks/p5-01-hybrid-retrieval.md)。

## 本轮核心范围与测试约定（2026-10-28）

本阶段已先冻结 P5-01 输入输出、语言/过滤/降级规则及合成比较样例，再编写测试并最小实现。不在单次会话执行 RED/GREEN 或回归，阶段结束后集中执行核心测试、已有离线回归、受影响真实集成/外部冒烟、必要人工复核和质量检查。集中验收失败须修复并重跑受影响范围；未执行、失败、跳过或被排除的项目不得标记通过。实际目标测试为 tests/unit/test_hybrid_retrieval.py 与 tests/integration/test_hybrid_retrieval.py；真实数据库通过 database 标记单独执行。

后续顺序固定为 Phase 3 → 4 → 5 → 6 → 7，不依赖延期 Phase 2 的 TaskRecord/receipt。复用现有 ResearchService/LangGraph、LangChain 通用模型边界、DTO 和存储/解析/引用模块。核心超时、错误分类、数据一致性及来源真实性必需；非核心健壮性、性能优化、复杂异常处理留 Phase 7 后收尾。核心验收及 `docs/learning/phase-05/` 六份真实学习材料齐备才标阶段完成。参见[开发计划](../development-plan.md)与[测试策略](../testing-strategy.md)。

## 1. 背景及目标

结合关键词精确匹配与向量语义召回，改善医学缩写、术语与表达变化下的检索。复用已有 PostgreSQL，不为演示技术复杂性引入第二套搜索服务。

## 2. 功能需求

- P5-F01：对本地已入库证据提供 PostgreSQL 全文检索通道和现有向量通道。
- P5-F02：按 chunk_id 去重并融合排序，稳定输出 EvidenceHit 及各通道排名与来源；同一文档不同片段不无故合并。
- P5-F03：支持相同的来源/日期/内容范围过滤；明确一条通道失败时是否允许带 degraded 标志返回另一条通道。
- P5-F04：冻结小型标注样例，比较关键词、向量和融合模式，检查核心可用性；额外重排器延期。

## 3. 非功能需求

同输入/固定数据下排名稳定，不能直接相加不可比较的距离与关键词分数。所有过滤先明确语义，候选集有上限。来源与定位元数据贯穿排序，不把 score 当医学可靠性概率。

## 4. 本阶段不实现的内容

不实现向量数据库、Elasticsearch 服务、自定义分词框架或默认神经重排模型；不宣称 PostgreSQL FTS 就是 BM25。中文关键词通道效果需单独验证，不能由多语言 embedding 可用推断中文 FTS 分词可用。

## 5. 输入输出契约

HybridRetrievalRequest(query, filters, mode=keyword/vector/hybrid, candidate_limit, top_k)。filters 沿用文献来源/日期/范围；不支持的语言或过滤应明确提示，不静默改义。

HybridRetrievalResult(hits, channel_status, degraded, warnings, strategy_version)。每条 hit 有 chunk_id、document_id、可信来源、location、keyword_rank、vector_rank、fusion_score；某通道未命中时 rank 为 null，不设成 0。

## 6. 数据模型

为现有 EvidenceChunk 增加可迁移的全文检索表达/索引设计，不重存一套失联文献。融合策略初选 RRF：对各出现通道累加 `1 / (k + rank)`，rank 从 1 起，k 初始候选 60；参数与 tie-break（chunk_id 升序）须在细化任务冻结并版本化。p501_0003已新增simple生成列与GIN；具体契约和执行证据见任务SPEC与阶段记录。

## 7. 核心业务流程

校验/标准化查询 → 相同过滤分别召回有限候选 → 统一片段身份 → 基于排名融合 → 稳定裁剪 top_k → 返回带通道状态的 hits → 原有回答与引用流程。并发召回有总超时，不能引入无上限线程。

## 8. 异常与边界场景

一边空/两边空、同一片段重复、同分、未知片段、过滤后空集、单通道超时、索引缺失、中英混合和精确 DOI/PMID 查询。通道错误不等于没有匹配；混合来源查询中的在线记录按 Phase 4 来源契约处理，不假设它们已入本地 FTS 索引。

## 9. 测试用例清单

- P5-T01：固定排名手算 RRF、缺通道、重复和同分稳定性。
- P5-T02：两通道过滤一致、top_k/候选上限及可追溯字段保留。
- P5-T03：空结果与通道错误/degraded 状态区分。
- P5-T04：真实 PostgreSQL FTS/pgvector 查询、迁移和索引行为。
- P5-T05：冻结小样例上的命中/排名对比；规模化指标与性能门槛延期 Phase 9。

## 10. 可执行验收标准

阶段末使用正式解释器执行目标与回归，实际命令和结果见 [Phase5记录](../phase5-acceptance.md)。固定小表的融合排序必须与手算结果完全一致；重复 chunk_id 只返回一次；排序后的每条 hit 可回到同一来源片段。

在实施前冻结小样例、k、语言范围和核心接受标准；记录三种模式命中/排序与失败案例。延迟优化和规模化效果实验不作为本阶段门槛，执行仍需必要超时/候选上限。融合并非必然优于单通道，不达目标时不能用更换测试集证明完成。hybrid-cases-v1已冻结在 tests/fixtures/hybrid/cases.json，并在真实PostgreSQL/pgvector上验证三种模式；只证明受控排序，不外推医学效果。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 4 验收与学习材料，不依赖 Phase 2 或 Phase 9 评估平台。先冻结语言范围、过滤语义、RRF 参数、候选上限和通道失败策略。阶段末集中验收真实 PostgreSQL FTS/pgvector、手算融合、来源定位一致性、固定小样例对比及已有问答/引用/入口回归，交付 docs/learning/phase-05/ 后完成。规模化效果评价、延迟门槛、索引调优与额外重排器延期；不声称已证明全面优于单通道。下一核心阶段为 Phase 6。
