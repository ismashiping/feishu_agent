# P5-01：PostgreSQL 关键词与向量混合检索

版本1.0；2026-10-28；实施前冻结，现已实现并完成核心范围集中验收。覆盖P5-F01–04/P5-T01–05，仅Phase5。

## 1. 基线与范围

Phase4核心范围已验收，Phase1/3旧缺口保留。现有PostgresRetriever提供严格E5空间内向量检索和可追溯hydration；Phase4 scope=hybrid仅合并来源。本次复用同一库、DTO、应用服务与共享图，新增FTS/RRF及必要迁移，不引入其他搜索服务、重排模型或Phase6。

## 2. 输入与默认行为

扩展既有RetrievalOptions：mode=vector|keyword|hybrid（默认vector），candidate_limit=50（1–100且不小于top_k），keyword_query可空（严格非空ASCII字符串，最多4000字符）。关键词模式不计算查询Embedding；hybrid计算一次。未指定keyword_query时使用原问题，若非ASCII则返回retrieval_language_unsupported，不静默降级。中文问题可配英文keyword_query；vector仍支持既有多语言模型。vector模式不接纳keyword_query，非vector模式不接纳非零min_similarity；混合时不会把余弦门槛误作用于FTS/RRF。

source_types/content_scopes/document_ids保持既有含义。新增date_from/date_to（成对ISO日期）用于本地两通道共同过滤：仅publication_date.precision=day且日期在闭区间；未知/年/月精度不补造日期，显式排除并提示策略。scope=online不接纳本地mode/日期/keyword_query；scope=hybrid的本地与PubMed日期各自明确配置，不宣称自动同步。CLI增加--retrieval-mode/--candidate-limit/--keyword-query/--local-date-from/--local-date-to，API使用options对象。

## 3. FTS与标识符

PostgreSQL `simple` 固定配置、plainto_tsquery和ts_rank_cd(normalization=32)，保留英文词/缩写而不宣称词形还原、中文分词或BM25。在chunks增加由text生成的STORED search_vector及GIN索引；原片段不重存、不改ID。单个PMID或DOI查询可精确匹配documents元数据后回到同一chunk证据，准确标识不由模型生成。参数全部绑定，用户输入不作为tsquery/SQL语法执行。

依据：[PostgreSQL16索引](https://www.postgresql.org/docs/16/textsearch-tables.html)、[全文查询与排名](https://www.postgresql.org/docs/16/textsearch-controls.html)。配置名固定以免索引与查询依赖会话默认值。

## 4. 候选与融合

keyword/vector各按本通道得分降序、chunk_id升序截断candidate_limit。每个命中记录keyword_rank/vector_rank（从1开始，缺通道null）。hybrid按chunk_id合并，`fusion_score=sum(1/(60+rank))`，strategy_version=rrf-v1；同分chunk_id升序。两通道同ID但证据/来源快照不一致拒绝为retrieval_corrupt；相同文献不同片段仍保留，禁止按document_id融合掉片段。

EvidenceHit增加score_type=fts_rank|rrf、通道排名/fusion_score；vector与PubMed原类型保留。FTS分数归一化在[0,1]内，RRF同样有界，任何分数不代表医学质量。最终top_k仍1–20，候选可到100但不通过临时放宽top_k契约实现。

## 5. 状态和故障策略

RetrievalResult增加channel_status（keyword/vector均为ok或not_requested）、degraded固定false、warnings、strategy_version。空通道为ok且无命中；任一必需通道失败/超时/迁移所需列缺失整个请求报错，不自动降级、不把失败当空召回。keyword模式不要求查询模型运行，但已入库片段仍须符合既有模型/来源一致性。GIN是访问优化，数据库缺少GIN时可能顺序扫描，不能据此返回正常空集；本阶段迁移验收仍要求GIN实际存在，不实现每次请求额外检查索引。

## 6. 数据一致性与期限

两通道查询与来源hydration在同一REPEATABLE READ只读事务内顺序执行，避免跨快照混用；不引入线程。复用现有来源反序列化/哈希/区间检查，只加载最终top_k关联文献和片段。研究/检索总期限保留，新增路径根据剩余期限设置statement_timeout并在查询/解析间复查。默认vector结果和排序不变。

## 7. 迁移

新增p501_0003依赖p107_0002，只增加生成列与GIN；升级覆盖已有行，新写入自动更新，降级仅删除新增索引/列，保留文献/片段/向量及旧迁移。用专用空测试库验证升级/降级/重升与Alembic check，无create_all替代迁移，不碰用户数据库。

## 8. 应用与来源合并

RetrievalService按options.mode选择原vector或新增通道入口，正式CLI/API/飞书共享装配复用同一个PostgresRetriever。ResearchAnswer返回本地检索模式/状态/策略，引用仍来自可信EvidenceHit。scope=hybrid先完成本地RRF再与在线名额合并，不对在线分数做RRF；跨来源去重不删除同一本地文献的不同chunk。

## 9. 先编写的测试与固定样例

tests/unit/test_hybrid_retrieval.py：手算RRF、缺通道/重复/稳定同分、同文献不同片段、不一致来源拒绝、严格上限/字段、语言和日期语义、跳过Embedding/只编码一次、失败不降级、问答/入口回归。tests/integration/test_hybrid_retrieval.py显式database：真实FTS/pgvector同快照、源/日期/范围一致过滤、精确PMID/DOI、迁移/GIN和默认vector回归。

固定合成数据集hybrid-cases-v1：A=aspirin trial（向量0.6），B=analgesic outcomes（向量1.0），C=metformin cohort（向量0.0）；查询aspirin；keyword命中A，vector前三为B/A/C，RRF期望A优先（双通道），B次之；top_k=2时三模式都须包含预设合成目标A，keyword/RRF首位A，vector首位B。该受控样例仅证明排序/来源可用，不证明真实医学召回提升，不根据结果改标注。中文/混合问题的关键词拒绝单列；另以ASCII关键词覆盖中文原问题的核心行为。

## 10. 集中执行

实施和六份教材/Demo齐备后执行正式.venv/Scripts/python.exe：目标unit/integration默认范围、全量默认回归、显式`-m database tests/integration/test_hybrid_retrieval.py`及已有真实数据库检索/入库/迁移回归；Ruff/format/mypy/Alembic SQL/Demo/链接检查分列。真实数据库必须独立clinical_agent_test_库、127.0.0.1和reset opt-in。Docker资源仅新建并清理本次所有，环境缺失失败/未验收，不用SQLite/Mock代替。

## 11. 完成与停止

核心实现/真实数据库/固定样例对比/既有引用与入口回归、六份学习材料和实际记录齐备才标Phase5核心完成。无需新增付费LLM或PubMed请求，不以合成Embedding当真实模型效果；原有人工/模型/部署缺口保留。性能优化/重排器/大评估延期，结束于Phase5，不进入Phase6。
