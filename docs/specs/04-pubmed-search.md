# SPEC 04：PubMed 官方实时检索

版本：0.1；状态：未来阶段概要，开发前细化；未实现。

## 1. 背景及目标

通过官方 E-utilities 检索并获取 PubMed 实时元数据，为已有本地知识补充在线来源。结果有时间边界与检索记录，不把一次查询称为覆盖全部最新医学研究。技术依据沿用 [技术选型](../tech-stack.md)，进入阶段前重核官方接口规则。

## 2. 功能需求

- P4-F01：把原问题/QueryPlan 转为可记录查询，支持日期范围、排序、结果上限和分页。
- P4-F02：ESearch 获取 PMID，EFetch 分批获取标题、作者、期刊、日期、摘要、DOI 及可获得的出版类型。
- P4-F03：保留结构化摘要、内嵌标签文本、团体作者、日期精度和 PMID 对应关系；无摘要仍可保留元数据，但不能伪造证据块。
- P4-F04：按当前官方要求配置 tool/email/key、限流、超时和有界重试；在线失败与零结果明确区分。
- P4-F05：问答可选择 local/online/hybrid 范围，记录来源与检索时间；来源不自动永久写入本地库。

## 3. 非功能需求

HTTPX 客户端可注入、显式连接/读写/池超时及总期限。连接重试和 HTTP 状态重试不叠加成无限次数，429 遵守有界 Retry-After；多工作者按同一 NCBI 配额协调，不各自宣称独享全额。密钥不能进入 query 日志或来源 URL。

## 4. 本阶段不实现的内容

不抓取付费全文、不把 PubMed 摘要标为 PMC 全文、不自动同步全库、不承诺系统性综述级检全率。Phase 1 的本地 XML 导入不等于本阶段在线检索；查询结果长期入库/更新策略留 Phase 8。

## 5. 输入输出契约

PubMedSearchRequest 包含 query 或 QueryPlan、可选 date_from/date_to、date_field、sort、max_results；日期倒置及非法上限拒绝。具体枚举、默认值及最大量须在首任务冻结，不能把服务端隐含默认当契约。

PubMedSearchResult 包含 query_sent、query_translation（若官方返回）、total_count、requested_limit、returned_count、truncated、fetched_at、records、warnings。每条 PubMedRecord 包含可信 PMID、标题/作者/期刊/日期/DOI/摘要、publication_types、source_url、content_scope=abstract/metadata_only。部分批次失败须标记 partial，不以 records=[] 代表“未找到证据”。

## 6. 数据模型

沿用 PublicationDate 和来源语义。SearchProvenance 保存接口、查询参数（脱敏）、检索时间、日期字段、排序与截断状态。在线 EvidenceChunk 与本地片段采用同一证据契约，赋独立内部标识并保存当次来源快照及哈希，生命周期足够支撑任务结果追溯；默认不触发知识库导入。

## 7. 核心业务流程

校验计划 → 构造官方查询 → 限流 ESearch → 有界分页与 PMID 去重 → EFetch 分批 → 解析并核对所请求 PMID → 返回可追溯记录 → 对有文本的记录构造证据 → 接入既有回答流程。外部元数据不能从 LLM 补 PMID/DOI。

零结果可作为成功搜索的结果；429/5xx、XML 错误、官方 error/warning、分页截断和部分获取失败分别保留。缺摘要文献不作为已阅读全文的证据，也不无声从检索计数中消失。

## 8. 异常与边界场景

网络/解析超时、429/5xx、HTTP 200 但错误体、无摘要、缺 DOI、日期字符串、团体作者、标签嵌套、重复/缺失/非请求 PMID、超大结果集、并发限流、查询翻译、部分批次失败和撤回/更正标志。线上获取失败不导致已有本地知识丢失。

## 9. 测试用例清单

- P4-T01：MockTransport 检查端点、参数、日期/排序及脱敏。
- P4-T02：ESearch/EFetch fixtures：嵌套标签、日期精度、无摘要、团体作者、缺 DOI。
- P4-T03：分页、上限、重复及缺失 PMID、部分失败计数。
- P4-T04：Fake clock 下限流、Retry-After、超时预算和重试耗尽。
- P4-T05：零结果与服务失败语义；在线/本地证据范围渲染。
- P4-T06：少量真实官方请求冒烟，保存查询/时间/计数，验证实际 PMID 链接与返回元数据。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k pubmed`，离线 fixtures 不访问网络；真实请求单独 external 标记并遵守当期官方配额。

用固定响应验证请求数不超过预算、返回数量不超过请求上限、PMID 不重复且来源 URL 来自实际记录；故障返回失败/partial 而不是正常空结果。真实冒烟只断言字段/来源一致及接口可用，不断言持续变化的实时文献数量或某研究结论。当前未执行。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 3 已验收。首任务细化 API 契约、官方配额、期限和分页规则；全部核心场景、真实接口冒烟、异步及本地 RAG 回归、配置与限制文档、docs/learning/phase-04/ 齐备才完成。Phase 5 再做关键词与向量融合。
