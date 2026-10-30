# SPEC 02：异步受理与任务状态

## 延期状态（2026-10-28）

Phase 2 保留原编号和需求，当前未实现，统一延期至 **Phase 3 → 4 → 5 → 6 → 7** 核心链路完成后的收尾批次；不是 Phase 3–7 的前置条件。收尾内部顺序届时确认；原有能力依赖保留（Phase 8 依赖 Phase 7，Phase 9 依赖 Phase 8 及既有证据），不能用编号强制 Phase 2 先于 Phase 3。

实施前重新细化 SPEC 和验收测试，采用先写测试/最小实现、阶段末集中测试与回归的策略；不要求逐任务 RED/GREEN。原文 TDD 描述不再表示每次会话执行测试。未执行不得标通过。核心阶段仍保留必要超时、错误处理、数据一致性、基础幂等及引用真实性；延期完整评价平台不等于延期核心阶段验收。详细状态以[开发计划](../development-plan.md)为准。

版本：0.2；状态：延期概要，核心 Phase 7 后再细化；未实现。

## 1. 背景及目标

在 Phase 1 有界处理基础上，给长耗时研究提供快速受理、可查询状态及明确超时体验。协议层 SDK ACK 与用户可见“已受理”是两件事，均不能代表研究完成。

## 2. 功能需求

- P2-F01：受理生成 task_id，先确认接纳再后台研究；忙碌时明确拒绝，不能先说已受理再静默丢弃。
- P2-F02：保存 accepted → running → succeeded/failed/timed_out及重启后的interrupted状态；启动恢复时把上一进程未完成任务标为 interrupted，不默认自动重放。
- P2-F03：API/CLI 支持状态查询，飞书可查询所属任务状态并在完成后收到结果或失败通知。
- P2-F04：总期限与各外部调用超时配合，迟到结果不能覆盖终态或再次发送正常答案。

## 3. 非功能需求

使用已有 PostgreSQL 保存任务事实及已有有界执行器，Redis 仍用于短期去重；不引入独立任务平台作为默认。限制在途任务和每个任务资源，隔离调用方任务查询。请求受理、研究执行、通知发送分别记录，不把通知失败改成研究失败。

## 4. 本阶段不实现的内容

不实现 Celery/分布式队列、跨进程自动恢复执行、exactly-once 发送、长期任务编排平台、强制杀线程或复杂补偿。不能仅用 FastAPI BackgroundTasks 就宣称任务持久可靠。

## 5. 输入输出契约

输入 QuestionRequest 加 origin、requester_key、可选 idempotency_key。成功受理输出 TaskReceipt(task_id, accepted_at, deadline_at, status=accepted)；忙碌/配置故障输出 ErrorInfo，不能返回成功 receipt。

TaskStatus 包含 task_id、status、created/started/finished 时间、deadline_at、结果引用或错误、delivery_status。delivery_status 独立为 pending/sent/failed/unknown；发送超时不得假定未发送。查询需匹配 origin/requester，不能仅凭可猜 task_id 读取别人的问题。

## 6. 数据模型

TaskRecord 记录上述字段、request_id、owner token 和最小来源上下文。终态不可退回 running；只有持有执行权的工作者可提交结果。研究结果沿用 [SPEC 00](00-project-overview.md) 的 ResearchAnswer，不把正文复制到每条日志。

提供 idempotency_key 时，以 origin/requester_key/key 作唯一约束；同键同内容返回原 receipt，同键不同内容报冲突，不覆盖原任务。未给该键的普通独立提问不按问题文本强行去重。

## 7. 核心业务流程

校验/去重/接纳容量 → 持久化 accepted → 成功提交执行器 → 快速确认 → running → 应用服务研究 → 条件更新终态 → 发送最终通知并单独记录。提交执行器失败需把任务标失败并释放容量；进程崩溃遗留 accepted/running 在重启时转 interrupted，用户可显式重试创建新任务。

计时器或执行器检查总期限；超时只停止等待和后续状态提交，实际外部调用靠自身超时结束。工作线程实际退出前继续占用容量，不能在超时回包时虚假释放为可无限新建。

## 8. 异常与边界场景

重复受理、存储失败、排队满、确认回复失败、研究成功但通知失败、总期限到达、晚到模型返回、重启未完成任务、越权查询、重复完成回调、关闭时在途任务。状态更新与 SDK 发送间崩溃不能保证一次发送，必须记录可见限制。

## 9. 测试用例清单

- P2-T01：阻塞 Fake 研究时 receipt 已返回；确认路径未等待 LLM。
- P2-T02：所有允许及禁止状态转移、重复完成和 owner 不符更新。
- P2-T03：Fake clock 驱动总超时，晚到成功不覆盖 timed_out、不发送答案；实际线程仍计入在途。
- P2-T04：满载/入队失败/数据库失败/通知失败的状态与资源回收。
- P2-T05：真实 PostgreSQL 任务查询、并发终态更新及重启 interrupted 标记。
- P2-T06：飞书快速受理与完成回复，重复消息复用受理结果且不重复研究；调用方隔离。

## 10. 可执行验收标准

开发时将 P2-T01–06 落地测试，并运行 `uv run pytest tests/unit tests/integration -k async_experience`（未来测试名约定，当前未创建）。用阻塞 Fake 研究验证 receipt 在解除阻塞前返回，使用受控环境测量用户确认目标 2 秒内并记录实测，而不对公网延迟作保证。

重启测试服务后查未完成任务，必须明确 interrupted；模拟任务超时再释放 Fake，最终状态及正常答案发送次数不改变。研究成功但发送失败时，查询仍显示研究 succeeded 与 delivery failed/unknown。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 1 已验收。细化存储保留期、期限、接纳顺序和任务查询权限后编写测试与最小实现，阶段末集中验收；完成单元/真实存储集成/入口回归、真实飞书体验及 docs/learning/phase-02/ 六份学习材料，明确重启不自动恢复的限制后验收。复用届时已有 Phase 3–7 业务能力，不重复实现问题分类。
