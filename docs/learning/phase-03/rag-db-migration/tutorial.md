# 适配器按职责归位

## 是什么
RAG将本地文本解析成带来源位置的文档/块，以Embedding和数据库索引检索证据。Integrations处理外部HTTP或模型系统协议。DB负责SQLAlchemy模型和PostgreSQL持久化实现；业务筛选与医学引用规则仍属于application/domain。

## 为什么需要
原adapters目录混合本地解析、在线下载和数据库；分类后可直接找到实现，但不能为了目录而改算法或再做一层通用接口。

## 底层原理
本项目离线PDF使用pypdf，XML使用defusedxml，模型为显式加载的E5适配，向量/全文检索仍在PostgresRetriever。领域切分仍在domain.chunking，OA段落切分仍由application.oa_fulltext使用既有LlamaIndex SentenceSplitter。两条切分路径的语义和签名不同，不因迁移而强行合并。

SQLAlchemy Base.metadata持有表、约束和索引声明，Alembic版本管理Schema演变。移动Python文件不是数据库迁移；本轮冻结DDL和迁移文件hash，不运行upgrade。

## 最小Demo
运行demo.py：读取仓库已有PDF并查看解析页数；离线编译documents表DDL；检查旧新Embedding模块是同一个对象。没有真实Embedding或数据库连接，不代表检索端到端验收。

## 工程取舍
旧import依然被历史教材和测试使用，测试还会替换模块全局create_engine、load_local_embedder等。只重导出类函数无法让旧模块patch影响新模块全局，因此旧文件把sys.modules中的旧键绑定到canonical模块。两条路径共享同一个对象、锁和ORM注册表。旧postgres包不整体别名，子模块分别绑定，避免相同源文件以两个完整模块名重复执行。
