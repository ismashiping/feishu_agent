# 最终验收（2026-10-29）

本轮仅新增验收资料，未修改生产代码、配置或既有测试。未清理备份、容器、镜像、卷或工作区。参考第一阶段调查、第二阶段SPEC与quality-runs/acceptance.md。

## 全量unit

实际命令：`.\.venv\Scripts\python.exe -m pytest tests/unit -q --basetemp=.pytest_final_acceptance --tb=short`。
结果：1097 passed，0 failed，0 skipped，0 errors，1第三方protobuf弃用警告，96.97秒。原始日志unit.txt。遵循现有pytest默认marker配置，数据库/外部服务集成不在本次unit范围。没有更改断言或跳过失败项。

## Docker归因与复用治理

初次沙箱读取Docker配置及engine pipe拒绝访问，随后只读提升检查成功。测试前后容器均0，最终身份列表docker-after.txt为空。本轮创建0、复用0、留下重复容器0，未执行up/run/down/build/prune。

实际历史证据：docs/archive/development-plan-before-governance.md:917/959/1012/1087/1135分别记录clinical-agent-p106/p107/p108/p110/p111-20261027独立Compose项目、独立测试数据库与随机密码，验收后只停止本次容器、不删除卷。当前对应命名卷仍存在（docker-volumes.txt）。这是已记录的多套资源来源；不是pytest每次自动创建的证据。检索tests/scripts/.github未发现docker run、compose run或Testcontainers启动钩子；tests/unit/test_feishu_deployment.py仅读取配置做断言。Compose本身无顶层name，历史命令-p覆盖项目名。

镜像仍包含clinical-literature-agent、pgvector、redis等；网络仅bridge/host/none。未读取Docker凭据内容。未来确需数据库时采用已有docs/postgres.md固定`-p clinical-agent-local`与`up -d --wait postgres`，只启动必要服务，复用已有卷前先确认对应密码、数据库及显式测试reset隔离授权，不能把生产库当测试库。避免按验收阶段生成新项目名。不将现有卷或密码配置改写来强行复用。本轮无需Docker，未实际验证数据库健康或复用启动。

## 真实流程和独立文献核验

live_check.py只检查现有环境/本地.env设置，不写环境配置，不输出凭据。LLMSettings不可用或无效，故两种语言均未调用模型、未执行ESearch或生成回答；见live.json。不能提供实际英文查询、querytranslation、总匹配数或最终引用，全部not_executed/unknown。没有用人工查询冒充真实QueryPlan。没有重复试错。

通过现有open_pubmed/RequestGate/fetch_metadata一次独立批量取得三篇官方记录，完整摘要/XML/hash保存在independent-pmids.json。这不是本次检索发现的候选，也未插入证据集合。

摘要级人工内容核对：
- PMID 39752907：HCC、CT、Otsu阈值划分4个habitats；232例、多中心回顾性队列，研究预后和免疫状态。是肝脏肿瘤内部亚区研究实例，但不能代表所有肝脏肿瘤类型。
- PMID 40601290：HCC、Gd-EOB-DTPA增强MRI，GMM聚类，轮廓系数选择3个亚区；187例，研究增殖型HCC预测。不可误写为Otsu或CT研究。
- PMID 41058349：不可切除HCC、增强CT体素影像组学与K-means，200例接受联合治疗，研究疗效与生存预测。摘要未提供聚类亚区数量，不应补造。

三篇均与主题直接相关，方法不同。仅核对摘要，未审查全文。其相关性不证明自然检索能在有限ESearch中发现它们。没有实际Agent回答，故引用支持、代表性覆盖、跨疾病错误归属、幻觉及真实科研准确性验收均未完成。

## 上下文与预算

使用三篇真实摘要作独立离线尺寸测量（不是生产候选）：当前GenerationInput为10372字符，同指令去掉新增title/PMID及空plan/provenance字段为9771，元数据增量601；均低于24000。见context.json。真实QueryPlan/provenance未取得，不能将这个差值当成完整生产开销；没有测模型实际token数。

源码application/research.py:205超过24000时直接context_limit失败，不做证据截断，也没有按相关性压缩。故不存在“超限时优先保留关键证据”的已实现保证；接近边界的旧上下文可能因新增元数据而失败。本轮未复现真实请求因此不修改生产逻辑、不扩大预算。

本轮生产模型调用0，ESearch0，独立EFetch一次批量（未单独记录底层重试计数，不能断言HTTP尝试恰好1）。预算常量未改。全量unit覆盖现有请求门、超时及反馈测试；report反馈可重入Scout，元数据核验也发请求，单search最多8次不等于report总计8次。未执行真实report，累计真实调用数、token费用与deadline端到端表现未验证。

## 结论

通过：修复后完整unit回归；本轮pytest不创建Docker容器；历史重复资源原因定位；三篇独立真实摘要相关性及方法核对；该快照样本未超上下文限制。
有限证据：上一轮合成候选选择改善，不升级为真实召回或跨疾病泛化结论。
未通过完整最终科研验收：缺少可用LLM设置，真实中英文规划/检索/回答仍未执行。当前关键边界仍有旧无组计划保守降级、词面选择局限、全流程累计预算未实测、上下文超限直接失败、本地chunk审计不完整。所有非阻塞建议仅记录。
