# 业务部署与真实端到端补验（2026-10-29）

业务库迁移、API/机器人镜像重建与真实API/飞书收发已执行。全文技术链路跑通；科研问题覆盖和回答质量未全部达到最终目标，仍保留第二阶段医学缺口、全文召回不足及模型抽取失败。不以HTTP200或飞书实收代替科研质量验收。

## 业务部署

目标：Compose项目`clinical-agent-e2e`；实际业务库`clinical_agent_e2e`。迁移前head为`p804_0007`，旧全文表也未创建。按顺序新增`p1001_0008`和`oa3001_0009`；最终head已核对为`oa3001_0009`，documents/chunks迁移前后均为0，未重置数据库/卷。PostgreSQL和Redis未重建。

- 停止应用后执行pg_dump自定义格式备份并用pg_restore --list检查：`data/deployment-backups/oa-stage3-20261029.dump`，21322字节，SHA256见[backup.json](backup.json)。备份受.gitignore保护，不发布数据库内容；本轮未做实际恢复演练。
- 旧镜像保留标签`clinical-literature-agent:pre-oa-stage3-20261029`；旧身份见[before.json](before.json)。迁移只增加缓存表，未在业务库执行降级。
- 新应用镜像`sha256:714bd8c9bc3e1e935d479a91872efedebb8f8e45c6f37baa491f0ebca1299dd1`同时用于API/机器人；六个关键源码hash均匹配，无`/app/src`宿主源码挂载，也无临时PYTHONPATH替换。见[runtime.json](runtime.json)、[最终健康状态](health-final.json)。
- 锁定依赖实际存在：llama-index-core 0.14.22、torch 2.14.1+cpu、psycopg 3.3.6。LLM输出预算4096；Compose新增OMP/OpenBLAS/MKL各2线程，复用此前实际验证的线程上限。
- 用户提供的OpenAlex key仅写本地忽略的.env，经HTTP200预检并透传新容器；文档/脚本/镜像不包含值。数据库及飞书/LLM配置复用原运行容器，不打印凭据。

冻结范围见[deployment-spec](../deployment-spec.md)。实际执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/oa_stage3_deploy.py build
.\.venv\Scripts\python.exe -X utf8 scripts/oa_stage3_deploy.py migrate
.\.venv\Scripts\python.exe -X utf8 scripts/oa_stage3_deploy.py recreate
.\.venv\Scripts\python.exe -X utf8 scripts/oa_stage3_e2e.py docs/openalex-stage3/deployment/e2e-default http://127.0.0.1:18080
```

以上为已执行命令，不是建议再次运行；脚本会拒绝覆盖已有备份/结果目录。构建日志[deployment-build.txt](../deployment-build.txt)、[迁移日志](migrate.txt)、[重建日志](recreate.txt)保留实际结果，三个操作退出0。API实际映射18080，沿用原部署端口。

## 真实API六题

默认请求`scope=hybrid`，本地检索保持产品默认vector；模型、OpenAlex、全文获取、数据库、生成和引用门禁均使用重建后实际服务。前五题未指定检索表达；第六题显式传入2024年范围与完整英文题名查询，是预先声明的全文正例，不冒称开放主题发现的召回质量。每题原始请求/响应/渲染答案见[e2e-default](e2e-default/summary.json)。

| 问题 | 状态 | 来源/全文引用数 | 秒 | 验收解释 |
| --- | --- | --- | --- | --- |
| 肝脏分割最新研究 | answered | 5 / 0 | 26.093 | 来源日期均在2024-10-29至2026-10-29；前两篇许可不符，其余受两篇预算限制，只有摘要 |
| 肝脏肿瘤亚区分割最新进展 | insufficient_evidence | 0 / 0 | 16.094 | partial且存在openalex_assessment_invalid；没有用整体肿瘤分割填充，检索质量仍未通过 |
| MedSAM与nnU-Net区别 | answered | 5 / 0 | 20.078 | 有任务条件比较，但部分筛选无效、缺基础原始论文/充分全文，不能称完整方法综述 |
| 最近三年MRI预测肝癌MVI | answered | 4 / 0 | 20.407 | 2023-10-29至2026-10-29过滤通过；全文来源/许可限制使本次仍仅摘要 |
| 肝脏肿瘤分割目前技术瓶颈 | insufficient_evidence | 0 / 0 | 17.765 | 候选37条但无直接入选，未借旧泛主题论文填充；问题覆盖不足 |
| 指定2024年双中心MVI论文采集方案（正例） | answered | 1 / 2 | 32.922 | 在线发现→真实官方JATS→29块E5向量入库→引用两段Methods/Patients；技术链路通过，具体采集参数召回不足 |

本轮五题总耗时100.437秒，六题总计133.359秒，均为串行单样本，不含服务启动模型加载；不是负载/P95结果。原始模型计费token/金额未采集，不能提供成本降幅。

全文正例：[实际完整回答](e2e-default/q6-answer.txt)。论文DOI 10.1186/s12880-024-01206-7，OpenAlex W4391277958。实际取得并引用患者纳入要求和CT训练/MRI外部测试数据分组；没有召回更具体的Image acquisition段，不能把“所附片段没有”说成“整篇没有”。同题热请求17.375秒，仍引用两段全文；缓存payload和到期时间完全未变。这里热请求仍重新做发现/筛选/生成，不等于整个问答零外部调用。

[引用独立核对](evidence-audit.json)：所有回答通过DTO、真实来源快照hash和引用集合校验；有时间范围的实际来源均满足边界。正例两段的文本/章节/字符区间逐字匹配业务缓存source_units；解析正文还与此前独立捕获的官方JATS正文一致。最终业务库1篇OA缓存、29向量；原文献库仍为0。医学语义与全部数值逐项签署仍待独立专家，不将工程校验当医学正确性证明。

## 飞书真实收发

新机器人连接成功。用户在真实飞书会话发送测试问题，服务记录accepted；约29.629秒后delivery状态为unknown。随后用户粘贴收到的正常科研回答（有论文和参考文献），证实实际实收；详见[原始状态和用户确认](feishu-receipt.md)。该回答只有1篇摘要，记录partial和一轮检索失败，不能用API同题5篇来源覆盖飞书实际结果。

因此“接收→研究处理→用户收到科研回复”已实际验证；自动发送确认/幂等收尾不算通过。unknown日志原样保存，没有盲目重试。没有确定HTTP失败原因，后续需增加安全的异常分类或核对发送响应；不在本次伪造sent。

## 失败与限制

1. 首次HTTP脚本误用8000，连接失败；实际部署18080，保留[e2e-live.txt](e2e-live.txt)。
2. 显式本地ASCII keyword/hybrid模式配中文五题被422拒绝，另一个长题名问题抽取502；保留[e2e-live-run2](e2e-live-run2/summary.json)。重跑默认vector不是修复该模式，不声称中文FTS已支持。
3. 英文对照采集问题另一次502 extraction_failed，保留[warm-en-response](warm-en-response.json)与请求；没有通过改写错误结果冒称成功。生产意图抽取仍有真实失败路径。
4. 默认五题中的两题证据不足、三题均只有摘要；有限域名/许可名单和“两篇预算按排名分配”导致可用全文覆盖有限。没有为了填满数量绕过许可、放宽任务或删除失败记录。
5. 中文采集方案正例的两段均为Patients，缺少CT/MRI具体采集细节；进一步段落召回优化和第四阶段写作仍未完成。
6. 飞书虽由用户证实收到，但发送ack unknown、去重状态untouched保留，不能称投递状态完整通过。
7. 第二阶段独立医学签署仍空白；回答仍有逐篇复述和重复免责声明。未开展第四阶段。

新增脚本Ruff通过，`git diff --check -- docker-compose.yml`通过。此次修改为部署配置和验收脚本，没有改研究业务源码；未重复跑全量离线测试或原122项opt-in测试，沿用并明确区分此前1382/209的范围。真实执行覆盖了本次受影响部署边界。技术部署完成，最终科研质量验收仍开放。
