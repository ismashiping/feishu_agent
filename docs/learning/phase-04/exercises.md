# 练习与阶段验收

运行离线Demo，比较query_sent和query_translation，检查PMID、source_url、snapshot_xml和content_hash。将响应里的摘要去掉，确认metadata_only，不生成假的摘要。

修改测试的EFetch身份，使返回非请求PMID，观察partial/missing_pmids；再令ESearch失败，确认抛错误而非total_count=0。独立添加一例只有年份的出版日期，对照原有XML测试理解日期精度。

阶段末集中执行：`.venv/Scripts/python.exe -I -m pytest tests/unit/test_pubmed_online.py tests/integration/test_pubmed_online.py -q`。真实官方小冒烟：`.venv/Scripts/python.exe -I -m pytest tests/integration/test_pubmed_online.py -m external -q`；不需LLM/数据库，不固定实时记录数量。

正式CLI示例：`.venv/Scripts/python.exe -I -m clinical_agent ask --model-dir models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a --question "What evidence is available?" --scope online --pubmed-query "aspirin[Title]" --max-results 5`。这会按现有配置调用PICO/回答模型；没有LLM配置时不能运行完整问答，不用官方接口单测通过代替整条真实链路。

API使用POST /v1/questions，JSON包含question、scope及pubmed对象。date_from/date_to成对，date_field为pdat或edat，sort为relevance或pub_date。日期只约束在线分支，不声称过滤了本地库。
