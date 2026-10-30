# 全量文档分类与处理清单

适用范围：治理前175份文档，逐文件登记；JSON及Python等非叙述性材料另见完整树与机器清单。每行说明用途、阶段、类型、有效范围、证据归属、重复处理、链接及最终路径。标题取正文首标题，不依据文件名判断完成。学习材料的有效性仅指教学参考；历史结果的有效性仅指原始证据，均不自动代表当前版本验收。

对照依据：全体Python AST/导入与定义清单、源码入口/工作流及阶段验收正文；自动扫描不等于逐句人工语义复核。外部链接未联网复验，Markdown代码围栏示例内路径不判为导航。

| 原路径 / 标题 | 用途 / 阶段 / 类型 | 有效范围与历史证据 | 重复与处理 / 建议路径 | 原链接 |
| --- | --- | --- | --- | --- |
| [AGENTS.md.txt](../../AGENTS.md.txt)<br>AI 开发规则 | 后续开发约定（2026-10-28，当前有效）；1. 项目开发模式；2. SPEC 规则<br>跨阶段 / 项目约定 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留正文，顶部增加当前/历史适用规则；原路径不变 | 0问题 |
| [PROJECT.md.txt](../../PROJECT.md.txt)<br>Clinical Literature Agent | 后续开发约定（2026-10-28，当前有效）；项目目标；开发阶段<br>跨阶段 / 项目约定 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留正文，顶部增加当前/历史适用规则；原路径不变 | 0问题 |
| [README.md](../../README.md)<br>Clinical Literature Research Agent | 当前后续开发路线（2026-10-28）；当前环境；安装（PowerShell，项目根目录）<br>跨阶段 / 操作指南 | 现状已更新，历史不覆盖<br>旧时点记录归档 | 旧长文归档 [docs/archive/readme-before-governance.md](../archive/readme-before-governance.md)；原路径简化为权威入口，消除并行现状 | 0问题 |
| [docs/api.md](../api.md)<br>FastAPI入口（P1-11） | Phase 5 本地混合检索（2026-10-28）；Phase 4 在线来源（2026-10-28）；Phase 3 PICO 接入（2026-10-28）<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/architecture.md](../architecture.md)<br>Clinical Literature Research Agent 架构设计 | Phase 5 已实施边界（2026-10-28）；Phase 4 已实施边界（2026-10-28）；后续扩展顺序（2026-10-28）<br>跨阶段 / 操作指南 | 现状已更新，历史不覆盖<br>旧时点记录归档 | 旧长文归档 [docs/archive/architecture-before-governance.md](../archive/architecture-before-governance.md)；原路径简化为权威入口，消除并行现状 | 0问题 |
| [docs/basic-rag.md](../basic-rag.md)<br>基础RAG与证据关联回答（P1-09） | Phase 5 本地混合检索（2026-10-28）；Phase 4 在线来源（2026-10-28）；Phase 3 PICO 接入（2026-10-28）<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/cli.md](../cli.md)<br>CLI离线入库与问答（P1-10） | Phase 5 本地混合检索（2026-10-28）；Phase 4 在线来源（2026-10-28）；Phase 3 PICO 接入（2026-10-28）<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/development-plan.md](../development-plan.md)<br>开发进度与任务记录 | Phase8维护核心收尾完成（2026-10-28）；Phase8 P8-03 来源别名与状态治理（2026-10-28）；Phase8 P8-02 本地增量运行（2026-10-28）<br>跨阶段 / 规划/时点记录 | 现状已更新，历史不覆盖<br>旧时点记录归档 | 旧长文归档 [docs/archive/development-plan-before-governance.md](../archive/development-plan-before-governance.md)；原路径简化为权威入口，消除并行现状 | 0问题 |
| [docs/documentation-audit.md](../documentation-audit.md)<br>文档一致性核对（2026-10-27） | 编号与当前阶段；发现与处理；核对结果与未解决项<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留正文，顶部增加当前/历史适用规则；原路径不变 | 0问题 |
| [docs/feishu-dedup.md](../feishu-dedup.md)<br>飞书 Redis 原子消息去重 | 合成身份；实际使用已通过filter_event的envelope.dedup_identity。；项目根目录；先保存并清除PYTEST_ADDOPTS/PYTEST_PLUGINS，结束后finally恢复。；P1-16 当前装配入口<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/feishu-events.md](../feishu-events.md)<br>飞书消息契约与事件过滤 | 飞书消息契约与事件过滤<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/feishu-runtime.md](../feishu-runtime.md)<br>P1-16 飞书运行时与部署入口 | 它解决什么问题；安装与配置；按实际执行顺序理解代码<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/feishu-sender.md](../feishu-sender.md)<br>飞书文本渲染与受限发送（P1-15） | 队列和调用顺序；官方API适配；验证和限制<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/feishu-worker.md](../feishu-worker.md)<br>飞书有界任务分派（P1-14） | P1-16 当前装配入口<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-01/README.md](../learning/ma-01/README.md)<br>MA-01 学习导航 | MA-01 学习导航<br>ma-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-01/code-walkthrough.md](../learning/ma-01/code-walkthrough.md)<br>真实执行顺序 | 真实执行顺序<br>ma-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-01/exercises.md](../learning/ma-01/exercises.md)<br>修改与验证练习 | 修改与验证练习<br>ma-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-01/interview.md](../learning/ma-01/interview.md)<br>面试表达 | 面试表达<br>ma-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-01/troubleshooting.md](../learning/ma-01/troubleshooting.md)<br>排错 | 排错<br>ma-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-01/tutorial.md](../learning/ma-01/tutorial.md)<br>角色化编排是什么 | 角色化编排是什么<br>ma-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-02/README.md](../learning/ma-02/README.md)<br>MA-02 导航 | MA-02 导航<br>ma-02 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-02/code-walkthrough.md](../learning/ma-02/code-walkthrough.md)<br>执行路径 | 执行路径<br>ma-02 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-02/exercises.md](../learning/ma-02/exercises.md)<br>练习与Demo | 练习与Demo<br>ma-02 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-02/interview.md](../learning/ma-02/interview.md)<br>面试表达 | 面试表达<br>ma-02 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-02/troubleshooting.md](../learning/ma-02/troubleshooting.md)<br>排错 | 排错<br>ma-02 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/ma-02/tutorial.md](../learning/ma-02/tutorial.md)<br>四角色与反馈原理 | 四角色与反馈原理<br>ma-02 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-00/README.md](../learning/phase-00/README.md)<br>Phase 0 学习导航 | 阅读与动手顺序；当前可定位的真实文件；学完应能证明什么<br>phase-00 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-00/code-walkthrough.md](../learning/phase-00/code-walkthrough.md)<br>按实际执行顺序读代码 | 1. 安装如何生成两个入口；2. main：先解析，不先装配；3. open_runtime：真正进入运行上下文<br>phase-00 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-00/exercises.md](../learning/phase-00/exercises.md)<br>Phase 0 修改练习与独立实现 | 1. 阅读练习：先预测，再证明；2. 修改练习：只在副本新增 --version；3. 故障练习：辨认阶段，而不是统一吞错<br>phase-00 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-00/interview.md](../learning/phase-00/interview.md)<br>Phase 0 面试表达 | 30 秒口述；1. 为什么先做 Phase 0，不直接接大模型；2. 显式配置和依赖注入分别解决什么<br>phase-00 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-00/troubleshooting.md](../learning/phase-00/troubleshooting.md)<br>Phase 0 运行、调试与排错 | 1. 第一条诊断命令；2. 按现象定位；3. 只重跑相关测试<br>phase-00 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-00/tutorial.md](../learning/phase-00/tutorial.md)<br>从零理解 Phase 0 工程骨架 | 1. 是什么：一条命令背后的几层责任；2. 为什么：把“我电脑上能跑”变成可核验的工程；3. 原理：解释器、src、锁文件与 wheel<br>phase-00 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-01/README.md](../learning/phase-01/README.md)<br>Phase 1 学习导航 | Phase 1 学习导航<br>phase-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-01/code-walkthrough.md](../learning/phase-01/code-walkthrough.md)<br>按真实调用顺序解析Phase 1 | 1. 入口与资源装配；2. 从输入文件到可追溯片段；3. 保存和并发幂等<br>phase-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-01/exercises.md](../learning/phase-01/exercises.md)<br>修改练习、独立实现与测试 | 阅读练习；修改练习一：证据不足也不补常识；修改练习二：边界与切片<br>phase-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-01/interview.md](../learning/phase-01/interview.md)<br>面试问题与30秒回答 | 项目做了什么？；如何防止幻觉引用？；为什么使用LangGraph？<br>phase-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-01/troubleshooting.md](../learning/phase-01/troubleshooting.md)<br>Phase 1 运行与排错 | 最小检查顺序；症状对应检查；真实服务测试<br>phase-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-01/tutorial.md](../learning/phase-01/tutorial.md)<br>从零理解医学文献RAG | 是什么；为什么需要；底层原理<br>phase-01 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-03/README.md](../learning/phase-03/README.md)<br>Phase 3 学习导航 | Phase 3 学习导航<br>phase-03 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-03/code-walkthrough.md](../learning/phase-03/code-walkthrough.md)<br>真实代码执行顺序 | 真实代码执行顺序<br>phase-03 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-03/exercises.md](../learning/phase-03/exercises.md)<br>练习与验证 | 练习与验证<br>phase-03 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-03/interview.md](../learning/phase-03/interview.md)<br>面试与口述 | 面试与口述<br>phase-03 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-03/troubleshooting.md](../learning/phase-03/troubleshooting.md)<br>运行与排错 | 运行与排错<br>phase-03 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-03/tutorial.md](../learning/phase-03/tutorial.md)<br>从问题到 PICO | 从问题到 PICO<br>phase-03 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-04/README.md](../learning/phase-04/README.md)<br>Phase 4 在线 PubMed 学习导航 | Phase 4 在线 PubMed 学习导航<br>phase-04 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-04/code-walkthrough.md](../learning/phase-04/code-walkthrough.md)<br>按执行顺序阅读代码 | 按执行顺序阅读代码<br>phase-04 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-04/exercises.md](../learning/phase-04/exercises.md)<br>练习与阶段验收 | 练习与阶段验收<br>phase-04 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-04/interview.md](../learning/phase-04/interview.md)<br>面试与30秒表达 | 面试与30秒表达<br>phase-04 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-04/troubleshooting.md](../learning/phase-04/troubleshooting.md)<br>排错与限制 | 排错与限制<br>phase-04 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-04/tutorial.md](../learning/phase-04/tutorial.md)<br>从检索到真实来源 | 从检索到真实来源<br>phase-04 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-05/README.md](../learning/phase-05/README.md)<br>Phase 5 学习导航 | Phase 5 学习导航<br>phase-05 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-05/code-walkthrough.md](../learning/phase-05/code-walkthrough.md)<br>按请求执行顺序阅读 | 按请求执行顺序阅读<br>phase-05 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-05/exercises.md](../learning/phase-05/exercises.md)<br>练习与集中测试 | 练习与集中测试<br>phase-05 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-05/interview.md](../learning/phase-05/interview.md)<br>面试表达 | 面试表达<br>phase-05 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-05/troubleshooting.md](../learning/phase-05/troubleshooting.md)<br>排错和边界 | 排错和边界<br>phase-05 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-05/tutorial.md](../learning/phase-05/tutorial.md)<br>两路召回为什么需要排名融合 | 两路召回为什么需要排名融合<br>phase-05 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-06/README.md](../learning/phase-06/README.md)<br>Phase 6 学习导航 | Phase 6 学习导航<br>phase-06 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-06/code-walkthrough.md](../learning/phase-06/code-walkthrough.md)<br>按真实执行顺序读代码 | 按真实执行顺序读代码<br>phase-06 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-06/exercises.md](../learning/phase-06/exercises.md)<br>练习与阶段测试 | 练习与阶段测试<br>phase-06 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-06/interview.md](../learning/phase-06/interview.md)<br>面试表达 | 面试表达<br>phase-06 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-06/troubleshooting.md](../learning/phase-06/troubleshooting.md)<br>运行与排错 | 运行与排错<br>phase-06 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-06/tutorial.md](../learning/phase-06/tutorial.md)<br>从零理解证据分析 | 从零理解证据分析<br>phase-06 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-07/README.md](../learning/phase-07/README.md)<br>Phase 7 学习导航 | Phase 7 学习导航<br>phase-07 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-07/code-walkthrough.md](../learning/phase-07/code-walkthrough.md)<br>按实际执行顺序读代码 | 按实际执行顺序读代码<br>phase-07 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-07/exercises.md](../learning/phase-07/exercises.md)<br>修改练习和验证 | 修改练习和验证<br>phase-07 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-07/interview.md](../learning/phase-07/interview.md)<br>面试表达 | 面试表达<br>phase-07 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-07/troubleshooting.md](../learning/phase-07/troubleshooting.md)<br>运行与排错 | 运行与排错<br>phase-07 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-07/tutorial.md](../learning/phase-07/tutorial.md)<br>从零理解报告与引用核验 | 从零理解报告与引用核验<br>phase-07 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/README.md](../learning/phase-08/README.md)<br>Phase8学习导航：版本、增量、来源治理与重建 | Phase8学习导航：版本、增量、来源治理与重建<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/code-walkthrough.md](../learning/phase-08/code-walkthrough.md)<br>按执行顺序读源码 | P8-03实际执行路径；收尾执行顺序<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/exercises.md](../learning/phase-08/exercises.md)<br>练习 | P8-03练习；收尾练习<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/interview.md](../learning/phase-08/interview.md)<br>面试表达 | P8-03面试表达；收尾面试题<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/maintenance.md](../learning/phase-08/maintenance.md)<br>Phase8在线窗口与显式重建 | 在线增量是什么；来源状态如何进入发布与检索；显式重建是什么<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/source-governance.md](../learning/phase-08/source-governance.md)<br>来源别名与状态治理（P8-03） | 运行；状态与使用范围；测试和调试<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/troubleshooting.md](../learning/phase-08/troubleshooting.md)<br>排错 | P8-03排错；收尾排错<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/tutorial.md](../learning/phase-08/tutorial.md)<br>版本发布与原子性 | P8-03：身份关联与状态不是原文版本；在线窗口与重建<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-08/update-runs.md](../learning/phase-08/update-runs.md)<br>P8-02 本地更新运行与恢复 | P8-02 本地更新运行与恢复<br>phase-08 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-09/README.md](../learning/phase-09/README.md)<br>Phase 9 学习导航 | Phase 9 学习导航<br>phase-09 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-09/code-walkthrough.md](../learning/phase-09/code-walkthrough.md)<br>按执行顺序读真实代码 | 按执行顺序读真实代码<br>phase-09 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-09/exercises.md](../learning/phase-09/exercises.md)<br>练习与测试 | 练习与测试<br>phase-09 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-09/interview.md](../learning/phase-09/interview.md)<br>面试表达 | 面试表达<br>phase-09 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-09/troubleshooting.md](../learning/phase-09/troubleshooting.md)<br>运行与排错 | 运行与排错<br>phase-09 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/learning/phase-09/tutorial.md](../learning/phase-09/tutorial.md)<br>从零理解离线评价 | 从零理解离线评价<br>phase-09 / 学习材料 | 教学参考；旧下一任务按阶段阅读<br>验收见对应阶段原记录 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/local-embedding.md](../local-embedding.md)<br>本地 Embedding 使用与验证（P1-05） | 环境与固定模型；准备本地资产；Python 调用<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/ma01-acceptance.md](../ma01-acceptance.md)<br>MA-01 规划/发现角色增量验收 | 修改与边界；实际集中验证；未验证项与后续<br>ma01 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/ma02-acceptance.md](../ma02-acceptance.md)<br>MA-02 剩余角色与反馈循环验收 | 实际验证；限制<br>ma02 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/minimal-evaluation-baseline-plan.md](../minimal-evaluation-baseline-plan.md)<br>Phase 7 之后的最小评价基线计划 | Phase 7 之后的最小评价基线计划<br>跨阶段 / 规划/时点记录 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/multi-agent-roadmap.md](../multi-agent-roadmap.md)<br>MA-02 当前状态（2026-10-28） | Phase 7 之后的 Multi-Agent 改造计划<br>跨阶段 / 规划/时点记录 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/offline-ingestion.md](../offline-ingestion.md)<br>离线入库应用服务（P1-07） | 准备与调用；快照、位置与身份；返回状态与非覆盖规则<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase0-acceptance.md](../phase0-acceptance.md)<br>Phase 0 阶段验收报告 | 1. 实际交付与架构摘要；2. 工程验收矩阵；3. 学习与独立验收矩阵<br>phase0 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase1-acceptance.md](../phase1-acceptance.md)<br>Phase 1 MVP阶段验收报告 | 范围与事实来源；需求与证据映射；实际执行与测试结果<br>phase1 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase1-medical-review.md](../phase1-medical-review.md)<br>P1-17 固定医学样例人工审查 | P1-17 固定医学样例人工审查<br>phase1 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase3-acceptance.md](../phase3-acceptance.md)<br>Phase 3 P3-01 实现与验收记录 | 交付范围；实际集中验证；未验收项<br>phase3 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase4-acceptance.md](../phase4-acceptance.md)<br>Phase 4 P4-01 在线 PubMed 验收记录 | 本地基线与交付；集中测试与实际证据；真实官方接口<br>phase4 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase5-acceptance.md](../phase5-acceptance.md)<br>Phase 5 P5-01 混合检索验收记录 | 基线与修改范围；集中测试证据；真实资源与清理<br>phase5 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase6-acceptance.md](../phase6-acceptance.md)<br>Phase 6 P6-01 核心实现与验收记录 | 基线和交付；集中验证证据；未验证项与完成边界<br>phase6 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase7-acceptance.md](../phase7-acceptance.md)<br>Phase 7 P7-01 核心报告链路交付与验收记录 | 实现范围；集中测试与修正；未验证及剩余门槛<br>phase7 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase7-medical-review.md](../phase7-medical-review.md)<br>Phase 7 真实验收医学复核准备材料 | blood-pressure；sepsis；人工复核项目（均待完成）<br>phase7 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase8-acceptance.md](../phase8-acceptance.md)<br>Phase8当前验收状态（2026-10-28） | Phase8 P8-01 显式版本发布验收；实现；实际验证<br>phase8 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/phase9-acceptance.md](../phase9-acceptance.md)<br>Phase 9 执行与验收（2026-10-28） | 本轮交付；可重复命令；不能自动完成的验收<br>phase9 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/postgres.md](../postgres.md)<br>PostgreSQL 与 pgvector：本地模型和迁移 | 安装与本地启动；调用者先设置 CLINICAL_AGENT_DB_PASSWORD；也可生成仅当前 shell 使用的开发密码。；两个表的契约<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/ml-cpu-py312-linux.txt](../research/dependencies/ml-cpu-py312-linux.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/ml.in --python-version 3.12 --python-platform x86_64-many<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/ml-cpu-py312-windows.txt](../research/dependencies/ml-cpu-py312-windows.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/ml.in --python-version 3.12 --python-platform x86_64-pc-w<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/ml-py312-linux.txt](../research/dependencies/ml-py312-linux.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/ml.in --python-version 3.12 --python-platform x86_64-many<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/ml-py312-windows.txt](../research/dependencies/ml-py312-windows.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/ml.in --python-version 3.12 --python-platform x86_64-pc-w<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/ml.in](../research/dependencies/ml.in)<br>CPU/GPU runtime and model smoke tests remain separate acceptance gates. | CPU/GPU runtime and model smoke tests remain separate acceptance gates.<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/phase0-py312-linux.txt](../research/dependencies/phase0-py312-linux.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/phase0.in --python-version 3.12 --python-platform x86_64-<br>phase0 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/phase0-py312-windows.txt](../research/dependencies/phase0-py312-windows.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/phase0.in --python-version 3.12 --python-platform x86_64-<br>phase0 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/phase0.in](../research/dependencies/phase0.in)<br>P0-03 research input, not the project's installed environment. | P0-03 research input, not the project's installed environment.<br>phase0 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/phase1-py312-linux.txt](../research/dependencies/phase1-py312-linux.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/phase1.in --python-version 3.12 --python-platform x86_64-<br>phase1 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/phase1-py312-windows.txt](../research/dependencies/phase1-py312-windows.txt)<br>This file was autogenerated by uv via the following command: | uv --cache-dir .research-cache/uv pip compile docs/research/dependencies/phase1.in --python-version 3.12 --python-platform x86_64-<br>phase1 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/dependencies/phase1.in](../research/dependencies/phase1.in)<br>Phase 1 compatibility probe only; no Phase 1 code or installation. | Phase 1 compatibility probe only; no Phase 1 code or installation.<br>phase1 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/environment-audit.md](../research/environment-audit.md)<br>Phase 0 / P0-01：目录与环境检查 | 范围与验收；初始目录与规则；实际执行与结果<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/p0-03-validation.md](../research/p0-03-validation.md)<br>P0-03 技术选型核查约定与执行记录 | 输入输出与边界；验收场景及 DoD；初始检查<br>p0-03 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/research/reference-repository-analysis.md](../research/reference-repository-analysis.md)<br>Phase 0 / P0-02：ClinicalAgent 参考仓库分析 | 1. 任务约定与验收方法；2. 来源、版本与核查范围；3. 实际目录<br>跨阶段 / 历史调研/依赖证据 | 历史研究/依赖探测，非当前版本保证<br>历史调研证据 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/00-project-overview.md](../specs/00-project-overview.md)<br>SPEC 00：项目总体与 Phase 0 工程初始化 | 当前阶段路线与验收规则（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/01-mvp.md](../specs/01-mvp.md)<br>SPEC 01：离线知识库、基础 RAG 与飞书 MVP | 后续路线说明（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/02-async-experience.md](../specs/02-async-experience.md)<br>SPEC 02：异步受理与任务状态 | 延期状态（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/03-pico.md](../specs/03-pico.md)<br>SPEC 03：问题分类与 PICO | 本轮核心范围与测试约定（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/04-pubmed-search.md](../specs/04-pubmed-search.md)<br>SPEC 04：PubMed 官方实时检索 | 本轮核心范围与测试约定（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/05-hybrid-retrieval.md](../specs/05-hybrid-retrieval.md)<br>SPEC 05：关键词与向量混合检索 | 本轮核心范围与测试约定（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/06-evidence-analysis.md](../specs/06-evidence-analysis.md)<br>SPEC 06：研究方法、相似研究与候选研究缺口分析 | 本轮核心范围与测试约定（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/07-citation-report.md](../specs/07-citation-report.md)<br>SPEC 07：科研选题现状调研报告与引用核验 | 本轮核心范围与测试约定（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/08-knowledge-update.md](../specs/08-knowledge-update.md)<br>SPEC 08：增量更新、去重与幂等 | 当前状态（2026-10-28）；原延期状态（历史）；1. 背景及目标<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/09-evaluation.md](../specs/09-evaluation.md)<br>SPEC 09：离线评价、引用准确性与性能回归 | 当前状态（2026-10-28）；1. 背景及目标；2. 功能需求<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/langchain-model-boundary.md](../specs/tasks/langchain-model-boundary.md)<br>通用模型 API 边界调整 | 需求与目标；功能边界；输入输出与数据模型<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/ma-01-planner-scout.md](../specs/tasks/ma-01-planner-scout.md)<br>MA-01：规划与文献发现角色增量提取 | MA-01：规划与文献发现角色增量提取<br>ma-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/ma-02-feedback.md](../specs/tasks/ma-02-feedback.md)<br>MA-02 剩余角色及有限反馈 | MA-02 剩余角色及有限反馈<br>ma-02 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/minimal-evaluation-baseline.md](../specs/tasks/minimal-evaluation-baseline.md)<br>最小评价基线 v1 | 最小评价基线 v1<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-01-literature-contracts.md](../specs/tasks/p1-01-literature-contracts.md)<br>P1-01 SPEC：文献与证据 DTO、来源和定位契约 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-02-pdf-parsing.md](../specs/tasks/p1-02-pdf-parsing.md)<br>P1-02 SPEC：PDF 文本层解析与逐页来源单元 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-02 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-03-pubmed-xml.md](../specs/tasks/p1-03-pubmed-xml.md)<br>P1-03 SPEC：本地 PubMed XML 解析与元数据映射 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-03 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-04-source-chunking.md](../specs/tasks/p1-04-source-chunking.md)<br>P1-04：来源单元分块与 tokenizer 长度契约 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-04 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-05-local-embedding.md](../specs/tasks/p1-05-local-embedding.md)<br>P1-05：本地 Embedding 与真实 tokenizer 适配 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-05 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-06-postgres-schema.md](../specs/tasks/p1-06-postgres-schema.md)<br>P1-06：PostgreSQL + pgvector 持久化模型与迁移 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-06 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-07-offline-ingestion.md](../specs/tasks/p1-07-offline-ingestion.md)<br>P1-07：离线入库服务与事务/幂等映射 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-07 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-08-vector-retrieval.md](../specs/tasks/p1-08-vector-retrieval.md)<br>P1-08：基础向量检索与证据命中DTO | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-08 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-09-basic-rag.md](../specs/tasks/p1-09-basic-rag.md)<br>P1-09：基础RAG工作流与证据关联回答 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-09 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-10-cli-entrypoints.md](../specs/tasks/p1-10-cli-entrypoints.md)<br>P1-10：CLI离线入库与问答入口 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-10 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-11-fastapi.md](../specs/tasks/p1-11-fastapi.md)<br>P1-11：FastAPI入库与问答入口 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-11 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-12-feishu-events.md](../specs/tasks/p1-12-feishu-events.md)<br>P1-12：飞书消息契约与事件过滤 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-12 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-13-redis-dedup.md](../specs/tasks/p1-13-redis-dedup.md)<br>P1-13：Redis 原子消息去重 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>p1-13 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-14-feishu-worker.md](../specs/tasks/p1-14-feishu-worker.md)<br>P1-14：飞书有界任务分派与服务复用 | 1. 需求与目标；2. 功能需求；3. 非功能需求<br>p1-14 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-15-feishu-sender.md](../specs/tasks/p1-15-feishu-sender.md)<br>P1-15：飞书文本渲染与受限发送 | 1. 需求与目标；2. 功能需求；3. 非功能需求<br>p1-15 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-16-feishu-runtime.md](../specs/tasks/p1-16-feishu-runtime.md)<br>P1-16 官方SDK长连接、装配与Compose入口 | 1. 需求与目标；2. 功能需求；3. 非功能需求<br>p1-16 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p1-17-mvp-acceptance.md](../specs/tasks/p1-17-mvp-acceptance.md)<br>P1-17 MVP阶段验收与学习文档 | 1. 需求与目标；2. 功能需求；3. 非功能需求<br>p1-17 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p3-01-pico.md](../specs/tasks/p3-01-pico.md)<br>P3-01：PICO 分析与查询规划核心链路 | 1. 目标与基线；2. 核心范围；3. 输入<br>p3-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p4-01-pubmed-online.md](../specs/tasks/p4-01-pubmed-online.md)<br>P4-01：PubMed 在线检索核心链路 | 1. 目标与范围；2. 官方依据；3. 输入<br>p4-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p5-01-hybrid-retrieval.md](../specs/tasks/p5-01-hybrid-retrieval.md)<br>P5-01：PostgreSQL 关键词与向量混合检索 | 1. 基线与范围；2. 输入与默认行为；3. FTS与标识符<br>p5-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p6-01-evidence-analysis.md](../specs/tasks/p6-01-evidence-analysis.md)<br>P6-01：带来源约束的研究方法、相似研究及候选缺口分析 | P6-01：带来源约束的研究方法、相似研究及候选缺口分析<br>p6-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p7-01-citation-report.md](../specs/tasks/p7-01-citation-report.md)<br>P7-01：科研选题现状调研报告核心链路 | P7-01：科研选题现状调研报告核心链路<br>p7-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p8-01-version-publication.md](../specs/tasks/p8-01-version-publication.md)<br>P8-01：显式版本发布核心 | P8-01：显式版本发布核心<br>p8-01 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p8-02-update-runs.md](../specs/tasks/p8-02-update-runs.md)<br>P8-02 本地增量批次、恢复、dry-run与调度 | P8-02 本地增量批次、恢复、dry-run与调度<br>p8-02 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p8-03-source-governance.md](../specs/tasks/p8-03-source-governance.md)<br>P8-03 来源别名与状态治理 | 输入输出与范围；数据与异常；先写测试与集中验收<br>p8-03 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p8-completion.md](../specs/tasks/p8-completion.md)<br>Phase8收尾：P8-04在线窗口与P8-05显式重建 | P8-04；P8-05；数据与异常<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/p9-evaluation.md](../specs/tasks/p9-evaluation.md)<br>Phase 9 冻结实施契约（2026-10-28） | Phase 9 冻结实施契约（2026-10-28）<br>跨阶段 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/phase0-acceptance.md](../specs/tasks/phase0-acceptance.md)<br>P0-08 SPEC：学习文档与 Phase 0 独立验收 | 1. 背景及目标；2. 功能需求；3. 非功能需求<br>phase0 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/specs/tasks/phase0-implementation.md](../specs/tasks/phase0-implementation.md)<br>Phase 0 最小工程任务 SPEC | 1. 背景及目标；2. 功能需求及任务拆分；3. 非功能需求<br>phase0 / 需求契约/阶段任务快照 | 冻结契约/阶段范围；完成程度查状态表<br>设计不等于验收 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/tech-stack.md](../tech-stack.md)<br>技术选型与兼容性基线 | 当前模型接入方式（2026-10-27 修订）；1. 结论与环境选择；2. 组件职责、依据、替代方案和风险<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/testing-strategy.md](../testing-strategy.md)<br>测试策略与 TDD 执行约定 | 阶段末集中验收策略（2026-10-28，当前有效）；1. 范围与原则；2. 分层与执行范围<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [docs/vector-retrieval.md](../vector-retrieval.md)<br>基础向量检索（P1-08） | Phase 5 本地混合检索（2026-10-28）；调用方式；参数与分数<br>跨阶段 / 操作指南 | 按原记录时点保留；不推定当前通过<br>非验收结论 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/README.md](../../evaluation/README.md)<br>最小评价基线 v1 | 最小评价基线 v1<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/minimal-v1/evidence/model-response-1.txt](../../evaluation/minimal-v1/evidence/model-response-1.txt)<br>model-response-1.txt | model-response-1.txt<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/minimal-v1/evidence/model-response-2.txt](../../evaluation/minimal-v1/evidence/model-response-2.txt)<br>model-response-2.txt | model-response-2.txt<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/minimal-v1/evidence/model-response-3.txt](../../evaluation/minimal-v1/evidence/model-response-3.txt)<br>model-response-3.txt | model-response-3.txt<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/minimal-v1/evidence/model-response-4.txt](../../evaluation/minimal-v1/evidence/model-response-4.txt)<br>model-response-4.txt | model-response-4.txt<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/local-start-smoke/results.md](../../evaluation/results/local-start-smoke/results.md)<br>Phase 9 replay | Phase 9 replay<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/ma01-baseline-replay/results.md](../../evaluation/results/ma01-baseline-replay/results.md)<br>最小评价基线 v1 | 最新完整启动记录；边界<br>ma01 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/ma02-baseline-replay/results.md](../../evaluation/results/ma02-baseline-replay/results.md)<br>最小评价基线 v1 | 最新完整启动记录；边界<br>ma02 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/minimal-v1/results.md](../../evaluation/results/minimal-v1/results.md)<br>最小评价基线 v1 | 最新完整启动记录；边界<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/p802-fixed-regression/results.md](../../evaluation/results/p802-fixed-regression/results.md)<br>最小评价基线 v1 | 最新完整启动记录；边界<br>跨阶段 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/phase8-completion/results.md](../../evaluation/results/phase8-completion/results.md)<br>最小评价基线 v1 | 最新完整启动记录；边界<br>phase8 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/phase9-final/results.md](../../evaluation/results/phase9-final/results.md)<br>Phase 9 replay | Phase 9 replay<br>phase9 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/phase9-formulas/results.md](../../evaluation/results/phase9-formulas/results.md)<br>Phase 9 replay | Phase 9 replay<br>phase9 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |
| [evaluation/results/phase9-historical/results.md](../../evaluation/results/phase9-historical/results.md)<br>最小评价基线 v1 | 最新完整启动记录；边界<br>phase9 / 验收/评价原始证据 | 原始证据保留，未执行/失败/未签署保持<br>是，按原范围 | 保留原路径，主题导航引用；不合并不同职责 | 0问题 |

## 本轮新增与归档文档

| 路径 | 用途/有效范围/处理 |
| --- | --- |
| [docs/README.md](../README.md) | 当前总导航，唯一索引入口 |
| [current/architecture.md](../current/architecture.md) | 当前架构权威说明，对照源码/测试，不代表医学验收 |
| [guides/README.md](../guides/README.md) | 当前操作指南索引，引用原专门指南 |
| [learning/README.md](../learning/README.md) | 当前主题学习导航，保留原阶段教程 |
| [governance/plan.md](plan.md) | 本轮审计、风险、理由与处理映射 |
| [governance/inventory.md](inventory.md) | 原175文档及本轮新增文件处理清单 |
| [governance/tree.md](tree.md) | 完整实际目录前后对比 |
| [governance/README.md](README.md) | 实际结果、失败、最终验证与未验证事项 |
| [governance/baseline.json](baseline.json) | 整理前373文件hash、文档结构/状态摘录与154个Python AST模块清单 |
| [archive/readme-before-governance.md](../archive/readme-before-governance.md) | 整理前README历史内容，适用原时点，仅重定位链接 |
| [archive/architecture-before-governance.md](../archive/architecture-before-governance.md) | 原设计/现状混合内容快照，不再维护当前架构 |
| [archive/development-plan-before-governance.md](../archive/development-plan-before-governance.md) | 原完整阶段开发日志，保留失败与缺口 |

没有删除或合并任何原SPEC、验收、医学复核、教材或评价证据。所谓归档是内容迁入快照，旧路径保留兼容入口；本轮不暂存用户工作区，避免git mv连同既有未提交修改进入暂存区。
