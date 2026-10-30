# Phase8当前验收状态（2026-10-28）

**本次冻结的维护核心开发与工程验收完成。** 在线窗口、来源状态原子发布、已知PMID在线门禁和显式重建已交付。最终PG联合98 passed/3外部项排除；真实PubMed+缓存E5+PG+重建/历史回读1 passed；默认回归1243 passed/1旧Schema断言failed，修正后及最后快照原子落盘的受影响联合278 passed/1外部项排除、PG目标1 passed。未将原失败批次改标全量通过。

最终质量检查与教材交付；所有临时容器/卷已清理。支持既定模型维护而非通用模型迁移，未部署业务环境；Phase7报告0/2及医学人工待审保持，Phase9未启动。详细命令、失败修复和限制见本文件最后P8-04/P8-05段落。

以下按任务时间保留历史记录，“未完成”等描述代表当时状态。

# Phase8 P8-01 显式版本发布验收

2026-10-28。完成P8-01版本发布核心与学习材料；**Phase8整体未完成**。用户明确启动本阶段，Phase7真实E2E/医学缺口保留。游标、调度、别名、免编码dry_run和固定回归触发仍属P8-02，不进入Phase9。

先读规则/进度/SPEC及存储、入库、检索和测试，冻结[P8-01](specs/tasks/p8-01-version-publication.md)，先写单元/真实PG测试，再实现并集中验收。默认PostgresStore行为不改；CLI ingest --update-existing显式装配VersionedPostgresStore。

## 实现

新增p801_0004迁移与DocumentVersionRecord。版本签名排除路径/入库时间/向量数值，保留内容、元数据、来源单位、解析和分块身份；新chunk按版本UUID重命名。归档旧PreparedIngestion、切换原documents/chunks、登记新活跃版本在单事务/行锁下完成。旧报告的chunk/hash/原文保留，首次更新旧库惰性归档旧ID原样，load_version供内部读取。历史文件不删除，历史DTO含向量/本地URI，不能直接作为公开输出。

重复最新输入already_present；内容变化updated；同hash元数据变化metadata_updated。模型/策略变化、试图回滚既存历史版本拒绝，PDF不按文件名归并。publish(prepared,dry_run=True)只对已编码DTO做只读计划，不写版本/投影；没有免编码dry_run命令。普通CLI/API原入库保持，问答检索只读当前投影。

## 实际验证

项目根.venv/Scripts/python.exe。

| 范围 | 结果 |
| --- | --- |
| 初期离线 | 旧head断言/类型问题修正后基础联合17 passed（11.54秒） |
| 首次真实PG目标 | 3 passed（5.43秒），database-3335db3dbb.txt |
| 数据库首次扩展联合 | 57 passed/27 errors/2 deselected（21.54秒）；旧ingestion/retrieval fixture仍断言p501_0003，修正为p801_0004，保留原迁移链断言 |
| 最终真实PG联合 | **84 passed/2外部项排除（29.10秒）**，database-1a019c80fb.txt；含版本发布/元数据并发/幂等/准备后dry_run/注入失败回滚/旧ID历史读取，及原PG、入库、向量、FTS/RRF回归 |
| 相关离线联合 | **138 passed（25.13秒）**，.artifacts/p801-related.txt |
| CLI/装配联合 | **48 passed（21.27秒）**，.artifacts/p801-cli.txt |
| 质量 | Ruff修正import排序后通过；mypy src 53源文件通过；格式及DDL Demo检查 |

相关离线命令：`-I -m pytest tests/unit/test_knowledge_versions.py tests/unit/test_ingestion_mapping.py tests/unit/test_command_runtime.py tests/unit/test_research.py tests/unit/test_hybrid_retrieval.py tests/integration/test_api.py -q --tb=short --basetemp=.artifacts/p801-related-tmp -o cache_dir=.artifacts/p801-cache`。

CLI联合命令：`-I -m pytest tests/unit/test_command_cli.py tests/unit/test_knowledge_versions.py tests/unit/test_ingestion_mapping.py tests/unit/test_command_runtime.py -q --tb=short --basetemp=.artifacts/p801-cli-tmp -o cache_dir=.artifacts/p801-cache`。各联合范围重叠，不合并为累计通过数。

真实PG命令由 .artifacts/p8-01-20261028/verify_db.py 设置隔离库后运行：`-I -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py tests/integration/test_hybrid_retrieval.py tests/integration/test_knowledge_versions.py -m "database and not external" -q --tb=short --basetemp=<本次唯一目录> -p no:cacheprovider`。数据库仅127.0.0.1、clinical_agent_test_p801和ALLOW_TEST_RESET=1，未碰业务库。

普通沙箱无法检查Docker缓存镜像，获准后使用现有pgvector/pgvector:0.8.7-pg16（image sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a），没有拉新镜像。唯一容器/卷3335db3dbb、首轮扩展及最终1a019c80fb均按本轮标签清理，报告在上述证据目录；未连接现有业务数据库或修改.env。没有模型付费、PubMed联网或真实医学签署。

## 剩余

P8-02：增量游标/失败恢复、简单调度、完整免编码dry_run、跨来源显式别名与固定回归触发；未实现。旧历史报告保留原引用，但本任务只提供内部版本读取，尚无历史报告持久化查询API。真实数据库验收使用合成文献和向量，不能声称医学或真实E5效果通过。[六份学习材料与DDL Demo](learning/phase-08/README.md)已交付。本轮停止。


## P8-02 本地增量运行与恢复（2026-10-28）

完成[任务SPEC](specs/tasks/p8-02-update-runs.md)的本地集合范围：新增UpdateRequest/Result、UpdateService、PostgresUpdateLedger、p802_0005游标/运行迁移、scripts/update_literature.py一次性命令与有界调度入口。每个文件发布后才checkpoint，部分失败不越过文件；文档先提交而游标失败时，从原位置重放并由版本幂等吸收。session advisory lock拒绝同批重入，短事务独立保存游标和逐项结果，运行结果含范围hash、窗口标签和各状态计数。

dry-run复用原PDF/XML只读解析，比较逻辑正文与元数据，不装配Embedding、不创建快照、版本、游标或运行记录。实际XML标题改变时，计划/发布均metadata_updated；修正P8-01以容器hash误判正文变化的问题。窗口标记仅审计，不执行在线查询。固定路径集合绑定batch_id，改变集合/顺序/根目录需新batch；--rescan及调度后续轮重新检查已处理文件。

命令支持--runs 1..100与间隔边界，默认一次；没有创建系统任务、聊天自动化或启动真实长期调度。发布需已有模型/数据库配置；本轮未加载真实E5、未动业务库。--evaluate固定调用已有离线基线脚本，记录passed/not_accepted/failed/not_run，失败不回滚已发布文献；不将旧观察基线当新增文献医学质量评价。

### 实际验证

- 首次离线目标46 passed（8.24秒）；最终受影响离线联合 **75 passed（16.88秒）**，.artifacts/p802-related.txt。范围包括knowledge_update、knowledge_versions、ingestion_mapping、command_cli、command_runtime、ingestion。
- 真实隔离PG联合首轮86 passed/2 deselected（15.41秒）；补发布提交后checkpoint异常场景87 passed/2 deselected（17.84秒）；补真实XML元数据计划/发布一致性后最终 **88 passed/2外部项排除（16.35秒）**，.artifacts/p8-02-20261028/database-44c23d3a5a.txt。各轮重叠不累计。
- 覆盖部分失败cursor停留、恢复只重放失败文件、已完成noop/rescan、dry-run无快照/编码/游标变化、不同PG session锁重入拒绝、评估异常仍保留已提交游标；真实解析+入库+版本存储串联（向量为合成替身）验证提交后异常恢复不增加版本。
- 初次mypy有5项类型错误（联合解析列表、ledger注解等），修正后src **56源文件通过**；Ruff src/tests/alembic/新脚本通过，相关9文件format --check通过。CLI --help已执行，不将帮助输出当真实发布。
- 固定基线实际复算写入evaluation/results/p802-fixed-regression：fresh仍0/2、来源4/4、医学未评价、新模型调用0；退出1正确记录为not_accepted，不算质量通过。

最终PG命令由本次verify_db.py设置唯一隔离库后执行：`-I -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py tests/integration/test_hybrid_retrieval.py tests/integration/test_knowledge_versions.py tests/integration/test_update_runs.py -m "database and not external" -q --tb=short --basetemp=<唯一目录> -p no:cacheprovider`。

离线命令：`-I -m pytest tests/unit/test_knowledge_update.py tests/unit/test_knowledge_versions.py tests/unit/test_ingestion_mapping.py tests/unit/test_command_cli.py tests/unit/test_command_runtime.py tests/unit/test_ingestion.py -q --tb=short --basetemp=.artifacts/p802-related-tmp -o cache_dir=.artifacts/p802-cache`。未重复无关全量。

只使用缓存pgvector/pgvector:0.8.7-pg16；三次唯一容器/卷d52a0e87cb、6e68387615、44c23d3a5a均按本次标签清理，报告container_removed/volume_removed均true。无新付费/联网调用，没有迁移业务库或修改.env。旧数据库测试只更新当前head断言为p802_0005，保留历史迁移链校验。

学习与可运行示例见[update-runs.md](learning/phase-08/update-runs.md)。发布/计划主路径已用真实PG和真实解析器验证，但尚未以真实E5/用户业务数据/真实长期间隔调度验证；跨进程能力依据PG session锁测试，不声称进行了OS强杀恢复实验。

### Phase8仍待完成

本任务不是Phase8全部验收：显式跨来源别名/歧义冲突与撤回更正状态治理、在线PubMed增量适配、显式模型/分块重建尚未实现，需后续P8-03细化。历史报告持久化查询API仍无。Phase7真实模型响应错误与医学人工缺口保留，不进入Phase9。本轮停止。

## P8-03 来源别名与状态治理（2026-10-28）

用户明确启动后按规则/进度/主SPEC/本验收及相关源码测试核对，先冻结[细任务SPEC](specs/tasks/p8-03-source-governance.md)，再写测试与最小实现，末尾集中验收。没有改动历史通过结论、业务库或.env。

### 实现及文件

- domain/governance.py定义显式依据、标识规范化、状态与CAS请求。adapters/postgres/governance.py登记别名、返回原生+显式候选集、并发幂等及冲突查询；不自动选择归属、归并文档或重写历史chunk。
- models.py和p803_0006_source_governance.py新增source_aliases、source_status_events、source_states。标识事务锁串行化登记，文档行锁与发布协调；事件ID锁避免跨文档复用，expected_event_id拒绝过期修改。事件和投影同事务，异常回滚。相同事件载荷重放不覆盖后续新状态。
- postgres/retrieval.py对三模式统一执行阻断状态NOT EXISTS；状态通过文档outer join在同一只读REPEATABLE READ快照hydration，不增加原vector三次/hybrid四次数据查询。
- domain/retrieval.py、domain/research.py、domain/report.py保留governance字段到CitationSource、分析模型上下文及报告JSON/Markdown。状态不改变来源content_hash/原文/版本；正文更新不清除来源状态。
- scripts/govern_sources.py支持claim/status有界JSON、resolve和inspect，不装配模型或自动联网。相关新单元/真实PG测试、旧迁移head断言已更新到p803_0006，保留旧down_revision链校验。
- 本SPEC、进度、CLI说明、六份Phase8学习材料补充及[source-governance.md](learning/phase-08/source-governance.md)、离线governance_demo.py。

### 实际集中验证

统一使用项目.venv/Scripts/python.exe，证据目录.artifacts/p8-03-20261028/。

| 范围 | 实际结果 |
| --- | --- |
| 初次沙箱Docker检查 | 无法访问缓存镜像，未创建测试容器/卷，未运行DB测试；随后获准使用隔离helper |
| 首轮真实PG联合 | 89 passed/5 failed/2 deselected（25.97秒），database-46da157d90.txt；两项旧查询次数断言揭示新增读取，三项新fixture漏request_id；真实失败如实保留 |
| 修复 | 将状态改为文档outer join保持原查询次数，补fixture ID，新增状态投影异常时事件/投影一起回滚测试 |
| 最终真实PG联合 | **95 passed/2外部项排除（46.87秒）**，database-e2e2f7e276.txt |
| 初次相关离线 | 154 passed（14.88秒），.artifacts/p803-offline.txt |
| 最终受影响离线 | **212 passed（23.76秒）**，.artifacts/p803-final-offline.txt，覆盖新增治理契约和原检索/版本/入库映射/分析/引用报告/问答/命令装配；范围重叠不相加 |
| 质量 | Ruff src/tests/alembic/治理脚本通过；11个实现/新测试/迁移文件format检查通过；mypy src58源文件通过；脚本--help及离线Demo运行通过 |

真实PG命令由本轮verify_db.py注入隔离配置：`-I -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py tests/integration/test_hybrid_retrieval.py tests/integration/test_knowledge_versions.py tests/integration/test_update_runs.py tests/integration/test_source_governance.py -m "database and not external" -q --tb=short --basetemp=<本次唯一目录> -p no:cacheprovider`。覆盖并发别名幂等、跨文档同DOI冲突、原生PMID/hash身份保护、规范化原生DOI查询、事件重放/ID冲突/过期CAS/并发CAS、三种阻断状态×三种检索模式、更正状态传到引用、更新后状态和旧版本仍保留、未知文档无写、迁移down/up与写失败原子回滚。

最终离线命令：`-I -m pytest tests/unit/test_source_governance.py tests/unit/test_knowledge_update.py tests/unit/test_knowledge_versions.py tests/unit/test_ingestion_mapping.py tests/unit/test_retrieval.py tests/unit/test_hybrid_retrieval.py tests/unit/test_citation_report.py tests/unit/test_evidence_analysis.py tests/unit/test_research.py tests/unit/test_command_runtime.py -q --tb=short --basetemp=.artifacts/p803-final-tmp -o cache_dir=.artifacts/p803-cache`。

Docker仅复用缓存pgvector/pgvector:0.8.7-pg16，image sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a，唯一clinical_agent_test_p803数据库。实际运行46da157d90、e2e2f7e276各自容器/卷均已按本轮标签清理，database-run-*.json记录removed=true。无业务库迁移、真实E5、模型付费或PubMed外网调用；两项external明确排除，未声称通过。

### 未完成与限制

本地治理核心工程验收通过，不标Phase8全部完成。来源状态为操作者提交依据的断言，系统未下载/验证notice、哈希或医学含义；合成测试不证明真实撤稿识别正确。状态不跨别名传播，不拦截online或hybrid在线副本；正在执行的请求使用其开始时的快照。corrected保留可检索，不代表更正后的论断已被人工确认。历史报告不实时重写当前状态。

别名唯一resolved不表示身份真实性；本次没有人工冲突裁决、撤销/修改别名依据接口；当前冲突可inspect/resolve供人工检查，不自动归并。业务环境需操作者显式升级迁移后使用，未实际部署治理命令。P8-04在线增量适配、P8-05显式模型/分块重建仍未实现；Phase7真实E2E和医学人工签署缺口保持，不进入Phase9。学习材料与运行Demo交付，本轮停止。

## P8-04 / P8-05 收尾与Phase8维护核心（2026-10-28）

用户明确要求完成Phase8；以当日本地规则/进度/SPEC/验收及源码测试为准，先冻结[收尾范围](specs/tasks/p8-completion.md)，先写核心契约与真实PG测试，再完成在线窗口和显式重建，并在末尾集中验收。后续边界修正和补测的实际结果分别记录，不改写原历史。基于Phase7已实现技术基线开展，不把Phase7真实报告或医学待审改为通过。

### 实现及修改文件

- domain/maintenance.py定义显式在线窗口、范围签名与RebuildRequest；domain/governance.py统一解释官方状态标签方向。
- application/online_updates.py、postgres/maintenance.py实现完整窗口门禁、冻结结果、哈希XML、恢复和metadata_only审计，复用UpdateService/UpdateLedger/原解析和E5入库。partial/truncated/缺条目不标完整，不越过失败文件；相同batch范围变更拒绝，重叠窗口幂等。
- postgres/online_publication.py、versions.py在同一发布事务登记官方来源状态；状态写失败，文献/chunks/版本也回滚。application/updates.py增加成功发布后的明确hook，失败不推进游标。无摘要通知可更新已有来源状态，不伪造摘要。
- postgres/governance.py的statuses_for_pmids与application/pubmed.py、command_runtime.py、api_runtime.py接入精确已知PMID状态，在线副本不能绕过已登记阻断；官方明确阻断状态也过滤。hybrid保留两侧治理提示，别名不隐式传播。
- postgres/rebuild.py实现全库一致快照、事务外分块/编码、rebuild_runs隔离payload、临时schema中真实vector/FTS/hybrid检查、显式activate、来源集合签名和原子整体切换；失败/来源变化保留旧索引。旧版本/chunk和治理状态保留；激活重放幂等。
- models.py和p804_0007_maintenance.py新增online_update_batches/rebuild_runs；旧迁移链与head断言同步维护。没有迁移业务库。
- scripts/sync_pubmed.py、rebuild_knowledge.py提供显式命令；update_literature.py与IngestionCommand补充可选--max-tokens，重建后维护可显式匹配预算，默认512不变。无自动模型下载、后台任务或新依赖。
- 新单元/集成测试、SPEC/进度/README/架构/CLI说明、六份Phase8教材补充及[maintenance.md](learning/phase-08/maintenance.md)、maintenance_demo.py。

### 实际验证与故障记录

项目根.venv/Scripts/python.exe，证据目录.artifacts/p8-completion-20261028/。

| 范围 | 实际结果 |
| --- | --- |
| 初期目标离线 | 108 passed（22.12秒），.artifacts/p8complete-unit.txt；尚不含后补在线副本门禁/预算测试 |
| 首轮隔离PG | 97 passed/2 deselected（33.24秒），database-d3434d4590.txt |
| 状态原子性/恢复补强 | 98 passed/2 deselected（54.59秒），database-e1e04fccc5.txt |
| 最终隔离PG联合 | **98 passed/3外部项排除（30.25秒）**，database-b79d17b679.txt；外部项不算通过 |
| 受影响离线联合 | **263 passed/1外部项排除（12.29秒）**，.artifacts/p8complete-related.txt；后补维护预算装配测试纳入最终默认回归，不混入263计数 |
| 官方小冒烟 | 普通沙箱pubmed_failed，保留official-smoke-sandbox.json；获准访问官方后指定PMID26551272在2015-11-01至11-30 edat窗口完整返回1条，official-smoke.json/official-window.json；没有模型调用 |
| 首次真实模型/PG链路 | **1 failed（314.58秒）**，database-22d3caf708.txt；加载缓存E5超过原300秒上限，未进入在线入库。helper读控制台编码另有UnicodeDecodeError，但finally完成容器/卷清理，测试失败未当通过 |
| 串行真实PubMed+E5+PG | **1 passed（67.15秒）**，database-5d98ace179.txt；pinned真实本地E5，限制本轮CPU线程，不放宽300秒加载限制，不下载模型。结果official-pipeline-result.json |
| 固定评价回放 | evaluation/results/phase8-completion：退出1/baseline_not_accepted，fresh报告仍0/2，真实来源离线回放4/4，医学指标null，新增模型调用0；是历史回放，不把维护链路成功当Phase7报告成功 |
| 质量与Demo | Ruff src/tests/alembic及三维护脚本通过；20个相关实现/测试/迁移/脚本/Demo格式检查通过；mypy src63文件通过；三个脚本--help与离线maintenance_demo.py通过 |

最终默认回归：`-I -m pytest -vv --tb=short --durations=5 --basetemp=.artifacts/p8complete-final-default-tmp -o cache_dir=.artifacts/p8complete-cache`，本轮OMP/MKL线程2，结果 **1243 passed/1 failed/122 deselected/1既有SDK警告（250.13秒）**，.artifacts/p8complete-final-default.txt。唯一失败是tests/unit/test_postgres.py旧断言仍要求ORM仅documents/chunks两表；更新为当前10表，原向量维度/DDL/DTO隔离断言保留。修正后受影响联合 **277 passed/1 deselected（20.63秒）**，.artifacts/p8complete-final-related.txt。随后补快照临时文件+fsync+原子rename和写失败清理测试，最终受影响联合 **278 passed/1外部项排除（24.39秒）**，.artifacts/p8complete-final2-related.txt；仅重跑受影响范围，没有将前次默认失败批次或新增测试改算为1244/1245全量通过。最后在线冻结/发布/恢复数据库目标 **1 passed（6.94秒）**，database-77ad56eab0.txt。

最终相关联合是在前述263命令基础上增加tests/unit/test_postgres.py，使用--basetemp=.artifacts/p8complete-final2-related-tmp；目标DB命令为tests/integration/test_phase8_completion.py::test_online_real_db_freezes_and_replays。最后业务变更仅快照原子落盘，已被新单元和该PG目标覆盖。维护预算装配测试也在278中实际通过。最终mypy63源文件、Ruff与21文件格式检查通过。前两次较宽回归中止：第一次并行资源争用时进度有2个F，未生成最终失败栈/计数，未认定原因或通过；第二次串行诊断至约75%未重现早期失败后中止，也不计完成。上述部分日志保留p8complete-regression.txt及p8complete-firstfail.txt。最终默认批次改为串行、限制本轮OMP/MKL线程并记录逐项结果。

核心PG断言覆盖：真实官方格式MockTransport→冻结→解析→PG发布，官方状态写入故障整文档回滚；文档/状态提交后checkpoint故障恢复不重新联网、不增加版本；已完成重放与重叠窗口幂等；同batch改范围拒绝；精确PMID当前状态查询；stage不影响旧活跃chunk；not_accepted拒绝激活；真实隔离schema检索检查；切换写入异常回滚、重放和来源集合变化拒绝；未知模型在编码前拒绝。P8-01–03原PG/版本/治理/本地更新/检索回归同时运行。

真实依赖单例：从官方PubMed获取PMID26551272，使用缓存intfloat/multilingual-e5-base@d128750597153bb5987e10b1c3493a34e5a4502a校验/加载并真实编码，实际入库/检索，256-token重建通过隔离PG检查，激活后可检索、旧版本chunk IDs原样回读。没有LLM、自评医学标签或付费模型调用；不声称该单例证明医学质量、广泛召回或全网检全。

最终真实PG命令：`-I -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py tests/integration/test_hybrid_retrieval.py tests/integration/test_knowledge_versions.py tests/integration/test_update_runs.py tests/integration/test_source_governance.py tests/integration/test_phase8_completion.py -m "database and not external" -q --tb=short --basetemp=<本轮唯一目录> -p no:cacheprovider`。

真实模型命令由verify_live.py注入专用配置：`-I -m pytest tests/integration/test_phase8_completion.py::test_official_window_real_e5_and_database_rebuild -m "database and external" -q --tb=short --basetemp=<本轮唯一目录> -p no:cacheprovider`。

相关离线命令：`-I -m pytest tests/unit/test_phase8_completion.py tests/unit/test_knowledge_update.py tests/unit/test_knowledge_versions.py tests/unit/test_source_governance.py tests/unit/test_ingestion_mapping.py tests/unit/test_retrieval.py tests/unit/test_hybrid_retrieval.py tests/unit/test_pubmed_online.py tests/unit/test_citation_report.py tests/unit/test_evidence_analysis.py tests/unit/test_research.py tests/unit/test_command_runtime.py tests/unit/test_api_runtime.py tests/integration/test_pubmed_online.py -m "not database and not external" -q --tb=short --basetemp=.artifacts/p8complete-related-tmp -o cache_dir=.artifacts/p8complete-cache`。

全部本轮实际容器/卷d3434d4590、e1e04fccc5、22d3caf708、5d98ace179、b79d17b679、77ad56eab0已按唯一label核对清理，database-run-*.json保留removed=true。仅缓存pgvector/pgvector:0.8.7-pg16、image sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a；只连127.0.0.1临时clinical_agent_test_p8complete，不动用户业务库/.env，不运行长期调度。

### 完成范围及保留限制

**Phase8本次冻结的维护核心开发与工程验收完成。** 覆盖P8-F01–05及T01–06在当前固定架构下的必要场景，教材/命令已交付；默认回归旧断言失败及修复后定向结果如实保留，不标原失败批次全量通过。窗口最多31天/20条且edat不代表所有历史修订；全库重建最多100文档，仅既定E5/768维及source-unit-v1，不支持通用模型/维度迁移。别名冲突供人工检查，不做自动消解或物理合并；没有新增历史报告持久化查询API或Phase9完整评价平台。

工程自检与真实依赖通过不替代医学判断。Phase7冻结fresh报告仍0/2，医学人工支持关系/方法/相似性/缺口审定与旧阶段签署继续待审。未部署业务环境、未承诺定期同步或生产性能；不得将本次维护验收改写为整个科研报告产品或医学质量验收通过。本轮范围完成后停止，不进入Phase9。
