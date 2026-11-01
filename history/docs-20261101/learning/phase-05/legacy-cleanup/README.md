# 遗留兼容层清理学习导航

本目录讲解 2026-10-31 架构迁移 Phase 5，与历史业务 Phase 5 分开。

建议顺序：

1. `tutorial.md`：理解兼容层、删除门禁和为什么不能直接删文件。
2. `code-walkthrough.md`：按四个清理批次阅读真实改动。
3. `troubleshooting.md`：定位旧导入、陈旧 console script、namespace package 和 wheel 残留。
4. `exercises.md`：完成引用审计与安全删除练习。
5. `interview.md`：准备渐进式重构的面试表达。

运行离线 Demo：

```powershell
.venv\Scripts\python.exe -X utf8 docs\learning\phase-05\legacy-cleanup\demo.py
```

Demo 只检查 representative canonical 模块和已删除旧导入，不连接数据库、Redis、模型或第三方 API。实际测试结果见 `docs/legacy-cleanup-phase5/acceptance.md`。
