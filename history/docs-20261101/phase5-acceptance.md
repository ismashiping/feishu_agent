# Phase 5 P5-01 混合检索验收记录

2026-10-28（Asia/Shanghai）。**Phase 5 核心范围验收完成**：FTS/RRF、真实PostgreSQL/pgvector与迁移、固定小样例对比、共享问答/引用及入口回归、学习材料齐备。Phase1/3原有医学人工/真实模型缺口不在本次伪标通过。

## 基线与修改范围

按项目规则 → 当前进度 → SPEC → 相关源码/测试核查。原有本地只有向量检索；Phase4的hybrid仅合并本地/在线来源。本次先冻结 [P5-01 SPEC](specs/tasks/p5-01-hybrid-retrieval.md)、hybrid-cases-v1及验收设计，再编写测试、复用架构最小实现，阶段末集中执行。没有逐任务RED/GREEN，不补造失败证据；原有未提交改动和历史记录保留。

- domain/hybrid.py实现RRF候选排名、chunk身份一致性、缺通道/稳定同分；domain/retrieval.py扩展mode、共同过滤、状态与排名契约。
- 现有PostgresRetriever复用来源hydration，以同一只读REPEATABLE READ事务完成两通道有限候选、最终top_k来源验证。keyword跳过查询Embedding，hybrid只编码一次，不相加余弦与FTS分数。
- 新迁移p501_0003在原chunks增加STORED simple tsvector及GIN；旧行回填，新写自动更新；原ID/片段/向量/旧迁移保留，无新依赖/新搜索服务。
- 共享装配与CLI/API提供本地mode/候选数/显式关键词/完整日期过滤。ResearchAnswer带本地策略/通道状态/warnings；原生成与引用门禁保持。scope=hybrid仍表示来源，不将在线条目放进本地RRF，来源合并保留同一本地文献的不同chunk。
- 六份 [学习材料及Demo](learning/phase-05/README.md)，API/CLI/数据库/架构说明和阶段计划同步。飞书普通文本仍用默认vector，未新增消息语法。

任何必需通道失败均报错，不自动降级；ASCII关键词范围及完整出版日过滤语义明确。simple FTS不是BM25或已验证中文分词。default vector行为、固定E5模型身份、来源/定位/hash校验保留。未部署容器或迁移用户现有库；使用新版本前需显式 `alembic upgrade head`。

## 集中测试证据

正式解释器 `.venv/Scripts/python.exe`，Python3.12.16。所有命令从项目根运行，本次证据目录 `.artifacts/p5-01-20261028/`。

| 范围 | 实际结果 |
| --- | --- |
| 首次新目标单元 | `-I -m pytest tests/unit/test_hybrid_retrieval.py -q --basetemp=.artifacts/p5-01-20261028/target-tmp -o cache_dir=.artifacts/p5-01-20261028/cache`：17 passed，2.44秒，target.txt |
| 首次真实数据库联合 | 79 passed /1 failed /2 deselected，8.60秒。旧全局字符串vector断言误判新增通道状态，修正为实际hit/chunk/document不包含原始vector字段，不删除泄露防护；database-1d9e8a8e69.txt |
| 数据库修复后 | 80 passed /2 deselected，6.95秒；database-3f6fe8796f.txt |
| 最终增强数据库联合 | 80 passed /2 deselected，7.41秒；database-8040b3fe77.txt。增加实际排名结果进入问答/引用门禁、源/范围过滤以及缺FTS列失败不降级的断言，未放宽原约束 |
| 首次默认全量 | 1140 passed /2 failed /103 deselected /1既有SDK警告，151.17秒；regression.txt。失败是旧head断言仍为p107_0002及旧“vector字样不得出现在全答案”断言；更新head同时保留旧迁移链检查，并继续验证实际来源/片段没有向量/内部路径泄漏 |
| 最终相关联合 | `-I -m pytest tests/unit/test_hybrid_retrieval.py tests/unit/test_ingestion_mapping.py tests/unit/test_research.py -q --basetemp=.artifacts/p5-01-20261028/target-final-tmp -o cache_dir=.artifacts/p5-01-20261028/cache`：83 passed，4.26秒；target-final.txt。含新混合模式/日期/partial多种局限共存仍满足原回答上限的边界 |
| 最终完整默认回归 | `-I -m pytest tests -q --basetemp=.artifacts/p5-01-20261028/regression-final-tmp -o cache_dir=.artifacts/p5-01-20261028/final-cache`：1143 passed /103 deselected /1既有SDK弃用警告，137.99秒；regression-final.txt |
| 质量与Demo | `-m ruff check src tests alembic docs/learning/phase-05/demo.py`通过；format同范围99文件已格式化；`-m mypy src --cache-dir .artifacts/p5-01-20261028/mypy-cache`45源文件通过；`-I docs/learning/phase-05/demo.py`返回手算一致的RRF与来源DTO |

真实数据库命令由本次隔离辅助脚本执行：`-I -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py tests/integration/test_hybrid_retrieval.py -m "database and not external" -q --tb=short --basetemp=<本次唯一目录> -p no:cacheprovider`。要求本机、clinical_agent_test_前缀及ALLOW_TEST_RESET=1；环境变量由脚本设置，只指向本次新库。2个外部E5项排除，不算通过。默认回归的103项排除也不算通过。

首轮mypy的字面量/SQL表达式类型与长行问题已修正并复验。P5新增模式与日期说明原先可能使最复杂合法混合回答超出原10条局限上限，已合并为一条本地策略说明并以完整DTO测试验证，未放宽引用或最大条数。

## 真实资源与清理

普通沙箱不能访问Docker管道；获准后仅使用缓存的 `pgvector/pgvector:0.8.7-pg16`，image_id=`sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a`，未拉取其他镜像。三个唯一命名测试容器/卷为clinical-p501-pg-1d9e8a8e69、3f6fe8796f、8040b3fe77及各自-data卷，随机127.0.0.1端口、随机进程环境密码，不打印或保存密码。

每次按本次run标签确认归属后finally清理，三轮报告均container_removed=true/volume_removed=true；没有碰既有Redis/其他容器、用户卷、全局Docker配置或业务数据库。脚本与每轮数据库运行JSON在忽略的证据目录。最终覆盖升级/降级/重升/Alembic check、既有持久化/入库/向量回归与新的FTS/pgvector同快照。

## 固定三模式比较

数据集hybrid-cases-v1，SHA256=`8b76ed6506eb868946f74042c69ba863916a9941d49b8745846721bfd1896065`，在实现前冻结。文本和二维方向由测试补零到768维，是合成向量，不是真实E5效果或医学标注。

| 模式 | 真实数据库返回chunk ID（top_k=2） | 受控目标A=1是否命中 |
| --- | --- | --- |
| keyword | [1] | 是，首位 |
| vector | [2,1] | 是，第二位 |
| hybrid RRF | [1,2] | 是，首位 |

A有aspirin字面匹配、向量排2，因此RRF=1/61+1/62；B只有向量排1，因此1/61。手算同分/缺通道/重复chunk与同文献不同片段另有单元测试。实际comparison.json随数据库测试保存在当轮basetemp。

失败/限制样例：中文或非ASCII关键词明确retrieval_language_unsupported；缺FTS列是retrieval_failed，不变成空结果；未知/仅年/月日期被排除；空通道成功但无命中；通道异常不降级。这些是核心正确性验证，不表明真实医学召回全面优于单通道。

## 保留的边界

未运行新增真实E5+LLM完整研究、付费调用、PubMed联网、性能压测、额外重排器或规模化评价。现有库尚需部署者显式升级；FTS的ASCII策略和日期精度排除规则有意明确。Phase1人工医学审查、Phase3真实模型/人工样例和其他历史迁移后部署缺口继续保留。本阶段不执行Phase6证据质量/冲突分析，不自动进入下一阶段。
