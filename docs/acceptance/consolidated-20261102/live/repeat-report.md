# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T20:20:04.370420+00:00；生成：2026-11-01T20:21:01.948160+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：unknown；判定来源：unknown 
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [2]
  待验证：核对出版类型与研究设计原文
- 推断（部分支持） 研究设计分类：cohort；判定来源：text [3]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（有证据支持） data\_sources：Public ICU datasets were widely used. [1]
- 文献事实（有证据支持） design：This systematic review comprehensively evaluated the AI models for the prediction of AKI in the ICU. [1]
- 文献事实（有证据支持） evaluation\_metrics：Model performance was primarily evaluated using AUROC, while other metrics and calibration were less reported. [1]
- 推断（部分支持） population：该综述聚焦于ICU中急性肾损伤（AKI）预测的AI模型研究，提示目标人群为ICU危重患者。 [1]
  待验证：需核对综述纳入研究的具体ICU人群定义与纳入排除标准。
- 文献事实（有证据支持） results：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP. [1]
- 文献事实（有证据支持） technical\_methods：Across the 47 included studies, models including LR, RF, XGBoost, and SVM were the most commonly used. [1]
- 推断（部分支持） design：该研究为模型开发与外部验证研究，包含一个外部队列，提示采用多队列开发-验证设计。 [2]
  待验证：需核对开发队列与外部验证队列的具体来源、样本量与划分方式。
- 文献事实（有证据支持） outcomes：the 12-h weight-adjusted urine output \(uo\_rt\_12 h\) tops global importance with bidirectional impact: Reduced output increases aKi risk \(positive attribution\), while increased output lowers risk. [2]
- 文献事实（有证据支持） results：While dC-aKi demonstrated strong performance in the development and one external cohort, performance varied substantially across institutions-most notably in eiCu-CRd, where coarser data granularity limited discrimination. [2]
- 文献事实（有证据支持） technical\_methods：in this study, we developed dC-aKi, a dual-channel deep learning model for continuous aKi risk prediction in the iCu. [2]
- 文献事实（有证据支持） design：In the present study, comparative analyses between the optimal ML model and conventional scoring systems demonstrated the superior performance of the AIP-integrated model in both internal and external validation cohorts. [3]
- 文献事实（有证据支持） evaluation\_metrics：Compared to other models, XGBoost demonstrated relatively superior model fit performance, with an AUC of 0.8127, BS of 0.1757 \(Sensitivity: 0.7165, Specificity: 0.7605, Accuracy: 0.7394, F1 score: 0. [3]
- 文献事实（有证据支持） outcomes：In addition, SHAP analysis identified 17 key risk factors associated with AKI in critically ill patients, most of which have been widely recognized in clinical practice. [3]
- 推断（有证据支持） population：该研究以危重患者为对象预测AKI发生，提示目标人群为ICU/危重症人群。 [3]
  待验证：需核对研究纳入的ICU数据库来源与患者纳入标准。
- 文献事实（有证据支持） results：Compared to other models, XGBoost demonstrated relatively superior model fit performance, with an AUC of 0.8127, BS of 0.1757 \(Sensitivity: 0.7165, Specificity: 0.7605, Accuracy: 0.7394, F1 score: 0. [3]
- 文献事实（有证据支持） technical\_methods：The variables representing AIP and AKI were selected based on the intersection of results from LASSO regression and the Boruta algorithm. [3]
## 5. 与用户想法的相似性分析
- 推断（有证据支持） data：overlap；综述指出公共ICU数据集被广泛使用，与用户使用公开ICU临床数据的设想一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） methods：overlap；综述总结了LR、RF、XGBoost、SVM等常用模型，与用户机器学习/深度学习建模设想重叠。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；综述以AUROC等指标评价AKI预测模型性能，与用户关注AKI风险预测结果一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；综述针对ICU中AKI预测，人群为ICU危重患者，与用户ICU患者设定重叠。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该综述系统评价ICU中AKI预测的AI模型，与用户预测AKI风险的问题方向一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；研究采用双通道深度学习模型，与用户深度学习建模设想重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；研究以AKI风险预测性能为结局，与用户关注的风险预测结果一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；研究针对ICU患者进行AKI风险预测，与用户ICU患者设定重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该研究开发连续AKI风险预测模型，与用户预测AKI风险的问题直接重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；研究构建XGBoost、SVM、随机森林、ANN等多种ML模型，与用户机器学习建模设想重叠。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） outcomes：overlap；研究以AUC等指标评价AKI预测模型，与用户关注的风险预测结果一致。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；研究在危重患者中预测AKI发生，与用户ICU患者设定重叠。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该研究应用ML进行AKI预测，与用户预测AKI风险的问题重叠。 [3]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（有证据支持） limitations：Overall, although progress in modeling approaches is evident, limitations in generalizability, transparency, and clinical translation remain. [1]
- 文献事实（有证据支持） quality\_signals：The PROBAST assessment suggested a high risk of bias in most studies, especially in the analysis domain. [1]
- 文献事实（有证据支持） limitations：While dC-aKi demonstrated strong performance in the development and one external cohort, performance varied substantially across institutions-most notably in eiCu-CRd, where coarser data granularity limited discrimination. [2]
- 推断（部分支持） supports；可比性：两者均涉及ICU中AKI预测建模，综述总结方法学现状，原始研究提供深度学习实例。；综述指出深度学习等方法被使用且外部验证有限，双通道深度学习研究展示了开发与一个外部队列验证，二者在方法学方向上相互支持。 [1] [1] [2] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（有证据支持） supports；可比性：综述总结常用ML模型与特征选择方法，原始多队列研究使用LASSO/Boruta与多种ML模型。；综述指出LR、RF、XGBoost、SVM常用且LASSO为常见特征选择方法，多队列研究实际采用LASSO与Boruta并构建多种ML模型，二者一致。 [1] [1] [3] [3]
  待验证：复核两侧研究设计、人群与结局
- 推断（有证据支持） 现有ICU AKI预测研究外部验证比例有限，用户若计划开展类似研究，可考虑将外部验证作为设计重点。；推理：综述指出仅14项研究进行外部验证，而双通道深度学习研究已开展一个外部队列验证，说明外部验证并非完全空白但整体仍有限。；范围：ICU中AKI预测AI模型的外部验证现状 [1] [2]
  待验证：需核实用户可获得的独立外部验证数据来源与规模。
- 推断（有证据支持） 模型在不同机构间性能差异明显，数据粒度与本地记录实践可能影响可迁移性，用户研究需考虑跨机构泛化。；推理：双通道模型在外部队列性能下降，综述亦指出泛化性局限，二者一致提示跨机构泛化挑战。；范围：ICU AKI预测模型的跨机构泛化 [2] [1]
  待验证：需核实目标数据集间数据粒度与记录规范差异。
- 推断（有证据支持） 多数模型尚未进入临床整合，用户研究若定位为方法学探索，可关注可解释性与临床可用性而非部署。；推理：综述指出多数模型远离临床整合，同时认为实时动态模型有助于早期识别，提示研究价值与方法学定位需区分。；范围：ICU AKI预测模型的临床转化现状 [1] [1]
  待验证：需核实用户研究目标是否包含临床部署评估。
- 推断（部分支持） 可行性（data；conditional）：公开ICU数据集被广泛用于AKI预测建模，提示数据可得性存在先例；但用户具体可访问的数据集、使用许可与标注质量仍需核实。；下一步核查：列出候选公开ICU数据集并逐一核查访问许可、AKI标签定义与数据完整度。 [1]
  待验证：需确认拟用公开ICU数据集的具体名称、访问授权、AKI标签定义与缺失/标注质量。
- 推断（部分支持） 可行性（methods；conditional）：已有研究常用LR、RF、XGBoost、SVM等模型，方法上有可复现基线；但用户具体模型适配与基线复现仍需验证。；下一步核查：在选定数据集上复现一个已报道的基线模型并记录预处理与评估流程。 [1]
  待验证：需确认所选模型架构、特征工程流程与可复现基线设置。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估所选模型训练与调参所需的算力资源与成本，并确认可用硬件。 
- 文献事实（有证据支持） 可行性（validation；reported\_barrier）：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP.；下一步核查：确认是否可获得独立外部验证队列或留出数据以支持外部验证。 [1]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
局限：Analysis quote selection was reduced to the context budget; omitted sentences are not evidence of absent findings.
待调查：Study 549385ae-e657-5537-8459-c67ae9e4efe5: not reported/unknown: comparison, effects, intervention, outcomes, sample\_size, time\_window
待调查：Study d07d59e0-b848-55f4-bdb5-ad8c5e5a2fc8: not reported/unknown: comparison, data\_sources, effects, evaluation\_metrics, intervention, population, quality\_signals, sample\_size, time\_window
待调查：Study 813570f1-5389-5fcd-a6ec-7ae13f49375f: not reported/unknown: comparison, data\_sources, effects, intervention, limitations, quality\_signals, sample\_size, time\_window
## 7. 可供考虑的研究方向
- 待验证假设（部分支持） 可供进一步调查的方向：现有ICU AKI预测研究外部验证比例有限，用户若计划开展类似研究，可考虑将外部验证作为设计重点。 [1] [2]
  待验证：需核实用户可获得的独立外部验证数据来源与规模。
- 待验证假设（有证据支持） 可供进一步调查的方向：模型在不同机构间性能差异明显，数据粒度与本地记录实践可能影响可迁移性，用户研究需考虑跨机构泛化。 [2] [1]
  待验证：需核实目标数据集间数据粒度与记录规范差异。
- 待验证假设（有证据支持） 可供进一步调查的方向：多数模型尚未进入临床整合，用户研究若定位为方法学探索，可关注可解释性与临床可用性而非部署。 [1] [1]
  待验证：需核实用户研究目标是否包含临床部署评估。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
## 8. 可追溯文献引用及证据支持状态
[1] Artificial intelligence models for predicting acute kidney injury in the intensive care unit: a systematic review of modeling methods, data utilization, and clinical applicability；作者：Tongyue Shi、Yu Lin、Huiying Zhao、Guilan Kong；日期：2025-06-14；期刊：JAMIA Open
DOI：10.1093/jamiaopen/ooaf065
URL：https://openalex.org/W4411994860
证据范围：已获取并引用的全文段落
https://doi.org/10.1093/jamiaopen/ooaf065
[2] Development and validation of a dual-channel deep learning for continuous acute kidney injury prediction in critically ill patients；作者：Siyu Tang、Chaoqun Niu、Huan Jiang、Yunchao Ling、Zihao Zheng、Jingquan Liu、Run Zhang、Jun Hong、Xu Bai、Guoqing Zhang、Xianghong Yang；日期：2026-07-01；期刊：Renal Failure
DOI：10.1080/0886022x.2026.2690700
URL：https://openalex.org/W7166805379
证据范围：已获取并引用的全文段落
https://doi.org/10.1080/0886022x.2026.2690700
[3] Atherogenic index of plasma and risk of acute kidney injury in critically ill patients: a multi-cohort study with machine learning and SHAP analysis；作者：De-Min Li、Fang Yu、Wei Xia、Meng-Han Jiang、Li-Juan Yang、Hai-Ying Yang、Sun-Jun Yin、Ping Wang、Rui Meng、Shu-Hua Cun、Han-Ni Yang、Pei-Ni Du、Y Wang、Gong‐Hao He；日期：2025-12-31；期刊：Renal Failure
DOI：10.1080/0886022x.2025.2611198
URL：https://openalex.org/W7124968102
证据范围：已获取并引用的全文段落
https://doi.org/10.1080/0886022x.2025.2611198
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。