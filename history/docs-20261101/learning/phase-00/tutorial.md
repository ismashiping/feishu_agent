# 从零理解 Phase 0 工程骨架

历史范围：本文记录Phase 0对应任务/教材时点，旧测试数、模块数及“下一任务”不表示当前状态。当前进度见[任务表](../../development-plan.md#phase-1-任务进度)；在当前仓库跑全量测试须安装ml/db/rag/api四个extras，基础doctor示例仍无需这些业务依赖。

## 1. 是什么：一条命令背后的几层责任

执行 `python -m clinical_agent doctor` 时，程序读取两个配置值、装配本地运行上下文，最后输出一份 JSON。JSON 是有固定键值结构的文本，方便另一个程序读取。这个 Demo 不会搜索医学证据，也不会连接数据库。

先认识几个词：解释器是执行 Python 的程序；虚拟环境是解释器对应的一套独立安装目录；模块是可导入的 Python 文件；发行包是安装工具处理的项目单位。这里发行名是 clinical-literature-agent，导入名是 clinical_agent，终端命令是 clinical-agent，它们各有用途。

## 2. 为什么：把“我电脑上能跑”变成可核验的工程

如果读取环境变量散落在每个函数中，同一次调用可能用到不同设置；如果 import 就建连接，连 help 和测试都需要服务；如果日志与结果混在一个输出流中，JSON 消费者会解析失败；如果只从仓库根运行，漏打包文件可能被源码目录掩盖。

本项目因此先固定环境和包安装，再提供显式配置、日志和装配入口。各层短小、可替换，测试能直接注入 Settings 或上下文工厂，不需要启动未来的数据库和模型。

## 3. 原理：解释器、src、锁文件与 wheel

`.venv/Scripts/python.exe` 选择项目环境，不依赖终端当前激活哪一个 Python。`src/clinical_agent/` 放真实包；安装后，Python 才能从临时工作目录找到它。`-I` 启用隔离模式，避免用户 site/PYTHONPATH 等干扰；它不替代虚拟环境，也不禁止网络。

pyproject.toml 声明直接依赖与脚本。uv.lock 固定解析得到的传递版本和发行哈希。`uv sync --locked` 要求声明与锁一致；`--offline` 禁止 uv 联网，所需缓存不存在就应停止排查，不能默默替换版本。

开发安装是 editable：导入仍指向项目 src，便于修改。wheel 是构建后的分发物：独立安装时应从目标环境 site-packages 导入。P0-07e 新建开发环境装了 25 个包，独立 wheel 环境只有 8 个运行依赖加根包，共 9 个；构建所用 setuptools 不是应用运行依赖。

## 4. 原理：配置只在需要时读取

[Settings](../../../src/clinical_agent/config.py) 继承 Pydantic Settings，两个 Literal 字段限制可选字符串。变量名前缀为 CLINICAL_AGENT_；变量名不区分大小写，值区分大小写。load_settings 每次新建实例，没有全局缓存；env_file=None 表示不自动读取 .env。

优先级只需记住当前用法：直接传给 Settings 的字段覆盖对应环境变量；未显式传入的字段仍可从环境读取。显式提供给 open_runtime 的整个 Settings 实例会被直接使用，不再重新读取环境。需要隔离主机环境的教学示例应明确传入两个字段。

## 5. 最小 Python Demo

下面示例分别保存成 .artifacts 下的不同 .py 文件，从项目根使用 `& '.venv/Scripts/python.exe' -I '<示例路径>'` 运行。文件路径是读者自选的实际路径，不能把尖括号占位符直接粘贴执行。

第一个示例只有配置，不配置日志，不连接外部服务；输出两个明确字段：

```python
from clinical_agent.config import Settings

settings = Settings(app_env="test", log_level="INFO")
assert settings.model_dump() == {"app_env": "test", "log_level": "INFO"}
print(settings.model_dump_json())
```

第二个示例使用真实 runtime、真实报告构造函数与真实日志。它与 CLI 的边界相同：在 with 内构造报告，成功离开后再输出。固定 UUID 便于核对 stdout 与 stderr，生产调用默认生成新的 UUID：

```python
import logging
from uuid import UUID

from clinical_agent.bootstrap import open_runtime
from clinical_agent.cli import build_doctor_report
from clinical_agent.config import Settings

request_id = UUID("00000000-0000-4000-8000-000000000004")
with open_runtime(Settings(app_env="test", log_level="INFO"), request_id=request_id) as runtime:
    report = build_doctor_report(runtime)
    assert report.request_id == request_id
    assert report.external_services_checked is False

logging.getLogger("clinical_agent").info(
    "learning_demo_ready", extra={"request_id": str(request_id), "app_env": "test"}
)
print(report.model_dump_json())
```

stdout 是一份 DoctorReport；stderr 是带 event、level、UTC timestamp 和同一 request_id 的一行 JSON。learning_demo_ready 是这个教学脚本的固定事件名，CLI 的实际成功事件是 local_check_completed。

第三个示例演示非法配置的处理。不要为调试打印原始输入；这里的字符串只是固定假值：

```python
from pydantic import ValidationError

from clinical_agent.config import Settings

try:
    Settings(app_env="test", log_level="DEMO_INVALID_LEVEL")
except ValidationError as exc:
    errors = exc.errors(include_input=False)
    assert any(error["loc"] == ("log_level",) for error in errors)
    assert "DEMO_INVALID_LEVEL" not in str(exc)
    print("configuration_rejected")
else:
    raise AssertionError("Invalid log level was accepted")
```

隐藏异常文本输入不等于任何错误对象都能随意序列化；默认 errors() 可能带输入，要明确 include_input=False。CLI 会使用固定错误文本，不把上述错误结构交给最终用户。

## 6. 最小 CLI Demo

在项目根运行整个块；结束会恢复原环境。帮助与 doctor 共用入口，只有 doctor 构造 runtime：

```powershell
$projectPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$savedAppEnv = $env:CLINICAL_AGENT_APP_ENV
$savedLogLevel = $env:CLINICAL_AGENT_LOG_LEVEL
try {
    $env:CLINICAL_AGENT_APP_ENV = 'test'
    $env:CLINICAL_AGENT_LOG_LEVEL = 'INFO'
    & $projectPython -I -m clinical_agent --help
    if ($LASTEXITCODE -ne 0) { throw 'Help failed.' }
    & $projectPython -I -m clinical_agent doctor
    if ($LASTEXITCODE -ne 0) { throw 'Module doctor failed.' }
    & '.venv/Scripts/clinical-agent.exe' doctor
    if ($LASTEXITCODE -ne 0) { throw 'Console doctor failed.' }
} finally {
    $env:CLINICAL_AGENT_APP_ENV = $savedAppEnv
    $env:CLINICAL_AGENT_LOG_LEVEL = $savedLogLevel
}
```

两个 doctor 的稳定字段相同：status=ok、scope=local_environment、external_services_checked=false、app_env=test、当前 Python 版本。每次 UUID/时间不同，不应对整段输出做固定字符串快照。stdout/stderr 可能交错显示，捕获时要分开读取。

## 7. 日志为什么要保守

structlog 将事件组织成字段，ProcessorFormatter 连接标准 logging，JSONRenderer 输出 JSON。我们只保留 event/level/timestamp 及 request_id、app_env、error_code、exception_type；上下文只接受字符串，额外对象、payload 和异常堆栈丢弃。

这是字段控制，不是任意文本秘密检测。event 和允许字段必须由程序控制；不能把用户问题或凭据塞进 event。标准 logging 使用固定事件名与 extra，不对位置参数做文本插值。重复配置只替换本模块拥有的 handler，项目 logger 不向 root 传播；其他自定义 handler 不在这个输出保证内。

## 8. 装配、生命周期与下一步

Runtime 是包含 Settings/request_id 的 frozen dataclass。frozen 阻止字段重新赋值，不会深度冻结内部 Settings。contextmanager 的 yield 是入口与调用方执行块之间的边界；当前没有外部资源，所以没有假 close 方法，也不会在离开 with 时卸载进程级日志配置。

下一篇 [代码解析](code-walkthrough.md) 按真实运行顺序追踪成功和失败分支，再进入 [调试](troubleshooting.md)、[修改/独立练习](exercises.md) 与 [面试表达](interview.md)。
