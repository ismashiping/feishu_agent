# P1-07：离线入库服务与事务/幂等映射

状态：2026-10-27按本任务范围验收完成。43目标用例、62数据库测试、1项真实E5+PG链路、445默认回归通过；先冻结SPEC再执行RED/GREEN，证据见 [开发记录](../../development-plan.md)。依赖P1-01–06；仅Python应用服务，不增加CLI/API/飞书或检索，Phase1未整体验收。

## 1. 背景及目标

串联离线PDF/XML、受控快照、来源分块、本地Embedding和PostgreSQL短事务，提供可复用、可替换边界的入库服务。完整来源与证据能在会话关闭后读取并重新验证。

## 2. 功能需求

单PDF或单PubMed XML批次输入；每篇独立事务，其他条目失败不回滚已提交篇目。文本解析、分块和编码全部在写事务外；未编码/数量不符/定位不符/模型不符不得开始写入。返回imported/already_present/needs_update/conflict/rejected/failed，附规范document_id、片段数和固定错误码，不返回本机路径或异常原文。

PDF身份=字节SHA256，PubMed身份=PMID；document_id使用固定namespace的UUID5(source_type:identity)，片段ID为UUID5(document_id,规范化tokenizer profile+完整policy+序号)。DTO自身不自动生成ID/时间。重新尝试同一来源保持身份，数据库唯一约束最终裁决；不使用先查询再插入作为唯一并发保障。

相同来源/相同hash且书目、来源单元、解析器、profile/policy、片段文本/位置/token计数相同，返回already_present和数据库既有ID/片段数。比较忽略输入ID、获取时间、source_uri及向量浮点位差；两个filename来源标题可因文件名变化而不同。其余元数据差异返回conflict；同PMID的hash不同优先needs_update，不覆盖。PubMed hash当前是整个XML快照，不同批次的相同摘要也可能needs_update，语义增量归并仍属Phase8。

## 3. 非功能需求

不新增依赖。SourceReader、Embedder、Store为当前实际消费者的最小可替换协议；应用层不import SQLAlchemy、飞书或模型SDK。默认最多32篇/文件、128片段/篇、120秒协作总预算；已有解析/分块/模型/数据库各自预算继续生效。不创建线程池/后台任务；并发调用不共享SQLAlchemy Session。阶段检查超时，单次外部调用无法被抢占；已知成功commit后不把该条目改报失败。

重复重试仍可重新解析/编码，不承诺跳过模型或生产吞吐。数据库故障不自动无限重试；调用者可重试，唯一约束保障不增加重复记录。连接在commit时中断可能结果未知，返回失败后再次调用读取既有记录；不宣称exactly-once。

## 4. 本任务不实现

不实现更新覆盖、跨来源语义归并、OCR、在线PubMed、检索/RAG、消息入口、分布式任务、自动快照垃圾回收、生产授权和性能压测。原始快照和DB无分布式事务，失败可以留下未引用快照；不删除用户原文件。重建不检查原始文件仍存在，证据回建依据为已持久化canonical来源单元。

## 5. 输入输出契约

ImportRequest：source_type=pdf/pubmed_xml、path、allowed_root、显式aware ingestion_time；禁止自动now/epoch。IngestionService(reader,embedder,store,policy,limits,clock).ingest(request)返回BatchIngestionResult(entries,error_code)。文件级读取/批次数量错误entries=[]且error_code固定；空XML返回空成功批次。解析拒绝保留原条目index；逐篇失败继续，超过总预算剩余合法条目标记failed/ingestion_timeout。

reader.read(request)→ParsedBatch，每项ParsedEntry(index,source|error_code)互斥；ParsedSource保存ParsedPdf/ParsedPubmedArticle和实际parser_name/version。OfflineReader在显式snapshot_dir中持久化字节快照，调用既有安全解析器；PDF人工元数据可通过该适配器构造参数注入，不在核心请求中复制解析器DTO。

reader可用固定batch_limit信号报告XML解析器的条目全局上限；应用保留这个已知码，不把批次超限模糊为普通解析失败，不透传其他未知异常码。

store.save(PreparedIngestion)→StoreResult(status,document_id,chunk_count)；store.load(UUID)→PreparedIngestion|None。应用层只接收业务DTO，返回后不依赖ORM/会话。验证或外部边界异常映射为固定码source_failed/ingestion_invalid/chunking_failed/embedding_failed/storage_failed/ingestion_timeout/batch_limit；解析逐条拒绝沿用既有安全码。未知异常不用于生成公开error_code。

## 6. 数据模型

所有结果error_code为封闭Literal集合，ParsedEntry只允许既有PubMed拒绝码；未知原文即使来自可替换reader也必须在边界重验证时拒绝，不能直接回传。内部IngestionError的存储/快照固定码也有明确枚举，应用仍以阶段码对外返回。

domain/ingestion.py：ImportRequest、ParsedSource/ParsedEntry/ParsedBatch、PreparedIngestion(parsed来源包装+chunking+embedded)、StoreResult、IngestionResult、BatchIngestionResult、IngestionLimits，以及稳定ID/等价比较规则。PreparedIngestion必须非空且<=128块，顺序、UUID、归属/来源/文本/定位和Embedding身份匹配；用既有解析DTO逐块回建；区间无重叠、按来源单元排序，空隙只允许空白，不能漏掉非空白字符。vector沿用EmbeddedChunk有限/维度/范数校验。

新增documents.ingestion_metadata JSONB nullable及object CHECK，通过Alembic p107_0002追加；保存schema_version=1、真实parser_name/version、tokenizer_profile、完整chunking_policy。旧行NULL保留，不伪造版本，store读取视为storage_corrupt，不能当合法重复成功。后续回填需显式任务。chunks结构不变，逐行映射token_count、policy、模型信息、位置、原文和向量；load按chunk_index排序，要求从1连续且每行policy/模型/预算一致，再经过PreparedIngestion完整验证。

## 7. 核心业务流程

显式请求验证 → bounded文件读取/快照 → 安全解析 → 检查批次数 → 每篇分块/编码 → PreparedIngestion验证 → store短事务：`INSERT documents ON CONFLICT ON CONSTRAINT uq_documents_source DO NOTHING RETURNING document_id` → 新增则插入全部片段并commit；未插入则在同事务新语句读取已提交来源，校验旧数据并判定already_present/needs_update/conflict。非目标PK/片段/其他约束失败绝不能当重复成功，回滚后转固定存储错误。READ COMMITTED下冲突等待后可读取winner，不复用失效事务。

OfflineReader严格受控根目录/普通文件/大小限制，默认快照20MiB（XML解析仍10MiB）；按hash.pdf/xml命名，先写同目录临时文件、flush/fsync，再使用os.link原子排他发布，最后清理自己临时文件；并发已存在目标必须校验字节hash，禁止覆盖不匹配文件。现有解析器再次读取并校验同一hash，记录受控快照URI。PDF filename标题保留原输入stem及filename来源，不把hash当文献标题。

store从既有engine借出连接，在开启Session事务前用Connection.execution_options显式设置READ COMMITTED，不依赖调用者engine或服务器默认隔离级别，不新建自定义连接池或改写调用者engine。实际测试传入REPEATABLE READ时仍验证入库事务为READ COMMITTED；不能仅依赖嵌套engine代理的执行选项。

## 8. 异常与边界场景

输入路径越界/损坏/过大/缓存损坏、批次超限、混合解析拒绝、空文档、错误embedding数量/身份/位置、DB不可用/约束/commit失败、合法数据读取/旧数据损坏、同source不同ID并发和不同source复用UUID。库层IngestionError仅包含固定码storage_corrupt/storage_conflict/storage_unavailable/source_invalid；应用不泄漏原始异常。Prepared输入验证失败不写库，脏数据读取不伪装为未检索到或重复成功。

## 9. 测试用例清单

- DTO互斥、输入时间、稳定ID、跨页/节定位、缺块/重叠/错序、向量与chunk绑定、等价比较边界。
- 应用reader/embedding/store替身验证步骤顺序、解析拒绝/逐篇失败/上限/协作超时；编码前后输入不被修改、失败不写库。
- 真实合成PDF/XML快照读取，原文件移除后快照/回建仍存在；同hash并发、已有损坏快照、越界/大小限制。
- PostgreSQL mapper往返、session关闭后DTO、同内容/变更/配置冲突不覆盖、legacy/损坏记录拒绝、真实插入/commit失败回滚、并发一imported其余already_present、错误约束不当重复。
- 增量迁移保留P106行，NULL元数据不伪造，降至P106再升head；旧数据库47项回归适配当前head并不覆盖历史证据。
- 单独external+database真实PDF→实际E5→PG→load回建，禁止联网；与普通数据库替身编码测试分开记录。
- 默认pytest、数据库全套、导入隔离、Ruff/mypy/lock/pip检查；完整阶段未完成不生成Phase1完成学习材料。

## 10. 可执行验收标准

先运行tests/unit/test_ingestion.py和tests/integration/test_offline_reader.py，确认目标缺失RED再实现GREEN。所有日志放.artifacts/p1-07-20261027-01，basetemp每次独立。database测试专用host=127.0.0.1、name前缀clinical_agent_test_、显式reset=1；独立Compose project/volume、随机密码环境注入、明确--env-file .env.example，不读用户.env。不删除既有卷/库。

实际命令：默认pytest；`pytest tests/integration -m "database and not external"`；真实链路`pytest tests/integration/test_ingestion.py -m "database and external"`。缺模型/数据库前提不能skip后声称通过。Ruff包含alembic，mypy src，正式依赖和锁保持；真正数据库/模型测试才算外部验收。

## 11. 阶段依赖及完成定义（DoD）

SPEC先行、真实RED/GREEN、原子事务/并发幂等/非覆盖分类/映射重验证/受控快照、真实模型链路与回归、迁移和进度全部验证后才完成本任务。未完成则明确记录，不将Fake通过等同真实服务。下一任务为基础向量检索与证据命中DTO，需用户指定后另行SPEC；不自动开始。

官方依据（2026-10-27核查）：[SQLAlchemy事务/会话](https://docs.sqlalchemy.org/en/21/orm/session_basics.html)、[PostgreSQL ON CONFLICT](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html#insert-on-conflict-upsert)、[psycopg错误诊断](https://www.psycopg.org/psycopg3/docs/api/errors.html)。本任务不新增或升级依赖。
