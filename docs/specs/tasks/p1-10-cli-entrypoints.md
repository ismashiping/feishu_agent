# P1-10：CLI离线入库与问答入口

历史记录说明（2026-10-27）：本文供应商专属模块、配置和实测结果属于任务交付时点。当前已移除专属适配器，统一使用 `adapters/llm.py` 的 `LLMSettings/open_llm` 和 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`，详见通用模型边界 SPEC；旧变量不会回退读取，迁移后未新增在线验收。

状态：已验收，2026-10-27；实施前冻结SPEC并执行真实RED/GREEN，依赖P1-01–09，仅CLI/Python装配，不进入API或飞书。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

让已实现的离线入库和证据关联问答通过已安装module/console入口调用。入口只解析、装配、调用与序列化，不复制业务规则。

## 2. 功能需求

保留doctor、空参数和help行为。新增`ingest --source-type pdf|pubmed_xml --path PATH --allowed-root DIR --snapshot-dir DIR --model-dir DIR [--request-id UUID]`；单文件，XML可含现有32条批次。新增`ask --question TEXT --model-dir DIR [--top-k 5] [--min-similarity 0] [--request-id UUID]`，只检索local，实际发送命中片段至配置DeepSeek。模型/数据库/密钥使用现有显式配置，不读取.env，不在argv接受密钥，不自动迁移或下载。

入库复用OfflineReader、LocalEmbedder、PostgresStore、IngestionService；问答复用RetrievalService/PostgresRetriever/ResearchService/DeepSeekGenerator。问答返回完整结构化claims/sources/limitations，不丢弃kind或定位。ingest不需要DeepSeek配置或rag依赖；help/doctor不需要任何业务extra。

## 3. 非功能需求

不新增依赖或修改锁。仅cli.py与新增command_runtime.py生产改动，现有核心业务保持。延迟导入所有db/ml/rag，装配先验证所需配置再加载模型，外部资源用context manager确定关闭顺序：生成HTTP客户端先于engine释放。模型为同步CPU对象无公开close，不假造关闭API；进程退出回收。进度/错误日志到stderr，stdout保留单个JSON文档；CLI在输出前先完成context退出，退出异常不发布成功结果。Unicode中文在Windows非UTF8默认编码下也须可JSON解析。

## 4. 本任务不实现的内容

无目录递归/通配批导、交互会话、stdin管道输入、输出文件、漂亮Markdown报告、配置文件/自动.env、在线检索、schema迁移、后台任务、API/飞书。CLI不证明任意医学问题有正确答案。

## 5. 输入输出契约

必需路径均显式，不默认把cwd当受控目录。ingest建立ImportRequest（UTC时间由CLI提供），问答建立QuestionRequest（trim1..4000、UUID、top_k1..20、有限阈值[-1,1]）。数字转换和Pydantic错误不得回显原始值/问题/路径。argparse失败保留usage但用固定错误文字；退出2，无业务装配。request_id可传入或uuid4生成，同时用于runtime日志/答案关联。

成功ingest stdout为`{"request_id":UUID,"result":BatchIngestionResult}`；成功ask stdout为ResearchAnswer本身。输出不含路径配置或密钥，保留现有业务DTO。退出0：ingest所有entries均imported/already_present且无batch error；ask answered或insufficient_evidence。退出3：ingest空批/全局错误或至少一条rejected/failed/needs_update/conflict，仍输出完整批次结果供判定。退出1：运行/装配资源错误，stdout空。退出2：参数/配置/缺可选依赖，stdout空。KeyboardInterrupt退出130，stdout空，不强杀线程。

业务错误stderr为单行JSON（日志可另占行）：request_id、error_code。错误码仅已知RetrievalError/ResearchError闭集或固定invalid_configuration、missing_dependency、command_failed、interrupted；不发布原始异常/traceback。由于参数解析尚未建立request_id，语法失败使用argparse固定文字，不假造JSON错误协议。doctor原有输出/退出及日志语义保持。

## 6. 数据模型

新增command_runtime.py内IngestionCommand（model_dir/snapshot_dir Paths）及两个Protocol（ingest/answer），仅覆盖实际消费者。装配函数open_ingestion/open_research返回对应服务的context manager；cli.main支持注入factory，便于独立验证。CLI结果必须经BatchIngestionResult/ResearchAnswer重验证，校验问答request_id一致，防替身/适配器返回错题。CLI无ORM或SDK DTO。

## 7. 核心业务流程

parse/help→建立关联UUID/业务DTO→open_runtime配置结构化日志→所需factory：配置校验→模型加载→engine context→可选HTTP context→应用服务→执行→重验证DTO→退出资源context/runtime→输出JSON→退出码。参数/请求错误在任何资源创建前返回；需要的extras缺失输出missing_dependency，不误把模块内部任意ImportError都当缺依赖。

## 8. 异常与边界场景

空/超长中文问题、NaN/Infinity阈值、top_k越界、无参数值/非法ID/重复未知参数、路径错误/受控根之外、缺配置/可选包、坏模型资产/连接失败、batch部分失败/重入/冲突、问答无证据、模型/引用故障、输出DTO不匹配、context退出失败、Ctrl-C。来源文件错误仍按既有入库服务返回批次error，不擅自改变其业务分类。CLI不打印argv/原始异常/密钥/本机路径字段。

## 9. 测试用例清单

- 注入factory：命令映射、request_id/UTC、参数早失败、help零装配、完整answer JSON、批次全部状态与0/3退出、错误脱敏与空stdout、context正常/异常/关闭异常释放、Ctrl-C。
- 装配替身：真实应用服务对象，ingest不读取DeepSeek，配置先于模型，model_dir/snapshot_dir传递，HTTP/engine逆序释放；不假造模型close。
- 安装入口子进程：module/console help、非法输入、缺配置、中文输出；受限环境不读.env；基础无extra环境help/doctor及missing_dependency。
- 实际CLI→本地E5→专用PostgreSQL：合成PDF/XML导入、重入、问答命中；LLM如未配置不重用聊天披露密钥，使用明确标注HTTP替身验证装配，真实付费LLM需当前有效配置，不以替身宣称实测。
- 相关默认回归、Ruff/mypy、manifest/lock不变；不改既有业务测试取得GREEN。

## 10. 可执行验收标准

先创建并运行`pytest tests/unit/test_command_cli.py -q`观察因目标命令/装配未实现RED，再最小GREEN；装配测试另行RED/GREEN。所有命令/结果记入.artifacts/p1-10-20261027-01与开发计划，各轮独立basetemp/cache，保存/恢复pytest环境。执行默认pytest、Ruff src/tests/alembic、mypy src、uv lock --check --offline、uv pip check。

真实数据库仅用专用clinical_agent_test_库/独立Compose project、显式reset开关/随机密码，不读用户.env；明确--env-file .env.example，运行后核对fixture并停止本次容器，保留卷/其他资源。新建无extra基础环境复验help/doctor。无真实服务配置时必须列出未验证项，不能用skip/fake冒充完成真实整链路。

## 11. 阶段依赖及完成定义（DoD）

SPEC/RED/GREEN、命令/输出/退出/关闭/脱敏、实际安装入口、基础隔离与默认回归通过并记录真实业务边界后验收本任务。Phase1仍有API/飞书及阶段验收，不生成完成学习材料、不自动开始下一项。

依据：[Python3.12 argparse](https://docs.python.org/3.12/library/argparse.html)、[contextlib资源生命周期](https://docs.python.org/3.12/library/contextlib.html)，复用既有固定版本和已验收服务，无新组件选型。
