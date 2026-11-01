# P1-15：飞书文本渲染与受限发送

版本：0.2；日期：2026-10-27；状态：离线发送边界已验收；72 sender目标、316联合、971默认回归通过；Phase1未整体验收。

## 1. 需求与目标

落实P1-F05/07、P1-T10的结果文本与受限投递，接续现有DeliveryPort、Delivery、Redis owner契约；沿用sender.py单发送线程/标准有界队列，不改研究工作流。

## 2. 功能需求

渲染合法ResearchAnswer的结论类别、逐结论来源编号与chunk标识、结论局限、来源标题/作者/日期/期刊/PMID/DOI/安全网络URL、document/hash/scope和证据定位，以及全局局限/本地范围声明。无证据明确不代表无效。保留完整关系，超限整体替换固定提示，不截断结论留下断裂引用，不分段多发。固定research_failed/busy/unavailable/invalid_input通知不回显异常或问题。

## 3. 非功能需求

每项最多一次消息请求；不重试、不递归错误、不持久化队列。导入无线程/I/O/配置及重型依赖。API使用已有锁定httpx（rag/api可选环境已有），固定官方HTTPS REST消息接口；token由有期限的注入函数提供，token获取/SDK长连接与生产装配留P1-16。不实现另一套鉴权缓存。研究/Redis/HTTP资源均借用，不由sender关闭。

## 4. 功能边界

不做SDK长连接、入口映射、Compose、Phase2状态、真实租户发送和Phase1整体验收。官方REST适配可离线测试；生产token提供者必须遵守传入的单调deadline且不能依赖sender执行线程取得token。没有凭据不调用真实API。

## 5. 输入输出

render_answer(answer)->str；Sender(dedup, transport, policy, clock)。offer(Delivery)->bool为现有非阻塞交接：有效快照入队才True；False不转移租约。offer_notice(envelope, code)->bool无租约通知，同队列同容量。无消息ID时按chat_id创建，正常有消息ID时reply。无owner通知不得complete/release。非法Delivery（非有限deadline、租约身份/请求ID不匹配、answer/error同时存在或皆无）拒绝并抛固定ValueError；没有接纳副作用。

## 6. 数据模型和预算

SenderPolicy：capacity严格整数1–64默认8，包含执行中项；send_ms严格整数1–10000默认5000，notice_ms严格整数1–15000默认5000。一个标准Queue与一个线程；研究deadline沿用P1-14，通知期限从接纳计时。文本content的JSON序列化UTF-8上限24000字节，完整外层JSON上限30000字节（项目保守上限，不宣称官方极限）；超长整体改为固定提示。使用ensure_ascii=False且保留中文/换行；不渲染本地source_uri，不允许元数据产生at标签，拒绝带凭据/非http(s)URL。

## 7. 流程与生命周期

入队快照→出队检查deadline→渲染→owner检查→再次deadline→单次transport.send。API在token取得后、实际消息HTTP前再调用owner/deadline门禁，避免token等待期间失租。确定sent才complete（错误提示成功亦同）；确定未发/明确拒绝failed按owner release；unknown保留TTL。owner lost/unavailable不发、不删除。每项只记录request_id、固定status与固定dedup结果，日志不记录正文/凭据/远端异常。

close(timeout_seconds=5)->bool停止接纳，有期限等待线程实际排空与清理，False不杀线程/不关闭借用资源，可重复等待；顺序为worker.close成功→sender.close成功→关闭共享客户端。HTTP timeout为剩余时间与send_ms最小值；httpx分阶段超时不是强制总墙钟上限，开始的请求无法撤回，晚到确认仍按sent处理并记录实际结果。容量只在实际处理/清理结束释放。

## 8. 异常处理

HTTP 2xx、严格整数code=0且data.message_id非空才sent；2xx业务非零码、4xx明确拒绝为failed；5xx/3xx/超时/连接异常/畸形响应及注入transport抛错均unknown，不重试。token阶段失败确定未发为failed。owner或Redis清理故障保留TTL/记录不可用，sent但complete失败不重发。不得假定HTTP与Redis跨系统原子性，不承诺exactly-once。

## 9. 测试场景

渲染合成PDF/摘要来源及多结论、编号映射、定位、局限、缺元数据/无证据/错误、标签转义、中文JSON字节和超长整体替换。真实线程Event验证容量含执行中、非阻塞拒绝、快照、关闭超时/排空、队列等待过期、出队owner/临发送复核、所有异常/完成/释放路径和日志隐私。httpx.MockTransport验证reply/create路由、Authorization、JSON双层序列化、timeout与全部响应边界；Dispatcher→Sender联动验证queued不等于completed、研究错误友好投递。新增sender隔离导入。替身不冒充真实飞书/Redis。

## 10. 可执行验收

先写tests/unit/test_feishu_sender.py运行缺模块RED，再最小实现GREEN。项目.venv/Scripts/python.exe；每轮清除并finally恢复PYTEST_ADDOPTS/PYTEST_PLUGINS，独立basetemp/cache；证据.artifacts/p1-15-20261027。目标及飞书联合、默认pytest、ruff check/format、mypy src、uv lock --check --offline、uv pip check、git diff --check真实执行。官方接口核查：2026-10-27 [回复](https://open.feishu.cn/document/server-docs/im-v1/message/reply)、[发送](https://open.feishu.cn/document/server-docs/im-v1/message/create)、[文本结构](https://open.feishu.cn/document/server-docs/im-v1/message-content-description/create_json)。

## 11. 完成定义

SPEC、真实RED/GREEN、边界/回归/静态验证、使用说明和进度齐备；清楚区分离线协议验证与真实租户收发。完成P1-15后停止；P1-16装配与P1-17阶段验收/学习材料仍待后续。
