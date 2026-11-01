# 离线入库应用服务（P1-07）

P1-07提供Python服务导入单个PDF或单个PubMed XML批次；当前已有[CLI](cli.md)和[API](api.md)入口。飞书只完成纯事件过滤，运行时尚未接通。依据 [详细SPEC](specs/tasks/p1-07-offline-ingestion.md)，执行证据见 [开发记录](development-plan.md)。

## 准备与调用

先按 [数据库说明](postgres.md) 启动自己的PostgreSQL服务、设置进程环境并执行 `python -m alembic upgrade head`；按 [模型说明](local-embedding.md) 准备固定本地E5快照和ml/db extra。当前head为p107_0002，新增ingestion_metadata以保存真实解析器版本及profile/policy。不会在导入时自动迁移、下载模型或读取.env。

```python
from datetime import UTC, datetime
from pathlib import Path

from clinical_agent.adapters.embedding import REVISION, LocalModelConfig, load_local_embedder
from clinical_agent.adapters.offline import OfflineReader
from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
from clinical_agent.adapters.postgres.store import PostgresStore
from clinical_agent.application.ingestion import IngestionService
from clinical_agent.domain.ingestion import ImportRequest

embedder = load_local_embedder(LocalModelConfig(
    snapshot_dir=Path("models/multilingual-e5-base") / REVISION,
))
reader = OfflineReader(Path("data/snapshots"))
with database_engine(DatabaseSettings()) as engine:
    store = PostgresStore(engine)
    service = IngestionService(reader=reader, embedder=embedder, store=store)
    result = service.ingest(ImportRequest(
        source_type="pdf",  # PubMed本地导出文件使用pubmed_xml
        path=Path("data/input/article.pdf"),
        allowed_root=Path("data/input"),
        ingestion_time=datetime.now(UTC),  # 调用者明确提供，不由DTO自动补时间
    ))
    print(result.model_dump_json(indent=2))
    # 内部读取：store.load(document_id)返回脱离会话的PreparedIngestion或None。
```

示例path由调用者替换为自己的受控文件。ImportRequest契约错误抛ValidationError；文件级失败返回空entries及固定error_code；逐篇结果保留源条目index。对外结果只有状态、document_id、片段数和固定码，内部load包含源URI/原文，不应将内部DTO直接回给聊天用户。

源读取、编码和存储为显式可替换接口，应用服务不依赖SQLAlchemy、飞书或模型SDK。模型实例由调用者复用；每次store操作独立借连接、独立Session，结束后释放。READ COMMITTED在借出的连接上、事务开始前显式设置，不改调用者engine隔离配置，不自建连接池。

## 快照、位置与身份

输入必须是allowed_root内的普通文件，快照默认最多20MiB，XML解析仍受原10MiB/32条目配置限制。快照按SHA256.pdf/xml保存在显式snapshot_dir。采用同目录临时文件、fsync和原子排他硬链接发布；已存在内容必须一致，不覆盖损坏快照。Windows验收使用NTFS；部署文件系统必须支持同目录硬链接，否则明确失败，不降级为可能被读到半文件的写入。

解析器针对受控快照再次计算hash，document.source_uri指向该快照；PDF filename标题保持原输入stem，不把hash当标题。数据库同时保留canonical来源单元及parser版本、完整分块/模型配置。源文件移走后仍能按页/摘要节和Unicode码点回建证据。快照目录是运行数据，应由部署者持久化/备份；这里没有自动垃圾回收或文件系统/数据库的分布式事务。解析/编码/写库失败可能留下未引用快照，不删除用户原件。

document_id按source_type+身份稳定生成UUID5：PDF身份为内容hash，PubMed为PMID。chunk_id包含文档ID、完整profile/policy和序号；向量的浮点位差不参与身份。DTO不自动发明时间、ID、作者或来源。

## 返回状态与非覆盖规则

| 状态 | 含义 |
| --- | --- |
| imported | 当前文献和全部片段已在一个事务中提交 |
| already_present | 合法既有来源、hash、书目/单元/解析/处理配置和证据一致，返回既有ID/片段数 |
| needs_update | 同PMID对应不同内容快照，旧证据保留；没有执行更新 |
| conflict | 同内容的元数据或处理配置不同，旧证据保留 |
| rejected | XML条目解析明确拒绝，沿用固定安全码 |
| failed | 某个阶段失败，未声称成功；后续篇目继续处理 |

等价比较忽略输入ID、获取时间、source_uri、向量浮点位差；两个filename来源的标题可因改名不同。其他书目变化（包括人工标题/作者/source_url等）、解析器版本或policy变化均为conflict，不暗中更正旧记录。资源参数也属于当前完整policy比较，改变配置需显式重处理设计。

PubMed当前hash是整个XML快照，同PMID在不同批次中即使摘要相同，也可能needs_update；语义更新/归并属于Phase8。不会仅凭DOI、标题或文件名归并PDF与PubMed。legacy行的ingestion_metadata=NULL表示未记录真实版本，store拒绝作为合法重复，不自动填造；回填需单独实施。

## 事务、并发与失败

解析、分块、编码和PreparedIngestion完整性校验均在写事务前完成。校验包括编码数量/模型/范数、UUID/来源/顺序绑定、逐块切片回建及非空白文本覆盖。写事务只负责文献、全部片段与结果裁决。

来源唯一约束通过 `ON CONFLICT ON CONSTRAINT uq_documents_source DO NOTHING` 裁决；并发输家等待后读取已提交合法winner。不会把其他PK/片段约束异常当重复成功。任一片段或commit失败会回滚新文献；结果未知的连接中断只报告失败，调用者可重试，不承诺exactly-once。重复调用仍可能重新解析/编码，未实现缓存优化。

默认32条目/文件、128块/篇、120秒协作总预算，加上既有解析/分块/模型/DB限制。单次调用无法硬抢占，已知commit成功的条目保留成功；剩余超时条目失败，不回滚先前文献。错误码为封闭集合，异常原文、密码、本机路径和文献正文不会被拼进公开错误码。

## 验证与当前边界

默认pytest不运行database/external测试。使用专用临时数据库和本地模型分别验证：

```powershell
# 先满足postgres.md中的专用host/name/reset安全前提，选择未用过的basetemp。
.venv/Scripts/python.exe -m pytest tests/unit/test_ingestion.py `
    tests/unit/test_ingestion_mapping.py tests/integration/test_offline_reader.py -q
.venv/Scripts/python.exe -m pytest tests/integration -m "database and not external" -q
$env:OMP_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.venv/Scripts/python.exe -m pytest tests/integration/test_ingestion.py `
    -m "database and external" -q
```

数据库tests/integration/test_postgres.py现使用当前head验收，证据目录可通过CLINICAL_AGENT_TEST_EVIDENCE_DIR显式指定，默认写本次临时目录，不覆盖历史P1-06结果。真实链路测试另行记录，不将替身编码结果当E5验证；当前不验证医学检索效果、生产负载、API/RAG或飞书。
