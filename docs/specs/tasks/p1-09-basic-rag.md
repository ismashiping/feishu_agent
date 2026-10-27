# P1-09：基础RAG工作流与证据关联回答

状态：本任务已验收，2026-10-27；实施前冻结SPEC并记录实际RED/GREEN，依赖P1-01–08。本任务只实现Python服务，不进入CLI/API/飞书或Phase2–9。

## 1. 背景及目标

复用已验收RetrievalService，使用真实LangGraph编排检索→空证据分支或生成→引用门禁→回答。保持生成端口可替换，书目及定位由命中构造，模型不能新增来源。结构门禁不能证明医学语义支持关系。

## 2. 功能需求

QuestionRequest继承RetrievalRequest并要求request_id UUID。ResearchService在构造时编译一次StateGraph，每次调用独立状态，无checkpointer、工具、重试或循环。检索失败传播受控错误；仅成功空hits返回insufficient_evidence且不调用LLM。非空hits按原排名整体提供，不截断证据；超过上下文预算明确context_limit，不静默删证据。

AnswerGenerator.generate(GenerationInput, *, timeout_seconds)返回严格JSON字符串。模型只能返回claims，每条text、kind(evidence/inference/uncertainty)、evidence_chunk_ids及limitations；claim_id由应用依序赋予c1/c2。所有类别均需至少一个本次上下文chunk_id；重复/未知ID、无引用、伪造书目字段或坏格式拒绝整个回答，不局部发布。模型不可生成外部PMID/DOI/URL，文本中的这类显式书目标记保守拒绝，可信标识只在sources中呈现；不能机械识别所有自然语言编造，仍需人工审查。

用户已指定DeepSeek端点/模型及环境变量。实现单个HTTPX REST适配器，按官方chat/completions协议发送JSON mode，不引入多家SDK。显式DeepSeekSettings读取DEEPSEEK_API_KEY/BASE_URL/MODEL，不读取.env，SecretStr隐藏密钥。仅https://api.deepseek.com（可带/v1）允许，避免错误端点泄露凭据；模型显式必填，不默认假定某模型仍可用。HTTP无工具、无重定向、无自动重试、trust_env=false；客户端有界连接池并由context manager负责关闭。

## 3. 非功能需求

新rag可选extra精确锁定langgraph1.2.17、langsmith0.14.12及httpx0.28.1；LangSmith用于显式tracing_context(enabled=False)，避免环境追踪上传问题/原文；不改变全局环境。导入research模块不加载LangGraph/HTTP或连网；构造服务才装配图。基础doctor及不含rag/db/ml环境保持可用。

ResearchLimits默认总预算90秒、生成60秒、上下文24000字符（GenerationInput JSON，含问题/片段/固定指令/schema）、模型输出32000 UTF-8 bytes；正数/有限/严格。总预算为协作检查，不承诺抢占检索或模型线程。生成端口收到min(剩余总预算,生成预算)。HTTP connect/write/pool至多5秒，read以剩余预算约束；每次读块后检查deadline，累计响应最多128000 bytes，不信任Content-Length。HTTP inactivity timeout及协作计时不是硬墙钟保证。

## 4. 本任务不实现的内容

无在线检索/PICO/混合排序/研究质量评级、完整报告/外部文献核验/自动语义蕴含判断、生产性能、持久任务、业务入口。无数据库迁移或改动既有入库/检索逻辑。真实LLM只用合成片段验证协议与来源关联，不把单次结果当医学效果评估。

## 5. 输入输出契约

GenerationInput：question、evidence(1..20个GenerationEvidence：chunk_id、text、content_scope、location)、instructions固定字符串、output_schema(由GenerationDraft生成)。无本机路径、标题/作者/PMID/DOI、向量或隐藏凭据。把用户问题和原文序列化为数据，system规则禁止把原文指令作为系统命令；模型没有工具权限。

GenerationDraft：claims1..20，每条text严格trim1..2000，kind枚举，evidence_chunk_ids1..20唯一UUID，limitations0..5、每条1..500。未知字段拒绝；不修复markdown围栏/截断JSON、不接受bytes/非字符串。JSON重复键拒绝，NaN拒绝。

ResearchAnswer：request_id、status、claims、sources、limitations、retrieval_scope=local、generated_at带时区UTC。answered必须有claims及sources，insufficient_evidence两者都空；claim_id连续唯一、所有引用均存在且每个source片段实际使用，无多余来源。固定局限至少说明本地检索非最新、仅结构关联非语义事实验证、科研辅助用途；摘要/提取文本范围如实附加，不宣称读过全文或证据证明无效。

ResearchError闭集：model_output_invalid、citation_invalid、generation_failed、generation_timeout、research_timeout、context_limit、research_failed；外部异常文字不进入错误。已知RetrievalError保留重建安全码；其他检索异常变retrieval_failed。格式错误与引用关系错误分别报告。

## 6. 数据模型

新增domain/research.py：QuestionRequest、GenerationEvidence/Input/Draft及DraftClaim、EvidenceClaim、CitationEvidence、CitationSource、ResearchAnswer、ResearchLimits/ResearchError。CitationSource只从命中可信摘要挑选document_id、标题/来源、作者、精度日期、期刊、DOI/PMID、source_type/source_url、content_hash、content_scope和实际使用的片段(ID、text、location)，不包含source_uri或EmbeddingInfo。未知值保持null/空作者，不拼造URL。

domain/citations.py提供独立parse_draft及build_answer；检查白名单、同document_id书目一致、重复/缺失关联，并生成确定顺序来源（首次使用顺序）。不依赖LangGraph/HTTP/SDK。重验证命中DTO，使用深副本防止外部generator改写可信来源；返回答案可JSON往返。

## 7. 核心业务流程

校验请求/限制→建立deadline→图retrieve节点调用注入RetrievalPort→重验证并核对options→无hits走empty节点生成明确不足结果→否则prepare完整上下文/预算检查→generate节点调用注入端口(一次)→输出大小/严格JSON/schema→validate节点执行引用门禁及可信来源构造→预算/UTC结果→END。每请求不在service上保存问题/证据/草稿。

DeepSeek适配器context manager创建/关闭HTTPX Client，可注入MockTransport；生成只接受finish_reason=stop、单个assistant choice、无tool_calls、非空content。不接受length截断/content_filter。HTTP鉴权/限流/5xx/连接失败为generation_failed，timeout为generation_timeout，响应包/输出格式错误为model_output_invalid；不记录错误body、Authorization或reasoning_content。

## 8. 异常与边界场景

输入坏/不支持scope、空召回、检索失败、坏retriever选项、坏来源、模型失败/超时/空白/额外字段/未知引用/重复引用/缺引用、JSON重复键/NaN/过大、上下文过大、总预算前中后到期。摘要不标全文，来源本机路径不进上下文/回答。并发两题共享编译图无状态串扰；LangSmith环境开启仍无追踪网络。模型含指令的证据保持普通字符串，不执行任何工具。

## 9. 测试用例清单

- 严格请求/Draft/回答DTO、JSON往返及空/answered不变量、UTC/精度/来源范围；书目不补造。
- 纯引用函数：合法多claim、多文档/重复使用片段，未知/缺失/重复引用拒绝，模型附加PMID/title等拒绝，源快照不一致拒绝，sources只保留实际引用。
- 真LangGraph+Fake ports：分支与调用顺序、一次编译/请求隔离、错误不伪装不足、预算与上下文限制、输出异常、生成器修改输入不能修改可信命中。
- HTTPX MockTransport：官方JSON mode/path/header/timeout/无tools、连接池生命周期、环境密钥不回显、端点/模型错误配置、4xx/5xx/timeout、截断/工具/坏包/超大流拒绝及资源关闭。
- 独立真实DeepSeek一次合成片段请求，保存脱敏的请求模型/响应模型/status/claims数量/来源关联结果；人工阅读合成答案支持关系，明确固定样例范围。
- 默认回归、Ruff/mypy、正式lock/pip及不含rag/db/ml基础环境/doctor；依赖变更需锁定并核查旧版本保持。

## 10. 可执行验收标准

先`pytest tests/unit/test_research.py -q`确认新功能缺失RED，再最小GREEN；HTTP适配器独立`tests/integration/test_deepseek.py`先RED后GREEN。真实LangGraph必须运行，不以自建状态机替代。实际命令与结果保存在.artifacts/p1-09-20261027-01并汇总开发计划；所有pytest独立basetemp/cache，保存/恢复pytest环境。真实模型测试标external，无配置时不能以skip声称通过。

依赖通过`uv lock`及`uv sync --locked --extra ml --extra db --extra rag`，不升级既有版本；执行默认pytest、Ruff src/tests/alembic、mypy src、uv lock --check --offline、uv pip check及新基础环境doctor。无既有检索/数据库改动时不重复启动全套数据库，仅记录P1-08实测边界；本任务真实LLM使用Fake检索，不能声称E5/PG/LLM全链路实测。

## 11. 阶段依赖及完成定义（DoD）

本任务以真实LangGraph、生成适配/HTTP协议、引用结构门禁、默认回归与真实LLM验证分别验收。若真实服务不可用保留代码及全部独立检查，明确未验证内容，不称完整真实RAG验收。Phase1整体仍未完成，不生成阶段完成学习文档。完成后停止；后续业务入口任务待用户指定。

依据：[LangGraph图API](https://docs.langchain.com/oss/python/langgraph/graph-api)、[LangGraph PyPI](https://pypi.org/project/langgraph/1.2.17/)、[禁用追踪](https://kb.langchain.com/articles/2491399069-how-do-i-disable-or-toggle-langsmith-tracing-during-execution)、[DeepSeek JSON](https://api-docs.deepseek.com/guides/json_mode/)、[官方请求/响应](https://api-docs.deepseek.com/api/create-chat-completion/)、[HTTPX timeout](https://www.python-httpx.org/advanced/timeouts/)。用户指定deepseek-chat，当前文档展示其他模型名，需实际请求验证兼容性，不擅自替换。
