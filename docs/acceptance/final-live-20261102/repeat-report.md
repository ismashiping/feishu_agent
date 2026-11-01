# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:33:04.610611+00:00；生成：2026-11-01T19:34:19.509577+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：cohort；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [2]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：systematic\_review；判定来源：text [3]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（待核查） design：in this study, we developed dC-aKi, a dual-channel deep learning model for continuous aKi risk prediction in the iCu. [1]
- 文献事实（待核查） outcomes：in this study, we developed dC-aKi, a dual-channel deep learning model for continuous aKi risk prediction in the iCu. [1]
- 文献事实（待核查） population：in this study, we developed dC-aKi, a dual-channel deep learning model for continuous aKi risk prediction in the iCu. [1]
- 文献事实（待核查） technical\_methods：in contrast, deep learning models can automatically learn features from high-dimensional EHR data, improving predictive accuracy. [1]
- 文献事实（待核查） design：In the present study, comparative analyses between the optimal ML model and conventional scoring systems demonstrated the superior performance of the AIP-integrated model in both internal and external validation cohorts. [2]
- 文献事实（待核查） evaluation\_metrics：Compared to other models, XGBoost demonstrated relatively superior model fit performance, with an AUC of 0.8127, BS of 0.1757 \(Sensitivity: 0.7165, Specificity: 0.7605, Accuracy: 0.7394, F1 score: 0. [2]
- 文献事实（待核查） outcomes：Therefore, these findings support AIP as a complementary metabolic biomarker for AKI risk assessment and reinforce its clinical utility in critically ill patients. [2]
- 文献事实（待核查） population：We constructed 13 models to predict AKI occurrence in critically ill patients, including XGBoost, Adaboost, CatBoost, Bagging, SVM, KNN, Random Forest and ANN, as shown in Figure . [2]
- 文献事实（待核查） results：Compared to other models, XGBoost demonstrated relatively superior model fit performance, with an AUC of 0.8127, BS of 0.1757 \(Sensitivity: 0.7165, Specificity: 0.7605, Accuracy: 0.7394, F1 score: 0. [2]
- 文献事实（待核查） technical\_methods：We constructed 13 models to predict AKI occurrence in critically ill patients, including XGBoost, Adaboost, CatBoost, Bagging, SVM, KNN, Random Forest and ANN, as shown in Figure . [2]
- 文献事实（待核查） data\_sources：Public ICU datasets were widely used. [3]
- 文献事实（待核查） design：Across the 47 included studies, models including LR, RF, XGBoost, and SVM were the most commonly used. [3]
- 文献事实（待核查） evaluation\_metrics：Model performance was primarily evaluated using AUROC, while other metrics and calibration were less reported. [3]
- 文献事实（待核查） results：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP. [3]
- 文献事实（待核查） technical\_methods：Across the 47 included studies, models including LR, RF, XGBoost, and SVM were the most commonly used. [3]
## 5. 与用户想法的相似性分析
- 推断（待核查） data：unknown；所给证据未明确说明是否使用公开ICU数据集。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：partial\_overlap；该研究采用深度学习，属于想法中机器学习/深度学习范畴，但具体为双通道连续预测架构。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：overlap；该研究人群为ICU患者，与想法中的患者群体一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；两者均以ICU患者AKI风险预测为核心问题。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；所给证据未明确说明数据是否来自公开ICU数据库。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：partial\_overlap；该研究使用多种传统机器学习模型，属于想法中机器学习范畴，但未突出深度学习。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：overlap；研究人群为危重患者，与想法一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；该研究同样进行ICU患者AKI预测建模。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：overlap；综述指出公开ICU数据集被广泛使用，与想法数据来源一致。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：overlap；综述总结了LR、RF、XGBoost、SVM等机器学习模型，覆盖想法中的方法范畴。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：overlap；综述聚焦ICU患者AKI预测。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；该综述系统评估ICU中AKI预测的AI模型，与想法问题一致。 [3]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（待核查） limitations：While dC-aKi demonstrated strong performance in the development and one external cohort, performance varied substantially across institutions-most notably in eiCu-CRd, where coarser data granularity limited discrimination. [1]
- 文献事实（待核查） limitations：Overall, although progress in modeling approaches is evident, limitations in generalizability, transparency, and clinical translation remain. [3]
- 文献事实（待核查） quality\_signals：The PROBAST assessment suggested a high risk of bias in most studies, especially in the analysis domain. [3]
- 推断（待核查） uncertain；可比性：两者均针对ICU患者AKI预测，但方法路线不同（深度学习连续预测 vs 传统机器学习加生物标志物）。；一项采用双通道深度学习，另一项采用多种传统机器学习模型并整合AIP，直接性能比较受数据与任务定义差异限制。 [1] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（待核查） supports；可比性：综述总结了ICU AKI预测的AI模型方法，涵盖深度学习路线。；综述指出AI模型在处理复杂ICU数据与时间动态方面具有优势，与深度学习研究的方向一致。 [3] [1]
  待验证：复核两侧研究设计、人群与结局
- 推断（待核查） supports；可比性：综述统计了常用模型类型，该研究使用XGBoost等模型。；综述指出LR、RF、XGBoost、SVM为最常用模型，与该研究采用XGBoost等模型一致。 [3] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（待核查） 现有ICU AKI预测研究外部验证比例有限，可探索更充分的验证设计。；推理：综述指出仅14项研究进行外部验证，提示验证不足，但已有研究也报告了泛化性局限。；范围：ICU AKI预测模型的验证设计 [3] [3]
  待验证：需核实该综述纳入研究的验证方式分类是否完整。
- 推断（待核查） 模型性能多以AUROC为主，校准与其他指标报告较少，可关注更全面的评估。；推理：综述指出评估主要用AUROC，其他指标与校准报告较少。；范围：AKI预测模型的评估指标 [3]
  待验证：需核实综述中指标报告的统计口径。
- 推断（待核查） 多数模型尚未进入临床整合，可探索面向实际工作流的验证。；推理：综述指出多数模型远离临床整合，但已有研究提供了网页计算器等工具。；范围：AKI预测模型的临床转化 [3] [3]
  待验证：需核实综述对临床转化的具体判定标准。
- 推断（待核查） 可行性（data；conditional）：公开ICU数据集被广泛用于AKI预测研究，但具体数据访问权限与标注质量需自行核实。；下一步核查：核查候选公开ICU数据库的数据使用协议与AKI标签可得性。 [3]
  待验证：需确认目标公开ICU数据集的使用许可、AKI标签定义与缺失情况。
- 推断（待核查） 可行性（methods；conditional）：已有研究常用LR、RF、XGBoost、SVM等模型，可作为可复现基线。；下一步核查：复现一个已报道的基线模型并核对评估流程。 [3]
  待验证：需确认所选基线的预处理流程与超参数设置可复现。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估本地或云端算力是否满足所选模型训练需求。 
- 文献事实（待核查） 可行性（validation；reported\_barrier）：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP.；下一步核查：确认是否可获得独立外部验证队列或留出验证方案。 [3]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
局限：Analysis quote selection was reduced to the context budget; omitted sentences are not evidence of absent findings.
待调查：Study d07d59e0-b848-55f4-bdb5-ad8c5e5a2fc8: not reported/unknown: comparison, data\_sources, effects, evaluation\_metrics, intervention, quality\_signals, results, sample\_size, time\_window
待调查：Study 813570f1-5389-5fcd-a6ec-7ae13f49375f: not reported/unknown: comparison, data\_sources, effects, intervention, limitations, quality\_signals, sample\_size, time\_window
待调查：Study 549385ae-e657-5537-8459-c67ae9e4efe5: not reported/unknown: comparison, effects, intervention, outcomes, population, sample\_size, time\_window
## 7. 可供考虑的研究方向
- 待验证假设（待核查） 可供进一步调查的方向：现有ICU AKI预测研究外部验证比例有限，可探索更充分的验证设计。 [3] [3]
  待验证：需核实该综述纳入研究的验证方式分类是否完整。
- 待验证假设（待核查） 可供进一步调查的方向：模型性能多以AUROC为主，校准与其他指标报告较少，可关注更全面的评估。 [3]
  待验证：需核实综述中指标报告的统计口径。
- 待验证假设（待核查） 可供进一步调查的方向：多数模型尚未进入临床整合，可探索面向实际工作流的验证。 [3] [3]
  待验证：需核实综述对临床转化的具体判定标准。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
## 8. 可追溯文献引用及证据支持状态
[1] Development and validation of a dual-channel deep learning for continuous acute kidney injury prediction in critically ill patients；作者：Siyu Tang、Chaoqun Niu、Huan Jiang、Yunchao Ling、Zihao Zheng、Jingquan Liu、Run Zhang、Jun Hong、Xu Bai、Guoqing Zhang、Xianghong Yang；日期：2026-07-01；期刊：Renal Failure
DOI：10.1080/0886022x.2026.2690700
URL：https://openalex.org/W7166805379
证据范围：已获取并引用的全文段落
https://doi.org/10.1080/0886022x.2026.2690700
[2] Atherogenic index of plasma and risk of acute kidney injury in critically ill patients: a multi-cohort study with machine learning and SHAP analysis；作者：De-Min Li、Fang Yu、Wei Xia、Meng-Han Jiang、Li-Juan Yang、Hai-Ying Yang、Sun-Jun Yin、Ping Wang、Rui Meng、Shu-Hua Cun、Han-Ni Yang、Pei-Ni Du、Y Wang、Gong‐Hao He；日期：2025-12-31；期刊：Renal Failure
DOI：10.1080/0886022x.2025.2611198
URL：https://openalex.org/W7124968102
证据范围：已获取并引用的全文段落
https://doi.org/10.1080/0886022x.2025.2611198
[3] Artificial intelligence models for predicting acute kidney injury in the intensive care unit: a systematic review of modeling methods, data utilization, and clinical applicability；作者：Tongyue Shi、Yu Lin、Huiying Zhao、Guilan Kong；日期：2025-06-14；期刊：JAMIA Open
DOI：10.1093/jamiaopen/ooaf065
URL：https://openalex.org/W4411994860
证据范围：已获取并引用的全文段落
https://doi.org/10.1093/jamiaopen/ooaf065
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。
支持度审核批次不可用或响应无效，未审核条目保持 uncertain。