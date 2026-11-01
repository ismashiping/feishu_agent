# P7-01：科研选题现状调研报告核心链路

2026-10-28。覆盖 P7-F01–07、P7-T01–09。依据用户本次明确启动指令复用 Phase 6 技术基线；其真实模型/医学人工验收缺口保留，不视为已通过。先冻结本契约与测试，再实现，阶段末集中测试。

输入 QuestionRequest：question 即科研想法原文，约束在原文/QueryPlan，scope/options/pubmed 沿用。CLI ask --report（可 --format markdown）、POST /v1/reports、飞书 /report 加空格和科研想法调用同一 ResearchService.report。原问答/分析入口保持。图内 plan/retrieve/analyze/report 串联，澄清提前结束，不手工注入分析结果。

输出 ReportResult：ResearchReport JSON 和同一对象确定性渲染的 markdown。八部分依 SPEC，全部分析项形成有稳定 claim_id 的 claims 并保留来源、认识状态及支持状态；研究方向由候选缺口确定性转成待调查假设，不新增研究设计生成。保留 Phase6 原始结构化分析以便复核，不静默删除审核不通过的结论。参考编号依首次使用稳定产生，仅实际引用来源列入 references；仅发现的其他来源留 analysis.sources，不列为支持文献。

校验分三层：本次检索来源/片段与分析身份一致；本地文件或在线 XML 快照 hash/原文定位核对；有 PMID 的引用通过现有 PubMedClient 的有界批量 EFetch 核对标题、DOI、PMID、撤回/更正。无 DOI 合法；本地无 PMID 官方校验 not_applicable。快照不可用或官方服务失败是 unavailable，报告 verification_incomplete；身份/hash/定位矛盾是 invalid，报告 rejected，不能改写或删引用掩盖问题。

每条非空分析结论（含研究类型、相似性理由、比较、缺口、研究方向）经过一次 LangChain 支持度审查调用，四态 supported/partially_supported/unsupported/uncertain。标注 basis 来自 model_review，不称确定性医学验证；假设保持假设。缺依据或 unknown 相似性只能 uncertain。unsupported 或确定性无效拒绝正常发布；partial/uncertain/服务不可用为 verification_incomplete；verified 仅表示本阶段定义的检查完成，不表示文献全面、创新或临床正确。content_status 独立记录 complete/partial/insufficient_evidence/needs_clarification。

预算复用 ResearchLimits，总期限覆盖规划、检索、分析和报告核验；官方批量核验最多20个PMID、单次总预算不超30秒、复用原配额门和有限重试；模型审查最多一次，输出/上下文有界；不构建循环/缓存系统。无文献/需澄清不调用审查模型，不产生缺口或方向。飞书按有限分段发送完整文本/引用/审核状态，最多32段，超限整体明确报错而不展示残缺报告；每段重检lease/期限，任何失败停止，部分发送后不自动重试。

测试文件 tests/unit/test_citation_report.py 先于实现编写。开发者合成固定标注：真实引文对应 supported；含推断及局限的句子 partial；不相关或相反原文 unsupported；信息缺失 uncertain。100% 拒绝未知ID、元数据冲突、hash或定位篡改注入；合法无DOI来源不误拒。额外验证八部分、编号与JSON/Markdown一致、空结果/澄清、故障区分、假设不升级及整链路入口。合成标签不是医学人工签署。

阶段末命令：.venv/Scripts/python.exe -I -m pytest tests/unit/test_citation_report.py -q；-I -m pytest tests -q；-m ruff check src tests docs/learning/phase-07/demo.py；-m ruff format --check 同范围；-m mypy src；-I docs/learning/phase-07/demo.py。实际参数/日志见验收记录。

真实验收仍要求配置模型、官方PubMed及隔离数据库/检索，冻结真实文献快照和独立医学标签；身份/定位错误容忍为0，真实支持度精确率/召回阈值须在真实测试前由人工标注评审冻结，未齐备标待验收，不能以Mock或旧结果替代。学习材料六份齐备且全部必需验证完成才标整个Phase7完成。不实施Multi-Agent或Phase2/8/9。
