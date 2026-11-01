# P1-02 SPEC：PDF 文本层解析与逐页来源单元

版本：0.2；日期：2026-10-26；关联 P1-T02；状态：本任务验收完成，Phase 1 整体未完成。依赖 [P1-01](p1-01-literature-contracts.md)、[MVP](../01-mvp.md)，实际执行见 [开发记录](../../development-plan.md)。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

将受控本地 PDF 的同一份内存字节快照转为逐页来源文本和已有 LiteratureDocument，保留页号、规范化版本、来源 URI/哈希和获取范围。验证未来证据可从单页文本回建；不把文字提取解释为全文阅读或医学真实性核验。

## 2. 功能需求

新增 domain.models 的 PdfSourceUnit、ParsedPdf；新增 adapters/pdf.py 的 parse_pdf、PdfMetadataOverrides、PdfParseLimits、PdfParseError 和必要 adapters/__init__.py。底层采用已核实的 pypdf==6.21.2（Python>=3.9，2026-10-21 发布，BSD-3-Clause），只引入基础运行依赖，不引入 crypto/OCR/image extras 或第二套解析器。[PyPI](https://pypi.org/project/pypdf/6.21.2/)、[提取局限](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)。

## 3. 非功能需求

单次只读一个文件，不改写/删除原文件。读取至多 max_file_bytes+1 字节，哈希与解析使用同一份 bytes；文件流、BytesIO 和 reader 在成功/失败时关闭。导入模块不读取文件/配置、不联网/建线程。默认 strict=True，不主动提供密码/调用 decrypt，也不采用解密后内容。已核对库源码：pypdf 初始化本身会尝试空密码；只要 reader 识别为加密，应用仍拒绝，包括空密码文件。库因不支持的加密/缺少算法依赖而初始化失败则按 pdf_invalid 拒绝，不承诺识别所有加密算法的精确原因。

限制在调用参数 PdfParseLimits 中显式可注入：max_file_bytes=20 MiB、max_pages=200、max_page_stream_bytes=10 MiB、max_total_characters=1,000,000、max_seconds=30.0，均严格正值、时间有限。总字符数包括最终聚合 text 中每个页间的两个 LF，不只统计单页内容。计时在读取后及各页提取前后检查。内容流解码后才可检查其长度；同步库的一次解码/提取和文件 I/O 不能被本函数强行中断，这些是协作预算，不是硬内存/时间沙箱。对外接收不可信大文件前需另行做进程隔离与实际资源验收，本任务不引入进程池。

## 4. 本任务不实现

无 OCR、表格/复杂阅读顺序保证、跨页分块、Embedding、数据库、持久化文件快照、XML、RAG、API/飞书或新增 CLI。无文本可能是扫描件/空白/无法解码字体，不能仅凭无文本断言扫描；明确拒绝并说明扫描件需另做 OCR。不读取 CreationDate 猜出版日期，也不从正文猜 DOI/PMID/期刊。

## 5. 输入输出契约

`parse_pdf(path: Path, *, allowed_root: Path, document_id: UUID, ingestion_time: datetime, metadata: PdfMetadataOverrides | None = None, limits: PdfParseLimits | None = None) -> ParsedPdf`。

allowed_root 必填并解析为真实目录；path.resolve(strict=True) 必须为其内部普通文件，拒绝越界/指向外部的符号链接。该检查不是对文件系统并发改名攻击的完整沙箱。扩展名不作为内容证明，由 pypdf 严格检查格式。document_id/ingestion_time 由调用方提供，不自动造身份/时间；无 .env/网络配置。

PdfMetadataOverrides 的 title、authors、publication_date、journal、doi、pmid、source_url 均可选；None 表示未覆盖。title 优先人工值→PDF /Title 非空值→文件 stem，并记录 manual/document_metadata/filename；authors 人工列表优先（[] 可清空），否则 /Author 作为一个原始署名字符串，不按逗号/分号猜拆作者。其余未知元数据保持 null、日期 precision=unknown；只允许明确人工提供出版日期等信息，不把 PDF 创建/修改时间冒充出版日期。

成功返回文献 content_scope=extracted_text、source_type=pdf、source_uri=原路径的 file URI、content_hash=本次原始 bytes SHA256；text 按每页文本用两个 LF 拼接，abstract=null、evidence_chunks=[]，尚未分块/编码。原路径不是持久化快照，后续入库仍需保存受控文件快照和来源单元。

## 6. 数据模型

- PdfSourceUnit：page 为从 1 开始严格正整数；text 为字符串，允许空页；normalization_version 固定 pdf-text-v1。适配器规范化仅 CRLF/CR→LF、移除 NUL，不 strip、不折叠空白、不去页眉、不合并断词、不改变 Unicode；DTO 拒绝仍含 CR/NUL 的假规范化文本，定位是此文本的 Unicode 码点右开区间。
- ParsedPdf：document 为 P1-01 LiteratureDocument、source_units 为按页顺序列表、page_count 为严格正整数；parser_name 固定 pypdf、parser_version 必填。要求页号连续 1..page_count、列表长度一致、至少一页非空白、document 为 extracted_text PDF 且聚合 text 对应、未带证据块。
- `ParsedPdf.validate_chunk(chunk: EvidenceChunk) -> None` 校验传入片段的文献 UUID、来源五字段、pdf_page kind、页存在、end<=len(page.text) 和该页切片==chunk.text；不跨页、不使用聚合偏移。不修改输入，不创建新片段；失败为固定原因 ValueError。
- PdfMetadataOverrides/PdfParseLimits 使用现有 DTO 的额外字段拒绝/安全错误策略；已知元数据按 P1-01 校验。声明参数/输出 DTO 的 ValidationError 不冒充 PDF 读取失败。

## 7. 核心流程

校验根目录/真实文件路径 → 有界读取一次并关闭原文件 → 检查文件字节限制/计时 → SHA256 → BytesIO + closing(PdfReader(strict=True)) → 拒绝加密/零页/页数超限 → 逐页检查计时、解码内容流预算、extract_text → 规范化/字符总量检查/保留空页 → 拒绝整份无文本 → 读取最小元数据 → 关闭 reader/stream → 构造已有文献与 ParsedPdf。

## 8. 异常与边界场景

PdfParseError 是单个扁平边界异常，只暴露 code，不拼接文件路径、原文或库错误消息；code 为 pdf_path_invalid、pdf_io_error、pdf_too_large、pdf_encrypted、pdf_invalid、pdf_no_pages、pdf_no_text、pdf_page_limit、pdf_stream_limit、pdf_text_limit、pdf_timeout。PdfReadError 等库/解码失败映射 pdf_invalid，I/O 失败映射 pdf_io_error；不捕获 MemoryError/KeyboardInterrupt 等进程级中断。参数配置/未知程序异常保留类型，不把所有错误都解释成损坏 PDF。不记录正文或原始异常；pypdf 仍用成熟组件的严格读取，不修改全局第三方 logger 配置。

混合空页必须保留页号；全空白和图像-only 样例均拒绝 no_text，明确无 OCR；单页提取失败不返回“部分成功”文献。文件路径与正文只在内部 DTO/本地测试可见，公开错误不带它们。

## 9. 测试清单

| 分组 | 必需场景 |
| --- | --- |
| P1-02-T01 | 真实 pypdf 合成的多页、空页、元数据、无元数据、手工覆盖、原始字节 hash、JSON 往返 |
| P1-02-T02 | 单页单元、连续页号/规范化/聚合一致性；有效片段回建，错页/越界/切片/来源/归属拒绝 |
| P1-02-T03 | 损坏/零字节/零页/全空/图像-only/加密（含空密码）明确拒绝；CreationDate 不当出版日期 |
| P1-02-T04 | 外部/缺失/目录路径、文件大小、页数、解码流、总字符预算；fake clock 确认提取后的超时也拒绝 |
| P1-02-T05 | 成功和提取异常时 reader/内存流/源文件关闭；库错误消息不透出；快照 hash 与解析 bytes 相同 |
| 回归 | 真实 PDF 解析与局部替身分别说明；已有 DTO/CLI 回归、导入安全、lint/format/mypy、锁/安装检查 |

用 PdfWriter/现有成熟库创建小型人工文本/空白/图像/加密 PDF，无真实论文或版权原文。允许少量 PDF 内容流语法作为合成 fixture，不作为运行时解析实现。计时/库故障用可替换调用和 monkeypatch，不以替身冒充真实 PDF 提取。测试收集成功后观察因缺目标能力导致 RED；安装/网络失败单列为前置失败。

## 10. 可执行验收标准

先准备并锁定已核实的 pypdf 依赖，然后项目解释器执行 `-I -m pytest tests/unit/test_pdf_contracts.py tests/integration/test_pdf.py -q`，记录目标缺失 RED；最小实现后原命令 GREEN；完整 unit/integration 回归和 Ruff/格式/mypy、uv lock --check、pip check 通过。若修复现有契约缺陷先补独立失败测试。记录版本/文件/命令/结果/局限，已有测试不能删除或弱化。

## 11. 依赖与完成定义

完成须有逐页文本、来源/hash/标题来源、真实合成 PDF 场景和错误预算/关闭测试、可回建证据、回归与文档记录。Phase 1 尚未完成。下一任务规划为 P1-03“本地 PubMed XML 解析与元数据映射”，本次不开始。
