# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:44:55.886410+00:00；生成：2026-11-01T19:46:30.263415+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：systematic\_review；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
- 推断（有证据支持） 研究设计分类：systematic\_review；判定来源：text [2]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（有证据支持） design：et al 2020\[125\] Retrospective not reported ICU patients Asian Pacific KDIGO KDIGO not reported 10921 Wiersema, R. [1]
- 文献事实（有证据支持） evaluation\_metrics：et al 2019\[124\] 10 at ICU admission 7 days after ICU admission Probab ly Yes Probab ly No LR multivariate logistic regression AUC: 0.833 \(0.802-0.864\) calibration plot, H-L test: p=0.511Yes No Wang, Y. [1]
- 文献事实（有证据支持） outcomes：et al 2020\[126\] Retrospective 27 March 2015 to 22 July 2015 adult patients admitted to ICU Europe KDIGO KDIGO sCr at ICU admission 1003 414 Xie, Y. [1]
- 文献事实（部分支持） population：Prediction models of AKI in ICU \(n=21\) An, S. [1]
- 文献事实（有证据支持） sample\_size：et al 2019\[128\] Retrospective 2001 to 2012 ICU patients North America KDIGO KDIGO sCr on day 1 of ICU admission 23950 3954 V. [1]
- 文献事实（有证据支持） technical\_methods：et al 2020\[125\] at 24 hours after ICU admission within 48 hours after a given prediction time point during ICU admission, dynamically Probab ly No Probab ly Yes ML ensemble learning and time series model AUC: 0.806± 0.002 F1 score: 0.44 Yes No Wiersema, R. [1]
- 文献事实（有证据支持） data\_sources：Prediction models typically include clinical pre-
dictors at baseline and, to a lesser extent, repeated measures. [2]
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
- 推断（待核查） data：unknown；所给摘要片段未明确说明模型是否基于公开ICU数据库构建。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） methods：partial\_overlap；综述涵盖机器学习集成与时间序列模型，但也包含传统logistic回归，与用户偏重机器学习/深度学习不完全一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；综述专门汇总ICU人群的AKI预测模型，与用户关注的ICU患者人群重叠。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该综述聚焦ICU急性肾损伤风险预测模型，与用户预测AKI风险的问题方向一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；所给片段未说明纳入研究是否使用公开ICU临床数据。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；综述纳入机器学习模型并提及深度学习模型的出现，与用户方法方向一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） outcomes：overlap；综述以模型区分度与校准作为评价结局，与用户预测AKI风险的目标一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；综述指出模型多针对ICU人群开发，与用户ICU患者人群重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该综述系统评价AKI机器学习预测模型，与用户预测AKI风险的研究问题一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（有证据支持） limitations：Mostmodelswerenot
externally validated. [2]
- 文献事实（有证据支持） quality\_signals：Data pre-processing
Twelve studies \(26%\) did not specify whether missing data were
present or how they were treated,and five \(11%\) did not use any
imputationmethod. [2]
- 推断（部分支持） supports；可比性：两篇均为AKI风险预测模型的综述，一篇覆盖含传统回归在内的预测模型，另一篇专门聚焦机器学习模型，范围部分重叠。；两篇综述均涉及ICU人群AKI预测，且都报告机器学习方法的使用，方向相互支持；但纳入标准与方法学评价重点不同，不能直接合并结论。 [1] [1] [2] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（有证据支持） 现有AKI机器学习预测模型多缺乏外部验证，且校准报告较少，提示在公开ICU数据上开展带外部验证与校准评估的研究仍有空间。；推理：综述指出多数模型未外部验证，同时提到所有研究均报告区分度但校准少见，二者共同指向验证环节的薄弱点。；范围：ICU人群AKI机器学习预测模型的验证与校准报告 [2] [2]
  待验证：需检索更多原始研究确认外部验证与校准报告的实际比例，不能仅凭本综述推断研究空白。
- 推断（有证据支持） 缺失数据处理在AKI预测模型研究中报告不一致，部分研究未说明或未做插补，提示数据预处理规范是可探讨的方法学差异点。；推理：综述报告部分研究未说明缺失数据或未插补，而少数研究使用MICE，显示预处理做法存在差异。；范围：AKI机器学习预测模型的数据预处理与缺失值处理 [2] [2]
  待验证：需核对原始研究确认缺失处理对模型性能的影响，不能据此断言缺失处理决定性能。
- 文献事实（待核查） 可行性（data；unknown）：证据不足，条件待确认；下一步核查：需确认拟使用的公开ICU数据库的访问许可、AKI标签定义（如KDIGO）与缺失数据情况，并核对综述中报告的缺失处理做法。 
- 推断（有证据支持） 可行性（methods；conditional）：综述显示传统灵活机器学习方法（随机森林、梯度提升树）仍被广泛用于AKI预测，深度学习模型自2014年起出现。；下一步核查：在选定数据上复现一个传统机器学习基线并记录预处理与变量选择流程。 [2]
  待验证：需确认所选公开数据是否支持可复现的基线模型与特征工程流程。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：需评估所选模型规模与数据量对应的训练资源需求，所给证据未提供算力信息。 
- 文献事实（有证据支持） 可行性（validation；reported\_barrier）：Mostmodelswerenot
externally validated.；下一步核查：需规划内部验证与外部验证方案，并确认是否有独立队列或留出数据可用于评估。 [2]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
待调查：Study 186fe080-74df-524c-8652-a1f3e4c89ce3: not reported/unknown: comparison, data\_sources, effects, intervention, limitations, quality\_signals, results, time\_window
待调查：Study 346f40e2-fcd7-5023-bd38-c1df77f0aaa2: not reported/unknown: comparison, effects, intervention, outcomes, results, sample\_size, time\_window
## 7. 可供考虑的研究方向
- 待验证假设（部分支持） 可供进一步调查的方向：现有AKI机器学习预测模型多缺乏外部验证，且校准报告较少，提示在公开ICU数据上开展带外部验证与校准评估的研究仍有空间。 [2] [2]
  待验证：需检索更多原始研究确认外部验证与校准报告的实际比例，不能仅凭本综述推断研究空白。
- 待验证假设（部分支持） 可供进一步调查的方向：缺失数据处理在AKI预测模型研究中报告不一致，部分研究未说明或未做插补，提示数据预处理规范是可探讨的方法学差异点。 [2] [2]
  待验证：需核对原始研究确认缺失处理对模型性能的影响，不能据此断言缺失处理决定性能。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
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