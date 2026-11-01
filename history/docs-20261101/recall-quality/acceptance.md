# 本轮交付与未通过验收记录

## 1. 现有流程和真实根因

实际链路：用户 → ResearchService.plan → IdeaPlannerAgent → PicoPlanner → LangChain extract → QueryPlan → LiteratureScout → PubMedRetrievalService → query_text → PubMedClient → ESearch相关性排序分页 → EFetch → XML摘要 → 治理/摘要/来源过滤 → select_candidates词面覆盖选择 → hybrid合并 → 生成/分析 → 引用核验。详细历史链见 ../research-quality-investigation.md；其中部分代码位置和“尚无来源ID列表”的描述已由后续代码更新。

当前不是全局OR。当前单查询限制、同义词组无法表达关系、带引号的长短语过窄均有源码/本次真实请求证据。历史具体论文丢失阶段仍未知。原始英文提取故障raw丢失，根因未确认；不得由后来成功回放认定修复。

失败定位：规划失败发生在ESearch之前；未进入ESearch前20不等于PubMed不收录；返回但缺摘要/治理阻止和top_k未入选分别有candidate_outcomes；引用覆盖与原始候选召回不同。本次亚区真实请求ESearch为0，未发生分页/过滤/排序损失，所以不能归咎于RRF或回答生成。

## 2. 修改模块和理由

- domain/pico.py：新增有原文锚定的ConceptRelation，保留旧字段/入口；区分7种关系、required、confidence、verification。来源必须存在于原问题，扩展不可变必需锚点。医学关系本身仍为模型候选。
- application/pico.py：传递关系计划；记录空响应及分类诊断，保持外部错误码兼容，不记录原文/raw/异常消息。没有增加重试或将失败伪装成规划成功。
- domain/pubmed.py：直接/补充查询编译，显式query优先，旧计划保持旧行为；诊断DTO新增trace与逐轮信息。
- adapters/pubmed_online.py：直接候选不足5条（或max_results更小）时最多一次相关/下位补充；组内OR，锚点间AND；不自动上位扩展。日期、排序、候选总预算、HTTP总尝试预算和deadline共享。

## 3. 关键实现与限制

不增加top_k、不修改RRF/飞书/全文/报告。每轮保留策略、真实查询、translation、官方警告、ID和累计HTTP尝试。UUID在检索开始后生成，尚不是贯穿规划/生成的统一trace。total_count仍为首轮匹配数，各轮计数见query_rounds，不能相加当作去重总数。候选少触发补充已实现；候选质量差/已知关键论文缺失触发尚未实现。未实现自动医学关系验证和自动安全降级；显式query绕过规划仍为原有能力。现有词面排序保持不变。

## 4. 测试集和评价方法

compare_recall_queries.py冻结6个公开问题：两个原题、英文胶质母细胞瘤异质性/MRI Habitat、中文肺癌预测、英文乳癌诊断、量子瞬移分割负例。时间固定2020-01-01至2026-10-29，相关性排序，候选10。before使用旧concept_groups，after同一固定计划加关系字段；这仅为编译器/API对照，不是旧模型与新模型的同条件试验。负例零命中不证明不存在直接研究。

已复用既有Phase9评价器的设计与回归，尚未提交符合其契约的完整独立标签集；不新建重复评分系统。已有independent-pmids.json可追溯39752907/40601290/41058349，但不足以覆盖跨疾病标签。A=直接完成目标任务，B=相关方法/任务，C=背景或不相关；需要基于论文原文独立复核，不能从本次搜索排序反推标签。未完成独立标注与医学签署，因此Recall、Precision、MRR、关系准确率、已知论文覆盖率和端到端成功率均为未验收，不填写虚构分数。

## 5. 实际量化结果

修改前定向测试：85 passed，2.92秒。修改后同范围加关系及诊断测试：101 passed，2.66秒（数量不同，不能当质量提升百分比）。扩大回归216 passed，1 deselected，6.02秒；最终重跑结果见regression-final.txt。deselected是真实在线opt-in项，未当作通过。另行真实请求不替代该测试本身。

真实ESearch/EFetch对照（before→after候选数/耗时秒）：

|问题|候选数|耗时|
|---|---|---|
|肝脏分割|10→10|2.28→1.97|
|肝脏肿瘤亚区分割|0→0|0.66→0.97|
|胶质母细胞瘤|10→10|2.02→1.59|
|肺癌预测|10→10|1.39→1.86|
|乳癌诊断|10→10|1.88→1.91|
|负例|0→0|1.89→0.91|

这是单次顺序运行，不是延迟统计，不能判断显著变化。原题亚区补充调用由1次ESearch变为2次，仍0命中；查询成本增加而未证明收益。完整请求、XML来源、ID见live-comparison.json。

真实deepseek-chat→规划→PubMed：原题1发生extraction_failed（plan阶段），原题2计划通过但直接/补充均0。见real-planner.json。不能声称规划稳定性或原题修复通过。本地模型配置缺失；真实模型改为在已有Docker API容器的独立/tmp副本运行，复用环境变量，不替换镜像或服务。此操作不是Docker HTTP服务验收，未测试本地库、HTTP服务或飞书。

## 6. 剩余缺陷与下一步

本次没有达到用户要求的成功标准，状态为开发中/未验收。尤其不能认定“无明显损害原能力”：跨疾病目前只有候选数，无独立相关性评价；且新模型输出一次校验失败。需采集新失败的受控raw并定位具体校验；在通用概念粒度/形态变化和字段策略上继续改进，然后冻结独立A/B/C标签及模型双版本基线，再决定启用或撤回新路径。旧concept_groups仍被兼容支持。

OpenAlex官方MCP支持Streamable HTTP/OAuth，可作为补充数据源；但它不自动修复概念关系和约束错误，也不能将OpenAlex命中视为PubMed收录。接入需要独立适配元数据/标识/来源和权限，不在本次擅自替换。官方说明：https://help.openalex.org/access/connector/ 。
