> 后续增量说明：本文原P3冻结契约保留；当前澄清决策由[探索型发现修复](exploratory-discovery.md)扩展，旧输出继续兼容，不追改原验收。

# P3-01：PICO 分析与查询规划核心链路

版本：1.0；日期：2026-10-28；状态：已按实施前冻结契约交付核心实现，阶段集中验收中。对应 P3-F01–04 / P3-T01–05；仅 Phase 3。

## 1. 目标与基线

现有 ResearchService 已有本地检索、生成、引用门禁；通用 LangChainAnswerGenerator/open_llm 已管理消息、JSON mode、超时及资源。没有 PICO 实现。直接扩展共享服务，不新增图引擎、数据库表、依赖、在线检索或异步任务状态。

## 2. 核心范围

一次受限模型调用同时分类与抽取，普通函数校验并构建 QueryPlan。图增加 plan、clarify 分支。CLI/API/飞书的正式装配默认启用；直接构造 ResearchService 可不传 planner 以兼容已有调用。该可选注入不是生产静默降级；已启用的规划失败必须报错。

## 3. 输入

ClassificationRequest(question, language_hint=null)：question 严格字符串，1–4000 Unicode 字符且非全空白，原样保留；language_hint 可选 zh/en/mixed。span 按传入该请求的精确 question、Python 码点半开区间。已有 CLI/API QuestionRequest 在进入规划前会去首尾空白；规划不再规范化，所有返回区间相对于返回的 original_question，不声称回指原始 HTTP 字节。

## 4. 输出与模型草稿

ExtractionDraft 只有 question_type、pico、ambiguities、terms，拒绝额外字段。分类 intervention/diagnosis/prognosis/etiology/other/uncertain；PICO 四项必需但可 null。ExtractedField(text, origin, source_span)：user_text 必须与合法 span 的原文精确相等，query_expansion 必须 span=null。PICO 只允许 user_text；扩展词只进 terms，避免给缺失 comparator 补值。文本最大 4000 字符、terms 最多 20、ambiguities 最多 5（每条 500 字符），草稿最多 32000 UTF-8 字节。

QueryPlan(version=pico-v1, original_question, structured_question, terms, preserved_constraints, search_intent)。search_intent 等于问题分类。为保留否定、剂量、人群和时间，preserved_constraints 固定保留整段原问题及其区间；本阶段不声称已穷尽结构化限制。模型 terms 不替代原问题，检索仍用现有 QuestionRequest。扩展词仅是候选，不自动产生医学事实。

## 5. 分支规则

uncertain 且 ambiguities 非空 → needs_clarification；不检索、不生成医学结论。其他分类即使 PICO 不完整或有非阻断歧义也可继续；四项皆有值为 complete，否则 partial。uncertain 无具体歧义也允许 partial 继续，不让模型单凭类别阻断流程。非医学问题可为 other，未命中走现有证据不足。

## 6. 服务输出

ResearchAnswer 新增可空 query_plan，status 增加 needs_clarification。该状态必须无 claims/sources 且有需要澄清的计划；正常/证据不足结果不得带阻断计划。JSON 返回完整计划；飞书纯文本显示分类、PICO、扩展词及歧义，沿用现有文本转义/完整结果长度限制。既有引用验证不放宽，原问题继续进入生成上下文。

## 7. 模型与资源

复用现有 LangChain 标准消息、模型配置、HTTPX/总期限、无重试、禁 tracing。抽取固定系统指令，原问题仅作为 JSON 数据。planner 默认 20 秒/32000 字节，服务传入不超过研究剩余预算。返回后再次检查期限；同步调用不能保证强制打断线程，不新增线程。超时 extraction_timeout，其他抽取/格式/span/来源错误 extraction_failed；不回显原始异常，不返回伪造计划。API 分别映射 504/502，CLI 继续既有安全错误契约。

## 8. 测试设计（先编写后实现）

tests/unit/test_pico.py：中英/混合及否定/剂量/时间/人群、完整/部分/无 comparator/非干预、多义分类；原始空白/emoji span、扩展词隔离、越界/错文/非法 JSON/重复键/多余字段、非法预算、模型错误/总期限；真实 LangGraph 继续/澄清/失败分支及多请求状态隔离；真实标准 LangChain 假模型的消息与预算；飞书渲染；包隔离导入。

tests/integration/test_pico.py：真实 ChatOpenAI + MockTransport 请求 → 计划 → 检索 → 生成 → 引用检查；API/CLI/飞书复用共享服务输出；无联网/模型/数据库。真实模型 external 使用同一冻结的 zh/en/mixed 小样例，最多每样例一次、共三次抽取调用，不调用证据生成；失败不自动重试，不根据结果改标签。

## 9. 样例与接受标准

tests/fixtures/pico/questions.json 版本 pico-cases-v1，在实现前冻结。确定性测试要求全部核心断言成立。真实样例分类均须与标签一致；已标注 PICO 原文的字段须精确一致，未提供 comparator 保持 null；全部 span 合法，数值/否定/时间通过原问题与 preserved_constraints 保留，不能输出冒充原文的扩展。记录逐样例输出、正确/遗漏/多抽取数及模型标识；固定三例只是工程冒烟，不是医学准确率评价。样例为合成开发测试与候选标注、无治疗结论，尚未获得人工审定；不能称作已完成人工医学评估。

## 10. 阶段末集中命令

使用正式 .venv/Scripts/python.exe，执行前清理 PYTEST_ADDOPTS/PYTEST_PLUGINS 等注入。核心实现齐备后集中执行：`-I -m pytest tests/unit/test_pico.py tests/integration/test_pico.py -q`；`-I -m pytest tests -q` 默认离线回归；`-m external tests/integration/test_pico.py -q` 仅在显式提供 LLM_* 配置时执行真实模型三例；Ruff check/format、mypy src、学习 Demo。配置缺失明确未验收，不 skip 伪装通过。不新增数据库行为，无需重跑无关真实 DB/Redis/部署。

## 11. 完成与停止

实施、核心/离线回归、真实模型三例、学习文档六份及 Demo、真实结果/未验证项齐备后才标 Phase 3 完成。外部不可用则保留待验收，完成不依赖它的交付。不重复 Phase 1 医学人工审查，不把它改为通过；不开发 Phase 4，不改延期任务。
