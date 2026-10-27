# P1-04：来源单元分块与 tokenizer 长度契约

状态：2026-10-27 已按本任务范围验收；38 目标用例、318 全量回归通过。先冻结 SPEC 再测试/实现，执行证据见 [开发记录](../../development-plan.md)。依赖 P1-01–03；仅本任务，不代表 Phase 1 验收。

阅读时点：本文保留本任务契约与验收范围，正文的“尚未/下一任务”属于该任务时点；当前仓库进度及规划统一见[开发计划](../../development-plan.md#phase-1-任务进度)。

## 1. 背景及目标

把已经验证的 ParsedPdf / ParsedPubmedArticle 转为可回建证据片段，长度由注入的模型 tokenizer 计数决定，不用字符数估算 token。

## 2. 功能需求

片段不跨 PDF 页或摘要节。Unicode 码点右开区间，PDF 相对页、摘要相对全文。原文切片不 decode、不归一化、不添加前缀；来源快照完全继承。空白单元跳过，非空白字符全部覆盖且不重叠。每个片段开始前跳过空白；片段内部和已接纳的末尾空白保留。

按 Unicode 码点递增候选右端点，每次计数完整 `document_prefix + 原文切片`。首次超预算时使用此前最后一个合格候选；不假设 tokenizer 的长度单调，不承诺全局最长或句子边界。首个非空白码点不能容纳时明确失败，不截断、不丢弃。默认不重叠，版本 source-unit-v1。

## 3. 非功能需求

无网络、模型加载或 I/O。显式输入字符、tokenizer 调用次数和输出片段数量上限；失败不返回部分结果。限制是工作量限制，单次回调不能被抢占；不宣称硬超时。ID 工厂不能依靠本模块实现跨次幂等。

## 4. 本任务不实现

不安装/加载模型 tokenizer，不实现 tokenizer 算法、Embedding、检索、存储、句子语义切分、重叠或 API。真实模型 tokenizer 加载、固定 revision 与实际长度一致性由下一 Embedding 适配任务验收；本任务的计数替身不是模型验证。

## 5. 输入输出契约

`chunk_source(parsed, *, tokenizer, profile, policy, chunk_id_factory)`，返回 ChunkingResult。tokenizer 是 `Callable[[str], int]`，须计数完整传入字符串，包含模型特殊 token，不 padding、不截断；不得仅返回模型已截断长度。prefix 只用于计数，必须与后续编码使用的一致。调用者提供真实的模型/tokenizer 不可变版本身份，当前 DTO 只校验非空，不核验远程登记。

ID 工厂接收从 1 开始的文档内片段序号，返回 UUID；重复/非 UUID 拒绝，工厂异常原样传播。无自动随机 ID。parsed/profile/policy 在入口重验证，不能信任可变 DTO 已经验证过。输入不修改。

## 6. 数据模型

TokenizerProfile：model_id、model_revision、tokenizer_revision 非空；document_prefix 原样字符串；model_max_tokens 正整数。

ChunkingPolicy：max_tokens 默认 512（不得大于 profile 的模型上限）；max_input_characters 默认 1,000,000；max_chunk_characters 默认 2,048；max_tokenizer_calls 默认 100,000；max_chunks 默认 10,000，均严格正整数。chunking_version 固定 source-unit-v1。单块字符上限额外限制候选探测成本，即使 tokenizer 把很长字符串压成极少 token，也不扫描无限增长的候选；它不是 token 估算规则。

ChunkingResult 保存 profile、policy、chunks。每项 TokenizedChunk 保存 evidence（EvidenceChunk）及正整数 token_count。evidence.embedding_info=null，不伪造已编码身份。结果校验预算、重复 ID 和片段数量；完整来源切片由 parsed.validate_chunk 再验证。

## 7. 核心业务流程

重验证输入 → 核对字符/模型预算 → 顺序扫描来源单元 → 计数候选切片 → 生成唯一 ID 与完整定位 → 原解析结果回建校验 → 返回携带版本/预算/计数的批次。PDF 空页仍保持原页号；摘要单位 start 加入全摘要偏移。

## 8. 异常与边界场景

参数错误使用 Pydantic ValidationError；业务异常 ChunkingError 仅含固定 code：chunk_model_limit、chunk_input_limit、chunk_call_limit、chunk_count_limit、chunk_tokenizer_invalid、chunk_tokenizer_failed、chunk_unfit_character、chunk_id_invalid。bool/负数/非整数计数拒绝；回调异常转换为固定错误，不输出原始文本或异常字符串。资源限制先于对应额外操作。空白单元不调用 tokenizer/ID 工厂。非单调 tokenizer 允许保守短块，但每个输出必须实测满足预算。

## 9. 测试用例清单

- 严格配置、空身份、超模型预算、非法计数及异常隐私。
- 中英文/emoji/组合字符、无空格长句、恰好预算、前缀与特殊 token、非单调计数。
- 多页含空页、摘要多节和全摘要偏移、每块回建、来源继承、原输入不变。
- 重复/错误 ID、字符/调用/数量上限、变异 DTO 重验证、JSON 往返。
- 真实合成 PDF/XML 解析后分块集成；tokenizer 使用显式替身。
- 新模块导入无副作用，全量 pytest、Ruff、mypy、正式锁文件一致。

## 10. 可执行验收标准

先运行 `.venv/Scripts/python.exe -m pytest tests/unit/test_chunking.py tests/integration/test_chunking.py -q --basetemp=.artifacts/p1-04-20261027-01/<本次独立目录>` 确认目标能力缺失 RED，再实现并获得 GREEN；保留 .artifacts/p1-04-20261027-01/ 输出。每次使用新临时目录，不清理历史证据。全量 pytest、ruff check/format、mypy src、uv lock --check --offline 和 uv pip check 均通过。输入输出真实回建，但不声称已验证实际模型或完成离线入库。

## 11. 阶段依赖及完成定义（DoD）

目标及回归测试通过、长度预算包含 prefix/特殊 token 的责任明确、来源可回建、进度和实际命令更新后本任务完成。新增生产文件仅 domain/chunking.py；测试新增两个文件并扩展导入审计。更新 MVP/架构/技术选型的当前实现状态，不增加未来模块。下一任务为本地 Embedding 与真实 tokenizer 适配，待用户指定后执行。

依据：2026-10-27 核查 [E5 作者模型卡](https://huggingface.co/intfloat/multilingual-e5-base) 的前缀/长度要求与 [Transformers tokenizer 官方文档](https://huggingface.co/docs/transformers/main_classes/tokenizer) 的特殊 token、padding/truncation API。当前只冻结边界契约，不引入尚未实测或锁定的 ML 依赖。
