# P1-08：基础向量检索与证据命中DTO

状态：已验收，2026-10-27；实施前冻结SPEC并保留实际RED/GREEN记录，依赖P1-01–07。仅Python本地检索，不进入生成/报告或业务CLI/API。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

以实际查询向量在已入库证据上进行pgvector精确余弦检索，返回可回建、可追溯、脱离会话且不携带向量值的EvidenceHit。空结果和故障严格区分。

## 2. 功能需求

查询文本→注入的embed_query→QueryEmbedding校验→PostgreSQL检索→候选完整映射/来源回建→EvidenceHit列表。限定local范围、固定当前已验证E5模型/同revision、768维、normalized=true、source-unit-v1；错误query身份在获取数据库连接前拒绝，不仅检查维度。实际query前缀由既有Embedding适配器添加一次。

使用pgvector <=>，score=1-cosine_distance，范围[-1,1]，score_type=cosine_similarity；不是概率、证据等级或临床价值。按distance升序、chunk_id UUID升序（相同分数稳定），不按输入/插入顺序。先应用全部过滤/阈值，再limit；阈值包含等号。

## 3. 非功能需求

不新增/升级依赖、不迁移、不建立ANN索引。精确扫描适用于当前MVP，不承诺大库吞吐。复用有界池/10秒statement_timeout，默认应用30秒协作预算，不能抢占单次模型或SQL。

检索单连接REPEATABLE READ + READ ONLY事务：在连接上显式设置隔离，事务第一语句SET TRANSACTION READ ONLY；候选与后续hydration来自同一快照。不改变调用者engine，不复用写入Session。最多三条数据SELECT：候选、文献、片段；最多20文献，每篇已有128片段契约，hydration额外limit(doc_count*128+1)检测越界，不能无限取全库或逐hit打开新连接。

## 4. 本任务不实现

不实现关键词/混合检索、重排序、PICO、实时PubMed、LLM、LangGraph生成工作流、引用语义核验、医学质量评级、CLI/API/飞书、查询缓存、ANN/性能优化。阈值未做医学数据校准，固定合成样例通过不代表检索医学效果。

## 5. 输入输出契约

RetrievalRequest(question,scope='local',options=RetrievalOptions())：严格字符串、trim后1..4000 Unicode码点，不解码bytes；不支持online/hybrid。RetrievalOptions：top_k默认5，严格整数1..20；min_similarity默认0.0，有限数值[-1,1]（拒绝bool/字符串）；source_types默认pdf/pubmed、content_scopes默认abstract/extracted_text/full_text，列表非空/无重复；document_ids可为None（全部）或1..100个不重复UUID。各过滤之间AND，互不相交时合法空结果。0.0只是透明的工程筛选默认，不是充分证据阈值。

RetrievalService(embedder,retriever,limits,clock).retrieve(request)→RetrievalResult。模型调用在数据库连接之外。request契约错误ValidationError；外部异常固定RetrievalError.code：retrieval_embedding_failed、retrieval_model_mismatch、retrieval_failed、retrieval_corrupt、retrieval_timeout。错误文字不包含query、文献、密码、DSN或第三方异常；数据库/模型失败不得返回空hits。

PostgresRetriever(engine).search(query:QueryEmbedding,options:RetrievalOptions)→RetrievalResult；低层输入先重验证，模型身份先于连接校验，库不重新归一化或截断输入。返回结果重验证options/模型/排名，错误候选拒绝整个请求，不静默丢掉后返回较少结果。

## 6. 数据模型

domain/retrieval.py定义RetrievalRequest/Options/Limits、DocumentSummary、EvidenceHit、RetrievalResult和固定错误。DocumentSummary保存document_id、title/title_origin、authors、publication_date、journal/doi/pmid、ingestion_time及全部SourceMetadata字段；不包含整篇abstract/text/evidence_chunks。

EvidenceHit：chunk(EvidenceChunk，包含原文/定位/来源/EmbeddingInfo)、document(DocumentSummary)、score、score_type固定cosine_similarity、rank从1连续。片段必须已经编码、document_id与全部来源快照一致。摘要只标abstract；filename标题仍保留title_origin。score有限且[-1,1]，bool无效。

RetrievalResult：scope=local、options、embedding_info（查询空间身份，不含向量）、hits。验证数量<=top_k、无重复chunk_id、rank连续、score递减/相同分数UUID递增、每项score满足阈值/过滤、全部hit模型身份匹配。结果为内部业务DTO，保留本机source_uri供追溯；未来聊天/API渲染不能直接暴露此内部DTO。

## 7. 核心业务流程

request验证→query编码→QueryEmbedding完整向量/身份校验→预算检查→只读一致性事务→join文献/片段并过滤来源/获取范围/doc_ids/完整模型字段/document_prefix→distance阈值/稳定排序/limit→批量读取选中文献及其全部有界片段→复用prepared_from_records验证parser/profile/policy、完整覆盖和逐块来源→仅选中片段生成摘要+命中→DTO校验→释放事务/连接→返回。

默认不排除legacy/corrupt metadata来冒充正常空库：若其进入top_k候选，映射必须报retrieval_corrupt；低于阈值/不在候选范围的内容不做全库核验。浮点距离仅允许[-1e-6,2+1e-6]，否则损坏；score=1-distance后仅对边界舍入误差clamp至[-1,1]，不得把明显错误距离归一化为合法分数。

## 8. 异常与边界场景

空问题/bytes/超长、非法top_k/阈值/过滤、重复ID、错误空间/归一化/维度/向量、空库/过滤无结果/阈值无结果、同分稳定、摘要范围/Unicode位置、legacy或损坏来源/丢片段、异常距离、数据库断线/timeout/模型故障、模型后总预算到期、hydration途中并发更新。只读同一快照避免前后数据混合。命中正文含指令仍是普通证据字符串，不触发工具或生成行为。

## 9. 测试用例清单

- DTO严格输入、有限分数、完整来源绑定、无向量/全文泄漏、排名/重复/模型/过滤一致性与JSON往返。
- 应用替身验证query只编码一次、不重复加前缀、编码前后无DB事务、超时/异常区别空结果、坏retriever输出拒绝。
- 真实pgvector轴向单位向量手算1/0/-1及普通向量约0.6，同分UUID顺序，top_k/阈值包含等号，过滤先于limit，摘要/Unicode回建。
- 错误query在连接前拒绝；只读/RR实际确认；hydration时并发元数据更新保持旧快照；legacy/源数据/缺片段和DB失败不冒充空。
- 全部既有数据库/默认回归；单独真实E5 query+入库向量→检索→命中回建，无非本机网络连接。
- 导入隔离、Ruff/mypy/lock/pip、基础无db/ml环境及doctor；不把Fake向量通过当真实编码验收。

## 10. 可执行验收标准

先运行 `pytest tests/unit/test_retrieval.py -q`（独立basetemp/cache_dir）确认缺目标能力RED，再最小实现GREEN。真实数据库专用host127.0.0.1/name前缀clinical_agent_test_/reset=1，独立Compose project/volume、随机密码环境、明确--env-file .env.example；不碰已有库/卷、不读用户.env。输出保存.artifacts/p1-08-20261027-01。

实际验收命令：默认pytest；`pytest tests/integration -m "database and not external"`；`pytest tests/integration/test_retrieval.py -m "database and external"`；Ruff src/tests/alembic、mypy src、uv lock --check --offline、uv pip check。未具备模型/DB前提不得skip后宣称通过，固定E5缓存不重新下载。

## 11. 阶段依赖及完成定义（DoD）

SPEC先行、实际RED/GREEN、来源/空间/排名/过滤/只读一致性、默认/真实数据库/实际模型检索及文档均完成方可验收本任务。Phase1仍未完成，不生成阶段完成学习文档。下一任务为基础RAG工作流与有证据关联的生成，需用户另行指定后细化SPEC，不自动开始。

依据（2026-10-27复核）：[pgvector精确距离/过滤](https://github.com/pgvector/pgvector)、[SQLAlchemy集成](https://github.com/pgvector/pgvector-python)、[连接隔离选项](https://docs.sqlalchemy.org/en/21/core/connections.html)、[PostgreSQL隔离](https://www.postgresql.org/docs/16/transaction-iso.html)。沿用已锁定且实际验证的依赖版本。
