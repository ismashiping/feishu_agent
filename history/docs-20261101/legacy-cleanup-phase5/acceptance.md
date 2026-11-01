# 遗留兼容层清理 Phase 5 实际交付（2026-10-31）

## 1. 当前架构和执行链

Agents、API、RAG、Integrations、DB 与飞书均只保留 canonical 模块。`clinical-agent` 仍进入 CLI，API 仍使用 `clinical_agent.api:create_app`，`clinical-feishu`、Dockerfile 和 Compose 进入 `clinical_agent.channels.feishu.main`。研究、HTTP、检索和消息业务仍由原 canonical 实现执行。

映射内旧导入现在应产生 `ModuleNotFoundError`。历史 before/archive 文档保留旧路径原文。

## 2. 问题与修改依据

Phase 1–4 的兼容文件已无生产算法，但测试、可运行文档、console、Docker 和 Compose 仍引用旧路径。删除前先迁移这些活动调用方。`api_runtime.py` 曾聚合 Schema、执行池和资源装配，调用方按 `api.schemas`、`api.execution`、`api.runtime` 的真实定义回迁，没有把三个职责重新合并。

`adapters/pmc_fulltext.py` 在 Phase 3 前已退役且无 canonical 对应模块，不纳入本阶段。

## 3. 迁移计划与回滚

四批按 Agents、API、RAG/DB、飞书执行。每批回滚只恢复该组别名文件和对应入口配置，不回滚 canonical 实现，也不使用全工作区 reset。

## 4. 实际修改

已删除 `application/workflow.py`、`application/agents.py`、`api_runtime.py`、Phase 3 映射的 adapters 兼容树，以及顶层 `feishu` 包。`api.py` 在本阶段开始前已经不存在。同步迁移活动测试和可运行文档，setuptools 只发现 `clinical_agent*`。

本阶段没有修改 Prompt、Agent State、HTTP 协议、数据库 Schema 或业务算法，也没有执行 Alembic。

## 5. 兼容性检查

正式命令和 canonical Python 入口保留。旧内部导入不再兼容，这是本阶段明确收口的行为。wheel `clinical_literature_agent-0.1.0-py3-none-any.whl` 不含旧路径，并包含 Agents、API、RAG、Integrations、DB 和飞书 canonical 文件；`clinical-feishu` 指向新 main。

## 6. 验证结果

环境为 Windows/PowerShell、仓库 `.venv` Python 3.12。没有连接真实数据库、Redis、模型或飞书。

1. Agents/API 清理后专项：101 passed、1 deselected。
2. RAG/DB 清理后专项：207 passed、2 deselected。
3. 飞书与遗留扫描首次 3 failed、466 passed。失败是 Phase 4 Demo 仍导入已删除别名，以及已安装 console script 仍指向旧模块。修正 Demo 后执行 `uv sync --frozen`，该命令按默认组移除可选依赖，隔离导入缺少 `httpx`；随后 `uv sync --frozen --all-extras` 恢复，锁文件未改。复验 86 passed。
4. Ruff 对 `src`、`tests` 和四份 Demo 最终通过。`uv lock --check --offline` 通过，解析 139 个包。Mypy 失败，记录时为 180 条错误，不标通过。
5. 学习 Demo 最终退出 0：canonical 导入成功、10 张表可见、4 个代表旧模块不可导入。
6. 第一次完整回归在 `f271ab3` 删除 PubMed 在线检索但测试尚未对齐时执行，结果 27 failed、1622 passed、121 deselected。该结果作废。对齐后的原失败文件复验为 288 passed。
7. 第二次完整回归结果为 32 failed、1602 passed、119 deselected、226.77 秒。运行期间工作区被暂存删除 `application/retrieval.py`、`db/retrieval.py`、`domain/hybrid.py`，并出现未跟踪迁移 `alembic/versions/oa3002_0010_drop_pubmed_cache.py`。失败主因是这些模块缺失及迁移 hash/head 从 `oa3001_0009` 变为 `oa3002_0010`。该结果不能代表稳定代码树，整库不通过。

## 7. 剩余风险与停止边界

兼容层清理已进入提交 `40a252a` 和后续代码，但 Phase 5 没有稳定的完整回归通过证据。当前暂存的检索删除和新迁移超出兼容层范围，不能由本阶段继续修改、执行或回滚。真实 Redis、数据库、模型、飞书、部署和医学验收均未执行。

教材位于 `docs/learning/phase-05/legacy-cleanup`。到此停止，不删除其他历史代码，也不进入新的业务阶段。
