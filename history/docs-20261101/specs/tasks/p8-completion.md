# Phase8收尾：P8-04在线窗口与P8-05显式重建

2026-10-28实施前冻结；用户授权完成Phase8，按P8-04、P8-05顺序实现，统一末尾集中验收，不进入Phase9。保留P8-F01–05/T01–06及所有历史记录。

## P8-04

输入OnlineUpdateRequest(batch_id,query,date_from,date_to,staging_root,dry_run)，日期为显式包含端点edat窗口，最多20篇、31天；使用现有PubMedClient，partial/truncated/缺条目一律拒绝完成和推进。操作者缩小窗口后使用新batch；不承诺edat能捕捉所有历史记录更正。新窗口重叠靠PMID版本幂等，不自动计划下一窗口。

持久online_update_batches保存范围hash、官方查询结果/文献快照及状态；首次完整发现先冻结，恢复使用冻结快照而非重新分页。只对有摘要记录创建只读可校验XML文件，复用UpdateService、PostgresUpdateLedger及原入库/版本发布。元数据条目保留并标记metadata_only，无虚构摘要。dry-run可联网读，不写文件/数据库/游标、不装配模型。输出查询追溯、各条状态、cursor、evaluation_status；固定基线回归仍仅工程回放，不伪标医学质量。

官方明确Retracted Publication/RetractionIn或撤回/关注声明/更正标签转为带官方URL/hash/原文依据的治理事件；只针对已存在文档登记，不自动清除历史阻断状态。状态与新正文在同一发布事务提交，状态写失败正文也回滚且不推进该条游标；常规在线检索读取精确已知PMID状态，阻断在线副本，查询不可用时不静默绕过。快照和路径均受显式staging_root约束；同batch改变查询/日期/根拒绝。

## P8-05

输入RebuildRequest(run_id,policy)，读取完整当前知识库最多100文档，保留原source/身份；复用chunk_source、现有本地Embedder和PreparedIngestion校验。支持既定E5重编码/同模型分块策略变化，不支持更换未经验证的模型或维度；未知profile提前拒绝。本任务不重新设计固定模型/数据库架构。

独立rebuild_runs持久化隔离的待发布PreparedIngestion集合及原集合签名。编码与质量评估在写事务外；评估passed才可显式activate。失败/not_accepted/not_run不能切换。激活时锁documents表防并发插入/更新，重查全部文档及原签名，变化则拒绝；单事务归档旧版本、替换所有活跃片段/元数据、切换版本和运行状态。重放激活幂等；新chunk按run/version重命名，强制重编码不覆盖旧证据。普通发布仍拒绝策略混写；维护脚本以--max-tokens显式选择匹配重建后的预算，默认512不变。保留治理状态，失败旧索引可用。

提供scripts/sync_pubmed.py、scripts/rebuild_knowledge.py显式入口；无默认后台任务/业务迁移/模型下载/付费调用。重建stage/activate分开，dry-run只读清单不加载模型。

## 数据与异常

p804_0007新增online_update_batches(batch_id,scope_hash,snapshot,result)、rebuild_runs(run_id,status,source_signature,payload,evaluation_status)。JSONB仅内部保存来源和向量，脚本公开输出摘要，禁止输出全量向量/本地原文载荷。上限、无结果、元数据缺失、网络中断、冻结落盘失败、发布后游标失败、并发变更、编码/评估/激活失败分别保留状态，不当完成。

## 先写测试与集中验收

unit/test_phase8_completion.py：请求边界、truncated/partial零发布零写、dry-run无模型/文件/游标；重建未知模型拒绝。integration/test_phase8_completion.py：MockTransport官方格式→真实PG冻结恢复/重放/重叠幂等/来源状态；真实数据库stage不影响旧检索，拒绝未通过评价、失败回滚、并发源变更拒绝、重放和旧片段回读、迁移上下链。

复用本轮唯一Docker容器/卷helper，联合原Phase8及存储/检索测试，末尾离线受影响回归、Ruff/mypy/format、六份教材补充和Demo。官方小查询冒烟仅现有无需付费网络范围尝试，不能成功时记未验证。医学人工不由模型代替；Phase7旧缺口保留。当前未测试/待验收，不以规划标功能通过。
