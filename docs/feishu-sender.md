# 飞书文本渲染与受限发送（P1-15）

本任务实现`src/feishu/sender.py`；[任务SPEC](specs/tasks/p1-15-feishu-sender.md)。承接[分派](feishu-worker.md)的DeliveryPort；SDK长连接、token提供者和生产入口仍待P1-16，当前没有可运行的飞书机器人入口。

`render_answer`仅接收已校验ResearchAnswer。展示结论类型、每项结论的来源编号及chunk ID、结论局限；展示来源标题/作者/日期/期刊、已存在的PMID/DOI/安全HTTP(S) URL、document ID/hash、摘要/PDF文本层/全文来源范围，以及页码或摘要节和半开字符区间。缺失元数据标未知或省略，不补造。全局局限及本地检索/最新覆盖和科研辅助限制保留。无证据明确不代表无效；结构校验不等于医学语义支持关系审查。

输出仅为text，中文/换行由JSON正确编码。元数据中的尖括号及&转为全角可见字符，防止`<at>`标签触发提及；不输出本地文件URI和带凭据/非HTTP(S)来源地址。不保证所有轻量文本样式都被禁用。内部content序列化最多24000 UTF-8字节，完整请求最多30000字节；渲染为外层预留最大256字符chat ID，含双层JSON转义。两层任一超限，整体替换为“结果过长”提示，不截断结论/引用或拆成多次发送。这是项目保守预算，不是对官方极限的声明。

## 队列和调用顺序

1. 显式构造`Sender(dedup=..., transport=..., policy=SenderPolicy(...))`启动一个标准线程；导入模块不启动线程、不导入HTTP客户端。
2. 将sender作为`Dispatcher(..., sink=sender)`传入。研究端`queued`只表示交接；只有远端明确成功后sender才调用`dedup.complete`。
3. `offer(Delivery)`在接纳前重校验并深复制envelope/lease/answer，校验租约身份、request_id、唯一answer/error和有限deadline。False表示未接管租约，worker按其契约释放。非法输入抛固定ValueError，没有接纳副作用。标准Queue及锁内pending计数限制全部在途（执行中+排队），默认8项，范围1–64；满载/关闭立即False。
4. 出队检查本地deadline和owner；渲染后再查；OfficialMessageAPI获取token后、实际HTTP前再次门禁。排队时间包含在P1-14发送期限内。失租或Redis不可用不发、不删除其他owner。
5. `offer_notice(envelope, code)`仅允许research_failed/busy/unavailable/invalid_input固定提示，与答案共用容量，默认5秒通知期限；没有租约，不占位、不complete、不release。需要合法envelope；无法映射出安全目标的输入错误只由入口记录，不凭空造收件人。P1-16负责把入口结果接入通知。
6. 先`worker.close(...)`直到True，再`sender.close(...)`直到True，最后关闭借用的服务、HTTP和Redis。sender.close默认等5秒，False表示仍有实际工作，继续等待；不强杀线程，不提前释放运行容量。

## 官方API适配

`OfficialMessageAPI(client, token=provider)`使用已有锁定httpx 0.28.1；已安装rag/api可选依赖的正式环境可用，不新增包或锁变更。provider签名`provider(deadline: float)->str`，必须在传入单调deadline内提供有效tenant_access_token。鉴权缓存/刷新与SDK生命周期由P1-16装配，sender不重新实现鉴权系统。

借用client必须禁用重试/重定向，不能带默认鉴权/参数或记录正文与凭据的事件hook。P1-16显式构造的建议为：

```python
client = httpx.Client(
    transport=httpx.HTTPTransport(retries=0),
    follow_redirects=False,
    trust_env=False,
)
```

不要将使用自定义重试transport的client注入；接口借用契约无法检测任意自定义transport内部是否重试。sender不会关闭client或provider；所有客户端须等线程排空后关闭。

有message_id时POST固定官方`/open-apis/im/v1/messages/{message_id}/reply`；仅event_id时POST`/open-apis/im/v1/messages?receive_id_type=chat_id`，使用已校验chat_id。请求为`msg_type=text`，`content`为`{"text":...}`序列化字符串，Authorization Bearer token；不使用机器人Webhook。每项最多一次消息POST，不使用UUID作为跨租约的去重承诺，不自动重试。

HTTP超时为`min(剩余Delivery期限, send_ms)`，默认send_ms=5000，token也消耗此预算；token之后再次检查剩余时间。httpx的阶段超时不能保证绝对墙钟总耗时，底层阻塞或已开始的远端调用无法强制撤回。明确晚到成功仍尝试owner complete；owner已丢失则记录lost，不重发。

| 发送结果 | 定义 | 租约处理 |
| --- | --- | --- |
| sent | 2xx、严格整数code=0且data.message_id为非空字符串 | owner complete；失败/未知不重发 |
| failed | token阶段失败/未开始HTTP的本地错误；4xx或明确业务非零code | owner release |
| unknown | 开始HTTP后异常/超时、5xx/3xx、畸形响应，或注入transport抛错/非法状态 | 保留TTL；不盲删、不重试 |
| timed_out | 消息调用开始前预算耗尽 | owner release |
| lost / unavailable | 临发送所有权丢失/无法确认 | 不发，保留TTL |

通知无租约，以上清理均不适用。成功的固定研究错误/过长提示也是终态，可complete。Redis清理异常只记录unavailable，不尝试第二次投递。TTL过期可能重新受理，不保证exactly-once或可靠持久交付。

模块使用标准logger `feishu.sender`记录固定事件`feishu_delivery`和extra字段`request_id/status/dedup_status`；不打印问题、答案、token、SDK/HTTP异常或响应正文。生产入口P1-16需为此logger配置保留这些允许字段的处理器；本模块不配置全局日志。

## 验证和限制

用项目`.venv/Scripts/python.exe -m pytest tests/unit/test_feishu_sender.py -q`运行目标。真实标准线程和Event同步验证容量、快照、超时关闭及实际排空；httpx.MockTransport验证官方请求结构和异常分类；Dispatcher→Sender验证正常/错误交接。全部来源为合成元数据，未连接真实租户/Redis/模型/数据库/LLM；不能以协议替身冒充真实收发或医学结论验收。实际命令与计数见[开发进度](development-plan.md)末尾P1-15记录。

官方依据（2026-10-27核查）：[回复消息](https://open.feishu.cn/document/server-docs/im-v1/message/reply)、[发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)、[文本content结构](https://open.feishu.cn/document/server-docs/im-v1/message-content-description/create_json)。P1-16保留官方SDK长连接与端到端真实收发验证，P1-17保留整个Phase1验收和学习材料。


## P1-16 当前装配入口

此前正文中的待装配描述保留为本任务交付时点；P1-16现已提供[官方SDK与生命周期入口](feishu-runtime.md)，复用本模块。真实服务及容器运行结果以[开发进度](development-plan.md#phase-1-任务进度)为准，不将离线用例解释为整体验收。
