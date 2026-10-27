# P1-06：PostgreSQL + pgvector 持久化模型与迁移

状态：2026-10-27 按本任务范围验收完成；13目标单元、47真实数据库测试、397默认回归通过。先冻结SPEC再执行RED/GREEN，证据见 [开发记录](../../development-plan.md)。依赖P1-01–05；仅schema、连接构造与迁移，不实现入库服务或宣称Phase1完成。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

建立文献、来源单元、证据及已验证 E5 向量的 PostgreSQL 存储契约。使用 SQLAlchemy 2.x、Alembic 和官方 pgvector Python 类型，真实 PostgreSQL 验收，不用 SQLite/Mock 代替。

## 2. 功能需求

documents/chunks 两个业务表。文献保留全部书目信息、原始获取范围、来源 URI/URL、内容 hash、精度日期、原文和 canonical source_units JSONB，原文件删除后仍可保留切片回建依据。chunks 保留文献外键、序号、位置、原文、token 计数/预算/分块 policy、模型身份及 VECTOR(768)。DTO 与 ORM 分离；本阶段不添加 DTO 映射器。

来源身份由数据库 generated stored 列计算：PDF=content_hash，PubMed=PMID；unique(source_type,source_identity)，不使用 URI/文件名/DOI 判重。同来源不同 UUID 并发写入也只能保留一条。内容更新不自动覆盖，后续服务识别 needs_update。

模型固定为 P1-05 的 intfloat/multilingual-e5-base，model_revision/tokenizer_revision=d128750597153bb5987e10b1c3493a34e5a4502a，768维、normalized=true、source-unit-v1、document_prefix=passage: 空格。替换模型须单独迁移，不允许旧向量混用。片段 unique(document_id,chunking_version,chunk_index)；文献删除明确级联删除片段，暂不开放业务删除接口。

## 3. 非功能需求

显式创建/关闭 engine，不在模块导入、doctor、应用启动自动连接或建表。SQLAlchemy 自带连接池：pool_size=5、max_overflow=0、pool_timeout=5s、pool_pre_ping；connect_timeout=5s、statement_timeout=10s、lock_timeout=2s、idle_in_transaction_session_timeout=10s。hide_parameters=True，禁止 SQL echo。

密码 SecretStr、仅显式环境/参数输入，配置不读取 .env；默认 CLI 不依赖数据库配置。Alembic 显式独立步骤，迁移用 PostgreSQL transactional DDL；vector 扩展由 upgrade 创建或复用。downgrade 删除本项目表而保留扩展，避免删除其他消费者依赖的扩展。

## 4. 本任务不实现

不实现导入应用服务、DTO/ORM 双向映射、持久文件快照、already_present/needs_update 枚举与转换、检索/索引调参、API/飞书、模型推理变更。数据库 constraints 保障结构性不变量，JSONB 内部日期/来源单元的完整业务校验和原文切片关系须由后续映射器使用已有 DTO 验证，不创建复杂 SQL 触发器重写业务验证。

## 5. 输入输出契约

DatabaseSettings：CLINICAL_AGENT_DB_HOST 默认127.0.0.1、PORT 默认55432、NAME 默认clinical_agent、USER 默认clinical_agent、PASSWORD 必填 SecretStr；host/user 非空，port严格整数1..65535，name仅 ASCII 简单标识符（最多63字符）。设置类显式构造，无自动 dotenv。database_engine(settings) 为 contextmanager，返回未预连接的 Engine，finally dispose；不执行迁移。Alembic env 支持显式 config.attributes['connection']，否则加载 DatabaseSettings 并构造 engine；offline模式生成 SQL 不要求密码或连接。

迁移命令 `python -m alembic upgrade head` / `downgrade base` / `upgrade head --sql`。无硬编码 DSN/密码；URL.create 负责转义特殊密码。迁移登录账号须有 CREATE EXTENSION/DDL 权限，生产业务角色授权在部署任务落实。

## 6. 数据模型

DocumentRecord：UUID document_id PK（无随机默认）、source_type、generated source_identity、content_hash、source_uri、source_url nullable、content_scope、title/title_origin、authors JSONB array、publication_date JSONB object、journal/doi/pmid nullable、abstract/text nullable、ingestion_time TIMESTAMPTZ、source_units 非空 JSONB array。保存全文本，不将摘要标为全文。PMID正整数字符串；PubMed 必须 PMID 且 scope=abstract；PDF scope=extracted_text/full_text；hash为64位小写十六进制；获取范围约束匹配 abstract/text。额外 unique(document_id,source_type) 用于片段组合外键。

ChunkRecord：UUID chunk_id PK、UUID document_id、source_type、chunk_index>0、text非空、location_kind、page nullable、section nullable、start_offset>=0/end_offset>start、模型七项身份字段、document_prefix、token_count>0、max_tokens<=512、chunking_policy JSONB object、embedding VECTOR(768) NOT NULL。end-start=char_length(text)；PDF页>0、kind=pdf_page，摘要page=null、kind=abstract；组合 FK(document_id,source_type) 确保父来源类型一致。token_count<=max_tokens；embedding_dimension=768；向量范数误差<=1e-4，pgvector自身拒绝非有限元素。精度/片段位置中的 Unicode 码点语义与既有 DTO 一致。

固定 identity/维度/前缀/分块版本通过 CHECK 约束；字段不自动伪造作者、出版日期、ID、时间或模型信息。来源元数据通过父文献获取，不重复保存一份可能漂移的 source_metadata JSON。仅建唯一约束和 FK 所需索引，不提前建立 HNSW/FTS。

## 7. 核心业务流程

准备专用 PostgreSQL16+vector0.8.7 → 显式 Alembic upgrade → 通过 ORM/SQL 显式事务写入文献与片段 → 提交后另一连接读取 JSON/位置/向量 → 约束拒绝非法写入并回滚 → downgrade/upgrade复验且无 metadata drift。业务解析/编码仍在事务外，由下一任务编排。

## 8. 异常与边界场景

配置错误 ValidationError 隐藏输入/密码；连接/DDL 权限或扩展缺失按实际失败记录，不能降级为无向量存储。ORM 不截获 IntegrityError 并冒充重复成功；后续 store 只解释已命名来源唯一约束。数据库约束拒绝错误模型、维度、范数、位置、FK、重复来源/序号；单文档事务中片段失败必须连同新文献回滚。

测试必须单独 database marker（默认排除），显式 `CLINICAL_AGENT_DB_ALLOW_TEST_RESET=1`、host=127.0.0.1、name前缀clinical_agent_test_；缺前提明确失败而非 skip。只操作本次独立 Compose project/测试数据库，不连接已有用户库、不执行 DROP DATABASE 或删除任何已有 volume。容器只绑定127.0.0.1端口，密码随机生成放进运行环境；Compose 用 `--env-file .env.example` 避免读取用户 .env。

## 9. 测试用例清单

- 显式配置/密码隐藏、URL特殊字符、连接池/超时/关闭与导入无资源副作用。
- SQLAlchemy PostgreSQL DDL：两表、向量768、唯一/外键/级联、generated身份；ORM不是Pydantic DTO。
- Alembic offline SQL 含扩展/表/约束、无 create_all；升降级 revision 完整。
- 真实数据库空库 upgrade、重复 upgrade、downgrade保留vector、再次upgrade、alembic check无漂移。
- 实际 JSONB/作者/不精确日期/Unicode/source_units/timestamptz/vector 往返；实际 pgvector cosine距离手算。
- 直接SQL/ORM非法数据、同内容多路径/同PMID唯一、重复片段、来源错配/孤儿、向量错误、跨页kind错、片段失败原子回滚。
- 两独立事务并发来源唯一争抢，一条提交、一条命名unique错误；不宣称已实现应用层幂等回复。
- 默认完整回归/导入隔离、Ruff/mypy、锁/安装兼容检查；模型推理逻辑未改，无需重复下载模型。

## 10. 可执行验收标准

先 `pytest tests/unit/test_postgres.py -q --basetemp=.artifacts/p1-06-20261027-01/red-temp` 确认因目标缺失 RED，再最小实现 GREEN。真实集成 `pytest tests/integration/test_postgres.py -m database -q` 独立记录；默认 pytest 排除 database/external/performance，不把默认通过当数据库验收。实际记录 SELECT version()/pg_extension.extversion、镜像 digest，Compose config 检验。官方依赖精确 db extra：SQLAlchemy2.1.6、alembic1.20.1、psycopg[binary]3.3.6、pgvector0.5.1，正式 uv.lock；Python3.12真实安装验证。Ruff包含迁移，mypy覆盖src，SQL迁移需实际运行后才可验收。

## 11. 阶段依赖及完成定义（DoD）

SPEC/真实 RED→GREEN、独立数据库约束/事务/迁移验收、默认回归及文档均通过，才完成本任务。下一任务 P1-07 离线入库服务与事务/幂等映射，需用户指定后开始。Phase1仍未完成，不创建阶段学习完成材料。

依据：2026-10-27 官方 PyPI 元数据存于本次 artifacts；[SQLAlchemy2.1约束](https://docs.sqlalchemy.org/en/21/core/constraints.html)、[Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)、[pgvector扩展](https://github.com/pgvector/pgvector)、[Python集成](https://github.com/pgvector/pgvector-python)、[psycopg安装](https://www.psycopg.org/psycopg3/docs/basic/install.html)。本阶段固定已验证的E5维度，未把768作为所有模型的通用维度。
