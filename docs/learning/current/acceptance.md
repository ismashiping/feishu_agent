# 如何读懂本次科研链路验收

## 是什么、为什么需要
验收证明某一份源码在明确环境与输入上满足哪些断言，不是“全部功能永远正确”。
本项目需分别看运行成功、引用可追溯、模型支持度和独立科研/医学质量。
入口返回verification_incomplete仍可能是正确执行，必须核对原因。

## 按真实执行顺序读代码
1. research_runtime.open_research_service显式创建HTTP/LLM资源，退出关闭；
   本地E5加载在Graph请求期限前，数据库由入口管理，不因导入自动连接。
2. application.research.ResearchService.report设置请求deadline并调用LangGraph。
3. PicoPlanner.plan校验用户原文与检索概念，扩展词不能冒充必要锚点。
4. OpenAlexRetrievalService.retrieve在线发现筛选；FulltextService.enrich仅处理选中论文。
5. paper_key按DOI或OpenAlex ID标识论文，PostgresFulltextStore.load按key/signature/TTL查缓存。
6. 未命中才下载/解析/切分/Embedding/事务发布；命中则在同论文内向量检索。
   安全URL/身份检查、失败警告和资源预算仍有效。
7. EvidenceAnalyzer把实际片段变为句子目录，模型选择quote_id，程序复制原句。
   sample_size_scope区分当前研究、综述汇总、被引单项研究与未知主体。
8. ReportBuilder核对来源与引用，review_context携带用户想法和比较约束；
   同时按输入字符和最多6条论断分批审核。每批响应须恰好覆盖请求ID。
9. ResearchService按剩余时间和反馈轮数决定继续或返回当前报告。被拒报告不能
   因预算不足变成通过。Graph结束后输出结构化JSON及render_report的Markdown。

```mermaid
flowchart LR
 A[原想法] --> B[规划校验]
 B --> C[在线发现与筛选]
 C --> D[按选中论文查缓存]
 D --> E[全文获取或复用]
 E --> F[全文RAG和证据句]
 F --> G[分析与引用核验]
 G --> H[有界分批审核]
 H --> I[反馈准入检查与报告]
```

## 可运行最小Demo和调试
仓库根执行：
```powershell
.venv/Scripts/python.exe -X utf8 docs/learning/current/demo.py
```
它仅演示公开请求边界，不调用外部服务，不能冒充全链路。
实际验收入口、命令、环境和结果见 ../../acceptance/consolidated-20261102/README.md。
有凭据且已获调用授权时才运行对应真实脚本，脚本拒绝覆盖已有产物目录。
调试时先看events.json阶段错误，再看逐批输入/输出和报告审核依据，勿打印密钥。
not_reviewed不是模型给出的不确定判断；basis非空也不代表审核成功。
finish_reason=length代表输出截断，不应解析残缺JSON或自动标记支持。

## 练习
- 修改练习：只在隔离测试中降低字符预算，运行test_review_context_bounds.py，
  观察批数而不是删除引用使测试变绿。
- 修改练习：给综述输入cited_study样本选择，运行test_sample_size_semantics.py，
  确认样本字段留空且来源仍存在。
- 独立实现：从验收JSON统计每批claim_id，检查每条恰好覆盖一次；
  再按缓存key区分实际命中与新下载，不能用总耗时推断命中。

## 30秒口述
“我把系统验收拆成离线正确性、真实业务执行和科研质量。真实链路使用OpenAlex
发现论文，按论文身份复用全文缓存，RAG选片段，模型分析后通过原句和位置校验。
审核按输入和输出预算分批，保存逐批覆盖证据。即使报告返回，部分支持或未知仍
保留，引用存在不能证明创新性或医学结论正确。”
