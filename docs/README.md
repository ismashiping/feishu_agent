# 文档导航

适用范围：2026-10-28工作区。当前事实、契约、操作步骤、教材、历史证据分别维护；旧文中的“尚未/下一任务”不自动成为当前状态。

- [当前架构、工作流、数据与资源生命周期](current/architecture.md)
- [当前状态与开发计划](development-plan.md)：每项链接到原始验收，保留待审缺口
- [开发、运行、模型、数据库与部署](guides/README.md)
- [学习主题索引](learning/README.md)
- [全部文档逐文件清单](governance/inventory.md)、[治理方案](governance/plan.md)、[验证与结果](governance/README.md)

## 需求与设计决策

[总体契约](specs/00-project-overview.md)，[MVP](specs/01-mvp.md)，[异步体验](specs/02-async-experience.md)，[PICO](specs/03-pico.md)，[PubMed](specs/04-pubmed-search.md)，[混合检索](specs/05-hybrid-retrieval.md)，[分析](specs/06-evidence-analysis.md)，[报告](specs/07-citation-report.md)，[知识更新](specs/08-knowledge-update.md)，[评价](specs/09-evaluation.md)。

[详细任务目录](specs/tasks) 保留冻结范围、输入输出和验收场景；SPEC不是进度日志，任务完成程度查状态表。重要选择理由见 [技术调查](tech-stack.md)、[模型调用边界](specs/tasks/langchain-model-boundary.md)、[多角色路线及其历史计划](multi-agent-roadmap.md)，不重复建立第二套决策文档。

## 阶段验收与原始证据

[Phase0](phase0-acceptance.md)、[Phase1](phase1-acceptance.md)、[Phase3](phase3-acceptance.md)、[Phase4](phase4-acceptance.md)、[Phase5](phase5-acceptance.md)、[Phase6](phase6-acceptance.md)、[Phase7](phase7-acceptance.md)、[Phase8](phase8-acceptance.md)、[Phase9](phase9-acceptance.md)、[MA01](ma01-acceptance.md)、[MA02](ma02-acceptance.md)。

医学审查独立保留：[Phase1](phase1-medical-review.md)、[Phase7](phase7-medical-review.md)。[评价数据、模型原始响应及失败结果](../evaluation/README.md) 不因治理重新生成或覆盖。验收只证明记录中的版本、环境与范围，不能把排除/跳过或未签署标为通过。

## 调研与历史

[参考仓库分析](research/reference-repository-analysis.md)、[环境调查](research/environment-audit.md)、[选型实验](research/p0-03-validation.md)、[依赖调查数据](research/dependencies)。

[整理前README](archive/readme-before-governance.md)、[旧架构混合快照](archive/architecture-before-governance.md)、[完整开发时点日志](archive/development-plan-before-governance.md)、[2026-10-27旧文档审计](documentation-audit.md)。原文关键失败、技术取舍和未验证项保留，不据今天实现重写当时事实。

## 探索型问题理解修复

[增量SPEC](specs/tasks/exploratory-discovery.md) · [独立验收与学习说明](exploratory-discovery-acceptance.md)。
