# SPEC 01：离线知识库、基础 RAG 与飞书 MVP

版本：0.12；状态：Phase1进行中，P1-01–11已实现离线入库、基础向量检索、RAG工作流/证据关联回答、CLI及FastAPI入口；飞书尚未实现。详细规则见 [P1-01](tasks/p1-01-literature-contracts.md)、[P1-02](tasks/p1-02-pdf-parsing.md)、[P1-03](tasks/p1-03-pubmed-xml.md)、[P1-04](tasks/p1-04-source-chunking.md)、[P1-05](tasks/p1-05-local-embedding.md)、[P1-06](tasks/p1-06-postgres-schema.md)、[P1-07](tasks/p1-07-offline-ingestion.md)、[P1-08](tasks/p1-08-vector-retrieval.md)、[P1-09](tasks/p1-09-basic-rag.md)、[P1-10](tasks/p1-10-cli-entrypoints.md)、[P1-11](tasks/p1-11-fastapi.md)。

## 1. 背景及目标

完成最小闭环：离线 PDF / PubMed 导出文件 → 本地知识库 → 有来源与定位的科研问答 → CLI/API/飞书复用。以可追溯和可测试为先，不将普通生成文本冒充循证结论。共享语义遵循 [SPEC 00](00-project-overview.md)。

## 2. 功能需求

- P1-F01：导入单个/批量有文字层 PDF，以及本地 PubMed XML 导出文件；解析真实元数据，保留原始来源和获取范围，不在线搜索。
- P1-F02：按页或摘要章节分块；MVP 不跨 PDF 页合块，以简化可核验定位；用实际模型 tokenizer 控制长度并记录版本。
- P1-F03：sentence-transformers 生成向量并校验数量/维度；SQLAlchemy + Alembic + pgvector 原子存文档及片段。
- P1-F04：基础向量检索和必要 LangGraph 分支：检索 → 无可用证据时说明不足；否则生成 → 基础引用检查 → 返回。节点调用应用能力，不创建多 Agent 人格。
- P1-F05：回答以结构化 claims 关联 chunk_id，文献引用由可信元数据渲染；模型输出未知标识或无证据关联的实质性结论时拒绝该回答，返回 citation_invalid/model_output_invalid 错误，不静默去掉错误引用后照常发布。只有检索成功但没有可用证据时返回 insufficient_evidence。
- P1-F06：CLI、FastAPI、飞书复用同一服务；不复制检索或生成规则。
- P1-F07：官方 SDK 长连接接收文本，过滤自身/非支持消息，event_id 或 message_id 短期去重，有界线程池执行 RAG，支持友好错误回复及关闭资源。

## 3. 非功能需求

单文档写入为原子事务；解析和 embedding 在事务外完成。重复及并发导入依靠数据库唯一约束解决，查询后插入不能作为唯一幂等机制。相同来源身份与内容重复导入不增加片段；同一外部身份内容变化返回 needs_update，待 Phase 8，不静默覆盖。

飞书在途数量有配置上限，线程池 max_workers 之外还限制已提交任务；饱和时不调用 RAG，不无限入队。Redis 不可用时不绕过跨进程去重继续处理，记录错误并尽可能回复暂不可用。进程崩溃和远端发送超时仍可能造成重复或丢回复，MVP 明示此限制，不宣称 exactly-once。

模型、SDK、数据库、LLM 均能注入替身；外部操作设超时及总预算。无证据不调用模型补知识，LLM 格式错误或故障不伪装成医学结论。日志按 SPEC 00 最小记录。

基础引用检查只覆盖来源标识、结论关联和内容范围等可确定规则，不能证明引用在语义上支持结论；MVP 需人工审查固定样例中的支持关系，并明确自动语义核验尚未完成。Phase 7 深化自动核验，不能把 Phase 1 的引用白名单检查称为医学事实已核实。

## 4. 本阶段不实现的内容

不实现实时 PubMed 检索、任务状态查询与持久化后台恢复、PICO、混合检索、研究质量评级、完整引用外部核验、增量同步和评估平台。不做 OCR、表格重建或保证任意 PDF 版面正确。网络接收回调与线程池是 MVP 必需能力，快速受理和长期任务体验在 Phase 2。

## 5. 输入输出契约

- ImportRequest：本地 pdf 或 pubmed_xml 路径、可选来源 URL/人工校正元数据；输出逐项 IngestionResult。PDF source_url 缺失可为 null，保留可追溯本地 source_uri；响应不暴露绝对路径给飞书。
- QuestionRequest / ResearchAnswer 遵循 SPEC 00；检索范围只接受 local，答案 sources 标明 abstract 或 full_text/extracted_text。关键词摘要数据不得标为全文。
- 检索输出 EvidenceHit：chunk、document 摘要元数据、score、score_type、rank；包含具体 chunk_id、location 和模型身份，不只返回文档 ID。
- MessageEnvelope：app_id、message_id/event_id、sender 标识及类型、chat_id、message_type、text、request_id。无可用去重 ID 的消息拒绝处理；仅文本且符合会话策略才受理。
- 去重键优先 app_id + message_id，缺失时 app_id + event_id，保留 key kind 防冲突。原子占位含 owner token/租期；失败释放必须核对 owner，不能删除他人的新租约。
- 飞书处理输出 accepted / duplicate / ignored / rejected；重复不再调用 RAG。用户错误回复不包含 SDK 原始异常、文献内容或密钥；发送失败只记录可定位结果，不递归发送错误。

输入大小、允许文件目录、PDF 页数/内存上限、线程数、在途数、租期、LLM 总期限以及消息格式上限需在进入相应任务前写入配置和用例；不在实现中用无限值代替待决项。

## 6. 数据模型

采用 SPEC 00 的 LiteratureDocument、EvidenceChunk、EmbeddingInfo、EvidenceClaim、CitationSource。来源外部身份、内容哈希、文档+分块版本+序号具备明确唯一约束；Chunk 外键引用 Document，删除策略在迁移任务明确。来源文本范围、定位、向量模型身份必须持久化。

本地 PubMed XML 无 PMID 的条目明确 rejected；一般文档 PMID/DOI 允许未知。authors 为空和出版日期不精确是正常数据，不虚构补全。PDF 标题可来自人工元数据/文档元数据/文件名，但须记录 title_origin，不能把文件名当作已核实的正式标题。

P1-01 当前落地 PublicationDate、SourceMetadata、EvidenceLocation、EmbeddingInfo、EvidenceChunk、LiteratureDocument；后续回答/claims/引用 DTO 尚未实现。文献平铺来源字段，片段保存同一来源快照；日期不补齐、字符偏移保留原文本、摘要与全文范围互斥。空片段/空 embedding_info 允许表示准备过程，不代表已经入库或可检索。结构校验不替代真实元数据核验。

P1-02 增加 PdfSourceUnit/ParsedPdf 和 pypdf 适配器，保留规范化单页文本、空页页号与同一字节快照 hash，并能验证单页证据切片；尚未持久化快照/来源单元，不能据此宣称完成入库。文件/页数/解码流/字符/协作时间限制以 P1-02 详细 SPEC 为准，不是硬资源隔离。

P1-03 增加 AbstractSourceUnit/ParsedPubmedArticle/PubmedXmlEntry/PubmedXmlBatch 和安全 XML 适配器；语法和实体安全先于条目映射，逐条报告拒绝，结构化摘要保留标签和整段偏移。批次只生成摘要文献，ID 由显式工厂提供，未做外部登记核验或数据库操作。

P1-04 增加 domain/chunking.py：不跨来源单元的原文切片、完整编码输入计数契约、版本/预算/计数结果与工作量上限。前缀不写入证据文本，未编码片段 embedding_info=null。tokenizer 是注入接口；计数替身测试通过不代表真实模型长度已实测，P1-F02 的实际模型 tokenizer 验收仍待 Embedding 适配任务。

P1-05 增加 domain/embedding.py 与 adapters/embedding.py，使用固定 E5 提交、实际 tokenizer 和 sentence-transformers CPU 编码。真实验收已验证 512/513 token 边界、来源分块与实际编码长度一致、768 维归一化向量及无网络推理；P1-F02 的实际 tokenizer 门槛在这一固定模型/样例范围内通过，不代表任意模型兼容或医学检索效果已评估。向量尚未持久化，未完成入库闭环。

P1-06 增加独立ORM、显式engine、Alembic初始迁移及本地Compose postgres。实际PostgreSQL16.15/vector0.8.7验证文献/来源单元/向量事务持久化、唯一/组合外键/模型约束和升降级；尚无DTO/ORM映射或导入用例，不能将ORM测试通过解释为离线入库闭环完成。P1-F03的存储结构部分通过，应用级幂等分类与事务编排仍待下一任务。

P1-07增加框架独立的入库应用服务、受控字节快照和DTO/ORM双向映射，单文档事务与来源唯一冲突裁决。相同来源返回already_present；同PMID快照变化needs_update；配置/元数据变化conflict，均不覆盖旧证据。真实PDF→E5→PG→读取回建通过；PubMed混合条目和批次限额、原子回滚、并发和脏数据拒绝通过。P1-F01/F02/F03在此固定模型/Python服务范围通过，不等于API/飞书或完整RAG闭环已完成。

P1-09增加QuestionRequest、EvidenceClaim、CitationSource及ResearchAnswer；真实LangGraph有空证据/生成/引用门禁分支。来源挑选可信命中字段，模型只提供带chunk_id的结论，结构门禁不证明医学语义支持关系。DeepSeek适配与真实合成证据请求通过；P1-F04/F05的结构工作流部分实现，医学人工审查及真实整链路仍待阶段验收。

本阶段 Redis 只维护短期 processing/completed 占位，不取代文献数据库事实。所有 DTO 与 ORM 分离，首任务只实现业务数据契约，不提前建一整套基础设施抽象。

## 7. 核心业务流程

入库：验证路径/格式 → 解析文档与 source units → 带位置分块 → 编码及数量/维度核查 → 开单文档事务 → 唯一约束判重并写入 → commit → 返回状态；任一写入错误回滚该文档，批量其他文档按明确策略继续并统计失败。

问答：校验输入 → 本地检索 → 可用证据判定 → 结构化生成 → 引用标识白名单及结论关联校验 → 从存储元数据渲染来源和局限 → 输出共享 DTO。相似度不是证据质量分数。

飞书：官方回调 → 文本/自身过滤 → 有界接纳及原子去重 → 工作线程调用服务 → 官方发送消息 → 记录结果并释放资源。满载和异常路径必须释放属于自己的容量及租约，成功结果保留短期去重标记。

src/feishu/ 约五个职责：入口/SDK 生命周期、事件解析与过滤、Redis 去重、受限任务分派、消息渲染与发送。具体文件名由 P0-05 确定；核心业务不得反向 import SDK。docker-compose.yml 增加 feishu_bot 服务，与 API 复用镜像/代码装配。

## 8. 异常与边界场景

空文档、扫描件、加密/损坏 PDF、未知期刊或日期、PubMed XML 混合标签、单篇条目损坏、超长句、维度/数量不符；相同内容重入、同 PMID 内容变化和并发冲突；空库、低相关度、未知引用、无证据结论、生成格式错误；SDK 非文本、机器人自身消息、重复事件、队列满、Redis 故障、发送超时和关闭时在途任务均需明确结果。

接收到的原文或用户文本含注入指令时不影响工具权限；错误与空检索分别统计。源码、测试 fixtures 中只使用人工样例或允许使用的文献片段，不能以真实医学结果断言模型正确。

## 9. 测试用例清单

| ID | 场景 | 期望 |
| --- | --- | --- |
| P1-T01 | DTO 正常、缺失/空值、非法日期、错误定位、摘要范围 | 正确校验，保留未知与精度，不补造 |
| P1-T02 | PDF 正常、空/扫描、加密/损坏、逐页定位 | 可重建来源；失败类型可区分且句柄关闭 |
| P1-T03 | 本地 PubMed XML 结构化摘要、内嵌标签、团体作者、无 PMID | 元数据完整或逐项拒绝，不访问网络 |
| P1-T04 | 实际 tokenizer 上限、超长句、空块、embedding 数量/维度不符 | 不静默截断/zip 丢失；不写半成品 |
| P1-T05 | 真实 PostgreSQL + pgvector：迁移、外键、回滚、并发判重及相似度 | 约束与事务有效，重复不增行 |
| P1-T06 | Fake 检索/LLM：有证据、空召回、错误引用、无关联结论 | 保留可追溯结果或明确拒绝，不能造来源 |
| P1-T07 | CLI/API/飞书替身调用同一服务 | 相同问题得到相同业务 DTO 语义 |
| P1-T08 | 消息类型、自身过滤、无 ID、重复及并发重复 | RAG 调用次数符合受理决策 |
| P1-T09 | 真实 Redis 原子占位、过期、owner 校验、满载及故障 | 不越过并发上限，不误删其他租约 |
| P1-T10 | LLM/发送失败、关闭线程池、SDK 超时 | 友好失败且资源释放；不无限重试 |
| P1-T11 | 真实模型与 SDK 长连接冒烟 | 实际维度、CPU 资源和收发可用，独立记录 |

## 10. 可执行验收标准

进入实施后建立上述用例对应测试文件，预期执行 `uv run pytest tests/unit tests/integration -m "not external"`，数据库/Redis 测试必须连测试专用服务，不用 Mock 冒充。真实模型、LLM 和飞书放 external 标记并分别记录命令、配置前提与结果；未执行不可标记该项通过。

验收实验：同一 PDF/本地 XML 导入两次并并发提交，文档/片段行数不增加；embedding 故障不留半成品；问题有证据时每项医学结论均有存在的片段标识，无证据时不调用 LLM；重复飞书文本只受理一次；以小容量池提交超过上限消息，观察快速拒绝及容量恢复。Compose config 有 feishu_bot，启动后用测试应用完成一次真实文本收发。

这些是未来验收步骤，不是当前已存在的 CLI/API 或测试结果。各细任务必须先固定命令、阈值和失败断言后再实现。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 0 全部验收及学习材料齐备。第一个任务 **P1-01：文献与证据 DTO、来源和定位契约**，先细化 SPEC，再写 P1-T01 的失败测试；不同时实现数据库、PDF 和飞书。

P1-01–11已按各自SPEC执行实际RED/GREEN，过程和当前回归见 [开发记录](../development-plan.md)。P1-08验证真实E5/PG检索，P1-09验证真实LangGraph及DeepSeek合成上下文，尚未验证E5/PG/LLM完整真实链路或医学专家审查。P1-10的CLI复用服务与生产装配已验证真实E5/PG，LLM为HTTP协议替身；真实付费整链路及医学人工审查仍待阶段验收。P1-11已验证真实Uvicorn TCP、生命周期共享E5及PG入库/问答，LLM仍为HTTP协议替身，真实付费整链路不因此视为通过。下一步建议飞书消息契约与事件过滤，需用户指定并细化SPEC。Phase1整体未验收。

完成 P1-F01–07、核心单元/真实集成/必要真实服务冒烟、CLI/API/飞书闭环、迁移与配置文档以及 docs/learning/phase-01/ 六份学习材料后，才可验收本阶段。完整报告核验和增量更新仍留在所属后续阶段，不因 MVP 完成而宣称全部目标达成。
