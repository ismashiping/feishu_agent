# 第四阶段：证据覆盖与科研综述质量改造（2026-10-29）

> 2026-10-30续验当前状态：API健康，最终镜像已安装；机器人退出，尚未恢复。宿主HTTPS正常，容器曾DNS解析失败；最后探测飞书/模型域名恢复解析，但OpenAlex仍失败。Docker进一步诊断因自动审批账户额度错误未执行，不是安全性拒绝；没有绕过审批或重启Docker Desktop。下文部署成功记录为各次当时事实，不代表当前机器人运行正常。最终在线比较题返回extraction_failed，保留api-architecture-final；架构修正的内容验证目前仅限真实冻结证据回放。阶段完整验收仍开放。

已按用户要求实施并更新API/飞书机器人：宽主题5–8篇为软覆盖目标，优先利用合法全文，按技术方向综合回答。不是“每次保证8篇/3篇全文”，也不是完整医学质量签署。未进入第五阶段。

## 原因、修改与数据流

实际原因：一篇论文覆盖维度就提前停止；同工作不同DOI重复计数；补检新论文被未筛旧候选占满输入；不合法/不支持的全文来源占用前两篇名额；中文采集问题召回Patients；三段召回仍被旧两段引用契约拒绝；检索trace挤占生成上下文；比较中的单侧原研究被错误排除；输出反复展示内部计数和免责声明。

| 代码位置（src/clinical_agent下，除另有说明） | 当前实现 |
| --- | --- |
| application/openalex.py | 软覆盖触发补检、精确同工作去重、维度覆盖选择；比较先综合检索再分别补查方法；新候选优先筛选；通用分析措辞不作必需研究主题，终点保持 |
| domain/openalex.py | 可选study_role；把文档对象/任务匹配与摘要能否回答每个分析维度分开；原方法论文可支持比较的一侧 |
| application/oa_fulltext.py | 最多3篇实际网络尝试；预检拒绝不占论文名额；16向量候选加最多4章节候选，最多3段；中文采集/架构/结果/局限意图 |
| domain/retrieval.py | OA最多3段与新召回一致，旧PMID保持2段；身份、hash绑定不放宽 |
| application/research.py | evidence_groups/study_role传入生成；大快照/内部trace留审计不进模型；上下文均衡删段，研究总90秒内给生成预留25秒 |
| domain/research.py | 可选section标题、study_role、evidence_groups；32k字符上限；方法归属、实验条件、跨论文综合与单次范围说明 |
| domain/citations.py | 按OpenAlex ID/文档ID/PMID正确记录cited，修复所有OA误标未引用；原引用门禁保留 |
| src/feishu/sender.py | 按技术主题分组、DOI链接、保留实际证据层级；普通输出隐藏候选/截断计数，audit完整保留；不模糊删除研究限制 |
| tests/unit/test_research_quality_v2.py、tests/fixtures/answer_quality/policy.json | 10项控制场景（含集中验收发现的架构遗漏回归）；合成元数据不用于真实论文引用 |
| scripts/oa_quality_check.py、scripts/oa_stage3_e2e.py | 真实模型回放/重新发现、输入与模型原文记录；部署后按案例索引执行HTTP测试 |

```mermaid
flowchart LR
 A[问题约束] --> B[有界OpenAlex检索/补检]
 B --> C[真实摘要筛选与独立工作去重]
 C --> D[维度覆盖选择]
 D --> E[合法全文缓存/获取]
 E --> F[章节和向量证据召回]
 F --> G[按维度组织多论文证据]
 G --> H[单次综述生成]
 H --> I[引用身份门禁]
 I --> J[主题段落与可信参考文献]
```

默认top_k仍5，显式8表示最大选择量。不会因数量目标接纳不相关、过期、错误任务或约束不匹配文献。方法比较的partial method_origin仅在constraints_match=true且明确覆盖请求方法时作为单侧方法参考；保留原partial标签，不伪装成双方法实验。没有疾病白名单或示例论文/年份/指标硬编码。

## 测试与真实运行

Windows虚拟环境，OMP/OpenBLAS/MKL均2线程，Ruff RAYON=1。原始失败与修复分批保留，没有单任务RED/GREEN假记录。

| 执行范围 | 实际结果 |
| --- | --- |
| 首次集中核心 | [4失败/211通过](core.txt)：新测试hit排序构造错误、两个旧契约期望及旧两段排序期望；修正后[215通过](core-final.txt) |
| 完整离线回归 | [1391通过/122未选中/1已知protobuf告警](regression-frozen-final.txt)，190.84秒；后续末轮修订按受影响范围重跑，未冒称最终代码又完整运行 |
| 后续规划/三段契约/角色/context修订 | [139通过](final-contracts.txt)，10.64秒 |
| 最后方法归属提示修订 | [101通过](attribution-tests.txt)，9.55秒；其中策略字符串断言只证明约束存在，不证明模型遵守 |
| 随后架构章节遗漏修复 | [118通过](architecture-tests.txt)，10.97秒；真实来源再生成见architecture-answer.txt，明确为回放，不冒称新发现 |
| Ruff | [通过](ruff-final.txt)，覆盖src/tests及两个运行脚本 |
| 最小学习Demo | [实际执行输出](demo.txt)：MRI与CT的Image acquisition优先于Patients，不联网/不写库 |
| 实际服务 | [镜像及8模块hash](release.json)、[运行核对](runtime.json)；两个容器使用新wheel，无源码挂载/临时PYTHONPATH |

完整命令用项目`.venv/Scripts/python.exe -X utf8`：

```text
-m pytest -q --basetemp=.pytest_openalex_stage4_frozen_final
-m pytest tests/unit/test_research_quality_v2.py tests/unit/test_openalex.py tests/unit/test_citation_report.py tests/unit/test_research.py tests/unit/test_oa_fulltext.py -q --basetemp=.pytest_openalex_stage4_final_contracts
-m pytest tests/unit/test_answer_synthesis.py tests/unit/test_research_quality_v2.py tests/unit/test_citation_report.py tests/unit/test_research.py -q --basetemp=.pytest_openalex_stage4_attribution
-m ruff check src tests scripts/oa_quality_check.py scripts/oa_stage3_e2e.py
```

默认pytest不执行external/database/redis/performance那122项；不能把它们标通过。新增业务逻辑的来源约束、拒绝不匹配、真实位置校验与失败路径均保留。

## 五题与全文正例：已实现不等于全部验收通过

真实模型使用现有运行配置和真实E5；先在API容器独立/tmp源码目录执行，不覆盖应用，再更新镜像。各目录批次完整保存，失败不被成功覆盖：replay-v1使用冻结候选，不是重新发现；live-v1/v2/v3/v4/v5/v6是实际重新发现或受影响题复验。

| 问题 | 真实观测 | 质量边界 |
| --- | --- | --- |
| 肝脏分割最新研究 | 发布后[单题复验](api-overview-recheck/summary.json)：5篇、6条结论、28.297秒；日期均在最近24个月 | 已按方向组织；仍仅摘要。首次发布后请求extraction_timeout/504，5.11秒，保留api-release失败，非一次全通过 |
| 肝脏肿瘤亚区分割 | live-v2：0篇，insufficient_evidence，10.833秒 | 不用整体肿瘤/下游预测凑数；未达到细分主题覆盖目标，不能说领域没有研究 |
| MedSAM与nnU-Net区别 | 发布后api-release：5篇（包含两侧原始方法）、2条全文定位、46.125秒；提示修订后api-attribution-final仍复现归属错误 | 两批均不能算内容验收通过。架构补齐后architecture-answer.txt纠正了该错误；最终发布后结果另记，不覆盖失败 |
| 最近三年MRI预测HCC-MVI | [live-v3](live-v3/summary.json)：6篇、14条结论、37.738秒 | 前轮context_limit与generation_timeout均保留。两篇全文获取可用，但模型最终引用0段全文；不能声称回答已使用这两篇正文 |
| 肝脏肿瘤分割技术瓶颈 | [live-v6](live-v6/summary.json)：1篇、6条结论、28.525秒 | 已消除分析措辞被当作强制主题的问题；仍不足以形成领域瓶颈综述，回答明确单篇摘要范围 |
| 指定2024年MVI论文CT/MRI采集 | 发布后[api-release](api-release/summary.json)：1篇、3条全文定位、31.750秒 | 成功召回CT和MRI两个Image acquisition段；表格未提供，不补造设备型号；保留partial/筛选失败状态 |

真实模型回放第一轮仍机械开头且q6出现citation_invalid（不是放宽门禁解决，而是OA合法三段契约统一）；live-v1/v2保留其他失败。比较题先仅查两方法造成应用比较覆盖变窄，已改为保留综合检索、再分别补查；旧结果也保留。诊断OpenAlex失败时两个小查询返回200，只能说明该次可用，不把之前openalex_failed擦掉。

新查询捕获源码的单题复验命令示例：

```text
docker exec -e PYTHONPATH=/tmp/oa_quality_20261029_4/src -e OMP_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 clinical-agent-e2e-api-1 python /tmp/oa_quality_20261029_4/check.py /tmp/oa_quality_20261029_4 live 3
python scripts/oa_stage3_e2e.py docs/openalex-stage4/api-release http://127.0.0.1:18080 1,3,6
python scripts/oa_stage3_e2e.py docs/openalex-stage4/api-overview-recheck http://127.0.0.1:18080 1
```

临时目录随后随容器重建移除；当前复现应另建目录并按usage准备输入。调用真实LLM会计费。源码运行与发布后HTTP结果分开，不能把临时PYTHONPATH样例当部署。

## 前后对比与资源

- 相比用户最初飞书收到1篇摘要，当前综述复验5篇，按技术方向/比较条件组织，DOI可点击，内部候选计数默认隐藏。对比不是固定同模型响应的因果性能评测。
- 方法比较现可使用两侧原始方法论文加任务比较；指定论文从Patients两段变为两个采集段加一段设计背景。新增每篇3段不等于3篇阅读全文。
- 仍最多两轮/四OpenAlex请求、40候选、最多两次摘要筛选；没有新增业务Agent或独立写作LLM调用。真实检查脚本的诊断封装仅记录输入输出，不用于运行服务。
- 全文三篇实际获取/六HTTP/35秒子预算；研究90秒总预算不增加，生成预留25秒。只读缓存不重编码，模型/解析签名未变化，因此沿用已发布全文向量。
- 单样本延迟见表；缓存、候选和供应商响应不同，不能据此给出性能提升百分比或P95。未采集计费token/金额，不声称成本下降。

## 已部署与未解决

新镜像通过Dockerfile.update复用已验证阶段三锁定依赖、离线重装项目wheel；具体源hash和当前镜像ID见release/runtime。数据库Schema不变，未重置文献库或缓存；PostgreSQL/Redis保持运行。API健康、机器人重连；本轮没有主动向飞书发送消息，之前用户确认的实收不冒充本版本实收；unknown ack仍开放。

方法归属错误真实保留在api-release/q3-answer.txt：模型把MedSAM论文中对照U-Net/nnU-Net的边界框编码归给MedSAM本体。随后补充通用“文章身份≠段落里每个模型身份”的约束并重新发布/复验，不删除原答案，不把策略字符串测试当医学验证。即使一次改正，仍不能据此证明模型普遍不会混淆。

仅提示修订后仍失败，保留api-attribution-final。进一步读取实际缓存发现此前只召回Training protocol and experimental setting，缺少Network architecture；现比较题优先补齐架构段落。以冻结真实候选和现有缓存生成的[架构对照](architecture-answer.txt)已正确区分ViT图像编码器/提示编码器/掩码解码器与nnU-Net框架，未再把基线的二值掩码拼接说成MedSAM结构。该次属于回放；不是独立医学签署，也不代表后续生成不会再犯。

尚未完整通过的质量门槛：细分亚区证据覆盖、全面瓶颈综述、宽主题2–3篇实际引用全文、所有比较/推断与数值的独立医学签署、供应商偶发超时/筛选无效。公开全文仍限既定许可/域名，未为追求数量绕过许可。下一步应针对这些真实样例补充来源与语义复核；不自动进入第五阶段。

学习材料：[六份教程与可运行Demo](../learning/phase-04/openalex-stage4/README.md)；[使用说明](usage.md)。当前交付为技术核心、部署和可复核实测，完整科研/医学验收保持开放。

## 2026-10-30中断后的交接

最终镜像身份见release.json。api-architecture-final/q3-response.json是502 extraction_failed，不是成功回答；之前提示词单独修复也未消除方法归属错误。architecture-answer.txt才是补入实际架构正文后的成功再生成，明确属于回放。最后118项受影响测试通过，完整离线1391项和后续修订测试的版本范围按上表分别保留。

机器人最后已确认exit=1、oom=false；重启一次后仍退出。公共无凭据探测：宿主飞书HTTPS200，容器No address associated with hostname；进一步探测飞书和api.deepseek.com可解析，api.openalex.org仍Temporary failure/No address。尚未证实网络持续恢复，不能直接归因于模型结构化输出或声称代码异常已全部解决。

自动审批读取docker desktop restart帮助时因账户额度失败，命令未执行。未重启Docker Desktop、未修改DNS/防火墙/hosts、未清空数据库或卷。待审批恢复后，先重新核对DNS与真实HTTPS，再启动同镜像机器人，确认feishu_connected，最后重跑方法比较HTTP题并阅读归属语义。无需再改业务Schema，也不应重做原阶段迁移。当前不可标全部交付完成。

## 2026-10-30规划维度上限补验

此前机器人退出状态已由本次部署恢复，API健康、feishu_connected；比较规划上限提示修复、74项受影响测试和真实HTTP同题通过。修复后飞书实收仍待确认，旧失败不覆盖，详情见[续验记录](feishu-e2e-20261030.md)。
