# 从源码学习当前系统

**推荐主线：[从数据流动学习整个项目](data-flow.md)**。先跟踪一次 HTTP 问答，再接入分析、报告、PDF 入库、CLI/飞书与维护；168 个函数入口均标注输入输出、职责、存在原因和源码位置。

学习目标：区分发现、缓存与证据；看懂 Pydantic 边界、LangGraph 编排、pgvector 持久化及有界执行。

按 [原理](tutorial.md) → [真实代码](code-walkthrough.md) → [练习](exercises.md) → [排错](troubleshooting.md) → [面试表达](interview.md) 阅读。

最小 Demo：在仓库根运行 `.venv/Scripts/python.exe -X utf8 docs/learning/current/demo.py`。它只验证当前公开输入契约，不调用模型、数据库或网络。完整科研流需要真实依赖，不能用 Demo 输出冒充端到端通过。

补充：[如何读懂科研链路验收](acceptance.md)，按实际资源生命周期、证据和审核流程
解释当前修复及可运行Demo、调试、练习和面试表达。
