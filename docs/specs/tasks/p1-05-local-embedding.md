# P1-05：本地 Embedding 与真实 tokenizer 适配

状态：2026-10-27 按本任务范围验收完成。先冻结 SPEC 再测试/实现；61 目标单元、381 默认回归和 1 项真实模型测试通过，执行证据见 [开发记录](../../development-plan.md)。依赖 P1-01–04；仅本任务，Phase 1 尚未验收。

## 1. 背景及目标

连接已经实现的来源分块和本地模型，生成数量、维度、身份和数值有效性经过验证的文档/查询向量。真实 tokenizer 与实际编码输入使用相同前缀，超限必须拒绝，不能依赖框架静默截断。

## 2. 功能需求

固定模型 intfloat/multilingual-e5-base，提交 d128750597153bb5987e10b1c3493a34e5a4502a，模型/tokenizer 同一 revision。当前只支持 CPU、768 维、L2 归一化、512 token；文档 passage: 空格、查询 query: 空格。直接使用 sentence-transformers 推理，不实现池化或 tokenizer 算法。

提供显式本地加载、count_tokens、tokenizer_profile、embed_chunks、embed_query。count_tokens 接收已经加前缀的字符串，包含特殊 token，禁止截断/padding。编码前重验所有片段、profile 一致性、重算 token_count 和预算；已编码片段拒绝。不修改输入；片段 ID、原文、来源、定位不变，只给返回副本补充 EmbeddingInfo。

## 3. 非功能需求

模型仅显式加载一次，由调用者复用；导入模块无模型/网络/线程/配置副作用。单实例锁串行 tokenizer/编码，锁等待默认 1 秒，饱和返回固定错误，不创建线程池或后台任务。每请求最多 128 片段、总正文 1,000,000 码点，query 最多 8,192 码点，编码 batch_size=8。操作协作预算默认 60 秒（等待锁、计数、批次前后检查），加载预算 300 秒；不宣称可以抢占一次模型加载/推理或硬内存隔离。

真实验收：CPU，单批 2 条/长文本分块，总推理 120 秒内、模型加载 300 秒内，进程峰值工作集不超过 6 GiB；记录实际资源，不把小样本当生产性能结论。部署外层硬资源隔离待运行入口任务。

## 4. 本任务不实现

不实现数据库、检索排序、API/CLI 命令扩展、飞书、RAG、模型微调、效果评估平台、GPU、量化或自动模型下载服务。下载是人工准备/本次验收步骤，运行时只允许本地文件。模型医学适用性仍待固定评估集检验。

## 5. 输入输出契约

load_local_embedder(config) 校验 snapshot_dir/manifest.json 后加载；配置显式传入，不读取 .env。支持 loader 注入测试边界，核心业务无 sentence-transformers 类型依赖。

LocalEmbedder(backend, limits) 支持替换后端单元测试；后端协议提供 dimension、max_tokens、count_tokens(text)、encode(texts,batch_size)，encode 返回二维 float 列表且已归一化。生产包装器调用官方 encode，明确 prompt=""、normalize_embeddings=True、precision="float32"，文档/查询前缀由本适配器添加，避免重复 prompt。

embed_chunks(ChunkingResult) 返回 list[EmbeddedChunk]；空 chunks 返回 []，不调用编码器。embed_query(非空字符串) 返回 QueryEmbedding。所有向量有限、非零、长度 768、范数误差 <=1e-4；数量严格匹配，不用 zip 静默丢失。查询只允许完整输入，超限拒绝。

query/count_tokens 输入严格为字符串，不把 bytes 自动解码。输入 ValidationError 的文字隐藏 input_value，非法类型/字节也不能回显敏感内容。

## 6. 数据模型

domain/embedding.py：EmbeddedChunk(evidence, vector)、QueryEmbedding(embedding_info, vector)；vector 元素严格浮点且有限，长度与 EmbeddingInfo.dimension 相同，normalized=true 时检验范数。业务 DTO 不导入 ML 框架。

adapters/embedding.py：EmbeddingLimits、LocalModelConfig(snapshot_dir, limits)、SnapshotManifest(model_id, revision, files)。身份使用固定模型/提交 Literal；files 是相对文件名到 SHA256 的完整映射，固定所需文件：config.json、modules.json、sentence_bert_config.json、1_Pooling/config.json、tokenizer.json、tokenizer_config.json、special_tokens_map.json、sentencepiece.bpe.model、model.safetensors。

manifest 最大 64 KiB，总模型文件默认最多 2 GiB；拒绝未知/缺失文件名、路径逃逸、非普通文件和 hash 不符。权重 SHA256 额外必须为官方仓库公布的 a18a44fad1d0b46ded15928144138cff1135d5cc8233bdd90be5f18822de09a7。tokenizer_revision 使用同一固定模型提交，具体文件校验值保存在 manifest。manifest 是本地完整性记录，不是独立签名认证。

## 7. 核心业务流程

准备固定提交的官方资产及 manifest → 显式校验资产/本地加载 → 核对实际维度/最大长度 → 生成 tokenizer_profile → chunk_source 注入 count_tokens → embed_chunks 预检全部片段 → 限量批次编码 → 验证数量/维度/有限性/范数 → 补齐身份返回。任何失败无部分返回。query 使用同一实例、同一模型身份和归一化规则。

## 8. 异常与边界场景

参数/DTO 验证错误使用 ValidationError；EmbeddingError.code 为固定码：embedding_snapshot_invalid、embedding_load_failed、embedding_model_mismatch、embedding_busy、embedding_timeout、embedding_input_limit、embedding_identity_mismatch、embedding_token_count_mismatch、embedding_token_limit、embedding_backend_failed、embedding_output_invalid。异常文字不包含原始文献、路径或第三方异常。超长文本拒绝优先于 encode；非有限/空/零/维度/数量错误明确失败。锁在任何异常后释放。

## 9. 测试用例清单

- 严格配置、错误 manifest/缺文件/hash/路径、加载失败与模型形状错误。
- fake 后端验证文档/查询前缀只加一次、特殊 token 计数、超限编码前拒绝、身份/计数篡改、空批次和输入不变。
- 数量不匹配、768 维、NaN/inf/零/非归一化/非浮点、异常隐私、批次顺序。
- 注入时钟验证超时、并发持锁饱和、异常释放、资源限额。
- external：实际固定 E5 本地加载、真实中英文 tokenizer、512/513 边界、来源分块与实际编码 tokenize 一致、查询/文档向量及重复稳定性；阻止网络连接。
- 全量默认测试及导入隔离、Ruff/mypy、uv 正式锁和依赖检查；真实模型结果单独记录。

## 10. 可执行验收标准

先运行 `.venv/Scripts/python.exe -m pytest tests/unit/test_embedding.py -q --basetemp=.artifacts/p1-05-20261027-01/red-temp`，确认因功能缺失失败，再最小实现并通过。全量默认 pytest/ruff/mypy/uv lock --check --offline/uv pip check。ML 依赖放可选 extra ml，CPU torch 显式独立索引，精确直接版本加正式 uv.lock。

真实验收运行 `pytest tests/integration/test_embedding_real.py -m external`，模型前提为固定 models/ 本地快照，ML extra 已装；没有前提时明确失败，不 skip 后宣称验收成功。记录加载/编码耗时、峰值工作集、向量维度/范数、模型/依赖/hash、无网络运行和 tokenizer 长度。真实服务失败不以替身通过结案。

## 11. 阶段依赖及完成定义（DoD）

RED/GREEN、默认回归、真实 CPU 模型/长度验收和文档均完成才能标记本任务完成。若下载或推理受阻，完成不依赖外部的代码/测试并记录阻塞，任务保留未验收。下一任务为持久化模型/迁移与 pgvector 存储，需用户另行指定，不自动进入。

官方依据（2026-10-27）：[模型卡](https://huggingface.co/intfloat/multilingual-e5-base)、[固定权重 SHA256](https://huggingface.co/intfloat/multilingual-e5-base/blob/d128750597153bb5987e10b1c3493a34e5a4502a/model.safetensors)、[SentenceTransformer API](https://sbert.net/docs/package_reference/sentence_transformer/model.html)、[tokenizer API](https://huggingface.co/docs/transformers/main_classes/tokenizer)、[uv CPU 索引](https://docs.astral.sh/uv/guides/integration/pytorch/)。官方 PyPI 元数据保存在 .artifacts/p1-05-20261027-01/，选 sentence-transformers==6.2.0、transformers==5.21.0、torch==2.14.1（CPU 构建），兼容 Python 3.12；实际解析/安装仍须执行。
