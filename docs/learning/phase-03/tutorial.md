# 从问题到 PICO

PICO 是人群 Population、干预 Intervention、对照 Comparison、结局 Outcome，帮助表达要查什么。例如“成人使用 aspirin 相比 placebo 是否改善 pain？”可以标出四项。诊断/预后问题可能不具备完整四项，缺失必须保留 null。

模型擅长理解自然语言，但可能补造字段。项目把理解与可验证规则分开：模型返回候选字段，Pydantic 验证类型，普通函数核对字符区间与原文。引用真实论文仍是独立业务；PICO 不能证明疗效。

SourceSpan 使用 Python 字符索引，起点包含、终点不包含。例如 `question[2:4]` 取第 3、4 个码点，emoji 不是按 UTF-8 字节计数。独立 ClassificationRequest 保留空白；现有 API/CLI 在 QuestionRequest 阶段已去首尾空白，因此应对照 QueryPlan.original_question，而非 HTTP 字节。

扩展词可帮助未来 PubMed 搜索，但它们不是用户给的事实，origin=query_expansion 且 source_span=null。PICO 只接纳原文引用。preserved_constraints 直接保留整个问题，继续使用原问题进行现有向量检索，防止只搜索实体而丢失“不包括妊娠”等限制；这不表示系统已经理解并执行每项限制过滤。

分类和抽取用一次模型调用，避免多次调用引入不一致。uncertain 且有具体歧义时要求重新提问；仅缺 comparator 不阻断。未知来源/错误区间不能靠继续生成掩盖。

先运行 Demo，再按代码流程阅读。练习为中英样例增加明确时间窗，观察保留的原问题与合法区间；不要把候选同义词填进缺失对照。
