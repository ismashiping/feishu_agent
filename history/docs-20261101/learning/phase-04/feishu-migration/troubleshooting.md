# 运行与排错

## 新旧导入不是同一对象

执行：

```powershell
.venv\Scripts\python.exe -I -B -c "import feishu.main as a; import clinical_agent.channels.feishu.main as b; print(a is b)"
```

应输出 `True`。若为 False，检查旧兼容模块是否在导入 canonical 模块后执行了 `sys.modules[__name__] = _implementation`，不要改成复制符号的 `from ... import *`。

## 命令在缺少环境变量时访问服务

`clinical-feishu --help` 和非法参数应在构造 `FeishuSettings` 前退出。若出现 startup 错误，说明参数解析顺序被改变。

## 重复消息或错误删除租约

不要在 Python 中拆分 Redis 的读、owner 校验和写操作。检查 `_SCRIPT` 是否仍原子执行，发送成功前不要调用 complete，未知网络结果不要盲重试或删除不属于当前 owner 的 key。

## 机器人显示 busy 或 unavailable

`busy` 表示本地工作容量已满；`unavailable` 可能来自 Redis、执行器提交或发送移交不可用。先查看 `feishu_admission` 的 status，再查看 `feishu.worker` 和 `feishu.sender` JSON 日志。不要通过无限队列掩盖容量问题。

## 关闭时持续 draining

正常关闭顺序是 worker → sender → 共享资源。检查科研调用和发送调用是否遵守原 deadline，Redis/HTTP 超时是否仍有界。不要提前关闭 Redis 或 HTTP Client，否则队列中的任务无法完成所有权检查和交付。

## 可执行验证

专项测试：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q tests\unit\test_feishu_migration.py tests\unit\test_feishu_events.py tests\unit\test_feishu_dedup.py tests\unit\test_feishu_worker.py tests\unit\test_feishu_sender.py tests\unit\test_feishu_main.py
```

静态检查：

```powershell
.venv\Scripts\ruff.exe check src tests
uv lock --check --offline
```

真实 Redis、飞书 SDK 连接与发送确认属于显式集成验证，不能由离线测试替代。
