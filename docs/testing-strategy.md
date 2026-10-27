# 测试策略与 TDD 执行约定

P1-17当前更新（2026-10-27）：已通过真实E5/PG/DeepSeek的合成PDF与固定NCBI摘要闭环，累计2次授权付费请求；Python3.12.16宿主/共享镜像已核验，六份学习材料已交付。医学支持关系人工审查按用户选择待完成，Phase1未标完成。详见[阶段报告](phase1-acceptance.md)和[学习导航](learning/phase-01/README.md)。下文旧任务结果按各自时点阅读。

版本：0.2；日期：2026-10-26；原制定任务：P0-06；2026-10-27文档核对更新。当前任务状态见[开发计划](development-plan.md#phase-1-任务进度)。下列逐任务计数是历史验收时点；P1-16最新默认回归为1023 passed /93 deselected，飞书联合368 passed。当前全量开发/测试使用uv sync --all-extras（含feishu SDK）。策略不等于执行结果；P0-07a–d 已建立最小包/显式配置/日志/runtime/CLI 与相应测试；P0-07e 完成 Windows 环境/wheel 验证，P0-08 完成学习材料与独立验收。真实 RED/GREEN、环境与文档复验分别记录在开发计划。

P1-01 当前增加纯 DTO 契约测试 97 项及两个 domain 隔离导入场景，完整回归为 158 passed（134 单元 + 24 CLI 集成）。范围仅结构、来源/定位内部一致性与序列化，不证明文献真实性或真实解析/数据库/模型能力；详细清单见 [P1-01 SPEC](specs/tasks/p1-01-literature-contracts.md)。

P1-02 增加 20 个逐页契约/预算单元用例、24 个 PDF 集成场景和两个 adapters 隔离导入参数；当前总回归见开发记录。PDF 集成使用真实 pypdf/PdfWriter 的合成多页/空白/图像/RC4 加密样例，故障/计时/规范化用局部替身明确区分；不是现实论文版面/中文字体/OCR/AES 全算法验证。预算是协作检查，非进程级资源隔离。[详细 SPEC](specs/tasks/p1-02-pdf-parsing.md)。

P1-03 增加 27 个摘要/条目/批次契约单元场景、47 个 XML 集成场景和一个导入参数。使用真实 defusedxml 解析合成 UTF-8/UTF-16、混合标签、结构化摘要、日期/作者/DOI 和实体反例；正常 DOCTYPE 的网络阻断证明不加载 DTD。安全/语法/全局预算整体失败与逐条拒绝明确区分，时钟/I/O/回调仅局部替身；未连接 PubMed API，不声称现实全 DTD/大基线/医学真实性验证。计数均为相应任务时点，最新回归见开发记录。[详细 SPEC](specs/tasks/p1-03-pubmed-xml.md)。

P1-09测试更新：新增54个纯契约/真实LangGraph+Fake ports测试、20个真实HTTPX MockTransport协议场景和4个导入隔离参数，默认回归581 passed /78 deselected。真实DeepSeek合成证据单独external测试1 passed，请求别名deepseek-chat实际响应deepseek-flash；未验证真实E5/PG/LLM整链路。P1-09时点全量pytest使用`uv sync --locked --extra ml --extra db --extra rag`；当前命令还须加`--extra api`（数据库/模型服务不因默认运行启动）；单独基础doctor仍不需要extras。[SPEC](specs/tasks/p1-09-basic-rag.md)、[运行说明](basic-rag.md)。

P1-10更新：新增43个CLI/装配/安装入口目标场景及1个导入审计参数，默认625 passed /79 deselected。独立真实E5/PG+HTTP替身CLI集成1 passed；不复用旧真实LLM记录宣称CLI付费整链路。11包无extra环境下module/console的help/doctor/缺依赖共10项通过。[SPEC](specs/tasks/p1-10-cli-entrypoints.md)、[CLI说明](cli.md)。

P1-11更新：新增60项实际FastAPI/生命周期/路径/错误/容量测试及2个导入审计参数，默认687 passed /80 deselected。独立真实Uvicorn TCP+E5/PG、明确HTTP替身集成1 passed，生命周期模型加载一次。11包基础与23包api-only环境通过；首轮与模型验收并行时旧CLI10秒超时，保留失败并在无模型并行负载下串行完整复验通过，未放宽断言。当前完整开发安装需选择api/ml/db/rag四个extras。[SPEC](specs/tasks/p1-11-fastapi.md)、[API用法](api.md)。

## 1. 范围与原则

本策略承接 [总体 SPEC](specs/00-project-overview.md)、[架构设计](architecture.md) 及 [Phase 0 详细任务](specs/tasks/phase0-implementation.md)。Phase 0与P1-01–15的测试已按任务SPEC落地；飞书其余能力和Phase 2–9仍须在进入对应任务时细化fixtures、阈值及外部前提，不提前实现评价平台。P1-Txx是阶段场景，开发任务P1-xx另列，见[MVP映射](specs/01-mvp.md#验收场景与开发任务的对应关系)。

每次一个最小任务，先读 SPEC/代码/测试，列文件和场景；先新增目标测试并观察因目标能力缺失而失败，再最小实现、必要重构和相关回归。不能通过删除断言、将失败改为 skip/xfail 或更换数据集取得 GREEN。只测会影响正确性、边界或维护性的行为，不断言私有函数顺序/每个文件名，也不为无功能的目录和依赖本身造单元测试。

## 2. 分层与执行范围

| 层 | 目录/标记 | 验证内容 | 外部条件与边界 |
| --- | --- | --- | --- |
| 单元 | tests/unit/ | 配置、引用/分块等纯规则；Fake 依赖下的用例；错误/资源行为 | 不调用真实外部服务；包含已落地的契约、业务替身、装配/容量及飞书纯过滤等测试 |
| 集成 | tests/integration/，integration | Phase 0 为安装包、CLI 和装配；Phase 1 起还验证真实 PostgreSQL/Redis | 有关服务缺失要明确失败/阻塞，不用 Mock 代替；不能把所有集成都标 external 以绕过必需验收 |
| 外部冒烟 | tests/external/，external | 真模型、LLM、飞书、官方 PubMed 实际互通 | 显式命令和测试凭据，单独记录成本、时间、结果；默认不执行不代表已通过 |
| 性能 | tests/performance/，performance | 固定模型、语料、硬件、负载下延迟/内存/饱和 | 对应阶段冻结预算；10 秒测试超时只是防挂起，不是性能门槛 |
| 人工复核 | 阶段验收/评估记录 | 医学论断支持度、研究类型/冲突和真实消息体验 | 固定样例与判定依据，不被 LLM 自评或总覆盖率取代 |

Phase 0 不需要数据库、Redis、模型、LLM、飞书或 PubMed 网络测试。依赖下载、解释器安装和构建另列为环境验证，不能用来声称产品已离线运行成功；离线 pytest 和 doctor 必须独立不联网。

未来 external/performance 标记显式注册；默认选择 `not external and not performance`，显式 `-m external` 或 `-m performance` 覆盖默认选择并配合对应路径。默认排除项报告为 deselected/未执行，而非通过；某阶段要求的真实冒烟未完成时不能验收该阶段。

## 3. Phase 0 测试清单与文件

详细字段和函数契约以 [实现任务 SPEC](specs/tasks/phase0-implementation.md) 为准，避免在策略文件中维护第二套默认值。

| 总体 ID | 任务 | 目标测试/检查 | 关键行为 |
| --- | --- | --- | --- |
| P0-T01 | P0-07a 起逐步扩展 | tests/unit/test_package.py | 从已安装包隔离导入；不读全局配置/连服务/建线程/配置日志 |
| P0-T02 | P0-07b | tests/unit/test_config.py | 默认值、环境覆盖和重新加载、非法值、不隐式读 .env |
| P0-T03 | P0-07c | tests/unit/test_logging_config.py | stderr JSON、级别、重复配置、敏感字段和异常原文控制 |
| P0-T04 | P0-07d | tests/integration/test_cli.py | help 无装配、doctor 本地 JSON、模块/脚本入口一致、失败退出码 |
| P0-T05 | P0-07d | tests/unit/test_bootstrap.py 与 CLI 集成 | 显式 Settings、request_id 和注入 factory 被采用；成功/异常均退出上下文 |
| P0-T06 | P0-07a / P0-07e | 锁文件同步、pip check、全新环境与 wheel 冒烟记录 | 不依赖共享 Conda、工作目录或 PYTHONPATH，锁文件不漂移 |
| P0-T07 | P0-07e，期间按需 | Ruff lint/format、mypy strict | 当前代码规范/类型有效，不全局屏蔽错误 |

预期五个聚焦测试文件，而非为每个内部 helper 写一份测试。测试参数数量由实际边界决定；P0-04 的 63 个阶段计划场景不是当前 pytest 测试数。本任务不创建这些文件，也不把“文件存在”当目标功能。

## 4. 测试环境与隔离

### 4.1 解释器和安装来源

始终确认 .venv 的绝对解释器、Python 与 uv 版本、当前项目包来源；Windows 开发和 Linux 部署分开记录。用标准 src 安装，不在 conftest.py 改 sys.path、不配置 pytest pythonpath、不依靠仓库根恰好在导入路径。

P0-07a 先用 `sync --locked --group dev --no-install-project` 仅准备测试依赖，目标测试 RED 后才安装最小根包。以 `& $projectPython -I -m pytest ...` 执行，避免 uv run 在目标缺失时自动安装/构建项目。后续任务保持同一解释器和相同目标测试命令；升级/改变依赖属于有原因的独立变更，须重新记录。

PyPI 安装错误、SSL/网络权限、找不到解释器/pytest 或错误测试路径，应先修复前置条件，不能计为 RED。官方 partial install 说明见 [uv 同步文档](https://docs.astral.sh/uv/concepts/projects/sync/)；src 安装与 importlib 模式依据 [pytest 官方实践](https://docs.pytest.org/en/stable/explanation/goodpractices.html)。

### 4.2 环境变量和本地文件

使用 monkeypatch 清理/设置本项目前缀及影响当前测试的环境变量，Settings 禁止隐式读真实 .env。子进程只传必要系统变量和测试明确设置的配置，保留 Windows 启动所需系统/临时目录值，不把 os.environ 整份打印进报告。清理 PYTHONPATH、PYTEST_ADDOPTS/PYTEST_PLUGINS 等可能改变本次运行的注入来源，测试结束恢复。

PYTEST_ADDOPTS/PYTEST_PLUGINS 等影响测试工具启动的变量须由调用方在启动 pytest **之前**保存、清理，并在命令结束后恢复；不能等 fixture 才试图撤销已加载的插件/选项。配置测试自身的业务环境变量再用 monkeypatch 管理。

测试日志只使用固定假秘密 sentinel，不放真实凭据。P0-07a 的 .gitignore 排除 .venv/、.tools/、.research-cache/、.artifacts/、dist/、build/、本地 .env 与 .env.*（保留 .env.example）、缓存/egg-info/覆盖率输出；data/、模型权重与运行产物也按实际目录排除。不能全局忽略 *.pdf/*.json 等而误伤未来小型 fixtures。

所有临时文件在 tmp_path 或显式项目测试目录中；不依赖绝对用户名路径来断言结果，不递归删除未确认归属的目录，不扫描或清理用户共享 Conda 环境。

### 4.3 导入及 CLI 子进程

使用 `sys.executable -I -B`、临时 cwd 和 10 秒超时。新子进程中先装失败哨兵，再导入目标，避免父进程模块缓存掩盖副作用。按实现进度明确列出目标模块，不用“存在才测”跳过承诺范围。

哨兵只拦实际副作用边界：socket.connect/create_connection/getaddrinfo、Thread.start、以及 Phase 0 不应加载的重库/SDK（如 torch、transformers、sentence_transformers、sqlalchemy、redis、lark_oapi、langgraph）。记录尝试次数，即使产品捕获异常也不能误判没有尝试；允许 Python 正常读取安装包，不能禁止所有文件读取而破坏导入机制。

子进程可用标准库重定向捕获导入期间 stdout/stderr，并返回审计数据给父测试；断言产品无输出/网络/线程尝试及项目/root handler 无启动变更，不断言 Pydantic 的私有加载顺序。不增加自制沙箱或全局 pytest 网络插件。

help 的“无装配”既通过非法环境下的真实子进程验证，也通过注入会失败的 runtime_factory 验证。CLI JSON 用 json.loads 和字段语义断言，不做整行文本/时间/UUID 的脆弱快照。

## 5. Fake、Mock 与真实系统的边界

| 对象 | 单元测试替换方式 | 仍须真实验证的内容 |
| --- | --- | --- |
| runtime factory | 小型 context manager，记录进入/退出与提供的 Settings | Phase 0 真实 CLI/安装入口；未来实际客户端关闭 |
| LLM/Embedding | 按契约返回固定 DTO/向量，或抛指定失败；不在 Fake 里重写模型/向量库 | 实际维度、模型身份/分词、格式约束、期限和资源 |
| PostgreSQL writer/retriever | 固定结果或用例所需调用记录 | 外键/唯一约束、rollback、并发冲突、pgvector 距离及迁移 |
| Redis 去重 | 用例测试用小型占位 Fake | 原子性、owner token、过期、续期、连接故障及多工作者 |
| PubMed HTTP | HTTPX MockTransport + 冻结官方格式样例 | 官方端点、限流和真实元数据来源一致性 |
| 飞书 SDK/发送 | 假事件和 sender 返回 sent/failed/unknown | 长连接、权限、自身识别、真实收发、未知投递边界 |
| 时间/并发 | 只有涉及期限时注入时钟，使用 Event/Barrier 精确控制进程内时序 | 真实服务超时与运行负载、资源释放 |

优先在“本项目自己拥有的边界”替换依赖，不 patch 第三方私有实现。Fake 固定返回只说明应用如何处理该返回，不能作为底层协议/事务正确性的证据。普通参数校验不需要构造一套数据库 Mock。

并发测试优先同步事件和明确 barrier，少用 sleep 赌时序；跨线程共享 SQLAlchemy Session、按超时提前释放仍在运行的槽位、只在排队前核对租约等错误要有实际边界用例。当前不实现这些未来测试工具。

## 6. 后续真实集成的安全与可复现前提

Phase 1 数据库/Redis 测试使用专用测试 DSN、独立数据库/schema 及本次唯一 key 前缀；连接配置缺失时明确失败/未验证，不自动用 SQLite/内存 Fake 降级通过。清理仅作用于自己创建且已核实归属的测试资源，不对用户库执行 DROP 或对 Redis 执行 FLUSHALL。

事务测试需要多个真实 Session 时，不用单个外层 rollback fixture 假装覆盖并发提交；选择专用隔离 schema/数据库和明确清理。真实模型/飞书/LLM/PubMed 冒烟须显式选择测试入口、测试应用/会话与少量请求，记录执行时间及来源，不在普通 pytest 收集时加载模型或调用服务。

集成服务不可用时，阶段验收停在该未完成项；可继续不依赖它的测试，但不能用“其余通过”标整阶段完成。CI/离线回归、真实服务、性能与人工复核的结果表分开，不用一条“全部通过”模糊范围。

## 7. RED → GREEN → REFACTOR 的证据

每个功能任务记录以下事实到 [开发计划](development-plan.md) 的对应任务段，不编造未运行日志：

1. 任务 ID、SPEC 版本、目标行为及新增测试文件/节点。
2. 前置状态：解释器、依赖已就绪、无意外模块来源；外部验证前提。
3. RED：完整实际命令、时间、退出码、目标失败/收集数和失败摘要；指出缺少什么能力，区分测试/环境错误。
4. GREEN：最小实现文件、相同目标命令及结果；必要时先保持简洁再重构。
5. REFACTOR/回归：改了什么/无必要重构，相关回归命令、实际 passed/failed/skipped/deselected 数。
6. 真实环境/外部/质量结果、未验证项和本任务验收决定；下任务不自动开始。

RED 不要求整个项目所有测试失败；目标测试有可信失败即可。禁止仅为了得到红灯执行不存在路径、让 pytest 退出码 5（无测试）、通过导入路径错误制造失败，或临时破坏已完成行为。缺目标模块应在测试函数体内体现，其他模块正常收集；配置错误作为被测输入时则可按契约断言。

P0-07e 无新功能，记录综合验证即可；发现缺陷时先做重现 RED。文档/环境任务没有产品代码时，如本次 P0-06，静态核查不伪装成 pytest/TDD。

## 8. 标准命令与选择规则

变量与引导过程见 [任务 SPEC 第 7 节](specs/tasks/phase0-implementation.md#7-核心流程与执行准备)。以下保留P0-07命令形式；测试文件现已存在。运行当前全量回归前按[README](../README.md)安装ml/db/rag/api四个extras，不能只同步基础环境后执行所有测试。

```powershell
# 仅当前新增测试；不要提前运行未来任务的测试路径
& $projectPython -I -m pytest tests/unit/test_config.py -q

# 当前全部默认离线回归：需完整测试依赖，但不启动真实服务
& $projectPython -I -m pytest tests/unit tests/integration --strict-markers --strict-config --import-mode=importlib --cov=clinical_agent --cov-branch --cov-report=term-missing

# 质量检查，不能代替行为测试
& $projectPython -m ruff check src tests
& $projectPython -m ruff format --check src tests
& $projectPython -m mypy src
```

到 Phase 1 之后，普通回归仍执行 unit/integration；独立外部与性能命令目标分别为 `pytest tests/external -m external`、`pytest tests/performance -m performance`，使用同一正式环境。必须有测试且选中应执行项目，不能以 deselect 全部获得验收；具体真实 DSN/凭据前提在相应阶段 SPEC/README 补齐。

默认 pytest 设置 testpaths=tests、importlib、strict markers/config，并在 addopts 使用默认 marker 选择；命令行显式 -m 选择该次范围。pytest-cov 采集语句与分支遗漏，不用“覆盖率 100%”代替异常/幂等/引用的正确性；有意不设任意 Phase 0 总分门槛，但 P0-T01–07 的必需行为必须验证。

## 9. 结果与验收报告格式

P1-12的`tests/unit/test_feishu_events.py`使用人工解码字典测试飞书消息契约、过滤及标识选择，`test_package.py`另检查feishu包隔离导入。[详细SPEC](specs/tasks/p1-12-feishu-events.md)。这些用例不执行SDK、Redis或RAG，不证明原子去重/实际收发；真实服务验收留给对应后续任务。

每次实现任务用一个简短表或段落记录：测试层、命令、环境、结果计数、数据/模型版本、是否真实服务、未完成项。错误输出只留足以判断失败的摘要，去除凭据、完整用户问题和本机敏感路径；完整日志如需留存，放受控本地 .artifacts/ 并在进度给出经过审核的摘要。

P0-07e 记录正式锁文件哈希、依赖一致性、全新环境同步/测试、wheel 路径/哈希/安装与临时 cwd CLI 运行。再次验证不应无故改锁文件；如果因真实兼容问题调整版本，先重核官方来源并更新相关技术文档，不悄悄降级版本。

P0-08 的学习文档与真实最小 Demo 已交付，Phase 0 结论见 [阶段验收报告](phase0-acceptance.md)；未来阶段仍需根据各自 SPEC 达到真实集成与评价门槛。通过 Fake 测试、通过静态文档检查、通过干净环境安装这三种结果不能互相替代。

## 10. P0-06 本次文档验收

本次计划检查：总体 P0-T01–07 全覆盖；P0-07a–e 顺序、范围和 RED 前提一致；配置/日志/CLI 可写出明确断言；文件路径及命令互相一致；运行/开发/构建依赖分离；相对链接有效、围栏闭合、无空白错误；不创建代码或执行下一任务。

P0-06 的文档核查结果和后续实现结果分别记录在 [开发计划](development-plan.md)。官方网页只支持工具能力/版本存在，不能当成本项目安装或功能验证。P0-07a–d 已有最小骨架测试 RED/GREEN 及正式锁文件；P0-07e 原/新环境各 59 passed，P0-08 最新复验 59 passed，学习示例与双入口复验通过。父进程覆盖率总计 78%（语句 81%、分支 50%），未采集隔离子进程，不能将日志/模块入口显示的低覆盖等同于未测试，也不能声称覆盖了所有子进程路径。Linux、无缓存下载、真实服务与性能尚未验证；Phase 0 已按本地骨架范围验收。


P1-13新增76项单元去重/故障/URL/资源测试、12项真实Redis集成和feishu.dedup隔离导入。默认pytest排除redis标记（与database同为显式服务测试），独立运行：

`python -m pytest tests/integration/test_feishu_dedup_redis.py -m redis -q`。

必须配置CLINICAL_AGENT_TEST_REDIS_URL；缺配置失败，不skip或降级Fake。UUID前缀隔离，只清理自己创建的键，不FLUSHALL/FLUSHDB；12客户端同步并发、租约过期/owner轮换/续租上限、完成TTL、损坏存储与响应丢失在真实Redis上验证。本次88目标/854默认回归通过，详情见[P1-13 SPEC](specs/tasks/p1-13-redis-dedup.md)及[说明](feishu-dedup.md)。P1-14已验证工作池与研究实际调用次数；P1-15已验证离线发送边界，真实租户收发仍待P1-16。


## P1-14 独立分派验收

43项worker测试使用真实ThreadPoolExecutor、Event/Barrier与替身去重/有界交接端口。真实ResearchService与LangGraph生成阶段强制两请求重叠，验证独立状态、完整DTO及来源保留；不连接真实模型/LLM/飞书。联合事件/去重/隔离导入243通过，worker语句和分支综合100%；默认回归898通过/92 deselected。默认排除真实服务场景不能视作本轮通过；P1-13 Redis脚本未修改，本轮未重跑独立真实Redis。详见[任务SPEC](specs/tasks/p1-14-feishu-worker.md)及[操作说明](feishu-worker.md)。


## P1-15 离线发送验收

72项sender目标、316项飞书/隔离导入联合、971默认回归通过（92 deselected）。真实线程/Queue/Event测试发送中容量、快照、关闭和排队过期；httpx.MockTransport验证官方reply/create、双层JSON、token后owner复查、失败/未知分类及晚到确认；Dispatcher→Sender覆盖正常和研究失败回复。sender综合语句/分支覆盖96%，未以覆盖率替代医学支持关系或真实服务验收。未连接真实飞书/Redis/模型/数据库/LLM；P1-16仍需生产鉴权/SDK装配及真实收发。详见[SPEC](specs/tasks/p1-15-feishu-sender.md)与[说明](feishu-sender.md)。


## P1-16 运行时验收

48项运行时与2项部署契约纳入367项飞书/包隔离联合；1022 passed, 93 deselected, 1 warning in 106.53s (0:01:46)。真实SDK DTO、事件处理器、protobuf数据帧ack、信号/后台终止与资源排空参与离线测试；Redis/HTTP/研究在单元测试中是替身。显式external+redis测试只回复指定测试口令：实际1 failed，185.34秒；真实SDK连接已确认，但180秒测试窗口内未收到指定口令（No matching test nonce received），未发生已确认测试回复；不得标真实收发通过。Compose config通过但镜像构建在Docker Hub鉴权网络阶段失败，不能解释为Linux/容器验收。详见[运行说明](feishu-runtime.md)和[SPEC](specs/tasks/p1-16-feishu-runtime.md)。


最终真实联调补记：用户重发并核对接收方式后，显式延长窗口至600秒；实际1 failed、606.82秒，已建立SDK连接但仍未收到指定口令/消息事件。不能确认原因是订阅方式、未生效权限、测试目标或其他客户端接收中的哪一项；未声称发送成功。需在开放平台选择使用长连接接收事件，添加im.message.receive_v1并发布所需权限后重新联调。最后证据live-external-600s.txt；接收进程与临时Redis均已清理。

## P1-16 发布后真实收发补验（2026-10-27）

用户在开放平台发布配置后再次执行既有external+redis测试：**1 passed、1个SDK弃用警告，34.38秒**。实际输出依次为P116_LIVE_CONNECTED、P116_LIVE_EVENT accepted/eligible、P116_LIVE_SENT；真实官方SDK收到指定口令，官方reply接口明确成功，真实Redis owner complete返回owned。证据`.artifacts/p1-16-20261027/live-external-published.txt`。旧180/600秒未收到事件的失败保留为当时事实，本次已补齐指定口令收发验收；不能将旧记录当作当前收发状态。

研究端口为明确的合成ResearchPort，仅回复本地范围/合成测试的证据不足文本，未执行真实医学检索、E5/PG/付费LLM完整链路，也未把HTTP成功当成医学正确性。沿用当前实现，没有因联调成功修改核心代码或放宽测试。凭据仅通过隐藏终端输入及进程环境传递，不写源码或证据；运行结束SDK进程及临时隔离Redis已退出。

当前剩余P1-16验收为Linux共享镜像构建、Compose容器启动/停止；不因真实收发成功自动标记部署或Phase1完成。P1-17未开始。

## P1-16 Linux容器最终验收（2026-10-27）

本次完成P1-16剩余验收，以下结论取代此前“镜像网络阻塞/容器待验收”的当前状态；旧失败保留为历史。

Docker直连Hub超时后，只读确认既有本机7890代理可访问官方registry。使用官方google/go-containerregistry的crane v0.22.1（校验官方release SHA256）获取固定python:3.12.15-slim-bookworm及redis:8.2.2-alpine的linux/amd64镜像；未使用不明镜像源、未关闭TLS/摘要检查、未改Docker/系统全局代理。Python源platform manifest为57d96f71de145a98e7ceca18ee4ade77bba4103a33a72dfaea026b23625c6bf0，Redis为3f835dae62fe5012baf5a768293967c93bc09cf9e848d415351dfba04ee87537。导入后以临时HTTP_PROXY/HTTPS_PROXY build args和正式uv.lock构建共用镜像；生产镜像未保留代理或凭据ENV。89个Linux运行包安装并uv pip check通过，CLI help与非root配置通过。

首次Compose脚本在机器人就绪日志上超时，不能算通过。定位发现_LOG=logging.getLogger(__name__)在python -m入口下成为__main__，脱离feishu JSON handler。新增真实runpy别名测试先RED（1 failed/48 deselected，entrypoint-red.txt），固定logger名称为feishu.main后GREEN（1 passed/48 deselected，entrypoint-green.txt）；仅这一行应用修复，不改SDK/研究/去重/发送算法。第二次脚本仍超时，核查是验收辅助脚本仅采集docker logs的stdout，漏掉了JSON日志所在的stderr；修正为日志命令合并两流，未放宽就绪条件，旧失败另存compose-accept-result-initial.json与compose-accept-result-stdout-only.json。修复后368联合（94.44秒）及1023 passed/93 deselected默认回归（155.73秒）通过；Ruff/format（82文件）/mypy（38源码）通过。证据container-fix-*.txt。

最终Compose使用独立项目clinical-p116-accept-20261027、全新测试卷及空env文件，端口通过验收override移除，避免触碰既有数据库/服务。PostgreSQL/Redis健康、现有Alembic迁移、真实E5只读挂载、API runtime ready与空库问答insufficient_evidence/零claims/零sources均通过；未调用付费LLM。生产python -m feishu.main入口加载共享研究装配并连接真实SDK；API/机器人使用同一镜像、UID10001、只读模型。收到SIGTERM后机器人exit_code=0，API exit_code=143且日志明确Application shutdown complete/Finished server process，两者OOMKilled=false。Uvicorn0.54会在优雅关闭后重新抛出已捕获信号，因此Linux API的143可为正常信号退出，不能单独据此判定失败或成功；已按实际源码及关闭日志修正验收判据，旧误判记录另存compose-accept-result-api143.json。随后只删除本次项目的容器、卷及网络，清理断言通过。实际脚本耗时111.28秒，脚本断言通过，不冒称pytest用例数量。

最终应用镜像ID：sha256:013d6909cef814039ea1f610e5bd4f4c1f60fc65e683714d2bde603266e50a9c。证据docker-build-proxy.txt、python-base-pull.txt、redis-base-pull.txt、image-check.json、compose-accept-result.json、compose-accept-commands.json及compose-accept-api/feishu_bot.log。真实口令收发仍以此前live-external-published.txt的1 passed/34.38秒为准（研究为合成替身）；本次生产容器验证启动/连接/停止，不追加真实医学消息。

P1-16任务内无阻塞，Phase1尚未整体验收。真实E5/PG/付费LLM完整研究链路、医学支持关系人工审查、解释器升级前置要求与phase-01六份学习文档仍归P1-17；未自动开始。原有未提交改动保留，未创建Git提交。
