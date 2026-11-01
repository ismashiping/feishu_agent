# 按实际顺序阅读代码

1. **api/schemas.py → api/routes.py**：QuestionBody 接收外部 JSON；请求 ID 从请求上下文进入 QuestionRequest。local 不在允许值中，因此不会提交科研任务。
2. **api/execution.py**：WorkerPool 在 submit 前限制容量，线程中的实际任务完成后释放槽。请求取消不等于线程立即停止。execute 将已知业务错误映射为安全 HTTP 响应。
3. **api/runtime.py → research_runtime.py**：加载本地 E5，创建 engine，进入 LLM/OpenAlex/全文 HTTP 客户端上下文，yield 服务；退出时按上下文释放资源。禁止 import 时创建客户端。
4. **application/research.py → agents/graph.py**：ResearchService 的 answer/analyze/report/respond 共享运行逻辑和 deadline。图调用节点，根据规划选择澄清、问答、分析或报告。
5. **agents/nodes.py → application/openalex.py**：Scout 将问题和规划交给在线发现与筛选；Works API 是生产发现源。模型筛选返回的 JSON 仍在边界验证，不因使用类型注解省略真实性规则。
6. **application/fulltext.py → application/oa_fulltext.py**：遍历选中论文，查 load(key, SIGNATURE)，再下载和向量化。db/fulltext.py 读写缓存。未命中的本地 PDF 不会被独立发现。
7. **application/research.py → domain/citations.py**：选片段、控制上下文、生成与核对引用。analysis.py 构造逐字事实与带验证说明的推断；report.py 组织报告并审核。
8. **channels/feishu**：events 过滤事件，dedup 管 Redis owner 租约，worker 有界执行，sender 发送并区分交付结果。它复用研究入口，不是另一套 RAG。

本轮类型修复将不同循环对象使用不同变量名，避免同一名字先代表 UUID 再代表字符串；JSON 上下文显式使用 dict[str, Any]。这类标注表达已有契约，不增加运行时分支。日期 cast 依赖已有 Pydantic 日期配对/精度校验；cast 本身不能保证值正确。

源码具体名称见 ../../source-index.md。历史学习材料仅作历史参考，不代表当前路径。
