# 基础向量检索（P1-08）

## Phase 5 本地混合检索（2026-10-28）

默认mode=vector保留原行为；API的options增加mode=keyword|vector|hybrid、candidate_limit（默认50、1–100且不小于top_k）、keyword_query（可选ASCII文本）、date_from/date_to（成对ISO日期）。CLI对应 --retrieval-mode、--candidate-limit、--keyword-query、--local-date-from/--local-date-to。本地日期仅接纳完整出版日，未知/年/月精度条目明确排除，不补造日期。

keyword不计算查询Embedding，hybrid计算一次原问题Embedding，再在同一PostgreSQL快照内取得FTS/向量候选并按chunk_id做RRF（k=60），同分UUID升序，不合并掉同文献不同片段。任何必需通道失败即报错，不静默降级；空通道为成功。非vector模式不支持非零min_similarity，不能用余弦阈值过滤RRF/FTS。

FTS为simple ASCII词项匹配与精确PMID/DOI辅助查询，不是BM25或中文分词。中文问题可显式给英文keyword_query；不提供时keyword/hybrid返回retrieval_language_unsupported（API422），vector仍用既有多语言模型。

结果ResearchAnswer增加local_retrieval_mode/strategy、local_channel_status和retrieval_warnings；Python RetrievalResult的hits还保留keyword_rank/vector_rank/fusion_score与score_type。分数不表示医学质量，引用仍来自原证据门禁。scope=hybrid表示本地与在线来源，options.mode=hybrid表示本地算法，两者独立；在线条目不参加本地RRF，PubMed日期仍使用pubmed对象设置。

**现有数据库需显式 `alembic upgrade head` 到 p501_0003**：该迁移增加STORED search_vector与GIN，旧文献/片段/向量/ID保留，新写入自动更新。应用不会自动迁移；本次真实迁移测试仅在隔离测试库执行，没有改用户现有库。用法/范围见 [P5-01](specs/tasks/p5-01-hybrid-retrieval.md)、[学习导航](learning/phase-05/README.md)及[验收记录](phase5-acceptance.md)。以下历史说明按原时点阅读。

本页说明P1-08的Python查询服务与内部EvidenceHit DTO；该服务自身不生成回答，当前已被[基础RAG](basic-rag.md)、[CLI](cli.md)及[API](api.md)复用。飞书运行时尚未接通。[详细SPEC](specs/tasks/p1-08-vector-retrieval.md)、[开发记录](development-plan.md)。

## 调用方式

先按 [数据库说明](postgres.md)、[模型说明](local-embedding.md) 和 [入库说明](offline-ingestion.md) 准备环境、执行迁移并导入文献。沿用db/ml可选依赖，当前任务未新增包/迁移，也未下载新模型。

```python
from pathlib import Path

from clinical_agent.adapters.embedding import REVISION, LocalModelConfig, load_local_embedder
from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
from clinical_agent.application.retrieval import RetrievalService
from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalRequest

embedder = load_local_embedder(LocalModelConfig(
    snapshot_dir=Path("models/multilingual-e5-base") / REVISION,
))
with database_engine(DatabaseSettings()) as engine:
    service = RetrievalService(embedder=embedder, retriever=PostgresRetriever(engine))
    result = service.retrieve(RetrievalRequest(
        question="What limitations are reported in the study?",
        options=RetrievalOptions(top_k=5, min_similarity=0.0,
            source_types=["pdf", "pubmed"],
            content_scopes=["abstract", "extracted_text", "full_text"]),
    ))
    for hit in result.hits:
        print(hit.rank, hit.chunk.chunk_id, hit.score, hit.document.title,
              hit.document.title_origin, hit.chunk.location.model_dump())
```

调用者复用一个模型实例；query前缀由既有embed_query添加，不要手动加query:。RetrievalRequest接受trim后1..4000字符的严格字符串，只允许local；字符数合格不代表token数合格，512 token限制由实际encoder校验，超限不截断。模型编码在获取数据库连接前完成。

## 参数与分数

| 参数/字段 | 当前语义 |
| --- | --- |
| top_k | 默认5、严格整数1..20 |
| min_similarity | 默认0.0、有限数值[-1,1]，包含等号；拒绝bool/字符串 |
| source_types | 非空、无重复pdf/pubmed列表，默认两者 |
| content_scopes | 非空、无重复abstract/extracted_text/full_text列表，默认全部 |
| document_ids | None表示全部；否则1..100个不重复UUID |
| score_type | 固定cosine_similarity |
| score | 1-pgvector余弦距离，越大越相似；范围[-1,1] |

过滤条件AND组合，在排序/limit之前生效。source_types=[pdf]与content_scopes=[abstract]可合法返回空，不偷换检索范围。按距离升序、同距离chunk UUID升序稳定排序，rank从1连续；不使用写入时间或随机顺序。

阈值过滤使用与显示分数一致的SQL表达式，避免单纯改写为1-min_similarity导致边界浮点差异。仅容许距离的微小边界舍入误差，明显越界/非有限距离报损坏，不把任意错误分数压进合法区间。

0.0是透明的工程默认值，未经过医学语料校准。相似度不是证据等级、支持结论的概率或临床效力；命中不等于该文献支持某项医学结论，空命中也不表示证据证明治疗无效。当前只表示在本地库及本次过滤/阈值下得到或没有得到候选。

## EvidenceHit保留什么

每个hit包括完整EvidenceChunk（ID、原文、位置、来源快照、EmbeddingInfo）、DocumentSummary（真实书目、标题来源、日期精度、获取时间及来源元数据）、分数类型/数值和排名。

DocumentSummary不含整篇text/abstract/evidence_chunks；命中DTO不含向量值。摘要维持abstract，PDF filename标题维持title_origin=filename，未知日期/作者不补造。chunk/document归属与全部来源快照必须一致。此DTO属于内部业务契约，source_uri保留本机快照路径供追溯；未来聊天/API应由专用渲染器生成安全结果，不能直接发布内部DTO。

## 检索与验证边界

查询向量先经QueryEmbedding数值/维度/范数校验，再比对完整固定E5身份：模型、不可变revision、tokenizer revision、768维、normalized=true及source-unit-v1。相同768维的其他模型也会在连接数据库前拒绝；不自动混合向量或重新归一化。

PostgresRetriever借连接并显式设置REPEATABLE READ，在事务第一语句设置READ ONLY。候选、文献和片段最多三条数据SELECT，共享同一快照；不改变调用者engine，不创建新连接池。默认数据库statement_timeout仍为10秒，应用总预算30秒为协作检查，不能抢占单次模型/SQL。

先以当前模型身份和过滤条件召回top_k，再批量读取其文献及有界片段，复用P1-07完整mapper验证parser/profile/policy、来源单元覆盖和逐块位置。每篇至多128块，批次hydration多取1行用于越界检测。选中文献有legacy/损坏元数据、缺片段或错位时，整个请求报retrieval_corrupt，不静默漏掉坏数据后冒充空结果。未进入候选范围的内容不做全库完整性检查。

## 错误与验收

请求契约错误抛ValidationError。已知失败用RetrievalError固定码：retrieval_embedding_failed、retrieval_model_mismatch、retrieval_failed、retrieval_corrupt、retrieval_timeout；不附加原始异常、query、文献或凭据。只有成功完成检索但未满足候选条件时返回hits=[]。

测试分开执行，数据库必须是专用临时库，前提与安全开关见postgres.md：

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_retrieval.py -q
.venv/Scripts/python.exe -m pytest tests/integration -m "database and not external" -q
$env:OMP_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.venv/Scripts/python.exe -m pytest tests/integration/test_retrieval.py `
    -m "database and external" -q
```

实际验证数学轴向向量、过滤/排名、只读快照/并发更新和错误边界；另用固定真实E5 query/document向量完成入库→检索→命中回建。没有进行医学检索质量评价、ANN/生产规模性能评估或生成答案验收；这些结果不能替代后续RAG和评估阶段。
