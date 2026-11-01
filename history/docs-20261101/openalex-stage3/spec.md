# 第三阶段冻结SPEC：OpenAlex开放全文RAG（2026-10-29）

用户明确授权在第二阶段医学验收仍开放的情况下进入第三阶段；保留其重复载体、当前性与人工签署缺口，不改称通过。本阶段只接入已筛选论文的合法全文、解析、缓存、向量索引与问题级段落召回，不升级第四阶段综合写作、不新增Agent、不重新发现文献。

## 契约与依赖

复用FulltextService、HTTPX、pypdf、defusedxml、LlamaIndex SentenceSplitter、现有E5与PostgreSQL/pgvector。旧PMC/BioC路径和历史引用保持兼容；OpenAlex路径不需要PMID，不调用PubMed发现。官方契约核查：OpenAlex locations含is_oa/pdf_url/landing_page_url/license；PMC OAI-PMH GetRecord metadataPrefix=pmc可合法取得允许再利用的JATS全文。来源：https://help.openalex.org/data/locations/ 、https://pmc.ncbi.nlm.nih.gov/tools/oai 。

输入：已选OpenAlexRecord、问题、检索预算和缓存。输出：原摘要命中保持不变，额外最多2个全文段落，含稳定paper_key、OpenAlex ID、DOI、来源URL、许可、内容hash、解析表示hash、章节/页码/字符位置。character offsets定位清洗后的source_units，不冒称PDF原始字节位置。无法取全文则保留摘要并给出稳定原因。

身份：DOI规范值优先作paper_key，无DOI可保存候选身份但本批次下载不能可靠校验则拒绝全文。PDF必须首页面同时匹配规范题名与DOI；JATS必须article-id DOI及题名匹配，实际正文和许可存在。不能以“文件可打开”代替身份核验。

合法性与安全：只下载明确is_oa且允许CC BY/CC0（含明确版本）的locations。首批仅允许明确的公共出版方/PMC域名；禁止任意主机、IP、凭据URL和非常规端口，重定向逐跳重验，最多2跳。只允许HTTPS，HTTPX trust_env=False。PMC仅走官方OAI，不抓HTML全文。一般OA落地页不爬取；无可直接PDF或PMC结构化来源则明确unsupported。域名白名单限制实际覆盖，不能声称覆盖全部合法OA。

## 最小实现与预算

OpenAlex最多处理2篇、共享最多6个HTTP尝试（含跳转），15秒获取子预算、35秒全文子预算并服从研究总deadline；单响应最多10MiB、PDF最多100页/500000字符、XML最多500000字符，最多128块/篇，300 E5 tokens/块、30重叠，最多8候选段/篇再按向量排名与英文查询词覆盖RRF重排取2。无额外LLM调用。重复页眉页脚只移除至少3页上边缘/下边缘重复的相同文本，不全局删除重复段落。章节按显式标题识别，未识别写UNKNOWN不臆造。参考文献等不进入索引，方法/结果/讨论/局限保留。

缓存使用DOI/OpenAlex稳定paper_key + 解析/模型signature，30天TTL；同内容hash续期复用不重编码，内容改变事务替换整套向量，失败不发布半成品。新增独立OA表迁移，不改旧PMID表和已发布文献。相同DOI只获取一次；第二阶段不同DOI同研究版本问题继续保留，不在本阶段以模糊标题强行合并。

必要异常：许可不明、无OA、主机不支持、跳转越界/超量、HTTP/超时、字节超量、PDF加密/无文本/身份错误、XML畸形/身份错误、无有效正文、缓存位置/身份错误均失败记录并回摘要。内部编程错误不在adapter内吞掉；任务级enrichment已有统一失败记录边界。索引发布必须事务且写入锁。

## 验收设计与fixtures

先写tests/unit/test_oa_fulltext.py再实现，合成PDF/JATS只作工程边界；真实DEMF-Net的OpenAlex元数据复用第二阶段快照，尝试保存PMC11699127官方OAI全文及出版方PDF（可达性与许可分别记录）。真实失败不能写通过，人工医学签署仍待。核心：无PMID、许可/身份/SSRF/重定向、章节与页码、页眉清洗、分块定位、缓存命中零下载/编码、TTL同hash复用、改变内容重建、失败摘要回退、预算、只检索已选文档、引用与来源绑定、SQL迁移与原子回滚。

阶段末命令：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/unit/test_oa_fulltext.py tests/unit/test_fulltext_rag.py -q --basetemp=.pytest_oa_stage3
.\.venv\Scripts\python.exe -X utf8 -m pytest -q --basetemp=.pytest_oa_stage3_regression
.\.venv\Scripts\python.exe -X utf8 -m ruff check src tests
```

真实验证使用隔离临时测试库/容器目录与现有模型；不自动升级运行服务的业务库，不发送飞书。迁移具体SQL由新增Alembic脚本及隔离库验证记录冻结。结束时提供六份学习材料和Demo。若真实网络/模型/数据库无法满足，逐项保留未验收，不因此进入第四阶段。

## 真实来源核查增量

DEMF-Net的已冻结OpenAlex location报告cc-by-nc-nd，不满足本批次CC BY/CC0许可白名单，因此不获取、不作为成功全文样例。改选同批已筛选MRI-MVI论文10.1186/s12880-024-01206-7（PMC10821254，元数据CC BY）；第一次实际响应在许可解析处失败，随后诊断HTTP 429，均保留未通过事实。不得为获取样例而绕过许可或访问限制。

## 集中验收修订与实际依赖

真实XML的许可链接位于license-p/ext-link内，已按JATS实际结构读取。内嵌table-wrap不再用itertext粘成无列标签数字；解析/分块signature升级v2，正文表示hash用于续期判断。真实PDF样例改用冻结候选中的PLOS CC BY文章（仅工程对照，不把其提升为问题直接证据），实际下载2,069,581字节，解析15页。

观测到宽泛发现查询词使背景段挤占具体问题段，重排改为实际问题词、通用科研章节偏好（Methods/Results/Discussion）与向量加权RRF，仍限制8→2段。没有疾病或器官白名单规则。该修订只能证明本次用例和固定测试，不声称跨领域召回率已验证。表格重建与PDF字体完全保真仍未实现。

隔离容器旧镜像缺llama-index，首次真实向量试验失败；从uv.lock提取依赖闭包安装到临时target后继续，不改运行虚拟环境。runtime新增缺依赖检查。完整离线回归1382通过/122未选中后，最后章节重排修复只重跑受影响209项，未伪称最终代码再次全量。业务库未迁移、运行服务未重启。

辅助缓存QA脚本最初用了默认空检索计数，不是新检索事实；原结果保留，脚本已改为加载此前真实OpenAlex检索记录并明确标为回放，来源字段修复不改变生成正文。最终案例以answer-final为准；不把缓存回放算作新在线端到端发现。
