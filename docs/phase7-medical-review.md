# Phase 7 真实验收医学复核准备材料

**尚未人工签署，不能作为医学质量通过结论。此次没有生成有效分析或报告；以下仅为真实检索文献清单与待审问题。**

来源：本次真实官方 PubMed 检索与再次 EFetch，2条想法、每条2篇，均仅摘要。原始文件位于 [.artifacts/p7-real-20261028](../.artifacts/p7-real-20261028/summary.json)。来源定位复验使用真实快照回放，不是新的在线端到端运行。

## blood-pressure

在无糖尿病的高心血管风险成人中，比较强化与标准降压目标的心血管获益和急性肾损伤风险。

显式检索式：`SPRINT intensive standard blood pressure randomized acute kidney injury`；不将此人工冻结检索式称为模型自主规划成果。

- PMID 26551272：A Randomized Trial of Intensive versus Standard Blood-Pressure Control.；hash `bb5cbe48cc62ef2d9b640af8da1217d1b0f3a350370e0aa4a44e285deefc9669`；摘要。
- PMID 34010531：Final Report of a Trial of Intensive versus Standard Blood-Pressure Control.；hash `ac5436a15977d26dd46c83bfba23e9afa392bcbb69404ee422d63e84d620da20`；摘要。

[完整元数据、原文区间和XML快照](../.artifacts/p7-real-20261028/blood-pressure-pubmed.json)

## sepsis

在成人脓毒症患者中，比较早期乳酸清除率与SOFA评分预测短期死亡风险的方法及局限。

显式检索式：`sepsis lactate clearance SOFA mortality cohort`；不将此人工冻结检索式称为模型自主规划成果。

- PMID 39011361：Associations of serum lactate and lactate clearance with delirium in the early stage of ICU: a retrospective cohort study of the MIMIC-IV database.；hash `b76d792384a40ee642078633a0516e232c47d09e5032920e07a51b1437efd678`；摘要。
- PMID 42196888：Prognostic Value of 48-Hour Biomarker Reassessment Beyond Admission SOFA for 28-Day Mortality in Sepsis.；hash `b2b3ec37286bf9b30e21af59c86e17b2210f88ee6bcbbbf02763d35bb274a478`；摘要。

[完整元数据、原文区间和XML快照](../.artifacts/p7-real-20261028/sepsis-pubmed.json)

## 人工复核项目（均待完成）

| 项目 | 要求 | 人工状态 |
| --- | --- | --- |
| 检索相关性 | 逐篇判断是否覆盖研究对象、比较方法、目标结局；特别检查脓毒症检索首篇标题涉及delirium，与死亡结局想法的关系 | 待审 |
| 方法抽取 | 对照摘要方法/结果原文，标注设计、数据来源、技术、指标、结局、局限；未报告与缺陷分开 | 无有效模型分析输出，待后续生成后审 |
| 相似性 | 逐维核对问题/对象/数据/方法/结局，不用标题或检索得分替代 | 无有效输出，待审 |
| 候选缺口 | 支持依据、反证、推理边界、待验证条件；不得以未命中判创新 | 无有效输出，待审 |
| 论断支持关系 | 冻结独立逐项标签，审核模型supported等建议；假设不升级为事实 | 未运行支持度审核，待审 |
| 真实可追溯性 | 对照文献PMID、XML哈希、摘要位置及最终报告引用；机器已做4篇位置/哈希校验，不等于医学签署 | 最终报告尚未生成 |

审查人：待填写；资质/角色：待填写；日期：待填写；逐项结论与理由：待填写。

不得由LLM填充人工签署或将本文件称为人工标注集。
