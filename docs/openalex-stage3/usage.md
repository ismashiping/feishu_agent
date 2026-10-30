# OpenAlex全文RAG运行说明

业务入口和OpenAlex配置沿用[第二阶段](../openalex-stage2/usage.md)，不另建API或飞书命令。已筛选OA论文由原FulltextService按需增强。失败保留摘要和原因；不能把摘要标成已读全文。

## 部署前提

2026-10-29后续已在实际业务库clinical_agent_e2e完成迁移及API/机器人重建，API实际端口18080，见[真实补验](deployment/acceptance.md)。以下为操作前提，不应无检查地再次运行部署脚本或覆盖备份。

1. 按项目锁文件安装依赖：`uv sync --frozen --all-extras`；运行环境需要rag中的LlamaIndex和已有E5模型。Dockerfile已有rag安装声明，但旧运行镜像不代表已包含它。
2. 核对DB_HOST/DB_PORT/DB_NAME/DB_USER目标；备份按原部署约定执行。在明确目标数据库上显式运行`alembic upgrade head`。新增head为`oa3001_0009`，上游为`p1001_0008`，不自动迁移业务库。
3. 按原部署方式重建镜像并重启所需服务后再验证；后续补验已执行，两个应用容器关键源码hash与当前业务源码一致。

密钥仅由现有环境变量加载，不写代码/fixture/日志。新增表`oa_fulltext_indexes`和`oa_fulltext_vectors`与旧PMID缓存分开。不同解析/Embedding签名不能复用旧向量；30天TTL内复用，过期重新取得正文但相同解析表示不重复编码。

## 本地离线学习与验收

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.\.venv\Scripts\python.exe -X utf8 docs/learning/phase-03/openalex-stage3/demo.py
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/unit/test_oa_fulltext.py tests/unit/test_fulltext_rag.py -q --basetemp=.pytest_oa_exercise
```

这是复现命令，不表示每次阅读已再次运行。集中验收的实际命令和结果见[acceptance](acceptance.md)。全套离线pytest默认排除external/database/redis/performance；不要把它称为全部外部依赖通过。

真实数据库验证脚本只接受`clinical_agent_test_oa_stage3_`开头的测试库，会执行迁移、写入和故意失败的向量事务，不应用于业务库。要求pgvector、已有E5模型、锁定依赖、fixture目录及Alembic目录；运行目录布局参照脚本和验收记录。QA脚本读取其`result4/warm.json`，需要真实LLM配置，会消耗一次模型调用，不会发送飞书消息。其计时不包含新文献发现。

## 缺口定位

优先查看全文warning分类、paper_key、正文许可/身份、source_units定位和签名，不用随机同题论文替代失败来源。仅支持有限域名的明确CC BY/CC0 PDF或官方PMC JATS；网页落地页、未知许可、扫描件、表格提取均不保证。完整错误说明见[学习排错](../learning/phase-03/openalex-stage3/troubleshooting.md)。
