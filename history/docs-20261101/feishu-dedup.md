# 飞书 Redis 原子消息去重

P1-13实现独立的短期去重边界，详见[任务SPEC](specs/tasks/p1-13-redis-dedup.md)。P1-12的accepted仅表示过滤通过；调用方还需取得容量与本模块租约，P1-14已实现[有界工作池](feishu-worker.md)；P1-15已实现[受限发送](feishu-sender.md)；SDK/生产装配和真实租户收发仍待P1-16。当前不能启动完整机器人。

安装：在既有开发extras之外增加 `uv sync --locked --extra dedup`；全量开发测试使用 `uv sync --locked --extra ml --extra db --extra rag --extra api --extra dedup`。redis-py固定8.1.0，可选extra不增加基础包的导入负担。模块不读取配置或隐式建连接。

```python
from feishu.dedup import DedupPolicy, create_deduplicator

# 合成身份；实际使用已通过filter_event的envelope.dedup_identity。
dedup = create_deduplicator(
    "redis://127.0.0.1:56379/0",
    policy=DedupPolicy(prefix="example-feishu"),
)
try:
    result = dedup.acquire(("cli_example", "message", "om_example"))
    if result.status == "acquired":
        lease = result.lease
        assert lease is not None
        # 本例不执行研究/发送，演示安全释放。真实调用方应逐次检查返回状态。
        released = dedup.release(lease)
        assert released in ("owned", "lost", "unavailable")
finally:
    dedup.close()
```

默认processing租期60秒，总处理上限300秒，completed保留24小时；策略有明确范围，见SPEC。身份规范JSON的SHA256编码为prefix:v1:hash，不包含原文、聊天或用户信息；不同app与message/event命名空间隔离。UUID4 owner只能操作对应的有效processing租约。

所有状态操作在单键Lua脚本内原子执行。首次占位使用SET NX PX，以Redis TIME记住不可延长的总期限；renew仅将TTL延长至min(租期, 剩余总时间)。check不续租，complete转独立completed TTL，release核对owner后删除。已经完成、租约丢失/到期、总期限到达时旧owner不能删除或续期新占位。

acquire返回acquired/duplicate/unavailable，只有acquired携带lease；其余四操作返回owned/lost/unavailable。lost或unavailable必须停止继续正常研究/发送，不能假定仍有独占权。发送前应重新check；检查后发送仍非跨系统事务。工作/发送模块须在总预算内设置底层调用超时并显式安排续租，本模块不启动后台线程。

超时和响应丢失可能发生在服务端已执行之后：返回unavailable，不重试、不盲删，允许有限TTL自然恢复。损坏存储/错类型键也失败关闭，不强行覆盖。终态complete只由调用方确认成功后调用；P1-15对发送超时/未知结果保留TTL、不重试/盲删；确定成功才owner complete，确定未发/明确失败owner release。Redis重启/故障转移、进程崩溃和过期仍可能导致重复或丢失回复，不能承诺exactly-once。

工厂固定连接/读超时各1秒、最大16连接、自动重试0次；只接收无query/fragment的redis/rediss URL，避免URL覆盖超时。凭据由调用方提供，不记录或回显。注入客户端必须具有相同的有限I/O/无重试约束，并交由dedup关闭；close之后本对象拒绝再执行命令。关闭须在所有工作和发送实际结束后进行。

真实集成测试须显式配置专用本机Redis。测试创建UUID前缀，只扫描/删除自己的键，不执行FLUSHALL/FLUSHDB；缺少URL会失败，不降级为Fake。

```powershell
# 项目根目录；先保存并清除PYTEST_ADDOPTS/PYTEST_PLUGINS，结束后finally恢复。
$env:CLINICAL_AGENT_TEST_REDIS_URL = "redis://127.0.0.1:56379/0"
.venv/Scripts/python.exe -m pytest tests/unit/test_feishu_dedup.py -q
.venv/Scripts/python.exe -m pytest tests/integration/test_feishu_dedup_redis.py -m redis -q
```

本次验收使用独立容器clinical-agent-p113-20261027，127.0.0.1随机宿主端口，Redis7.4.11；本机现有镜像digest为`redis@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499`，无持久卷、关闭快照/AOF，结束停止本次容器。没有新增生产Compose服务；容器本身不代表SDK/工作池/发送验收，也没有启用外部业务。默认pytest排除redis，与database测试一样单独执行；阶段完整集成命令选择redis时必须提供测试服务。

原子执行及客户端选项依据：[Redis Lua](https://redis.io/docs/latest/develop/programmability/eval-intro/)、[SET NX PX](https://redis.io/docs/latest/commands/set/)、[redis-py超时与重试](https://redis.io/docs/latest/develop/clients/redis-py/produsage/)。本次结果及未完成事项见[开发进度](development-plan.md#phase-1-任务进度)。


## P1-16 当前装配入口

此前正文中的待装配描述保留为本任务交付时点；P1-16现已提供[官方SDK与生命周期入口](feishu-runtime.md)，复用本模块。真实服务及容器运行结果以[开发进度](development-plan.md#phase-1-任务进度)为准，不将离线用例解释为整体验收。
