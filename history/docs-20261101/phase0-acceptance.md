# Phase 0 阶段验收报告

历史范围：本文记录Phase 0对应任务/教材时点，旧测试数、模块数及“下一任务”不表示当前状态。当前进度见[任务表](development-plan.md#phase-1-任务进度)；在当前仓库跑全量测试须安装ml/db/rag/api四个extras，基础doctor示例仍无需这些业务依赖。

日期：2026-10-26（Asia/Shanghai）；任务：P0-08；结论：**Phase 0 验收通过，范围为 Windows 本地工程骨架、学习材料与已记录的缓存离线验证。尚未进入 Phase 1。**

本报告保留 P0-08 验收时点的状态/计数；后续 Phase 1 进展以 [开发计划](development-plan.md) 为准，不将旧 wheel/覆盖率证据作为新增代码的验证结果。

依据：[总体 SPEC](specs/00-project-overview.md)、[工程任务 SPEC](specs/tasks/phase0-implementation.md)、[P0-08 验收清单](specs/tasks/phase0-acceptance.md)。详细历史过程见 [开发计划](development-plan.md)，学习材料见 [学习导航](learning/phase-00/README.md)。

独立验收按撰写前冻结的 P0-A01–06 清单重新执行，由本次执行者完成。历史功能 RED/GREEN、本次回归、文档示例和静态核查分别记录，不互相替代。

## 1. 实际交付与架构摘要

当前是一个 Python 发行包，只有六个源模块：最小包 __init__、模块入口 __main__、显式配置 config、日志 logging_config、运行装配 bootstrap 和 CLI。两个入口复用 main，通过 open_runtime 获取 Settings/request_id，在上下文退出成功后发布 DoctorReport。

依赖为 Pydantic 2.14.1、pydantic-settings 2.16.1、structlog 26.1.0；标准 argparse/contextlib/dataclass 承担命令、上下文和简单数据载体。正式 uv.lock 与精确构建依赖 setuptools 83.0.0 已验证，不引入未使用的业务框架。推荐未来模块边界和医学数据流仍见 [架构设计](architecture.md)、[技术选型](tech-stack.md)，不是当前已实现服务。

总体和 Phase 1–9 SPEC、参考仓库固定版本分析、技术选型、测试策略、开发记录均已交付。学习材料包含：

- [README：学习导航](learning/phase-00/README.md)
- [tutorial：原理与可运行 Demo](learning/phase-00/tutorial.md)
- [code-walkthrough：真实调用顺序与流程图](learning/phase-00/code-walkthrough.md)
- [exercises：修改练习与独立实现](learning/phase-00/exercises.md)
- [interview：面试题与 30 秒口述](learning/phase-00/interview.md)
- [troubleshooting：运行、调试与排错](learning/phase-00/troubleshooting.md)

## 2. 工程验收矩阵

| ID | 验收要求 | 实际证据 | 结论 |
| --- | --- | --- | --- |
| P0-T01 | 六模块静默导入，无服务/配置构造/线程/日志副作用 | test_package 的六个隔离子进程场景；本次完整回归 | 通过 |
| P0-T02 | 默认配置、环境覆盖、非法值/.env | test_config 的 17 个参数化场景；教程配置示例 | 通过 |
| P0-T03 | JSON/UTC/stderr、级别/重复配置、敏感字段 | test_logging_config 的真实双路径日志测试；真实 runtime 示例 | 通过 |
| P0-T04 | 双入口 help/doctor、安全错误/退出码 | test_cli 的 24 场景；本次项目/wheel 双入口 12 项冒烟 | 通过 |
| P0-T05 | 显式装配、关联 ID、上下文退出与错误阶段 | test_bootstrap 的 2 装配 + 7 生命周期场景；固定 ID/Fake 工厂教学示例 | 通过 |
| P0-T06 | 锁定新环境与 wheel 独立安装 | P0-07e 原/新开发环境各 59 passed、wheel 九包来源/哈希检查；本次复核历史产物与重新运行 | 通过（Windows、本地缓存） |
| P0-T07 | lint/格式/严格类型 | 本次 Ruff 全通过、11 文件格式通过、mypy 六源文件无错误 | 通过 |

P0-07a–d 的十份 RED/GREEN 日志已检查存在和结果标记；P0-07b 的一次测试假阳性修正单独留档。P0-07e/P0-08 无新产品功能，没有制造新 RED 或将环境准备失败称为 RED。

## 3. 学习与独立验收矩阵

| ID | 结果与证据 |
| --- | --- |
| P0-A01 | 六份文档齐全，导航映射完整学习顺序，源码/测试/既有 SPEC 均有链接 |
| P0-A02 | 抽取全部 4 段 Python、3 段 PowerShell 围栏，真实执行均退出 0；12 项项目/wheel CLI 冒烟通过，doctor 稳定字段相同 |
| P0-A03 | 对照六模块审阅调用链和 Mermaid：解析在装配前、yield 交接、body/退出验证错误返回 1、成功退出后输出；修改与独立练习均有 SPEC/TDD/验收要求，未实施为产品功能 |
| P0-A04 | 本次 59 passed，无 skip/xfail；Ruff、格式、mypy、离线锁和安装一致性通过 |
| P0-A05 | 十份历史 RED/GREEN、P0-07e 双环境日志/wheel 证据复核；本次基线 16 文件哈希不变，wheel 哈希与源码载荷一致，安装来源为 site-packages |
| P0-A06 | 本报告/开发计划记录范围、取舍、新知识与剩余限制；下一步只规划 P1-01 |

## 4. 本次实际命令与结果

证据目录：项目 `.artifacts/p0-08-20261026-01/`。详细完整参数见开发记录；所有 Python 命令使用项目 .venv/Scripts/python.exe。

| 检查 | 结果 |
| --- | --- |
| `-I -m pytest tests/unit tests/integration --cov=clinical_agent --cov-branch --cov-report=term-missing`，输出/缓存指定本次目录 | 2026-10-26 22:24:57 +08:00 启动；退出 0，59 passed / 21.77s |
| `-m ruff check src tests` / `-m ruff format --check src tests` | All checks passed / 11 files already formatted |
| `-m mypy src --cache-dir <本次目录/mypy-cache>` | Success: no issues found in 6 source files |
| `-m uv lock --check --offline` / `-m uv pip check --python <项目解释器>` | 25 个包解析/安装一致性检查通过 |
| `-I <本次目录/verify-learning.py>` | 四段 Python、三段 PowerShell、12 项 CLI、历史证据及文件/产物完整性通过 |
| 最终文档核查 | 27 份 Markdown、144 个本地链接/锚点与围栏通过；14 份本次文档空白诊断为 0 |

本次覆盖率与 P0-07e 一致：父进程汇总 78%（语句 81%、分支 50%），不含未采集的隔离子进程。日志主体/模块入口已有子进程行为断言，不能由父进程比例推导所有路径完整覆盖。教程 PowerShell 的 1 节点 + 17 配置场景复跑仅作为文档示例验证，不算新增 18 个测试。

正式锁 SHA256：`0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8`。

P0-07e 既有 wheel SHA256：`dea64436482b1700a1be54e38c6129e9da2f8ee7b9d11b44f882d88d55fd4a92`。本次复验该产物，没有另行构建或把旧轮子冒充新构建。

## 5. 阶段总结：新知识与设计取舍

| 学到的机制 | 实际选择与原因 |
| --- | --- |
| 环境、发行包与导入路径是不同层 | 项目独立 Python/.venv、src 安装、正式锁、临时 cwd 和 wheel 来源检查共同证明可运行边界 |
| 配置读取本身是副作用 | 显式 load_settings，不在 import 构造实例；help 不受坏配置和未来服务影响 |
| 上下文和依赖注入控制执行边界 | 简单 Runtime/callable 工厂足够；报告构造与发布分开，退出失败不发布成功 |
| 日志既要可诊断也要约束内容 | 使用成熟格式化组件和短小允许字段筛选，不自建任意文本秘密检测框架 |
| TDD 证明行为的建立过程 | 保存真实缺能力 RED 与最小 GREEN；测试假阳性如实修正，回归/环境验收不伪造新 RED |
| 指标和替身必须说明范围 | 解释覆盖率的子进程边界；Fake 生命周期和缓存安装都不能代替真实外部能力 |

适度工程化使当前入口、配置、日志、装配可以独立解释和测试；没有提前创建业务空壳、微服务、资源容器或通用重试体系。后续业务特有的来源/定位/引用规则仍需独立实现。

## 6. 保留限制与下一步

已验证平台为 Windows x64、Python 3.12.15、uv 0.13.5。Linux、无缓存下载、sdist、性能和真实数据库/Redis/Embedding/LLM/飞书/PubMed 未验证；这些不是 doctor 的成功含义。Python 安全修订构建升级的既有问题继续按任务 SPEC 保留，启用外部业务/部署前重新核查。当前系统没有医学问答能力，也不承担诊断/治疗决策。

Phase 0 的 P0-01–08 已完成；本次不改源码、测试、依赖或规则，不创建 Git 提交。下一任务为 **P1-01：文献与证据 DTO、来源和定位契约**，关联 [MVP SPEC 的 P1-T01](specs/01-mvp.md)。需先细化输入输出/边界与失败测试，再写实现；本次不开始。
