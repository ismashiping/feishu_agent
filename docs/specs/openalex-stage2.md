# OpenAlex 第二阶段冻结 SPEC（2026-10-29）

范围：唯一在线文献发现源替换为OpenAlex，扩展已有Planner，摘要语义筛选、质量驱动补检与可信引用接入。不下载全文，不更换模型，不建设新Agent。历史PubMed离线入库、快照和测试保留；新runtime不得装配PubMed。在线候选保持请求局部快照，不发布入库，本阶段不改documents数据库schema；第三阶段迁移全文缓存身份。

## 官方契约

核查日期2026-10-29：
- https://help.openalex.org/api/authentication/ ：Bearer认证；配置OPENALEX_API_KEY，日志不含认证或请求完整URL。
- https://help.openalex.org/api/searching/ ：GET https://api.openalex.org/works，search英文AND/OR及引号；默认相关性，另以publication_date:desc补充近期候选，不用PubMed字段语法。
- https://help.openalex.org/api/filtering/ ：filter=from_publication_date:YYYY-MM-DD,to_publication_date:YYYY-MM-DD；类型可filter type。
- https://help.openalex.org/data/works/attributes/ ：id、doi、title、authorships、publication_date/year、primary_location、abstract_inverted_index、open_access、best_oa_location、locations。
倒排索引按非负整数位置恢复；重复位置/非连续位置/类型非法不猜字补齐，记录invalid_abstract；null为空缺。正文缺失不得支持结论。

## 模型与输入输出

复用ExtractionDraft/QueryPlan，新增ResearchConstraints：原文锚定对象、任务、数据类型、论文类型、回答维度、时间意图。字段必须引用问题原句；英文表达复用concept relations/groups；不硬编码医学领域词典。时间识别由同次LLM结构化抽取，日期由注入today确定性解析。latest默认24个月，relative_years转12*n，explicit_years按自然年，classic无近期限制；“目前”不自动当latest。显式API日期与问题日期取交集，冲突失败，不静默覆盖。未知时间意图不得声称满足最新。

OpenAlexRecord：官方ID/规范DOI/作者/日期精度/摘要/期刊/OA信息/完整记录canonical JSON及hash；保持ID为OpenAlex，不伪造PMID。OpenAlexProvenance：轮次、实际查询/日期/排序、获取时间、候选去向、模型评估及预算/缺口；与旧SearchProvenance用不同endpoint区分。候选评估为direct/partial/irrelevant/uncertain，原文quote、研究对象/任务/模态/类型符合度、实验信息、创新/代表性依据、覆盖的回答维度；quote必须来自标题或摘要，ID必须为此次候选。无摘要不进入生成。partial不补满名额。回答保留可信书目和快照校验。

## 预算与补检

最多2轮、每轮2查询：同一概念的相关性与发表时间排序；第二轮仅扩展表达，不放宽硬约束。最多4 HTTP尝试（无自动重试）、40唯一候选（每响应最多10）、2次批量筛选LLM调用；每批输入JSON UTF8最多24000字节，输出最多16000字节。采用可直接执行的字节上限替代前期草案未经验证的Token估计，不宣称精确Token成本；截断按整文献执行并标记去向。查询30秒，筛选与检索合计最多45秒并服从传入总deadline。时间预算耗尽保留partial和原因；零成功请求抛分类错误。筛选失败不回退词面“伪合格”，可返回证据缺口。只要缺少直接证据或请求回答维度未覆盖，预算允许则补检，与返回篇数无关。以相关性/实验信息/代表性/OA/时间作稳定多因素次序，引用量不当质量分。非OA直接研究可入选。

混合模式对本地和在线候选使用同一语义筛选，既有本地历史文献可复用；自然语言日期同时约束本地候选，按DOI/OpenAlex ID/已有PMID去重，冲突记录；不混合比较向量分和OpenAlex分。在线元数据缺摘要保留审计，不能据标题生成方法或结果。

必要异常：HTTP401/403认证、429限流、超时、坏响应分类；部分请求失败可继续并记录。响应字节上限5MiB，不跟随重定向；SDK异常消息不外泄。旧pubmed参数明确拒绝，CLI增加--openalex-query，通用问题/scope接口兼容。无完整科研约束的旧抽取结果在OpenAlex路径失败，不假称识别成功；旧离线调用兼容。

## Fixtures及人工复核

tests/fixtures/openalex/{organ,subregion,comparison,mvi,bottlenecks,holdout}.json及manifest为真实匿名API响应，保存请求、时间和hash。测试内合成记录仅用于边界，不将合成ID/DOI作真实证据。五题意图预期：器官分割+latest、肿瘤内部亚区+latest、方法comparison无疾病限制、MRI+肝癌+MVI预测+3年、肿瘤分割limitations无自动近期限制；另以脑肿瘤问题检查无领域硬编码。相关性标签为工程审查建议，独立医学签署待补，不能标医学通过。

## 验收与命令（阶段末执行）

先写tests/unit/test_openalex.py，再实现。必需验证倒排索引、快照篡改、缺摘要、日期月底/闰年/交集、真实fixture规范化、五题意图原文锚定、多轮去重、质量不足但数量足仍补检、无直接证据不填充、部分失败、预算、错误分类、引用往返与来源渲染、runtime无PubMed发现。复用离线完整测试；真实OpenAlex传输/真实模型/数据库分别记录，未执行不算通过。

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_openalex.py -q --basetemp=.pytest_openalex
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_openalex_regression
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe scripts/openalex_smoke.py
```

真实前提：联网、有效OPENALEX_API_KEY（匿名可验证公共契约）、已配置LLM与本地模型/测试库才可真实混合问答。smoke只测传输，不能代替科研质量端到端。阶段验收与学习文档完成后停止；不自动进入全文阶段。

## 集中验收中的契约修订（2026-10-29）

真实模型复验发现：有效原文引用可能配有错误Unicode偏移；一篇候选的错误引文或额外字段会使整批失败。修订为：新科研契约存在时，唯一逐字原文引用的偏移由代码确定，不接受模糊匹配，重复出现且模型定位无效仍拒绝；整批ID集合与信封先严格校验，逐篇严格schema/quote/维度校验，单篇失败标记partial并排除，其他已通过项可用。该行为不改变历史无research_constraints契约。新增对应测试后实施。编译时仅排除时间锚点，不因结构化task字段粒度粗而丢掉显式终点概念。原始失败记录保留。

CLI非默认PubMed排序/数量调优参数在本轮末明确拒绝，新增3个参数化验收场景；不静默忽略。最终新契约31项通过，详见验收记录。
