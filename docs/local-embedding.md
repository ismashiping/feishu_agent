# 本地 Embedding 使用与验证（P1-05）

本页说明P1-05的Python适配器；当前已有复用该适配器的[入库/问答CLI](cli.md)及[API](api.md)。详细范围见 [SPEC](specs/tasks/p1-05-local-embedding.md)，验收结果见 [开发记录](development-plan.md)。共享 Conda 环境无需修改。

## 环境与固定模型

在项目根目录、既有 Python 3.12 隔离环境中执行：

```powershell
$env:UV_CACHE_DIR=Join-Path (Get-Location) '.research-cache/uv'
$env:UV_PYTHON_INSTALL_DIR=Join-Path (Get-Location) '.tools/python'
.venv/Scripts/python.exe -m uv sync --locked --extra ml --system-certs
```

本页sync命令仅安装模型模块所需ml extra，uv会移除未选中的extras；当前全量开发/测试请按[README](../README.md)同时选择ml/db/rag/api。

ML 是可选 extra：sentence-transformers 6.2.0、transformers 5.21.0、torch 2.14.1；Windows/Linux 的锁定 CPU 构建为 2.14.1+cpu。其他依赖由 uv.lock 锁定。普通 `uv sync --locked` 不安装 ML；加载模型是显式操作，doctor/模块导入不会自动加载模型。

当前模型为 intfloat/multilingual-e5-base，固定提交 d128750597153bb5987e10b1c3493a34e5a4502a。CPU、512 token（包括前缀及特殊 token）、768 维、L2 归一化。医学检索效果尚未评估；通过向量形状和长度测试不代表医学适用性得到证明。

## 准备本地资产

以下是本次实际采用的官方 HTTPS 下载方式。磁盘需容纳约 1.11 GB 权重及 tokenizer/依赖；models/ 已被 Git 忽略。不要关闭 TLS 证书验证，也不要下载/执行远程 Python 模型代码。

```powershell
$ErrorActionPreference='Stop'
$revision='d128750597153bb5987e10b1c3493a34e5a4502a'
$target="models/multilingual-e5-base/$revision"
$files=@('config.json','modules.json','sentence_bert_config.json',
    '1_Pooling/config.json','tokenizer.json','tokenizer_config.json',
    'special_tokens_map.json','sentencepiece.bpe.model','model.safetensors')
New-Item -ItemType Directory "$target/1_Pooling" -Force | Out-Null
foreach ($file in $files) {
    Invoke-WebRequest "https://huggingface.co/intfloat/multilingual-e5-base/resolve/$revision/$file" `
        -OutFile "$target/$file" -TimeoutSec 900
}
```

完成下载后生成 manifest；已有快照不要边推理边改写。下面核验权重与官方 SHA256 一致，并记录其余固定提交文件的本地 SHA256。manifest 是本地完整性记录，不是签名认证；模型/配置更新应创建新版本并重新验收。

```powershell
@'
import hashlib
from pathlib import Path
from clinical_agent.adapters.embedding import (
    MODEL_ID, REVISION, SNAPSHOT_FILES, WEIGHT_HASH, SnapshotManifest,
)
root = Path("models/multilingual-e5-base") / REVISION
files = {}
for name in sorted(SNAPSHOT_FILES):
    with (root / name).open("rb") as stream:
        files[name] = hashlib.file_digest(stream, "sha256").hexdigest()
assert files["model.safetensors"] == WEIGHT_HASH
manifest = SnapshotManifest(model_id=MODEL_ID, revision=REVISION, files=files)
(root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
print("Snapshot complete; official weight checksum matches")
'@ | .venv/Scripts/python.exe -
```

运行时校验 manifest 的身份、文件集合、路径、总大小和 SHA256，强制 local_files_only=True、trust_remote_code=False、CPU 和 safetensors。缺失/不匹配会失败，不自动转为在线下载。

## Python 调用

```python
from pathlib import Path
from clinical_agent.adapters.embedding import (
    REVISION, LocalModelConfig, load_local_embedder,
)
from clinical_agent.domain.chunking import ChunkingPolicy, chunk_source

embedder = load_local_embedder(LocalModelConfig(
    snapshot_dir=Path("models/multilingual-e5-base") / REVISION,
))
query = embedder.embed_query("What are the limitations of this evidence?")
assert len(query.vector) == 768

# parsed 为 parse_pdf / parse_pubmed_xml 返回的单篇解析结果。
# chunk_id_factory 为调用者提供的 UUID 工厂，不能依靠本适配器实现入库幂等。
# source = chunk_source(parsed, tokenizer=embedder.count_tokens,
#     profile=embedder.tokenizer_profile, policy=ChunkingPolicy(),
#     chunk_id_factory=chunk_id_factory)
# encoded = embedder.embed_chunks(source)
```

不要给 embed_query 的业务文本手动加 query: 前缀，也不要给证据正文加 passage: 前缀；适配器负责添加一次。count_tokens 接受已经准备好的完整输入，可直接交给 chunk_source。编码前会复核计数、身份和预算，超长查询拒绝。输出保留原片段 ID、定位和来源，补充 EmbeddingInfo；不会修改输入对象。

模型实例由调用者持有并复用，单实例串行访问。默认锁等待 1 秒，最多 128 片段、每批 8 条、操作协作预算 60 秒、加载 300 秒；EmbeddingLimits 可显式调整。超时不能抢占当前一次模型调用，不应在 async 请求处理器中直接阻塞执行；后续应用入口应配置有界执行和进程级资源限制。

## 验证与排错

默认测试不加载真实模型；真实验收必须显式运行：

```powershell
$env:OMP_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.venv/Scripts/python.exe -m pytest tests/integration/test_embedding_real.py -m external -q `
    --basetemp=.artifacts/p1-05-manual-real-temp
```

选择未使用过的 basetemp，保留历史运行证据。测试要求已准备快照及 ML extra，缺失会失败；测试内阻止网络连接，核验 512/513 token 边界、模型实际输入 mask 长度、来源回建、向量维度/范数、重复稳定性、耗时及峰值工作集。结果写入 .artifacts/p1-05-20261027-01/real-model-result.json，复验前保留已有结果。

embedding_snapshot_invalid：检查全部九份文件、manifest 和 hash；embedding_load_failed：检查 ML extra、CPU wheel 与本机运行库，业务异常已隐藏第三方原文；embedding_token_limit：缩短查询或用相同 tokenizer 重新分块；embedding_token_count_mismatch / identity_mismatch：不要混用其他模型的分块结果；embedding_busy：等待在途操作结束；embedding_timeout：根据测量调整预算，而非忽略超时后接收部分向量。
