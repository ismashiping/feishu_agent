> 历史快照：2026-10-28 整理前内容，原结论仅代表记录时点。当前事实见 [文档导航](../README.md)。仅重定位链接，未改写验收结论。

# Clinical Literature Research Agent

Phase8维护核心已交付并完成范围内工程验收：文献版本、本地/在线完整窗口增量、来源状态治理、显式重建和历史证据保留。运行前需由操作者显式升级p804_0007；[验收结果与限制](../phase8-acceptance.md)、[使用及学习导航](../learning/phase-08/README.md)。Phase7真实报告/医学待审保留，Phase9未启动。

Phase 5：本地支持vector/keyword/hybrid，采用PostgreSQL FTS与RRF，默认vector保留。现有库需显式升级迁移p501_0003；关键词当前支持ASCII英文/标识符。见[学习导航](../learning/phase-05/README.md)与[验收记录](../phase5-acceptance.md)。

Phase 4：已新增官方 PubMed 在线检索和 local/online/hybrid 问答范围，包含分页/限流/摘要来源与引用追溯。用法见 [学习导航](../learning/phase-04/README.md)和[验收记录](../phase4-acceptance.md)。这不包含 Phase 5 关键词融合、自动入库或全文获取；Phase 3 真实模型样例仍待验收。

## 当前后续开发路线（2026-10-28）

**Phase 3 PICO 分析与查询规划 → Phase 4 PubMed 在线检索 → Phase 5 关键词 + 向量混合检索 → Phase 6 医学证据分析 → Phase 7 引用核验与结构化报告**；Phase 3 核心实现与学习材料已交付、待真实模型验收，Phase 4 在线核心链路已完成范围验收，Phase 5核心混合检索已完成范围验收，Phase 6–7 核心分析/报告实现已交付，真实报告链路和医学人工待审仍保留；最小评价基线与六角色有界反馈已交付。Phase8维护核心已实现，包括版本、本地/在线窗口增量、来源治理和显式重建，实际验收与限制见[Phase8记录](../phase8-acceptance.md)及[学习导航](../learning/phase-08/README.md)。Phase2继续延期，Phase9完整评价未启动；非核心健壮性、性能和复杂异常处理另行规划；现有超时、错误、数据一致性及医学引用真实性约束保留。

每阶段先明确 SPEC 和验收测试，再实现核心链路；取消单次会话测试/回归，在阶段末集中执行测试与验收，未执行不标通过。Phase 1 技术和教材已交付，医学人工签署仍待完成，保留原验收状态及历史证据。最新基线、阶段依赖、延期清单和完成标准见[开发计划](../development-plan.md)及[测试策略](../testing-strategy.md)。Phase 3 使用说明见 [学习导航](../learning/phase-03/README.md)和 [详细 SPEC](../specs/tasks/p3-01-pico.md)。正式问答入口新增一次 PICO 模型调用（默认上限 20 秒），即使本地空库也先规划；JSON 附加 query_plan，需澄清时不检索/不生成结论。

当前架构职责：**LangGraph 负责 Agent 编排，LangChain 负责标准化模型调用及通用 Agent 工具接口，DeepSeek 仅作为底层模型供应商。** 模型生成使用 LangChain 通用 `ChatOpenAI` 兼容接口和 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 配置；源码不包含供应商专属模块、类型或依赖。HTTPX 承担底层传输与边界防护；领域层独立核验引用。详见[架构设计](../architecture.md)与[本次调整 SPEC](../specs/tasks/langchain-model-boundary.md)。

医学文献检索与循证问答的渐进式Python项目，用于科研辅助。**Phase0已完成，Phase1当前完成P1-01–16：离线入库、本地向量检索、基础RAG证据关联回答、CLI、FastAPI、飞书纯事件过滤、Redis原子去重、有界研究任务分派及文本渲染/受限发送**。可通过HTTP、CLI或Python服务调用；P1-16官方SDK真实收发、鉴权装配、共享镜像与隔离Compose运行已验收，具体边界见[运行说明](../feishu-runtime.md)；[有界分派说明](../feishu-worker.md)。[渲染与发送](../feishu-sender.md)（P1-15离线协议与P1-16合成研究的真实SDK收发已验证）。[飞书过滤契约](../feishu-events.md)。[API用法](../api.md)。[CLI用法及退出码](../cli.md)。当前RAG装配与验证边界见 [使用说明](../basic-rag.md)。

## 当前环境

| 项目 | 已验证值 |
| --- | --- |
| 开发平台 | Windows x64 |
| 项目解释器 | CPython 3.12.16，位于项目 .tools/p117-python31216/python/ |
| 项目环境 | .venv/，不继承共享 Conda 的安装包 |
| 工具 | uv 0.13.5（引导环境原有 uv 0.13.1 未修改） |
| 发行包 / 导入名 | clinical-literature-agent 0.1.0 / clinical_agent |
| 正式依赖 | pyproject.toml + uv.lock |
| 构建后端 | setuptools.build_meta；构建隔离依赖固定 setuptools 83.0.0 |

P1-17已通过官方standalone20261026的SHA256SUMS取得并验证3.12.16；正式.venv与Dockerfile已升级，原环境保留为.venv-p117-prior。uv0.13.5内置下载清单落后于官方资产，安装时显式使用已核验的解释器。复验及边界见[阶段报告](../phase1-acceptance.md)。

## 安装（PowerShell，项目根目录）

以下为本机已验证的引导方式；其他机器可替换引导 Python 路径或使用已安装的 uv 0.13.5。下载/安装需要网络权限，测试本身不需要服务或密钥。

```powershell
$taskBootstrapPython = 'C:\Users\11091\.conda\envs\medical-agent\python.exe'
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.research-cache/uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path (Get-Location) '.tools/python'
$env:UV_TOOL_DIR = Join-Path (Get-Location) '.tools/uv-tools'
function Invoke-ProjectUv {
    & $taskBootstrapPython -m uv tool run --from uv==0.13.5 uv @args
}

Invoke-ProjectUv --version
# uv内置清单尚无3.12.16；脚本从官方资产下载并校验已冻结SHA256。
$phase1Python = & ./docs/learning/phase-01/install-python.ps1
Invoke-ProjectUv sync --locked --group dev --extra ml --extra db --extra rag --extra api --extra feishu --python $phase1Python
```

引导脚本仅解包至项目内目录，不注册用户级解释器入口；无需更改系统 PATH 或激活/改造共享 Conda。实际 .venv 基于受控的项目内解释器。不要把 docs/research/dependencies/ 的历史解析清单当正式环境安装说明。

## 最小验证

```powershell
$projectPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
& $projectPython -I -c "import clinical_agent; print(clinical_agent.__file__)"
& $projectPython -m uv lock --check --offline
& $projectPython -m uv pip check --python $projectPython
& $projectPython -I -m pytest tests/unit/test_package.py -q --basetemp=.artifacts/pytest-p0-07a
& $projectPython -I -m pytest tests -q --basetemp=.artifacts/pytest-local
& $projectPython -m ruff check src tests
& $projectPython -m ruff format --check src tests
& $projectPython -m mypy src
```

测试从新子进程的临时工作目录导入已安装的包，检查静默导入、包来源、网络/线程调用及日志 handler 变更；它不验证医学业务或任何外部系统。已提供等价的 `python -m clinical_agent` 和 `clinical-agent` 入口；修改脚本声明后需重新安装项目，不能只复制源码。

若主机设置过 PYTEST_ADDOPTS/PYTEST_PLUGINS 等测试注入变量，先在启动 pytest 前保存并清理，结束后恢复；实际执行记录采用这种隔离方式。--basetemp 目录只能用于本项目测试，pytest 会清理自身临时目录，勿指向用户数据目录。

## 显式配置

导入 clinical_agent.config 不创建配置实例；调用 load_settings() 才读取当前进程环境，每次返回新实例，不使用全局缓存。

| 环境变量 | 默认值 | 合法值 |
| --- | --- | --- |
| CLINICAL_AGENT_APP_ENV | development | development / test / production |
| CLINICAL_AGENT_LOG_LEVEL | INFO | DEBUG / INFO / WARNING / ERROR / CRITICAL |

变量名不区分大小写，枚举值区分大小写；缺失时使用默认值，不要求数据库或 API 密钥。无关主机环境变量忽略。`.env.example` 只作示例，应用不会自动读取当前目录或父目录的 `.env`，需显式设置环境变量：

```powershell
$env:CLINICAL_AGENT_APP_ENV = 'test'
$env:CLINICAL_AGENT_LOG_LEVEL = 'DEBUG'
& $projectPython -I -c "from clinical_agent.config import load_settings; print(load_settings().model_dump_json())"
```

上例返回 `{"app_env":"test","log_level":"DEBUG"}`。非法值抛出 Pydantic ValidationError，异常文本隐藏输入值；如需结构化错误，使用 errors(include_input=False)，不要原样输出默认 errors() 中的输入。CLI 将装配阶段的配置错误映射为固定安全文本。

## 结构化日志

日志必须显式配置；导入 logging_config 不创建 Settings 或配置日志。调用后使用 `clinical_agent` 命名 logger，日志输出到 stderr，每条一行 JSON，stdout 留给结果。

```python
import logging
import structlog
from clinical_agent.config import Settings
from clinical_agent.logging_config import configure_logging

configure_logging(Settings(app_env="test", log_level="INFO"))
structlog.get_logger("clinical_agent").info(
    "local_logging_ready", request_id="local-check", app_env="test"
)
logging.getLogger("clinical_agent").warning(
    "local_warning", extra={"request_id": "local-check", "error_code": "example"}
)
```

必需字段是 event、level、timestamp（UTC）；可选上下文字段仅 request_id、app_env、error_code、exception_type，且只接受字符串。UUID 请显式转字符串。其他字段/对象、原始异常消息、traceback 和 stack_info 不进入本模块 JSON 输出，不会调用被丢弃对象的自定义序列化。level/timestamp 由处理器生成，附加字段不能伪造它们。

event 和允许字段的值必须来自受控上下文，不放凭据、用户问题或文献原文；字段筛选不识别字符串内任意秘密。标准 logging 使用固定事件名及 extra，不对位置参数做文本插值。重复配置可更新级别，不叠加本模块 handler；不向 root 重复传播，也不重置其他 logger 的 handler。该策略只控制本模块的 handler，不接管外部日志或用户另加的 handler。

## 本地 CLI 与 runtime

在项目根目录按上文设置 `$projectPython` 和 uv 缓存目录后：

```powershell
& $projectPython -m uv sync --locked --group dev --extra ml --extra db --extra rag --extra api --offline
& $projectPython -I -m clinical_agent --help
$env:CLINICAL_AGENT_APP_ENV = 'test'
$env:CLINICAL_AGENT_LOG_LEVEL = 'INFO'
& $projectPython -I -m clinical_agent doctor
& '.venv/Scripts/clinical-agent.exe' doctor
```

两种入口均已在 Windows 实际运行。`doctor` 的 stdout 为一份 JSON，例如以下结构（request_id 每次生成，python_version 来自实际解释器）：

```json
{"status":"ok","scope":"local_environment","external_services_checked":false,"python_version":"3.12.16","app_env":"test","request_id":"017969be-9f9e-4a43-9963-aa577b754ee8"}
```

INFO 下 stderr 有一条 `local_check_completed` JSON 日志，与结果使用同一 request_id；WARNING 可过滤该日志。无参数、主帮助和 doctor 帮助均不装配 runtime，非法环境配置也不影响帮助。未知命令/参数返回 2；doctor 配置错误返回 2，stderr 为 `Invalid configuration.`；意外失败返回 1，输出 `Local check failed.` 和已可用的受控错误日志，不输出原始异常。当前解析器覆盖了argparse错误输出，只显示usage与固定Invalid arguments.，不回显非法参数值；仍不应通过命令参数传密钥。

`bootstrap.open_runtime()` 在进入上下文时读取一次配置、配置日志并生成 UUID；也可显式传入 Settings/request_id。Runtime 是冻结 dataclass，只有配置与关联 ID，当前没有外部连接或线程，也没有假的关闭操作。CLI 支持注入上下文工厂，在上下文内构造 DoctorReport，成功退出后才发布结果；Fake 生命周期测试不证明未来数据库或 SDK 的关闭行为。

## 干净环境与 wheel 复现

下述25/8包、六模块及59项测试是P0-07e历史记录。复用这些命令验证当前仓库时，全量测试需安装ml/db/rag/api四个extras；当前wheel的模块数与依赖按现有源码/锁文件重新核对，不能套用旧计数。基础wheel环境只用于help/doctor与轻量导入，不运行全部测试。

2026-10-26 在 `.artifacts/p0-07e-20261026-01/` 新建两个环境验证成功：repro-venv 安装锁定的 25 个开发/运行包，wheel-venv 仅安装 8 个运行依赖及项目 wheel。两者不继承系统 site-packages；wheel 的六个模块均从该环境的 site-packages 导入，不依赖源码路径。使用本地缓存完成离线验证，未验证无缓存下载或 Linux 安装。

以下在项目根运行；每一步退出码非 0 时应停止排查。使用新目录，不删除或覆盖旧环境：

```powershell
$verificationRoot = Join-Path (Get-Location) '.artifacts/p0-07e-local'
if (Test-Path -LiteralPath $verificationRoot) { throw 'Choose a new verification directory.' }
New-Item -ItemType Directory -Path $verificationRoot | Out-Null
$basePython = Join-Path (Get-Location) '.tools/p117-python31216/python/python.exe'
$savedProjectEnvironment = $env:UV_PROJECT_ENVIRONMENT
try {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $verificationRoot 'repro-venv'
    & $projectPython -m uv sync --locked --group dev --extra ml --extra db --extra rag --extra api --offline --python $basePython --no-python-downloads
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $savedProjectEnvironment
}
$reproPython = Join-Path $verificationRoot 'repro-venv/Scripts/python.exe'
& $projectPython -m uv pip check --python $reproPython
& $reproPython -I -m pytest tests/unit tests/integration -q --basetemp="$verificationRoot/pytest-repro"
& $reproPython -m ruff check src tests
& $reproPython -m ruff format --check src tests
& $reproPython -m mypy src

& $projectPython -m uv build --wheel --no-sources --offline --python $basePython --no-python-downloads --out-dir "$verificationRoot/wheel-build"
& $projectPython -m uv export --locked --no-dev --no-emit-project --format requirements-txt --output-file "$verificationRoot/runtime-requirements.txt" --offline --quiet
& $projectPython -m uv venv "$verificationRoot/wheel-venv" --python $basePython --no-python-downloads --offline
$wheelPython = Join-Path $verificationRoot 'wheel-venv/Scripts/python.exe'
$wheel = Join-Path $verificationRoot 'wheel-build/clinical_literature_agent-0.1.0-py3-none-any.whl'
& $projectPython -m uv pip install --python $wheelPython --require-hashes -r "$verificationRoot/runtime-requirements.txt" --offline
& $projectPython -m uv pip install --python $wheelPython --no-deps $wheel --offline
& $projectPython -m uv pip check --python $wheelPython
Get-FileHash $wheel -Algorithm SHA256
```

随后用绝对路径从临时目录验证两个入口：

```powershell
$smokeCwd = Join-Path $verificationRoot 'smoke-cwd'
New-Item -ItemType Directory -Path $smokeCwd | Out-Null
$savedAppEnv = $env:CLINICAL_AGENT_APP_ENV
$savedLogLevel = $env:CLINICAL_AGENT_LOG_LEVEL
Push-Location $smokeCwd
try {
    $env:CLINICAL_AGENT_APP_ENV = 'test'
    $env:CLINICAL_AGENT_LOG_LEVEL = 'INFO'
    & $wheelPython -I -m clinical_agent --help
    & $wheelPython -I -m clinical_agent doctor
    & "$verificationRoot/wheel-venv/Scripts/clinical-agent.exe" --help
    & "$verificationRoot/wheel-venv/Scripts/clinical-agent.exe" doctor
} finally {
    Pop-Location
    $env:CLINICAL_AGENT_APP_ENV = $savedAppEnv
    $env:CLINICAL_AGENT_LOG_LEVEL = $savedLogLevel
}
```

比较稳定报告字段及每次调用的日志关联 ID；UUID/时间每次变化。安装来源和完整检查结果见 [开发记录](../development-plan.md)。PYTEST 注入变量仍按前文清理/恢复；VIRTUAL_ENV 指向原环境时 uv 会提示不匹配并忽略，实际安装目标以 UV_PROJECT_ENVIRONMENT/--python 为准，无需激活新环境。

P0-07e 历史 wheel SHA256 为 `dea64436482b1700a1be54e38c6129e9da2f8ee7b9d11b44f882d88d55fd4a92`。当时内容检查为六个源码模块和五个 dist-info 文件，源码字节及 RECORD 哈希一致，没有打入缓存、环境或密钥；该产物不包含后续 Phase 1 代码/依赖。wheel 带构建时间等元数据，不承诺重复构建得到同一 SHA256，也不将平台标签当作 Linux 运行证据。

## 文献与证据 DTO（P1-01）

纯领域模型位于 [domain/models.py](../../src/clinical_agent/domain/models.py)，包含 PublicationDate、SourceMetadata、EvidenceLocation、EmbeddingInfo、EvidenceChunk、LiteratureDocument。未知元数据保持 null/[]，日期保留 raw/precision，不补造 DOI/PMID；UUID、时间、来源快照 hash 必须由调用方提供。

```powershell
& $projectPython -I -c "from clinical_agent.domain.models import PublicationDate; print(PublicationDate(precision='year', raw='2020', year=2020).model_dump_json())"
```

上例返回年份及 month/day=null。证据文本不去空白，定位为 Unicode 码点右开区间；文献校验片段归属、来源快照一致性和摘要切片。PDF 页号/区间只做结构验证，真实页边界和切片留给解析/分块任务。摘要范围不能填入全文，未分块/未编码状态显式允许，但不表示可检索。

DTO 不读取文件、不联网，不验证 URL 可达性、DOI/PMID 的真实登记或医学结论。source_uri 是内部追溯字段，不应原样公开；结构化错误使用 errors(include_input=False)，不要直接输出完整原始错误。细节见 [P1-01 SPEC](../specs/tasks/p1-01-literature-contracts.md)。

## PDF 文本层解析（P1-02）

[adapters/pdf.py](../../src/clinical_agent/adapters/pdf.py) 提供 `parse_pdf(path, *, allowed_root, document_id, ingestion_time, metadata=None, limits=None)`，返回 ParsedPdf：文献、原页号来源单元、规范化版本和解析器版本。新增的 pypdf 6.21.2 已精确锁定；P1-02验收时的开发环境共26个包；当前安装范围见顶部安装命令。

调用方明确传入允许根目录、UUID 和带时区时间。解析只读一次有界字节快照，hash 和 Reader 用同一份 bytes；混合空白页保留原页号，正文以两个 LF 拼接，始终标记 extracted_text。标题按人工值→PDF /Title→文件名回退；创建时间不当成出版日期，作者字段不猜拆，DOI/PMID 等未知值不从正文补造。`ParsedPdf.validate_chunk()` 可验证指定页内区间与证据文本一致。

默认限制为文件 20 MiB、200 页、每页解码内容流 10 MiB、聚合文本 1,000,000 字符（含页间分隔符）、协作计时 30 秒。同步解码/提取不能被强制中断，流大小在解码后检查；这些不是硬内存/时间沙箱。原路径不是持久化快照，后续入库仍需保存受控文件和来源单元。

加密、损坏、零页及整份无文本的文件明确拒绝；空白与扫描/图像-only 可能都无文本，不声称已区分扫描类型或做了 OCR。应用不提供密码/调用 decrypt；库初始化可能尝试空密码，识别到加密后仍拒绝。不支持的加密算法/依赖导致初始化失败时按 pdf_invalid 拒绝。本轮真实加密样例为 pypdf 默认 RC4，不代表所有 AES 变体已验证。

用真实合成 PDF 验证（不读取你的文献文件）：

```powershell
& $projectPython -I -m pytest tests/unit/test_pdf_contracts.py tests/integration/test_pdf.py -q
```

源码/API、错误码、预算和测试边界见 [P1-02 SPEC](../specs/tasks/p1-02-pdf-parsing.md)。P1-02本身不提供CLI；当前已有P1-10的PDF/XML导入CLI和P1-11的API，见顶部用法链接。OCR、复杂版面或真实论文效果评估仍未完成。

## 本地 PubMed XML（P1-03）

[adapters/pubmed_xml.py](../../src/clinical_agent/adapters/pubmed_xml.py) 提供 `parse_pubmed_xml(path, *, allowed_root, ingestion_time, document_id_factory, limits=None)`。只接受本地未压缩 PubmedArticleSet，由调用方显式提供允许目录、带时区时间和纯 PMID→UUID 工厂。返回批次中每个顶层条目的 parsed/rejected 结果，不将解析说成已入库。

元数据包含 PMID、标题、个人/团体署名、期刊、显式 DOI 与精度保留的期刊日期；缺 PMID/标题/摘要或冲突元数据按条拒绝。创建/历史日期不补出版日期，MedlineDate/季节/未识别月份保留 raw/unknown；未知 DOI 等保持 null。只获取摘要，source_url=null，不凭 PMID 构造已访问链接，也不验证真实登记。

混合标签按文本顺序提取，空白折叠为单空格，版本 pubmed-xml-text-v1；章节标签/类别单独保留，正文以两个 LF 拼接，偏移相对整段摘要。`ParsedPubmedArticle.validate_chunk()` 核验片段属于同一来源且位于单节内；不会把摘要标为全文。

安全解析使用精确锁定defusedxml 0.7.1；P1-03验收时开发环境共27包，属于历史计数。正常 DOCTYPE 可出现但不加载外部 DTD；自定义/外部实体明确拒绝。默认限制：10 MiB、1000 顶层条目、深度 64、100000 节点、每篇摘要 1000000 字符、协作计时 30 秒。语法/安全/全局预算失败整体抛错，不返回前半批次；逐篇文本预算或映射错误明确 rejected。这不是进程级硬时间/内存沙箱或完整 DTD 验证。

```powershell
& $projectPython -I -m pytest tests/unit/test_pubmed_contracts.py tests/integration/test_pubmed_xml.py -q
```

上述使用真实安全库与合成 XML，不请求 PubMed API。[详细 SPEC](../specs/tasks/p1-03-pubmed-xml.md) 记录字段路径、安全设置、限制与错误码。defusedxml 稳定版发行较久，选择与维护风险见 [技术选型](../tech-stack.md)，不将版本声明代替当前环境实测。

## 历次测试证据与范围

本节计数对应各任务验收时点，不是当前pytest总数。P1-13最近默认回归为854 passed、92 deselected；最新结果及待验收项统一见[开发计划](../development-plan.md#phase-1-任务进度)。

2026-10-26 实际执行：目标包缺失时 **1 failed**，原因 ModuleNotFoundError: clinical_agent；只添加包初始化文件并安装后，同一测试命令 **1 passed**。锁文件检查、25 个已安装包的一致性检查、Ruff、格式检查及 mypy 通过。原始 RED/GREEN 输出保存在本机忽略目录 .artifacts/；可审阅摘要在 [开发计划](../development-plan.md)。

P0-07b 实际执行：配置模块缺失时 **17 failed**；最小实现后目标测试 **17 passed**，加上包与配置模块隔离导入的全量回归 **19 passed**。首次 GREEN 尝试有一条测试误把 information 中的 info 子串视作泄漏，已修正完整值匹配并保留全部用例及输入标记/秘密哨兵断言，过程留档。Ruff、格式检查和 mypy 通过，依赖与 uv.lock 未变。

P0-07c 实际执行：日志模块缺失时 **3 failed**；最小实现后目标测试 **3 passed**，当前全量回归 **23 passed**。测试使用真实 structlog/标准 logging，覆盖 JSON/UTC/stderr、已有 logger 重配置、敏感字段/异常/对象处理及无导入副作用；没有验证医学业务或外部服务。测试列表经 Ruff 仅调整排版，完整过程见开发计划。

P0-07d 实际执行：runtime 缺失时 **2 failed → 2 passed**；随后 CLI 缺失时 **31 failed、2 passed → 33 passed**。扩展六模块导入检查及错误日志断言后，全量回归 **59 passed**，Ruff/格式/mypy、离线锁检查及已安装依赖检查通过。仅新增项目脚本声明并离线重装根包，无新增依赖，uv.lock 哈希保持不变。

P0-07e 实际执行：原环境 **59 passed / 23.03s**，新建开发环境 **59 passed / 27.17s**；两套环境 Ruff/格式/mypy 全通过。独立 wheel 环境完成安装来源检查和 12 项 CLI 冒烟，三套环境 doctor 稳定字段一致。父进程分支覆盖率汇总 78%（语句 81%、分支 50%），未采集的隔离子进程不计入；日志主体和模块入口已由子进程测试验证，不能将该比例解释为全部运行路径的完整覆盖。未为凑覆盖率增加测试或修改源码。

P0-08 实际复验：**59 passed / 21.77s**；四段 Python、三段 PowerShell 教学示例全部执行通过；项目/既有 wheel 的 12 项 CLI 冒烟与来源检查通过。学习六文件和独立验收清单齐备，Phase 0 按 Windows 本地骨架范围验收完成。

未验证 Linux、无缓存下载、数据库、Redis、模型、LLM、飞书或 PubMed；Phase 0 完成不表示医学业务或部署到其他平台已完成。

P1-01：首轮 **93 failed → 93 passed**；时间 epoch 与错误输入回显边界分别补真实失败测试后修复，目标最终 **97 passed**。当前完整回归 **158 passed**，Ruff/格式/mypy/离线锁检查通过，未新增依赖。旧 Phase 0 wheel 不包含新增 domain 模块，本任务未重建新 wheel 或验证真实文献服务。

P1-02：首轮 **41 failed → 41 passed**；补规范化与分隔符预算的真实 RED/GREEN 后，目标 **44 passed**，当前全量 **204 passed**。Ruff/格式/mypy、锁与 26 包一致性检查通过，详情见 [开发记录](../development-plan.md)。真实 pypdf 合成 PDF、局部故障替身和 fake clock 分开记录；新增依赖仅 pypdf，未升级原有包、未重建 Phase 1 wheel。

P1-03：首轮 **68 failed → 68 passed**；补齐章节空属性、未知精度中的非法已知组件，以及 UTF-16/读取失败验证后，目标 **74 passed**，全量 **279 passed**。Ruff/格式/mypy、锁与 27 包一致性检查通过；详情见开发计划。只新增 defusedxml，未升级既有包，未重建 Phase 1 wheel。各任务上文计数为其验收时点，不代表未来新增代码均被旧轮子验证。

## 文档

- [总体 SPEC](../specs/00-project-overview.md)
- [Phase 0 详细任务](../specs/tasks/phase0-implementation.md)
- [架构设计](../architecture.md)
- [技术选型](../tech-stack.md)
- [测试策略](../testing-strategy.md)
- [开发计划与执行记录](../development-plan.md)
- [Phase 0 学习导航](../learning/phase-00/README.md)
- [Phase 0 独立验收报告](../phase0-acceptance.md)

P1-04：来源分块/长度契约完成，38 目标用例、318 全量回归；实际 tokenizer 由 P1-05 继续验收。

P1-05：本地 Embedding 完成，61 个单元目标用例、381 个默认回归通过（1 个真实模型测试默认排除）；真实固定 E5 CPU 测试另行 1 passed，验证 512/513 token 门禁、768 维归一化向量和离线来源分块。ML 为可选 extra，不影响基础 doctor。详见 [本地模型操作](../local-embedding.md)、[任务 SPEC](../specs/tasks/p1-05-local-embedding.md) 与开发计划。模型医学效果、数据库和 RAG 尚未验收。

P1-06：PostgreSQL模型/迁移完成，13目标单元、47真实数据库测试通过；默认完整回归397 passed、48 deselected。PostgreSQL16.15/vector0.8.7实测升降级、持久化、约束、向量距离、回滚及并发唯一性；db为可选extra，基础doctor不受影响。[数据库说明](../postgres.md)、[任务SPEC](../specs/tasks/p1-06-postgres-schema.md)。尚无导入服务，未将数据库约束通过等同完整业务幂等。

P1-07：离线入库服务完成，43目标用例、62数据库测试、1项真实E5+PG链路通过；默认445 passed、64 deselected。支持受控快照、完整映射、单文档事务、并发重复及非覆盖分类；legacy记录不伪造版本。详见 [入库说明](../offline-ingestion.md)、[SPEC](../specs/tasks/p1-07-offline-ingestion.md)、开发计划。

P1-08：基础向量检索完成，55目标单元、74真实数据库回归和1项真实E5+PG检索链路通过；默认503 passed、77 deselected。支持完整模型身份门禁、阈值/来源过滤、稳定排序、只读一致快照及可回建证据DTO。详见 [检索说明](../vector-retrieval.md)、[SPEC](../specs/tasks/p1-08-vector-retrieval.md)、开发计划。未新增依赖/迁移。

P1-09：真实LangGraph编排、DeepSeek JSON生成和基础引用门禁完成；74目标用例、581默认回归通过（78项数据库/外部测试默认排除），另1项真实DeepSeek合成证据冒烟通过。请求deepseek-chat实际响应deepseek-flash；来源及定位仅从可信命中构造。详见 [RAG说明](../basic-rag.md)、[任务SPEC](../specs/tasks/p1-09-basic-rag.md) 和开发计划。无医学专家评审或E5/PG/LLM整链路验收。

P1-10：新增ingest/ask命令，复用现有应用服务及显式资源装配，支持JSON输出、受控退出码和错误脱敏。43目标测试、625默认回归及1项实际E5/PG集成通过；LLM为明确HTTP替身，本轮未验证真实付费LLM。[使用说明](../cli.md)、[任务SPEC](../specs/tasks/p1-10-cli-entrypoints.md)。

P1-11：新增FastAPI工厂、离线导入／问答及健康接口，生命周期复用模型/engine/HTTP资源，使用有界线程池接纳和统一脱敏错误。60目标、687默认回归及1项真实Uvicorn TCP/E5/PG集成通过；LLM仍为明确HTTP替身。详见 [API说明](../api.md)、[任务SPEC](../specs/tasks/p1-11-fastapi.md) 与开发记录。

P1-12：已完成消息DTO、解码事件过滤、群聊@校验及去重身份选择；88项事件用例、34项隔离导入、777项默认回归通过。[契约说明](../feishu-events.md)、[任务SPEC](../specs/tasks/p1-12-feishu-events.md)。accepted仅为过滤通过；Redis去重由P1-13单独实现，机器人运行时尚未实现。

P1-13：已完成Redis原子占位、owner校验、有限续租、完成/释放和故障隔离；76单元+12真实Redis测试、854默认回归通过。[说明](../feishu-dedup.md)、[SPEC](../specs/tasks/p1-13-redis-dedup.md)。

**P1-16：官方SDK长连接、装配与Compose入口** 已按任务范围验收，证据以[开发进度](../development-plan.md#phase-1-任务进度)为准。当前验收任务 **P1-17：MVP阶段验收与学习文档**（技术验收与教材已交付，医学人工审查待完成；见[阶段报告](../phase1-acceptance.md)与[学习导航](../learning/phase-01/README.md)）；完整剩余任务见[开发计划](../development-plan.md#phase-1-任务进度)。`P1-xx`是开发任务，`P1-Txx`是阶段验收场景，两者不一一对应；见[MVP映射](../specs/01-mvp.md#验收场景与开发任务的对应关系)。Phase1尚未验收。


## 科研选题调研报告（Phase 7 核心链路）

`clinical-agent ask --report --question "科研想法" --model-dir <已有模型目录>` 输出结构化报告和Markdown；`--format markdown` 仅输出Markdown。API使用 `POST /v1/reports`，飞书使用 `/report 科研想法`。沿用现有数据库、E5与通用模型配置，无新增迁移或依赖。

报告包含已有研究、方法/技术路线对比、与想法的相似性、候选缺口和待调查方向，并保留来源、支持度、事实/推断/假设及核验状态。无命中不代表创新，verified也不证明医学正确。当前真实模型/真实依赖整链路与医学人工验收仍待完成，详见[Phase7验收记录](../phase7-acceptance.md)、[学习入口](../learning/phase-07/README.md)。

## Phase 9 离线评价（2026-10-28）

入口：`.venv/Scripts/python.exe -I scripts/evaluate_phase9.py --output evaluation/results/my-phase9 --performance`。
可选 `--baseline <独立的旧results.json>`；相同数据/标签/配置/门槛hash才比较，回归容忍度冻结在thresholds.json。默认合成公式集故意含失败，退出1，不能当医疗质量基线。零分母/缺标注返回null，未执行真实范围保留inconclusive。详情见[阶段报告](../phase9-acceptance.md)与[学习导航](../learning/phase-09/README.md)。
