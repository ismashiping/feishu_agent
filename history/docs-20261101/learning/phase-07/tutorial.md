# 从零理解报告与引用核验

报告将同一结构化分析组织成医生和科研人员可复核的科研选题调研结果。只有检索或漂亮文本不够：来源真实、结论支持程度和检索覆盖范围是三件事。

底层按三层校验：先把分析绑定到本次检索，模型不能提供新的文献身份；再核验在线 XML 或本地快照的哈希、原始页码/摘要字符位置，以及 PMID 官方元数据；最后调用一次模型逐项审查支持度。supported、partially_supported、unsupported、uncertain 是审核建议，事实/推断/假设标签保持独立。

verification 的 verified 仅表示规定检查完成，不证明医学结论正确或创新。缺快照、官方服务不可用、支持度未知均 verification_incomplete，身份矛盾或 unsupported 则 rejected。内容范围另用 content_status 表达；例如字段缺失的 partial 报告仍可能完成既定核验。空检索不会生成方向，更不能证明空白。

最小例子见 demo.py：真实的合成字符串和固定模型替身说明原文引用是如何回指的；不存在的源文件不会伪标 verified。所有 Markdown 来自 ResearchReport 同一对象，文献元数据来自可信来源字段。研究方向只是把已有候选缺口转为待调查假设，不自动设计研究或宣称可行。
