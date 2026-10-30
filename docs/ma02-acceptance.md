# MA-02 剩余角色与反馈循环验收

2026-10-28。六角色编排和有限反馈核心实现交付，真实医学/E2E验收仍未通过。先冻结[任务SPEC](specs/tasks/ma-02-feedback.md)并编写测试，再实现，增量末集中验证。

新增MethodsAnalystAgent、PriorArtGapAnalystAgent、ResearchDesignAgent、EvidenceReviewerAgent。Methods复用原EvidenceAnalyzer联合抽取，不把一个模型调用伪称四次独立推理；PriorArt独立校验联合草稿的原文、比较/候选缺口证据；Design仅从这些缺口和已报告方法整理待评估方案，附假设、适用范围、反证和验证事项，不产生无依据的样本量/效果/可行性承诺；Reviewer复用原ReportBuilder门禁及支持度审核。四角色与MA-01两角色共享状态、deadline与同一LangGraph。

报告流程为plan/retrieve/analyze/prior_art/design/report。unsupported允许返回Methods重建；空或partial检索允许回Scout按原范围/名额/策略重检。每轮重新生成分析、方案和审核，不沿用旧支持状态。身份无效直接停止；unknown与官方不可用不盲目循环。默认1轮，严格整数0–2；原期限不重置，模型调用结构上界为规划1+每轮分析/审核各1（最大7），没有新增供应商或依赖。普通问答无反馈，分析入口经过PriorArt后结束。

ResearchReport增加research_designs、feedback_history及feedback_stop，Markdown显示待评估方案与停止原因；核心认识标签和引用门禁不变。预算耗尽unsupported保持rejected，空/partial保持verification_incomplete，不因为轮数用完标verified。

## 实际验证

项目根.venv/Scripts/python.exe：首轮相关234 passed（22.65秒）；补三边界后237 passed（21.86秒）；再补空结果耗尽后的最终联合 **238 passed（26.42秒）**，.artifacts/ma02-release-tests.txt。没有伪造RED记录。Ruff及format --check改动的5文件通过；mypy src 52源文件通过。六份[学习说明与合成Demo入口](learning/ma-02/README.md)交付。

最终命令：`-I -m pytest tests/unit/test_feedback_agents.py tests/unit/test_agent_roles.py tests/unit/test_pico.py tests/unit/test_research.py tests/unit/test_evidence_analysis.py tests/unit/test_citation_report.py tests/unit/test_api_runtime.py tests/unit/test_command_runtime.py tests/integration/test_api.py -q --tb=short --basetemp=.artifacts/ma02-release-tmp -o cache_dir=.artifacts/ma02-cache`。

质量范围：src/clinical_agent/application/agents.py、research.py、workflow.py、src/clinical_agent/domain/report.py、tests/unit/test_feedback_agents.py。`-m mypy src --cache-dir .artifacts/ma01-mypy`通过；没有重复无关全量。最小基线命令 `-X utf8 -I scripts/evaluate_minimal_baseline.py --output evaluation/results/ma02-baseline-replay`，保留v1，fresh仍0/2、来源4/4、医学未评价，退出1为预期。

## 限制

新增真实模型/网络/数据库调用0；不会自动使用历史剩余付费授权。测试验证编排与门禁，不代表医学质量提高。联合草稿仍来自同一现有模型调用，PriorArt校验不是独立医学审查；方案是保守的待调查草案，数据可得性/设计选择仍须人工。重检不扩展策略、不证明检全。原Phase7模型响应错误、数据库未通、人工标签缺失均保留。本轮不实施Phase8/9，完成后停止。
