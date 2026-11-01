# P8-01：显式版本发布核心

2026-10-28。用户明确启动Phase8，保留旧真实E2E/医学缺口。本任务实现P8-F01/F02核心及T01/T02/T03/T05相关边界，不标Phase8全完成；游标、调度、跨来源别名和固定回归触发留P8-02。

稳定文档身份沿原PDF内容hash/PubMed PMID，不按文件名归并PDF。仅显式ingest --update-existing使用VersionedPostgresStore，普通入库不变。内容或元数据更新先在事务外完成原解析/分块/编码，再在同一写事务锁定文档、归档旧PreparedIngestion（含原chunk/来源/向量）、生成新版本chunk UUID、替换活跃文档/片段并登记不可变版本。检索仍使用原documents/chunks，因此只见活跃版本；load_version返回原版本完整快照，历史报告已有来源片段不覆盖。物理快照仍由原OfflineReader内容寻址文件保留，不删除历史文件。

version_id由稳定document_id及内容/元数据/解析/分块签名生成。签名排除路径/入库时间/向量数值；同内容metadata更新也新版本。重复最新无新版本，已存在历史版本不自动回滚；模型或分块策略变化拒绝，显式重建后续处理。Postgres行锁/来源唯一约束处理并发，任意失败全部回滚，旧活跃保持。

API内部publish(prepared,dry_run=False)和load_version(version_id)。dry_run只在已准备的DTO上计算计划，事务回滚、无写；本任务不提供免编码的UpdateRequest dry_run命令，不能声称完整dry_run链路已交付。CLI显式更新返回updated/metadata_updated；普通API/入库默认保持。

迁移p801_0004新增document_versions（JSONB归档、不可变ID、活跃唯一索引），旧行首次更新时惰性归档，不改写旧chunks。旧报告在更新前后保留旧ID/hash/text/location，新活跃chunk重新命名避免旧ID含义变化。历史版本只提供内部Python读取，不把大向量暴露到问答。

先写tests/unit/test_knowledge_versions.py和tests/integration/test_knowledge_versions.py，再实现；阶段末集中验证签名、不可变chunk重键、真实PG更新/元数据/重放/dry_run/并发/回滚与旧版读取。真实测试只用唯一隔离容器库，缺依赖如实待验收。相关旧存储/检索回归及质量检查需记录，不用Mock替代PG事务保证。六份学习说明齐备后记录本任务状态，不进入Phase9。
