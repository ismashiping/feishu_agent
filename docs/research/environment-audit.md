# Phase 0 / P0-01：目录与环境检查

历史范围：本文记录Phase 0对应任务/教材时点，旧测试数、模块数及“下一任务”不表示当前状态。当前进度见[任务表](../development-plan.md#phase-1-任务进度)；在当前仓库跑全量测试须安装ml/db/rag/api四个extras，基础doctor示例仍无需这些业务依赖。

检查日期：2026-10-26（Asia/Shanghai）。状态：本任务完成，Phase 0 尚未完成。

## 范围与验收

本任务只读取项目目录、项目规则、Git 状态、指定 Python 环境及开发工具状态；记录可用性和风险。不安装依赖、不修改共享 Conda 环境、不实现业务、不启动基础设施。

验收标准：能够确认现有文件、Python 版本、依赖一致性、测试工具及 Docker 可用性，并区分实际验证与未验证内容。

## 初始目录与规则

工作目录：`E:\02_Projects\chatgpt_project\clinical_agent`。

初始文件仅有 `.git/`、`AGENTS.md.txt`、`PROJECT.md.txt`；不存在代码、测试、SPEC、依赖声明或锁文件。两份文本规则均已读取。实际文件名带 `.txt`，后续执行任务时须显式读取，不能假定工具会自动发现为 `AGENTS.md`。

Git 初始状态：`master` 分支无提交；两份文本文件未跟踪；`git remote -v` 无输出。未修改上述文件或 Git 配置。

项目规则要求每次一个当前阶段任务，先 SPEC 后 TDD；阶段完成还须有基于真实代码的学习文档。本次只完成 P0-01 环境检查，不标记整个 Phase 0 完成。

## 实际执行与结果

以下 PowerShell 命令均在项目目录执行。`$projectPython` 在下列示例中表示指定解释器路径：

```powershell
$projectPython = 'C:\Users\11091\.conda\envs\medical-agent\python.exe'
```

| 命令或检查 | 实际结果 |
| --- | --- |
| `Get-Location`、`Get-ChildItem -Force`、`rg --files --hidden -g '!.git/**'` | 确认工作目录与上述初始文件 |
| `Get-Content AGENTS.md.txt`、`Get-Content PROJECT.md.txt` | 已读取项目规则与阶段约束 |
| `git status --short --branch` | 无提交，两个文本文件未跟踪 |
| `git log -1 --oneline` | 因尚无提交而失败，符合初始状态 |
| `git remote -v` | 无输出 |
| `Test-Path` 指定解释器路径 | `True` |
| `& $projectPython --version` | Python 3.10.21 |
| `& $projectPython -m pip --version` | pip 26.2.1，来自指定环境 |
| `& $projectPython -m pip list --format=json` | 已安装大量依赖，含其他项目的 editable 安装 |
| `& $projectPython -m pip check` | `No broken requirements found.` |
| `& $projectPython -m uv --version` | uv 0.13.1 |
| `& $projectPython -m pytest --version` | pytest 9.1.1 |
| `& $projectPython -m ruff --version` | Ruff 0.16.7 |
| `& $projectPython -m mypy --version` | mypy 2.3.1 |
| `Get-Command git,uv,python,docker -ErrorAction SilentlyContinue` | Git、默认 Python、Docker 可发现；uv 无独立 PATH 命令，指定环境可用 `python -m uv` |
| `Get-Command conda -ErrorAction SilentlyContinue` | `E:\00_DevEnv\miniconda\Library\bin\conda.bat` |
| `& 'E:\00_DevEnv\miniconda\python.exe' --version` | 默认 Python 为 3.14.7，与指定环境不同 |
| `docker --version` | Docker 29.7.2 |
| `docker compose version` | Docker Compose v5.5.1 |
| `docker info --format '{{.ServerVersion}}'` | 无法连接 `docker_engine` 命名管道；未验证服务端可用性 |

Docker 命令同时报告无法读取 `C:\Users\11091\.docker\config.json`（Access is denied）。没有读取该配置内容、调整权限或尝试绕过限制。命名管道不存在可能与 Engine 未启动或当前连接配置有关，未进一步确认原因。

## 环境判断与待决事项

1. 指定环境是 Python 3.10.21，低于用户候选基线 3.11。正式选择 Python 版本前需检查依赖官方支持范围；不在本任务中升级或改造此环境。
2. 默认 Python 是 3.14.7，不能因版本较新就假定适合机器学习依赖。后续命令需显式指定解释器。
3. 指定环境包含 `customer-agent` 的 editable 安装，位置为其他项目目录。建议后续采用项目内隔离环境及锁文件，避免依赖污染；这只是建议，尚未创建环境或确定版本。
4. `pip check` 只验证已安装包声明的依赖一致性，不代表运行兼容性、官方支持或本项目依赖选型已完成。
5. 工具版本来自本机实际输出，尚未经官方文档或 PyPI 核验，不能作为项目锁定版本依据。

## 测试与未验证内容

本次没有应用实现，也没有运行 pytest 测试套件；不存在 RED/GREEN 记录。`pytest --version` 只是工具可用性检查。后续最小工程功能必须先有 SPEC 和失败测试，再实现并回归。

尚未验证：参考仓库代码、架构和提交版本；官方组件文档、PyPI 版本与维护状态；干净环境依赖解析；数据库、Redis、模型、PubMed、飞书及容器运行。未访问外部 API，未下载模型，未处理真实医学文献。

## 后续任务

P0-02：研究 `https://github.com/ismashiping/clinicalagent` 的实际代码，记录提交标识、目录、依赖、数据模型与执行流程，并分析可借鉴与不宜照搬的决策。只据可访问的源码下结论，无法访问的部分明确列为未核实。

后续依次开展技术选型、总体与阶段 SPEC、架构设计、Phase 0 测试清单和最小骨架的 TDD 验证。Phase 0 未验收前不进入 Phase 1。
