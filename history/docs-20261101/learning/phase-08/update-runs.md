# P8-02 本地更新运行与恢复

本任务新增本地集合批次，不是在线PubMed增量抓取。manifest使用相对路径，batch_id绑定允许根目录、文件顺序、格式及窗口标记；不能用同batch_id悄悄改集合。示例见update-manifest.json，替换为自己已有的PDF/XML文件。

项目根一次性计划：

```powershell
.venv/Scripts/python.exe -I scripts/update_literature.py --manifest docs/learning/phase-08/update-manifest.json --allowed-root <已有文献目录> --dry-run
```

dry-run只加载数据库读取配置与原解析器，不打开Embedding模型、不编码、不写快照/游标/运行记录。仍需现有数据库配置和迁移p802_0005。正式发布去掉--dry-run并传--model-dir、--snapshot-dir；新文档/版本复用原入库和VersionedPostgresStore。

程序运行顺序：取得同batch advisory lock → 读取持久cursor → 按文件发布 → 每文件短事务保存cursor和逐项结果 → 失败停止或完成 → 可选固定回归 → 保存最终运行。锁连接使用AUTOCOMMIT，编码不跨数据库写事务。文档已提交但游标未写时，重启原batch重放，版本幂等避免新增重复版本。每文件若有部分成功，不越过该文件。

已完成批次再次运行是noop；显式--rescan重新检查同集合。添加--runs 3 --interval-seconds 3600可手动启动3轮有界进程内调度，后续轮自动rescan；最多100轮，间隔范围受限。不会创建系统任务或聊天自动化，同批并发调用拒绝。失败时停止，不做无限重试。

--evaluate只运行已有最小基线的离线复算，结果输出本次唯一.artifacts/update-evaluations目录。passed/not_accepted/failed/not_run独立记录，当前基线退出1必须not_accepted；不能叫医学质量通过，评估失败不回滚已提交文档。此回归只验证冻结证据，不验证新入库文献医学效果，也不是完整Phase9。

更新返回run_id、范围hash、窗口标记、cursor_before/after、created/unchanged/updated/metadata_updated等计数及逐项结果。原始XML字节hash变化不等于正文改变，按原摘要/正文和来源单元判断逻辑内容，元数据差异保留新版本。

数据更新可能发生在已处理文件中；恢复只继续失败位置，需rescan或下轮调度重新检查之前的文件。来源集合/顺序改变必须新batch_id，不能以跳过失败推进游标。在线同步、跨来源别名、模型重建仍未实现。
