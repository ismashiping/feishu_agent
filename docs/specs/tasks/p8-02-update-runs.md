# P8-02 本地增量批次、恢复、dry-run与调度

2026-10-28。只实现本地PDF/XML显式有序集合的更新，不宣称在线PubMed增量抓取、跨来源别名、模型重建或Phase9已完成。输入batch_id、allowed_root、相对文件列表及source_type，文件集合签名约束顺序/范围；窗口标记仅审计元数据，不伪装在线查询。

使用Postgres更新游标/运行表，跨进程session advisory lock防止同批重入；锁连接autocommit，不让模型运行占用写事务。每文件先复用IngestionService+VersionedPostgresStore提交文档，再持久化cursor与item结果；部分失败保持该文件游标，重启重放已提交项由版本幂等吸收。记录run_id、cursor_before/after、状态、条目、评估状态；cursor持久化失败可重放，不越过失败文件。

dry_run直接调用原PDF/XML解析器与只读历史读取，比较逻辑内容与元数据，不创建游标/运行记录、快照、模型或向量。固定batch路径不允许越界或重复；运行时重验真实路径。已完成批默认noop，显式rescan从0重新检查同集合；调度后续轮使用rescan，不改变文件集合，新增文件需新batch_id。只提供用户手动启动的有界循环脚本，不创建系统/聊天自动化。

固定小回归仅运行现有最小基线离线脚本，记录passed/not_accepted/failed/not_run；退出1保留not_accepted，不能标质量通过，评估失败不回滚已提交文档。嵌入/模型只在真实发布分支装配，dry-run无模型依赖。

先写tests/unit/test_knowledge_update.py、tests/integration/test_update_runs.py，再实现。验收含越界、部分失败恢复、cursor回放、dry-run零写/零编码、锁重入、rescan、评估状态与真实PG事务。阶段末集中执行目标及受影响版本/CLI/入库回归，实际依赖缺失不标通过。新增迁移p802_0005。P8-01物理文件hash与逻辑正文分开，元数据变化不因XML容器hash改变误判为正文变化。
