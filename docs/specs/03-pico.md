# SPEC 03：问题分类与 PICO

版本：0.1；状态：未来阶段概要，开发前细化；未实现。

## 1. 背景及目标

将医学科研问题转为可解释的结构化检索意图，保留缺失项和歧义；PICO 是查询辅助，不是诊断结论。承接 [基础问答契约](00-project-overview.md) 与 [异步任务](02-async-experience.md)。

## 2. 功能需求

- P3-F01：分类为 intervention/diagnosis/prognosis/etiology/other/uncertain，可返回需澄清项。
- P3-F02：抽取 population、intervention、comparison、outcome；明确来自用户原文还是查询扩展，不填造缺失 comparator。
- P3-F03：输出 QueryPlan，包含原问题、关键词、同义词候选、PICO 和检索意图，后续供实时/混合检索使用。
- P3-F04：LangGraph 增加分类、结构化和歧义分支，普通字段校验保持普通函数，不重复实现图引擎。

## 3. 非功能需求

中文、英文及混合问题均需样例覆盖，否定、剂量、时间和人群限制不得丢失。结构化输出须经过 Pydantic 校验；模型置信度只是抽取参考，不能成为医学可靠性分数。同一输入在 Fake 下结果可重复。

## 4. 本阶段不实现的内容

不训练临床 NER，不维护庞大药物规则表，不自行诊断，不实时访问 PubMed，不自动判定研究质量。非干预问题不强行套完整 PICO；缺失项也不强迫用户全部补齐才允许检索。

## 5. 输入输出契约

输入 ClassificationRequest(question, language_hint 可空)。输出 StructuredQuestion(question_type, pico, ambiguities, extraction_status) 与 QueryPlan(original_question, structured_question, terms, preserved_constraints)。

PICO 的每项为 null 或 ExtractedField(text, origin, source_span 可空)；origin=user_text 时 span 必须回指原问题，origin=query_expansion 必须明确是检索扩展。不能把模型扩展词作为用户已给条件。格式无法修复时返回 extraction_failed，不能生成看似完整结构。

## 6. 数据模型

QuestionType 为上述枚举；PICO 四项可空。SourceSpan 为字符起止区间，约定对规范化前原始 question 的 Python 字符索引，半开区间；范围与原文一致。QueryPlan 有 version 及保留的否定/时间/人群约束；不改写原问题事实。

## 7. 核心业务流程

校验问题 → 分类与结构化输出 → schema/span 校验 → 明确歧义或保留部分 PICO → 生成可解释检索计划 → 接回既有问答服务。需澄清与可带不确定性继续两种结果由详细任务规则明确，不能凭模型任意阻断流程。

## 8. 异常与边界场景

非医学问题、空问题、超长问题、多个干预比较、无 comparator、否定用词、中英缩写、错误 span、LLM 格式错误及超时。一个字段未知须保留 unknown/null，不将“未知”抽为医学实体或补成默认值。

## 9. 测试用例清单

- P3-T01：固定人工标注中英问题的分类及允许 uncertain 行为。
- P3-T02：完整/部分 PICO、缺 comparator、非干预问题。
- P3-T03：span 回指、负面限制、数值/时间不被扩展覆盖。
- P3-T04：模型扩展词与用户原文来源分离，非法 JSON/span 失败。
- P3-T05：LangGraph 分支及旧问答/异步入口回归，外部 LLM 用替身。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k pico`。冻结包含上述边界的人工 fixtures：Fake 输出校验测试全通过，缺失字段保持 null，任何不合法来源区间均不得进入有效结果。

真实模型另记录 fixture 集版本、分类混淆矩阵、各 PICO 字段正确/遗漏/幻觉数；进入本阶段前冻结语料与接受阈值，不能根据跑分反改标签或仅凭 prompt 演示验收。当前未建立语料或运行这些测试。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 2 验收；开发前细化标签准则、歧义规则和评价阈值。P3-F01–04、结构化契约、模型替身测试、真实样例评估与回归及 docs/learning/phase-03/ 齐备后完成。下一阶段再连接实时 PubMed。
