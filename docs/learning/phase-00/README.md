# Phase 0 学习导航

本组教材以 Phase 0 骨架快照讲解；后续 domain 模块和当前任务状态见 [开发计划](../../development-plan.md)，不改写本阶段历史测试与 wheel 计数。

本阶段学习如何让一个 Python 项目能安装、配置、运行、测试和解释。当前真实产品只有本地环境检查 CLI；尚未实现文献导入、RAG、数据库、模型、API 或飞书。

前置知识：会运行 Python 文件，知道函数、字典、异常的基本写法即可。环境为 Windows x64、项目 Python 3.12.15、uv 0.13.5；安装与新环境复现先看 [项目 README](../../../README.md)。不用激活或修改共享 Conda，也不需要服务密钥。

## 阅读与动手顺序

| 顺序 | 学习目标 | 材料与完成动作 |
| --- | --- | --- |
| 1 | 是什么、为什么需要 | [教程](tutorial.md)：解释环境、包、配置、日志、CLI 的关系 |
| 2 | 底层原理与最小 Demo | 教程的完整示例：先预测 stdout/stderr，再实际运行 |
| 3 | 真实代码与执行流程 | [代码解析](code-walkthrough.md)：顺着 doctor 调用链定位六个模块 |
| 4 | 调试与测试 | [排错手册](troubleshooting.md)：从解释器、安装来源、输出通道逐层检查 |
| 5 | 修改与独立实现 | [练习](exercises.md)：先写 SPEC/失败测试，在独立练习目录完成作业 |
| 6 | 复述取舍 | [面试表达](interview.md)：先读 30 秒回答，再回答追问 |

教程中每个 Python 代码围栏都是完整示例，可保存到项目 .artifacts/ 下的练习文件，再用项目解释器 `-I` 执行；不是让你替换 src 中的实现。PowerShell 示例约定从项目根目录运行。练习是未实施的作业，验收报告不会将其列为产品已实现功能。

## 当前可定位的真实文件

| 责任 | 文件 |
| --- | --- |
| 安装、依赖、工具和 console script 声明 | [pyproject.toml](../../../pyproject.toml) |
| 最小包与模块入口 | [__init__.py](../../../src/clinical_agent/__init__.py)、[__main__.py](../../../src/clinical_agent/__main__.py) |
| 两字段配置 | [config.py](../../../src/clinical_agent/config.py) |
| JSON 日志与字段控制 | [logging_config.py](../../../src/clinical_agent/logging_config.py) |
| 显式装配与上下文 | [bootstrap.py](../../../src/clinical_agent/bootstrap.py) |
| 解析参数、构造报告、处理退出码 | [cli.py](../../../src/clinical_agent/cli.py) |

## 学完应能证明什么

你能解释 help 为什么不读取坏配置，能从 doctor 的 request_id 找到同一次调用的日志，能区分配置失败与执行失败，能用测试证明上下文退出后才输出成功结果，也能说明为何 wheel 安装检查必须离开源码工作目录。

历史功能 TDD 记录见 [开发计划](../../development-plan.md)；当前阶段结论与 P0-T01–07 映射见 [验收报告](../../phase0-acceptance.md)。P0-07e 已验证原/新开发环境各 59 个测试、wheel 独立安装和 12 项 CLI 冒烟；P0-08 的最新复验结果以报告为准。

验收只覆盖 Windows 本地骨架和缓存离线安装。Linux、无缓存下载及真实医学服务仍需后续验证；父进程覆盖率没有包含隔离子进程。Python 3.12.16 构建升级待核查的背景见 [任务 SPEC](../../specs/tasks/phase0-implementation.md)，启用外部业务/部署前须处理，不能凭本阶段推导部署能力。

下一开发任务为 P1-01“文献与证据 DTO、来源和定位契约”，需要用户另行指定后细化 SPEC。
