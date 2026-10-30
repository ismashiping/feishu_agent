# MA-02 剩余角色及有限反馈

2026-10-28。实现Methods Analyst、Prior-Art & Gap Analyst、Research Design、Evidence Reviewer，复用单次EvidenceAnalyzer联合抽取与ReportBuilder审核，不为角色数增加无意义模型调用。Methods取得经门禁的联合草稿，Prior-Art独立校验比较/缺口及来源归属，Design生成与候选缺口一一关联的待评估方案（假设/范围/验证事项），Reviewer复用确定性引用和逐项模型审核。共同使用原LangGraph状态和总deadline。

报告链路：plan/retrieve/analyze(methods)/prior_art/design/report(reviewer)。分析入口也经过prior_art；普通问答不变。反馈只作用report：无证据或partial检索时可退回Scout按同一用户范围/名额/查询重新检索；unsupported可退回Methods重做全部受影响分析。不得自动扩大用户查询或修改来源；每轮重建比较/设计/报告，不沿用旧支持状态。缺信息unknown、官方不可用或身份冲突不盲目循环，保留不完整/拒绝。

默认最多1轮反馈，配置严格整数0–2；原总期限不重置，图递归上限按轮数有限增加。最多一次规划、每轮至多一次分析与审核（总最多7次模型调用，真实次数可能更少）；配置0兼容单遍。耗尽保持最终拒绝/不完整，记录反馈轮次/目标/停止原因；不能因预算耗尽标verified。共享状态只存结构化记录，不执行文献中的指令。

先编写tests/unit/test_feedback_agents.py。阶段末验证：四角色顺序、unsupported重分析后通过、持续unsupported耗尽仍拒绝、空结果重新检索后重建、0轮/非法轮数、原文引用错误不得反馈绕过、旧入口和冻结基线不变。使用合成替身及冻结回放，不新增付费/联网。医学与真实E2E缺口不标通过。只运行受影响联合测试/质量检查，学习说明和进度同步，不实施Phase8/9。
