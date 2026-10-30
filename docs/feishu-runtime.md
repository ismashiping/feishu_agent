# P1-16 飞书运行时与部署入口

> 2026-10-30工作区变更：普通文本经respond执行单次规划，方向评估进入已有报告流程，比较/论文解释/定义/一般问答走回答流程；有阻断歧义先澄清。/report继续显式请求报告。代码未部署且待测试，详见[契约](specs/tasks/natural-intent-routing.md)。

本任务新增第五个飞书模块 `src/feishu/main.py`，保留现有 events/dedup/worker/sender 的职责。实现和离线验收边界见 [任务SPEC](specs/tasks/p1-16-feishu-runtime.md)。Phase1尚未整体验收；真实租户收发和容器运行不能从默认pytest推导。

## 它解决什么问题

P1-15已经能渲染和受限发送，但没有程序负责创建研究服务、Redis和HTTP客户端，也没有官方SDK把网络事件交给现有过滤器。main.py只负责这些装配、适配和关闭；临床研究规则仍在共享ResearchService里，SDK不进入核心业务层。

## 安装与配置

项目根目录，使用项目解释器：

```powershell
.venv\Scripts\python.exe -m uv sync --frozen --all-extras
.venv\Scripts\python.exe -m feishu.main --help
```

安装固定 `lark-oapi==1.7.5`，其websockets约束使正式锁从17.3降为15.0.1，另新增pycryptodome 4.2.0。不是原样保留旧锁。`clinical-feishu`与`python -m feishu.main`调用同一入口。导入及help不读取配置、不加载SDK/模型、不创建线程或连接。

| 环境变量 | 值与约束 |
| --- | --- |
| CLINICAL_AGENT_FEISHU_APP_ID | 自建应用ID，必填 |
| CLINICAL_AGENT_FEISHU_APP_SECRET | 必填，仅环境注入，不输出repr |
| CLINICAL_AGENT_FEISHU_BOT_OPEN_ID | 本应用机器人的open_id，必填，用于自身过滤与群提及匹配 |
| CLINICAL_AGENT_FEISHU_MODEL_DIR | 已存在的固定E5模型快照目录，必填 |
| CLINICAL_AGENT_FEISHU_REDIS_URL | 必填，redis/rediss URL，禁止query/fragment覆盖超时设置 |
| CLINICAL_AGENT_FEISHU_CAPACITY | 1–4，默认2，执行中研究任务也计入 |
| CLINICAL_AGENT_FEISHU_SENDER_CAPACITY | 1–64，默认8，执行中的发送也计入 |
| CLINICAL_AGENT_FEISHU_SHUTDOWN_SECONDS | 0–120，默认5，每次排空的等待窗口，CLI最小0.1秒；不是强杀期限 |

数据库和DeepSeek环境变量沿用 [CLI](cli.md)、[数据库](postgres.md)与 [RAG](basic-rag.md)，不新增第二套研究配置。程序不会自动读取`.env`；Compose由CLI解析自己的env文件，再显式注入容器。不要把真实配置加入源码、日志或构建上下文。

## 按实际执行顺序理解代码

1. `main()`先解析help与环境配置，再配置飞书专属JSON日志。`build_runtime()`调用现有`open_research(model_dir)`，只创建一个共享研究服务、模型、engine和LLM客户端。
2. 装配`RedisDeduplicator`：lease/max_processing均120秒，覆盖worker默认90秒研究+15秒交接+5秒余量。Redis仍使用已有1秒连接/操作超时、零重试及owner Lua，不改算法，不后台续租。
3. 创建无环境代理、无重定向/重试、无默认鉴权和日志hooks的HTTP客户端；`TenantToken`借用它，每次发送前按deadline单次获取官方tenant token。无新增缓存，增加一次鉴权HTTP开销，以保持MVP简单。鉴权不能占用SDK事件循环，也不需要sender线程取得自己才能推进的token。
4. 先创建`Sender`，再创建借用该sender与研究服务的`Dispatcher`。中途失败由ExitStack逆序清理，已启动sender先排空。
5. `run_sdk()`创建官方事件处理器并订阅`im.message.receive_v1`。`Receiver`只取已约定的schema/header/sender/message/mentions字段，交给`filter_event`；不凭空补事件ID或绕过自身/群提及过滤。SDK对象不是业务DTO。
6. accepted事件经Dispatcher接纳、原子判重后执行共享服务；回调不等待Future，不在SDK线程研究或发送。接纳阶段Redis I/O仍可能阻塞至既有有限超时。busy/unavailable/submit_failed尝试既有固定通知；duplicate/closed/ignored/rejected不回复，避免重复/无可信回复对象。
7. 研究结束沿用Delivery→Sender；获取token后，既有OfficialMessageAPI仍在实际消息POST前检查owner/deadline。真实发送成功才owner complete；未知结果保留TTL，不重试。

```mermaid
flowchart LR
    SDK[官方SDK帧与事件处理器] --> R[Receiver字段映射]
    R --> E[既有filter_event]
    E --> W[既有Dispatcher与Redis]
    W --> Q[共享ResearchService]
    Q --> S[既有Sender]
    S --> T[有期限tenant token]
    T --> H[官方消息REST]
```

## SDK接口取舍与停止

[官方1.7.5发行](https://pypi.org/project/lark-oapi/1.7.5/)的实际wheel显示：`ws.Client.start()`没有公开stop，发现请求也没有timeout。本项目把兼容点集中在main.py：局部子类只覆盖`_get_conn_url`，用5秒HTTP timeout解析官方EndpointResp/ClientConfig；帧、合包、心跳、重连仍由SDK处理。鉴权使用[官方内部应用token接口](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)，沿用P1-15 REST消息协议。

专用CLI进程使用SDK模块的loop，调用`_connect/_ping_loop/_disconnect`；只能在专用、未运行的事件循环使用。SIGINT/SIGTERM让stop置位；SDK后台任务未处理异常也会终止入口，不能留下无接收能力的进程继续等待。随后取消SDK任务、最多3秒等待disconnect、关闭loop并恢复信号与SDK日志状态。SDK原始日志会含payload/连接URL，运行期间禁用；只输出项目固定事件、UTC时间、request_id、状态和去重结果。安装SDK的首次导入可能较慢；本机冷导入曾触发20秒诊断，但栈显示仍在导入生成模块，不是网络等待。

私有接口是明确的版本风险：升级SDK前必须重跑DTO/事件处理器、协议数据帧ack、发现接口及停止测试；代码也拒绝非1.7.5运行版本。不宣称这是SDK公开支持的嵌入API。

SDK停止后，`BotRuntime.close()`先停止接纳并等worker实际结束，再等sender实际发送/清理结束，最后关闭HTTP、Redis和研究上下文。False表示尚未排空，保留全部依赖，可重复等待；CLI每个窗口记录固定draining，继续排空。HTTP的分阶段timeout和协作式研究预算均不提供硬线程终止，Compose最终SIGKILL可能丢回复，不能承诺exactly-once。关闭资源异常固定输出并非零退出，不回显原始异常。

## Compose用法与验收前提

`Dockerfile`按uv.lock安装api/rag/db/ml/feishu共用镜像，使用非root用户；默认执行机器人入口。`.dockerignore`采用允许清单，只传源码/锁/迁移，不传本地.env、模型、测试数据或研究缓存。模型通过只读挂载提供；不在镜像构建时下载模型。

`docker-compose.yml`保留原postgres，增加不持久化的Redis与`api`/`bot` profiles。API和机器人镜像均为`clinical-literature-agent:local`；数据库与Redis健康后再启动依赖服务，API另有ready健康检查。机器人进程存活不等于已连接，本任务不添加伪就绪HTTP接口。Redis不发布宿主机端口；postgres/API仅绑定127.0.0.1。数据库不自动迁移；模型和数据库内容也不自动准备。

在准备真实环境变量及模型目录后，以下为运行步骤，**不是本次已执行成功的容器命令清单**：

```powershell
docker compose --profile api --profile bot config --quiet
docker compose --profile api build api
docker compose up -d postgres redis
docker compose --profile api run --rm --no-deps api alembic upgrade head
docker compose --profile api up -d api
# 先通过现有CLI/API导入合成或允许使用的文献，再显式启用测试机器人。
docker compose --profile bot up -d feishu_bot
docker compose --profile bot logs -f feishu_bot
docker compose --profile bot stop feishu_bot
```

模型宿主目录用`CLINICAL_AGENT_MODEL_DIR`覆盖；容器内统一`/app/model`。`incoming_data`为API只读导入卷，`snapshot_data`为可写快照卷；准备导入文件时需单独拷入卷，API不接受宿主绝对路径。Linux bind mount需给UID10001读权限；宿主替换快照卷时还需写权限。默认API无鉴权，维持既有本机开发边界。Compose不替代生产安全部署方案。

真实收发需要自建测试应用启用机器人、发布权限、长连接订阅`im.message.receive_v1`，以及向机器人发送文本的专用测试会话。核对自身/非文本/未提及群消息不研究、正常文本仅研究一次、友好错误、停止排空；保留脱敏request_id和状态证据。不要在测试中向非测试群或真实患者发送内容。正式启用外部业务前还需完成仓库已记录的解释器构建核查要求。

## 调试与练习

目标命令：`.venv\Scripts\python.exe -m pytest tests/unit/test_feishu_main.py tests/unit/test_feishu_deployment.py -q`。真实SDK对象/帧与真实线程参与；HTTP/Redis/研究结果使用明确替身，不能当作真实飞书或数据库验收。完整执行结果见[进度](development-plan.md#p1-16-本次执行2026-10-27)。

固定startup/connection错误先核对配置、模型目录、DB/Redis及应用权限；不要为排错打开SDK DEBUG日志。draining表示实际任务未结束，不应提前关闭HTTP/Redis。镜像构建访问Docker Hub失败时，config/pytest通过不能代替build成功。

练习：把研究服务替身改为抛错，观察仅发送research_failed提示；把sender容量改为1并阻塞HTTP，观察worker交接失败且不无限积压；把token响应改成超时，确认没有消息POST且释放owner。独立实现练习：不用重写RAG，在现有Receiver测试中增加群提及与duplicate组合断言。

30秒口述：我把官方SDK限制在入口适配层，过滤、去重、有界执行和发送仍复用既有模块。一个共享研究服务避免每条消息重复加载模型。关闭时先停止接收，再按worker、sender、客户端顺序排空；超时不等于线程已结束。通过SDK真实DTO、协议帧和HTTP替身验证边界，但真实租户与容器运行需要独立验收。


## 本次执行结果

367项联合通过；1022 passed, 93 deselected, 1 warning in 106.53s (0:01:46)；Ruff/格式/mypy与锁/安装检查通过。真实身份接口成功；实际1 failed，185.34秒；真实SDK连接已确认，但180秒测试窗口内未收到指定口令（No matching test nonce received），未发生已确认测试回复；不得标真实收发通过。共享镜像实际构建因Docker Hub鉴权网络超时失败，未进入Linux安装。共享镜像构建因Docker Hub网络失败，Linux安装与容器启动/停止尚未验收；真实口令收发也未闭环，不能将P1-16或Phase1标记完整验收。外部测试使用隐藏输入的瞬时凭据及临时隔离Redis，默认pytest不会执行；运行前显式确认并配置LIVE_CONFIRM/LIVE_NONCE，其他消息一律忽略。


再次执行真实冒烟时，先准备专用Redis实例并在环境中提供FeishuSettings所需的应用/机器人/Redis配置，再显式设置`CLINICAL_AGENT_FEISHU_LIVE_CONFIRM=1`和`CLINICAL_AGENT_FEISHU_LIVE_NONCE`。命令为：

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/test_feishu_runtime_live.py -m "external and redis" -vv -s
```

该测试使用临时目录代替模型目录与合成ResearchPort，不加载真实模型；看到`P116_LIVE_CONNECTED`后才发送与LIVE_NONCE完全相同的测试文本。测试180秒后停止，只有收到口令、消息成功且真实Redis owner complete才通过。首次连接检测基于实际_connect完成；SDK的on_reconnected只表示重连，不能作为首次就绪信号。


### 开放平台消息订阅配置

本项目使用官方SDK长连接，不提供`/feishu/events` Webhook接收路由，不需要Cloudflare tunnel或开发者服务器HTTP请求地址。在测试连接在线时，到应用后台的「事件与回调 → 事件配置」选择「使用长连接接收事件」并保存，添加「接收消息 v2.0」（`im.message.receive_v1`）。开通私聊消息接收与机器人发送消息权限，按后台要求发布版本并确认测试用户在可用范围内；修改后重新发送测试口令，旧消息不应当作新事件已送达。

文本任务不要求添加卡片交互回调。同一应用若运行多个SDK客户端，不能假定每个客户端都会收到同一条消息；本次测试需使用指定测试应用和接收进程。应用凭据鉴权成功、WebSocket建连成功、消息事件收到及消息发送成功是四个不同的检查点。

官方入口：[Python事件处理](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/handle-events)、[消息事件与权限](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1)。平台页面正文可能需要浏览器加载，请以应用后台实际显示为准。外部测试默认180秒，通过`CLINICAL_AGENT_FEISHU_LIVE_TIMEOUT_SECONDS`可显式设置1–600秒；延长窗口不表示收发已通过。


最终真实联调补记：用户重发并核对接收方式后，显式延长窗口至600秒；实际1 failed、606.82秒，已建立SDK连接但仍未收到指定口令/消息事件。不能确认原因是订阅方式、未生效权限、测试目标或其他客户端接收中的哪一项；未声称发送成功。需在开放平台选择使用长连接接收事件，添加im.message.receive_v1并发布所需权限后重新联调。最后证据live-external-600s.txt；接收进程与临时Redis均已清理。

## P1-16 发布后真实收发补验（2026-10-27）

用户在开放平台发布配置后再次执行既有external+redis测试：**1 passed、1个SDK弃用警告，34.38秒**。实际输出依次为P116_LIVE_CONNECTED、P116_LIVE_EVENT accepted/eligible、P116_LIVE_SENT；真实官方SDK收到指定口令，官方reply接口明确成功，真实Redis owner complete返回owned。证据`.artifacts/p1-16-20261027/live-external-published.txt`。旧180/600秒未收到事件的失败保留为当时事实，本次已补齐指定口令收发验收；不能将旧记录当作当前收发状态。

研究端口为明确的合成ResearchPort，仅回复本地范围/合成测试的证据不足文本，未执行真实医学检索、E5/PG/付费LLM完整链路，也未把HTTP成功当成医学正确性。沿用当前实现，没有因联调成功修改核心代码或放宽测试。凭据仅通过隐藏终端输入及进程环境传递，不写源码或证据；运行结束SDK进程及临时隔离Redis已退出。

当前剩余P1-16验收为Linux共享镜像构建、Compose容器启动/停止；不因真实收发成功自动标记部署或Phase1完成。P1-17未开始。

## P1-16 Linux容器最终验收（2026-10-27）

本次完成P1-16剩余验收，以下结论取代此前“镜像网络阻塞/容器待验收”的当前状态；旧失败保留为历史。

Docker直连Hub超时后，只读确认既有本机7890代理可访问官方registry。使用官方google/go-containerregistry的crane v0.22.1（校验官方release SHA256）获取固定python:3.12.15-slim-bookworm及redis:8.2.2-alpine的linux/amd64镜像；未使用不明镜像源、未关闭TLS/摘要检查、未改Docker/系统全局代理。Python源platform manifest为57d96f71de145a98e7ceca18ee4ade77bba4103a33a72dfaea026b23625c6bf0，Redis为3f835dae62fe5012baf5a768293967c93bc09cf9e848d415351dfba04ee87537。导入后以临时HTTP_PROXY/HTTPS_PROXY build args和正式uv.lock构建共用镜像；生产镜像未保留代理或凭据ENV。89个Linux运行包安装并uv pip check通过，CLI help与非root配置通过。

首次Compose脚本在机器人就绪日志上超时，不能算通过。定位发现_LOG=logging.getLogger(__name__)在python -m入口下成为__main__，脱离feishu JSON handler。新增真实runpy别名测试先RED（1 failed/48 deselected，entrypoint-red.txt），固定logger名称为feishu.main后GREEN（1 passed/48 deselected，entrypoint-green.txt）；仅这一行应用修复，不改SDK/研究/去重/发送算法。第二次脚本仍超时，核查是验收辅助脚本仅采集docker logs的stdout，漏掉了JSON日志所在的stderr；修正为日志命令合并两流，未放宽就绪条件，旧失败另存compose-accept-result-initial.json与compose-accept-result-stdout-only.json。修复后368联合（94.44秒）及1023 passed/93 deselected默认回归（155.73秒）通过；Ruff/format（82文件）/mypy（38源码）通过。证据container-fix-*.txt。

最终Compose使用独立项目clinical-p116-accept-20261027、全新测试卷及空env文件，端口通过验收override移除，避免触碰既有数据库/服务。PostgreSQL/Redis健康、现有Alembic迁移、真实E5只读挂载、API runtime ready与空库问答insufficient_evidence/零claims/零sources均通过；未调用付费LLM。生产python -m feishu.main入口加载共享研究装配并连接真实SDK；API/机器人使用同一镜像、UID10001、只读模型。收到SIGTERM后机器人exit_code=0，API exit_code=143且日志明确Application shutdown complete/Finished server process，两者OOMKilled=false。Uvicorn0.54会在优雅关闭后重新抛出已捕获信号，因此Linux API的143可为正常信号退出，不能单独据此判定失败或成功；已按实际源码及关闭日志修正验收判据，旧误判记录另存compose-accept-result-api143.json。随后只删除本次项目的容器、卷及网络，清理断言通过。实际脚本耗时111.28秒，脚本断言通过，不冒称pytest用例数量。

最终应用镜像ID：sha256:013d6909cef814039ea1f610e5bd4f4c1f60fc65e683714d2bde603266e50a9c。证据docker-build-proxy.txt、python-base-pull.txt、redis-base-pull.txt、image-check.json、compose-accept-result.json、compose-accept-commands.json及compose-accept-api/feishu_bot.log。真实口令收发仍以此前live-external-published.txt的1 passed/34.38秒为准（研究为合成替身）；本次生产容器验证启动/连接/停止，不追加真实医学消息。

P1-16任务内无阻塞，Phase1尚未整体验收。真实E5/PG/付费LLM完整研究链路、医学支持关系人工审查、解释器升级前置要求与phase-01六份学习文档仍归P1-17；未自动开始。原有未提交改动保留，未创建Git提交。

## 探索型问题来源契约

普通文本与/report共用修复后的Planner门禁；未提供完整PICO不自动阻断。飞书文本及/report默认hybrid，会使用本地与PubMed；没有新增scope消息命令。需要显式local/online时使用CLI/API参数；回复保留真实在线查询追溯。见[增量SPEC](specs/tasks/exploratory-discovery.md)。
