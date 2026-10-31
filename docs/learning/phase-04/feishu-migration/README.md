# 飞书通道结构迁移学习导航

本目录讲解 2026-10-31 架构迁移 Phase 4，与历史业务 Phase 4 分开。

建议顺序：

1. `tutorial.md`：理解通道边界、幂等租约和有界执行。
2. `code-walkthrough.md`：按真实消息执行顺序阅读代码。
3. `troubleshooting.md`：定位导入、配置、Redis、SDK 和关闭问题。
4. `exercises.md`：完成安全修改与独立实现练习。
5. `interview.md`：准备面试表达。

运行最小 Demo：

```powershell
.venv\Scripts\python.exe -X utf8 docs\learning\phase-04\feishu-migration\demo.py
```

Demo 只执行纯事件过滤、稳定请求 ID 和旧新模块身份检查，不连接飞书、Redis、数据库或模型。实际验证范围见 `docs/feishu-migration-phase4/acceptance.md`。
