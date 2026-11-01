# P8-03 来源别名与状态治理

2026-10-28，实施前冻结。对应P8-F01/F02、P8-T03/T05；仅本地显式治理，不实现在线增量、重建或Phase9。

## 输入输出与范围

显式AliasClaim(namespace=pmid/doi/pdf_sha256, value, document_id, evidence)登记外部标识到本地稳定文档的关联。规范化PMID、DOI前缀/大小写和PDF摘要；依据包括URI、快照SHA256、原文和操作者。输入依据为人工提交的断言，系统不冒充在线核验。无自动猜测、物理归并、重写chunk或别名驱动入库。相同键多个文档归属返回conflicted及全部候选，不选择赢家；可检查记录，冲突人工裁决/撤销接口留后续，不隐式覆盖。相同claim幂等。原生PubMed PMID/PDF hash归属不允许被错误claim冒用；DOI允许冲突登记。

StatusChange(event_id, document_id, status, expected_event_id, evidence)显式登记normal/corrected/retracted/withdrawn/expression_of_concern。首次expected为空，后续必须匹配当前事件；同event同载荷重放幂等，不同载荷冲突。只有显式新事件可解除旧状态；无记录表示unreviewed而非已核验正常。每次保留不可变事件，当前状态投影与事件同事务。更正记录可检索并附依据；撤回/撤稿/关注声明在本地vector/keyword/hybrid候选阶段统一排除，并输出策略提示。状态不改版本/原文/快照，更新正文不得重置状态，不自动沿别名传播。

提供仓库脚本scripts/govern_sources.py：JSON单条claim/status、resolve、inspect。无模型、联网、自动调度；读取已有数据库配置，不加载.env。依据有大小边界，不输出底层异常或密钥。

## 数据与异常

source_aliases复合唯一键namespace/value/document_id、依据JSON；source_status_events以event UUID为主键存完整请求；source_states每文档当前状态/事件/依据。FK禁止孤立记录，事务锁串行化同alias和同文档变更；版本发布复用原document行锁。非法标识/缺依据、未知文档、原生标识不匹配、过期状态修改、事件ID复用均失败，不改变现状。迁移p803_0006下接p802_0005。

## 先写测试与集中验收

- 单元tests/unit/test_source_governance.py：标识规范化/非法输入、状态与证据边界。
- 真实PG tests/integration/test_source_governance.py：重复/并发claim与跨文档冲突、原生身份保护；事件幂等/过期更新/并发CAS；三检索模式阻断与更正信息；更新后状态不丢、历史版本原ID可读、非法请求无写；迁移回退再升级。
- 使用现有隔离Docker PG验证helper，唯一容器/卷清理，不碰业务库。受影响联合含原postgres/ingestion/retrieval/hybrid/versions/update_runs。离线集中运行新增契约、原检索/版本/映射/命令回归；Ruff/format/mypy及脚本help。
- 不需要新的医学推断或付费调用；合成fixture只能证明工程门禁，真实撤稿元数据和医学人工判定未验收，不以模型代替。

完成门槛：上述工程测试实际通过、结果和缺口记录、六份现有Phase8教材补充真实调用流程与可运行示例；不标Phase8整体完成。
