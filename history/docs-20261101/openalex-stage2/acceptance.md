# OpenAlex第二阶段交付与验收记录（2026-10-29）

## 状态与边界

已实现并完成本轮技术核验；独立医学相关性/代表性标签与签署仍待补，不能标完整科研质量验收通过。没有进入第三阶段全文改造。当前工作区原有大量修改，本记录只归属OpenAlex增量；未提交或覆盖用户已有修改。

## 已实现

- 新增domain/openalex.py：科研约束、日历日期解析、摘要倒排索引、DOI规范化、OpenAlex记录快照、逐篇评估与来源记录。
- 新增adapters/openalex.py：Works API、Bearer环境配置、日期过滤、相关性与时间排序、字节和期限限制、认证/限流/超时分类。不自动重试。
- 新增application/openalex.py：质量驱动最多两轮补检、文档去重、硬约束预过滤、批量语义筛选、坏项排除、证据缺口与审计记录。无合格文献不补齐名额。
- 扩展已有PicoPlanner与QueryPlan，同一次模型抽取携带科研意图；唯一逐字原文引用由代码确定偏移。时间/回答要求不作为论文关键词；显式研究终点不因粗粒度task字段被丢掉。
- 改造domain/models、retrieval、research、analysis及citations，新增真实OpenAlex来源与快照验证，复用既有生成与可信引用；SnapshotVerifier支持原始摘要位置。完整快照不进入生成/分析/审核Prompt。
- command_runtime/api_runtime唯一在线发现源均改为OpenAlex；飞书继续共用此装配，保留有界线程池、Redis幂等与sender。历史PubMed离线解析、测试与快照保留，不作运行时检索兜底。PMC仍只作已有文献全文获取，不作在线发现。
- CLI新增--openalex-query；旧--pubmed-query及非默认的PubMed调优参数显式拒绝，不把PubMed语法偷偷映射到新API。API通用question/scope接口继续使用。OpenAlex参数使用openalex对象。
- 没有发布候选入库，因此本阶段不改数据库Schema或全文缓存。数据持久化身份迁移属于下一阶段。

## 冻结与测试顺序

先核实官方契约，采集六组各8条真实API响应及请求/hash manifest，写入docs/specs/openalex-stage2.md；再创建首批测试，然后实现。阶段末集中执行测试，不将任何执行标为RED。集中验收中发现真实失败后新增对应断言并修复，修订写入SPEC，保留原失败结果。

固定模型输出用于边界、五题/跨领域意图契约及管线传递，不证明真实模型识别率。实现后补充engineering-review.json，明确其不是预先冻结的独立医学gold标签。独立相关性标签这一门槛尚未完成。

## 实际命令与结果

环境：Windows PowerShell、项目.venv Python3.12、锁定依赖；网络调用在获得网络访问权限后执行。fixture采集与OpenAlex冒烟使用匿名公共访问，未持久化对话中提供的密钥。真实模型使用现有.env配置的deepseek-chat，凭据未输出到结果。

|命令/范围|实际结果|证据|
|---|---|---|
|pytest tests/unit/test_openalex.py 首轮|20通过、1失败（时间测试缺time_text），已修复|本轮工具输出|
|pytest 全部默认离线范围 首轮|1355通过、1失败、122未选中；旧CLI仍期望PubMed语法成功|openalex-regression.txt|
|pytest 全部默认离线范围 修复后|1358通过、122未选中、1个既有protobuf弃用警告，158.87秒|openalex-regression-final.txt|
|pytest 受影响8文件，包含PICO/研究/分析/报告/runtime/历史在线契约|202通过、1未选中，9.80秒|openalex-affected.txt|
|pytest tests/unit/test_openalex.py 最终31项|31通过，3.31秒；包含预算耗尽、本地复用与旧CLI调优参数拒绝|openalex-contract-cli-final.txt|
|ruff check src tests scripts/openalex_smoke.py scripts/openalex_research_check.py|通过；另修复两个相关历史查询测试的格式/导入，无语义变更|openalex-ruff-final.txt|
|python scripts/openalex_smoke.py|真实200响应，10条规范记录，warnings为空|本轮工具输出|
|python docs/learning/phase-02/openalex-stage2/demo.py|成功读取真实fixture、验证快照并算出2024-10-29起点|本轮工具输出|

全量回归发生在最后的逐篇筛选/偏移/预算修复之前，不能冒称最终源码又跑过全量；随后按项目要求重跑受影响范围，预算修复另由最终31项覆盖。122/1未选中是外部/数据库/Redis/性能等opt-in，不算通过。本轮没有真实数据库、Redis、飞书收发、Embedding模型或完整回答生成验收。

完整命令形式均使用 `.\.venv\Scripts\python.exe -X utf8 -m pytest ... -q --basetemp=<工作区目录>`；各范围/临时目录见SPEC及保存日志。测试后未继续无理由扩大回归。

## 真实五题链路

本次实际运行的是“真实模型规划 → OpenAlex → 真实摘要筛选”，不含全文、Embedding或最终回答。原始计划、查询、候选、快照和判定见live-check.json；原始模型输出受控保存在model-diagnostics.json，仅作故障定位，不执行其中内容。每题顺序单次耗时，不能作为P95或性能提升统计。

|问题|入选数|HTTP尝试|筛选调用|秒|检索状态|
|---|---|---|---|---|---|
|肝脏分割最新研究有哪些？|5|4|2|17.375|complete|
|肝脏肿瘤亚区分割最新进展有哪些？|0|4|2|14.25|complete|
|MedSAM与nnU-Net有哪些区别？|5|2|1|14.125|partial|
|最近三年MRI预测肝癌微血管侵犯有哪些研究？|5|2|1|12.0|partial|
|肝脏肿瘤分割目前有哪些技术瓶颈？|2|4|2|17.609|complete|

亚区分割0篇是本次证据缺口，不解释为领域无研究。模型仍可能错误评估直接性，独立医学审查未完成。方法比较与MRI题存在无效quote/额外字段，坏项排除且整体partial；没有把它们记为成功证据。

## 真实失败与修复依据

live-check-first/second/third.json保持各次原结果。首轮出现时间短语进入检索、抽取校验失败、整批筛选失败；后续观察到模型偏移错误、quote改写和额外字段。修复只处理这些已发生风险：时间与科学概念分离、精确唯一原句定位、全批ID集合检查后逐篇严格验收。没有模糊quote纠错或放过坏项。第三轮MRI检索曾因过度依赖粗粒度task列表丢掉MVI终点；现保留所有非时间科学锚点，末轮重新取回相关候选。无效项仍记录为partial，不能声称模型已稳定。

## 对比与费用边界

这是OpenAlex增量的失败修复对比，不是PubMed与OpenAlex同条件质量实验；旧调查结果不能拼成新系统提升百分比。检索源由PubMed变为OpenAlex；词面选择改为受约束语义判断；固定数量补检改为覆盖缺口触发。实际质量指标Recall/Precision、独立医学支持度均未验证。

每请求最多4次HTTP、2次筛选、40个在线候选快照及40个筛选池位置（可能含本地）；输入JSON<=24000 UTF8字节，输出<=16000字节，受期限约束。本轮真实脚本使用max_tokens=4096；生产配置默认值可能更小，建议按本阶段示例设置LLM_MAX_TOKENS=4096以减少结构化输出截断，截断不会被算通过。未采集真实Token用量或账单，不能提供费用数字。新增在线摘要发现不执行Embedding；混合模式仍有原本本地查询编码成本，不能声称整个请求零Embedding。

## 学习与剩余事项

学习材料在docs/learning/phase-02/openalex-stage2/，六份文档与可运行demo.py齐全。此目录命名不代表历史Phase2异步体验完成。

仍待：独立医学候选标签与签署、真实混合数据库/飞书端到端、新旧检索同条件对比、真实Token与冷/热缓存成本。OpenAlex的OA位置仅保留元数据，下载/许可复核/解析/缓存身份/段落重排序属于第三阶段，尚未实现。数值支持检查与多文献证据组织升级属于第四阶段，尚未实现。

本轮停止。新增业务能力已实现与技术测试通过，完整科研质量验收仍开放；不自动进入第三阶段，也不删除历史失败。

## 后续补验增量（2026-10-29）

已补一次真实模型+本地库+OpenAlex的hybrid问答，4篇真实来源，来源渲染错误已修复，113项受影响测试通过；106条独立复核材料已准备，尚未填写或签署。完整记录与限制见[补验结果](followup/acceptance.md)。上文“未运行真实混合数据库/完整生成”仅代表原交付时点；本轮仍未验收真实飞书发送、全文、冷/热缓存和独立医学支持度。
