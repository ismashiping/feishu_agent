# 运行与排错

## 删除后旧包仍能 import

检查源码目录是否只剩 `__pycache__`。没有 `__init__.py` 的残留目录仍可能被识别为 namespace package。清理生成缓存后，在 `-I -B` 子进程中重新验证。

## canonical 导入缺少某个名称

旧聚合 wrapper 可能从多个模块重导出符号。不要把全部调用机械改到一个新文件；查看定义位置，例如 API 的 `ApiSettings` 属于 `schemas`、`WorkerPool` 属于 `execution`、`ServiceBundle` 属于 `runtime`。

## console 命令仍导入旧路径

修改 `pyproject.toml` 不会自动重写已经安装的 console script。使用锁文件同步环境或构建新 wheel 后再测。同步时必须保留项目需要的 extras；若默认 sync 移除了可选依赖，应使用 `uv sync --frozen --all-extras` 恢复。

## 静态扫描仍发现旧路径

区分活动代码和历史证据。`docs/archive`、before 快照及历史日志应保留原文；活动 `.py`、Docker、Compose 和 pyproject 必须归零。logger 名称 `feishu.sender` 不等于旧 Python 模块导入，不应机械替换。

## 验证命令

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q tests\unit\test_legacy_cleanup.py
.venv\Scripts\ruff.exe check src tests
.venv\Scripts\uv.exe lock --check --offline
```

真实 Redis、数据库、模型和飞书连接仍需显式集成环境；wheel 内容检查不能替代真实部署。
