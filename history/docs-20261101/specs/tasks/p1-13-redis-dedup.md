# P1-13：Redis 原子消息去重

版本：0.2；日期：2026-10-27；状态：本任务独立去重边界已验收；76单元+12真实Redis、854默认回归通过。Phase1整体未验收；执行记录见[开发进度](../../development-plan.md)。

## 1. 背景及目标

P1-12已有纯事件过滤与MessageEnvelope.dedup_identity，当前没有Redis代码或依赖。沿用既定五模块架构，仅增加feishu/dedup.py，落实P1-F07、P1-T08/09/10中的原子租约部分。

## 2. 功能需求

身份为(app_id, message/event, ID)，沿用message_id优先与event_id回退；规范JSON经SHA256生成固定长度版本键，隔离应用、ID种类和测试前缀。acquire原子创建processing占位，重复返回duplicate且不返回owner。每次尝试生成UUID4 owner；check、renew、complete、release均在Redis原子脚本内核验processing及owner，防止旧工作者操作新租约。

## 3. 非功能需求

redis-py可选dedup extra，锁定已有技术基线候选8.1.0并验证Python3.12兼容。模块导入不加载redis、不读取环境、不建连接、不启动线程。客户端使用成熟连接池；工厂固定连接/读超时各1秒，最大连接16，禁用自动重试；不允许URL query覆盖参数。无自建连接池、重试、调度器或日志系统。

## 4. 功能边界

不实现线程池、发送、SDK、机器人装配、生产Compose服务、RAG调用、长期任务恢复；容量与消息通知由P1-14–16消费此接口。只验证独立本机Redis，不启用外部业务。不是exactly-once；进程崩溃、TTL到期、故障转移或远端发送结果未知可能重复/丢回复。

## 5. 输入输出契约

RedisDeduplicator(client, policy=DedupPolicy())显式注入并接管client关闭责任。acquire(identity)返回AcquireResult(status=acquired/duplicate/unavailable, lease)；仅acquired有Lease(identity, owner)。check/renew/complete/release(lease)返回owned/lost/unavailable。lost包括已过期、超过总期限、owner不符及已完成。Redis错误/未知脚本响应固定unavailable，不回显异常、URL、原文；参数错误在I/O前ValidationError/ValueError，不静默容错。unavailable不能继续业务或假定独占。

create_deduplicator(url, policy=...)延迟导入redis，仅允许无query/fragment的redis/rediss URL；客户端由调用方在全部工作结束后close。close返回布尔成功标记，关闭错误不回显异常。不隐式读.env或全局Settings。

## 6. 数据模型

DedupPolicy复用DTO，禁止额外字段：prefix为1–128字符ASCII标识（默认clinical-agent-feishu）；lease_ms默认60000，范围1–300000；max_processing_ms默认300000，范围lease_ms–900000；completed_ttl_ms默认86400000，范围1–604800000；整数严格拒绝bool/字符串。这些预算是去重上限，后续处理/发送预算必须在此上限内，不能据此声称已冻结未实现的工作池预算。

Redis单键存JSON：processing含owner和deadline_ms；completed仅短期标记，不存原文/聊天/发送人/凭据。deadline由首次占位Redis TIME+max_processing_ms决定，调用方不能延长。Lease不携带可篡改的服务端截止时间。键prefix:v1:SHA256规范身份JSON。

## 7. 核心业务流程

单段Lua、单key：acquire以SET NX PX原子创建；其他动作先读processing/owner，再取Redis TIME检查硬截止及有效TTL。renew TTL=min(lease_ms, deadline-now)，不改变deadline；check只检查不续期；complete转completed并设置独立TTL；release只删除当前owner的有效processing。完成后旧owner不能release/renew/complete。续租不运行后台线程，未来worker/sender显式调用；发送前须check并检查结果。

## 8. 异常与边界场景

Redis连接/超时/脚本错误均unavailable，无内存降级、无自动再次占位或盲删。响应丢失时服务端可能已执行，须停止业务并等待有限TTL，不假定回滚。损坏JSON/错类型键作为unavailable处理，不能覆盖未知状态。Redis脚本以服务端时间为准，多实例使用相同policy/prefix；prefix变更会改变去重域。单实例Redis不是分布式共识锁。

## 9. 测试用例清单

单元：身份编码稳定/隔离、非法身份/策略/Lease、唯一owner、acquire三分支、四种操作的三分支、Redis异常隐私、工厂超时/无重试/URL限制及关闭、模块隔离导入。Fake只验证调用/故障映射，不冒充Lua执行。

真实Redis集成：多客户端并发同身份只一个acquired；不同身份隔离；processing和completed拒绝重入；释放后重入；租约到期换owner，旧owner四操作均lost且新key不变；续租超过初始TTL仍有效但总期限到达后lost；complete保留独立TTL且旧owner不能删除；损坏数据/错类型/连接故障失败关闭；不使用FLUSHALL/FLUSHDB，仅清理本次UUID前缀。

## 10. 可执行验收标准

先运行tests/unit/test_feishu_dedup.py及tests/integration/test_feishu_dedup_redis.py得到缺模块RED，再最小实现GREEN。Redis集成标记integration和redis，默认pytest排除redis（与database一致）；显式-m redis运行，未配置CLINICAL_AGENT_TEST_REDIS_URL必须失败，不skip。服务仅loopback、本次专用容器，不读用户.env/Docker凭据，不影响其他容器。记录实际服务版本/digest及清理。

每轮pytest清除并finally恢复PYTEST_ADDOPTS/PYTEST_PLUGINS，独立basetemp/cache，证据.artifacts/p1-13-20261027-01。完成目标/Redis集成/默认回归、Ruff check/format、mypy src、uv lock --check --offline、uv pip check、git diff --check。只新增Redis可选依赖，既有版本不主动升级。

## 11. 阶段依赖及完成定义（DoD）

任务SPEC、真实RED/GREEN、真实Redis/故障/owner/期限验证、回归、使用说明与进度齐备才标P1-13完成；若服务不可用必须记录未验收，不以Fake替代。不标Phase1完成，不提前生成完整阶段学习文档，不自动执行P1-14。

依据：[Redis SET](https://redis.io/docs/latest/commands/set/)、[Lua原子脚本](https://redis.io/docs/latest/develop/programmability/eval-intro/)、[redis-py超时与重试](https://redis.io/docs/latest/develop/clients/redis-py/produsage/)。参数与状态机是项目决策，非平台exactly-once保证。
