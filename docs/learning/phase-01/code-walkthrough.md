# 按真实调用顺序解析Phase 1

阅读前先运行[Demo](tutorial.md)。下面路径都指向当前源码；函数存在不等于对应真实外部服务已经验收，结果以[阶段报告](../../phase1-acceptance.md)为准。

## 1. 入口与资源装配
[cli.main](../../../src/clinical_agent/cli.py)先解析参数，再由_business构造ImportRequest或QuestionRequest；非法输入只输出固定错误和request_id。help在装配前退出，因此不需要密钥和数据库。open_runtime设置日志与关联ID，实际业务工厂来自[command_runtime](../../../src/clinical_agent/command_runtime.py)。

open_ingestion进入上下文时才检查可选依赖、读取DatabaseSettings、验证本地模型并构造OfflineReader/LocalEmbedder/PostgresStore。open_research装配同一检索/生成逻辑：RetrievalService(PostgresRetriever)加open_llm形成ResearchService。上下文退出关闭借用期内拥有的数据库引擎与HTTP客户端；不在模块导入时联网、迁移或下载模型。

## 2. 从输入文件到可追溯片段
[OfflineReader.read](../../../src/clinical_agent/adapters/offline.py)验证路径在allowed_root内，以受控快照解析。PDF调用[parse_pdf](../../../src/clinical_agent/adapters/pdf.py)，XML调用[parse_pubmed_xml](../../../src/clinical_agent/adapters/pubmed_xml.py)，正文、元数据、hash和来源单元组成ParsedSource。源数据错误逐项拒绝或返回批次错误，不虚构PMID。

[IngestionService.ingest](../../../src/clinical_agent/application/ingestion.py)先read，再对每个有效条目调用_ingest_source。后者依次取tokenizer_profile→[chunk_source](../../../src/clinical_agent/domain/chunking.py)→embed_chunks→PreparedIngestion重校验→store.save。每次调用前后检查预算；编码错或维度错不进入事务。批次按文档处理，不承诺整个批次单一事务。

[load_local_embedder](../../../src/clinical_agent/adapters/embedding.py)验证模型manifest、文件集合/哈希与固定revision；LocalEmbedder使用实际tokenizer计数，串行保护模型并验证输出数量、维度和归一化。模型加载可达数百秒预算，不能拿一次加载耗时当单次问答延迟。

## 3. 保存和并发幂等
[PostgresStore.save](../../../src/clinical_agent/adapters/postgres/store.py)将PreparedIngestion映射到独立ORM；[models](../../../src/clinical_agent/adapters/postgres/models.py)的外键/唯一约束与Alembic迁移共同保证一致性。事务提交才算imported。重复返回数据库已有的canonical document_id；同外部身份变更内容返回needs_update；处理配置矛盾返回conflict。

load不是“读出JSON就信任”：回建DTO、来源单元与切片校验能发现存储污染。原始文字与元数据是证据真相，不能让模型生成书目信息再写回库。

## 4. 查询、图分支与引用门禁
[RetrievalService.retrieve](../../../src/clinical_agent/application/retrieval.py)校验请求，编码问题，调用[PostgresRetriever](../../../src/clinical_agent/adapters/postgres/retrieval.py)做模型一致的过滤与余弦相似度排序，返回EvidenceHit。options在各层保持一致，不能偷改阈值获得看似更好的答案。

[ResearchService.answer](../../../src/clinical_agent/application/research.py)深复制请求，创建本次deadline，禁用LangSmith自动追踪，然后调用已编译图。_retrieve检查结果和options；_route按hits进入empty或prepare；_prepare限制上下文；_generate用剩余预算调用生成器；_validate调用[build_answer](../../../src/clinical_agent/domain/citations.py)。每次请求状态独立，图可以共享。

[LangChainAnswerGenerator.generate](../../../src/clinical_agent/adapters/langchain_generation.py)构造标准 SystemMessage/HumanMessage，通过 BaseChatModel.invoke 调用模型并验证 AIMessage。它不读取供应商配置；[open_llm](../../../src/clinical_agent/adapters/llm.py)按 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL 装配通用 ChatOpenAI、temperature=0、无重试及受限 HTTP 客户端，保留 JSON mode、响应大小/期限与供应商包校验。LangGraph 管理执行状态，LangChain 管理标准调用，配置 URL 指定的 API 服务商提供模型。parse_draft拒绝重复键、非JSON、格式错误等；build_answer拒绝未知/重复引用并由命中构造CitationSource。answered与insufficient_evidence是业务结果，generation_failed/citation_invalid是错误，不能互相伪装。

## 5. API共享服务和线程生命周期
[create_app](../../../src/clinical_agent/api.py)创建路由和传输边界；lifespan进入[open_api_runtime](../../../src/clinical_agent/api_runtime.py)，共享模型/服务和WorkerPool。请求只转换DTO并交给同一能力。HTTP等待被取消时，底层同步线程可能继续，所以容量随真实Future完成释放；关闭先停止接纳，再排空，最后关闭共享资源。

## 6. 飞书五模块顺序
1. [main](../../../src/feishu/main.py)：FeishuSettings→build_runtime→run_sdk；Receiver将官方SDK字段映射到既有事件契约。固定SDK版本的私有生命周期兼容点有专项测试，升级必须重验。
2. [events.filter_event](../../../src/feishu/events.py)：拒绝自身/机器人/非文本、非法身份或未被提及的群消息；只把accepted envelope交给Dispatcher。
3. [dedup](../../../src/feishu/dedup.py)：Redis SET/Lua以app+message优先、event后备做原子owner占位，Redis TIME约束租期；故障fail closed。
4. [worker.Dispatcher.submit](../../../src/feishu/worker.py)：先拿容量，再占位，accepted后线程运行共享ResearchPort；保留request_id，结束前核owner/deadline，再向Sender交接。满载不占位。研究失败产生固定失败投递。
5. [sender.Sender](../../../src/feishu/sender.py)：有界队列/单线程渲染，完整引用或整体超长提示，临HTTP前再核owner/deadline。OfficialMessageAPI每项最多一次POST；明确成功complete，确定未发送release，不确定保留TTL。发送失败不递归发错误。

## 7. 关闭与异常为什么这样做
BotRuntime先等待worker，再等待sender，成功后逆序关闭HTTP/Redis/研究上下文。超时返回False而保留依赖，CLI继续有限等待；Python不能安全强杀正在运行的线程。信号退出与投递确认是不同事实，SIGTERM后的API退出143必须结合Uvicorn关闭日志判断。Redis与飞书没有分布式事务，TTL和owner解决基本幂等，不保证任何崩溃时点exactly-once。

调试时先看request_id及固定错误码，再按[排错](troubleshooting.md)进入对应层；禁止临时打开SDK原始日志把密钥、连接URL或消息正文写进证据。
