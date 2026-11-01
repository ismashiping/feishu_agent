# 练习

运行demo.py观察版本ID、document_id、归档JSON与活跃唯一索引。独立练习：用隔离测试库先普通入库，再显式更新，检查旧chunk ID仍存在load_version输出、新检索只见活跃chunks。

修改练习：在事务写chunks时注入失败，确认旧摘要与旧版本仍可读取；并发两次相同元数据更新只能一次metadata_updated、一次already_present。

测试入口tests/unit/test_knowledge_versions.py及tests/integration/test_knowledge_versions.py。数据库测试只允许隔离库，命令/结果见验收记录；缺真实PG不算通过。保持增量末集中验证，不新增逐会话测试要求。

P8-02练习：创建2文件manifest，令第二文件失败，检查cursor停在1，修复后原batch只重放第二文件。再模拟文档提交后checkpoint失败，版本重放不能重复。dry-run应不创建snapshot目录；真实库测试入口test_update_runs.py。

## P8-03练习

运行governance_demo.py，解释为何唯一DOI映射不是身份验证。修改练习：在专用测试库用同一DOI登记两文档，确认conflicted而非选择最新；用旧expected_event_id变更状态应失败。独立实现练习：仅在新测试中给source_states写入注入异常，断言事件数量和旧状态同时保持。不要在业务库运行迁移回退测试；不要为练习伪造真实医学依据。

## 收尾练习

修改练习：用MockTransport返回21条总数和20条记录，确认没有freeze/发布或游标越界；让状态写入抛错，确认文献版本一起回滚。独立实现练习：在专用库stage之后添加一篇新文献，确认activate报source_changed；恢复不是删除新文献，而是新run重新stage。只在允许清理的测试库运行迁移/隔离schema实验，不把工程自检当作医学召回证明。
