# Phase 1 MVP阶段验收报告

历史记录说明（2026-10-27）：本文供应商专属模块、配置和实测结果属于任务交付时点。当前已移除专属适配器，统一使用 `adapters/llm.py` 的 `LLMSettings/open_llm` 和 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`，详见通用模型边界 SPEC；旧变量不会回退读取，迁移后未新增在线验收。

日期：2026-10-27；任务P1-17。**技术验收与学习材料已交付；按用户选择保留医学人工审查待完成，P1-17/Phase1尚未完成。**

## 范围与事实来源
规则为AGENTS.md.txt/PROJECT.md.txt，需求为specs/01-mvp.md，实施约束见[SPEC](specs/tasks/p1-17-mvp-acceptance.md)。基于当前仓库源码和测试；不采用聊天中的旧结论。未改现有架构、业务服务、去重算法或依赖。保留原有未提交改动。

## 需求与证据映射
| 需求/场景 | 当前对应证据 | 边界 |
| --- | --- | --- |
| F01、T01/02/03 | DTO/PDF/XML单元及离线集成 | 本地导入，不在线检索或OCR |
| F02、T04 | chunking/embedding单元与固定E5 CPU外部测试 | 不等于医学召回质量评估 |
| F03、T05 | 真实PG迁移/事务/并发/检索测试 | 专用测试库，非生产库 |
| F04、T06 | ResearchService真实图替身测试及真实研究闭环 | 无证据与生成错误严格区分 |
| F05、T06 | 引用门禁、切片回建及人工审核资料 | 标识门禁不证明医学语义支持 |
| F06、T07 | CLI/API真实E5/PG、飞书共享服务测试 | CLI/API协议测试LLM为明确替身 |
| F07、T08/09/10 | 事件/worker/sender/main及真实Redis组合 | 不承诺exactly-once |
| F07、T11 | P1-16真实SDK收发、Linux Compose证据；P1-17真实E5/PG/LLM | 不把分项合成测试称为真实医学飞书整链路 |

P1-16历史证据：.artifacts/p1-16-20261027/live-external-published.txt（1 passed/34.38秒、合成研究）；compose-accept-result.json及compose-accept-api/feishu_bot.log（Linux镜像/迁移/API空库/SDK连接/关闭）。本轮不伪称重新运行这两项，也不发送未授权的医学飞书消息。

## 实际执行与测试结果
全部命令使用显式项目解释器；PYTEST_ADDOPTS/PYTEST_PLUGINS在测试子进程移除，独立basetemp/cache，UTF-8日志；证据.artifacts/p1-17-20261027/。

| 检查 | 实际结果/证据 |
| --- | --- |
| 学习交付RED→GREEN | red.txt：1 failed（缺学习README）；learning-green.txt：1 passed；补六份教材与真实图/引用门禁离线demo |
| 安全补丁配置RED→GREEN | patch-red.txt：1 failed（.python-version为3.12.15）；最终deployment检查通过 |
| 原3.12.15默认回归 | 1024 passed/95 deselected；regression.txt，135.15秒 |
| 3.12.16候选默认回归 | 1024 passed/95 deselected；py31216-regression.txt，177.78秒（早于新增安全版本测试） |
| 最终正式环境默认回归 | 1025 passed/95 deselected/1 SDK弃用警告，266.94秒；final-regression.txt |
| 真实PG | 原环境及3.12.16各74 passed；database.txt/py31216-database.txt；迁移、事务、回滚、并发、向量 |
| 真实Redis与worker/sender组合 | 原环境及3.12.16各13 passed；redis.txt/py31216-redis.txt；重复、饱和不占位、真实发送交接和排空 |
| 真实E5/CLI/API/PG | 原环境5 passed；model-cli-api.txt。候选首次组合4 passed/1 failed，独立检索复验1 passed；串行诊断/修复后5 passed；py31216-lifecycle-model-cli-api.txt，失败记录单列保留 |
| 合成PDF真实E5/PG/DeepSeek | 1 passed，36.21秒；real-pipeline.txt，pipeline-result.json；空库不调用LLM、重复入库与引用切片核对通过 |
| 固定真实PubMed摘要+E5/PG/DeepSeek | 1 passed，61.97秒；py31216-real-pipeline.txt、medical/pipeline-result.json；摘要来源/切片核验通过，不等于人工医学审核通过 |
| Ruff/format/mypy/锁/安装一致性 | 候选Ruff/84文件格式及锁/104包pip通过；mypy独立新缓存38源码通过。正式环境Ruff通过、84文件格式通过、mypy38源码通过、106锁定包检查及104安装包一致性通过；final-*.txt |
| Linux3.12.16共享镜像 | 构建、版本、help、pip check、非root、无凭据/代理ENV通过；docker-candidate-check.json |

升级后隔离Compose API复验：真实PG迁移、只读本地E5、runtime ready、空库insufficient_evidence/空claims/sources、非root与SIGTERM关闭均通过；API exit143伴随Application shutdown complete/Finished server process且无OOM。0次LLM调用。项目clinical-p117-compose-20261027的容器/测试卷/网络均已清理，证据compose-smoke-result.json/compose-smoke-api.log。首次辅助脚本日志解码使用GBK导致断言采集失败，修正为显式UTF-8后重跑通过，旧失败compose-smoke-result-encoding-failed.json保留；未改产品或放宽关闭判据。本轮未重发飞书消息，真实SDK收发仍引用P1-16历史证据。

实际核心命令（服务环境仅指本轮独立测试库/Redis，需按教材明确配置，不可指向业务库）：

```powershell
& .venv/Scripts/python.exe -m pytest
& .venv-p117/Scripts/python.exe -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py -m 'database and not external'
& .venv-p117/Scripts/python.exe -m pytest tests/integration/test_feishu_dedup_redis.py tests/integration/test_phase1_acceptance.py -m redis
& .venv-p117/Scripts/python.exe -m pytest tests/integration/test_embedding_real.py tests/integration/test_command_pipeline.py tests/integration/test_api_pipeline.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py -m external
# 以下已完成两次授权样例，不自动重跑（会付费）：
# python -m pytest tests/integration/test_phase1_acceptance.py -m 'external and database'
& .venv/Scripts/python.exe -m ruff check src tests alembic docs/learning/phase-01/demo.py
& .venv/Scripts/python.exe -m ruff format --check src tests alembic docs/learning/phase-01/demo.py
& .venv/Scripts/python.exe -m mypy src --cache-dir .artifacts/p1-17-20261027/final-mypy-cache
& .venv/Scripts/python.exe -m uv lock --check --offline
& .venv/Scripts/python.exe -m uv pip check
```

模型/LLM使用固定输入和本地E5 revision；DeepSeek为供应商模型别名，未声称不可变远端模型版本或任意医学问题准确率。SDK弃用警告未全局屏蔽，私有兼容接口后续升级仍须复验。

付费请求累计2次（合成PDF1次、固定真实摘要1次），均为用户授权范围；之后不再执行付费测试。仅白名单读取.env中的DEEPSEEK_API_KEY/MODEL到子进程内存，不保存密钥。默认排除的真实服务/性能项不算通过；本轮未新增性能评估平台。

首次候选mypy复用旧缓存发生INTERNAL ERROR，使用独立新缓存后完整检查通过；旧失败保留py31216-mypy.txt。首次候选五项模型测试在并行默认回归/镜像构建期间最后一次模型加载失败（embedding_load_failed），独立进程同测试通过；不能仅凭时间相关性声称已证明根因。串行复验仍失败，诊断包装捕获safetensors.safe_open抛Windows os error1455（页面文件不足），不是已证明的解释器不兼容。为五项真实模型测试及新闭环增加显式release_model_memory夹具：恢复测试patch后gc.collect回收已结束的模型/ASGI/图循环引用；同一组合最终5 passed（80.74秒，py31216-lifecycle-model-cli-api.txt）。不改系统页面文件、生产模型配置、预算、依赖或断言。新建测试容器在finally中按唯一名称清理；不删除此前任务的Redis容器。

## 人工医学支持关系审查
**待有资格的人工审查者签署，不以AI自行核对代替。**
已经冻结NCBI官方PMID26551272原始XML及SHA256，并通过真实E5/PG/DeepSeek生成10条claims，原始答案/来源片段在medical/pipeline-answer.json；合成教学样例另存pipeline-answer.json。逐论断审查表见[人工审查包](phase1-medical-review.md)，含实际文本、chunk_id、摘要章节/字符区间及待签署栏。AI预核对仅提示c5限制分类、c9术语/背景时间范围和c10范围推论，不代替人工结论。

用户已明确选择“先保留待人工审查状态”。因此不填写虚构审查人，不将真实LLM/引用自动检查通过写成医学支持关系已验收。

## Python构建前置条件
开发解释器与Dockerfile已升级至3.12.16；原.venv保留为.venv-p117-prior，不修改共享Conda。官方[Python安全发行](https://www.python.org/downloads/release/python-31216/)与[standalone20261026](https://github.com/astral-sh/python-build-standalone/releases/tag/20261026)已核查。uv0.13.5内置清单仍最高3.12.15，不能用其旧清单否认官方新构建；GitHub API限流后通过官方release HTML发现资产。先前猜测单资产.sha256 URL不存在，未使用未校验构建；改从发行页实际列出的SHA256SUMS校验后才解包。Windows资产SHA256为1f2ab53880fc67ea323398c6388e05af28addc99a8e389209f08a51fdff4b149。

Linux官方基础镜像python:3.12.16-slim-bookworm的linux/amd64 digest为72c1d56207fb14ca388f9b3855ac0e55ab557703928180ec40aa9d4c4f5d5f80；候选镜像/依赖验证详docker-candidate-check.json。使用既有本机代理临时环境访问官方registry/包源，未改系统全局代理、未关闭TLS、未将代理或凭据写入镜像。P1-16的Compose运行/真实SDK收发是历史独立证据，本轮镜像升级不冒称已重新收发真实消息。

## 学习材料和设计取舍
[学习导航](learning/phase-01/README.md)包括六份材料及[离线Demo](learning/phase-01/demo.py)，解释来源/位置、固定tokenizer、单文档原子事务、必要图分支、可信引用、有界线程/发送与owner TTL。没有增加Phase2任务平台、实时检索或自动语义核验。

## 阶段判定与下一步
已补齐可执行技术验收与学习材料；人工医学支持关系审查未签署，P1-17/Phase1保持验收中。下一步仅完成该人工审查并据结果修复/复验，不自动进入Phase2。
