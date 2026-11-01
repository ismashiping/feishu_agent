# Phase8学习导航：版本、增量、来源治理与重建

P8-01交付显式版本发布；P8-02补齐本地游标/调度/免编码dry-run，P8-03补齐来源治理，收尾增加在线窗口和显式重建。先读[原理](tutorial.md)及[代码路径](code-walkthrough.md)，运行demo.py，再做[练习](exercises.md)，参考[表达](interview.md)和[排错](troubleshooting.md)。[验收记录](../../phase8-acceptance.md)记录真实PG与未完成项。

项目根 `.venv/Scripts/python.exe -I docs/learning/phase-08/demo.py` 仅展示真实ORM版本归档表的DDL，不连数据库，不假装发布成功。

P8-02新增[本地更新批次/计划/恢复与有界调度](update-runs.md)，运行示例和限制以该文档及阶段验收为准；Phase8整体仍有在线同步/别名/模型重建待办。

P8-03新增[来源别名与状态治理](source-governance.md)及governance_demo.py。按领域契约→登记事务→检索门禁→引用/报告的顺序阅读；此前“别名未实现”仅代表P8-01/02历史时点。在线增量和重建仍未实现，Phase8不标整体完成。

Phase8收尾补充：[在线增量窗口、来源状态原子发布与显式重建](maintenance.md)。新的在线副本门禁会读取精确已知PMID状态，P8-03“只本地”的描述保留其历史范围。重建支持既定模型的重编码/分块策略调整，其他模型/维度明确拒绝；不等于通用模型迁移。
