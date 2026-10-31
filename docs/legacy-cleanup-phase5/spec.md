# 架构迁移 Phase 5 遗留兼容层清理冻结 SPEC

## 目标与授权

在 Phase 1–4 canonical 模块已完成迁移和相对基线验证后，迁移仓库内活动调用方并删除对应兼容文件，避免长期维护两套可导入路径。用户已明确授权按 Agents → API → RAG/Integrations/DB → 飞书四批执行；每批失败即停止。

## 边界

只删除已有 canonical 替代且本 SPEC 列明的兼容文件：

- `application/workflow.py`、`application/agents.py`
- `api.py`、`api_runtime.py`
- `adapters` 下 Phase 3 映射的 21 个子模块及两个兼容包入口
- 顶层 `feishu` 六个兼容包文件

不删除 `application`、`domain`、`agents`、`api`、`rag`、`integrations`、`db`、`channels` 的 canonical 实现，不改数据库 Schema、Alembic 版本、业务算法、Prompt、API 协议、Agent State 或飞书交付语义。已在 Phase 3 前退役的 `adapters/pmc_fulltext.py` 不归因于本阶段，也不恢复或重新处理。

历史验收 Markdown、before 快照、archive、日志和 XML/TXT 证据保留旧路径原文；活动源码、测试、脚本、可运行文档、部署配置和 wheel 不再依赖旧路径。

## 输入输出与兼容变化

输入为现有 canonical 公共接口。输出、DTO、异常、状态码和资源生命周期保持不变。

仓库内以下旧 Python 导入在本阶段后明确不再兼容，并应抛出 `ModuleNotFoundError`：`clinical_agent.application.workflow`、`clinical_agent.application.agents`、`clinical_agent.api_runtime`、Phase 3 的 `clinical_agent.adapters*` 路径和顶层 `feishu*`。`clinical_agent.api:create_app`、`clinical-agent`、`clinical-feishu`、`python -m clinical_agent` 和 `python -m clinical_agent.channels.feishu.main` 保留。

## 真实引用依据与影响

- 生产 `src` 仅剩待删兼容文件之间的旧导入；canonical 实现已使用新路径。
- 当前测试仍有 50 余文件使用旧路径，需要机械迁移 patch 目标和导入。
- 可运行 learning/final-acceptance/fulltext/OpenAlex 脚本存在旧导入，需要迁移；archive、before 和历史结果不改。
- Dockerfile、Compose 仍执行 `python -m feishu.main`，pyproject 包发现仍包含 `feishu*`；删除顶层包前必须切到 canonical 入口。
- Alembic 已使用 `clinical_agent.db`，scripts 活动实现已使用 canonical；`scripts/audit_repository.py` 中的旧字符串是违规扫描规则，不是运行依赖，保留。

删除后，使用未声明旧路径的仓库外调用方会导入失败。这是 Phase 5 的有意兼容性收口，不影响已冻结的正式命令和 HTTP/消息协议。

## 分批实现与回滚

1. Agents：迁测试和可运行教材，删除两个兼容文件。回滚只需恢复两个别名文件及旧测试导入。
2. API：迁测试和可运行教材，删除 `api.py`/`api_runtime.py`。回滚恢复两个文件；`clinical_agent.api` 包保持不动。
3. RAG/DB：一次性迁全部活动测试/文档脚本，删除映射内 adapters 兼容树。回滚恢复别名文件，不回滚 canonical 实现或 Alembic。
4. 飞书：迁测试，切 Docker/Compose 和包发现，删除顶层包。回滚需同时恢复顶层包、`feishu*` 包发现及部署命令。

任何批次出现新的导入、契约或回归失败，停止后恢复该批兼容文件和配置；不得用恢复整个工作区覆盖 Phase 1–4 或用户未提交修改。

## 验收测试

- 先编写 `tests/unit/test_legacy_cleanup.py` 和冻结 fixture。
- 所有列明旧文件不存在，旧模块在隔离子进程导入时失败。
- canonical 模块可隔离导入且不创建外部资源。
- 活动 Python/配置零旧导入；历史证据仅按明确目录允许。
- Graph 拓扑/State/ResearchService、API OpenAPI/lifespan/容量、RAG/DB DDL/Alembic hash、飞书事件/租约/队列/关闭和日志契约复用前四阶段测试。
- 两个 CLI、canonical 飞书模块入口及 `clinical-feishu` 的 help/非法参数契约保持。
- wheel 只含 canonical 包，不含待删文件或顶层 `feishu`。
- 阶段末运行 Ruff、Mypy、默认离线完整回归、锁检查和独立 wheel 检查；真实服务不可用项单列。

## 完成标准

四批删除均有引用零结果和专项测试证据；完整回归相对 Phase 4 不新增失败；学习材料与实际验收完成。未运行、失败、排除、真实依赖和医学人工复核不得标记通过。完成后停止，不再删除其他历史代码。
