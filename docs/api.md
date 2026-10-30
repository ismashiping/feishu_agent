# FastAPI入口（P1-11）

## Phase 5 本地混合检索（2026-10-28）

默认mode=vector保留原行为；API的options增加mode=keyword|vector|hybrid、candidate_limit（默认50、1–100且不小于top_k）、keyword_query（可选ASCII文本）、date_from/date_to（成对ISO日期）。CLI对应 --retrieval-mode、--candidate-limit、--keyword-query、--local-date-from/--local-date-to。本地日期仅接纳完整出版日，未知/年/月精度条目明确排除，不补造日期。

keyword不计算查询Embedding，hybrid计算一次原问题Embedding，再在同一PostgreSQL快照内取得FTS/向量候选并按chunk_id做RRF（k=60），同分UUID升序，不合并掉同文献不同片段。任何必需通道失败即报错，不静默降级；空通道为成功。非vector模式不支持非零min_similarity，不能用余弦阈值过滤RRF/FTS。

FTS为simple ASCII词项匹配与精确PMID/DOI辅助查询，不是BM25或中文分词。中文问题可显式给英文keyword_query；不提供时keyword/hybrid返回retrieval_language_unsupported（API422），vector仍用既有多语言模型。

结果ResearchAnswer增加local_retrieval_mode/strategy、local_channel_status和retrieval_warnings；Python RetrievalResult的hits还保留keyword_rank/vector_rank/fusion_score与score_type。分数不表示医学质量，引用仍来自原证据门禁。scope=hybrid表示本地与在线来源，options.mode=hybrid表示本地算法，两者独立；在线条目不参加本地RRF，PubMed日期仍使用pubmed对象设置。

**现有数据库需显式 `alembic upgrade head` 到 p501_0003**：该迁移增加STORED search_vector与GIN，旧文献/片段/向量/ID保留，新写入自动更新。应用不会自动迁移；本次真实迁移测试仅在隔离测试库执行，没有改用户现有库。用法/范围见 [P5-01](specs/tasks/p5-01-hybrid-retrieval.md)、[学习导航](learning/phase-05/README.md)及[验收记录](phase5-acceptance.md)。以下历史说明按原时点阅读。

## Phase 4 在线来源（2026-10-28）

CLI `ask` 增加 `--scope local|online|hybrid`，API `POST /v1/questions` 接受同名 scope（默认local）及可选 pubmed 对象。pubmed 有 query、date_from/date_to（成对ISO日期）、date_field=pdat|edat、sort=relevance|pub_date、max_results（默认10，1–20）。CLI 对应 --pubmed-query、--date-from/--date-to、--date-field、--sort、--max-results。date_* 仅约束在线分支；online/hybrid 不支持本地 document_ids 或非零 min_similarity。

正式装配仍复用现有 LLM/E5/数据库资源。online 不调用本地向量检索；hybrid 合并本地和PubMed来源、预留名额并去重，不是 Phase 5 的关键词/向量融合。飞书纯文本入口继续默认local，未新增消息语法；渲染器可显示带在线来源的共享结果。

JSON 的 retrieval_scope 与实际请求一致，search_provenance 记录实际query/官方translation、时间、日期/排序、数量、截断、partial和缺失PMID。在线摘要保留真实官方URL/快照hash/字符定位与出版类型、更正关联。无摘要仅metadata_only，不能当claims证据；不自动入库、不代表全文或全部最新研究。仅本地回答的原有引用规则保留。

可选环境 PUBMED_TOOL/PUBMED_EMAIL/PUBMED_API_KEY；基础公开小请求不要求key，部署时登记真实tool/contact。每进程串行/至少0.34秒间隔，总期限30秒，最多20条/8次HTTP尝试。不同进程不协调，启用在线检索的实例需限制为一个并考虑同IP其他工具配额。API 的 pubmed_failed/invalid/timeout 对应503/502/504；获取失败不伪装成完整零结果，partial明确显示。

详情见 [P4-01 SPEC](specs/tasks/p4-01-pubmed-online.md)、[学习导航](learning/phase-04/README.md)及[验收记录](phase4-acceptance.md)。Phase 3 和更早验收记录按当时事实阅读，不当成当前仅local的限制。

## Phase 3 PICO 接入（2026-10-28）

正式共享装配默认先做一次 PICO 分类/抽取，复用 LLM_* 配置和现有模型连接，默认上限 20 秒并受研究总期限限制。每次普通问答会增加一次模型调用；即使本地没有证据也先执行规划。直接构造 ResearchService 不传 planner 时保持原行为，不代表正式入口会在规划失败后静默跳过。

结果 JSON 新增 query_plan，保留原问题、分类、PICO、候选扩展词与原文区间。现有 QuestionRequest 先去首尾空白，区间相对 query_plan.original_question 的 Python 码点索引。检索/生成仍用原问题，未接入 PubMed 或新的关键词通道。

status 新增 needs_clarification：仅 uncertain 且有具体歧义时返回，claims/sources 为空；补充问题后重新提交，无持久对话状态。缺 comparator 合法保留 null，不自动补造。规划错误为 extraction_failed/timeout，不能伪装成证据不足；API 对应 502/504，CLI 沿用错误 JSON/非零退出码，飞书显示澄清与 PICO。

完整契约、阶段验收边界见 [P3-01 SPEC](specs/tasks/p3-01-pico.md)及[开发进度](development-plan.md)。真实模型三例未验收时不声称已证明 PICO 语言理解准确率；原有命令/历史验证按各自时点阅读。

API复用已有IngestionService、RetrievalService和ResearchService，不改变当前基础RAG编排。CLI保留原有行为；飞书已完成[纯事件过滤](feishu-events.md)，尚未接入业务运行时。[任务SPEC](specs/tasks/p1-11-fastapi.md)、[执行记录](development-plan.md)。

## 安装与启动

```powershell
.venv/Scripts/python.exe -m uv sync --locked --extra ml --extra db --extra rag --extra api --system-certs
New-Item -ItemType Directory -Force data/incoming, data/snapshots | Out-Null
$env:CLINICAL_AGENT_API_IMPORT_ROOT = (Resolve-Path 'data/incoming').Path
$env:CLINICAL_AGENT_API_SNAPSHOT_DIR = (Resolve-Path 'data/snapshots').Path
$env:CLINICAL_AGENT_API_MODEL_DIR = (Resolve-Path 'models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a').Path
$env:CLINICAL_AGENT_API_MAX_IN_FLIGHT = '2'
.venv/Scripts/python.exe -m uvicorn clinical_agent.api:create_app --factory `
    --host 127.0.0.1 --port 8000 --workers 1 --loop asyncio --http h11 --ws none `
    --limit-concurrency 8 --timeout-graceful-shutdown 130 --no-access-log
```

先按[数据库](postgres.md)、[模型](local-embedding.md)说明准备固定E5资产、数据库及迁移，并显式设置数据库环境变量。API完整运行还需LLM_API_KEY、LLM_BASE_URL、LLM_MODEL；具体供应商及别名边界见[RAG说明](basic-rag.md)。密钥不要写入命令行、共享脚本或请求体。应用不自动加载.env；本示例不使用Uvicorn的--env-file。

api extra精确包含FastAPI0.162.0、Uvicorn0.54.0及HTTPX0.28.1。使用最小发行，未安装standard CLI全家桶或遥测导出器；正式uv.lock保存传递依赖。纯API契约测试可安装api extra并注入业务替身，真实服务需要四个extras。普通CLI help/doctor及api模块导入在11包基础环境仍可运行。

当前服务面向本机可信调用，不包含公网认证授权或TLS部署；上述命令绑定loopback，不启用宽泛CORS。一个worker持有一份模型/连接池/HTTP客户端与编译图；增加workers会复制模型和资源，不能忽略内存成本。启动时只校验配置并加载资源，不自动下载模型、迁移数据库或导入目录。

## HTTP契约

| 方法与路径 | 请求 | 成功结果 |
| --- | --- | --- |
| GET /health/live | 无 | 进程响应，scope=process |
| GET /health/ready | 无 | 生命周期ready，scope=runtime |
| POST /v1/documents/import | source_type和relative_path | request_id及完整BatchIngestionResult |
| POST /v1/questions | question、可选scope/options | 完整ResearchAnswer |
| GET /docs、/openapi.json | 无 | 实际OpenAPI契约及本地文档页 |

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health/ready'

$apiImport = @{source_type='pdf'; relative_path='paper.pdf'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/documents/import' `
    -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($apiImport))

$apiQuestion = @{question='已导入研究报告了哪些局限？'; options=@{top_k=5; min_similarity=0.0}} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/questions' `
    -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($apiQuestion))
```

paper.pdf必须预先放在服务端固定import_root内。XML导入将source_type设为pubmed_xml，仍由已有安全解析器和32篇批次预算处理。API不上传文件、不接受客户端allowed_root、snapshot_dir、model_dir或凭据；relative_path不允许绝对路径、盘符、反斜杠、空字符、.或..路径段，解析后必须是受控目录内已有文件。已有来源验证和快照再次核对路径，不承诺对恶意本机用户的硬文件系统隔离。

问答只支持scope=local，使用现有top_k/阈值/来源范围/文献ID过滤契约。body不接受request_id；可通过单个X-Request-ID UUID关联请求，不提供时自动生成。响应header及业务JSON保持相同ID；非法/重复ID返回400并生成安全错误ID，不回显原值。

ask接口会把问题和命中片段发送给配置的模型 API 服务，并产生供应商调用费用；应确认文献适合发送。输出保留claims.kind、关联chunk_id、实际使用的可信sources、定位和limitations。没有原文依据的医疗语义不会因结构校验而得到自动事实保证，不能省略来源和局限后作为个体诊疗结论。

## 状态与错误

入库调用正常完成时统一200，批次中的failed/rejected/needs_update/conflict和全局error_code仍原样保留；调用者必须检查result，HTTP 200不代表所有条目入库成功。问答answered和insufficient_evidence均200；空召回不调用模型，也不代表文献证明无效。

错误JSON为request_id、error_code、固定message和retryable；不返回Pydantic的input、请求体、文件路径或上游原始异常。OpenAPI错误schema与实际ApiError一致。

| HTTP状态 | 场景 |
| --- | --- |
| 400 | 无效request_id、Content-Length、受控文件路径或无法解码的JSON |
| 408 | 请求体读取超过10秒预算 |
| 413 | 声明或实际请求体过大 |
| 415 | 业务请求非application/json或使用压缩body |
| 422 | DTO/JSON格式或context_limit |
| 404 / 405 | 路径不存在／方法不支持，仍为受控JSON |
| 502 | 模型输出格式或引用无效 |
| 503 | busy、not_ready或已知上游不可用；busy含Retry-After=1 |
| 504 | 检索/研究/生成timeout |
| 500 | 损坏记录、模型空间不匹配或未知内部故障 |

retryable仅表示调用者可决定重试，API不自动重试。入库commit后断线/响应失败不能推导数据库已回滚；按原有幂等重入规则核对。没有后台任务ID、202确认、持久恢复或Exactly-once承诺，Phase2体验尚未实现。

## 容量与关闭

CLINICAL_AGENT_API_MAX_IN_FLIGHT默认2、范围1..4，覆盖导入和问答的运行及已提交任务；超过容量立即503。使用标准ThreadPoolExecutor加接纳上限，不无限排队。同步模型/数据库/LLM在工作线程执行，健康检查不占业务池，事件循环可继续响应。

HTTP等待取消不会强行停止正在工作的线程；容量绑定到底层Future实际完成，不能因客户端断开而提前复用。关闭时先标记not_ready/停止接纳，等待实际线程结束，再退出HTTP/engine上下文。底层协作预算和timeout不是硬墙钟保证；Uvicorn的graceful参数也不能安全强杀Python线程，底层调用长期不返回时关闭仍可能等待。

CLINICAL_AGENT_API_MAX_REQUEST_BYTES默认16384、最大65536，按UTF-8实际bytes统计并包含JSON包装；即使业务字符数合格，较长options也可能触发传输上限。既检查Content-Length也累计分片，默认拒绝压缩体。Uvicorn limit-concurrency限制连接/任务，与业务池容量含义不同，服务器自身拒绝的503不保证采用应用的JSON格式。

ready仅代表资源生命周期已装配，不在每次探针访问数据库/LLM；服务随后故障时业务接口仍可能返回错误。启动/关闭失败只报告固定startup_failed/shutdown_failed，排错先核对目录、固定模型资产、数据库环境/迁移和供应商配置。

## 实际验证边界

真实FastAPI与HTTPX TestClient覆盖接口/隐私/大小、满载、取消和生命周期。另用实际Uvicorn loopback TCP、固定E5 CPU及专用PostgreSQL完成PDF导入/重入、XML导入与引用问答，实际模型只加载一次；LLM明确为HTTPX MockTransport，没有发起真实DeepSeek付费请求。没有将前序独立真实LLM记录冒充本轮整链路验收。

基础11包环境与api-only23包环境分别验证导入/CLI、真实生命周期/路由；未新建wheel或验证Linux、公网部署、生产性能、医学专家支持关系评审。Path.resolve逃逸测试使用明确解析替身，不声称Windows实际符号链接权限已验收。已撤销四节点修订保持撤销，Phase1飞书与完整阶段验收仍待后续任务。

## Phase 6 证据分析

`POST /v1/analyses` 复用 `/v1/questions` 请求结构，question 为科研想法，options/scope/pubmed 仍遵循既有校验。返回 AnalysisResult：研究方法、五维相似性、候选缺口、双侧比较、可信文献来源及检索追溯。澄清不检索；空结果不判创新；非法引文拒绝。普通 `/v1/questions` 保持原行为。本入口不是 Phase 7 报告。真实医学验收状态见 [阶段记录](phase6-acceptance.md)。

## Phase 7 科研选题现状调研报告

`POST /v1/reports` 与 questions 使用同样请求体，返回 `report`（结构化报告）及由该对象渲染的 `markdown`。question 是用户科研想法；无需手工传入分析。复用规划/检索/Phase6，核对来源快照与有PMID来源的官方元数据，再做逐项模型支持审核。status 为 verified/verification_incomplete/rejected，content_status 独立表达覆盖范围。verified 不代表医学正确或创新。原 questions/analyses 保持；实际验收及待审项见 [阶段记录](phase7-acceptance.md)。

## 探索型发现增量

问答、分析、报告请求共用Planner澄清决策，缺C/O/模态本身不再阻断新契约。请求scope默认hybrid；仅本地时显式提交`"scope":"local"`，仅在线可提交`"scope":"online"`。mode与scope独立。QueryPlan新增可选blocking_ambiguities，空列表表示非阻断，null兼容旧输出；响应仍保留原文、候选词与实际来源追溯。见[增量SPEC](specs/tasks/exploratory-discovery.md)。
