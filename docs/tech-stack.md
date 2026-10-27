# 技术选型与兼容性基线

核查日期：2026-10-26（Asia/Shanghai）。原调研任务：P0-03；P0-07a 补充实际环境差异。调研解析与实际运行证据分开记录。

P1-02 实施更新：已复核并安装 pypdf 6.21.2 基础包（Python>=3.9、BSD-3-Clause、2026-10-21 发布），正式声明精确锁定，环境从 25 增至 26 包；未安装 crypto/image/OCR extras，也未引入第二套 PDF 解析器。版本/平台兼容由 Python 3.12.15 的真实合成 PDF 测试验证，运行与解析预算见 [P1-02 SPEC](specs/tasks/p1-02-pdf-parsing.md)。原调研表中其他 Phase 1 包仍是候选，不是已安装依赖。

P1-03 实施更新（2026-10-27）：安全 XML 明确选择 defusedxml 0.7.1，精确锁定后共 27 包，复用 ElementTree 树 API并显式禁止实体，不使用全局 defuse_stdlib。Python 官方文档推荐此类加固包，但其稳定版为 2021-03-08、PSFL，发行较久；PyPI 的宽泛 Requires-Python 不等于已验证现代版本，本次实际测试 Python 3.12.15/Expat 2.8.5。未声称近期维护活跃；原生 lxml 与需要额外 DTD 配置的 Biopython 属备选，当前无相应消费者，不同时引入。安全/类型边界及风险见 [P1-03 SPEC](specs/tasks/p1-03-pubmed-xml.md)。

P1-05 实施更新（2026-10-27）：官方 PyPI 核查 sentence-transformers 6.2.0（Python>=3.10）、transformers 5.21.0（Python>=3.11）、torch 2.14.1（Python>=3.10），精确加入 ml 可选 extra 并正式锁定。与原候选 5.20.2 不同，本次选用已发布的 5.21.0，实际安装/模型验证通过。torch 显式映射官方 CPU 索引，不允许该索引替换其他 PyPI 包；Windows 实装 2.14.1+cpu、tokenizers 0.23.3，65 个唯一包；通用锁解析 67 个包含不同平台分支，无 CUDA 包。原 27 包版本不变。基础 extra-free 干净环境只有 11 包，确认不安装 torch/sentence-transformers，适配器导入和 doctor 通过。真实 Linux/macOS/GPU 未验证。

P0-07a 修订：原计划 3.12.16 在 uv 0.13.5 中无 Windows 下载；[官方 standalone 20261021](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021) 最新发布的是 3.12.15。当前离线开发环境显式选择 3.12.15，兼容范围不变；下文 3.12.16 是原先推荐的安全修订目标，不代表已取得其构建。后续启用外部业务/部署前需重新核查并升级，当前不证明外部服务可用。

P1-06 实施更新（2026-10-27）：官方PyPI复核SQLAlchemy2.1.6（Python>=3.11）、Alembic1.20.1/psycopg3.3.6/pgvector0.5.1（均Python>=3.10），精确加入db extra。SQLAlchemy声明ORM、Alembic管理事务DDL、psycopg[binary]提供当前Windows开发驱动、pgvector客户端提供成熟VECTOR类型；不自建连接池或迁移框架。SQLAlchemy2.1是当前稳定系列，不使用参考项目旧ORM写法；pgvector0.5.1有类型信息，mypy无需忽略该导入。官方扩展镜像0.8.7-pg16实际digest固定为7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a，SELECT version()/extversion实测PostgreSQL16.15/vector0.8.7。72个Windows已装包、74项跨平台锁；基础环境仍11包且不安装SQLAlchemy/torch。[详细约束](specs/tasks/p1-06-postgres-schema.md)、[配置及迁移](postgres.md)。真实生产角色授权、Linux Python宿主部署、索引规模性能尚未验证。

P1-07实施更新（2026-10-27）：未新增/升级依赖，72个已装包和74项锁保持。使用SQLAlchemy定向ON CONFLICT及独立Session管理入库，不自建事务/重试框架；实际补测发现嵌套engine代理的隔离选项可能仍继承父代理设置，因此在借出Connection上、事务前显式设置READ COMMITTED，调用者engine保持不变。快照用标准库临时文件/fsync/同目录排他硬链接，NTFS实际并发验证通过，不引入对象存储。真实本地E5+PostgreSQL链路与重试/非覆盖分类已验证；无新的医学效果或生产性能结论。[契约与局限](specs/tasks/p1-07-offline-ingestion.md)、[运行方式](offline-ingestion.md)。

P1-08实施更新（2026-10-27）：沿用全部精确依赖/锁，未新增包。检索直接采用pgvector SQLAlchemy cosine_distance；借出的Connection显式REPEATABLE READ并开启只读事务，避免候选和后续来源映射跨快照。不自建向量算法、连接池或排序框架，不建立未经规模验证的ANN索引。阈值基于与展示一致的1-distance表达式，包含等号；数学轴向向量、实际快照并发和真实E5检索均通过。分数不等于概率/证据等级，未评价医学检索质量。[SPEC](specs/tasks/p1-08-vector-retrieval.md)、[操作说明](vector-retrieval.md)。

P1-09实施更新（2026-10-27）：新增rag可选extra：LangGraph1.2.17（Python>=3.10）、LangSmith0.14.12（>=3.10）及HTTPX0.28.1（>=3.8），官方PyPI元数据保存在本轮证据目录，当前Python3.12.15实际安装/类型/运行验证。LangGraph管理必要分支，LangSmith直接使用tracing_context显式关闭自动追踪，HTTPX按DeepSeek官方REST/JSON mode实现单供应商边界；不用OpenAI SDK或多供应商框架。新增25个锁定包，既有全部版本保持，99条锁记录（98个唯一名称）/97个当前安装唯一包。LangGraph会传递引入langchain-core及相关包，不声称没有LangChain依赖；不启用其checkpoint、Agent预置或网络追踪。真实请求deepseek-chat解析为deepseek-flash，不能视作不可变模型版本。仅rag的44包隔离环境可运行空证据图，无db/ml；基础环境仍11包。[SPEC](specs/tasks/p1-09-basic-rag.md)、[操作说明](basic-rag.md)。

P1-10实施更新（2026-10-27）：不新增/升级依赖或修改正式锁，沿用Python3.12 argparse/contextlib和已有应用服务/SDK。CLI显式路径和环境配置，延迟导入db/ml/rag，业务JSON使用ASCII转义保证Windows非UTF8管道可解析。command_runtime.py只装配现有对象，不自建业务、连接池、重试或迁移。BaseSettings必需字段实际来自环境，构造处用窄Callable类型说明环境读取，不全局放宽mypy。当前仍99条锁/97个已装唯一包，基础环境11包。[SPEC](specs/tasks/p1-10-cli-entrypoints.md)、[操作说明](cli.md)。

P1-11实施更新（2026-10-27）：api可选extra精确固定FastAPI0.162.0、Uvicorn0.54.0（均Python>=3.10）及已有HTTPX0.28.1。FastAPI官方lifespan与DTO/OpenAPI管理HTTP契约；Uvicorn最小发行承担ASGI/TCP服务，标准库asyncio/concurrent.futures管理有界同步工作，不引入新任务框架。新增4个锁定包：FastAPI、Uvicorn、Starlette1.10.0及FastAPI所需opentelemetry-api1.45.1；未装遥测SDK/导出器或standard全家桶。旧包版本全部保持，103条锁/101个当前已装唯一包。Uvicorn直接urllib元数据请求3次TLS EOF，使用官方PyPI web工具核验精确版本和>=3.10，并实际安装/运行验证，未关闭TLS校验。FastAPI元数据成功保存。基础环境11包；api-only23包无db/ml/rag可运行注入替身的真实生命周期/路由。实际TCP/E5/PG已验收，公网部署/真实付费LLM/医学质量仍未验收。[SPEC](specs/tasks/p1-11-fastapi.md)、[操作说明](api.md)。

## 1. 结论与环境选择

采用轻量模块化 Python 单体，入口适配器共享应用服务；先以同步业务服务及受限并发完成 MVP，再按 Phase 2 需求引入后台任务状态。文献与证据持久化采用 PostgreSQL + pgvector，模型推理使用成熟库，外部服务通过可替换适配器接入。

推荐项目解释器 **CPython 3.12.16**，正式项目兼容范围先限制为 `>=3.12,<3.13`；本次依赖解析目标为 3.12，尚未安装该解释器、执行该补丁版或创建 `.venv`。官方发布页确认 3.12.16 已于 2026-10-25 发布；3.12 系列处于安全维护阶段，选择它是兼顾本次 wheel 可用性和成熟生态的工程判断，不是长期不升级的承诺。后续定期重核 3.13/3.14。[Python 3.12.16](https://www.python.org/downloads/release/python-31216/)、[生命周期](https://devguide.python.org/versions/)。

本机指定 `medical-agent` 是 Python 3.10.21，另有默认 Python 3.14.7；uv 已安装解释器清单仅发现这两者。保留原环境作为工具引导环境，不升级或清理其中的包。项目使用 uv 管理自己的 `.venv`、`pyproject.toml` 和 `uv.lock`，具体创建留 P0-07。Python 3.12 当前官方安全发行不提供常规 Windows 安装器；uv 使用独立发行构建，3.12.16 构建的实际可取得性需在环境任务核实，不能根据官网源码发行假定已可安装。[uv Python 管理](https://docs.astral.sh/uv/concepts/python-versions/)。

## 2. 组件职责、依据、替代方案和风险

下表“采用”表示设计选择；仅 Phase 0 最小工具计划进入 Phase 0 环境。未来阶段的候选包只进行解析研究，没有提前安装或创建模块。

| 组件 / 引入阶段 | 职责与选择依据 | 替代方案及主要风险 |
| --- | --- | --- |
| Pydantic v2 / Phase 0 起 | 明确 DTO、配置边界及运行时校验，数据库 ORM 与对外 DTO 分离 | dataclass 适合内部纯值对象，但不承担外部输入校验；不用 Pydantic v1 混合 API |
| pydantic-settings / Phase 0 起 | 环境变量配置、启动时显式校验；只在装配入口实例化 | 标准库 environ + 手工校验会重复已有能力；SecretStr 仍需日志脱敏，不能将其等同加密 |
| structlog + logging / Phase 0 起 | JSON 日志、任务关联字段、异常信息；与服务器标准日志协作 | logging 也可完成，但要维护格式器；不再同时引入 Loguru，避免双重日志配置 |
| argparse / Phase 0 CLI 骨架及 Phase 1 | 轻量标准库命令行；复用应用服务 | Typer 暂无必要；CLI 不承担数据库或 LLM 业务实现 |
| FastAPI + Uvicorn / Phase 1 | 明确 API 契约、依赖注入和生命周期 | Flask/Starlette 可用，但需要额外契约装配；同步 embedding、数据库或 SDK 不能直接塞入 async 路由阻塞事件循环 |
| SQLAlchemy 2.x + psycopg 3 / Phase 1 | 显式事务、连接池和类型化模型；先用同步 Session | psycopg2 仍有生态但新项目选 psycopg3；asyncpg 暂不引入。Session 每线程/任务独立，不把会话跨线程共享 |
| Alembic / Phase 1 | 数据库结构迁移与版本管理 | create_all 只适合有限测试建表，不代替演进迁移；autogenerate 结果须审查，扩展及向量索引迁移需显式处理 |
| PostgreSQL 16 系列 + pgvector 扩展 / Phase 1 | 文献、片段、唯一约束、向量与事务一致存储；避免双库同步 | Qdrant/Weaviate 适合独立大规模向量服务，但本项目暂无该需求；SQLite 无法代替 PostgreSQL 集成验收 |
| pgvector Python 包 / Phase 1 | SQLAlchemy Vector 类型与距离运算集成 | 不自行实现向量存储；客户端包版本与数据库扩展版本是两个不同版本体系 |
| redis-py + Redis / Phase 1 | 消息短期去重、原子占位与后续短期状态 | 进程内 set 不覆盖多进程；TTL 不等于永久幂等。任务事实及文献幂等仍需数据库约束，Redis 故障策略必须在 SPEC 明确 |
| pypdf / Phase 1 | MVP 有文字层 PDF 的按页提取、页码定位、元数据读取；纯 Python、成熟 API | PyMuPDF 更适合性能和复杂版面需求，但本次 PyPI 最新已到 2.0，不能按参考项目旧 API 盲目迁移；先不引入两套解析器。扫描件明确返回需要 OCR，MVP 不做 OCR |
| sentence-transformers / Phase 1 ML 可选组 | 加载成熟 embedding 模型、批量编码、归一化 | 托管 embedding 简化本地推理但引入网络及数据流向；不自写模型推理框架。CPU 吞吐、模型效果、内存必须实测 |
| PyTorch + Transformers / Phase 1 ML 可选组 | 本地推理底座及匹配模型 tokenizer | 暂不增加 ONNX/OpenVINO 双运行时。CPU 为默认目标；CUDA、驱动及 GPU 镜像作为单独变体验收 |
| LangGraph / Phase 1 必要分支起 | 检索、证据不足分支、生成及基础引用标识检查的状态编排；后续 PICO/在线检索按阶段扩展 | 简单无分支步骤保留普通函数；不创建多 Agent 人格或重复状态机。LangChain 顶层包不列直接依赖，但 LangGraph 会传递引入 langchain-core |
| lark-oapi / Phase 1 | 官方长连接、事件解析与消息 API；只进入 src/feishu 适配层 | 不自写 WebSocket。webhook 不作为默认，因为用户指定长连接；SDK 自持事件循环，建议独立 feishu_bot 进程/Compose 服务 |
| ThreadPoolExecutor + 有界接纳 / Phase 1 | SDK 回调只校验、去重、提交任务；工作线程调用共享应用服务 | max_workers 只限制线程数，不自动限制提交队列；用标准库 Semaphore 等对在途任务限额，满载快速失败并释放占位。超时 Future 不会杀死正在执行的线程，要靠外部调用超时和总期限 |
| HTTPX / Phase 1 外部 HTTP；Phase 4 PubMed | 连接池、明确超时、同步/异步客户端和 MockTransport；复用一个成熟 HTTP 层 | requests 缺少原生异步；不用本机 httpx2 自动替换 SDK 所需 httpx。连接重试不覆盖 HTTP 429/503，状态重试与总期限在对应任务选成熟工具或 SDK 能力 |
| NCBI E-utilities + HTTPX / Phase 4 | 官方 ESearch/EFetch，查询规划、分页、请求标识及元数据映射保留在独立 PubMed 适配器 | Biopython Entrez 是成熟备选，内置 XML、限流和重试；但同步调用、模块配置与默认重试等待需包装。本项目统一可注入 HTTPX 传输；当前本地 XML 用 defusedxml/标准库树 API，医学字段映射保留业务逻辑，在线格式仍需对应阶段核查 |
| PostgreSQL 全文检索 + pgvector / Phase 5 | 关键词召回与语义召回后融合，单库维护 | 初期不引入 Elasticsearch/BM25 服务；postgres FTS 的排序分数不等于 BM25。中文分词和中英混合查询效果需专门验证 |
| pytest + pytest-asyncio + pytest-cov / Phase 0 起 | 真实 RED/GREEN、异步生命周期、覆盖率及分层回归 | 不用调用真实服务的打印脚本代替断言；Mock 通过与真实集成通过分开记录 |
| Ruff + mypy / Phase 0 起 | 一套 lint/format 加类型检查 | pyright 可替换 mypy，但不同时配置两套；第三方 SDK 类型不完整时局部隔离，不全局忽略错误 |
| uv / Phase 0 起 | Python、隔离环境、锁定与可复现同步 | pip + pip-tools 可用，但不并存两套依赖真相；Conda 环境不作为锁文件 |
| Docker Compose / 基础设施验证及 Phase 1 | PostgreSQL、Redis、API、feishu_bot 的本地编排 | 不默认 Kubernetes/微服务；API 与机器人可独立入口但共享同一代码包与数据库 |

能力依据：[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)、[structlog](https://www.structlog.org/en/stable/)、[FastAPI 并发](https://fastapi.tiangolo.com/async/)、[SQLAlchemy Session](https://docs.sqlalchemy.org/en/21/orm/session_basics.html)、[psycopg 安装](https://www.psycopg.org/psycopg3/docs/basic/install.html)、[Alembic](https://alembic.sqlalchemy.org/en/latest/)、[pgvector-python](https://github.com/pgvector/pgvector-python)、[redis-py](https://redis.io/docs/latest/develop/clients/redis-py/)。

解析与工作流依据：[pypdf 文本提取局限](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)、[PyMuPDF 变更记录](https://pymupdf.readthedocs.io/en/latest/changes.html)、[sentence-transformers 安装](https://www.sbert.net/docs/installation.html)、[LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)、[官方飞书 SDK](https://github.com/larksuite/oapi-sdk-python)、[Python 3.12 Executor](https://docs.python.org/3.12/library/concurrent.futures.html)。

网络与工具依据：[HTTPX 超时](https://www.python-httpx.org/advanced/timeouts/)、[HTTPX transport/重试/Mock](https://www.python-httpx.org/advanced/transports/)、[NCBI API](https://www.ncbi.nlm.nih.gov/home/develop/api/)、[Bio.Entrez](https://biopython.org/docs/latest/api/Bio.Entrez.html)、[pytest](https://docs.pytest.org/en/stable/)、[pytest-asyncio](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html)、[pytest-cov](https://pytest-cov.readthedocs.io/en/latest/)、[Ruff](https://docs.astral.sh/ruff/)、[mypy](https://mypy.readthedocs.io/en/stable/)、[Compose](https://docs.docker.com/compose/)。

## 3. 官方发行核查与精确候选版本

来源为 PyPI JSON 官方接口，完整记录见 [元数据快照](research/pypi-metadata-2026-10-26.json)：25 个包均校验了请求名称与返回名称、至少一个发行文件。快照包含依赖、Python 要求、官方链接、文件名、上传时间、撤回标记和 SHA256。日期是所选版本首个发行文件上传日（UTC），不是 GitHub 最后提交时间；维护判断结合近期发行及官方文档，不保证没有漏洞。

| 包 | 版本 | Requires-Python | 上传日 UTC | 决策 |
| --- | --- | --- | --- | --- |
| pydantic | 2.14.1 | >=3.10 | 2026-10-11 | Phase 0 |
| pydantic-settings | 2.16.1 | >=3.11 | 2026-10-20 | Phase 0 |
| structlog | 26.1.0 | >=3.10 | 2026-06-06 | Phase 0 |
| pytest | 9.1.1 | >=3.10 | 2026-06-19 | Phase 0 开发依赖 |
| pytest-asyncio | 1.4.1 | >=3.10 | 2026-10-25 | Phase 0 开发依赖 |
| pytest-cov | 7.1.0 | >=3.9 | 2026-03-21 | Phase 0 开发依赖 |
| ruff | 0.17.2 | >=3.7 | 2026-10-22 | Phase 0 开发依赖 |
| mypy | 2.4.0 | >=3.10 | 2026-10-01 | Phase 0 开发依赖 |
| uv | 0.13.5 | >=3.8 | 2026-10-22 | 工具目标；本次解析器实际是本机 0.13.1 |
| fastapi | 0.162.0 | >=3.10 | 2026-10-23 | Phase 1 |
| uvicorn | 0.54.0 | >=3.10 | 2026-09-25 | Phase 1；不启用 standard extra |
| SQLAlchemy | 2.1.6 | >=3.11 | 2026-10-21 | Phase 1；使用 2.x API |
| alembic | 1.20.1 | >=3.10 | 2026-10-22 | Phase 1 |
| psycopg | 3.3.6 | >=3.10 | 2026-09-18 | Phase 1；开发与探测采用 binary extra |
| pgvector | 0.5.1 | >=3.10 | 2026-10-09 | Python 集成包 |
| redis | 8.1.0 | >=3.10 | 2026-07-30 | Python 客户端，不是服务端版本 |
| pypdf | 6.21.2 | >=3.9 | 2026-10-21 | Phase 1 默认 PDF 解析 |
| httpx | 0.28.1 | >=3.8 | 2024-12-06 | 稳定 API 与 SDK 兼容；发行较旧，后续升级须重核 |
| langgraph | 1.2.17 | >=3.10 | 2026-10-24 | Phase 1 工作流候选 |
| lark-oapi | 1.7.5 | >=3.8 | 2026-10-15 | Phase 1 官方 SDK |
| sentence-transformers | 6.2.0 | >=3.10 | 2026-10-21 | ML 可选组 |
| torch | 2.14.1 | >=3.10 | 2026-09-30 | ML 可选组；构建变体另行指定 |
| transformers | 5.20.2 | >=3.10.0 | 2026-10-19 | ML 可选组，满足 ST 的 >=5,<6 |
| pymupdf | 2.0 | >=3.11 | 2026-10-19 | 已核查备选，不加入候选依赖 |
| biopython | 1.88 | >=3.10 | 2026-08-06 | 已核查备选，不加入候选依赖 |

各包的版本和 Python 范围可按快照内 `source` 的 `https://pypi.org/pypi/<包名>/json` 核查；URL 是移动最新版本，复核历史版本应使用 `https://pypi.org/pypi/<包名>/<版本>/json`。上述精确值固定于本次快照，不跟随最新版本自动修改。

参考仓库旧依赖不直接沿用。本次明确的兼容点：

- pydantic-settings 2.16.1 要求 Python >=3.11，本机 Python 3.10 不适合该组合；pydantic 版本满足其 >=2.7 声明。
- SQLAlchemy 2.1.6 要求 Python >=3.11；Alembic 1.20.1 要求 SQLAlchemy >=2.0。本次采用当前 2.1 API 文档，不混用旧 Query 风格作为新实现。
- sentence-transformers 6.2.0 要求 transformers >=5,<6、torch >=2.2；候选组合满足这些约束，仍需真实模型 smoke test。
- lark-oapi 1.7.5 声明 `websockets>=11,<16` 及 `httpx>=0.24,<1`；本次解析为 websockets 15.0.1 和 httpx 0.28.1。共享环境的 websockets 16 不可直接复用。
- 不直接引入 LangChain 顶层包或 langchain-community；LangGraph 传递依赖的 langchain-core 在本次解析为 1.7.0，不声称完全没有 LangChain 依赖。

## 4. 数据库、缓存与部署基线

PostgreSQL 选择受支持的 **16 系列**，官方当前列出 16.15、支持至 2028-11-09；pgvector 扩展选择 **0.8.7**，官方列出 `0.8.7-pg16` 镜像标签并支持 PostgreSQL 13+。客户端 `pgvector==0.5.1` 不是扩展 0.8.7。后续必须拉取并 inspect 镜像、记录 digest、实测 `SELECT version()` 和 `pg_extension.extversion`，不能由镜像标签推断底层具体 PostgreSQL 补丁版本。[PostgreSQL 支持表](https://www.postgresql.org/support/versioning/)、[pgvector 安装与标签](https://github.com/pgvector/pgvector)。

Redis 服务端选择当前 8 系列作为后续容器候选，具体补丁版和镜像 digest 待 Compose 任务验证后固定；本次只锁定 Python 客户端。去重仅使用基础原子命令及过期机制，不引入 Redis 向量功能或 RedisVL。[官方 Docker 文档](https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/docker/)。

Compose 采用 Compose Specification，不写过时顶层 version 字段。开发机实际 CLI 是 Docker 29.7.2 / Compose v5.5.1，但 Engine 在 P0-01 未能连接，当前没有容器运行验证。Linux 应用镜像优先 glibc/Debian 系列，避免在 ML 镜像中默认采用 musl/Alpine；本次 Linux wheel 目标是 x86_64-manylinux_2_28，不覆盖 ARM、macOS 或 musl。

Phase 1 再创建 postgres、redis、api、feishu_bot 服务，机器人相关代码按约 5 个职责模块组织在 `src/feishu/`；本任务不提前创建服务或空模块。API 和机器人可分别运行，复用核心应用服务而不互相依赖 SDK。

## 5. 模型与外部接口决策

Embedding 框架已选 sentence-transformers；模型暂以 `intfloat/multilingual-e5-base` 为中英跨语言检索候选，对比参考项目的 `NeuML/pubmedbert-base-embeddings` 英文医学候选。作者模型卡确认前者支持多语言、要求 query/passage 前缀并截断至 512 tokens；后者模型卡标记英文。医学适用性、实际维度和内存均需模型任务实测，不以模型名称或公开通用指标代替本项目评估。[E5 作者模型卡](https://huggingface.co/intfloat/multilingual-e5-base)、[PubMedBERT 作者模型卡](https://huggingface.co/NeuML/pubmedbert-base-embeddings)。

启用模型前必须记录 model_id、不可变 revision、tokenizer、实际维度、归一化方式、query/document 前缀及分块版本；更换模型不得混用旧向量。P0-03 未下载权重、未选定模型 revision，也不在 ORM 中提前写死 768。MVP 不把通用 LLM 自评分当研究质量评分。

P1-04（2026-10-27）重新核查上述 E5 作者模型卡与 [Transformers tokenizer 官方文档](https://huggingface.co/docs/transformers/main_classes/tokenizer)，仅落地纯业务分块与可注入计数契约，不新增 ML 依赖。计数完整 document_prefix + 原文切片且包含特殊 token，禁止 padding/truncation；证据正文保留原切片。模型版本仍为待决项，fixture 声明不是 E5 实测。逐码点保守探测不依赖 token 长度单调，单块字符/总计数调用上限控制工作量；真实吞吐、模型前缀一致性与编码不被截断必须在 P1-05 实测，不能据此关闭 P1-F02 验收项。

P1-05 将 E5 模型/tokenizer 固定为提交 d128750597153bb5987e10b1c3493a34e5a4502a；使用模型官方的前缀、归一化和 CPU 推理，实际维度 768、512 token。选该模型以维持中英检索候选的一致性，暂不增加第二套模型/ONNX 运行时。权重约 1.11 GB，SHA256 与官方仓库一致，九份运行文件哈希记录在 [模型 manifest](research/p1-05-model-manifest.json)。本地 manifest 是完整性记录，不能充当签名认证；运行期间不要修改快照。最终真实离线复验加载 25.5s、分块与推理 5.5s、峰值工作集约 1.83 GiB（首轮加载 112.8s），不能据此保证任意机器/文本的吞吐。SDK 已按当前版本使用 get_embedding_dimension，消除了旧方法改名警告。模型医学适用性与生产资源配置尚待评估。[操作及复现](local-embedding.md)、[范围与门槛](specs/tasks/p1-05-local-embedding.md)。

LLM 供应商和模型尚未由用户指定，当前只确定可替换的生成端口、显式配置与超时要求，不虚构可用模型名。Phase 1 对应任务在具体服务明确后选择其成熟 SDK、核查版本并加入锁文件；当前不为展示功能加入多家供应商 SDK，也不实现通用模型客户端框架。该待决项不阻碍 Phase 0 离线测试骨架。

PubMed 来源选官方 E-utilities；离线导入与 Phase 4 实时检索分开。NCBI Books 使用指南本次访问遇到浏览器校验，未将该页面内容标成已读；已读取 NCBI API 概览和 Biopython 官方 Entrez 文档。后者确认 3/10 请求每秒及内置重试；进入 Phase 4 前再次核查 NCBI 当前规则、email/tool 标识、多进程限流、日期过滤与重试预算，不进行本次真实文献检索。

## 6. 锁定材料与解析验收

研究输入在 [dependencies/](research/dependencies/)：`phase0.in`（3 个运行组件与 6 个开发/工具组件）、`phase1.in`（包含 Phase 0 加 MVP 候选）、`ml.in`（含前两组加推理底座）。每个直接依赖使用实际核实的精确版本，解析输出锁定传递版本并带 SHA256。它们是阶段兼容性探测，不是要求现在安装未来阶段所有依赖。

实际解析器：指定 Conda Python 执行 `python -m uv`，uv 版本 0.13.1；目标工具版本 0.13.5 只列入候选，没有安装。解析使用 `--no-python-downloads`，因此不代表本机已具备 Python 3.12。正式 `pyproject.toml` 与 `uv.lock` 留待 P0-07 工程骨架任务生成并用目标 uv、解释器复验；运行与开发依赖须在正式声明中分组。

基础复现命令（PowerShell；替换 group 与 platform/output 为记录中的组合）：

```powershell
& 'C:\Users\11091\.conda\envs\medical-agent\python.exe' -m uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/phase0.in --python-version 3.12 --python-platform x86_64-pc-windows-msvc --only-binary :all: --no-python-downloads --generate-hashes --index-url https://pypi.org/simple --output-file docs/research/dependencies/phase0-py312-windows.txt --quiet
```

| 组 | Windows x64 | Linux x64 glibc >=2.28 | 性质 |
| --- | --- | --- | --- |
| Phase 0 | 成功，24 个包 | 成功，23 个包 | 本阶段最小候选 |
| Phase 1（不含 ML） | 成功，74 个包 | 成功，72 个包 | 未来兼容性探测 |
| ML（PyPI 默认） | 成功，102 个包 | 成功，119 个包 | 对照探测；Linux 带入 CUDA 依赖，不作为 CPU 安装清单 |

逐项退出码见 [resolution-results.json](research/dependencies/resolution-results.json)。解析阶段出现一条旧式版本说明 `>= '2.7'` 被 uv 规范化的警告，不影响退出码，但不等同完全无警告。没有安装 wheel、导入这些候选包或运行模型。

发现 PyPI 默认 Linux torch 会引入 nvidia CUDA 依赖后，追加官方 CPU 索引探测，使用相同 `ml.in` 加 `--torch-backend cpu`，单独输出 `ml-cpu-py312-<平台>.txt`。两项均成功：Windows 102 包、Linux 100 包，torch 均为 2.14.1+cpu、无 nvidia-* 依赖；8 项合计全部解析成功。CPU 输出仍需配合正确来源索引安装，不能仅凭文本清单假定能从 PyPI 下载 CPU wheel。详细记录见 [P0-03 执行记录](research/p0-03-validation.md)。正式项目应通过明确的 PyTorch CPU 索引映射选择构建，而不是给所有包开放不受限的多索引混合。[uv 官方 PyTorch 指南](https://docs.astral.sh/uv/guides/integration/pytorch/)。

## 7. 未验证项与下一步

本次完成的是官方来源核查、精确候选约束和元数据级解析。没有 pytest 应用测试，也没有 RED/GREEN；未实现产品功能，不能声称 Phase 0 工程验收完成。

后续验收必须包括：独立 Python 3.12 环境安装、正式锁文件、import smoke test；FastAPI 生命周期；真实 PostgreSQL 扩展/外键/事务/向量距离；Redis 原子去重与故障路径；模型维度/分词/效果/CPU内存；飞书 SDK 回调、在途上限与真实长连接；PubMed 官方接口限流；具体 LLM 端点及超时。容器镜像 digest、Python 构建来源和模型 revision 都必须落地记录。

P0-03 不自动进入下一任务。后续 P0-04 编写总体 SPEC 和 Phase 0–9 概要，将本次选择、待决项及验证门槛转成分阶段验收；正式架构、测试策略与实现仍按任务顺序推进。
