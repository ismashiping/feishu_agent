# P1-16 官方SDK长连接、装配与Compose入口

版本0.3；2026-10-27；P1-16任务范围已验收，368联合/1023默认回归、真实SDK收发及隔离Linux Compose通过。Phase1未整体验收。

## 1. 需求与目标
接续P1-12–15，落实P1-F06/07、P1-T07/10/11的生产入口；复用open_research、Dispatcher、Sender、RedisDeduplicator及官方SDK，不改研究服务或去重算法。

## 2. 功能需求
新增第五模块feishu/main.py；官方lark-oapi 1.7.5长连接订阅im.message.receive_v1，将SDK对象显式映射至filter_event既有字典契约；保持schema/header身份，不凭空补app/event ID。只将accepted交给Dispatcher；duplicate/ignored/rejected不发送；busy/unavailable/submit_failed发送既有固定通知，不执行研究。回调不等待Future或发送HTTP，Redis接纳仍有1秒I/O上限。

## 3. 非功能需求
导入无重型依赖/配置/I/O/线程；--help无资源；配置仅显式环境。统一使用项目解释器、版本锁和现有五模块边界。SDK原始日志可能含payload、连接URL/密钥，运行期间静音SDK日志，项目日志只允许固定事件/状态与request_id，不输出异常正文或配置；入口日志固定在feishu命名空间，模块以python -m运行时也必须进入配置的JSON handler。配置与外部边界可注入测试。

## 4. 功能边界
不实现Phase2状态、重试框架、多Agent、实时检索、迁移新版本或自动入库。Compose提供运行入口而非默认启动真实机器人。真实租户验收需要显式凭据、应用权限/事件订阅与测试消息；未具备不得标记真实收发通过。P1-17阶段验收及六份学习材料不在本任务。

## 5. 输入输出
FeishuSettings环境前缀CLINICAL_AGENT_FEISHU_：app_id、app_secret(SecretStr)、bot_open_id、model_dir(已存在目录)、redis_url(SecretStr、无query/fragment)、capacity(1–4默认2)、sender_capacity(1–64默认8)、shutdown_seconds(0–120默认5)。密钥不出现在repr/错误输入。启动先校验配置，再装配一个共享ResearchPort、无重试/无重定向/trust_env=False的HTTP客户端、Redis、sender、worker。python -m feishu.main/clinical-feishu启动，失败固定消息且非零退出。

## 6. 数据模型和预算
复用既有DTO与默认worker 90秒+handoff15秒；装配DedupPolicy lease_ms=120000/max_processing_ms=120000，覆盖既有110秒门槛；不后台续租。发送沿用5秒，队列8。HTTP鉴权每次按deadline单次调用官方tenant_access_token/internal，不新增缓存；严格校验响应、token及expire，HTTP超时为剩余预算且不超过5秒。token调用后仍由发送器检查deadline/owner。鉴权失败明确未发送消息，不自动重试。

## 7. 流程和生命周期
资源装配完成→SDK连接→过滤/接纳→共享研究→既有Sender发送。SDK 1.7.5没有公开stop且发现请求无timeout：局部子类覆盖_get_conn_url，用既有HTTP客户端补5秒期限与官方EndpointResp/ClientConfig映射；协议帧、分片、心跳和重连沿用SDK。专用CLI事件循环使用SDK的_connect/_ping_loop/_disconnect；SIGINT/SIGTERM停止等待、取消SDK任务、有期限disconnect，恢复信号和SDK日志状态。此私有接口是固定版本兼容点，升级必须复验。启动失败同样清理。worker.close成功→sender.close成功→HTTP/Redis/研究资源逆序关闭。关闭超时返回False且保留依赖，可重复排空；CLI定期等待并只记录固定draining，进程管理器最终强杀不能承诺回复完成。

## 8. 异常处理
非法/不支持SDK事件不调用研究；不回显原文。Redis故障fail closed。SDK连接失败不伪装就绪，非零退出；运行中重连由SDK负责。HTTP分阶段timeout不是硬墙钟限制；已开始请求不能撤回，未知投递保留TTL。SDK停止和线程排空分别处理，不提前关闭借用资源。资源构造中途失败只关闭已拥有资源。

## 9. 测试场景
配置正常/非法/隐私；真实SDK DTO与dispatcher构造、缺header/畸形/群提及/机器人过滤；accepted/duplicate/busy/故障通知；实际worker→sender→MockTransport的共享ResearchPort与owner complete；鉴权成功/失败/迟到/无缓存/超时/无重定向；SDK发现请求期限、实际SDK协议handler、连接/关闭/任务取消和信号恢复；装配复用、逆序关闭、超时不关闭依赖及启动回滚；隔离导入、help；Dockerfile/Compose共享镜像/依赖/健康检查/模型挂载/无嵌入密钥。替身不算真实租户。

## 10. 可执行验收
先tests/unit/test_feishu_main.py真实缺模块RED，再实现GREEN；飞书联合及默认pytest、ruff check/format、mypy src、uv lock --check --offline和uv pip check。证据.artifacts/p1-16-20261027；命令子进程清除PYTEST_ADDOPTS/PYTEST_PLUGINS且独立basetemp/cache。Compose config静态验证、能用Docker时构建共享镜像；真实服务另记，不用离线结果代替。

官方依据（2026-10-27核查）：[PyPI固定版本](https://pypi.org/project/lark-oapi/1.7.5/)、[官方源码](https://github.com/larksuite/oapi-sdk-python/blob/v2_main/lark_oapi/ws/client.py)、[鉴权](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)。实际兼容接口以下载的1.7.5 wheel源码及安装测试为准，不以变动的主分支代替。

## 11. 完成定义
代码/锁文件/测试/部署入口/任务使用和取舍说明/进度记录齐备。离线验收、容器构建、真实租户收发分别报告；缺外部前提的项目明确未验收，不能标P1-T11/Phase1完成。完成当前可执行范围后停止，不进入P1-17。
