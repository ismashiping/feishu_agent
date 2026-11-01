# 用户入口默认混合来源

2026-10-28，用户明确要求“默认改成混合”。本记录取代此前探索型发现SPEC中的默认local决策；旧验收只代表当时事实。

## 行为与兼容性

- CLI `ask`省略`--scope`时使用hybrid；问答、分析、报告均适用。
- API三类研究路由的QuestionBody默认scope=hybrid，OpenAPI同步体现；显式local/online/hybrid继续有效。
- 飞书普通文本及/report构造scope=hybrid，复用同一ResearchService与Scout。
- hybrid按原实现先本地、再在线PubMed，并按原规则合并；在线失败保持错误，不降级伪装为零结果或本地成功。
- mode仍默认vector，仅控制本地召回。PubMed预算、请求门、结果上限、deadline、引用及版本规则不变。

底层RetrievalRequest/QuestionRequest保留local默认，兼容内部显式服务调用和维护工具；用户入口已明确传入hybrid，不依赖底层默认。仅本地使用CLI `--scope local`或API `"scope":"local"`；飞书没有新增来源选择命令。使用document_ids或非零min_similarity等本地限定时必须显式local，不能默认放宽约束用于在线来源。

默认调用将访问PubMed，部署须满足既有在线联系人/网络配置和单实例配额约束。返回的scope及实际query_sent继续可见；无需迁移数据库或更新依赖。

## 验证与测试调整

新增test_hybrid_default.py的10例：CLI默认及三种显式scope、API请求schema默认及显式scope、飞书文本/报告的默认传参；全部通过。

首轮完整回归：1260 passed /12 failed /122 deselected /1既有警告，140.58秒。失败来自原离线入口测试未显式声明local、固定local输出替身与新hybrid请求不一致，以及飞书真实图测试缺少在线替身；保留失败日志，不将其改标通过。

原本地业务测试增加显式local以继续验证原引用、分析、关键词模式和导入后检索；飞书两项真实LangGraph测试增加明确空在线通道及provenance，比较hybrid输出与同scope直接调用，未放宽生产引用/来源校验。原“携带PubMed参数而不带scope会拒绝”的测试改为“显式local携带PubMed参数会拒绝”，因为默认已按授权改为hybrid。

相关联合：230 passed /1 external排除，8.85秒，包含新入口默认、探索型路由及显式local不联网、CLI/API、报告/分析、飞书消息、来源错误和关键词模式回归。Ruff通过，mypy结果见最终补记。

真实PubMed/PostgreSQL/飞书收发未在本轮重跑；先前真实PubMed失败及Docker不可访问记录见[探索型修复验收](exploratory-discovery-acceptance.md)，不据Fake测试推定外部服务可用。没有扩大网络预算或触碰业务数据。

本地日志：`.artifacts/hybrid-default/full.txt`、`related.txt`、`final.txt`。最终全量及文档核查在下方补记。

## 最终验证

完整命令：`.venv/Scripts/python.exe -I -m pytest -q --tb=short --basetemp=.artifacts/hybrid-default/final-tmp -o cache_dir=.artifacts/hybrid-default/cache`（本进程OMP/MKL线程各2）。结果 **1282 passed /122 deselected /1既有SDK弃用警告，129.36秒**。

`ruff check src tests scripts`、4个新增/改动入口文件的格式检查、`mypy src --no-incremental`（64源文件）、CLI ask help、API OpenAPI默认hybrid检查、文档本地链接/锚点/围栏扫描及`git diff --check`通过。文档扫描390文件、189文档、156 Python，0链接问题，domain反向依赖0。真实外部测试仍未复验，不将122项排除计为通过。
