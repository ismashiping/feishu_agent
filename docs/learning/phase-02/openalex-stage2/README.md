# OpenAlex 第二阶段学习导航

这里的“第二阶段”指2026-10-29科研检索改造，不是历史延期的Phase 2异步体验。能力与验收缺口见 ../../../openalex-stage2/acceptance.md。

按 tutorial → code-walkthrough → troubleshooting → exercises → interview 学习。目标是理解科研约束如何成为真实查询，候选如何凭可追溯摘要进入现有回答链。模型判定不是医学人工签署。

最小Demo位于 demo.py，在项目根运行 `.\.venv\Scripts\python.exe -X utf8 docs/learning/phase-02/openalex-stage2/demo.py`。它读取真实fixture、重建摘要和计算日期，不联网，不编码，不生成科研结论。
