# 飞书与工程配置结构迁移 Phase 4 实际交付（2026-10-31）

## 1. 当前架构和执行链

`clinical-feishu` 进入 `clinical_agent.channels.feishu.main:main`。main 读取配置并显式组装 ResearchService、Redis 去重器、HTTP Client、Sender、Dispatcher 和官方 SDK。SDK 回调经 Receiver/filter_event 校验后非阻塞提交到有界 worker；worker 持有 Redis owner 租约调用 `respond()` 或 `report()`，再把 Delivery 移交有界 sender。sender 发送前检查所有权，明确成功后才标记 completed。关闭顺序仍为 worker → sender → HTTP/Redis/科研资源。

顶层 `feishu` 包不再保存算法，只把五个旧模块名绑定到对应 canonical 模块对象。`python -m feishu.main`、`python -m clinical_agent.channels.feishu.main` 和控制台命令均保留。

## 2. 问题与修改依据

原顶层 `feishu` 将通道实现放在项目主包之外；目标架构要求归入 `channels/feishu`。既有测试和调用方会 patch 模块全局，简单符号重导出会破坏注入可见性，因此兼容文件复用 Phase 3 的 `sys.modules` 同对象方案。

飞书日志 formatter 监听 `feishu` 命名空间。迁移后若继续使用 `__name__`，日志会变成 `clinical_agent.channels.feishu.*` 而脱离现有 formatter；新实现显式保留 `feishu.main`、`feishu.worker` 和 `feishu.sender` 名称。迁移前当前工作区源码保存在 `before/`，AST 检查仅归一化内部导入、Ruff 导入排序和日志名，不重写业务算法。

## 3. 迁移计划与映射

五个模块逐文件移动：main、events、dedup、worker、sender。实际路径见 `migration-map.md`。保留旧包、两个 `python -m` 入口、`clinical-feishu` 命令、可选依赖和 Compose 入口；不合并文件，不改变同步/异步边界。

工程配置只把 pyproject 控制台入口指向 canonical main，并继续打包 `clinical_agent*` 与 `feishu*`。`uv.lock`、Dockerfile、Compose 内容和可选依赖冻结不变。Alembic 仍为显式机制，不整理版本目录、不生成或执行迁移。

## 4. 实际修改

- 新增 `clinical_agent/channels/feishu`，保存五个唯一实现及无副作用包入口。
- 将顶层 `feishu` 五个模块改为同模块对象兼容文件；旧包 `__init__` 保留。
- 更新 `clinical-feishu` entry point；未改 `clinical-agent`、API 或数据库入口。
- 新增迁移契约 fixture 和专项测试，冻结 FeishuSettings Schema、Redis Lua hash、依赖/部署文件 hash、源码算法、导入顺序、日志、CLI、无 I/O 导入和 wheel 内容。
- 更新 AGENTS 架构边界与验证命令、当前架构和状态文档；新增六份学习材料及离线 Demo。
- 未删除旧入口、未改 Prompt、Agent State、API、数据库 Schema、依赖版本、锁文件、Docker/Compose 或 Alembic 版本。

本轮新增兼容代码没有重试、降级、默认成功、通用 Factory/Repository 或异常吞并。原边界中为未知 Redis/HTTP 结果保留的处理属于既有交付正确性契约。

## 5. 兼容性检查

- 五组旧新模块在两种全新导入顺序下均为同一对象，旧路径 monkeypatch 对 canonical 实现可见。
- 迁移后源码与五份 before 快照的 AST 一致，仅含冻结允许的导入及日志名变化。
- FeishuSettings JSON Schema、Redis Lua 脚本、事件和消息 DTO、worker/sender 状态及容量未变。
- `--help` 返回 0、非法参数返回 2，均在读取配置和连接服务前退出；三个入口不产生 RuntimeWarning。
- 日志仍进入原 `feishu` JSON formatter；wheel 同时包含新包与旧兼容包，entry point 指向新 main。
- ResearchService 调用仍为 `respond()` / `report()`；资源关闭顺序、SDK 专用 loop、HTTP 超时及未知交付语义保持。

## 6. 验证结果

环境：Windows/PowerShell，仓库 `.venv` Python 3.12；没有安装或更新依赖，没有连接真实数据库、Redis、模型、飞书或第三方 API。

1. 飞书迁移及全部既有飞书/相关契约专项：**409 passed、2 个 SDK 弃用警告**，106.97 秒，见 `targeted.txt/xml`。
2. 完整默认离线回归：**1622 passed、29 failed、122 deselected、0 skipped、0 errors、3 warnings**，260.81 秒，见 `full.txt/xml`。29 个失败测试身份与 Phase 3 完全一致，新增 0、消失 0；整库仍未通过。
3. `.venv/Scripts/ruff.exe check src tests` 通过，见 `ruff.txt`；IDE 对本阶段 Python 文件未报告 lint 错误。
4. `.venv/Scripts/python.exe -X utf8 -m mypy src --no-error-summary` 失败，共 **193 条**既有类型错误，见 `mypy.txt`；未标类型检查通过。
5. `uv lock --check --offline` 通过，解析 139 个包；未重写 `uv.lock`，见 `lock-check.txt`。
6. 在独立临时副本构建 wheel 成功；静态检查确认新旧包文件和 `clinical_agent.channels.feishu.main:main` entry point，见 `wheel-build.txt`、`wheel-check.json`。未安装 wheel。
7. 学习 Demo 退出 0，真实事件过滤得到 accepted、文本去空白、request_id 稳定且旧新 events 为同一模块；Demo Ruff 通过，见 `demo.txt`。它不代表真实收发。
8. 本阶段差异 `git diff --check` 通过。未重建镜像、启动 Compose、运行 Alembic 或部署服务。
9. 文档收尾后单独复验 `test_feishu_migration.py`：**27 passed、1 个 pytest cache 权限警告**，19.55 秒；测试本身通过，警告未当作通过项。

## 7. 剩余风险、教材与停止边界

相对 Phase 3 基线的结构兼容门槛满足，但整库因原 29 项失败未通过，193 条类型错误仍开放。默认回归排除的 122 项不计通过。真实 Redis 原子行为、飞书 SDK 连接、消息发送 ack、关闭中的在途任务、数据库/模型/外部 API、部署和医学人工签署均未执行。

教材位于 `docs/learning/phase-04/feishu-migration`。新增知识点包括：通道边界、有界回调、owner 租约、未知交付语义、同模块对象兼容、日志命名空间和 wheel 入口验证。

旧 `feishu` 包与 Compose 旧入口继续保留。删除须在 Phase 5 提供实际引用证据、影响范围和回滚方案，并获得明确确认。本阶段到此停止，不自动进入 Phase 5，也不改变历史业务 Phase 4 的验收事实。
