# OpenAlex第二阶段使用

生产运行复用原API/CLI/飞书部署。配置OPENALEX_API_KEY（运行环境或忽略的.env）和OPENALEX_RECENT_MONTHS=24；不要把密钥写进查询URL、文档或源码。LLM、数据库、本地模型与飞书配置沿用现有部署。结构化筛选需要充足输出预算，示例LLM_MAX_TOKENS=4096；输出截断会失败，不会当作合格证据。

CLI通用问题：

```powershell
.\.venv\Scripts\python.exe -m clinical_agent ask --model-dir <已有模型目录> --scope online --question "肝脏分割最新研究有哪些？"
```

显式英文检索用--openalex-query，日期用--date-from/--date-to；与问题时间窗取交集。它们只改变查询，不绕过语义筛选。旧--pubmed-query及edat字段退役。排序由内部相关性/时间双通道控制，--sort/--max-results旧参数的非默认值会明确拒绝；使用本阶段冻结预算。scope local保持离线，hybrid复用本地候选并统一摘要级筛选。

API通用body：

```json
{"question":"最近三年MRI预测肝癌微血管侵犯有哪些研究？","scope":"online","openalex":{"date_from":"2023-10-29","date_to":"2026-10-29"}}
```

生产不再使用pubmed对象，发送它会明确拒绝。历史离线PubMed导入/快照仍可用。当前新OpenAlex文献只支持摘要证据，OA链接并不代表已经下载全文。

离线验收：python -m pytest tests/unit/test_openalex.py -q；真实传输：python scripts/openalex_smoke.py；真实DeepSeek五题：python scripts/openalex_research_check.py（显式读取当前.env的DEEPSEEK_*，产生真实调用）。测试与质量缺口见acceptance.md，不能将这两个脚本当作飞书/数据库/全文验收。
