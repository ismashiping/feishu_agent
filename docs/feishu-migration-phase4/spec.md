# 飞书与工程配置结构迁移 Phase 4 冻结SPEC

目标：将main/events/dedup/worker/sender五个现有模块迁入clinical_agent.channels.feishu，保留事件、Redis原子租约、工作容量、发送队列、重试/不重试及未知交付语义，不合并文件、不修改业务算法。输入为原SDK事件/配置及消息封装，输出为原准入/工作/交付状态、渲染文本和退出码。

旧feishu子模块按Phase3的同模块对象别名兼容；旧feishu.main在作为__main__执行时调用canonical main。新main仍支持python -m。clinical-feishu命令不变，pyproject入口指向canonical实现，包发现继续包含旧feishu兼容包。原日志命名空间feishu及feishu.sender/worker显式保留，避免__name__随迁移改变后日志脱离既有安全formatter。

先编写tests/unit/test_feishu_migration.py，冻结FeishuSettings JSON Schema、Redis Lua脚本hash、可选依赖、锁文件/部署文件hash以及五个源码快照。验收覆盖五组模块身份、两个全新导入顺序、AST只允许导入映射/排序和日志名保持、无I/O导入、旧新模块和console的--help/非法参数退出、日志路由和wheel内容。

复用全部飞书事件、dedup、worker、sender、main及资源关闭测试和全量离线回归，默认排除external/performance/database/redis。原29失败与193类型错误继续保留。真实Redis、SDK连接、发送ack和医学验收未运行单列。

工程配置：锁定依赖不变；uv lock --check --offline只验证，不自动重写锁。Docker/Compose保留旧入口作为兼容验证，不重建容器。确认Alembic为显式迁移机制，版本目录不整理、不执行迁移。更新AGENTS架构边界、命令及修改约束，保留已有用户规则。wheel在独立临时副本构建，检查新旧包和entry_points，不安装新依赖或覆盖现有环境。

命令：.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/feishu-phase4 --junitxml=docs/feishu-migration-phase4/full.xml；.venv/Scripts/ruff.exe check src tests；mypy src与Phase3归一对比；uv lock --check --offline；独立wheel编译及ZIP静态检查。失败修复后重跑受影响范围，如实保留失败。学习材料交付后停止，不删除任何兼容路径、不进入Phase5。
