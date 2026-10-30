# Phase 4 P4-01 在线 PubMed 验收记录

日期：2026-10-28（Asia/Shanghai）。状态：**Phase 4 核心范围验收完成**：核心实现、目标离线测试、最终完整回归、官方接口小冒烟及学习材料齐备。Phase 3 真实模型/人工样例缺口保留，用户明确要求进入 Phase 4，本阶段未将旧缺口改为已通过。

## 本地基线与交付

按项目规则 → 当前进度 → Phase 4概要/相关PICO接口 → 研究/检索/引用/装配与XML映射/测试顺序核查。原有PubMed仅离线XML，本次先冻结 [P4-01 SPEC](specs/tasks/p4-01-pubmed-online.md)、编写目标测试，再实现和集中验收。原有未提交改动全部保留，没有重做架构。

新增 domain/pubmed.py（参数/记录/快照/检索追溯）、adapters/pubmed_online.py（官方HTTP请求、限流和期限）、application/pubmed.py（真实摘要到证据、来源合并）。pubmed_xml.py复用原映射，在线允许metadata_only，离线仍拒绝无摘要。没有新依赖、Schema、自动入库或Phase5能力。

扩展现有scope、未编码在线命中、ResearchService路由与领域引用：local沿用向量；online不调用本地向量检索；hybrid预留来源名额、PMID去重，不相加不可比较的分数。QueryPlan未指定显式query时保留原问题，未假造MeSH或宣称执行了所有医学约束。

CLI/API可选在线范围；飞书纯文本仍默认local，渲染器支持在线来源。正式装配和可选PUBMED_*配置同步至.env.example/Compose；无容器重建/部署。SourceMetadata可用实际PubMed HTTPS URI，不生成虚假本地路径。每个已用在线引用返回规范化snapshot_xml、SHA256、文本/定位和可信元数据；修改快照后完整DTO验证拒绝，便于后续核验。仅本次结果返回，不自动持久化到知识库。

## 集中测试与实际证据

解释器：正式 .venv/Scripts/python.exe / Python3.12.16。测试不是逐任务RED/GREEN，以下均为核心实现与教材齐备后的集中批次；未伪造RED。

| 范围 | 实际结果 |
| --- | --- |
| 首批目标 | `-I -m pytest tests/unit/test_pubmed_online.py tests/integration/test_pubmed_online.py -q`：31 passed /1 deselected，2.92秒；target.txt |
| 首次完整回归 | `-I -m pytest tests -q`：1122 passed /97 deselected /1既有SDK弃用警告，134.65秒；regression.txt |
| 期限/范围边界修复后的目标 | 33 passed /1 deselected，3.97秒；target-final.txt。修复解析也计入剩余期限、零count不允许带ID、在线超长渲染不误称仅本地 |
| 第二次默认回归 | 1124 passed /97 deselected /1既有SDK警告，134.48秒；regression-final.txt。之后补齐已用在线引用的XML快照交付，不将此轮当最终源码结果 |
| 快照链复验 | 33 passed /1 deselected，2.87秒；snapshot-target.txt，涵盖快照篡改拒绝 |
| 最终源码完整回归 | `-I -m pytest tests -q --basetemp=.artifacts/p4-01-20261028/delivery-regression-tmp -o cache_dir=.artifacts/p4-01-20261028/delivery-cache`：1124 passed /97 deselected /1既有SDK警告，147.31秒；delivery-regression.txt |
| 质量 | Ruff check通过；format 92文件已格式化；mypy src 44源文件通过；离线Demo返回metadata_only合法记录，无网络/模型 |

命令的完整公共参数使用本次专属目录，例如 `--basetemp=.artifacts/p4-01-20261028/target-tmp -o cache_dir=.artifacts/p4-01-20261028/cache`；最终源码回归为 `--basetemp=.artifacts/p4-01-20261028/delivery-regression-tmp -o cache_dir=.artifacts/p4-01-20261028/delivery-cache`。所有原始测试输出在该证据目录。默认排除真实模型/数据库/Redis/性能，不将97项排除计为通过。

12份相关文档54个本地链接和Markdown围栏核查通过，git diff --check通过。首轮质量检查的长行/导入与HttpUrl类型标注已修复并复验；没有放宽身份、时间、快照或医学来源断言。

## 真实官方接口

真实入口：`-I -m pytest tests/integration/test_pubmed_online.py -m external -q`，固定查询 `aspirin[Title] AND randomized controlled trial[Publication Type]`，最多2篇，正常ESearch+EFetch两请求。无需LLM、E5、数据库或付费模型。

普通受限环境首次1 failed /6 deselected，1.06秒，受控pubmed_failed；未当作正常零结果。获得网络执行权限后同入口 **1 passed /6 deselected，2.34秒**，一次pytest缓存目录权限警告，不影响行为断言。官方返回2篇摘要、total_count=2377、truncated=true、status=complete、warnings=[]；时间2026-10-27T17:47:29Z（上海时间2026-10-28）。当次PMID为[40961426](https://pubmed.ncbi.nlm.nih.gov/40961426/)与[40888737](https://pubmed.ncbi.nlm.nih.gov/40888737/)，只作为返回身份记录，不作治疗结论。

期限校验修复后最终官方入口再验 **1 passed /6 deselected，2.74秒**，关闭pytest缓存插件避免辅助缓存权限警告；live-final.txt。未调换查询或放宽实时断言，未固定持续变化的返回数量/标题。成功外部批次共两个小查询/各最多2篇（约4次成功HTTP请求）；另有首个受限环境失败尝试，0次LLM/付费请求。

完整JSON/XML证据位于 `.artifacts/p4-01-20261028/live-network-tmp/test_live_official_pubmed0/pubmed-live.json` 和 `live-final-tmp/test_live_official_pubmed0/pubmed-live.json`。网络验收进程创建的临时文件在普通沙箱身份下不可读，已通过同一获准执行身份只读核对前一份摘要；未修改全局ACL或删除用户数据。此限制不改变测试结果，后续读取需使用有权身份。

## 边界与未解决项

- 未执行真实LLM+在线PubMed完整问答或新的医学支持度人工审查；生成与图/入口/引用组合使用明确替身，不能当医学语义验收。Phase 1 人工审查、Phase 3 真实模型样例仍保留原状态。
- 速率门仅覆盖本进程；多个进程/主机和同IP其他工具不协调。部署仅允许一个启用在线检索实例，真实tool/contact登记由部署者完成。本次没有发送联系邮件。
- 保存本次规范化记录与已用引用，不自动持久化全部原始响应；无全文抓取、MeSH自动规划、Phase5融合排序、Phase8更新或性能压测。
- 不因本阶段接口通过声称检全、证据质量或结论支持度全部通过；不自动进入Phase5。

学习资料：[Phase 4六份教材与Demo](learning/phase-04/README.md)。
