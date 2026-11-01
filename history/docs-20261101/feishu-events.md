# 飞书消息契约与事件过滤

P1-12只提供纯过滤函数，入口为`feishu.events.filter_event`。输入是未来官方SDK认证并解码后的事件字典；当前没有机器人进程、长连接或发送接口；Redis原子去重已由P1-13独立实现，见[去重说明](feishu-dedup.md)。详细行为见[任务SPEC](specs/tasks/p1-12-feishu-events.md)。

```python
from feishu.events import EventPolicy, filter_event

policy = EventPolicy(app_id="cli_example", bot_open_id="ou_bot")
event = {
    "schema": "2.0",
    "header": {
        "app_id": "cli_example",
        "event_type": "im.message.receive_v1",
        "event_id": "ev_example",
    },
    "event": {
        "sender": {"sender_type": "user", "sender_id": {"open_id": "ou_user"}},
        "message": {
            "message_id": "om_example",
            "chat_id": "oc_example",
            "chat_type": "p2p",
            "message_type": "text",
            "content": '{"text":"合成科研问题"}',
        },
    },
}
decision = filter_event(event, policy=policy)
assert decision.status == "accepted"
assert decision.envelope.dedup_identity == ("cli_example", "message", "om_example")
```

`accepted/eligible`仅表示可进入后续接纳；尚未取得线程容量或Redis租约，同一输入会再次返回accepted。ignored代表不属于本入口处理范围，rejected代表输入损坏或超限；两者均无envelope，只包含固定reason。过滤器不记录日志、不回显输入、不回复消息。调用方不得把原始Pydantic错误或完整事件写入日志。

策略显式传入目标app_id及机器人open_id，缺少身份配置会报ValidationError。只处理人类文本；所有bot消息和与本机器人open_id相同的消息都过滤。用户身份只取sender_id.open_id，缺少它时不混用user_id/union_id。单聊受理；群聊要求mentions中有本机器人open_id，而且对应完整`@_user_N`占位符存在于正文。仅删除这些占位符，保留其他人的@及换行，最终strip。机器人身份必须来自应用实际配置，不能根据用户昵称推断。

message.content为JSON字符串，UTF-8最多32KiB；解码后必须含字符串text，重复键、坏Unicode/JSON均拒绝。最终问题为1–4000字符，超长不截断，与核心QuestionRequest长度一致。群聊mentions最多100条，损坏/冲突条目拒绝；单聊不消费mentions。标识为1–256字符的ASCII字母、数字、下划线、连字符；可选去重ID缺失/null/空白归一为None，非空损坏ID拒绝。

去重身份优先(app_id, message, message_id)，无message_id时回退(app_id, event, event_id)，双缺失拒绝。三元组区分应用及ID种类；Redis键编码与原子占位由[P1-13](feishu-dedup.md)实现。request_id用三元组的规范JSON生成UUID5，同消息不同event_id仍保持关联；不能将此关联ID当作身份认证或去重存储。将来worker可用envelope.text与request_id构造原QuestionRequest并调用原服务。

验证命令（PowerShell，项目根目录；如有PYTEST_ADDOPTS/PYTEST_PLUGINS需先保存清理并在finally恢复）：

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_feishu_events.py tests/unit/test_package.py -q
```

测试只使用人工事件字典；未安装或运行官方SDK，未验证真实机器人权限、open_id获取、收发与重复投递。输入字段参照[官方接收消息文档](https://open.feishu.cn/document/server-docs/im-v1/message/events/receive)。SDK对象到字典的映射与认证边界需在长连接任务通过真实SDK测试。
