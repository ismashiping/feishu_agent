# P1-03 SPEC：本地 PubMed XML 解析与元数据映射

版本：0.2；制定：2026-10-26，验收：2026-10-27；关联 P1-T03；状态：本任务验收完成，Phase 1 整体未完成。依赖 [文献契约](p1-01-literature-contracts.md)、[MVP](../01-mvp.md)，实际过程见 [开发记录](../../development-plan.md)。

## 1. 背景及目标

安全读取本地 PubmedArticleSet，映射元数据、结构化摘要与定位，逐条区分 parsed/rejected，不访问 PubMed API。只处理 PubmedArticle，明确拒绝书籍/删除指令等其他顶层条目；不是 NLM 全 DTD 验证器或全量基线更新器。

## 2. 功能需求

新增 adapters/pubmed_xml.py 及必要来源 DTO：AbstractSourceUnit、ParsedPubmedArticle、PubmedXmlEntry、PubmedXmlBatch。保留每个顶层条目的顺序/错误，合法条目生成已有 LiteratureDocument。新增精确依赖 defusedxml==0.7.1：复用标准库树 API并显式禁止自定义实体和外部实体，不编写 XML 安全解析器、不全局 monkeypatch。

官方依据：[NLM 2026 说明](https://www.nlm.nih.gov/pubs/techbull/jf26/jf26_PubMed_2026_BaselineRelease.html) 确认仍用 pubmed_250101.dtd；已取得 [官方 DTD](https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd) 核对字段。选择依据见 [Python XML 安全文档](https://docs.python.org/3.12/library/xml.html)、[defusedxml 0.7.1](https://pypi.org/project/defusedxml/0.7.1/)。该稳定版发布于 2021-03-08，PSFL、纯 Python，Requires-Python 排除旧 3.0–3.4；发行较久，不声称近期活跃或仅凭声明证明兼容，需当前 Python 3.12 实测。替代 lxml 增加原生依赖，Biopython Entrez 当前无在线消费且可能需要 DTD 配置，本任务不额外引入。

## 3. 非功能需求

只从显式 allowed_root 内解析后的普通文件读取一次至多 max_file_bytes+1 bytes，文件关闭后解析同一内存快照并计算 SHA256。保留本地 file URI，不持久化快照，不读取 .env，不联网或下载 DTD。允许正常 DOCTYPE 声明，但 forbid_entities=True/forbid_external=True，不展开自定义实体、外部资源或 XInclude。支持 UTF-8/UTF-16 和 XML 内置/数值字符引用；不支持依赖 DTD 自定义实体的文件。

PubmedXmlLimits：max_file_bytes=10 MiB、max_records=1000（所有顶层条目）、max_depth=64、max_nodes=100000、max_abstract_characters=1000000（每篇，含分隔符）、max_seconds=30.0；均正值，整数严格、时间有限。树解析在事件间检查预算，文本限制逐条拒绝；语法/安全/文件预算失败整体抛错，不返回部分结果。单次库调用/本地 I/O 不能强制中断，非硬时间/内存沙箱，不支持压缩文件或大规模基线导入。

## 4. 本任务不实现

无 E-utilities、外部 PMID/DOI 核验、全文获取、分块/tokenizer/Embedding、入库、去重数据库、更新删除、RAG/报告、新 CLI 或新的通用解析框架。XML 中出现的 PMID/DOI 是来源声明，不代表实际注册已核实；source_url=null，不凭标识造已访问链接。生成 evidence_chunks=[]，不冒充已编码/可检索。

## 5. 输入输出契约

`parse_pubmed_xml(path: Path, *, allowed_root: Path, ingestion_time: datetime, document_id_factory: Callable[[str], UUID], limits: PubmedXmlLimits | None = None) -> PubmedXmlBatch`。

调用方提供带时区 datetime 与纯 ID 工厂。先完成 XML 语法/安全/结构预算检查，再按记录映射；只有有效、非重复 PMID 条目才调用工厂。工厂异常/非法 UUID 和错误调用参数保留异常，不解释为文献被拒绝，不自动生成 ID 或当前时间。空 PubmedArticleSet 返回空批次；非该无命名空间根节点整体拒绝。顶层未知条目逐项 rejected，嵌套未知非消费字段忽略，不声称完整验证 DTD。

## 6. 数据模型与映射

| 字段 | 规则 |
| --- | --- |
| PMID | MedlineCitation/PMID 必须唯一且为正整数 ASCII 字符串；不从 PubmedData 补造。ArticleIdList 中显式/DTD 默认 IdType=pubmed 的非空值若与其冲突则拒绝；已 parsed 的 PMID 再出现拒绝后项，非跨文件/数据库幂等 |
| 标题/期刊 | Article/ArticleTitle 必须非空；journal 取 Journal/Title，缺失可用 ISOAbbreviation，否则 null；title_origin=pubmed_metadata，不由文件名补标题 |
| 作者 | 原顺序保留；CollectiveName 或 ForeName（缺失用 Initials）+LastName+Suffix，不猜缺失字符；LastName 可单独存在。明确 ValidYN=N 的署名忽略，其余缺 CollectiveName/LastName 的作者拒绝该条。无 AuthorList 时 [] |
| DOI | 汇集 PubmedData/ArticleIdList 中 IdType=doi 与 Article/ELocationID 中 EIdType=doi 且 ValidYN!=N 的非空值；完全相同可重复，出现不同值拒绝，不猜哪个是真的，不做 URL/prefix/大小写归一化或登记核验 |
| 日期 | 只取 Journal/JournalIssue/PubDate。Year/Month/Day 支持年、年月、年月日，月份为数字或英文全称/三字母名，真实日历验证；raw 为来源组件按空格组合。MedlineDate/Season/不识别月份保留 raw 且 precision=unknown，不猜日期。缺日期 unknown/raw=null；已知非法组件/冲突结构拒绝。ArticleDate/History/DateCompleted 等不替代期刊日期 |
| 摘要 | 只取 Article/Abstract/AbstractText；itertext 保留混合标签文本顺序和 tail，再将 Unicode 空白折叠为单空格并 strip，版本 pubmed-xml-text-v1；空节忽略，无非空节则拒绝。Label/NlmCategory 分别保留，不插入正文；各节以两个 LF 拼接为 document.abstract，text=null、scope=abstract |
| 来源 | 所有条目共享本次 XML 原始 bytes 的 hash/file URI；单篇外部身份另保留 PMID。source_url=null、source_type=pubmed、ingestion_time 归 UTC，不将原路径当作持久化快照 |

- AbstractSourceUnit：index 从 1 开始连续，label/category 可 null，text 非空规范化字符串，start/end 为在整段摘要中的 Unicode 码点右开区间；end-start=len(text)，首段 start=0，之后 start=前段 end+2。
- ParsedPubmedArticle：document 和 source_units，必须为未分块的 abstract PubMed 文献且摘要拼接/区间一致；validate_chunk 要求相同文献/来源、abstract 定位、切片相等且在一个节内；section 非空时须匹配该节 label。
- PubmedXmlEntry：index 严格正整数；status=parsed/rejected，article/error_code 互斥且必填可空，错误码只用固定值。
- PubmedXmlBatch：source 为已有 SourceMetadata（pubmed/abstract）、entries 顺序连续；parsed 文献来源五字段一致，PMID/文献 UUID 各不重复；parser_name=defusedxml，parser_version 必填。全 rejected 仍返回真实逐项结果，不假造文献。

## 7. 核心流程

验证调用时间与路径 → 有界 bytes 快照 → 安全 iterparse 检查根、深度/节点/顶层数量/协作时间 → 语法全部成功 → 各顶层记录识别 → 校验 PMID/标题/作者/日期/DOI/摘要 → 同批已成功 PMID 判重 → 调 ID 工厂 → 构造已有文献与摘要节 → 返回批次。工厂与映射业务不做任何持久化动作。

## 8. 异常与边界场景

PubmedXmlError 为扁平 file 级异常，str 仅固定 code：xml_path_invalid、xml_io_error、xml_too_large、xml_invalid、xml_unsafe、xml_root_invalid、xml_record_limit、xml_depth_limit、xml_node_limit、xml_timeout。条目 rejected 的固定 code：pubmed_unsupported_record、pubmed_invalid_pmid、pubmed_pmid_conflict、pubmed_duplicate_pmid、pubmed_missing_title、pubmed_no_abstract、pubmed_invalid_author、pubmed_invalid_date、pubmed_doi_conflict、pubmed_text_limit。错误不带路径、原文或库消息；安全/预算失败不降级普通无文献结果。

只有来源记录的已定义映射失败逐项拒绝；未知程序错误、ID 工厂错误不得广泛捕获为“坏文献”。不读无关本地文件，不触发 DTD URL；截断尾部不返回前面已解析文献。错误结构与 DTO 保持不记录正文和原始输入的现有策略。

## 9. 测试清单

| 分组 | 必需场景 |
| --- | --- |
| P1-03-T01 | 真实库解析合成多篇/Unicode/内嵌标签、结构化摘要与空节、个人/团体作者、DOI 双来源、未知字段、JSON 往返 |
| P1-03-T02 | 年/月/日、闰日、英文月份、MedlineDate/Season/未知月份/缺日期、非法日期；历史/创建日期不冒充出版日期 |
| P1-03-T03 | 缺/坏/冲突/同批重复 PMID、缺标题/摘要、坏作者、DOI 冲突与 unsupported 条目逐项拒绝，合法条目继续 |
| P1-03-T04 | 语法截断、错根、正常 DOCTYPE 不联网、自定义/外部/UTF-16 实体拒绝；无文件泄漏，XXE 不展开 |
| P1-03-T05 | 文件/根/路径/大小/节点/深度/记录/文本/计时边界；同一快照解析/哈希、资源关闭、回调错误不吞掉 |
| P1-03-T06 | 摘要节区间/拼接/规范化与批次状态/来源/身份一致，证据从正确节回建，越界/跨节/标签不符拒绝；全量回归/导入安全 |

全部用例为小型合成 XML，不下载实际医学文献；安全解析为真实 defusedxml，网络/时钟/故障仅局部替身。目标 import 在测试函数内，收集必须成功后缺能力 RED；依赖前置失败单列。

## 10. 可执行验收标准

先锁定/安装已核实 defusedxml；项目解释器执行 `-I -m pytest tests/unit/test_pubmed_contracts.py tests/integration/test_pubmed_xml.py -q`，先真实 RED，再最小实现、同命令 GREEN，必要缺陷补失败测试后修复。完整 unit/integration、Ruff/格式/mypy、锁/安装一致性通过；保留实际命令、计数、失败与未验证范围。不得删减已有测试；仅在第三方无类型标记的确切 import 处局部隔离类型，不全局忽略。

## 11. 完成定义与阶段依赖

P1-03 须交付离线字段/摘要定位、逐项结果、安全与预算验证、真实库测试/回归和文档。Phase 1 未完成，不提前生成阶段完成材料。下一任务只规划 P1-04“基于来源单元的分块与 tokenizer 长度契约”，须另行细化模型/tokenizer 与失败测试；本次不开始。
