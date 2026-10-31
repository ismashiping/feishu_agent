# 当前状态与开发计划

> 2026-10-31 回归归因/产物治理：37项逐项归因完成，8项CLI非法输入验证顺序已修复；最新完整离线1480通过、29失败、122排除、0跳过。29项为旧PubMed契约8项及local业务范围冲突21项，保持开放。清理11个空测试目录、3个缓存及build副本，证据/环境/备份/数据保留。详见[本轮记录](regression-attribution/README.md)。未部署、未进入新Phase。

> 2026-10-31 专项架构收敛：已统一 API/CLI/飞书科研装配、清理全文旧参数；受影响专项54项及入口检查1项通过。默认回归1468通过、41失败，其中本轮四项迁移失败已专项修复复验；其余37项待定位，整库未验收。未部署、未变更数据库、未推进业务阶段。见[实际报告](architecture-convergence.md)。

> 2026-10-30 OpenAlex 全文地址：缓存之后按 `content_urls.grobid_xml`、`content_urls.pdf`、`best_oa_location.pdf_url`、`locations[].pdf_url` 尝试实际给出的 HTTPS 地址。不因域名、`is_oa` 或许可字段拒下；许可只作元数据。成功后仍分块、Embedding 并写入 pgvector。失败分开记录为无地址、下载失败、无效文件、身份不符、解析失败、向量化失败。比较题会继续选择另一侧论文。相关单元测试已通过。`W3014974815` 的真实下载、解析和召回未完成，未部署。

> 2026-10-30 飞书端到端准备：当前工作区已装入镜像 `feishu-e2e-20261030`（`sha256:46274483a2c1…`）并重建 API/机器人。API healthy，机器人 `feishu_connected`（源时间 2026-10-30T09:03:47Z）。未迁移、未清卷、未跑 pytest。四题实收尚未开始，不标端到端或医学通过。见 [续验](openalex-stage4/feishu-e2e-20261030.md)。

> 2026-10-30 OpenAlex-only 全文：科研链路改为 Works API 发现、Content API 获取 TEI/PDF、既有 pgvector 缓存和生成。运行时不再装配 PMC。历史 PubMed 客户端和库表仍在仓库中，供既有离线解析与历史测试使用，科研回答不调用它们。本轮未重建镜像、未改生产库。见当前架构。

> 2026-10-30 分析确定性构造：模型选择 quote_id，程序写入逐字事实、缺失方法字段和总体关系。真实三题均生成合法 AnalysisResult，状态为 partial，总体关系均为 unknown。MedSAM 本轮 eligible=4、命中 4，命中变化来自筛选可用数和 top_k=5，不是分析丢文献。图神经网络规划失败未改。见[任务记录](specs/tasks/analysis-structured-assembly.md)。未部署。

> 2026-10-30 分析事实与推断：事实值必须逐字等于引文，推断必须带验证说明。生成说明已分开这两类；业务规则失败可修正一次。真实三题在修正后仍未生成 AnalysisResult。见[任务记录](specs/tasks/analysis-epistemic-contract.md)。未部署。

> 2026-10-30 分析失败归因：JSON 与 Schema 已能分开记录。MedSAM 与钙钛矿的真实输出都解析成功并通过 Schema，随后因 `reported_fact_quote`（钙钛矿还含 `inference_requires_verification`）被拒绝，仍没有 AnalysisResult。见[任务记录](specs/tasks/analysis-failure-stage.md)。未部署。

> 2026-10-30 分析输出预算：分析单独使用 16384，截断可再试一次 32768；`finish_reason=length` 记为 analysis_output_truncated。共享预算仍不超过 4096。续费后的真实复验未再遇到 HTTP 402，也未再截断；MedSAM 与钙钛矿各命中 5 篇后因结构/证据校验失败，肝脏题两次停在 `relation_anchor`。三道方向题都还没有 AnalysisResult。见[任务记录](specs/tasks/analysis-output-budget.md)。未部署。

> 2026-10-30 科研检索证据：筛选思考关闭、标准化术语并入锚点、方向题进入可行性分析。真实复验已有命中并交给分析节点，分析输出在 4096 token 处截断，未形成 AnalysisResult。见[任务记录](specs/tasks/evidence-retrieval-trace.md)。未部署，不代表医学或飞书端到端通过。

> 2026-10-30 QueryPlan 诊断：固定规则码、脱敏日志、原文与标准化术语分离、自动路由缺意图失败。离线测试与真实规划复验见[任务记录](specs/tasks/query-plan-diagnostics.md)。未部署，不代表医学或飞书端到端通过。

> 2026-10-30最新工作区：证据驱动可行性分析代码/测试已编写，待阶段集中验收，未部署；见[任务记录](specs/tasks/evidence-feasibility.md)。上一检索身份任务也仅静态检查通过，真实四题与人工签署未完成。

> 2026-10-30最新工作区状态：单次规划与自然语言意图路由代码/测试已编写，[任务记录](specs/tasks/natural-intent-routing.md)。Ruff静态检查通过；pytest及真实模型/飞书未执行，未部署，待阶段集中验收。原飞书业务失败保持开放；下列旧状态按各自记录时点阅读。

> 2026-10-30最新状态：[科研回答第四阶段](openalex-stage4/acceptance.md)技术核心及教材已交付，完整验收开放；API已更新，机器人启动/容器DNS故障未恢复，进一步Docker操作被账户额度导致的自动审批失败阻断。历史阶段记录不代表当前运行状态；未进入第五阶段。

> 最新增量：OpenAlex第三阶段技术核心及教材已交付；后续用户授权的业务库迁移、新镜像部署、真实API/飞书实收已补验。[本阶段技术验收](openalex-stage3/acceptance.md)、[部署与端到端实际结果](openalex-stage3/deployment/acceptance.md)。科研质量、医学签署和发送ack仍有缺口。这是科研改造第三阶段，与下表历史Phase 3 PICO不同；未进入第四阶段。

适用范围：2026-10-28 当前工作区。状态依据下列原始验收记录，不能仅依据实现或教材判定完成。本轮目录治理不开展下一阶段业务开发。

| 能力/阶段 | 当前状态 | 证据与缺口 |
| --- | --- | --- |
| Phase 0 | 历史工程范围已验收 | [记录](phase0-acceptance.md)，不代表后续业务 |
| Phase 1 | 技术与教材交付；医学待签署 | [验收](phase1-acceptance.md)、[人工复核](phase1-medical-review.md) |
| Phase 2 | 延期，尚未开展完整阶段验收 | [SPEC](specs/02-async-experience.md)；已有有界工作池不等于完整异步体验 |
| Phase 3 | 核心/教材交付，真实模型和人工样例待验收 | [记录](phase3-acceptance.md) |
| Phase 4、5 | 各自冻结核心范围已验收 | [Phase4](phase4-acceptance.md)、[Phase5](phase5-acceptance.md)；不推定医学召回提升 |
| Phase 6、7 | 核心/教材交付，真实链路与医学仍有缺口 | [Phase6](phase6-acceptance.md)、[Phase7](phase7-acceptance.md)、[医学复核](phase7-medical-review.md) |
| 最小基线 | 失败基线已冻结，可复算 | [结果](../evaluation/results/minimal-v1/results.md)；fresh0/2、来源4/4、医学null |
| MA-01/02 | 六角色与有界反馈核心完成 | [MA01](ma01-acceptance.md)、[MA02](ma02-acceptance.md)；未新增真实模型/医学验收 |
| Phase 8 | 冻结维护核心工程验收完成 | [记录](phase8-acceptance.md)；版本、运行账本、治理、同步、显式重建，不代表医学通过 |
| Phase 9 | 离线核心/教材/CI配置交付；完整阶段未验收 | [记录](phase9-acceptance.md)；真实固定模型/人工标签/服务饱和测试缺失，远端CI未核实 |

## 后续事项

优先补独立医学标签、真实报告成功样例和指定真实模型链路，再冻结服务负载预算。Phase2顺序待确认；没有证据表明有正在开展的业务开发或已取消任务。完整Phase9与医学验收不能通过文档治理完成。

## 历史记录

[整理前完整开发日志](archive/development-plan-before-governance.md) 原样保留阶段计划、失败、重试、局部与全量测试范围。后追加记录可能取代更早的“下一任务”，按各自时点阅读。历史Phase9记录在独立验收文件，不据旧日志声称尚未启动。

<!-- Historical inbound anchors; detailed sections are in the snapshot. -->
<a id="multi-agent-ma-02-剩余角色与反馈2026-10-28"></a>
<a id="multi-agent-增量-ma-012026-10-28"></a>
<a id="p0-02-本次执行"></a>
<a id="p0-03-本次执行"></a>
<a id="p0-04-本次执行"></a>
<a id="p0-05-本次执行"></a>
<a id="p0-06-本次执行"></a>
<a id="p0-07a-本次执行"></a>
<a id="p0-07b-本次执行"></a>
<a id="p0-07c-本次执行"></a>
<a id="p0-07d-本次执行"></a>
<a id="p0-07e-本次执行"></a>
<a id="p0-08-本次执行"></a>
<a id="p1-01-本次执行"></a>
<a id="p1-02-本次执行"></a>
<a id="p1-03-本次执行"></a>
<a id="p1-04-本次执行2026-10-27"></a>
<a id="p1-05-本次执行2026-10-27"></a>
<a id="p1-06-本次执行2026-10-27"></a>
<a id="p1-07-本次执行2026-10-27"></a>
<a id="p1-08-本次执行2026-10-27"></a>
<a id="p1-09-本次执行2026-10-27"></a>
<a id="p1-10-本次执行2026-10-27"></a>
<a id="p1-11-本次执行2026-10-27"></a>
<a id="p1-12-本次执行2026-10-27"></a>
<a id="p1-13-本次执行2026-10-27"></a>
<a id="p1-14-本次执行2026-10-27"></a>
<a id="p1-15-本次执行2026-10-27"></a>
<a id="p1-16-linux容器最终验收2026-10-27"></a>
<a id="p1-16-发布后真实收发补验2026-10-27"></a>
<a id="p1-16-本次执行2026-10-27"></a>
<a id="p1-17-本次执行2026-10-27"></a>
<a id="phase-0-后续最小任务路线"></a>
<a id="phase-09-阶段路线"></a>
<a id="phase-1-任务进度"></a>
<a id="phase-3-p3-01-当前交付2026-10-28"></a>
<a id="phase-4-p4-01-当前交付2026-10-28"></a>
<a id="phase-5-p5-01-当前交付2026-10-28"></a>
<a id="phase-6-p6-01-当前交付2026-10-28"></a>
<a id="phase-7-p7-01-当前交付2026-10-28"></a>
<a id="phase-9-离线核心执行2026-10-28"></a>
<a id="phase8-p8-01-显式版本发布2026-10-28"></a>
<a id="phase8-p8-02-本地增量运行2026-10-28"></a>
<a id="phase8-p8-03-来源别名与状态治理2026-10-28"></a>
<a id="phase8维护核心收尾完成2026-10-28"></a>
<a id="全量回归与质量"></a>
<a id="分步真实-tdd-记录"></a>
<a id="历史证据人工内容复核与验收决定"></a>
<a id="原环境与干净开发环境回归"></a>
<a id="各阶段共同进入条件与完成定义"></a>
<a id="回归依赖与真实冒烟"></a>
<a id="场景与文件范围"></a>
<a id="场景与最小实现"></a>
<a id="场景实现与文件范围"></a>
<a id="完整性变更与验收边界"></a>
<a id="官方结构与组件核查"></a>
<a id="实现与修改范围"></a>
<a id="实际-red--green--回归"></a>
<a id="开发进度与任务记录"></a>
<a id="文件与学习内容"></a>
<a id="文档一致性核对2026-10-27p1-12后"></a>
<a id="最小设计与交付文件"></a>
<a id="最小设计与文件"></a>
<a id="最小评价基线-v12026-10-28"></a>
<a id="最终回归兼容与冒烟"></a>
<a id="本次-wheel-与独立安装冒烟"></a>
<a id="本次可执行复验"></a>
<a id="框架职责调整2026-10-27-历史快照已由下述通用接入替代"></a>
<a id="环境与质量验证"></a>
<a id="环境事实与显式修订"></a>
<a id="环境命令约定与原始证据"></a>
<a id="真实-tdd-与发现的边界缺陷"></a>
<a id="真实-tdd-记录"></a>
<a id="真实-tdd-记录-1"></a>
<a id="真实-tdd-过程"></a>
<a id="真实-tdd-过程-1"></a>
<a id="科研选题调研定位与-phase-67-规划更新2026-10-28"></a>
<a id="组件核实与环境准备"></a>
<a id="质量与环境验证"></a>
<a id="质量与环境验证-1"></a>
<a id="质量安装与实际-demo"></a>
<a id="路线调整2026-10-28计划修订历史"></a>
<a id="通用模型-api-接入调整2026-10-27"></a>

## 探索型发现工作流修复

用户授权的最小增量：澄清决策区分阻断/可选、候选PubMed查询和来源说明。默认来源后续按用户要求改为hybrid；保留原检索/引用/反馈预算。真实执行结果单列于[本次验收](exploratory-discovery-acceptance.md)，不改历史P3–8/MA或医学验收。

## OpenAlex 科研问答改造（2026-10-29）

用户新需求的第一阶段静态代码分析已交付，详见[源码调查与分阶段设计](openalex-research-upgrade-analysis.md)。确认现有按需PMC全文、缓存和综合提示词可复用，同时列出时间解析、任务语义筛选、OpenAlex身份与来源契约的缺口。本轮仅新增调查文档和本条状态记录，未改生产逻辑、未运行测试或真实服务，不代表新增业务能力已验收。后续第二至第五阶段均未实施；第二阶段先完成官方契约核查、完整SPEC与验收fixtures冻结。本轮依单阶段边界停止。


## OpenAlex科研检索第二阶段（2026-10-29）

[冻结SPEC](specs/openalex-stage2.md)、[验收记录](openalex-stage2/acceptance.md)、[学习材料](learning/phase-02/openalex-stage2/README.md)。已实现唯一在线OpenAlex、科研约束/日期、摘要语义筛选、有界补检及现有引用链接入；完整离线回归1358通过/122未选中，后续修复受影响范围202通过/1未选中，最终新契约31通过，Ruff通过。真实五题规划/检索/筛选均执行，入选5/0/5/5/2；坏引文排除并保留partial。独立医学标签与签署、真实本地库/飞书/完整生成、成本对比未完成，不标完整科研质量验收。本轮停止，第三阶段全文与第四阶段回答改造未开展。历史Phase2异步体验不因新“第二阶段”命名而改变状态。

## 第二阶段后续补验（2026-10-29）

[记录](openalex-stage2/followup/acceptance.md)：当前源码在独立容器目录执行真实hybrid问答，状态answered、4篇OpenAlex来源、79.094秒（含模型加载），未重启服务或向飞书发送。修复来源渲染误标PubMed；113项受影响测试和Ruff通过。新增106条盲化医学复核材料，决定与签署未填写。完整科研质量与飞书/全文验收仍未通过，不进入第三阶段。

## 候选医学证据AI复核（2026-10-29）

[逐项记录与结论](openalex-stage2/followup/review/ai-review.md)：106条均完成AI证据阅读，输入/输出hash冻结，随后比对旧模型。34直接、36部分相关、19不相关、17不确定；17条入选记录主题相关，但存在疑似同工作双载体重复入选与历史证据当前性不足，建议第二阶段修订。独立专家decisions/signoff未修改，仍待真实医学签署。本轮未改生产代码，未进入第三阶段。

## OpenAlex第三阶段全文RAG（2026-10-29）

用户授权进入本阶段，保留第二阶段医学复核不通过建议与待签署事实。实现OA JATS/PDF、许可和身份核验、章节分块、E5/pgvector缓存与问题段落召回；技术核心及六份教材交付。[验收](openalex-stage3/acceptance.md)、[SPEC](openalex-stage3/spec.md)、[教材](learning/phase-03/openalex-stage3/README.md)。集中离线1382通过/122未选中；最后章节重排修正受影响209通过，未再称全量；Ruff通过。实际HTTP验证JATS/PDF，真实E5及隔离库29向量、缓存/回滚/迁移验证；真实模型回放回答引用两段全文。未执行新五题全链路、飞书、业务库迁移或镜像重建；MRI细节召回不足和重复免责声明保留，医学未签署。停止第三阶段，未开展第四阶段。

## 第三阶段业务部署与真实端到端补验（2026-10-29）

用户明确授权业务库迁移和服务重建。已备份clinical_agent_e2e并从p804_0007经p1001_0008升级oa3001_0009；API/机器人使用新镜像，API healthy、机器人connected，旧数据和卷保留。默认五题真实HTTP执行：3 answered、2 insufficient_evidence；指定论文正例完成真实在线发现到JATS/E5/pgvector/2段全文引用，业务库1篇/29向量；热请求保持缓存不变。用户真实飞书提问被accepted并实际收到含参考文献回答，但发送ack为unknown；不伪称sent。[记录](openalex-stage3/deployment/acceptance.md)。保留中文ASCII FTS限制、抽取失败、段落召回不足和医学未签署；未进入第四阶段。

## 2026-10-30飞书规划上限修复

本轮将模型输出维度总数（含比较方法名）最多5项写入提示，保留拒绝契约。74项受影响测试通过/1未选中，Ruff通过；新镜像已部署，API健康、机器人重新连接；同题真实规划与HTTP answered复验通过。原失败保留，修复后真实飞书实收仍待复验，不标完整端到端或医学通过。详见[本次记录](openalex-stage4/feishu-e2e-20261030.md)。本轮未进入下一阶段。

## 科研可行性系统重构设计（2026-10-30）
用户重新明确产品定位，整体设计见[重构SPEC](specs/research-feasibility-refactor.md)。当前仅设计冻结及飞书错误分类日志补丁，95项受影响测试通过，补丁未部署；四题业务缺陷、意图路由、科研报告质量与独立签署仍开放。下一任务为单次规划与意图路由，不将设计标记为实现。

## 架构迁移 Phase 1（2026-10-31，本次专项）

用户确认后完成Agents状态/角色迁移与Graph组装提取，ResearchService和旧导入兼容保留。[SPEC](agents-migration-phase1/spec.md)、[实际验收](agents-migration-phase1/acceptance.md)、[教材](learning/phase-01/agents-migration/README.md)。全量1484通过/30失败/122排除，其中29项与Phase0一致，新增签名测试比较缺陷已修复，受影响9项全部重跑通过；未再次全量，不重写首轮失败。Mypy仍193错误，归一后无新增；Ruff src/tests通过。结构兼容专项交付，整库/真实依赖/医学未验收，未部署，停止等待用户确认API架构Phase2。本专项编号不改变历史业务Phase1验收事实。

## 架构迁移 Phase 2（2026-10-31，本次专项）

用户确认后完成API包职责拆分及旧工厂/运行时导入兼容。[SPEC](api-migration-phase2/spec.md)、[实际验收](api-migration-phase2/acceptance.md)、[教材](learning/phase-02/api-migration/README.md)。完整离线1524通过/29失败/122排除，失败身份与Phase0完全一致；API补充契约36通过，扩展专项101通过，Ruff src/tests通过。Mypy仍193错误，无新增。相对基线结构兼容专项交付，整库、真实依赖和医学未验收；未部署、未迁移数据库，停止等待架构Phase3确认。本记录不改变历史业务Phase2状态。

## 架构迁移 Phase 3（2026-10-31，本次专项）

完成21模块渐进迁移至rag/integrations/db，旧模块同对象兼容保留；未改算法、数据库Schema/事务/迁移原文。[SPEC](rag-db-migration-phase3/spec.md)、[映射](rag-db-migration-phase3/migration-map.md)、[实际验收](rag-db-migration-phase3/acceptance.md)、[教材](learning/phase-03/rag-db-migration/README.md)。完整离线1595通过/29失败/122排除，原失败身份不变，新增70项检查全部通过。Ruff源码/测试通过；Mypy仍193错误无新增，scripts仍17个旧E402。结构兼容专项交付，不代表整库、真实依赖或医学通过；未部署、未迁移数据库，停止等待架构Phase4确认。本编号不改变历史PICO业务Phase3状态。

## 架构迁移 Phase 4（2026-10-31，本次专项）

完成飞书main/events/dedup/worker/sender迁入`clinical_agent.channels.feishu`，顶层`feishu`以同模块对象保留旧导入与`python -m`兼容；`clinical-feishu`指向canonical入口。事件、Redis owner租约、工作/发送容量、未知交付语义、日志命名空间及关闭顺序保持。[SPEC](feishu-migration-phase4/spec.md)、[映射](feishu-migration-phase4/migration-map.md)、[实际验收](feishu-migration-phase4/acceptance.md)、[教材](learning/phase-04/feishu-migration/README.md)。专项409通过；完整离线1622通过/29失败/122排除，失败身份与Phase3一致。Ruff和锁检查通过，Mypy仍193错误；wheel构建和静态内容检查通过。真实Redis/飞书收发、部署、数据库/模型及医学未验证，未运行迁移；停止等待架构Phase5明确确认。本编号不改变历史业务Phase4状态。
