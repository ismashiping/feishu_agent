> 后续增量说明：本文原P3冻结契约保留；当前澄清决策由[探索型发现修复](tasks/exploratory-discovery.md)扩展，旧输出继续兼容，不追改原验收。

# SPEC 03：问题分类与 PICO

版本：0.3；日期：2026-10-28；状态：P3-01 核心实现与测试已交付，集中验收中，真实模型样例待配置。详细冻结契约见 [P3-01 SPEC](tasks/p3-01-pico.md)。

## 本轮核心范围与测试约定（2026-10-28）

本阶段概要已在 [P3-01](tasks/p3-01-pico.md) 细化契约、断言、冻结 fixtures、测试命令和真实依赖前提，再先编写测试后实现最小功能。不在单次会话执行 RED/GREEN 或回归，阶段结束后集中执行核心测试、已有离线回归、受影响真实集成/外部冒烟、必要人工复核和质量检查。集中验收失败须修复并重跑受影响范围；未执行、失败、跳过或被排除的项目不得标记通过。实际测试已落在 tests/unit/test_pico.py 与 tests/integration/test_pico.py；执行范围与未验收项以开发进度为准。

后续顺序固定为 Phase 3 → 4 → 5 → 6 → 7，不依赖延期 Phase 2 的 TaskRecord/receipt。复用现有 ResearchService/LangGraph、LangChain 通用模型边界、DTO 和存储/解析/引用模块。核心超时、错误分类、数据一致性及来源真实性必需；非核心健壮性、性能优化、复杂异常处理留 Phase 7 后收尾。核心验收及 `docs/learning/phase-03/` 六份真实学习材料齐备才标阶段完成。参见[开发计划](../development-plan.md)与[测试策略](../testing-strategy.md)。

## 1. 背景及目标

将医学科研问题转为可解释的结构化检索意图，保留缺失项和歧义；PICO 是查询辅助，不是诊断结论。承接现有 Phase 1 [基础问答契约](00-project-overview.md)；异步任务状态为延期能力，不是本阶段依赖。

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

PICO 的每项为 null 或 ExtractedField(text, origin, source_span 可空)；当前 P3-01 进一步限制 PICO 仅接纳 user_text，扩展词只放 terms。origin=user_text 时 span 必须回指原问题，origin=query_expansion 必须明确是检索扩展。不能把模型扩展词作为用户已给条件。格式无法修复时返回 extraction_failed，不能生成看似完整结构。

## 6. 数据模型

QuestionType 为上述枚举；PICO 四项可空。SourceSpan 为字符起止区间，约定对规范化前原始 question 的 Python 字符索引，半开区间；范围与原文一致。QueryPlan 有 version 及保留的否定/时间/人群约束；不改写原问题事实。

## 7. 核心业务流程

校验问题 → 分类与结构化输出 → schema/span 校验 → 明确歧义或保留部分 PICO → 生成可解释检索计划 → 接回既有问答服务。P3-01 固定 uncertain 且有具体歧义才转 needs_clarification；其他完整/部分 PICO 可继续。preserved_constraints 保留整个原问题，检索仍用原问题，不声称已执行每个条件的语义过滤。

## 8. 异常与边界场景

非医学问题、空问题、超长问题、多个干预比较、无 comparator、否定用词、中英缩写、错误 span、LLM 格式错误及超时。一个字段未知须保留 unknown/null，不将“未知”抽为医学实体或补成默认值。

## 9. 测试用例清单

- P3-T01：固定人工标注中英问题的分类及允许 uncertain 行为。
- P3-T02：完整/部分 PICO、缺 comparator、非干预问题。
- P3-T03：span 回指、负面限制、数值/时间不被扩展覆盖。
- P3-T04：模型扩展词与用户原文来源分离，非法 JSON/span 失败。
- P3-T05：LangGraph 分支及既有问答/CLI/API/飞书入口回归（不要求新增异步状态），外部 LLM 用替身。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k pico`。冻结包含上述边界的人工 fixtures：Fake 输出校验测试全通过，缺失字段保持 null，任何不合法来源区间均不得进入有效结果。

真实模型使用少量冻结的中英样例，记录 fixture 版本和各字段正确/遗漏/幻觉数；大规模混淆矩阵/统计平台延期 Phase 9。进入本阶段前冻结语料与接受阈值，不能根据跑分反改标签或仅凭 prompt 演示验收。冻结三例位于 tests/fixtures/pico/questions.json；真实模型运行结果单列，未执行不计通过。

## 11. 阶段依赖及完成定义（DoD）

依赖现有 Phase 1 技术基线，不依赖 Phase 2；Phase 1 医学人工签署仍待完成，不转为已通过。先冻结标签、歧义规则、来源区间和少量中英人工标注样例的接受标准。集中验收 P3-F01–04 的核心分类/PICO/查询计划、真实模型小样例与既有问答入口回归，交付 docs/learning/phase-03/ 后完成。大规模分类混淆矩阵/统计评估留 Phase 9。下一核心阶段为 Phase 4，需另行明确指令。
