# 冻结的OpenAlex协议fixtures

六个.json及manifest在本阶段实现前从公共API匿名获取，每组8条。manifest保存请求参数、获取时间与原始字节SHA256，不能用后续API变化覆盖这些文件。候选很旧是有意保留的真实负例：默认相关性搜索并不自动满足“最新”。

单元测试合成模型判定只用于协议、筛选状态与引用传递；不构成医学标签。engineering-review.json是实现后补充的源码/元数据人工工程检查，明确记录来源和待独立医学复核状态，不能用作无偏质量评价。真正独立的全量相关性与方法代表性标签尚未签署；不填Recall/Precision或医学通过率。

五题真实动态日期检索、模型输出及各次失败见 docs/openalex-stage2/。其中live-check-first/second/third保持原结果，live-check.json是最后一次执行。此处无凭据、无全文，无虚构研究指标。
