# Docker恢复后真实验收结果（2026-10-29）

本轮根据“现在试一下”继续，未改生产代码、规则或预算；未重跑unit。之前两题均未执行，确认无actual-*.json后才启动。原镜像构建已可用，当前local镜像ID为82ee0f0b872284fa1641be94d9d334e0ce5c227f04cb388e9475d1a9ae71481d。

## 环境与真实路径

同一clinical-agent-e2e项目恢复postgres与应用CLI容器。应用加载当前只读src与已有本地embedding，调用command_runtime.open_research → ResearchService.answer，使用真实DeepSeek、真实PubMed、真实PostgreSQL治理查询；没有Mock或注入候选。在线scope不执行本地召回，不以本次结果证明多来源合并能力。

两题执行前后容器ID相同：api=2521e102156e，postgres=9c92ff7c8f34。Postgres healthy；api是CLI宿主、关闭HTTP健康检查，不能宣称API端点已验收。最终两容器running，保留开发复用，无额外项目或重复容器。原始证据retry-before.json/retry-after.json。

## 中文结果

工作流成功，9.26秒，2次真实LLM调用，ESearch+EFetch共2次HTTP尝试。计划保留广义肝脏肿瘤，没有强制HCC、影像模态或算法。research_intent=exploration，对代表研究发现的意图分类不够精确。

实际查询：

```text
("liver tumor" OR "liver neoplasm" OR "hepatic tumor" OR "hepatic neoplasm" OR "liver cancer") AND ("subregion segmentation" OR "subregion partitioning" OR "subregion division" OR "intratumoral subregion" OR "tumor subregion")
```

PubMed返回总计3条，顺序35576953、26819533、42321976；全部EFetch成功，无候选截断，全部进入证据并被引用。已知39752907、40601290、41058349均不在本次返回集合；不是获取失败、top_k或合并丢失。不代表这些论文不存在，也不证明其不匹配另一个更合适的查询。

真实querytranslation显示部分引号短语作为All Fields处理，另一些拆成subregion变体与partition/division词族；这提供了地理区域歧义的实际解释。不能将引号理解为严格语义概念约束，也不能把全部问题归结为OR/AND。完整解释及原始官方摘要/XML/hash保存在actual-zh.json。

3条均非肿瘤内部亚区直接研究：35576953为肝硬化病毒感染流行率及地区汇总，26819533为巴基斯坦HCV流行率/基因型，42321976为亚太MASH肝癌负担与地区差异。摘要核对支持回答对它们的判断。

实际回答识别“subregion”为地理区域，明确三篇不支持肿瘤内部划分，未冒称已有代表性方法或全文审查，并说明本次有限检索不能证明PubMed不存在相关研究。引用身份与摘要解释一致；未发现该回答中的实验结果编造。但它不能提供用户真正要求的代表论文，真实发现能力未通过本题验收。建议重建策略时提到限定影像/肿瘤类型不等于已经执行，也不应将这些可选条件强制加入通用逻辑。

正文claims没有UUID/hash/内部JSON，结构化返回仍保留chunk引用ID，这是预期审计结构，不算正文污染。

## 英文结果

一次真实模型调用，2.99秒，Provider返回usage；PicoPlanner报extraction_failed，尚未得到经验证的QueryPlan，无ESearch、EFetch或最终回答。不重复付费请求。

当前PicoPlanner统一包装异常，验收记录器只保留成功返回的计划和usage，未保存失败的原始提取JSON或内部验证详情。因此不能确定是source_span、映射原文、schema还是其他验证错误；不凭猜测改代码。本例证明英文真实路径仍有阻断性问题，不能声称跨语言一致性验收成功。

## 上下文、成本与结论

中文生成上下文14136字符，小于24000，未触发context_limit；这次全部3篇摘要均进入上下文，没有截断。英文未进入生成阶段。Provider报告合计input=7827、output=2085、total=9912 tokens（含缓存字段，详见summary.json）；调用总数3（中文2、英文1），PubMed HTTP总数2。未执行report，无反馈或元数据核验额外请求；不把本次answer计数推广为report上限。金额未知。

通过：真实容器CLI与治理数据库链路、DeepSeek调用、PubMed请求、来源快照和中文引用回答门禁、两题容器身份复用；中文回答对无关结果保持谨慎。

失败：中文未发现目标直接研究，英文提取失败；科研发现能力与跨语言一致性不通过。旧合成样例和1097unit通过不足以消除这些真实缺陷。

后续需要调查并修复英文提取校验原因、真实PubMed短语解释/同义概念覆盖和噪声候选处理。本轮仅记录，不为命中已知PMID调参，不加搜索轮次，不重试两个问题。
