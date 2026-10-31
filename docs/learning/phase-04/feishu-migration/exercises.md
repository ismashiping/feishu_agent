# 练习与测试

## 修改练习

1. 为 `events.filter_event` 增加一个合法点对点事件测试，断言相同 message_id 产生相同 request_id。不要修改生产代码。
2. 在测试中把 Dispatcher 容量设为 1，用阻塞 Fake Research 占用槽位，断言第二条消息返回 busy，释放后可以继续提交。
3. 构造 Fake Redis Client，让 Lua 调用返回 1、0 和异常，分别验证 acquired、duplicate 和 unavailable；确认异常不会被标为成功。
4. 使用 Fake HTTP Transport 模拟飞书成功、明确失败和读取超时，核对 sent、failed、unknown 与租约状态。

## 独立实现练习

实现一个只用于测试的内存 `DedupPort`：

- 身份首次 acquire 返回带 owner 的 Lease。
- 相同身份再次 acquire 返回 duplicate。
- check/release 只能由相同 owner 操作。
- 不添加生产降级路径，也不把它接入运行时。

为它编写并发测试，解释为什么该 Fake 能验证 worker 契约，却不能替代 Redis Lua 的跨进程原子性验证。

## 结构迁移练习

在临时包中实现“旧模块名和新模块名共享同一对象”：

1. 先导入旧路径，再导入新路径。
2. 反向导入。
3. 从旧路径 monkeypatch 一个模块全局，确认新路径可见。
4. 解释为什么简单重导出函数不能保证函数执行时读取旧模块上的 patch。

## 完成标准

每项练习都应区分：纯单元测试证明的契约、需要真实 Redis 的行为、需要真实飞书服务确认的交付事实。不得把 timeout 当成明确失败，也不得把 accepted 当成消息已发送。
