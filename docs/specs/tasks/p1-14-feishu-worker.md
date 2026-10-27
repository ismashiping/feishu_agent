# P1-14：飞书有界任务分派与服务复用

版本：0.2；日期：2026-10-27；状态：独立分派边界已验收；43 worker目标、243联合、898默认回归通过，Phase1未整体验收。

## 1. 需求与目标

承接P1-12消息契约和P1-13原子租约，落实P1-T07–10中飞书接纳、实际RAG次数、容量及关闭部分。沿用五模块架构，新增src/feishu/worker.py，注入既有ResearchPort，生产装配由P1-16负责。

## 2. 功能需求

标准ThreadPoolExecutor与非阻塞Semaphore限制全部在途任务，容量先于Redis占位；重复/Redis不可用不调用研究；提交失败释放自己的租约与容量。所有成功提交的容量只随实际Future完成回收，调用方等待超时或cancel不能提前释放正在运行的容量。复用一个外部注入服务，逐消息构造独立QuestionRequest，保留text和request_id。

## 3. 非功能需求

无新依赖、无自建线程池/调度器、无自动重试。导入不读配置、不连Redis、不启动线程或加载模型。固定线程数=capacity，没有额外研究排队额度。异常不回显原文、凭据或异常文本。

## 4. 功能边界

不实现SDK、渲染、发送队列、通知投递、生产装配、Compose、Phase2任务状态/快速确认/持久恢复。返回busy/unavailable/closed供未来入口处理，不在SDK回调同步发通知。P1-15实现本任务定义的非阻塞发送交接端口。Fake验证调度联动，不冒充Redis原子性/真实模型/真实发送。

## 5. 输入输出

Dispatcher(research, dedup, sink, policy=WorkerPolicy(), clock=monotonic)。dedup使用既有RedisDeduplicator契约，资源借用。submit(MessageEnvelope)返回Submission(status=accepted/busy/duplicate/unavailable/closed/submit_failed, future)，仅accepted有Future[WorkResult]。输入在I/O前重校验及深复制。

Delivery包含envelope、lease、单调时钟deadline、answer或固定error_code，正常answer必须是合法ResearchAnswer且request_id匹配。sink.offer(delivery)->bool必须非阻塞、有界；True表示接管租约，须在实际发送前检查deadline及check，并在确认投递后complete；deadline为min(处理截止,交接时刻)+handoff_ms，仅限同进程；False表示确定未入队，worker释放owner。offer异常意味着是否入队未知，保留TTL不盲删、不重发。WorkResult仅status=queued/delivery_failed/delivery_unknown/lost/unavailable/timed_out。研究错误转固定research_failed（不泄露供应商详情），可作为Delivery交接。

## 6. 数据模型及预算

WorkerPolicy为DTO，capacity严格整数1–4默认2；processing_ms严格整数1–240000默认90000；handoff_ms严格整数1–30000默认15000。构造时要求dedup.policy.lease_ms及max_processing_ms >= processing_ms+handoff_ms+5000（Redis及交接裕量）。因此默认DedupPolicy的60秒租期不够，装配必须显式配置至少110000ms；不静默修改外部策略。当前采用覆盖预算的固定租约，研究前后check，不另建续租线程；发送端可沿用P1-13有限renew，但不能越过首次占位硬期限。

## 7. 流程与资源生命周期

校验→锁内检查closed/非阻塞取容量→acquire→提交；计时从占位前开始，避免Redis耗时遗漏。worker先检查本地期限与owner，再调用共享服务；返回或抛错后再次检查期限与owner，迟到/失租/不可用不offer。有效结果交接后结束，finally由Future完成回调一次性释放容量。未交接且确定未发送的租约按owner释放；owner未知/检查不可用保持TTL，不能假定Redis操作回滚。

close(timeout_seconds=5.0)->bool：停止接纳，shutdown(wait=False,cancel_futures=False)，取得接纳锁后有期限等待当前Future及清理回调；已在接纳中的Redis调用仍受自身1秒I/O超时约束；False表示仍有实际线程，不取消/杀线程，不关闭共享服务/Redis/sink。调用方必须继续等待，只有返回True且发送端排空后才关闭资源；可重复close。此机制不提供强制终止阻塞模型能力。

## 8. 异常与边界

过滤在本模块之前；满载不占位。重复/故障归还容量。ThreadPoolExecutor提交失败清理自己owner；cancel尚未开始Future时回调清理租约，运行中的cancel不会成功。服务报错、非法DTO、错误request_id均固定research_failed。未知投递不重试；失去owner不删除其他租约。close与submit串行确定受理边界，工作回调不依赖接纳锁，避免立即完成死锁。

## 9. 测试场景

实际线程与Event/Barrier验证容量上限、忙碌不占位、并发重复仅一次研究、容量在实际结束恢复、取消/等待超时、close超时后拒绝及最终排空、submit失败恢复、输入快照。替身逐项验证acquire/check/release分支、过期前后、故障隐私、有界sink拒绝及未知、服务失败/非法输出、策略严格校验。真实ResearchService及LangGraph配合合成检索/生成验证共享服务、独立request_id、DTO与直接调用语义一致。新增隔离导入检查。Redis原子性沿用P1-13真实服务证据，本任务不改Lua。

## 10. 可执行验收

先运行新增tests/unit/test_feishu_worker.py取得缺模块RED，再最小实现GREEN。每轮清除并finally恢复PYTEST_ADDOPTS/PYTEST_PLUGINS，独立basetemp/cache，证据.artifacts/p1-14-20261027。目标测试、默认pytest回归、ruff check/format、mypy src、uv lock --check --offline、uv pip check、git diff --check必须实际执行。对真实共享ResearchService验证使用本地合成端口，不连接业务系统。

## 11. 完成定义

SPEC、真实RED/GREEN、目标/回归/静态检查、使用说明及进度记录齐备才完成任务。P1-15/16发送和装配责任明确保留，不标Phase1完成，不自动开始下一任务，不生成未完成阶段的学习材料。
