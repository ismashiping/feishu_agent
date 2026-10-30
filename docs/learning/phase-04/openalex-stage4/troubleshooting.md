# 运行与排错

`limited_independent_evidence`：有直接证据但未达软覆盖目标，不表示答案一定错误或领域没有更多研究。检查实际查询、第二轮是否不同、筛选引文与任务是否匹配，再看超时/截断，而不是降低相关性门槛。

`duplicate_study`：题名与摘要同时相同，虽然DOI不同，也不算两项独立工作。不同版本摘要不同不会被该规则合并，这是已知覆盖边界。

`fulltext_license_not_allowed`/`location_unsupported`：本轮没有扩大出版域名和许可白名单。预算修复只能让后续合法来源有机会，不能使所有论文都有全文。不要绕过来源校验。

采集问题仍召回Patients：看section_priority是否识别问题；再查payload中是否真的有Image acquisition，以及补入候选是否保留原始chunk ID。不能凭章节名生成不存在的扫描参数。

`citation_invalid`：保存生成context与draft，比较引用ID和已供应段落，核对文档身份、原文区间。不要删除错误引用后发布剩余文本。本轮真实检查脚本会保存模型原文；失败记录与成功分开。

真实检查有两种：scripts/oa_quality_check.py的replay使用冻结候选、可重新召回全文并调用真实模型；live重新规划/在线发现。两者都可能失败，不能把回放作为新在线召回率。结果见验收文档。

默认渲染不显示候选截断数量；需要排查时用render_answer(include_audit=True)或API provenance。研究特定限制仍可见。Prompt要求综合写作不等于保证模型遵守；必须阅读真实生成文本再评价。

本轮有实际反例：一篇原始论文的Methods也描述了对照基线，模型把基线输入机制归给主模型。只加“不要混淆”提示仍失败。缓存中本有Network architecture，但没有召回；补齐架构段后，冻结证据再生成才纠正该例。文章标题不等于段落主体，章节召回也必须覆盖用户真正要比较的内容。这不是可以靠引用ID门禁解决的问题。

飞书收到“研究处理失败”时，先用request_id关联admission与delivery；delivery=sent可能只是错误提示送达。2026-10-30同题隔离复现发现比较规划生成6个answer_dimensions，而Schema最多5个。修复在PICO_INSTRUCTIONS明确所有方法名与维度合计最多5项，优先用户要求并合并相关维度；不扩大DTO、不截断、不添加重试。tests/unit/test_pico.py回放真实6项fixture仍应失败，合法5项保留两方法；提示词断言只检验指令存在，真实供应商仍须复验。原始失败及后续结果见第四阶段feishu-e2e-20261030.md。
