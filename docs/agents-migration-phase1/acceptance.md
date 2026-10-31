# Agents 结构迁移 Phase 1 实际交付（2026-10-31）

本轮仅完成用户确认的Agents迁移。相对Phase0的结构兼容专项门槛已满足；完整离线回归仍有29个原有失败，整库未通过，未进入Phase2。未部署、未迁移数据库、未调用真实外部服务，不代表医学验收。

## 当前执行链与修改依据

原入口/runtime → ResearchService.__init__创建角色 → agents.graph.build_research_graph注册绑定节点与路由并compile → respond/answer/analyze/report按请求创建state、invoke并验证结果。application业务方法继续负责超时、上下文准备、生成、引用、反馈和输出，agents节点继续调用原业务组件。

原research构造函数混合业务依赖与Graph组装，原workflow和agents承载状态及角色，具有独立迁移依据。没有重写算法或引入新框架。

## 实际文件映射

- application/workflow.py原实现→agents/state.py；原路径保留三个TypedDict同对象重导出。
- application/agents.py原实现→agents/nodes.py；原路径保留六角色、RetrievalPort、remaining、steps同对象重导出。
- application/research.py只调整导入并将注册编译部分提取为agents/graph.py；新增agents/__init__.py。构建函数以TYPE_CHECKING引用ResearchService，运行时没有反向导入；LangGraph仍在构建时导入。
- 新增tests/unit/test_agents_migration.py、tests/fixtures/agents/phase0-contracts.json、阶段SPEC/本记录/执行日志以及docs/learning/phase-01/agents-migration教材。
- 仅向当前架构与状态表追加本次记录。没有删除任何文件；已有未提交业务改动以现场内容保留，未从Git HEAD恢复。git diff对HEAD包含用户既有改动，不能全部归为本轮。

## 兼容性检查

双拓扑完整节点和边与Phase0一致：无Planner12节点16边；有Planner14节点20边（含START/END）。State字段、类型和必需性一致；ResearchService构造和四个公开方法签名一致，仅角色Protocol及State类型显示路径随迁移变化。旧新对象身份相同；未承诺序列化类型的__module__字符串不变。

OpenAPI完整相等；API、CLI、飞书、数据库、HTTP、Embedding所有权保持原位，未增加导入时资源创建。四项新模块隔离导入通过。反馈轮数、递归上限、预算、异常映射、业务提示词和既有结果处理未修改。

## 环境与实际验证

Windows PowerShell，仓库.venv Python3.12.16，-X utf8。真实依赖使用既有Fake/Mock隔离；pytest默认排除external/performance/database/redis。

1. 初始新增测试：3 passed、2 failed。失败来自迁移后类型显示路径变化以及跨进程默认函数地址差异；修正对比仅允许两处迁移模块路径和函数地址变化。
2. 全量命令：`.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/agents-phase1 --junitxml=docs/agents-migration-phase1/full.xml`，stdout保存在full.txt。实际 **1484 passed、30 failed、122 deselected、0 skipped、0 errors，154.29秒**。对比Phase0：原29失败身份全部相同，新增1项为test_public_signatures_and_api_unchanged的地址归一化测试缺陷。
3. 隔离导入补充后专项第一次8 passed、1 failed：占位字符串0xADDRESS的十六进制前缀被再次替换，属于新增测试的比较错误，业务代码未改。记录contracts.xml保留失败。
4. 修复正则为只匹配函数repr中紧邻右尖括号的实际地址后重跑受影响的全部迁移测试：`.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_agents_migration.py -q --basetemp=.artifacts/tmp/agents-phase1-contracts-fixed --junitxml=docs/agents-migration-phase1/contracts-fixed.xml`，**9 passed，8.03秒**，见contracts-fixed.txt/xml。该9项包含双拓扑、State、签名/OpenAPI、旧新对象及四项隔离导入。未再次全量，不能把full.xml中的失败改写为通过；最终无新增未解决失败。
5. `.venv/Scripts/ruff.exe check src tests`通过。首次兼容重导出import排序失败已修复，再检通过。
6. `.venv/Scripts/python.exe -X utf8 -m mypy src --no-error-summary`失败，193条错误。与Phase0按迁移路径及行号归一后新增0、消失0，详见mypy.txt；不标类型检查通过。
7. src/tests/scripts/alembic共192个Python文件AST解析通过；本轮源码git diff --check通过。学习Demo及两个模块入口--help退出成功，见demo.txt、cli-help.txt、feishu-help.txt。

## 防御逻辑与资源审查

新增生产代码只有Graph装配及兼容重导出，未新增异常捕获、默认返回、重试、资源对象或通用抽象。原有必要异常/超时/引用校验保持不动。Graph函数直接依赖服务的私有节点属于有意保留的内部耦合，不为目录调整额外创建Protocol或Factory。

## 剩余问题与下一任务

原29失败（8个PubMed契约、21个local范围冲突）及193条类型错误继续开放；scripts的17个既有Ruff错误不在本轮修改范围。真实数据库/Redis、模型、OpenAlex、飞书端到端及医学人工签署未验证，122项排除不计通过。旧模块兼容导出继续保留，删除须另获明确确认。

下一任务候选为用户确认后的架构Phase2 API整理；本轮停止。教材包括六份导航/教程/走读/练习/面试/排错及可运行Demo；不替代历史业务Phase1验收。
