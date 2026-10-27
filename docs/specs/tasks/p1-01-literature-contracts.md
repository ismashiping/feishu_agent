# P1-01 SPEC：文献与证据 DTO、来源和定位契约

版本：0.2；日期：2026-10-26；关联 P1-T01；状态：本任务验收完成（Phase 1 整体未完成）。依赖 [Phase 0 验收](../../phase0-acceptance.md)、[总体语义](../00-project-overview.md)、[MVP](../01-mvp.md)，实际 RED/GREEN 与边界修复见 [开发记录](../../development-plan.md)。

## 1. 背景及目标

在解析、入库和检索之前固定内部文献/证据的数据边界：未知元数据不补造，日期不丢精度，片段保留来源快照与可定位位置，摘要不得冒充全文。DTO 是输入结构和内部一致性校验，不证明来源、DOI/PMID、作者或结论真实有效。

## 2. 功能需求

在 clinical_agent/domain/models.py 公开 PublicationDate、SourceMetadata、EvidenceLocation、EmbeddingInfo、EvidenceChunk、LiteratureDocument 六个 Pydantic DTO。domain/__init__.py 仅包说明。统一拒绝额外字段，错误文本隐藏输入；正常 constructor/model_validate/model_validate_json 校验，JSON 往返保留未知值、日期精度、Unicode 证据和定位。调用方不得用 model_construct、未验证更新或原地修改绕过边界；重新接收修改数据时应重验。

## 3. 非功能需求

只依赖标准库和既有 Pydantic 2.14.1；无文件读取、网络、配置读取、SDK、ORM 或模型推理。复用成熟字段/模型验证，不自建校验框架。document_id/chunk_id 由调用方提供 UUID，不自动造身份、时间、哈希或引用元数据；它们不能替代外部 PMID。

## 4. 本任务不实现

不实现 PDF/XML 解析、文件存在性校验、分块/tokenizer、向量推理/存储、数据库约束、检索/回答/claims/引用报告 DTO、外部元数据核验或新的 CLI。空 evidence_chunks 允许表示尚未分块；embedding_info=null 表示尚未编码，不能据此宣称已可检索。后续编码/持久化任务再要求准备完成。

## 5. 输入输出契约

输入为明确字段的映射或 JSON；成功输出类型化 DTO，失败为 Pydantic ValidationError。模型错误使用固定原因，不拼接原文。默认 errors() 仍可能包含输入，结构化诊断须 include_input=False；不要把完整 DTO/错误原样放入日志或公开报告，source_uri 是内部追溯字段。

元数据非空字符串去首尾空白，作者含团体名按原列表顺序保留；证据/文档 abstract/text 只拒绝空白，**保留原字符和空白**，避免改变定位。日期原始 raw 也保留原文本；有值时不可全空白。数值字段要求严格整数，拒绝 bool/数字字符串；normalized 要求真实 bool。

## 6. 数据模型

| DTO/字段 | 契约 |
| --- | --- |
| PublicationDate | precision=unknown/year/month/day 必填；raw、year/month/day 缺省为 null。unknown 时所有组件为 null，可保留无法解析的 raw；year/month/day 精度分别只允许对应已知组件，已知精度要求 raw。year 1–9999，month 1–12，day 真实日历合法，含闰年；不解析 raw 猜日期，不补 1 月/1 日 |
| SourceMetadata | source_type=pdf/pubmed；source_url 必填但可 null，非空仅 http(s) 且不得含用户名/密码；source_uri 必填 file URI，指向离线快照，DTO 不读取文件；content_hash 为调用方计算的原始来源快照 SHA256，小写 64 位 hex；content_scope=abstract/extracted_text/full_text。当前 PubMed 离线内容只接受 abstract；PDF 可显式记录获取范围 |
| EvidenceLocation | kind=pdf_page/abstract；page 缺省 null，pdf_page 必须为从 1 开始的整数，abstract 不得有 page；section 可空或非空字符串。start/end 必填，从 0 开始、右开区间，start>=0、end>start；PDF 相对规范化的单页文本，abstract 相对整段规范化摘要，不是按 section 重新计数；单位为 Python Unicode 码点，不是字节/token |
| EmbeddingInfo | model_id、model_revision、tokenizer_revision、chunking_version 非空；dimension 严格正整数，normalized 严格 bool；字段全部必填，不包含向量值，无默认模型/维度 |
| EvidenceChunk | chunk_id/document_id 为 UUID；text 非空且原样保留；location、source_metadata 必填；embedding_info 必填但可 null。end-start 必须等于 len(text)；来源为 pdf/pubmed 时 location.kind 必须对应 pdf_page/abstract |
| LiteratureDocument | 包含 SourceMetadata 的五个平铺字段，及 document_id、title、title_origin、authors、publication_date、journal、doi、pmid、abstract、text、ingestion_time、evidence_chunks。除已说明的日期/定位缺省字段外均必填；journal/doi/pmid/abstract/text 可 null，作者未知传 []，日期未知用 precision=unknown 对象 |
| title_origin | manual/document_metadata/filename/pubmed_metadata，显式记录，不把文件名说成核实标题；pubmed_metadata 只配 pubmed 来源，document_metadata/filename 只配 pdf；manual 可用于两者 |
| 标识和时间 | doi 有值时仅按非空字符串保留，不声称格式/登记核验；pmid 有值时为不带前导零的正整数 ASCII 字符串，不从 DOI 等推导；pubmed 文档必须有 pmid，符合本地 XML 无 PMID 拒收规则。ingestion_time 接收显式带时区的 ISO 日期时间字符串或 datetime 对象，统一为 UTC；拒绝无时区及 epoch（包括数值、数字字符串和 bytes），不自动取当前时间 |

文献内容与跨对象约束：

- scope=abstract 要求 abstract 非空、text=null；其他 scope 要求 text 非空，abstract 可空。不允许仅元数据、没有可用内容的文献通过。
- 文献中每个片段的 document_id 必须相同，chunk_id 不重复；source_metadata 五字段必须与文献一致，包括来源快照哈希和范围。
- PubMed 片段 start/end 不得超摘要边界，摘要切片必须逐字符等于片段 text。PDF 文献的 text 是聚合文本，当前 DTO 没有页单元，不能证明页数/页内边界/切片真实性；由 P1-02/P1 分块任务负责，本任务只校验页号、区间与长度。
- 同一文献中非空 embedding_info 必须相同，不混模型身份、版本、维度、规范化和分块版本；未编码片段仍可为 null。DTO 不核验声明与实际模型输出是否一致。

## 7. 核心流程与模块边界

调用方提供来源快照身份/元数据/可用文本 → Pydantic 字段校验 → 日期/定位局部关系 → 片段范围/来源关系 → 文献内容、引用关系和摘要切片校验 → JSON 序列化。LiteratureDocument 复用 SourceMetadata 字段以保持顶层字段符合总体 SPEC；片段嵌入同一小型 SourceMetadata，不复制作者/标题，也不引入任意 payload。

## 8. 异常与边界场景

未知日期、季节/区间 raw 不自动猜；非法闰日、组件与精度冲突；空标题/作者/正文、未声明字段、坏 URI/携带凭据的 URL、错误 hash/PMID/时区；零/负/布尔页号、反向/越界区间、Unicode 偏移；摘要填入 text、篡改 chunk 来源/范围/归属、重复 chunk ID、嵌入信息混用均须明确拒绝。URL 解析只检验结构，不请求网络，也不证明它是公网可达来源。

## 9. 测试清单

| 分组 | 场景 |
| --- | --- |
| P1-01-T01 | 四种日期精度、未知 raw/缺失；非法日历/类型/多余组件，原始值不变 |
| P1-01-T02 | PDF/PubMed 合法来源、未知 URL；坏 URL/URI/hash/scope，凭据拒绝 |
| P1-01-T03 | 单页/摘要定位、Unicode/空白保留；页号、区间、字符数和来源 kind 不一致 |
| P1-01-T04 | EmbeddingInfo 的完整性、严格类型、维度/版本与不同身份混用 |
| P1-01-T05 | 完整文献/JSON 往返、未知字段保留 null/[]、UTC 归一化、标题来源；缺字段/空白/摘要伪全文/缺内容/坏标识/无时区拒绝 |
| P1-01-T06 | 外文档片段、重复 ID、来源/哈希/范围变化、摘要越界/切片不符拒绝；空片段与未编码状态允许 |
| 导入与回归 | 扩展隔离导入到 domain/domain.models；所有既有测试、lint/格式/mypy、锁检查通过 |

样例全部为合成文本/标识/URI，不使用真实医学结论、凭据或实际文件读取。目标 import 放测试函数内部，确保缺实现时能收集并出现真实 RED。

## 10. 可执行验收标准

项目解释器依次执行 `-I -m pytest tests/unit/test_literature_models.py -q`，先记录目标缺失 RED，再最小实现、同命令 GREEN；然后完整 unit/integration 回归及 Ruff/格式/mypy。保留命令、退出码、实际计数和未验证内容。正式声明/锁与共享环境不变。导入副作用检查扩展到当前新增模块；不得删除/弱化原测试。

## 11. 依赖及 DoD

P1-01 完成须有冻结契约、真实 RED/GREEN、正常/错误/序列化及交叉关系测试、回归/质量通过和进度记录。Phase 1 尚需 P1-F01–07 与真实服务验收及学习材料，不能因 DTO 完成而标阶段完成。下一最小任务规划为 P1-02“PDF 文本层解析与逐页来源单元”，须先细化 SPEC/核实依赖；本次不开始。
