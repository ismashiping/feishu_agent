# 排错与限制

pubmed_failed：HTTP状态/网络不可用、全部批获取失败，或没有可用记录的partial。pubmed_invalid：官方响应格式/身份/快照不一致。pubmed_timeout：锁/限流/HTTP耗尽总预算。API分别映射503/502/504，异常不回显远端请求与key。

429：默认最多重试一次，遵守Retry-After；超过3秒或剩余期限不够时失败，不提前缩短等待。多个进程/其他程序仍可能共享IP配额；不要靠增加workers绕过限制。

配置为可选PUBMED_TOOL、PUBMED_EMAIL、PUBMED_API_KEY，部署时填写真实登记联系信息。不自动读取.env，不伪造email，不把key放查询字符串。基础公开小请求无需key；有key时本实现仍限3rps。

结果partial：查看missing_pmids与warnings，不能写成完整检索通过。全部metadata_only不代表“证据证明无效”。出版类型和更正/撤回关联只是官方标记，不自动作研究质量等级。

本阶段保留在任务对象中的规范化XML快照，回答保留已用来源的规范化XML、摘要/定位/hash与查询记录；不会自动持久化全部远端原始响应。需要长期存档应由调用方明确保存结果，不能将内存对象称作永久知识库。

Phase3真实模型/人工样例缺口仍保留。默认飞书local；API/CLI才有scope选择。完整真实LLM+在线问答若未运行须单列，不能用HTTP替身或PubMed小冒烟冒充。
