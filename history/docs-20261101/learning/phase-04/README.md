# Phase 4 在线 PubMed 学习导航

另见2026-10-29科研改造的[第四阶段证据综述教材](openalex-stage4/README.md)，与本页历史PubMed阶段分开记录。

按 [原理](tutorial.md) → [代码流程](code-walkthrough.md) → [练习](exercises.md) → [排错](troubleshooting.md) → [面试表达](interview.md) 阅读。详细契约见 [P4-01 SPEC](../../specs/tasks/p4-01-pubmed-online.md)，真实测试与缺口以[进度](../../development-plan.md)为准。

运行 `.venv/Scripts/python.exe -I docs/learning/phase-04/demo.py`，使用 HTTPX 固定响应，不联网、不加载模型，不代表真实官方接口验收。正式问答仍需要已有 LLM/E5/DB 装配；独立 PubMed 客户端只需现有 rag 的 HTTPX 依赖。
