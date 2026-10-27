# Phase 1 运行与排错

先确认你在真实仓库根目录，始终显式使用.venv/Scripts/python.exe。Settings不自动读取.env；真实部署必须按[运行文档](../../feishu-runtime.md)明确导入环境，不要将密钥复制到命令历史或调试日志。当前阶段状态见[报告](../../phase1-acceptance.md)。

## 最小检查顺序
```powershell
& .venv/Scripts/python.exe --version
& .venv/Scripts/python.exe -m clinical_agent --help
& .venv/Scripts/python.exe -m clinical_agent doctor
& .venv/Scripts/python.exe docs/learning/phase-01/demo.py
& .venv/Scripts/python.exe -m pytest
```
doctor仅检查本地配置，不连接数据库、模型或飞书。Demo要求rag extra；缺langgraph不应为了通过而删掉真实图调用。依赖安装和精确锁以[pyproject](../../../pyproject.toml)和uv.lock为准，不手动升级单个包破坏组合。

## 症状对应检查
| 症状 | 先定位 | 应做什么 |
| --- | --- | --- |
| help可用但ask失败 | 配置/可选依赖 | 核对db/ml/rag extras和环境，不打印Settings秘密 |
| source_failed或拒绝扫描件 | OfflineReader/PDF | allowed_root、文件文本层、权限和预算；MVP没有OCR |
| embedding_input_limit | E5完整前缀计数 | 查实际token数和512上限，不静默截断 |
| 模型加载失败 | manifest/revision | 按[模型说明](../../local-embedding.md)核对本地快照；不要关闭哈希校验 |
| already_present/needs_update | 既有文献身份 | 前者正常幂等，后者内容变化不覆盖；不要清库“修复” |
| insufficient_evidence | hits和过滤条件 | 检查本地是否导入、阈值/范围/模型一致；不是证明治疗无效 |
| generation_failed/timeout | LLM边界 | 确认固定供应商端点、凭据和预算；错误不等于空召回 |
| citation_invalid | 原始生成的引用集合 | 拒绝回答，保留固定错误；不要删坏引用后发布剩余结论 |
| 飞书无事件 | 应用发布/长连接订阅 | 依[飞书说明](../../feishu-runtime.md)查im.message.receive_v1和权限 |
| busy/close返回False | 在途Future/发送队列 | 检查实际线程是否结束；不能提前关共享客户端 |
| 重复或投递未知 | Redis owner/HTTP结果 | 按TTL和未知语义处理，不重复POST强行确认 |

## 真实服务测试
先建独立loopback测试PG/Redis，不使用业务库。数据库名必须以clinical_agent_test_开头，并显式设置CLINICAL_AGENT_DB_ALLOW_TEST_RESET=1；这会授权该测试清理专用库内容。DatabaseSettings还需要CLINICAL_AGENT_DB_HOST/PORT/NAME/USER/PASSWORD。Redis使用CLINICAL_AGENT_TEST_REDIS_URL，测试仅清理随机前缀，禁止FLUSHALL。

```powershell
& .venv/Scripts/python.exe -m pytest tests/integration/test_postgres.py tests/integration/test_ingestion.py tests/integration/test_retrieval.py -m 'database and not external'
& .venv/Scripts/python.exe -m pytest tests/integration/test_feishu_dedup_redis.py tests/integration/test_phase1_acceptance.py -m redis
```

E5模型位于models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a，测试先验证manifest。真实研究测试另需CLINICAL_AGENT_TEST_EVIDENCE_DIR、LLM_API_KEY、LLM_BASE_URL、LLM_MODEL，并显式设置CLINICAL_AGENT_P117_PAID_CALLS=1。这是付费单请求测试，仅在人已授权后运行；不要放进默认回归：

```powershell
& .venv/Scripts/python.exe -m pytest tests/integration/test_phase1_acceptance.py -m 'external and database'
```

先对专用空库执行既有Alembic迁移，再跑闭环；外部前提不足是未验收，不以skip当通过。CLI/API真实模型集成仍使用明确HTTP替身，命令和真实边界见[CLI](../../cli.md)与[API](../../api.md)。SDK真实收发需要人工发送指定测试口令，不能无人值守反复等待并计为成功。

## 安全修订构建与恢复
Python3.12.16已取得官方Windows构建并完成候选复验；原3.12.15环境保留备份。Python安全补丁的源码发布不等于Windows/容器目标构建已能取得。升级需取得官方构建、核哈希、在独立候选环境复验锁/模型/SDK/DB，再替换.python-version和镜像，不能只改版本字符串宣称闭环。实际核查结论见阶段报告。

临时服务测试结束只删除本轮唯一名称的容器与卷。不要清理此前任务资源或共享Conda环境。若在日志看到SDK弃用警告，记录具体来源并在升级时复验，不全局屏蔽。

医学摘要复验还需将CLINICAL_AGENT_P117_MEDICAL_XML指向冻结XML；SHA256必须匹配P1-17 SPEC，原始NCBI接口为https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=26551272&retmode=xml。快照/答案见阶段报告，不自动联网获取或重跑付费请求。更换解释器后mypy使用独立新缓存；模型组合验收避免与镜像构建/全量回归并行争抢内存，失败须保留原始记录。

连续真实模型测试曾因已结束测试的引用尚未回收而触发Windows os1455；release_model_memory夹具在恢复patch后显式gc.collect，原五项同进程组合复验通过。不是通过提高预算或修改系统页面文件解决。Windows x64可用[官方解释器引导脚本](install-python.ps1)校验并安装项目内3.12.16。
