# 修改练习与独立实现

先运行tests/unit/test_rag_db_migration.py；理解旧新模块身份、两种导入顺序、完整DDL、迁移hash、AST和无I/O导入检查。

修改练习（独立练习分支）：把一个旧模块别名改成简单函数重导出，运行模块身份测试，并阅读test_postgres.py的create_engine monkeypatch，说明为什么旧patch可能不影响新函数全局。恢复后再将ORM约束改一个字符，观察完整DDL冻结测试失败；不能通过更新fixture掩盖非授权Schema变化。

独立实现：在临时文件创建一个小模块及旧路径别名，验证两种import顺序下模块、类与可变计数器身份相同。不要在生产代码创建新Repository或额外框架。

验收：能指出解析、切分、索引、在线发现和证据判断分别在哪里；解释事务/engine/HTTP/模型的所有权；说明为什么离线DDL一致不等于真实数据库事务已验收。
