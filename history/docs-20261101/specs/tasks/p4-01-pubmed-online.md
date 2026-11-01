# P4-01：PubMed 在线检索核心链路

版本 1.0；日期 2026-10-28；实施前冻结、现已实施并完成核心范围集中验收。覆盖 P4-F01–05/P4-T01–06。用户明确进入 Phase 4，允许复用 Phase 3 已交付技术基线；Phase 3 真实样例/人工标注缺口继续保留，不标已验收。

## 1. 目标与范围

已有 XML 离线映射、PICO 和共享 ResearchService。新增 HTTPX 官方 ESearch/EFetch、本次来源快照、在线证据及 local/online/hybrid 入口。无自动入库、关键词融合、神经重排、全库同步或新依赖/Schema。

## 2. 官方依据

[NCBI 配额](https://support.nlm.nih.gov/kbArticle/?pn=KA-05510)：无 key 默认最多 3 rps，有 key 3–10 rps。本实现即使有 key 仍最多 3 rps。[NLM E-utilities 接口说明](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html)提供固定端点及 tool/email 参数；[参数参考](https://www.ncbi.nlm.nih.gov/books/NBK25499/)定义 PubMed、日期/排序/分页。官方 Bookshelf 网页本次触发校验页，配额以可读取 NLM 官方页面为准。tool 默认 clinical-literature-agent；email/API key 可显式配置，不伪造 email；部署者负责按官方要求登记真实联系信息。不发送邮件。

## 3. 输入

PubMedOptions(query=null, date_from/date_to=null, date_field=pdat|edat 默认 pdat, sort=relevance|pub_date 默认 relevance, max_results=10 范围 1–20)。日期必须成对且不倒置。query 严格非空、最多 4000 字符。显式 query 优先；否则使用 QueryPlan.original_question 或原问题原样交给官方翻译，不自造 MeSH 或自动删掉否定/剂量条件，也不承诺已把每项医学约束变为字段过滤。原问题与实际 query/translation 均追溯。

QuestionRequest/QuestionBody 增加 scope=local|online|hybrid，pubmed 可空，仅 online/hybrid 可指定。CLI 增加 --scope、--pubmed-query、--date-from/--date-to、--date-field、--sort、--max-results。local 维持原路径；在线暂不支持 document_ids 或非零 min_similarity，显式拒绝；source/content 过滤仍适用。本地日期过滤不在现有契约，date_* 明确只过滤 PubMed 分支。

## 4. 输出

PubMedSearchResult 保留 query_sent、query_translation、total_count、requested_limit/returned_count、truncated、fetched_at、records、warnings、status=complete|partial、missing_pmids。SearchProvenance 保留脱敏查询/时间/日期字段/排序/计数、warnings/status/缺失 PMID；不含 key/email/完整请求 URL。

PubMedRecord 保存 PMID、可信标题/作者/期刊/日期/DOI、结构化摘要及 publication_types、来源更正/撤回标记、content_scope=abstract|metadata_only、规范化 XML 快照和 SHA256；不把缺摘要当解析失败或全文。规范化版本 pubmed-record-xml-v1，以安全解析后序列化的记录为快照，非原始 HTTP 字节。每次快照保留在本次结果对象，不自动持久化；回答保留实际使用来源的 snapshot_xml、文本/定位、hash 和检索记录，可重新计算记录哈希；未使用条目和整个原始 HTTP 响应不会自动持久化。

## 5. HTTP 与配额

固定 HTTPS eutils.ncbi.nlm.nih.gov/entrez/eutils/，POST form 避免 key 在 URL；不重定向、不继承代理、不自动 HTTP 重试。全进程共用串行请求门，至少 0.34 秒间隔，锁等待与暂停计入总期限。独立进程/主机及同 IP 其他工具配额不协调，未配置外部协调时仅支持一个启用在线检索的进程实例；不宣称分布式配额保障。

默认总期限 30 秒，每次读取最多 10 秒，连接/写/池最多 5 秒，实际不超剩余预算。单响应最多 5 MiB，XML 复用深度/节点/实体保护。搜索页/获取批均 10，最多 20 结果；每个 HTTP 请求最多重试一次，仅 429/5xx；所有操作总请求最多 8 次。Retry-After 支持秒与 HTTP 日期，最多等待 3 秒且须在剩余期限内，否则明确失败/partial；不缩短服务端要求后提前请求。

## 6. 搜索一致性与失败

ESearch JSON 校验 count/idlist；PMID 必须为正数字且去重，分页 retstart 按服务返回页推进，上限有界。首个搜索失败抛 pubmed_failed/timeout/invalid；后续页失败保留已有 ID 并标 partial。EFetch 返回非请求 PMID、重复/冲突身份或非法记录拒绝该批；缺请求 PMID/批失败保留已获取记录并标 partial/missing_pmids。失败从不伪装完整零结果，完全获取失败不能生成证据不足回答。官方 error/warning 使用受控代码，不把远端错误体/凭据写日志。

## 7. 来源与证据复用

复用 pubmed_xml 字段映射（新增允许 metadata_only 的在线入口，不放宽离线无摘要拒绝）。在线 URI 是真实公开 PubMed URL，扩展 SourceMetadata 接受该 HTTPS URI，不伪造本地文件。document/chunk UUID 从实际 PMID+快照 hash/摘要区间派生。在线 hit score_type=pubmed_rank，score 仅为 1/rank 排序显示，embedding_info=null；不假装计算向量或将得分称医学可靠性。

## 8. 问答接入与混合来源

共享图在规划后按 scope 路由。local 沿用向量路径；online 不调用本地向量检索；hybrid 顺序获取两边，各取约半数、剩余容量补齐，按 PMID/document/chunk 去重，最终本地在前、在线在后，分别保留通道 score_type。不是跨通道分数相加，不实现 Phase 5。任一分支完全故障不静默降级；在线 partial 但有可用摘要允许带明确局限回答，无可用记录的 partial 直接错误。metadata_only 可出现在检索记录但不能作为 claims 证据。

## 9. 测试设计

先写 tests/unit/test_pubmed_online.py 和 tests/integration/test_pubmed_online.py：请求参数/日期/排序、分页/去重、批身份/缺失/partial、无摘要/混合标签/日期/团体作者、出版类型/撤回、更正/实体防护、超时/429/Retry-After/上限/跨客户端门、零结果不混失败、真实图 online/hybrid 和引用门禁、CLI/API/飞书范围及凭据不泄漏。更新 Phase 1 仅 local scope 的旧断言以保持新契约，不删旧来源/一致性断言。

真实 external 仅一个小查询（aspirin[Title] AND randomized controlled trial[Publication Type]，max_results=2）以及 EFetch（正常共两请求），无需 LLM/E5/数据库或付费 API。不固定文献数量/标题，检查实际 PMID/URL/元数据/快照/摘要范围一致。网络不可用如实失败，不以浏览器结果替代工具验收。

## 10. 集中验收命令

核心实现与学习材料后，用正式 .venv/Scripts/python.exe 执行 `-I -m pytest tests/unit/test_pubmed_online.py tests/integration/test_pubmed_online.py -q`、`-I -m pytest tests -q`，以及 `-I -m pytest tests/integration/test_pubmed_online.py -m external -q` 单独真实接口。Ruff/format、mypy src、离线 Demo、链接/围栏/diff 检查分列。记录实际数，未执行不得标通过。

## 11. 完成标准

核心契约/图/入口/真实官方冒烟、离线回归和质量、六份学习文档及 Demo 齐备后按 Phase 4 范围验收。保留 Phase 1/3 人工/模型缺口和网络限制，不将 PubMed 真实性等同医学结论支持度。停止于 Phase 4，不进入 Phase 5。
