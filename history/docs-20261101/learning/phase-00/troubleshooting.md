# Phase 0 运行、调试与排错

历史范围：本文记录Phase 0对应任务/教材时点，旧测试数、模块数及“下一任务”不表示当前状态。当前进度见[任务表](../../development-plan.md#phase-1-任务进度)；在当前仓库跑全量测试须安装ml/db/rag/api四个extras，基础doctor示例仍无需这些业务依赖。

先确认自己测的是哪一个解释器、哪一种安装，再分析业务行为。当前命令只做本地检查，不需要数据库、API 密钥或模型下载。环境准备参照 [项目 README](../../../README.md)，源码调用链参照 [代码解析](code-walkthrough.md)。

## 1. 第一条诊断命令

从项目根运行，不依赖终端里 python 指向谁：

```powershell
$projectPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
& $projectPython -I -c "import sys, clinical_agent; print(sys.version.split()[0]); print(sys.prefix); print(clinical_agent.__file__)"
```

开发安装预期版本 3.12.15，prefix 为项目 .venv，包来自 src/clinical_agent。wheel 环境则要把 projectPython 换成那个环境的绝对解释器，预期模块来自它的 site-packages。完整绝对路径只供本地排错，不放入业务报告或公开日志。

## 2. 按现象定位

| 现象 | 核查与处理 |
| --- | --- |
| No module named clinical_agent | 检查解释器/prefix 和是否安装根包；使用同一环境执行 uv sync --locked --group dev。不要追加 sys.path/PYTHONPATH 来掩盖安装问题 |
| 找不到 clinical-agent 或加载旧入口 | 使用 `.venv/Scripts/clinical-agent.exe`；脚本声明变化后重新安装根包，核对入口元数据与包来源 |
| `.env` 写了值却不生效 | 当前 env_file=None，示例不是自动读取配置；显式设置 CLINICAL_AGENT_APP_ENV/LOG_LEVEL。不要为调试私自改成隐式加载真实 .env |
| help 成功，doctor 配置失败 | 这是设计行为；检查合法枚举和大小写。变量名不区分大小写，但 INFO/DEBUG 等值必须大写 |
| doctor stdout 不能解析 JSON | 分开捕获 stdout/stderr；确认没有用 2>&1 将日志混入结果。当前成功结果只有一份 JSON |
| INFO 日志不见了 | 检查 LOG_LEVEL 是否 WARNING/ERROR/CRITICAL，是否调用 configure_logging，以及 logger 名是否 clinical_agent |
| 同一事件出现多次 | 检查是不是读了两次命令输出，或用户增加了其他 handler；本模块只替换自己的 handler，不接管其他输出 |
| token/payload 或异常堆栈不显示 | 这是字段控制契约；使用固定 error_code 与 exception_type 诊断，不解除筛选去打印凭据或完整用户文本 |
| 错误对象 errors() 带输入 | 结构化读取明确 include_input=False；用户输出仍用固定安全文本，不原样打印 ValidationError |
| UV_PROJECT_ENVIRONMENT 与 VIRTUAL_ENV 不一致 | uv 会说明忽略哪个；显式使用目标环境/--python，并用 sys.prefix 证明。不要加 --active 随意改装主机环境 |
| --offline 缓存缺失 | 属于环境前置失败；检查原锁/缓存，再按权限联网准备同一版本。不能当作功能 RED 或默默升级/降级 |
| 构建提示缓存可能进包 | 检查本次 wheel zip 的文件清单；P0-07e 实际 wheel 只有六模块和五个 dist-info。不能仅凭警告或文件名断定包内容 |
| wheel 命令可以跑，但来自 src | 检查是否装成 editable、是否用了错误解释器/注入了源码路径；从临时 cwd 使用 -I 并查看模块来源 |
| 子进程 10 秒超时 | 保留命令/退出状态，检查本机资源和环境；不无限延长超时来掩盖挂起，也不将此当正式性能测试 |

## 3. 只重跑相关测试

从项目根运行下面整个块。先保存并清理 pytest 启动注入变量，结束恢复，避免主机插件/参数改变结果。这里仅执行已有目标，不构造新的 TDD 红灯：

```powershell
$projectPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$savedOptions = $env:PYTEST_ADDOPTS
$savedPlugins = $env:PYTEST_PLUGINS
Remove-Item Env:PYTEST_ADDOPTS,Env:PYTEST_PLUGINS -ErrorAction SilentlyContinue
try {
    & $projectPython -I -m pytest 'tests/unit/test_bootstrap.py::test_cli_runtime_factory_lifecycle[exit_validation]' -q
    if ($LASTEXITCODE -ne 0) { throw 'Lifecycle check failed.' }
    & $projectPython -I -m pytest tests/unit/test_config.py -q
    if ($LASTEXITCODE -ne 0) { throw 'Configuration check failed.' }
} finally {
    $env:PYTEST_ADDOPTS = $savedOptions
    $env:PYTEST_PLUGINS = $savedPlugins
}
```

配置目标当前为 17 个参数化场景，生命周期节点为 1 个。完整回归请按 [测试策略](../../testing-strategy.md) 执行 unit/integration，再跑 Ruff/格式/mypy；不要把一个节点通过说成全项目通过。pytest 的 basetemp 若显式指定，只能指向项目专用测试目录，它会清理自己的临时产物。

## 4. 在哪里设置断点

按顺序看 cli.main 的 parse_args 返回处、open_runtime 的 load_settings/configure_logging/yield、build_doctor_report、with 退出后的日志/print。坏配置通常到不了 yield；body/退出错误已进入 runtime。先看异常发生阶段，再看类型，不要把所有 ValidationError 当配置问题。

调试器可能改变导入/环境，最终仍用未注入调试器的命令复验。不要通过打印整份 os.environ、问题或文献正文来定位问题。Logger 缺字段时确认值是否为允许的字符串，UUID 在日志上下文里需显式 str。

## 5. 失败测试不一定是产品失败

历史上配置测试曾用子串 info 检查输入泄漏，误匹配 Pydantic 帮助词 information；已更正为完整 token，并保留所有非法值与秘密哨兵断言。正确做法是核对失败证据与 SPEC，单列测试假阳性修正；不是删用例或放宽产品规则。

开发包路径断言来自 src，是测试设计的一部分；wheel 来源检查则来自 site-packages，二者目标不同。覆盖率显示日志低或模块入口为零，先看有没有采集子进程；当前报告明确没有，不能据此改掉隔离测试。

## 6. 验证边界与求助材料

记录命令、解释器版本、失败阶段、退出码、最小假数据和安全错误摘要；不要复制真实凭据。P0-07e 的完整产物/哈希与 P0-08 复验摘要见 [阶段验收报告](../../phase0-acceptance.md) 和 [开发记录](../../development-plan.md)。

Linux、无缓存下载、sdist、真实数据库/Redis/模型/LLM/飞书/PubMed、医学正确性和性能尚未由 Phase 0 验证。若问题属于这些能力，先定位所属阶段与 SPEC，不能用 doctor 的 status=ok 作为它们可用的证据。
