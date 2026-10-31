# 运行与排错

使用仓库.venv Python3.12和锁定api依赖。uvicorn工厂入口仍为`clinical_agent.api:create_app --factory`；Docker/Compose不需因目录迁移修改。

启动失败：从lifespan配置验证→open_api_runtime→共享科研装配核查，客户端只得到脱敏startup_failed；不输出密钥。503 busy：看max_in_flight和实际运行Future，取消等待不会终止运行任务。关闭卡住：先确认同步任务是否结束，不能强行在其执行中关闭借用资源。

旧local请求在业务入口被拒绝，会遮挡注入服务的预设错误。新增test_api_migration.py显式使用online来验证原错误映射和池满行为；历史29失败保持记录，不借迁移撤门禁或改旧业务断言。

独立导入api_runtime和api子模块必须都成功；若出现partially initialized module，检查canonical模块是否反向导入旧兼容模块。ApiSettings仍只在lifespan进入时实例化，不能在导入时读取配置。

实际测试结果与未验证项以阶段acceptance.md为准。真实模型、数据库、Redis及飞书未执行时不得据Fake测试声称端到端通过。
