# 排错

先显式alembic upgrade head到p801_0004，再使用 `clinical-agent ingest ... --update-existing`。没有该标志仍只基础幂等，不更新旧文献。新状态updated/metadata_updated是实际发布，不代表医学结论正确。

storage_conflict可能是来源身份不一致、重建策略变化或试图重放旧历史版本；不能自动改写身份。storage_unavailable检查隔离数据库和迁移。历史load_version包含向量与本地快照URI，勿直接暴露为公开报告。

源文件必须保留；PDF内容变化默认视为新身份，不能用文件名覆盖。dry_run只接受已编码PreparedIngestion的内部publish方法；没有调度、游标、自动重建或完整UpdateRequest入口，不能排查不存在的命令。

P8-02的update_busy表示同批正在运行；batch_scope_conflict表示原batch与集合/顺序/根目录/窗口不匹配，应使用新batch而非覆盖游标。当前新脚本完整支持免编码dry-run，与P8-01内部PreparedIngestion计划方法不同。原来“没有游标/调度命令”的描述仅指P8-01时点。

## P8-03排错

解析失败先核对JSON字段、UUID、URI和SHA256；脚本只返回错误类型，接口错误码可在专用环境通过直接调用定位。stale_status表示有人已变更，先inspect，核对依据后再提交新事件，不能盲重试。event_conflict表示同事件ID用了不同载荷；native_identity_conflict表示试图冒用原生PMID或PDF hash。conflicted需人工核对全部候选，当前无自动裁决/撤销接口。撤稿在在线分支仍出现属于本次仅本地治理的范围限制；不能将在线查询结果当已经过本地状态门禁。

## 收尾排错

在线batch绑定查询、日期和staging根；改变范围必须新ID。来源文件与冻结内容不同会失败，先检查根目录和文件来源，不盲目覆盖。重建未通过工程检查不能activate；source_changed说明stage后知识库有变化，使用新UUID重建。模型加载或编码超时应记录实际失败，确认机器资源后串行复验，不修改超时结果为通过。真实E5与默认测试同时执行可能争用资源；不要把被中止的回归算完成。具体首次失败和重跑记录见阶段验收。
