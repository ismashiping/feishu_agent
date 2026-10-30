# CLI离线入库与问答（P1-10）

## Phase 5 本地混合检索（2026-10-28）

默认mode=vector保留原行为；API的options增加mode=keyword|vector|hybrid、candidate_limit（默认50、1–100且不小于top_k）、keyword_query（可选ASCII文本）、date_from/date_to（成对ISO日期）。CLI对应 --retrieval-mode、--candidate-limit、--keyword-query、--local-date-from/--local-date-to。本地日期仅接纳完整出版日，未知/年/月精度条目明确排除，不补造日期。

keyword不计算查询Embedding，hybrid计算一次原问题Embedding，再在同一PostgreSQL快照内取得FTS/向量候选并按chunk_id做RRF（k=60），同分UUID升序，不合并掉同文献不同片段。任何必需通道失败即报错，不静默降级；空通道为成功。非vector模式不支持非零min_similarity，不能用余弦阈值过滤RRF/FTS。

FTS为simple ASCII词项匹配与精确PMID/DOI辅助查询，不是BM25或中文分词。中文问题可显式给英文keyword_query；不提供时keyword/hybrid返回retrieval_language_unsupported（API422），vector仍用既有多语言模型。

结果ResearchAnswer增加local_retrieval_mode/strategy、local_channel_status和retrieval_warnings；Python RetrievalResult的hits还保留keyword_rank/vector_rank/fusion_score与score_type。分数不表示医学质量，引用仍来自原证据门禁。scope=hybrid表示本地与在线来源，options.mode=hybrid表示本地算法，两者独立；在线条目不参加本地RRF，PubMed日期仍使用pubmed对象设置。

**现有数据库需显式 `alembic upgrade head` 到 p501_0003**：该迁移增加STORED search_vector与GIN，旧文献/片段/向量/ID保留，新写入自动更新。应用不会自动迁移；本次真实迁移测试仅在隔离测试库执行，没有改用户现有库。用法/范围见 [P5-01](specs/tasks/p5-01-hybrid-retrieval.md)、[学习导航](learning/phase-05/README.md)及[验收记录](phase5-acceptance.md)。以下历史说明按原时点阅读。

## Phase 4 在线来源（2026-10-28）

CLI `ask` 增加 `--scope local|online|hybrid`，API `POST /v1/questions` 接受同名 scope（默认local）及可选 pubmed 对象。pubmed 有 query、date_from/date_to（成对ISO日期）、date_field=pdat|edat、sort=relevance|pub_date、max_results（默认10，1–20）。CLI 对应 --pubmed-query、--date-from/--date-to、--date-field、--sort、--max-results。date_* 仅约束在线分支；online/hybrid 不支持本地 document_ids 或非零 min_similarity。

正式装配仍复用现有 LLM/E5/数据库资源。online 不调用本地向量检索；hybrid 合并本地和PubMed来源、预留名额并去重，不是 Phase 5 的关键词/向量融合。飞书纯文本入口继续默认local，未新增消息语法；渲染器可显示带在线来源的共享结果。

JSON 的 retrieval_scope 与实际请求一致，search_provenance 记录实际query/官方translation、时间、日期/排序、数量、截断、partial和缺失PMID。在线摘要保留真实官方URL/快照hash/字符定位与出版类型、更正关联。无摘要仅metadata_only，不能当claims证据；不自动入库、不代表全文或全部最新研究。仅本地回答的原有引用规则保留。

可选环境 PUBMED_TOOL/PUBMED_EMAIL/PUBMED_API_KEY；基础公开小请求不要求key，部署时登记真实tool/contact。每进程串行/至少0.34秒间隔，总期限30秒，最多20条/8次HTTP尝试。不同进程不协调，启用在线检索的实例需限制为一个并考虑同IP其他工具配额。API 的 pubmed_failed/invalid/timeout 对应503/502/504；获取失败不伪装成完整零结果，partial明确显示。

详情见 [P4-01 SPEC](specs/tasks/p4-01-pubmed-online.md)、[学习导航](learning/phase-04/README.md)及[验收记录](phase4-acceptance.md)。Phase 3 和更早验收记录按当时事实阅读，不当成当前仅local的限制。

## Phase 3 PICO 接入（2026-10-28）

正式共享装配默认先做一次 PICO 分类/抽取，复用 LLM_* 配置和现有模型连接，默认上限 20 秒并受研究总期限限制。每次普通问答会增加一次模型调用；即使本地没有证据也先执行规划。直接构造 ResearchService 不传 planner 时保持原行为，不代表正式入口会在规划失败后静默跳过。

结果 JSON 新增 query_plan，保留原问题、分类、PICO、候选扩展词与原文区间。现有 QuestionRequest 先去首尾空白，区间相对 query_plan.original_question 的 Python 码点索引。检索/生成仍用原问题，未接入 PubMed 或新的关键词通道。

status 新增 needs_clarification：仅 uncertain 且有具体歧义时返回，claims/sources 为空；补充问题后重新提交，无持久对话状态。缺 comparator 合法保留 null，不自动补造。规划错误为 extraction_failed/timeout，不能伪装成证据不足；API 对应 502/504，CLI 沿用错误 JSON/非零退出码，飞书显示澄清与 PICO。

完整契约、阶段验收边界见 [P3-01 SPEC](specs/tasks/p3-01-pico.md)及[开发进度](development-plan.md)。真实模型三例未验收时不声称已证明 PICO 语言理解准确率；原有命令/历史验证按各自时点阅读。

已安装的`clinical-agent`与`python -m clinical_agent`提供相同入口，复用现有入库、检索及RAG服务。[任务SPEC](specs/tasks/p1-10-cli-entrypoints.md)、[执行记录](development-plan.md)。P1-11已增加[API入口](api.md)，飞书已完成[纯事件过滤](feishu-events.md)，业务运行时尚未接通。

## 环境与帮助

```powershell
.venv/Scripts/python.exe -m uv sync --locked --extra ml --extra db --extra rag --system-certs
.venv/Scripts/python.exe -m clinical_agent --help
.venv/Scripts/python.exe -m clinical_agent ingest --help
.venv/Scripts/python.exe -m clinical_agent ask --help
.venv/Scripts/python.exe -m clinical_agent doctor
```

入库只需db/ml extras；问答另外需要rag。上述命令针对CLI，会移除未选择的api extra；保留当前全量开发/测试环境时还应添加--extra api。help/doctor不加载模型、不读取数据库/DeepSeek配置，11包基础环境仍可执行。缺可选依赖时报missing_dependency，不自动安装或下载。现有控制台脚本无需修改，模块和console均已通过安装入口测试。

业务命令需要先按[数据库说明](postgres.md)启动PostgreSQL并手动执行迁移；CLI不会自动迁移。按[本地模型说明](local-embedding.md)准备固定E5 revision资产；CLI不会下载模型。设置数据库密码等环境变量，问答另需LLM_API_KEY、LLM_BASE_URL和LLM_MODEL；不要把密钥写入argv或共享脚本，应用不会自动读取.env。

## 导入单个文件

```powershell
$cliPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$cliModel = Join-Path (Get-Location) 'models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a'
& $cliPython -m clinical_agent ingest `
    --source-type pdf --path 'data/incoming/paper.pdf' `
    --allowed-root 'data/incoming' --snapshot-dir 'data/snapshots' --model-dir $cliModel

& $cliPython -m clinical_agent ingest `
    --source-type pubmed_xml --path 'data/incoming/pubmed.xml' `
    --allowed-root 'data/incoming' --snapshot-dir 'data/snapshots' --model-dir $cliModel
```

示例文件需由调用者准备，不是仓库自带文献。路径相对调用者cwd解析；文件、允许目录、快照目录和模型目录均需显式提供。OfflineReader按真实resolved路径核对受控根及文件上限并创建内容寻址快照，不提供递归目录扫描。单次一个PDF或XML，XML复用已有32篇批次预算；不会绕过来源或单文档事务规则。

stdout为一个JSON对象：request_id和result；result保留每项index/status/document_id/chunk_count/error_code及batch error。同一来源重入返回already_present，内容变化needs_update，配置或元数据冲突conflict，不覆盖旧数据。CLI在调用时生成UTC ingestion_time；可传`--request-id UUID`关联日志，不把此ID当文献ID。

## 问答

```powershell
& $cliPython -m clinical_agent ask --question '已导入研究报告了哪些局限？' `
    --model-dir $cliModel --top-k 5 --min-similarity 0.0
```

ask只检索local，top_k为1..20，min_similarity为[-1,1]有限数；默认5和0.0。相似度不是概率或证据质量。问题trim后1..4000字符，编码器仍执行token预算，不静默截断。只有成功空召回才返回insufficient_evidence；服务故障不会伪装成无证据。

**ask会把问题及命中的原文片段发送至已配置的模型 API 服务，产生供应商调用费用。** 应确认文献适合发送至该服务。书目/定位从可信命中构造，不接纳模型新增来源；结构引用检查不是医学语义核验。完整生成/来源规则及局限见[RAG说明](basic-rag.md)。

stdout直接输出ResearchAnswer：request_id、status、claims、sources、limitations、retrieval_scope、generated_at。保留kind以区分证据、推断和不确定性，sources保留实际引用原文和定位，不能丢弃局限后当成诊疗结论。JSON使用ASCII转义表示Unicode，`json.loads`会还原中文，适合Windows非UTF8管道；这不是中文丢失。

## 输出、退出码与资源

| 退出码 | 含义 | stdout |
| --- | --- | --- |
| 0 | 导入条目全部imported/already_present；问答answered或insufficient_evidence | 完整JSON |
| 3 | 空批/批次错误，或条目含failed/rejected/needs_update/conflict | 完整批次JSON；不要丢弃部分成功项 |
| 2 | 参数、配置或缺可选依赖 | 空；stderr说明错误 |
| 1 | 装配、业务调用或资源关闭故障 | 空；stderr受控错误 |
| 130 | KeyboardInterrupt | 空；stderr interrupted |

PowerShell使用`$LASTEXITCODE`读取退出码。语法失败保留usage但不回显非法参数值；业务错误stderr为单行含request_id/error_code的JSON，结构化日志可能另占行。正常输出与错误不会包含配置密钥、原始异常或本机路径字段；证据原文本身仍按实际内容保留。doctor沿用原有输出协议。

参数校验先于任何资源创建，所需配置校验先于模型加载。问答HTTP客户端先关闭，随后dispose数据库engine；业务context退出成功后才打印结果。异常/关闭失败不打印成功答案；入库若已commit而后关闭/输出失败，数据库提交仍可能已发生，应用重入规则用于核对，不能把进程退出码理解为分布式回滚。Ctrl-C遵循同步调用与底层超时限制，不强杀线程或宣称撤销已提交数据。

每次CLI进程会加载本地E5，启动成本明显；本任务未增加常驻模型服务或交互会话。模型无公开close接口，不假造关闭API，由进程结束回收对象和CPU内存。

## 验证范围

43个命令/装配/安装入口目标用例，默认回归625 passed；另1项真实E5/PostgreSQL集成验证PDF导入与重入、XML导入、检索、问答及来源关联。该集成在单个进程调用cli.main，生产装配保持，实际模型在测试中复用一次；LLM明确为HTTPX MockTransport，不是实际DeepSeek。本轮没有有效LLM环境配置，未重用聊天中披露的旧密钥，不声称真实CLI→E5→PG→LLM整链路已验证。

专用测试库已清空fixture、迁移仍p107_0002，容器停止而卷保留。11包基础环境分别以module/console执行help、doctor、缺依赖共10项，cp936管道通过。未新建wheel或验证Linux部署；API已在P1-11单独验收，飞书及Phase1整体验收仍待后续任务。

## Phase 6 分析入口

`clinical-agent ask --question "科研想法" --model-dir <现有模型目录> --analyze` 输出分析 JSON；其余本地/在线/混合选项复用原 ask。无该参数仍输出原问答。模型需支持结构化 JSON，配置复用 LLM_*，无新依赖或数据库迁移。结果保留精确引文、来源定位及事实/推断/假设标签，真实医学验收仍以 [阶段记录](phase6-acceptance.md) 为准。

## Phase 7 科研选题报告

`clinical-agent ask --report --question "科研想法" --model-dir <模型目录>` 返回 report/markdown JSON；加 `--format markdown` 输出完整 Markdown。--report 与 --analyze 互斥。选项 scope/options 复用现有检索能力，无新增依赖和迁移。Windows 文本导出建议启用 PYTHONUTF8=1。核验不可用返回 verification_incomplete，确定性冲突或 unsupported 返回 rejected；不要把 CLI 调用成功等同于医学核验通过。

## Phase8显式版本发布

`clinical-agent ingest <原有必需参数> --update-existing` 使用p801_0004版本表，返回updated/metadata_updated或幂等状态。普通ingest不覆盖旧文献。需先显式迁移数据库；没有自动迁移、调度或完整dry-run命令，内部历史读取仅Python接口，见[验收记录](phase8-acceptance.md)。

## P8-02本地批次命令

项目根使用 `python -I scripts/update_literature.py --manifest <JSON> --allowed-root <根目录> --dry-run`；发布时去掉dry-run并传model-dir和snapshot-dir。新迁移为p802_0005。--rescan重查同集合，--runs/--interval-seconds只提供有界进程内循环，不安装调度任务；--evaluate固定回归不接受任意shell命令。详见[批次使用说明](learning/phase-08/update-runs.md)。

## Phase8 本地来源治理脚本（P8-03）

`python -I scripts/govern_sources.py claim --request alias.json`显式登记别名，`resolve --namespace doi --value <DOI>`查询原生/显式候选，冲突退出1且不自动归并。`status --request status.json`使用event_id和expected_event_id提交有依据的来源状态，`inspect --document-id <UUID>`读取当前状态及审计事件。非法输入/数据库错误退出2。无模型或自动联网；需显式升级到p803_0006，使用现行数据库环境配置。

输入示例与限制见[来源治理说明](learning/phase-08/source-governance.md)。撤稿/撤回/关注声明阻断仅作用于本地新检索；在线副本与真实通知核验尚未实现。普通文献导入不会自动生成已审核状态。

## Phase8收尾脚本

`python -I scripts/sync_pubmed.py --request online.json --dry-run`读取显式日期窗口并给出计划；实际发布还需--model-dir和--snapshot-dir。完整窗口最多31天/20篇，partial/truncated不标完成，批次冻结后恢复不重新检索，重叠窗口由版本幂等吸收。

`python -I scripts/rebuild_knowledge.py plan`只读；`stage --run-id <UUID> --model-dir <现有模型目录> --max-tokens 256 --evaluate`暂存并运行隔离PG工程检查；`activate --run-id <同UUID>`仅在评价passed且来源集合未变化时原子切换。最多100文档，既定E5/768维，未知模型/维度拒绝。

输入示例、状态语义、真实测试及容量边界见[维护说明](learning/phase-08/maintenance.md)。上述命令不会自动迁移业务库、加载.env或创建定时任务；需由操作者显式升级p804_0007后使用。

## 探索型提问与来源范围

`ask --question "我想进行肝脏肿瘤亚区的划分，有没有相关研究？" --scope hybrid --model-dir "<已有模型目录>"` 使用既定本地+PubMed流程；省略scope默认hybrid，会请求本地及在线PubMed；仅本地请显式--scope local。mode只控制本地vector/keyword/hybrid。缺C/O/模态可作为后续可选细化，主题可识别时不阻断；零命中仅说明实际范围内证据不足。见[决策契约](specs/tasks/exploratory-discovery.md)。
