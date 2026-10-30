# 单次规划与自然语言意图路由

2026-10-30；实现任务，阶段末待测试/待验收。

## 范围与契约

在现有ExtractionDraft、QueryPlan增加task_intent，取值feasibility/comparison/paper_explanation/definition/question_answer。独立于现有research_intent（检索语义）。历史显式answer/analyze/report所用计划允许该字段为空；新增自动入口respond要求planner及非空task_intent，缺失报extraction_failed，不猜测路由。无planner调用respond为配置错误。普通飞书文本使用respond，/report保留report。

同一LangGraph内plan节点输出路由标志，feasibility设置analysis_requested/report_requested，其他意图保持问答；有阻断歧义先输出ResearchAnswer(needs_clarification)，不走检索/报告。自动入口返回ResearchAnswer或ResearchReport，复用现有发送器支持的两种结构。输入仍QuestionRequest。显式入口不依task_intent改变分支。

每次respond只invoke一次图，只执行一次planner；反馈复用计划并共享deadline/request_id，不重新调用answer/report，不重置期限。不新增LLM路由调用、关键词分类器、数据库迁移或重试。Planner提示按用户最终要求分类；定义/原文解释不因涉及科研就变报告；方向评估中的可选资源信息不阻断，改变对象的歧义需要澄清，不能自行补成某个医学子类型。

## 测试与验收

先编写tests/unit/test_intent_routing.py：冻结四条用户文本和人工预期意图，以合成结构化输出验证真实PicoPlanner→图路由；方向评估走真实报告组件、其余轻量路径；澄清不检索；显式answer/report不受自动路由影响；反馈不重复规划；模型缺失/非法task_intent失败；共享预算与请求ID。worker测试替身显式实现respond并验证/report保留。合成输出不代表真实LLM分类准确或医学通过。

阶段末命令：.venv/Scripts/python.exe -m pytest tests/unit/test_intent_routing.py tests/unit/test_feishu_worker.py tests/unit/test_pico.py tests/unit/test_exploratory_discovery.py tests/unit/test_feedback_agents.py tests/unit/test_command_runtime.py tests/unit/test_feishu_main.py；随后默认离线pytest与Ruff，记录marker排除。真实四题需要LLM/OpenAlex/数据库/E5/Redis/飞书已配置，部署后核对计划、接收与实收；本任务不执行外部调用或部署。真实模型分类、报告质量、原飞书失败根因不由静态路由测试替代。

## 本任务交付记录

已先编写路由测试，再修改domain/pico、application/pico/research/workflow、command_runtime和feishu/worker。同步worker/main/sender及live runtime测试替身的respond契约；四题测试与反馈/澄清复用现有真实图和隔离组件。增加显式/report与自动报告交付的断言。测试数据为合成内容，不作医学证据。

防御逻辑静态审查：仅自动入口缺planner配置检查、自动计划缺task_intent错误；其余字段继续由原Pydantic契约校验。沿用入口错误分类、单一deadline和现有反馈上限；无新增重试、默认成功或兼容探测。历史显式计划允许task_intent=None的范围在上文明确，自动路由不会静默退回普通问答。

本轮只执行受影响11个Python文件的Ruff check和format --check。首次check发现3处行长，format修正后检查通过。未执行pytest、真实模型调用、飞书发送、镜像构建或部署；所有新测试待阶段末集中执行，之前95项结果不适用于本轮路由改动。学习文档在阶段验收后生成，不标阶段完成。

下一个任务：按研究问题检索与论文身份，先冻结真实正反例及标注。原比较/原论文解释失败根因、真实意图分类准确性和报告质量仍未验证。本任务不宣称解决这几项问题。
