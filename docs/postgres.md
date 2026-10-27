# PostgreSQL 与 pgvector：本地模型和迁移

P1-06 只提供 ORM、连接构造、Alembic 和本地基础设施；还没有文献导入服务、DTO 映射、检索或问答命令。[任务 SPEC](specs/tasks/p1-06-postgres-schema.md)、[实际验收记录](development-plan.md)。

P1-07当前补充：Python离线入库服务/DTO映射已实现，操作见 [入库说明](offline-ingestion.md)。最新head=p107_0002，增加nullable ingestion_metadata；既有P106行不伪造解析信息，读作legacy并拒绝当合法重复。上文P106是历史交付范围；当前已有[P1-08检索](vector-retrieval.md)、[基础RAG](basic-rag.md)、[CLI](cli.md)及[API](api.md)。

## 安装与本地启动

```powershell
$env:UV_CACHE_DIR=Join-Path (Get-Location) '.research-cache/uv'
$env:UV_PYTHON_INSTALL_DIR=Join-Path (Get-Location) '.tools/python'
.venv/Scripts/python.exe -m uv sync --locked --extra db --extra ml --system-certs
```

只做数据库工作可以省略 ml extra；当前完整默认开发/测试需要ml/db/rag/api四个extras，见[README](../README.md)；上述sync只面向入库/数据库模块，会移除未选中的extras。基础 doctor 不需要任一 extra。

Compose 镜像固定为 pgvector/pgvector:0.8.7-pg16 及实际 digest。P1-06 实测 PostgreSQL16.15 / pgvector0.8.7；容器只绑定127.0.0.1，数据保存在 project 独立 named volume。本阶段没有 Redis/API/飞书服务占位。

下面先设置专用的本地环境变量。密码由调用者通过进程环境提供，示例不会回显或写入源码；不要粘贴真实密码到仓库。`--env-file .env.example` 是显式读取不含秘密的模板，避免 Compose 自动读取用户 .env；Python配置本身从不自动读取 dotenv。

```powershell
$env:CLINICAL_AGENT_DB_HOST='127.0.0.1'
$env:CLINICAL_AGENT_DB_PORT='55432'
$env:CLINICAL_AGENT_DB_NAME='clinical_agent'
$env:CLINICAL_AGENT_DB_USER='clinical_agent'
# 调用者先设置 CLINICAL_AGENT_DB_PASSWORD；也可生成仅当前 shell 使用的开发密码。
$env:CLINICAL_AGENT_DB_PASSWORD=[Convert]::ToHexString(
    [Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose -p clinical-agent-local --env-file .env.example config --quiet
docker compose -p clinical-agent-local --env-file .env.example up -d --wait postgres
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic check
```

同一数据卷初始化后，后续启动必须沿用首次设置的数据库密码；更换 shell 中环境变量不会自动更改卷内账号密码。迁移账号需要建扩展/表权限；生产业务账号最小授权留待部署任务，不把本地超级用户配置当生产方案。

P1-06 本次实际使用独立 project `clinical-agent-p106-20261027`、database `clinical_agent_test_p106_20261027`，随机密码只保存在忽略的 artifacts 中供本次验收进程使用，没有读取已有用户数据库配置。Docker Desktop 的 Linux engine 通过 `--host npipe:////./pipe/dockerDesktopLinuxEngine` 访问；调用者本机默认 context 正确时无需此参数。

## 两个表的契约

| 表 | 保存的事实与约束 |
| --- | --- |
| documents | UUID、来源类型/哈希/URI/URL/获取范围、标题及来源、作者、日期精度、期刊/DOI/PMID、原文/摘要、UTC获取时间、canonical source_units JSONB |
| chunks | UUID、父文献及来源类型、序号、原文、页/摘要节/码点区间、实际 token 计数与预算、policy JSONB、完整模型/分块身份、VECTOR(768) |

source_identity 是数据库 generated stored 列：PDF使用内容哈希，PubMed使用PMID。`uq_documents_source` 保障并发唯一，不以文件名、路径或 DOI 猜测同一来源；`uq_chunks_position` 保障文献/分块版本/序号唯一。直接 SQL 也不能绕过组合来源外键、768维固定模型身份、token预算、片段字符长度和单位向量范数约束。文献显式删除会由数据库级联删除片段。

来源字段通过父文献读取，不在片段重复一份可能漂移的来源 JSON。JSONB 日期/来源单元保留原契约，但数据库只约束容器形状；完整字段及切片业务关系须由下一任务的 DTO 映射器验证。只有已编码片段可写此表；不保存空向量半成品，不把摘要伪装成全文。

VECTOR(768) 是基于 P1-05 实测固定 E5 模型作出的迁移选择；更换模型/维度必须新迁移并重新编码，不混用。当前没有 ANN/FTS 索引或业务检索排序。PubMed content_hash 当前指整个 XML 快照，相同 PMID 的不同快照仍受唯一身份约束；更新分类和语义级去重不是本任务已完成的能力。

## 连接与迁移生命周期

```python
from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine

# 显式构造时读取环境；password为SecretStr，不拼接未转义DSN。
settings = DatabaseSettings()
with database_engine(settings) as engine:
    # engine尚未预连接；实际调用才从池中获取连接。
    with engine.begin() as connection:
        pass  # 后续应用服务在短事务中使用；当前没有自动导入服务。
# finally dispose，包含业务异常分支。
```

池大小5、额外连接0、池等待5s；连接5s、语句10s、锁2s、空闲事务10s超时。SQL参数隐藏且echo关闭；应用不得把数据库异常原文直接回复外部用户。应用启动不会 create_all/CREATE EXTENSION，也不自动迁移。

初始迁移 `p106_0001` 由 Alembic 从空库生成，经审查增加显式 `CREATE EXTENSION IF NOT EXISTS vector`。迁移声明冻结在版本文件，不 import 当前 ORM 来生成历史 DDL。downgrade base 会删除两个业务表及数据，只用于专用可重建数据库；保留vector扩展。升级失败通过PostgreSQL事务DDL回滚。`alembic check` 只覆盖工具可检测的差异，不能替代真实约束测试。

离线 SQL 无需密码或数据库连接，可供审查：

```powershell
.venv/Scripts/python.exe -m alembic upgrade head --sql
```

## 独立数据库测试

默认 pytest 排除 database/external/performance。数据库测试要求显式本机、`clinical_agent_test_` 数据库前缀及 reset opt-in；准备专用新 project/volume，不能指向用户业务库。

```powershell
$env:CLINICAL_AGENT_DB_NAME='clinical_agent_test_manual'
$env:CLINICAL_AGENT_DB_ALLOW_TEST_RESET='1'
# 同时设置 HOST/PORT/USER/PASSWORD 并启动独立 Compose project。
.venv/Scripts/python.exe -m pytest tests/integration/test_postgres.py -m database -q `
    --basetemp=.artifacts/p106-manual-db-temp -o cache_dir=.artifacts/p106-manual-db-cache
```

使用未用过的 basetemp 保留历史证据。测试会升降级/重建该库业务表，验证实际持久化、向量距离、约束、回滚和双连接争抢；缺少安全前提时失败，不 skip 后冒充通过。这组schema测试不代替应用级幂等验收；already_present/needs_update/conflict及应用幂等已由P1-07实现并另测，见[入库说明](offline-ingestion.md)。当前不提供通用自动重试。

结束后可停止自己的服务并保留卷：`docker compose -p <自己的project> --env-file .env.example stop postgres`。不要清理其他 project、执行 volume prune，或为了重复验收删除用户数据卷。
