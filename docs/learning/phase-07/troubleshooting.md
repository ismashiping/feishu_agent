# 运行与排错

CLI 示例：`clinical-agent ask --report --format markdown --question "科研想法" --model-dir <已有E5模型目录>`。Windows 导出 Markdown 推荐 `PYTHONUTF8=1` （或在解释器支持的入口使用 `-X utf8`），JSON 默认用 ASCII 转义保持管道可读。API POST /v1/reports 请求结构与 questions 相同，返回 report 与 markdown。飞书发送 `/report 科研想法`；普通文本仍走旧问答。

需要现有模型路径、数据库与 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL；不要输出密钥。官方核验仍遵守 PUBMED 配额与联系信息约定。没有新迁移或依赖。

citation_invalid：分析来源或片段不属于本次检索、元数据/位置被篡改。rejected：快照或官方身份冲突、来源撤回、审查 unsupported，必须复核。verification_incomplete：缺快照、官方服务不可用、模型输出非法/超预算、unknown 或 partial 支持，不能标全核验。

research_timeout：总期限耗尽，不会无限重试；context_limit 沿原分析预算处理。支持度审核超预算保留 uncertain。缩小实际 top_k 与文献片段范围，保留检索限制，不能以省略坏引用绕过门禁。

飞书最多32段，每段保留序号；失败即停止，不能将部分发送称为完整交付。超出上限整体错误，不截断引用，请用CLI/API获取完整报告。本地文献快照必须保留在可读路径，源文件消失时仅有 hash 不足以完成原文核验。
