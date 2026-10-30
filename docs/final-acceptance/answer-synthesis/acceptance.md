# 科研回答组织与展示验收

## 真实调用链与根因
ResearchService._prepare 把原问题、QueryPlan、SearchProvenance、证据文本与定位传给 GenerationInput；LangChainAnswerGenerator.generate 单次生成结构化 claims。parse_draft/build_answer 检查 JSON 和引用身份，组装可信书目并添加统一局限。Feishu Sender 调 render_answer，默认 _readable_answer_lines，显式 include_audit=True 保留完整旧审计。
模型原指令未约定首段结论、按科研观点综合及任务单位核对；确定性 build_answer 又追加摘要/检索/免责声明。旧默认 renderer 同时逐 claim、逐 source、全局显示这些信息，造成重复。原默认全文定位被隐藏；有 PMID 时 DOI 被 elif 隐藏。

## 变更
- src/clinical_agent/domain/research.py：仅修改 INSTRUCTIONS，原问题优先于失真的 QueryPlan；先核对人群、任务、分析单位、结局；任务不匹配先给带引文 uncertainty；按发现、方法比较、单篇分析、空白问题组织；支持有依据的跨论文综合，禁止无依据合并结果/优越性；不强制引文数量，要求不重复泛化局限。
- src/feishu/sender.py：相同局限精确去重并保留引用集合；按来源类型合并证据范围；精确已知系统提示转换为等价简洁展示，其他未知或具体限制保留；保留语义仍需人工核验提醒。默认显示全文页/章节/字符偏移，不伪造段落号；同时显示可信 PMID 与 DOI。complete/partial 请求状态独立于候选截断。局限合并不会修改 ResearchAnswer 原对象，审计模式不变。
- tests/unit/test_answer_synthesis.py：9 项新增用例；真实摘要与测试替身明确区分。

## 参考设计及取舍
借鉴 [PaperQA2](https://github.com/Future-House/paper-qa) 的证据到引用回答组织、[OpenScholar](https://arxiv.org/abs/2411.14199) 的多论文引用支撑综合。未移植额外证据摘要、迭代反馈或检索节点，未引入其模型、依赖或数据集。不能据此宣称获得这些系统的质量。

## RED / GREEN / 回归
red.txt：三个新增展示/指令合同测试失败；green.txt：138 passed；snapshot.txt：9 passed；render-final.txt：82 passed。
首次全量 regression.txt：1119 passed、1 failed、1 warning。失败是原默认 renderer 缺少本地模式显式“未执行在线 PubMed”提示，未删除断言，已恢复。scope-regression.txt：96 passed。最终全量见 regression-final.txt。
旧引用门禁测试覆盖未知 UUID、重复/错配引用、伪造书目信息、输出超限、上下文超限、失败清洗；飞书测试仍覆盖安全 URL、at 转义和完整消息超限回退。未放宽来源、引用或 deadline 规则。

## 来源与真实生成检查
既有 actual-zh.json 的真实不匹配摘要仍用于原问题/内容/预算传递测试。工作区未找到用户示例的器官分割摘要快照，因此额外从官方 EFetch 定向取 PMID 24962337，保存 organ-segmentation.xml（SHA256 见 metrics.json）。这是负例资料获取，不是自然 ESearch 召回结果。没有加入生产候选。
中文/英文/混合负例采用官方摘要、人工保守回答与合成 identity/embedding 测试环境：只证明链路与引用一致，不证明模型能力。
另通过既有 deepseek-chat 做一次真实负例生成（live_negative.py / live-negative.json），无 Docker、无 ESearch、无额外生产节点。一次模型调用：1197 input + 330 output = 1527 tokens；上下文 5848 字符，小于24000。
人工核对：首条 uncertainty 明确整肝分割不能支持肿瘤内亚区研究；统计图谱初始化可变形模型、化学位移脂肪分数、14例MR、与另外两种图谱方法比较，均在官方摘要中。未出现凭空具体数值结果或肿瘤内亚区方法。
限制：模型说“唯一检索到的摘要”，本实验实际只提供单个固定摘要，故检索过程措辞仍不精确；两条后续内容有重复，摘要级局限仍有不同措辞的重复。未进行多轮调优，不用模糊文本规则删除潜在重要限制。

## 前后对比与预算
render-before.txt / render-after.txt 使用相同真实模型响应，隔离展示差异（并非生成质量 A/B）。714→691字符；减少重复系统提示、合并局限且保留来源关联，双标识补全；不能将字数变化视为医学质量指标。
请求轮次、max_results、top_k、总 deadline、max_output_bytes 和24000字符限制均不变；提示更长会占用更多固定上下文空间，既有真实快照仍可容纳，但极限长上下文仍可能触发 context_limit，未扩大上限。未实现上下文重排或全文RAG。

## 未验证及边界
未完成跨疾病真实模型评测、多论文综合准确率、真实中英文检索与飞书用户端新回答验收。当前测试中有确定性真实内容快照，也有固定生成替身，两者不等同端到端科研质量。引用身份校验仍不能阻断所有医学语义错误；泛化和高风险结论仍需人工检查。
所有旧未提交改动保留；生产变更前副本与 SHA256 位于 .quality-backup/answer-synthesis-20261029。changes.patch 是相对于本轮副本的差异，不相对于 HEAD。

## 最终结果
最终完整 unit：1120 passed、0 failed、0 skipped、0 errors、1 条既有 SDK 弃用警告（127.15s）。Ruff 通过，mypy 两个生产文件通过，最终9项新用例再次通过。固定 Compose 项目复用 API c10bdb4a0f06 与飞书 86c384d4af78 执行 restart，无新容器/卷/镜像构建。
