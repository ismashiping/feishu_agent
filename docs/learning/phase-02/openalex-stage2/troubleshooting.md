# 运行与排错

在项目根使用虚拟环境。OPENALEX_API_KEY只放运行环境或git忽略的.env，OPENALEX_RECENT_MONTHS默认24；匿名访问可测试公共接口，可能限流。现有LLM_*配置机制不变。openalex_research_check.py是显式DeepSeek验收脚本，从当前.env读取现有DEEPSEEK_*，不能当默认生产配置说明。

openalex_auth_failed：检查运行环境密钥，不打印请求头。openalex_rate_limited：本次预算内不自动重试，记录部分失败；不要无限重放。openalex_plan_required：缺少新科研约束或英文科学概念，不能伪装为已理解问题。openalex_options_retired：旧PubMed语法退役，CLI使用--openalex-query；不把PubMed字段语法原样发OpenAlex。

screening_failed/assessment_invalid：查看受控验收输出的schema、ID、quote及回答维度，不输出SDK异常或凭据。日期为空与严格时间窗必须分别审查；没有命中不等于没有研究。

`python scripts/openalex_smoke.py`只验证HTTP与规范化。`python scripts/openalex_research_check.py`调用真实模型并产生费用，保存五题计划、候选与失败；它不测试数据库/飞书真实发送或全文。历史结果文件不可覆盖成通过。
