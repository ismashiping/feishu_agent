# 工程与文档治理结果

适用范围：2026-10-28本轮工作区；既有未提交改动保留，未创建提交。当前业务状态见 [状态表](../development-plan.md)。

## 审计与交付

[审计与方案](plan.md)、[完整文档分类处理清单](inventory.md)、[整理前后实际文件树](tree.md)、[整理前文件哈希/模块/文档扫描数据](baseline.json)。清单覆盖原175份文档，包含根规则、依赖调查、evaluation结果及模型响应；新文件通过本导航及最终检查登记。自动提取用途与分类不等于逐句语义人工审查。

保留合理的模块化单体结构与全部公开入口，未搬迁Python模块。重写根README，建立文档总导航、当前架构、当前状态、运行指南索引和学习主题索引。三份原长文归档，旧架构/进度路径与历史标题锚点兼容；相对链接随快照重定位。验收、SPEC、教材、评价原始数据保留原路径，避免机械搬迁和外部链接破坏。

唯一源码变更是补齐command_runtime的ResearchLimits导入：整理前类型注解触发NameError，CLI/API/飞书及pytest收集均失败；只补导入，不变更DTO或业务规则。整理前哈希可复核其原状态。

## 分批检查记录

| 批次 | 实际检查与结果 |
| --- | --- |
| 1 审计 | 373文件、175文档、154 Python AST解析；内部链接/锚点及围栏0问题，domain反向依赖0；本地before.json |
| 2 导航/快照 | 扫描381文件，发现5处指向尚待生成的治理索引/清单；未把中间态称为通过，随后生成目标文件 |
| 3 初次运行 | 默认pytest收集失败：ResearchLimits未导入；CLI/API/飞书同因失败；保留pytest.txt。新增审计工具首轮Ruff失败，格式修正后通过 |
| 4 修复/验证 | 补一处导入后CLI help、飞书help、API工厂与10条路由导入通过。wheel离线构建成功；首轮uv默认缓存权限失败，改本地缓存且使用已安装构建后端成功 |

最终默认回归、文档复查、打包安装及diff记录在下方补记。详细本地运行日志位于`.artifacts/governance/`，不将忽略日志当作已提交的可共享证据。

## 未验证与维护边界

未重新执行真实PostgreSQL/Redis/在线PubMed/LLM/飞书收发、容器部署、远端CI或医学签署。默认marker排除不算通过。历史Phase0–9及MA验收不重新签署，失败基线、未执行与未验收项不覆盖。未改迁移、数据库表、排序、引用、Agent路由或版本发布规则。

后续新增功能同时更新当前架构与状态表；SPEC维护契约，执行结果写原阶段验收；操作说明只维护在专门指南，导航仅链接；阶段教材可继续原目录并维护主题索引。先核验冲突文档的时点和范围，再修订现状，不把旧计划改写为完成事实。

复查命令：` .venv/Scripts/python.exe scripts/audit_repository.py --output .artifacts/governance/recheck.json`。该工具使用标准库，检查文件、AST、显式Markdown链接/标题与围栏和domain导入；不验证外链可达性、Mermaid渲染、动态import或所有Markdown方言。输出issues须人工复核。

## 最终验证补记

- 默认全量：`.venv/Scripts/python.exe -I -m pytest -q --tb=short --basetemp=.artifacts/governance/pytest-final-tmp -o cache_dir=.artifacts/governance/cache`，本进程OMP/MKL线程各2：**1258 passed、122 deselected、1既有SDK弃用警告，140.80秒**。包括默认选中的集成测试；未选中的真实依赖不算通过。首轮收集失败单独保留，未覆盖。
- `python -m ruff check src tests scripts`：通过；审计工具Ruff format已执行。`python -m compileall -q src scripts alembic`：通过。
- `python -m clinical_agent --help`、`python -m feishu.main --help`：通过；API工厂导入并核对健康、问答、报告、分析、导入等10条路由：通过。
- `python -m uv build --wheel --offline --no-build-isolation --cache-dir .artifacts/governance/uv-cache --out-dir .artifacts/governance/dist`：成功；随后用uv pip --no-deps --target安装该wheel至独立目录，CLI/API/飞书导入成功，核实来源为该安装目录。复用了现有环境依赖，不声称全新环境依赖解析或容器部署通过。
- 最终Markdown显式本地链接、锚点、围栏：0问题；domain静态禁止反向导入：0。外链和Mermaid渲染未执行。
- 整理前SHA256对比：tests、evaluation、alembic、部署配置和依赖未变；既有源码仅command_runtime增加ResearchLimits导入。其他业务模块与历史证据未改。原工作区已有变更不纳入本轮成果。
- `git diff --check`：通过，Git提示若干既有文件LF/CRLF转换提醒，不是空白错误。没有运行外部服务或迁移业务库。

本地日志：`pytest.txt`（首轮失败）、`pytest-final.txt`（最终回归）、`ruff-all.txt`及`before/batch2/final.json`。后续可用审计命令复查；原始阶段结果并未由本轮回归替代。
