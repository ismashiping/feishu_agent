# SPEC
链路：ResearchService._prepare → GenerationInput/INSTRUCTIONS → LangChainAnswerGenerator.generate → parse_draft/build_answer → ResearchAnswer → feishu.sender.render_answer/_readable_answer_lines。answer 引用门禁只校验标识，不是 report 语义审核。

确认：提示词未约定首段回答和跨论文综合；build_answer 确定性追加 BASE_LIMITATIONS、摘要/截断限制；渲染又逐 claim 输出局限、逐 source 输出摘要范围、全局提示与免责声明，导致重复。默认全文来源丢失页面/章节/偏移定位；同有 PMID/DOI 时 DOI 被省略。

最小修改：只更新生成指令（不改 JSON schema），保留意图区分与相关性自检；只更新默认渲染，精确相同局限合并且关联引用，已知系统提示合并为等价简短展示；保留未知局限和所有审计模式。不得用词面规则判定医学直接性。新增提示不增加调用或预算；校验 24000 上限与原有安全测试。

RED：重复限制/默认全文定位/双标识/提示合同测试应失败。GREEN 后用既有真实不匹配摘要快照和单篇定向获取的官方肝脏整体分割 XML 做数据流负例。无 mock 医学准确性声明；固定模型响应只能验证传递、引用与展示，真实生成遵循尚待验证。

参考 PaperQA2 的证据到带引文回答组织与 OpenScholar 的多论文综合；不移植额外摘要、检索或自反馈调用。
- https://github.com/Future-House/paper-qa
- https://arxiv.org/abs/2409.13740
- https://arxiv.org/abs/2411.14199
