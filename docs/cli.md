# CLI离线入库与问答（P1-10）

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
