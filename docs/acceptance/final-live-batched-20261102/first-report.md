# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:43:13.872333+00:00；生成：2026-11-01T19:44:55.680179+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：cohort；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [2]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [3]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [4]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [5]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（有证据支持） data\_sources：This study analyzed data collected from the MIMIC IV database. [1]
- 推断（部分支持） design：该研究为基于MIMIC-IV数据库开发并外部验证的预测建模研究，外部验证纳入370例脓毒症患者。 [1]
  待验证：需核对全文方法部分确认训练队列规模与建模流程。
- 文献事实（有证据支持） evaluation\_metrics：Among the externally validated models, the AUC for XGBoost was the highest at 0.838, RF was 0.799, making it the second highest after XGBoost. [1]
- 文献事实（有证据支持） population：A total of 370 sepsis patients were included in the external validation, Among them, 61 patients developed AKI. [1]
- 文献事实（有证据支持） results：Among the externally validated models, the AUC for XGBoost was the highest at 0.838, RF was 0.799, making it the second highest after XGBoost. [1]
- 文献事实（有证据支持） sample\_size：A total of 370 sepsis patients were included in the external validation, Among them, 61 patients developed AKI. [1]
- 文献事实（有证据支持） technical\_methods：Among the externally validated models, the AUC for XGBoost was the highest at 0.838, RF was 0.799, making it the second highest after XGBoost. [1]
- 推断（有证据支持） design：该研究开发了双通道深度学习模型用于ICU患者AKI的连续风险预测。 [2]
  待验证：需核对全文确认数据来源、样本量与验证方式。
- 文献事实（有证据支持） outcomes：in this study, we developed dC-aKi, a dual-channel deep learning model for continuous aKi risk prediction in the iCu. [2]
- 文献事实（有证据支持） results：Model interpretation \(Figure \) identifies dynamic urine output as the key predictor. [2]
- 文献事实（有证据支持） technical\_methods：in this study, we developed dC-aKi, a dual-channel deep learning model for continuous aKi risk prediction in the iCu. [2]
- 文献事实（有证据支持） data\_sources：data from MIMIC. [3]
- 文献事实（有证据支持） design：\[8\] take such an approach, aiming 
to validate a previously derived machine learning model for 
the prediction of persistent severe AKI. [3]
- 文献事实（有证据支持） population：The two clinical scenarios ICU and cancer 
population in any situation \(active treatment up to follow-up\) 
differ in multiple aspects. [3]
- 文献事实（有证据支持） results：We find it very inter -
esting that a model derived in such a different cohort of 
patients can achieve such good performance on an external 
test cohort. [3]
- 推断（部分支持） design：该研究为多队列研究，结合机器学习与SHAP分析评估危重患者AKI风险因素。 [4]
  待验证：需核对全文确认队列数量与数据来源。
- 文献事实（有证据支持） population：In addition, SHAP analysis identified 17 key risk factors associated with AKI in critically ill patients, most of which have been widely recognized in clinical practice. [4]
- 文献事实（有证据支持） results：In addition, SHAP analysis identified 17 key risk factors associated with AKI in critically ill patients, most of which have been widely recognized in clinical practice. [4]
- 文献事实（有证据支持） technical\_methods：The variables representing AIP and AKI were selected based on the intersection of results from LASSO regression and the Boruta algorithm. [4]
- 文献事实（有证据支持） data\_sources：Multiparameter Intelligent Monitoring in Intensive Care Database IV \(MIMIC-IV\) is a large public relations database. [5]
- 推断（部分支持） design：该研究基于MIMIC数据库构建动态列线图模型，预测ICU肝硬化患者早期AKI发生。 [5]
  待验证：需核对全文确认建模方法与验证策略。
- 文献事实（有证据支持） population：However, there is no relevant research or clinical prediction model for the risk assessment of AKI within 7 days after admission in ICU patients with liver cirrhosis. [5]
- 文献事实（有证据支持） technical\_methods：MAP, WBC, TB, GCS, Cr, Alb, HR and PLT were included in this nomogram, making it an objective and simple-to-use tool to screen patients for AKI in a dynamic online manner. [5]
- 文献事实（有证据支持） time\_window：However, there is no relevant research or clinical prediction model for the risk assessment of AKI within 7 days after admission in ICU patients with liver cirrhosis. [5]
## 5. 与用户想法的相似性分析
- 推断（有证据支持） data：overlap；该研究使用公开的MIMIC-IV数据库。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；该研究比较了XGBoost、随机森林等机器学习模型。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） outcomes：overlap；结局为AKI发生，并以AUC等指标评估预测性能。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） population：partial\_overlap；该研究限定于早期血流动力学稳定的脓毒症患者，而非全部ICU患者。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；该研究同样以ICU患者AKI风险预测为目标。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；该研究采用双通道深度学习模型进行连续预测。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；结局为AKI风险预测。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；研究对象为ICU危重患者。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该研究同样针对ICU患者AKI风险预测。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） data：overlap；涉及MIMIC数据。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：partial\_overlap；涉及机器学习模型的验证而非开发。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：partial\_overlap；验证场景为普通ICU人群，但模型来源于肿瘤人群。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：partial\_overlap；该研究聚焦于已有AKI机器学习模型的外部验证，而非新建模。 [3]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：overlap；采用LASSO、Boruta与SHAP等机器学习方法。 [4]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；结局为AKI风险预测与风险因素识别。 [4]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；研究对象为危重患者。 [4]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；该研究同样应用机器学习进行ICU患者AKI预测。 [4]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） data：overlap；使用公开的MIMIC-IV数据库。 [5]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：partial\_overlap；采用列线图预测模型，与机器学习/深度学习不完全相同。 [5]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；结局为入院后7天内AKI发生风险。 [5]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：partial\_overlap；限定于ICU肝硬化患者，而非全部ICU患者。 [5]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） question：overlap；该研究同样预测ICU患者AKI风险。 [5]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（有证据支持） limitations：Given limitations in data availability, novel biomarkers and genetic polymorphisms were not included in the analysis. [1]
- 文献事实（有证据支持） limitations：these findings highlight the importance of aligning model requirements with local documentation practices. [2]
- 文献事实（有证据支持） limitations：However, the number of cases in these studies was small, and a short-term prediction model for AKI in critically ill patients with cirrhosis after admission to the ICU is lacking. [5]
- 推断（有证据支持） uncertain；可比性：两者均针对ICU患者AKI风险预测，但人群限定与方法不同。；一项使用MIMIC-IV的脓毒症患者并比较XGBoost等模型，另一项开发双通道深度学习连续预测模型，评估方式不同，难以直接比较性能。 [1] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（有证据支持） uncertain；可比性：两者均使用MIMIC数据库预测ICU患者AKI，但人群与方法不同。；一项针对脓毒症患者使用机器学习模型，另一项针对肝硬化患者使用列线图，人群与方法差异使性能不可直接比较。 [1] [5]
  待验证：复核两侧研究设计、人群与结局
- 推断（部分支持） 现有AKI预测研究多限定于特定亚人群（如脓毒症、肝硬化、肿瘤），面向全部ICU患者的通用模型证据仍需核实。；推理：多个研究针对特定亚人群建模，但已有综述性表述称不同临床场景均有预测模型，需核实通用性。；范围：ICU患者AKI风险预测的人群覆盖范围 [5] [5]
  待验证：需系统检索确认是否存在覆盖全部ICU人群的AKI预测模型。
- 推断（有证据支持） 部分研究受限于数据可得性，未纳入新型生物标志物，公开数据建模可能面临特征覆盖限制。；推理：该研究报告因数据可得性未纳入部分标志物，提示公开数据存在变量覆盖限制。；范围：公开ICU数据的变量覆盖与特征选择 [1]
  待验证：需核实目标公开数据库中可用变量是否满足建模需求。
- 推断（部分支持） 可行性（data；conditional）：公开ICU数据库（如MIMIC-IV）可用于AKI预测建模，但需确认数据使用权限与标注质量。；下一步核查：确认拟用公开ICU数据库的申请条件、变量覆盖范围与AKI结局标注方案。 [5]
  待验证：需核实目标公开数据库的访问申请流程、伦理/数据使用协议及AKI标签定义的一致性。
- 推断（部分支持） 可行性（methods；conditional）：已有研究采用XGBoost、随机森林及深度学习等方法进行AKI预测，可作为方法学参照。；下一步核查：复现一个已报道的基线模型（如XGBoost）并核对评估流程。 [1]
  待验证：需确认所选模型在目标数据上的可复现性与特征工程流程。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估本地GPU/CPU资源与训练数据规模是否匹配所选模型。 
- 推断（部分支持） 可行性（validation；conditional）：已有研究采用外部验证队列评估模型性能，提示需设计独立验证集。；下一步核查：确定训练/内部验证/外部验证的数据划分与评估指标。 [1]
  待验证：需确认是否可获得独立外部验证数据及留出评估方案。
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
局限：Analysis quote selection was reduced to the context budget; omitted sentences are not evidence of absent findings.
待调查：Study db50365c-545f-5f49-accb-59508e7e5630: not reported/unknown: comparison, effects, intervention, outcomes, quality\_signals, time\_window
待调查：Study d07d59e0-b848-55f4-bdb5-ad8c5e5a2fc8: not reported/unknown: comparison, data\_sources, effects, evaluation\_metrics, intervention, population, quality\_signals, sample\_size, time\_window
待调查：Study e5282ea0-735a-547f-b8a6-be41d460f29a: not reported/unknown: comparison, effects, evaluation\_metrics, intervention, limitations, outcomes, quality\_signals, sample\_size, technical\_methods, time\_window
待调查：Study 813570f1-5389-5fcd-a6ec-7ae13f49375f: not reported/unknown: comparison, data\_sources, effects, evaluation\_metrics, intervention, limitations, outcomes, quality\_signals, sample\_size, time\_window
待调查：Study 7dbbaee1-21bf-5fe7-94da-9789e1ccb660: not reported/unknown: comparison, effects, evaluation\_metrics, intervention, outcomes, quality\_signals, results, sample\_size
## 7. 可供考虑的研究方向
- 待验证假设（待核查） 可供进一步调查的方向：现有AKI预测研究多限定于特定亚人群（如脓毒症、肝硬化、肿瘤），面向全部ICU患者的通用模型证据仍需核实。 [5] [5]
  待验证：需系统检索确认是否存在覆盖全部ICU人群的AKI预测模型。
- 待验证假设（有证据支持） 可供进一步调查的方向：部分研究受限于数据可得性，未纳入新型生物标志物，公开数据建模可能面临特征覆盖限制。 [1]
  待验证：需核实目标公开数据库中可用变量是否满足建模需求。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
## 8. 可追溯文献引用及证据支持状态
[1] Machine learning model for predicting the risk of AKI in early hemodynamically stable sepsis patients: a study based on the MIMIC IV database；作者：Miao He、Xinran Li、Jiajing Wu、Luyao Huang、Nan Wang、Le Chen、Mingxin Jiang、Zhe Chen、Lin Wei、Haitao Zhang；日期：2026-05-26；期刊：Frontiers in Medicine
DOI：10.3389/fmed.2026.1846554
URL：https://openalex.org/W7162403943
证据范围：已获取并引用的全文段落
https://doi.org/10.3389/fmed.2026.1846554
[2] Development and validation of a dual-channel deep learning for continuous acute kidney injury prediction in critically ill patients；作者：Siyu Tang、Chaoqun Niu、Huan Jiang、Yunchao Ling、Zihao Zheng、Jingquan Liu、Run Zhang、Jun Hong、Xu Bai、Guoqing Zhang、Xianghong Yang；日期：2026-07-01；期刊：Renal Failure
DOI：10.1080/0886022x.2026.2690700
URL：https://openalex.org/W7166805379
证据范围：已获取并引用的全文段落
https://doi.org/10.1080/0886022x.2026.2690700
[3] Validation of a cancer population derived AKI machine learning algorithm in a general critical care scenario；作者：Lauren Abigail Scanlon、Catherine M. O’Hara、Matthew Barker-Hewitt、Jorge Barriuso；日期：2025-03-26；期刊：Clinical &amp; Translational Oncology
DOI：10.1007/s12094-025-03906-0
URL：https://openalex.org/W4408921566
证据范围：已获取并引用的全文段落
https://doi.org/10.1007/s12094-025-03906-0
[4] Atherogenic index of plasma and risk of acute kidney injury in critically ill patients: a multi-cohort study with machine learning and SHAP analysis；作者：De-Min Li、Fang Yu、Wei Xia、Meng-Han Jiang、Li-Juan Yang、Hai-Ying Yang、Sun-Jun Yin、Ping Wang、Rui Meng、Shu-Hua Cun、Han-Ni Yang、Pei-Ni Du、Y Wang、Gong‐Hao He；日期：2025-12-31；期刊：Renal Failure
DOI：10.1080/0886022x.2025.2611198
URL：https://openalex.org/W7124968102
证据范围：已获取并引用的全文段落
https://doi.org/10.1080/0886022x.2025.2611198
[5] A dynamic model to predict early occurrence of acute kidney injury in ICU hospitalized cirrhotic patients: a MIMIC database analysis；作者：Huilan Tu、Junwei Su、Kai Gong、Zhiwei Li、Xia Yu、Xianbin Xu、Yu Shi、Jifang Sheng；日期：2024-08-27；期刊：BMC Gastroenterology
DOI：10.1186/s12876-024-03369-7
URL：https://openalex.org/W4401905536
证据范围：已获取并引用的全文段落
https://doi.org/10.1186/s12876-024-03369-7
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。