# MA-01 规划/发现角色增量验收

2026-10-28。首个增量完成；只提取IdeaPlannerAgent与LiteratureScoutAgent，不标六角色或Multi-Agent整体改造完成。按用户明确指令复用现有技术基线；Phase7真实端到端和医学待审项保留。

## 修改与边界

先读规则、进度、路线、最小观察基线及源码/测试，冻结[任务SPEC](specs/tasks/ma-01-planner-scout.md)，先编写8个角色场景，再实施并于本增量末集中验证。

- application/workflow.py：从ResearchService迁出request-local共享TypedDict，补充内部agent_steps和局部AgentPatch。
- application/agents.py：规划角色调用原PicoPlanner，发现角色调用原本地/在线检索及来源合并；调用前后检查原deadline，保持DTO/原文/身份/错误约束。
- application/research.py：同一LangGraph的plan/retrieve节点委托角色，其余图节点、入口/装配和报告保持。保留原内部端口属性以兼容现有装配检查。
- tests/unit/test_agent_roles.py：冻结4份真实模型规划输出的门禁回放、2条真实PubMed快照的ID/hash/顺序和调用次数、2项共享期限场景；新步骤列表不原地修改旧状态。
- [六份说明与Demo](learning/ma-01/README.md)，架构、路线和进度同步。没有新增依赖、表、模型/检索请求或用户输出字段。

本轮不是给六个同一调用的包装类命名：只迁移有独立端口和patch职责的两个节点。Methods/Prior-Art/Gap/Design/Reviewer仍未提取，没有补检、返工循环或并行模型执行；当前图无回边，仍有限终止。后续新增反馈必须另冻结轮数/预算与验收。

## 实际集中验证

项目根解释器 .venv/Scripts/python.exe。

| 范围 | 结果 |
| --- | --- |
| 角色及受影响联合 | **258 passed（25.99秒）**，.artifacts/ma01-tests.txt |
| Ruff | agents.py、workflow.py、research.py、新测试和Demo通过 |
| 格式 | 同范围5文件通过 |
| mypy src | 52源文件通过；冷缓存类型检查耗时较长，没有作为通过提前记录 |
| 离线Demo | 显示idea_planner → literature_scout，PMID26551272/34010531，与冻结快照一致；不是在线运行 |
| 最小基线回放 | 证据manifest有效，fresh仍0/2，来源仍4/4，医学未评价，新增模型/网络0；预期退出1 |

联合命令：`-I -m pytest tests/unit/test_agent_roles.py tests/unit/test_pico.py tests/unit/test_research.py tests/unit/test_pubmed_online.py tests/unit/test_evidence_analysis.py tests/unit/test_citation_report.py tests/unit/test_command_runtime.py tests/unit/test_api_runtime.py tests/unit/test_minimal_baseline.py tests/integration/test_api.py -q --tb=short --basetemp=.artifacts/ma01-tests-tmp -o cache_dir=.artifacts/ma01-cache`。

质量命令：`-m ruff check src/clinical_agent/application/agents.py src/clinical_agent/application/workflow.py src/clinical_agent/application/research.py tests/unit/test_agent_roles.py docs/learning/ma-01/demo.py`；format --check同范围；`-m mypy src --cache-dir .artifacts/ma01-mypy`。

Demo：`-X utf8 -I docs/learning/ma-01/demo.py`。基线：`-X utf8 -I scripts/evaluate_minimal_baseline.py --output evaluation/results/ma01-baseline-replay`。结果置于新目录，未覆盖minimal-v1证据。对照摘要见[migration-checks.json](../evaluation/results/ma01-baseline-replay/migration-checks.json)。首次格式检查列出的长行已由format修正，最后Ruff/格式均通过。

## 未验证项与后续

没有新真实模型、PubMed联网或业务数据库调用，没有消耗历史剩余付费授权；没有重复无关全量测试。回放只验证来源门禁/身份和角色迁移兼容，不证明新完整链路通过或科研分析更好。失败基线、无医学独立标签和未通本地库仍保留，未将其变为成功。观察基线跨未提交历史版本，不是受控医学改进实验。

本轮完成后停止。下一增量再明确Methods与Prior-Art/Gap拆分边界，之后才考虑方案和有限审核反馈；不自动实施后续角色、Phase8或完整Phase9。
