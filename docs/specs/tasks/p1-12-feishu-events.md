# P1-12：飞书消息契约与事件过滤

版本：0.2；日期：2026-10-27；状态：本任务范围已验收，Phase 1整体未验收。范围：纯事件边界，承接MVP P1-F07、P1-T08的过滤部分；不实现P1-T08的重复裁决。88项事件测试、34项隔离导入、777项默认回归通过，执行记录见[开发计划](../../development-plan.md)。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

P1-01–11已有离线文献/RAG/CLI/API；仓库尚无飞书实现或本任务详细SPEC。按既定五模块架构，先实现src/feishu/events.py，明确哪些消息可进入后续接纳流程。

## 2. 功能需求

处理schema=2.0、header.event_type=im.message.receive_v1的解码字典；只受理目标app_id的人类文本。过滤机器人及自身open_id、非文本、不支持会话；单聊允许，群聊只允许明确@本机器人且占位符出现在正文中的消息。只移除本机器人的完整@占位符，其他正文保持，最后strip。

## 3. 非功能需求

纯函数、无日志/网络/配置读取/资源创建，不调用RAG。外部字段严格检查使用部分，允许无关扩展字段；错误返回固定reason，不携带原始输入/异常。DTO复用现有Pydantic及核心DTO配置，无新依赖。

## 4. 功能边界

不实现SDK安装/对象适配/长连接/签名认证、Redis占位、重复裁决、有界工作池、业务调用、消息发送、Docker或环境配置。输入必须由未来官方SDK认证/解码边界提供，不能直接当公网Webhook处理器。重复输入仍返回accepted，本任务不声称完成去重。

## 5. 输入输出契约

filter_event(payload: object, *, policy: EventPolicy) → EventDecision。policy显式app_id与bot_open_id；不读取环境。结果status为accepted/ignored/rejected，reason固定枚举，只有accepted携带MessageEnvelope。accepted仅代表过滤通过，未取得容量或租约。duplicate留待去重任务。

顺序：字典/header结构→事件类型/schema→目标应用→sender及message结构→自身/机器人→人类身份→消息类型→会话类型→内容与mentions→文本→去重ID。明确无关事件/其他应用/机器人/非文本不解析其内容。结构损坏rejected；不支持事件/schema、其他应用、机器人/自身、未知sender/chat类型、无群聊@为ignored。

使用open_id作为发送人身份，不以user_id/union_id回退混用命名空间。缺失/null/空白message_id/event_id视为无ID；存在但类型或格式错误则拒绝，不回退掩盖损坏。至少一个ID，优先message_id。

## 6. 数据模型

events.py包含EventPolicy、MessageEnvelope、EventDecision。标识严格字符串，匹配[A-Za-z0-9_-]，1–256字符，不修剪非空ID；可选ID空白归一null。MessageEnvelope含app_id、message_id/event_id、sender_id、sender_type=user、chat_id、chat_type=p2p/group、message_type=text、text、request_id(UUID)。text strip后1–4000字符，与QuestionRequest一致；保留Unicode/换行。

dedup_identity为(app_id, message或event, ID)三元组，区分应用与ID类型，后续Redis键编码由去重任务负责。request_id以uuid5(NAMESPACE_URL, JSON编码dedup_identity)生成，重复同消息稳定；不信任外部request_id。DTO禁止未知字段、重验实例。EventDecision验证status/reason/envelope一致。

## 7. 核心业务流程

校验策略→读取可信解码字典→固定顺序过滤→解码message.content JSON对象的text→群聊验证mentions并清除本机器人完整占位符→文本限制→校验去重身份→构造共享消息DTO。未来worker再接纳/占位并构造QuestionRequest，本任务不复制研究业务。

## 8. 异常与边界场景

message.content必须是JSON字符串，UTF-8编码最多32KiB；正文超过4000拒绝而不截断。拒绝无效Unicode、坏JSON/非对象/非字符串text、空白正文、深嵌套JSON、重复JSON键。最多100个mentions；群聊mentions缺失/null等同无@，其他类型/损坏条目拒绝；key匹配@_user_[1-9][0-9]*，id.open_id有效，同key冲突拒绝。匹配完整占位符，不能将@_user_1误删自@_user_10。单聊不消费mentions。bot_open_id缺失或非法由策略DTO报ValidationError，不自动放行群聊。

## 9. 测试用例清单

- 正常单聊/群聊、Unicode/换行、扩展字段、@清除与保留其他@、占位符边界。
- 自身/所有bot、非文本、不支持事件/schema/应用/会话/发送者类型；忽略路径不解析坏正文。
- 缺字段/错类型/空ID/双ID缺失/优先与回退/应用或类型隔离/稳定request_id。
- JSON类型/编码/重复键/嵌套/32KiB、4000字符边界、空白、mentions损坏/冲突/上限。
- DTO未知字段/不一致决策/非法策略；过滤不修改输入，重复不是duplicate；导入隔离。

## 10. 可执行验收标准

先新增tests/unit/test_feishu_events.py，运行.venv/Scripts/python.exe -m pytest tests/unit/test_feishu_events.py -q得到缺模块RED；最小实现后GREEN。每次保存/清除并恢复PYTEST_ADDOPTS与PYTEST_PLUGINS，独立basetemp/cache，输出保存在.artifacts/p1-12-20261027-01。运行默认完整回归、Ruff check/format、mypy src、uv lock --check --offline、uv pip check及git diff --check；manifest/lock不修改。test_package增加feishu导入隔离，不创建未来空模块。

## 11. 阶段依赖及完成定义（DoD）

过滤/契约/边界真实RED/GREEN、回归与使用文档、进度记录完成即验收P1-12；不代表飞书端到端/Phase1完成。不新增阶段学习材料，待Phase1验收时统一生成。下一任务建议Redis原子消息去重，须用户另行指定。

事件字段依据：[飞书官方接收消息](https://open.feishu.cn/document/server-docs/im-v1/message/events/receive)、[官方同文档国际入口](https://open.larkenterprise.com/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive)。2026-10-27官方搜索索引核对事件头与sender字段；正文直读为空壳，未声称验收SDK运行。群聊@策略、容量阈值与错误码是本项目决策，不是平台保证。
