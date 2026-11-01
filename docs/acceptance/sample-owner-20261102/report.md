# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:50:35.750558+00:00；生成：2026-11-01T19:50:55.695057+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：systematic\_review；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
- 推断（有证据支持） 研究设计分类：systematic\_review；判定来源：text [2]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（部分支持） design：Prediction models of AKI in ICU \(n=21\) An, S. [1]
- 文献事实（有证据支持） evaluation\_metrics：et al 2020\[125\] at 24 hours after ICU admission within 48 hours after a given prediction time point during ICU admission, dynamically Probab ly No Probab ly Yes ML ensemble learning and time series model AUC: 0.806± 0.002 F1 score: 0.44 Yes No Wiersema, R. [1]
- 文献事实（部分支持） outcomes：et al 2020\[126\] Retrospective 27 March 2015 to 22 July 2015 adult patients admitted to ICU Europe KDIGO KDIGO sCr at ICU admission 1003 414 Xie, Y. [1]
- 文献事实（有证据支持） population：et al 2020\[126\] Retrospective 27 March 2015 to 22 July 2015 adult patients admitted to ICU Europe KDIGO KDIGO sCr at ICU admission 1003 414 Xie, Y. [1]
- 文献事实（有证据支持） technical\_methods：et al 2020\[125\] at 24 hours after ICU admission within 48 hours after a given prediction time point during ICU admission, dynamically Probab ly No Probab ly Yes ML ensemble learning and time series model AUC: 0.806± 0.002 F1 score: 0.44 Yes No Wiersema, R. [1]
- 文献事实（有证据支持） data\_sources：Data pre-processing
Twelve studies \(26%\) did not specify whether missing data were
present or how they were treated,and five \(11%\) did not use any
imputationmethod. [2]
- 文献事实（有证据支持） design：We followed the Preferred
Reporting Items for Systematic Reviews and Meta-analyses
\(PRISMA\) guidelines \[31\]. [2]
- 文献事实（有证据支持） evaluation\_metrics：Althoughallstudiesprovidedmodeldiscrimination,equallyim-
portantmeasuresofcalibrationwererare. [2]
- 文献事实（有证据支持） population：Models were mostly developed
for the ICU population, followed by the general hospital and
\(cardiac\) surgery populations. [2]
- 文献事实（有证据支持） technical\_methods：Although deep-learning models
have emerged since 2014,more traditional,flexible ML methods
\(random forest and gradient-boosted trees\) are still widely used
to predict AKI. [2]
## 5. 与用户想法的相似性分析
- 推断（待核查） data：unknown；所给引文未明确说明数据是否来自公开ICU数据库。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） methods：partial\_overlap；综述涵盖机器学习集成与时间序列模型，也包含传统回归模型，与用户机器学习/深度学习设想部分重叠。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） population：overlap；综述纳入ICU成人患者，与用户关注的ICU患者人群重叠。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该综述聚焦ICU内AKI风险预测模型，与用户预测AKI风险的问题方向一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；所给引文未说明是否使用公开ICU数据集。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；综述涵盖深度学习及随机森林、梯度提升树等机器学习方法，与用户设想一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；综述指出模型多针对ICU人群，与用户ICU患者设定重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该综述系统评价AKI机器学习预测模型，与用户问题高度一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（有证据支持） limitations：Mostmodelswerenot
externally validated. [2]
- 推断（部分支持） supports；可比性：两篇均为AKI预测模型的综述，一篇覆盖更广的预测模型（含传统回归），一篇专门聚焦机器学习模型。；两者均报告ICU人群AKI预测模型研究，方法学结论方向一致，可相互补充。 [1] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（有证据支持） 已纳入的机器学习AKI预测研究普遍缺乏外部验证，用户方案需明确外部验证设计。；推理：综述指出多数模型未经外部验证，提示验证环节是可行性的关键约束。；范围：ICU AKI机器学习预测模型的验证设计 [2]
  待验证：需核实目标公开数据集是否可划分独立外部验证队列。
- 推断（有证据支持） 校准评估在已有研究中较少报告，用户方案应纳入校准指标。；推理：综述指出尽管所有研究提供区分度，校准指标罕见，提示评估维度存在缺口。；范围：AKI预测模型的评估指标选择 [2]
  待验证：需确认所选评估框架支持校准曲线与校准指标计算。
- 推断（有证据支持） 缺失数据处理与变量选择方法在已有研究中不一致，用户方案需预先规定处理策略。；推理：综述显示部分研究未说明缺失数据处理，方法学差异可能影响可比性。；范围：AKI预测建模的预处理与变量选择 [2]
  待验证：需核实目标数据集的缺失模式以选择合适插补方法。
- 推断（部分支持） 可行性（data；conditional）：已有研究使用ICU临床数据构建AKI预测模型，但所给证据未说明数据是否公开、获取权限与标注质量。；下一步核查：核查目标公开ICU数据库的数据使用协议与AKI标签（如KDIGO）可计算性。 [1]
  待验证：需确认拟用公开ICU数据集的具体来源、使用许可、缺失率与AKI标签定义。
- 推断（有证据支持） 可行性（methods；conditional）：综述显示传统机器学习方法（随机森林、梯度提升树）仍被广泛使用，深度学习自2014年起出现，方法选择需与数据规模匹配。；下一步核查：搭建逻辑回归与梯度提升树基线并复现文献报告的评估流程。 [2]
  待验证：需确认可复现的基线模型与预处理流程是否适配所选数据集。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估所选模型规模与数据量对应的训练资源需求，确认本地或云端算力是否足够。 
- 文献事实（有证据支持） 可行性（validation；reported\_barrier）：Mostmodelswerenot
externally validated.；下一步核查：规划内部交叉验证与独立外部队列验证，并预先确定校准评估方案。 [2]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
待调查：Study 186fe080-74df-524c-8652-a1f3e4c89ce3: not reported/unknown: comparison, data\_sources, effects, intervention, limitations, quality\_signals, results, sample\_size, time\_window
待调查：Study 346f40e2-fcd7-5023-bd38-c1df77f0aaa2: not reported/unknown: comparison, effects, intervention, outcomes, quality\_signals, results, sample\_size, time\_window
## 7. 可供考虑的研究方向
- 待验证假设（有证据支持） 可供进一步调查的方向：已纳入的机器学习AKI预测研究普遍缺乏外部验证，用户方案需明确外部验证设计。 [2]
  待验证：需核实目标公开数据集是否可划分独立外部验证队列。
- 待验证假设（有证据支持） 可供进一步调查的方向：校准评估在已有研究中较少报告，用户方案应纳入校准指标。 [2]
  待验证：需确认所选评估框架支持校准曲线与校准指标计算。
- 待验证假设（有证据支持） 可供进一步调查的方向：缺失数据处理与变量选择方法在已有研究中不一致，用户方案需预先规定处理策略。 [2]
  待验证：需核实目标数据集的缺失模式以选择合适插补方法。
## 8. 可追溯文献引用及证据支持状态
[1] Characterization of Risk Prediction Models for Acute Kidney Injury；作者：Yunlin Feng、Ying Wang、Min Jun、Lei Pu、Steven Darrow Weisbord、Rinaldo Bellomo、Daqing Hong、Martin Gallagher；日期：2023-05-15；期刊：JAMA Network Open
DOI：10.1001/jamanetworkopen.2023.13359
URL：https://openalex.org/W4376609544
证据范围：已获取并引用的全文段落
https://doi.org/10.1001/jamanetworkopen.2023.13359
[2] Machine learning models for predicting acute kidney injury: a systematic review and critical appraisal；作者：Iacopo Vagliano、Nicholas C Chesnaye、Jan Hendrik Leopold、Kitty J. Jager、Ameen Abu–Hanna、Martijn C. Schut；日期：2022-08-02；期刊：Clinical Kidney Journal
DOI：10.1093/ckj/sfac181
URL：https://openalex.org/W4289519525
证据范围：已获取并引用的全文段落
https://doi.org/10.1093/ckj/sfac181
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。