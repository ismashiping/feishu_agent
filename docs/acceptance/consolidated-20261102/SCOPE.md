# 集中验收冻结范围（2026-11-02）

对象：当前工作区源码（以manifest.json的内容哈希为准），不是仅Git HEAD。
业务范围：原中文公开ICU数据AKI想法，正式ResearchService.report两次；
真实OpenAlex、全文获取/缓存、E5、独立PG、分析、四维可行性、多批审核、Markdown。
现有clinical_agent_test_context_20261102库，不清空、不迁移生产库。
技术门槛：默认排除external/performance/database/redis的全套离线pytest，Ruff、
mypy、uv lock --check --offline。分别保存命令/输出，不把排除项记为通过。
业务断言：两次均返回；审核批次ID覆盖无重复无遗漏且无not_reviewed；引用原句
对应本轮真实全文；有合理证据边界。至少一次实际cache_load命中后同key检索，
不可由耗时或库有数据推断。若论文变化未命中标未覆盖，不能强制替换结果。
审核状态不要求verified：证据不足/partial/unknown或合理rejected不伪造通过；
但若发现主体归属、引用或推断严重错误，科研质量结论必须保留限制/失败。
身份/定位校验不等于独立医学审核。
不在范围：HTTP部署、飞书实收、完整历史DB/Redis集成、性能基准、医学专家签署。
真实验证不稳定时只做本批两次，不无限重跑挑选绿色结果。
本轮不主动改业务功能；发现必修缺陷则记录并集中最小修复/受影响重跑。
