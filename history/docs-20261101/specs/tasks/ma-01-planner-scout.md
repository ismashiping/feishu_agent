# MA-01：规划与文献发现角色增量提取

2026-10-28；用户明确授权增量Multi-Agent。首个任务只迁移IdeaPlannerAgent与LiteratureScoutAgent，保留Phase7待审状态和冻结观察基线，不实施六角色全量改造或Phase8/完整Phase9。

输入输出：共享WorkflowState保留request/deadline/QueryPlan/RetrievalResult/AnalysisResult/ResearchReport及现有分支标志，新增仅内部agent_steps。角色返回局部补丁，不能原地修改共享请求/既有步骤。Planner调用原PicoPlanner，输出经同一严格原文校验的QueryPlan；Scout调用现有本地检索及PubMedRetrievalService，按原scope进行本地/在线来源合并，输出经原DTO验证的快照。共享总期限在调用前后检查，超时和外部失败沿原错误码；不将失败当空结果。

ResearchService同一已编译LangGraph的plan/retrieve节点分别委托独立角色，入口及其他节点保持。无额外LLM/检索调用、无新供应商/存储/依赖。不伪称Methods、Prior-Art/Gap、Design或Reviewer已独立为Agent；反馈循环留后续任务，当前图无回边，每次至多规划1次及既定scope检索1次/通道，调用总期限仍原ResearchLimits。内部步骤含角色/耗时，不包含原文、密钥或路径，不增加用户输出字段。

异常：阻断澄清不检索，原文区间不符仍拒绝；scope/options/返回快照不一致仍失败。空通道沿既有语义。无模型配置时不调用付费模型，不承诺修复历史真实失败。

先写tests/unit/test_agent_roles.py，再实施。固定场景：共享请求/步骤不可变，过期前不调用、外部调用后超时；计划4份冻结真实响应中2份错误继续拒绝、2份合法继续通过；真实PubMed冻结快照回放保持ID/hash/命中顺序且不新增调用；原问答/分析/报告、澄清、hybrid和错误链路回归。跨请求并发状态隔离复用原测试。

阶段末命令：.venv/Scripts/python.exe -I -m pytest tests/unit/test_agent_roles.py tests/unit/test_pico.py tests/unit/test_research.py tests/unit/test_pubmed_online.py tests/unit/test_evidence_analysis.py tests/unit/test_citation_report.py tests/unit/test_command_runtime.py tests/unit/test_api_runtime.py tests/unit/test_minimal_baseline.py tests/integration/test_api.py -q；Ruff/mypy；最小基线脚本指定新output目录，不覆盖v1。既有默认基线仍fresh0/2、source4/4、医学未审，退出1为预期。仅角色回放对照不是新真实端到端或医学效果验收。

验收：上述核心目标及受影响回归通过；基线manifest不变；模型/网络新增调用0；六份学习说明和离线Demo齐备；记录未验证的真实链路。下一增量再考虑方法与缺口职责边界，不自动开始。
