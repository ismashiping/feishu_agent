# 方案A本轮最小实现记录

2026-10-29。生产改动限于application/pico.py、domain/pubmed.py、adapters/pubmed_online.py。备份位于.artifacts/plan-a-backup，before-sha256.txt保存修改前hash；未使用HEAD重置既有修改。

## 已确认根因及修复

1. PicoPlanner把Provider/JSON/schema/span/映射/状态等错误统一包装且不留诊断。新增静态阶段、响应hash及受控字段路径的warning日志，外部extraction_failed/extraction_timeout保持兼容。没有原文、raw模型响应、异常消息、Pydantic input/ctx或凭据。日志不带不可信JSON键。只在响应未超限后计算hash。
2. 当前concept_mappings.required与concept_groups没有一致性验证：固定中英/混合/跨疾病计划中，required=False的方法仍可成为AND组。现在Planner拒绝完全相同的可选词组被强制使用，诊断为mapping。它是严格校验，不是让模型自动删除用户必要约束。该检查不是完整医学概念关系验证；多义、上下位和混合组仍需独立设计/标注。
3. PubMed warninglist此前仅保存official_search_warning，丢弃短语警告细节。现在保留至多10条、每条300字符；属于结构化查询审计，默认不写日志。当前查询语义仍保持原实现，没有以全局去引号、全局AND或疾病关键词替换历史问题。
4. SearchProvenance.pmid_status明确区分候选去向、missing、已获取但选择未知、返回但获取未知、not_in_returned_set与unknown。只有自然ESearch来源且完整时才能判断未在返回集合；历史缺ID或部分失败保守unknown。fetch_metadata仍为定向获取，不构造自然搜索provenance。

## RED/GREEN

新增test_plan_a.py最初9项全部失败：4种安全诊断、4种可选约束冲突、1项真实快照状态判别。日志red.txt。GREEN与既有pico/PubMed/phase2回归118 passed，见green.txt。后补官方warning上限和跨疾病实际查询/显式覆盖测试；完整unit结果以regression.txt最终输出为准，未完成前不标通过。

其中人工构造响应全部注明synthetic；actual-zh.json来自既有真实验收，不伪造文献。已知PMID只用于断言不在自然返回集合，未加入查询或证据。

## 实际查询改善与不确定性

可验证改善：可选条件不会以完全相同组静默成为强制AND；显式用户query保持原样，中英、混合及无疾病方法问题的固定概念组仍按原预算构造。官方短语降级警告现在可追溯。

**没有证据证明自然ESearch召回提高。** 历史中文Count=3、获取3、保留3、引用3，损失位于查询召回而非候选截断。此次保留实际查询作为基线，不因想要命中特定论文而修改词汇。尚未实施完整概念关系DTO或字段编译，因为缺少本轮独立真实证据证明具体编译策略收益。

历史英文原响应已丢失，只能确认一次Provider响应后提取失败，不能断言是span或schema。新增诊断使下一次失败可定位阶段，但不恢复历史信息；没有放宽span、安全JSON或来源规则。未执行付费重试来碰运气。

## 预算与环境

没有增加LLM调用、搜索轮次、max_results/top_k、90秒deadline、30秒搜索/20秒提取或8次HTTP尝试限额。没有Embedding、缓存、索引或数据库变化。所有测试在现有.venv离线运行，本轮不创建/替换Docker容器，无真实模型/网络调用。完整unit最终结果另记录。

## 后续

### 继续执行后的最终结果

完整unit实际完成：**1110 passed、0 failed、0 skipped、0 errors、1第三方弃用警告，139.65秒**，见regression.txt。最终静态日志文案增加stage/hash后的定向13项回归通过，见final-targeted.txt；Ruff通过。没有修改关键断言以消除失败。

用户要求继续后，复用已有clinical-agent-e2e容器执行一次真实英文提取诊断，未启动/替换容器。此次Provider返回有效计划，通过全部校验；1次调用、input=2616/output=765/total=3381 tokens，3.54秒，无PubMed请求或回答生成。安全输出在`../final-acceptance/docker-e2e/plan-a-english-diagnostic.json`，原始响应仅保存于忽略的.artifacts/plan-a-backup/english-response.json（容器/tmp也有副本），未写入默认日志。

离线使用保存的修改前Planner和当前Planner回放同一真实响应，**两者均通过且结果一致**，见english-replay.json。因此不能将这次成功归因为代码修复，更不能宣称历史英文故障根因已查明。历史raw丢失这一限制仍成立。

真实响应保留广义liver tumors，同时把其亚型及相关研究表达放入同义组；这与架构文档要求的严格同义/上下位/相关方法区分不一致，是仍待解决的规划质量问题。无需固定疾病字典即可描述这个问题，但缺少跨疾病关系标注验证，不在本轮匆忙实现自动关系推断。此次生成的具体医学术语不得成为生产硬编码。

本轮实际查询编译逻辑未改，未进行新的自然ESearch，所以没有新的召回提升数据。新增的是可靠的失败定位和可选约束一致性防线，不是完整方案A全部任务已验收。

推荐下一次获准真实英文执行时采集本次新增阶段诊断，若span唯一匹配等缺陷真实复现再最小修复；不要先放宽校验。自然查询策略需按架构文档以跨疾病字段/关系fixture与真实QueryTranslation对照验证，不能仅凭日志可见或单测通过宣布科研发现成功。
