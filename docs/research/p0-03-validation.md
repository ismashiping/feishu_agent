# P0-03 技术选型核查约定与执行记录

日期：2026-10-26（Asia/Shanghai）。任务范围：官方文档、包元数据、Python 支持范围、候选依赖的解析核查与技术决策；不实现业务，不修改共享 Conda 环境。

## 输入输出与边界

输入为项目规则、P0-01 环境记录、P0-02 源码分析以及组件官方来源。输出为 `docs/tech-stack.md`、官方包元数据快照、按阶段拆分的候选版本输入与解析记录，以及开发进度更新。

元数据记录包含包名、版本、Requires-Python、依赖声明、发布日期、下载文件名/哈希、官方项目链接；不采集密钥或用户环境变量。候选约束与解析结果只是研究材料，不等同项目安装、最终 uv.lock 或真实服务验证。

无法访问来源则记录失败与未核实项；不凭本机已安装版本填充官方结果。候选解析发生冲突则保留原因、调整后重新验证；不删除需求以掩盖冲突。Python 基线需兼顾 Windows 开发和 Linux 部署，机器学习依赖单独核查。

## 验收场景及 DoD

1. 所选包存在官方 PyPI 发行，记录 Python 要求、近期发布时间与官方文档。
2. 各组件明确职责、引入阶段、选择依据、替代方案与主要风险。
3. Phase 0 保持最小依赖，未来阶段组件只作候选；运行时、测试、ML 依赖区分。
4. 用解析器核查明确的 Python/平台组合，记录命令及结果；不将解析成功当作安装或推理成功。
5. 明确未完成的解释器安装、真实服务集成、模型效果及锁文件落地工作。
6. 文档链接、格式、阶段进度记录一致；本次不进入 P0-04 或 Phase 1。

本任务没有产品功能实现，不产生 pytest RED/GREEN。后续工程骨架必须按独立 SPEC 完成真实 TDD。

## 初始检查

已重读 AGENTS.md.txt、PROJECT.md.txt、开发进度及参考仓库分析，并检查已有文件和 Git 状态。当前无代码、测试和项目依赖声明。

普通沙箱读取 PyPI 时遇到套接字权限错误；按环境规则申请联网执行后，已成功读取 FastAPI 元数据。默认 uv 缓存目录不可写，后续核查使用项目内研究缓存，避免修改共享环境。

## 官方来源核查结果

已读取 Python 发布与生命周期、uv/PyTorch、Pydantic Settings、FastAPI、SQLAlchemy、Alembic、psycopg、pgvector、redis-py、pypdf、PyMuPDF 变更、sentence-transformers、LangGraph、飞书 SDK、HTTPX、NCBI API 概览、Bio.Entrez、pytest 工具与模型作者说明。具体页面链接、版本、职责和替代方案见 [技术选型](../tech-stack.md)。NCBI Books 指南被浏览器校验拦截，未声称读到其内容。

PyPI 查询采用 PowerShell `Invoke-RestMethod -Uri https://pypi.org/pypi/<包名>/json -TimeoutSec 30`，批量获取后保存字段快照。初次批处理中 langgraph、structlog 两个请求遇到 EOF，未取得有效响应；检查发现对应记录与请求身份不符，已按 source 排除无效记录，用 `-ErrorAction Stop` 等效的全局错误偏好和有限重试重新读取这两个包，再校验全部 25 个包身份。最终快照没有保留两条无效数据。实际执行未修改 Conda 内安装包。

指定解释器执行 `python -m uv --cache-dir .research-cache/uv python list --only-installed`，只发现 CPython 3.10.21 和 3.14.7。缓存新增在项目内，并用 `.gitignore` 排除。

## 依赖解析矩阵

实际工具为 `C:\Users\11091\.conda\envs\medical-agent\python.exe -m uv`，版本 0.13.1；输出是研究用精确版本及哈希清单，不是项目正式 uv.lock。全部调用使用 PyPI 官方 simple 索引，CPU 变体还通过 uv 的官方集成使用 PyTorch CPU 索引。

实际命令共同参数如下；group、platform 和输出文件对应下表逐项执行。首项单独执行，后五项通过 foreach 执行并记录 `$LASTEXITCODE`，两项 CPU 探测随后追加。

```powershell
& 'C:\Users\11091\.conda\envs\medical-agent\python.exe' -m uv --cache-dir .research-cache/uv pip compile $inputPath --python-version 3.12 --python-platform $platform --only-binary :all: --no-python-downloads --generate-hashes --index-url https://pypi.org/simple --output-file $outputPath --quiet
# CPU probes add: --torch-backend cpu
```

| group / 输入 | platform | 输出文件（dependencies/ 下） | 包数量 | 退出码 |
| --- | --- | --- | --- | --- |
| phase0.in | x86_64-pc-windows-msvc | phase0-py312-windows.txt | 24 | 0 |
| phase0.in | x86_64-manylinux_2_28 | phase0-py312-linux.txt | 23 | 0 |
| phase1.in | x86_64-pc-windows-msvc | phase1-py312-windows.txt | 74 | 0 |
| phase1.in | x86_64-manylinux_2_28 | phase1-py312-linux.txt | 72 | 0 |
| ml.in | x86_64-pc-windows-msvc | ml-py312-windows.txt | 102 | 0 |
| ml.in | x86_64-manylinux_2_28 | ml-py312-linux.txt | 119 | 0 |
| ml.in + CPU backend | x86_64-pc-windows-msvc | ml-cpu-py312-windows.txt | 102 | 0 |
| ml.in + CPU backend | x86_64-manylinux_2_28 | ml-cpu-py312-linux.txt | 100 | 0 |

机器可读结果：[基础矩阵](dependencies/resolution-results.json)、[CPU 结果](dependencies/cpu-resolution-results.json)。CPU 两份清单均为 `torch==2.14.1+cpu`，无 nvidia-* 依赖。PyPI 默认 Linux ML 清单保留为对照，不用于默认 CPU 安装。CPU 安装时仍需正确配置来源索引，哈希清单不会自动配置安装器的索引。

实际警告：基础 ML 解析输出一条 `>= '2.7'` 被规范化为 `>= 2.7` 的版本说明修正；CPU 索引读取曾触发一次 uv 自动网络重试，最终成功。源码搜索首次把 Windows 文件通配符直接传给 rg 报路径错误，已改成 `rg -g 'ml-py312-*.txt' ... docs/research/dependencies` 完成核查。这些不是应用测试失败，也未通过删除约束掩盖依赖冲突。

## 静态交付检查及验收结论

使用指定 Python 执行一次内联只读检查：

- JSON 解析；25 个规范化包名唯一且与 source URL 匹配；每包有未撤回发行；文件 SHA256 格式正确。
- 两份结果 JSON 共 8 条，均为退出码 0；输出清单存在、版本条目不重复且包含哈希。
- 两份 CPU 输出均为 torch 2.14.1+cpu，且没有 nvidia-* 条目。
- 技术选型、执行记录、进度文档的相对链接目标存在，Markdown 围栏成对。

检查退出码 0，输出 `25 metadata identities, artifact hashes, 8 resolutions and document links: PASS`。随后加强检查，确认所有文档链接、全部直接版本约束及每个传递包的哈希均通过。交付前对 18 个本次文件执行 `git -c core.autocrlf=false diff --no-index --check`：首次发现生成 JSON 的 CRLF 被按尾随空白报告，已将生成研究材料统一为 UTF-8/LF，复验输出 `Whitespace diagnostics: 0 / 18 files`。这些是材料静态验证，不是产品测试。

P0-03 技术研究验收完成，Phase 0 未完成。未运行 pytest，没有 RED/GREEN、应用代码、候选包安装、模型权重下载或真实数据库/Redis/飞书/LLM/PubMed 功能调用。尚待 P0-07 创建独立 Python 环境、正式声明及锁文件；服务和模型验证按所属阶段推进。LLM 供应商、模型 revision、容器镜像 digest 是已明确保留的后续决策门槛。
