# 练习与测试

## 修改练习

1. 从 fixture 选一个已删除旧模块，在隔离子进程中断言 `ModuleNotFoundError`，再断言对应 canonical 模块可导入。
2. 为活动导入扫描增加 `importlib.import_module("常量")` 场景，确认能发现动态旧路径。
3. 构建 wheel 并检查 ZIP 文件名，确认旧路径不存在、正式 console entry point 指向 canonical main。
4. 为 Dockerfile 和 Compose 编写静态契约，确保两者使用同一飞书模块入口。

## 独立实现练习

设计一个两阶段弃用方案：

- 第一版保留旧路径并发出可观测的 deprecation 日志。
- 统计仓库内和部署入口调用方。
- 第二版删除旧路径，并提供按批次恢复的最小补丁。

说明哪些证据来自静态扫描，哪些必须通过运行时或发布物验证。

## 评审练习

给出一个只有 `from new import X` 的三行 wrapper，不要仅凭行数决定删除。逐项核对动态导入、monkeypatch、console script、Docker 命令、历史教材和仓库外公共契约，再作结论。

## 完成标准

练习结果必须区分：仓库内引用归零、安装包收口、真实服务行为和医学验收。不得把“文件已删除”直接等同于“迁移完成”。
