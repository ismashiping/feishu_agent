# 探索型研究问题理解与检索：执行记录

日期：2026-10-28。适用范围为本次增量，不重新签署历史Phase3–8、MA或医学验收。[冻结SPEC](specs/tasks/exploratory-discovery.md)。

## 根因与调用链

CLI `_business`将默认local参数传QuestionRequest，API QuestionBody继承RetrievalRequest.scope=local，飞书worker.py:158直接构造默认QuestionRequest；三个入口均复用ResearchService。IdeaPlannerAgent调用PicoPlanner，后者调用LangChain标准抽取，校验JSON与原文span。旧pico.py将uncertain且ambiguities非空判为needs_clarification，StructuredQuestion再次验证该规则；提示词却允许ambiguities包含非阻断信息。这是语义不一致，不是PICO四字段必填（其值允许null）。

research.py:129的_plan_route只看extraction_status，所以普通问答、analyze、report均在Scout之前被挡住。MA-02反馈发生在报告审核之后，不能补救提前澄清。agents.py:84原本已把query_plan传入在线服务，但domain/pubmed.py原query_text只采用显式query或原问题，候选扩展未变为实际查询。本地RetrievalService仍采用原问题，避免改变vector/FTS语义。

默认vector来自本地mode；默认local来自入口，并非每次用户显式选择。两者是独立维度。本轮维持默认local，避免既有离线/飞书请求自动联网；明确提示实际范围，CLI/API可显式online/hybrid。飞书当前不接受scope参数，文本及/report仍local，未伪造一个不存在的飞书选项。

## 最小修改与兼容

- domain/pico.py：新增可选blocking_ambiguities。新模型必须给列表，ambiguities仅代表缺失/可选问题；未知主题或无法尊重显式约束才阻断。旧null输出按旧冻结规则解释，保留历史回放。
- application/pico.py：新空阻断列表要求至少一项原文锚定的PICO或关键词，否则生成针对主题的澄清。不能只靠模型扩展词假定已识别主题；所有原文span及约束全文校验保留。
- domain/pubmed.py：新契约使用原问题与候选词组成一次有界、字面引用的OR查询；显式query优先，超长回原问题；不增加请求数或过滤条件。候选词不写回用户PICO。检索并不保证执行了原问题所有自然语言条件的严格语义过滤，真实query_sent可追踪。
- research.py：澄清分析结果优先展示阻断问题；原节点、条件路由、deadline和反馈规则不变。
- feishu/sender.py：local明确未联网；澄清明确未执行检索；非阻断问题显示为可选细化（最多两条）。CLI文本复用此渲染，JSON保留scope与QueryPlan。
- 测试、当前架构、CLI/API/飞书指南与进度导航同步；原SPEC增加后续增量链接，不重写旧验收正文。无新依赖、迁移、表或第二服务。

## RED、GREEN及真实执行

1. 新回归首轮7 failed（2.32秒），新blocking字段被旧DTO拒绝并封装extraction_failed。首版测试还存在手写中文span偏移错误，GREEN前改为question.index计算；不将fixture错误冒充独立产品缺陷。
2. 最小实现后首批7 passed（1.59秒）。补在线/混合/失败/入口默认测试时，测试错误地假定总预算60秒（实际90秒）、并遗漏空回答limitations最低一项约束，出现7 failed/7 passed；修复测试使其遵循既有预算/DTO，不修改生产预算或放宽DTO。
3. 相关联合：`python -I -m pytest tests/unit/test_exploratory_discovery.py tests/unit/test_pico.py tests/unit/test_feedback_agents.py tests/integration/test_pubmed_online.py -q --tb=short --basetemp=.artifacts/discovery/related-tmp`：**73 passed /1外部测试排除，3.88秒**。包括新14例、旧PICO来源/历史兼容、MA反馈/总期限、CLI/API既有在线合同。新三入口测试在Scout处注入可辨识异常以证明路由到达，不将此声称为真实报告生成成功。
4. 第一次默认回归未指定工作区basetemp，系统临时目录PermissionError：953 passed /5 failed /307 errors /122 deselected（28.81秒）；不标通过。指定工作区临时目录后完整重跑，结果见下方补记。
5. `python -m ruff check src tests scripts`通过；`python -m mypy src --no-incremental`通过（64源文件）。Markdown链接/锚点/围栏及git diff --check最终复查见补记。中间导航曾指向尚未生成的本文件，不将中间态当最终通过。

本地日志在`.artifacts/discovery/`；首轮RED/最早回归在`.artifacts/governance/discovery-*.txt`。日志为本地忽略产物，本文保存实际摘要。

## 真实依赖与未验证事项

实际运行既有`test_live_official_pubmed`：**1 failed /6 deselected，2.08秒**，官方调用返回pubmed_failed；未伪装成零命中。没有足够证据区分网络限制、TLS或远端故障，不臆断具体根因。命令：`python -I -m pytest tests/integration/test_pubmed_online.py -m external -k live_official -q --tb=short --basetemp=.artifacts/discovery/live-tmp`。

`docker version`无法读取Docker配置且无法连接docker_engine，因此未运行隔离PostgreSQL测试，未触碰业务库。真实LLM对肝肿瘤问题的分类/关键词质量、真实PubMed肝肿瘤命中、真实PG链路、飞书收发及医学质量均未完成本轮验收。确定性Fake与既有HTTP Mock集成验证了调度/契约，不证明某篇实际医学论文存在或方法有效。

## 学习说明

Planner负责“理解与是否可启动”，不是要求用户填满表单。PICO为空可以是合法研究发现；需要的是可回指用户原文的主题，而不是模型自行猜测的模态。StructuredQuestion把阻断决策编码为状态，LangGraph只根据状态选clarify/retrieve；Scout独立按scope选择通道。候选词只是PubMed一次查询的可追踪备选表达，不能变成已确认研究条件。报告反馈始终使用同一deadline与原次数上限，不能靠重新检索无限重试。

旧模型若省略新增字段仍按旧规则，属于兼容边界；新提示词/schema明确要求返回列表。模型仍可能误判阻断或产生不佳扩展，真实模型验收尚未执行，不能把确定性测试当模型效果保证。

## 最终完整回归补记

实际命令（本进程OMP_NUM_THREADS=2、MKL_NUM_THREADS=2）：

```powershell
.venv/Scripts/python.exe -I -m pytest -q --tb=short --basetemp=.artifacts/discovery/full-tmp -o cache_dir=.artifacts/discovery/cache
```

**1272 passed /122 deselected /1既有飞书SDK弃用警告，147.76秒**，日志`.artifacts/discovery/full.txt`。本批包含最终14例新测试和全部本轮生产源码修改；排除的真实依赖不算通过。默认集成测试通过不替代上面真实PubMed失败或未运行PG。最后变更仅为文档记录补记，无后续生产代码修改。

最终文档扫描388文件、188文档、155 Python，显式内部链接/锚点/围栏0问题，domain禁止反向导入0；Ruff format检查6个改动Python文件通过，git diff --check通过。没有改默认scope、MA反馈次数、总期限、引用白名单、数据库或知识发布规则。
