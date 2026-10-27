# P1-11：FastAPI入库与问答入口

状态：已验收，2026-10-27；实施前冻结SPEC并执行实际RED/GREEN，依赖P1-01–10。沿用当前基础RAG，不恢复已撤销的四节点修订。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

通过本机HTTP API复用现有离线入库与ResearchService，明确输入输出、来源限制、并发与资源生命周期。API不实现新的医学逻辑。

## 2. 功能需求

应用工厂create_app，lifespan启动时创建一次固定E5、engine、DeepSeek HTTP客户端、入库/检索/问答服务及编译图，关闭时先停止接纳并等待实际线程工作结束，再关HTTP/engine。不每请求加载模型，不自动下载/迁移/入库。

- GET /health/live：进程响应检查，不访问模型/DB/LLM。
- GET /health/ready：资源生命周期ready状态，不宣称数据库/供应商实时可达。
- POST /v1/documents/import：JSON source_type(pdf/pubmed_xml)、relative_path；服务器固定import_root/snapshot_dir/model_dir，客户端不能改目录或密钥。调用既有IngestionService。
- POST /v1/questions：JSON question、scope=local及options，复用RetrievalRequest字段，服务端建立QuestionRequest；返回完整ResearchAnswer。
- /docs和/openapi.json提供实际明确DTO契约。错误响应记录request_id/error_code/message/retryable，不返回原始异常、校验input/body、路径或密钥。

## 3. 非功能需求

api可选extra精确固定FastAPI0.162.0、Uvicorn0.54.0及已有HTTPX0.28.1；使用最小发行，不装standard全家桶或遥测导出器。若实际使用AnyIO则显式锁其选定兼容版本。旧包版本保持。新增api.py/api_runtime.py，不改既有核心规则/CLI/迁移。

默认仅本机可信调用，无公网鉴权部署承诺；文档启动绑定127.0.0.1、workers=1、limit-concurrency=8、关闭access log避免URL泄漏。并发业务默认2，上限4，标准ThreadPoolExecutor加非阻塞容量接纳；容量覆盖运行和已提交任务，满载503，无无限排队。事件循环不运行同步模型/DB/LLM；健康检查不占业务池。

取消HTTP等待不代表终止线程，容量由底层Future真正结束/取消后释放；shutdown(wait=True)在独立线程等待完成后才关服务资源。外部调用沿用已有预算/超时，不能硬杀线程或承诺硬关闭期限。线程池submit失败回收容量，关闭后不再接纳。

请求体上限默认16384 bytes、配置最大65536；既检查Content-Length也累计实际ASGI分片，body读取预算10秒。只接收JSON业务请求，禁止压缩请求体以避免解压歧义。X-Request-ID可为单个合法UUID，否则400，不回显非法值；未提供则生成uuid4。所有响应尽量携带一致X-Request-ID和业务request_id。

## 4. 本任务不实现的内容

无文件上传/下载、任意本机路径读取、目录递归、CORS放开、用户鉴权平台、公网部署、后台任务/202、持久任务/状态轮询/取消、Redis/飞书、Docker镜像部署、四节点Agent/RAGAS/LangSmith新功能。Phase2异步体验保持后续范围。

## 5. 输入输出契约

ImportBody：source_type枚举、relative_path严格字符串1..512；拒绝绝对路径、反斜杠/盘符/空字符、.或..路径段；resolved路径必须是固定import_root内已有普通文件，符号链接逃逸也拒绝。读取前仍由OfflineReader二次核验，非恶意本机用户的硬文件系统沙箱不在本任务承诺。

QuestionBody继承RetrievalRequest，不接受body request_id或目录/凭据字段；请求关联来自header。ImportResponse为request_id和BatchIngestionResult，所有有结构的批次结果统一200，包含失败/拒绝/needs_update/conflict，调用者必须检查entries/error_code。answered和insufficient_evidence均200；只返回原服务的真实状态。

错误：400 invalid_request_id/source_invalid/invalid_headers，413 request_too_large，415 unsupported_media_type，408 request_timeout，422 invalid_request/context_limit；503 busy/not_ready/上游不可用，504业务timeout，502模型格式或引用无效；损坏数据/模型空间不符和未知内部故障500。不存在/方法错误保持404/405但使用受控JSON。错误message使用固定文字，retryable仅指可由调用者决定重试，不自动重试。满载Retry-After=1。

## 6. 数据模型

api_runtime.py定义ApiSettings（CLINICAL_AGENT_API_前缀，model_dir/import_root/snapshot_dir必填，max_in_flight/max_request_bytes有界，不读.env）、ImportBody/ImportResponse、QuestionBody、ApiError、HealthReport和ServiceBundle。复用原业务DTO及现有IngestionPort/ResearchPort；SDK/ORM不进入API契约。

API装配open_api_runtime先校验应用/DB/LLM/目录配置，再加载一次模型，在同一个engine和HTTP上下文中构造两项业务服务。create_app可注入settings和runtime_factory；测试无需真实模型/数据库/LLM。导入api模块本身不加载FastAPI或业务extra，构造工厂才需要API依赖，lifespan才读取配置/创建服务。

## 7. 核心业务流程

启动：构造工厂→lifespan加载配置及日志→线程内enter runtime→创建有界池→ready。请求：header/体积/类型边界→Pydantic校验→确定服务器路径或QuestionRequest→非阻塞接纳→业务线程执行及结果重验证/关联ID检查→返回完整JSON。释放容量依靠真实Future完成回调。关闭：ready=false/关闭接纳→等待池→退出runtime，线程结束前不释放engine/HTTP。

API没有可导入的全局app单例，不在模块导入时装配。启动配置/资源故障向ASGI服务器报告固定startup_failed，已创建资源按context释放，不输出原始异常。请求级结构化日志仅event/request_id/error_code等白名单，不记录问题/原文/路径/异常。

## 8. 异常与边界场景

缺配置/模型文件、启动中途失败、关闭中途失败；坏JSON/未知字段/错误UUID/重复header、超大声明或流式分片、压缩/非JSON体；路径穿越/符号链接逃逸/不存在；DTO/结果错误、request_id错配、空召回、部分入库、上游故障、满载及恢复；取消运行中请求不提前释放容量、关闭等待实际工作、多个应用实例隔离。已有入库commit后HTTP失败/断线不等于回滚，调用者按原幂等规则核对。

## 9. 测试用例清单

- 先测试工厂/路由/契约缺失RED，真实FastAPI TestClient和HTTPX ASGI协议验证，不以手写HTTP服务替代。
- 正常完整问答/空证据/批次状态，来源及kind/定位保持，未知输入和bad schema无input泄漏。
- 目录固定、绝对路径/..及符号链接逃逸拒绝，不能body传root/model/凭据；header关联、404/405、请求大小/分片/媒体类型。
- 全部已知错误映射与未知异常脱敏；坏result及错题拒绝，受控日志不含问题/凭据。
- lifespan仅创建一次、请求不重装、启动失败释放、关闭次序；事件循环健康不被阻塞，满载/异常/submit失败/取消/关闭容量管理。
- 标准Uvicorn真实loopback HTTP冒烟，固定本地E5+专用PG的API PDF/XML导入/重入/问答装配；LLM若无有效当前环境使用明确HTTP替身，不重用聊天泄漏密钥，不冒充付费整链路。
- 默认回归、CLI/import隔离、Ruff/mypy、锁/pip、无extra基础环境help/doctor。

## 10. 可执行验收标准

先`pytest tests/integration/test_api.py -q`观察因目标模块未实现RED，再最小GREEN；runtime/pool单元测试亦先RED/GREEN。所有pytest保存/恢复PYTEST_ADDOPTS/PLUGINS，独立basetemp/cache。证据.artifacts/p1-11-20261027-01，真实/替身与未验证内容分别记录。

官方核查后精确加入api extra并锁定，安装保留ml/db/rag。执行默认pytest、Ruff src/tests/alembic、mypy src、uv lock --check --offline、uv pip check。实际服务需显式专用clinical_agent_test_库/独立Compose project/随机密码/reset开关，Compose明确--env-file .env.example，不读用户.env；结束清fixture、停本次容器保留卷。

## 11. 阶段依赖及完成定义（DoD）

接口/生命周期/有界执行/脱敏/真实框架与网络入口、相关回归及操作文档齐备后验收P1-11，保持已撤销草案不恢复。Phase1尚有飞书与完整阶段验收/学习材料，不自动进入后续任务。

依据：[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)、[同步/异步](https://fastapi.tiangolo.com/async/)、[Uvicorn工厂及并发限制](https://uvicorn.dev/settings/)、[标准线程池](https://docs.python.org/3.12/library/concurrent.futures.html)。当前PyPI版本/兼容性及安装实证记录在开发计划。
