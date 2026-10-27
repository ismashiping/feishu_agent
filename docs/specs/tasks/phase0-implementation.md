# Phase 0 最小工程任务 SPEC

历史范围：本文记录Phase 0对应任务/教材时点，旧测试数、模块数及“下一任务”不表示当前状态。当前进度见[任务表](../../development-plan.md#phase-1-任务进度)；在当前仓库跑全量测试须安装ml/db/rag/api四个extras，基础doctor示例仍无需这些业务依赖。

版本：0.7；日期：2026-10-26；制定任务：P0-06；状态：P0-07a–d 已取得 RED/GREEN；P0-07e Windows 干净环境/wheel/回归与 P0-08 学习/独立验收均完成。结论见 [阶段报告](../../phase0-acceptance.md)，过程见开发计划。

P0-07a 环境修订：uv 0.13.5 无 CPython 3.12.16 Windows 下载；官方 standalone 最新发行 20261021 仅提供 3.12.15。当前开发环境显式固定 3.12.15，保留 >=3.12,<3.13 范围；原 3.12.16 准备失败不算 RED。3.12.16 安全修订的构建升级仍待后续核查，不能把 3.12.15 离线骨架验证扩大成外部服务/部署验证。[官方发行](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021)。

## 1. 背景及目标

依据 [总体 SPEC](../00-project-overview.md)、[架构设计](../../architecture.md) 和 [测试策略](../../testing-strategy.md)，将 P0-T01–07 落到 P0-07a–e 五个顺序任务。每次只执行其中一个任务；P0-07e 为综合验证而非新增功能，之后 P0-08 才生成学习材料及阶段验收。

制定本 SPEC 的 P0-06 仅交付文档；命令是实现任务的执行约定，不能据此判断已运行。P0-07a–d 已执行的环境/包/配置/日志/runtime/CLI 与真实 RED/GREEN，以及 P0-07e 的原/新环境回归、wheel 构建/独立安装证据单列于开发计划。本次为 Windows、本地缓存验证，非 Linux 或无缓存验证。

## 2. 功能需求及任务拆分

| 任务 | 当前任务必须交付 | 允许修改文件 | 不提前交付 |
| --- | --- | --- | --- |
| P0-07a | 隔离 Python、最小包声明、正式锁文件、可安装且导入无副作用的包 | pyproject.toml、uv.lock、.python-version、.gitignore、README.md 环境段；src/clinical_agent/__init__.py；tests/unit/test_package.py；必要的 tests/conftest.py；进度记录 | config、日志、CLI、业务接口 |
| P0-07b | Settings、显式 load_settings、环境覆盖及验证 | src/clinical_agent/config.py；tests/unit/test_config.py；扩展导入安全参数；.env.example；进度记录 | SDK 配置、线程数/模型等未使用字段 |
| P0-07c | 显式、可重复配置的结构化日志及敏感字段控制 | src/clinical_agent/logging_config.py；tests/unit/test_logging_config.py；扩展导入安全参数；进度记录 | 日志平台、文件轮转体系、任意文本脱敏框架 |
| P0-07d | 本地 runtime 装配、CLI help/doctor、两种等价入口 | src/clinical_agent/bootstrap.py、cli.py、__main__.py；tests/unit/test_bootstrap.py、tests/integration/test_cli.py；脚本声明/README/必要锁文件同步；导入安全参数；进度记录 | 医学业务、API、飞书、假 RAG 服务 |
| P0-07e | 干净环境重现、wheel 验证、全量回归及质量验收 | README.md、必要工具设置/锁文件及进度；缺陷修复前先补对应失败测试 | 新增产品功能、仅为覆盖率添加无关测试 |

tests/conftest.py 只在已存在两处以上真实共享需求时抽取 fixture；不要求预建 helper 框架。各任务可补必要文档，但不能据此批量创建未来模块。

## 3. 非功能需求

- 当前项目开发解释器固定 CPython 3.12.15、`requires-python = ">=3.12,<3.13"`；本机 Python 3.10 只作工具引导，不修改其安装包。原 3.12.16 无构建的问题及本次显式修订见上，不静默替换版本或将环境失败称为 RED。
- 采用标准 src 布局，不设置 pytest pythonpath、不注入 sys.path；发行名 clinical-literature-agent，初始项目版本 0.1.0，实际 import 为 clinical_agent。
- 普通模块导入不读配置、不配置日志、不建连接/线程、不下载模型；__main__ 仅在作为入口执行时委托 main。
- 测试不依赖真实 .env 或当前工作目录；子进程用项目解释器、隔离导入和临时工作目录，设置有界超时，避免无限挂起。
- 功能 RED 的目标测试应成功收集并因约定能力缺失失败；pytest 缺失、网络/安装错误、语法错误和测试路径错误都属于前置问题，不能作为功能 RED。
- 不预先加入领域、数据库、LangGraph、LLM、API、飞书或 ML 依赖；锁文件、构建产物和真实安装均需明确区分。

## 4. 本阶段不实现的内容

不实现 Phase 1–9 的任何业务，也不创建 application/domain/adapters/feishu 空包。无数据库迁移、Compose 服务、外部健康检查、任务队列、线程池或自动化调度。doctor 只说明本地配置和运行环境，不代表科研系统已可用。

P0-07e 不通过破坏现有代码、人为添加错误再修复来制造 RED；它运行已建立的测试及环境验证。若发现实际行为缺陷，应先补能重现缺陷的测试再修复并回归。

## 5. 输入输出契约

### 5.1 P0-07a：包与依赖

运行依赖采用已核查的 pydantic 2.14.1、pydantic-settings 2.16.1、structlog 26.1.0；开发组为 pytest 9.1.1、pytest-asyncio 1.4.1、pytest-cov 7.1.0、ruff 0.17.2、mypy 2.4.0、uv 0.13.5。研究清单只是依据，P0-07a 用目标环境重新解析、生成正式 uv.lock 并验证。

构建后端选择 `setuptools.build_meta`，build-system.requires 固定 setuptools==83.0.0；此构建依赖不混作运行依赖。P0-06 已从 [该版本 PyPI](https://pypi.org/project/setuptools/83.0.0/) 核实版本可用、Python >=3.10，发行日 2026-07-04，非最新版本；选择其成熟 src/pyproject 支持并限制本次新增变量。使用静态版本、显式 src 包发现，不在构建时 import 项目求版本。[官方 pyproject 配置](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)。P0-06 制定时尚未执行安装/构建及正式锁解析；现有实际安装/构建证据见 P0-07a–e 开发记录，不能只凭官网声明兼容已通过。

先准备环境与测试依赖，暂不安装根项目；编写包行为测试并取得 RED 后，才创建 __init__.py 并安装项目取得 GREEN。允许提前创建空 src/ 供元数据/包发现准备，但不能提前写目标 Python 实现。若后端在源码缺失时拒绝元数据准备，先解决仅涉及构建声明/空目录的前置问题；不得把安装失败记作测试失败，或预写包实现绕过 RED。

### 5.2 P0-07b：配置

公开接口 `Settings` 和 `load_settings() -> Settings`。后者每次显式构造新实例，不全局缓存。Settings 使用 pydantic-settings；环境变量前缀 CLINICAL_AGENT_，环境变量名不区分大小写；枚举值区分大小写。

| 字段 | 环境变量 | 默认值 | 合法值 |
| --- | --- | --- | --- |
| app_env | CLINICAL_AGENT_APP_ENV | development | development / test / production |
| log_level | CLINICAL_AGENT_LOG_LEVEL | INFO | DEBUG / INFO / WARNING / ERROR / CRITICAL |

不自动读 .env（包括当前目录和仓库根目录）；.env.example 仅为这两个值的使用示例。无关主机环境变量忽略，不能将整份 os.environ 当严格配置模型输入。非法值抛 Pydantic ValidationError，错误文本隐藏输入值；CLI 再映射安全错误。数字字符串如 log_level=123 也是非法值，不为满足“非法数值”测试增加无用途的数值字段。

### 5.3 P0-07c：日志

公开接口 `configure_logging(settings: Settings) -> None`；显式配置本项目的 `clinical_agent` 命名日志，支持 structlog 和同名标准 logging 接入。使用成熟处理器/formatter，必要的业务字段筛选保持短小函数，不造日志框架。[structlog 标准日志集成](https://www.structlog.org/en/stable/standard-library.html)。

日志为 stderr 上一行一 JSON，stdout 留给 CLI 结果。每条含 event、level（小写）、timestamp（可解析带时区 UTC）；request_id、app_env、error_code、exception_type 为可选允许字段。时间不要求精确字符串格式或时刻相等；级别遵循 Settings，INFO 下 DEBUG 不输出。

采用小范围允许字段策略，丢弃 api_key、token、password、headers、payload、任意额外对象和 exc_info 等未允许字段；不输出原始异常消息/堆栈。event 与 error_code 是程序控制的标识，不能直接填用户文本；request_id 是应用生成/可信上下文的关联标识。此策略不承诺能检测任意字符串里的秘密，应用不得把问题、文献或凭据塞进允许字段。

重复 configure_logging 不叠加本项目 handler；新设置可更新项目级别，不重置第三方/root 的全部 handler。测试需隔离并恢复 structlog/logging 状态或使用子进程，不能靠运行顺序通过。

P0-07c 实施细化：允许的上下文字段仅保留字符串，UUID 由调用方显式转字符串；非字符串对象即使位于允许字段也丢弃，不调用其 repr/自定义序列化。level/timestamp 由日志处理器生成，不能由附加字段伪造。标准 logging 使用固定事件标识和 extra 元数据，不将位置参数插值为事件文本；原始 exc_info/stack_info 不进入输出。本项目命名 logger 不向 root 重复传播；只替换本模块拥有的 handler，不关闭其他 logger 的 handler。

### 5.4 P0-07d：runtime 与 CLI

bootstrap 公开 `open_runtime(settings: Settings | None = None, *, request_id: UUID | None = None)` 上下文管理器，yield 一个 Runtime。显式 settings 直接采用，不再读环境；未传入时只调用一次 load_settings。request_id 未传时生成 UUID；启动时显式 configure_logging；Phase 0 不持有外部客户端或线程，不伪造资源生命周期演示。

CLI 公开 `main(argv: Sequence[str] | None = None, *, runtime_factory: Callable[[], AbstractContextManager[Runtime]] | None = None) -> int`。默认使用 open_runtime，允许测试注入 Fake context manager。help/解析在 runtime 前处理；argparse 的 help/解析异常可按标准行为抛 SystemExit(0/2)，doctor 正常返回 0，配置失败返回 2，意外失败返回 1。模块入口调用 `raise SystemExit(main())`，console script 同样使用 main。

| 命令 | stdout | stderr | 退出码 / 装配 |
| --- | --- | --- | --- |
| clinical-agent --help / python -m clinical_agent --help | 帮助文本 | 空 | 0；不建 runtime，不读取配置 |
| 无子命令 | 帮助文本 | 空 | 0；不建 runtime |
| doctor | 一份 DoctorReport JSON | 可有项目 JSON 日志 | 0；只检查本地环境 |
| 不支持命令/参数 | 无结果 JSON | argparse 用法提示 | 2；不建 runtime |
| doctor + 非法配置 | 无结果 JSON | 固定安全配置错误 | 2；不能原样输出 ValidationError |
| doctor 意外失败 | 无成功结果 JSON | 固定安全错误与可用的受控错误日志 | 1；已进入的上下文必须退出 |

固定安全错误文本分别为 `Invalid configuration.` 和 `Local check failed.`，不附环境输入值、异常消息、路径或 traceback。早期配置错误还没装好 logger 时直接输出安全文本，不为它强行构建日志系统。不能承诺 argparse 对用户自己输入的任意非法参数隐藏其内容，但不得把环境密钥当参数传入或主动打印环境。

DoctorReport 的 status=ok、scope=local_environment、external_services_checked=false；包含 python_version（只含主/次/补丁）、app_env 和 request_id。JSON 不固定键顺序/缩进；不含密钥、绝对路径、全量包清单或医学问答状态。日志与结果使用相同 request_id。允许用 cli.py 内的小函数 `build_doctor_report(runtime)` 构造结果以便在错误路径中验证上下文退出，不额外拆模块。

doctor 在上下文内构造结果、成功退出上下文后再向 stdout 发布成功 JSON；清理失败时不能已输出成功结果又返回失败。配置错误仅指配置读取/装配阶段的验证错误，不能把结果构造时任意 ValidationError 都误归为用户配置错误。

P0-07d 实施细化：doctor 成功退出上下文后记录固定事件 `local_check_completed`，使用字符串 request_id 和 app_env；INFO 下可见，WARNING 及以上可被级别过滤。意外失败返回固定安全错误；已进入 runtime 时记录受控 `local_check_failed`（error_code=local_check_failed、异常类型名，不附异常内容），未完成装配时不强制初始化日志。配置装配阶段的 ValidationError 返回 2，body/退出阶段的 ValidationError 返回 1。Runtime 只是 frozen dataclass，冻结字段绑定，不宣称深度冻结 Settings。使用标准 argparse/contextlib/dataclasses 与已有 Pydantic，不新增依赖；console script 声明为 `clinical-agent = "clinical_agent.cli:main"`，通过正式重新安装生成入口，不手写启动脚本。

## 6. 数据模型

Settings 为上述两个受限字段；Runtime 用简单不可变 dataclass，字段 settings、request_id，不实现容器接口、service locator 或假的 close 方法。DoctorReport 用 Pydantic 模型，字段仅为第 5 节所列；这些是 Phase 0 本地契约，不创建 Phase 1 领域模型。

RuntimeFactory 是局部 callable 类型别名，不增加工厂继承体系。Fake context manager 只验证 CLI 是否使用并退出注入上下文；它不证明未来数据库/SDK 已正确关闭。

## 7. 核心流程与执行准备

### 7.1 工具与环境准备（P0-07a 才执行）

以下 PowerShell 约定在项目根运行；实际执行结果以 P0-07a 记录为准。Bootstrap uv 已由 P0-01/03 验证存在，但需要联网的安装/下载在实施时遵守环境权限规则。

```powershell
$taskBootstrapPython = 'C:\Users\11091\.conda\envs\medical-agent\python.exe'
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.research-cache/uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path (Get-Location) '.tools/python'
$env:UV_TOOL_DIR = Join-Path (Get-Location) '.tools/uv-tools'
function Invoke-ProjectUv {
    & $taskBootstrapPython -m uv tool run --from uv==0.13.5 uv @args
}
Invoke-ProjectUv --version
Invoke-ProjectUv python install 3.12.15 --no-bin --no-registry
Invoke-ProjectUv python pin 3.12.15
```

Invoke-ProjectUv 仅用隔离工具环境运行已选版本，不向共享 Conda pip install。工具与 Python 缓存使用项目内排除目录。构建声明、测试设置与空源码目录准备好后生成正式锁文件：

```powershell
Invoke-ProjectUv lock
Invoke-ProjectUv sync --locked --group dev --no-install-project
$projectPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
& $projectPython -I -m pytest --version
```

此时测试依赖已具备，目标包还未实现/安装；先写 tests/unit/test_package.py，再执行下节 RED。不要使用 uvx pytest，因为它不一定能看到项目安装；这里用准确项目解释器直接执行，避免 uv run 在 RED 时自动安装根项目。[uv 工具隔离](https://docs.astral.sh/uv/guides/tools/)、[partial sync](https://docs.astral.sh/uv/concepts/projects/sync/)。

环境准备失败时只记录前置失败并修复，不进入功能 GREEN；不执行不存在测试路径来制造“失败”。每个后续任务只新建其自己的测试，不提前运行含未来未实现模块的全套测试。

### 7.2 各任务 RED → GREEN → 回归

下表命令中的 $projectPython 均指同一个 .venv 解释器。测试在函数体内 import 缺失的目标模块，或用子进程观察目标行为；测试模块本身必须能收集。

| 任务 | 首个目标 RED 命令与预期失败 | 最小 GREEN 与回归 |
| --- | --- | --- |
| P0-07a | `& $projectPython -I -m pytest tests/unit/test_package.py -q`；目标 import clinical_agent 失败，或子进程 returncode 断言失败，原因必须是目标包未提供 | 仅创建轻量 __init__.py，`Invoke-ProjectUv sync --locked --group dev` 安装根项目，原命令通过；检查包来源为本项目 src，不是其他已安装同名包 |
| P0-07b | `& $projectPython -I -m pytest tests/unit/test_config.py -q`；缺失 clinical_agent.config/约定配置能力 | 实现两个字段和显式 load_settings；相同测试通过，再跑已有 tests/unit；扩展导入安全覆盖 config |
| P0-07c | `& $projectPython -I -m pytest tests/unit/test_logging_config.py -q`；缺失 logging_config/约定日志行为 | 实现最小日志配置/字段策略；相同测试通过，再跑已有 tests/unit；扩展导入安全覆盖 logging_config |
| P0-07d | `& $projectPython -I -m pytest tests/unit/test_bootstrap.py -q`；缺失 bootstrap/约定 runtime；另在写 CLI 前跑 integration/test_cli.py 的 help/doctor 目标 RED，记录缺入口而非错误解释器 | 先最小 bootstrap、再 CLI/__main__/console script，各目标分别取得 GREEN；完整 tests/unit tests/integration 回归。不能先写完 CLI 再补称已有 RED |
| P0-07e | 无新增功能不制造 RED；执行既有回归、干净环境、构建验证；若发现缺陷先补最小重现失败测试 | 修复后重跑目标及相关回归，最后执行第 10 节所有门禁 |

P0-07d 的两个 RED 检查仍属于同一小型入口任务，过程必须分清；它不能顺带添加 API/业务服务。每次 RED 留存真实失败摘要及命令退出码，必要重构后重复原断言，不删除或降级用例。

## 8. 异常与边界场景

解释器/工具版本不可得、依赖解析/下载失败、残留环境污染、同名包误导入；配置缺省、环境变化、未知主机变量、非法数字/枚举及意外 .env；日志重复 handler、级别更新、敏感嵌套字段和异常对象；无参数/help 受非法配置影响、stdout/stderr 混用、JSON 脆弱快照、runtime 构造/消费失败及错误中泄漏输入。

测试子进程默认 10 秒上限，只约束本地轻量命令，超时算失败，不算性能评估。mock 的网络阻断应只覆盖本地测试进程，不能影响依赖下载/安装；缓存/安装过程的联网与产品运行不联网分别记录。

## 9. 测试用例清单及映射

此处是未来测试函数名称约定，参数化样例数量实施时如实报告，不能把下列清单当实际执行数量。

| 总体 ID | 测试文件 / 函数 | 关键断言 |
| --- | --- | --- |
| P0-T01 | tests/unit/test_package.py::test_package_import_is_isolated_and_quiet | 已安装目标包在临时 cwd + -I/-B 子进程可导入；项目模块 import 无输出、无资源行为；逐任务参数化仅已实现模块 |
| P0-T02 | tests/unit/test_config.py::test_defaults_without_external_credentials | 默认 development/INFO，无数据库或密钥要求 |
| P0-T02 | tests/unit/test_config.py::test_environment_overrides_and_reloads | test/DEBUG 等覆盖生效；两次调用之间改环境后能读到新值 |
| P0-T02 | tests/unit/test_config.py::test_invalid_values_are_rejected | 非法枚举/数字字符串均失败，异常文本隐藏输入 |
| P0-T02 | tests/unit/test_config.py::test_no_implicit_dotenv | 临时目录放冲突 .env 仍不影响默认/显式环境 |
| P0-T03 | tests/unit/test_logging_config.py::test_json_fields_and_stderr | structlog 和同名标准日志均输出 JSON 到 stderr；时间 UTC；stdout 空 |
| P0-T03 | tests/unit/test_logging_config.py::test_level_filter_and_reconfiguration | INFO 不输出 DEBUG；两次配置不重复发一条记录；级别更新有效 |
| P0-T03 | tests/unit/test_logging_config.py::test_sensitive_fields_are_not_emitted | 测试用秘密、嵌套 payload 与异常原文不出现在最终输出 |
| P0-T05 | tests/unit/test_bootstrap.py::test_explicit_settings_are_used_with_fixed_request_id | 采用注入 Settings 与 request_id，不重读相冲突环境 |
| P0-T05 | tests/unit/test_bootstrap.py::test_cli_runtime_factory_lifecycle | Fake context manager 的进入/退出及传入值确实被 CLI 消费；成功和 body 异常路径均退出 |
| P0-T04 | tests/integration/test_cli.py::test_help_does_not_build_runtime | 无命令及 help 成功，非法环境也不触发配置读取；默认入口与注入入口分别验证 |
| P0-T04 | tests/integration/test_cli.py::test_doctor_json_and_logs | 模块/console script 语义相同，JSON 合法、scope 本地、不验证外部服务，日志关联 ID 一致 |
| P0-T04 | tests/integration/test_cli.py::test_invalid_cli_and_config_are_safe | 未知命令 exit 2；坏配置 exit 2；意外失败 exit 1；环境 sentinel 不在配置/意外错误输出 |
| P0-T06 | P0-07a 安装记录 + P0-07e 干净重建/wheel 冒烟 | 锁定安装、pip check、临时 cwd 导入及 doctor，无源码路径注入 |
| P0-T07 | Ruff/mypy 命令 | 当前源代码和测试规范检查通过，无全局 ignore_errors |

导入安全测试使用临时 cwd、最小必要系统环境、`sys.executable -I -B`，对 connect/create_connection 和受控重库 import 设失败哨兵；模块在测试子进程里加载，不能因父进程提前 import 命中缓存误判。只检测会破坏边界的资源行为，不断言 Pydantic 内部实现。

## 10. 可执行验收标准

### 10.1 共同回归与质量门禁（P0-07 完成后执行）

```powershell
Invoke-ProjectUv lock --check
Invoke-ProjectUv sync --locked --group dev
& $projectPython -m uv pip check --python $projectPython
& $projectPython -I -m pytest tests/unit tests/integration --strict-markers --strict-config --import-mode=importlib --cov=clinical_agent --cov-branch --cov-report=term-missing
& $projectPython -m ruff check src tests
& $projectPython -m ruff format --check src tests
& $projectPython -m mypy src
& $projectPython -I -m clinical_agent --help
& $projectPython -I -m clinical_agent doctor
```

pytest 配置固定 testpaths=tests、importlib 模式、strict markers/config；注册 external、integration、performance 标记供之后分层使用，addopts 默认选择 `not external and not performance`，显式命令行 -m 覆盖默认选择；不跳过 Phase 0 必须项。pytest-asyncio 使用 strict、fixture loop scope=function，Phase 0 不为展示依赖而写无业务含义的 async 测试。Ruff target-version=py312、line-length=100，基础 E/F/I/UP/B 规则；mypy 对 src 开 strict，不把第三方错误整体屏蔽。覆盖率用于查遗漏，不以任意百分比替代清单验收。

### 10.2 干净环境和 wheel

P0-07e 通过 UV_PROJECT_ENVIRONMENT 指向项目内新的 .artifacts/repro-venv，使用同一锁文件/解释器执行 sync --locked --group dev、pip check、全部离线测试；使用该新环境的解释器，不能继续误用旧 $projectPython。记录前后 uv.lock 哈希，结束恢复临时环境设置。若目录已存在且非本次新建，不直接递归删除，先另建确定的新路径。

构建并记录本次 wheel 的绝对路径与 SHA256：`Invoke-ProjectUv build --wheel --no-sources --out-dir .artifacts/wheel-build`。用 `Invoke-ProjectUv export --locked --no-dev --no-emit-project --format requirements-txt --output-file .artifacts/runtime-requirements.txt` 导出仅运行依赖及哈希；在另一新隔离环境先按该文件 `pip install --require-hashes`，再安装本次 wheel（--no-deps），从临时 cwd 执行 help/doctor 并比较结果。不拿旧 dist 中第一个 wheel 冒充本次产物，也不发布 PyPI。

构建与新环境安装允许按权限规则访问官方包索引；pytest/doctor 不访问网络。P0-07e 已使用本地缓存离线完成构建/安装，具体证据见开发计划；上述步骤不能扩大为无缓存或其他平台均已验证。

P0-07e 执行细化：为每次验证新建 .artifacts/p0-07e-日期-序号/，其下分别放 repro-venv、wheel-venv、wheel-build、临时 cwd 与命令日志，拒绝复用已有环境或删除旧目录。uv 使用固定 0.13.5 与项目内 Python 3.12.15、缓存，优先 --offline；`uv pip install --python <wheel-python> --require-hashes -r <requirements>` 执行运行依赖的哈希约束安装，随后 `--no-deps` 安装本次明确路径的 wheel，不额外引入 pip。开发环境与干净开发环境各运行现有完整回归/分支覆盖率，覆盖率不含未启用采集的子进程，应如实解释而不改测试凑比例。wheel 环境仅含运行依赖，从临时 cwd 检查六个模块来源位于该环境 site-packages、无 editable 源路径，再执行模块/脚本的 help、doctor 与安全错误冒烟。比较 doctor 的稳定语义字段及其日志关联 ID，不比较随机 UUID/时刻。记录前后锁/源码/测试哈希及实际 wheel SHA256；缓存可用不代表无缓存安装或 Linux 已验证。

## 11. 阶段依赖及完成定义（DoD）

进入 P0-07a 需 P0-01–06 文档任务验收；每个 P0-07 子任务在其文件范围内完成目标 RED/GREEN、相关回归及实际命令记录后停止。纯环境/质量步骤单列，不把它们替代功能 RED。README 只填写真实执行过的安装/Demo，不照抄本计划当运行成功。

P0-07a–e 完成不自动标 Phase 0 完成：P0-08 的真实 Demo、学习六文件、设计取舍、阶段总结与独立验收现已交付，详见 [学习导航](../../learning/phase-00/README.md) 和阶段报告。下一任务为 P1-01 文献与证据 DTO、来源和定位契约，用户未指定时不自动开始。
