# 仓库治理审计与实施方案

适用范围：2026-10-28 工作区快照，包含已有未提交和未跟踪文件。先扫描后实施；不以代码存在推定验收。全量逐文件清单见 [inventory](inventory.md)，原始机器扫描保存在本地 `.artifacts/governance/before.json`。

## 审计结果

扫描373文件、154个Python文件、175份Markdown/TXT/RST/依赖输入文档；包括根目录规则、evaluation原始模型响应及结果。JSON、迁移、配置、脚本也纳入文件哈希清单，不冒充叙述性文档。未读取忽略的密钥、模型缓存、虚拟环境。内部链接/标题锚点初查0问题；外链未联网复验。

源码层级最深为 adapters/postgres，符合外部系统归属；application最大文件 research/report各337行，agents265行，workflow52行。编排、节点、路由集中在research，角色在agents，状态在workflow，职责可定位，无拆分收益证据。domain的静态导入未发现反向依赖application/adapters或LangGraph/SQLAlchemy/HTTPX。此结论是静态检查，不证明所有动态依赖均不存在。

本地retrieval与pubmed各处理不同来源；pubmed_xml复用本地和在线解析；ingestion、updates、online_updates分别负责普通导入、持久批次和在线发布，并非重复检索服务。postgres按存储、版本、治理、检索、运行账本、重建分开合理。Protocol位于消费者处，不新增ports或repository层。未发现可据此删除的孤立模块；未来边界全部保留。测试按unit/integration分层，test_agent_roles/feedback_agents、hybrid_retrieval、knowledge_versions等可对应能力；phase8_completion是冻结验收范围命名，改名收益低。

真实问题是根README长达300余行且混入早期执行日志；architecture混合设计与现状；development-plan反向追加历史且最新Phase9记录未统一呈现；PROJECT当前Phase5与源码/Phase9验收冲突；旧documentation-audit仍称当前Phase1。学习目录按阶段是规则约定和脚本稳定路径，属于组织风格，不应机械搬迁为主题目录。以主题索引解决查找问题。

## 推荐结构及移动映射

代码树、tests、alembic、scripts、evaluation保留。cli/api、command_runtime/api_runtime、feishu.main、pyproject脚本名、Docker/Compose命令均属稳定入口；不移动、不修改。迁移编号与历史不变。不新增依赖。

文档采用 current（当前事实）、guides（操作索引）、specs（现有契约）、learning（主题导航加原阶段材料）、research（原调查）、archive（原入口快照）、governance（审计证据）。验收原路径保留，以导航分类，不额外制造acceptance空目录。

| 原路径 | 处理/新路径 | 原因 |
| --- | --- | --- |
| README.md | 原文归档 archive/readme-before-governance.md；原路径改为简明入口 | 保存环境/历史命令及失败证据，减少重复 |
| docs/architecture.md | 原文归档 archive/architecture-before-governance.md；原路径兼容导航至 current/architecture.md | 唯一当前架构说明 |
| docs/development-plan.md | 原文归档 archive/development-plan-before-governance.md；原路径当前状态表和历史锚点兼容 | 分离当前状态与时点日志 |
| docs/documentation-audit.md | 原文保留，加历史适用说明 | 旧审计不再冒充当前 |
| PROJECT.md.txt / AGENTS.md.txt | 顶部当前阅读规则覆盖时点状态；保留原约定 | 避免重写历史路线 |
| 其余原文档 | 保留原路径，逐文件登记；导航集中引用 | 避免移动已修改/未跟踪文件与外部稳定链接 |

不合并不同阶段SPEC、医学复核与验收，不改写失败/跳过/未验收结果。不大规模重写高质量教程。重复的当前架构和进度由原入口指向权威文件；历史长文仅保留在明确标记的快照，不能用来判断今天状态。

## 批次与风险

1. 全量文件/AST/链接审计与本方案先落盘。
2. 建当前架构、状态、导航；归档三份旧入口，重定位相对链接并保留旧标题锚点；检查全仓链接。
3. 增加指南与学习主题导航、逐文档处理清单；检查规则、SPEC、evaluation和脚本引用。
4. 源码无需移动：保持公开导入、patch路径、包发现、启动契约；执行离线回归、入口/路由导入、构建、依赖方向和diff检查。

风险：快照命令依赖当时环境，不当作当前部署保证；原工作区已有大量未提交修改，不创建提交或重置。外部DB/Redis/模型/医学签署依赖不能由文档治理补验；本轮不自动操作业务库或调用付费模型。外部服务验收只保留既有证据并明确未复验。
