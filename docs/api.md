# FastAPI入口（P1-11）

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
