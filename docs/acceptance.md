> 当前版本集中验收见 [2026-11-02记录](acceptance/consolidated-20261102/README.md)：限定技术范围通过，整体质量验收仍部分通过。下文2026-11-01失败与未验证事实保留，不被新结果改写。

# 2026-11-01 专项验收

## 结论

公开 local 退役、类型治理和开发文档重建的离线技术门槛通过。整体正式验收尚未通过：真实 OpenAlex 全文获取冒烟失败；本轮未部署当前源码、未发送飞书消息、未完成医学人工签署。不得据此标记新 Phase 或项目整体完成。

环境：Windows、PowerShell、仓库 .venv Python 3.12；本机 Docker PostgreSQL/pgvector、临时 Redis 8.2.2；真实模型 API 使用已有配置，仅发送虚构教学证据。所有秘密仅在进程环境中处理。

## 实际结果

| 检查 | 实际命令/环境 | 结果 |
| --- | --- | --- |
| 完整离线 | `.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/governance-final -o cache_dir=.artifacts/tmp/governance-final-cache` | 1588 passed、100 deselected、1 SDK 弃用警告，272.77 秒 |
| 受影响专项 | 相同 pytest，选择 agents/api/citation/exploratory/feishu/rag-db/CLI/retired-local 八个测试文件 | 166 passed，70.49 秒 |
| 类型 | `.venv/Scripts/python.exe -X utf8 -m mypy src` | 标准配置 77 个源码文件无错误；不是原 strict 配置通过 |
| 静态 | `.venv/Scripts/ruff.exe check src tests`；`git diff --check -- src tests pyproject.toml README.md` | 通过 |
| 锁文件 | `.venv/Scripts/uv.exe --cache-dir .artifacts/tmp/governance-uv lock --check --offline` | 139 个依赖解析通过 |
| 真实 PDF 入库 | `python -X utf8 .artifacts/governance/run-real.py`，新建独立库 clinical_agent_test_governance_20261101_retry1；显式 Alembic upgrade head；选择 API/CLI pipeline 文件并 `-m database` | 2 passed，145.01 秒；真实 E5、PG、loopback Uvicorn；PDF imported/already_present，local HTTP 422/CLI 2；未执行在线问答 |
| Redis 与飞书内部调度 | `python -X utf8 .artifacts/governance/run-redis.py`，临时容器、独立端口56379、随机键前缀 | 13 passed，4.70 秒；容器已停止并自动删除；未调用飞书真实发送 |
| 真实模型 API | `python -X utf8 .artifacts/governance/run-live.py`，test_research_live.py，`-m external` | 1 passed，8.40 秒；隔离检索替身、合成证据；非全链路或医学验收 |
| OpenAlex 搜索/全文 | `python -X utf8 .artifacts/governance/run-openalex.py`，MedSAM、最多两篇获取、50秒预算 | 搜索返回10条、快照身份校验通过；全文未获取，分别 fulltext_no_fulltext_url / fulltext_budget，脚本退出1 |
| 学习 Demo | `python -X utf8 docs/learning/current/demo.py` | online 接受、local 在资源前拒绝 |

[原始证据目录](acceptance/evidence/)同时保存初次失败与最终日志；执行脚本副本可检查具体命令。复跑数据库脚本需使用新的专用库名，脚本拒绝复用未知已有库。两个本轮创建的测试库保留供审阅，不修改业务库，不自动删除其数据。OpenAlex fulltext_budget 可表示时间、大小或请求等预算，不将其误写为确定网络故障。

## 本轮失败与处理

- 首轮离线：10 failed、1584 passed、100 deselected。旧 OpenAPI/入口断言和历史 AST 源码快照与本次已授权改动冲突；修正后专项与最终回归通过。未删除失败日志。
- 6 项历史 AST 相等参数退出当前冻结范围：5 个 integrations 模块和飞书 sender。本次修改已超出当时“仅移动导入”的假设，不能要求源码永远等于历史 AST；其快照、行为测试、导入隔离检查保留。测试总数下降包含这6项退出，不是新增6项行为通过。OpenAPI 快照仅调整 QuestionBody scope，保留其余完整比较。
- 初次真实环境：缺少本地数据库密码环境、默认端口超时；从容器内存环境取得凭据和实际55522端口后改用专用库。
- 首次真实入库：2 failed，旧测试硬编码 p107_0002，而实际迁移 head 为 oa3003_0011；将断言同步到当前版本后2项通过。
- 首次 Redis：2 failed、11 passed。一个 owner 隔离测试的250ms租约不足覆盖本机Docker多次往返；仅该非过期场景改用5秒租约，过期测试保留。另一个替身只实现answer，当前Dispatcher调用respond，且缺少线上检索来源；按现有契约补齐后13项通过。生产Redis/工作逻辑未改。
- 真实全文获取仍失败，未通过放宽大小/超时、安全和身份门禁掩盖问题。

## 类型和文档治理范围

原 strict 检查180条错误包含强制所有函数注解、泛型实参等要求。本轮改为标准 mypy 加 check_untyped_defs、warn_unused_ignores、warn_redundant_casts；仅对无stubs的defusedxml第三方导入允许缺失类型。没有按模块忽略项目错误。修复变量类型复用、JSON上下文推断、受上游Pydantic约束的日期/身份类型收窄、URL类型和文本节点类型。Any与cast的局限见开发文档，不声称实现了全源码严格类型证明。

旧 docs 全量移出当前目录，存于 history/docs-20261101，历史事实原文保留。根 README 旧版也存档。更新测试读取历史样例的位置，断言不因归档被删。当前文档从源码重写，学习材料位于 docs/learning/current。

内部历史 DTO 的 local、隔离测试替身和来源格式暂留；公开输入不再接纳 local。PDF 入库与在线论文缓存保留。online/hybrid 均沿当前在线发现流程，不宣称联合召回。

## 未完成门槛

1. 真实全文成功获取、缓存入库、再次查询复用及问答/分析/报告联合端到端未完整复验。
2. 当前工作区未部署；此前健康容器不能作为当前代码部署通过证据。业务库两条迁移未在本轮执行。
3. 飞书用户实收未执行；发送队列/租约内部集成不能替代用户实收。
4. 独立医学人工审核与签署未完成；不声称覆盖最新研究或临床正确。
5. 默认排除的100项未整体运行，仅单独执行本表列明的真实依赖子集；其余不计通过。性能测试、全套历史数据库测试和远端CI未执行。

本轮停止，不进入下一阶段。

文档收尾验证：当前 Markdown 相对链接均可解析；重建文档后运行 test_active_python_has_no_legacy_imports，1 passed（0.99 秒）；Ruff src/tests 再次通过。
