# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:31:19.196613+00:00；生成：2026-11-01T19:33:04.508904+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：cohort；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：text [2]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 推断（待核查） comparison：该研究将堆叠集成机器学习模型与既往基于逻辑回归、Cox比例风险模型等传统方法的AKI预测模型进行对比，认为传统方法可能过度简化非线性关系且易受多重共线性影响。 [1]
  待验证：需核对原文结果部分是否报告了与这些传统模型的直接性能比较数据。
- 文献事实（待核查） data\_sources：Therefore, this study used a large database to develop and validate a superior performing stacked ensemble machine learning predictive model. [1]
- 文献事实（待核查） design：Therefore, this study used a large database to develop and validate a superior performing stacked ensemble machine learning predictive model. [1]
- 文献事实（待核查） outcomes：The aim was to predict the occurrence of AKI during ICU hospitalisation in patients with AP complicated by sepsis, using key risk factors determined through feature selection. [1]
- 文献事实（待核查） population：The aim was to predict the occurrence of AKI during ICU hospitalisation in patients with AP complicated by sepsis, using key risk factors determined through feature selection. [1]
- 文献事实（待核查） results：Our model successfully predicted whether patients would experience AKI during their ICU stay. [1]
- 文献事实（待核查） technical\_methods：Therefore, this study used a large database to develop and validate a superior performing stacked ensemble machine learning predictive model. [1]
- 文献事实（待核查） data\_sources：RESUL TS
We combined and harmonized data for 334,812 ICU 
stays that occurred between 2003 and 2019. [2]
- 文献事实（待核查） design：At each repetition, we randomly 
held out 20% of each ICU dataset as test set and split 
remaining data into training \(64%\) and validation 
\(16%\) sets. [2]
- 文献事实（待核查） evaluation\_metrics：This model was then evaluated on the held-
out test set using the area under the receiver operating 
characteristic \(AUROC\), the area under the precision-
recall curve \(AUPRC\), sensitivity, and positive predic-
tive value \(PPV\). [2]
- 推断（待核查） outcomes：该研究以ICU住院期间AKI与脓毒症为预测目标之一，并采用AUROC、AUPRC等指标评估模型，提示其任务与用户设想的ICU AKI风险预测存在部分重叠。 [2]
  待验证：需核对原文是否将AKI作为独立预测结局及其标签定义细节。
- 文献事实（待核查） sample\_size：RESUL TS
We combined and harmonized data for 334,812 ICU 
stays that occurred between 2003 and 2019. [2]
- 文献事实（待核查） technical\_methods：We used a neural network consist-
ing of gated recurrent units \(29\) followed by a simple 
fully connected network for prediction. [2]
## 5. 与用户想法的相似性分析
- 推断（待核查） data：partial\_overlap；该研究使用大型数据库（MIMIC），与公开ICU临床数据方向一致，但具体数据源需核对。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：partial\_overlap；该研究采用堆叠集成机器学习模型，属于机器学习范畴，但未明确使用深度学习。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：overlap；结局均为ICU住院期间是否发生AKI。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：partial\_overlap；该研究限定为急性胰腺炎合并脓毒症的ICU患者，用户仅泛称患者，人群范围更宽。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；两者均以ICU患者AKI发生风险预测为核心问题。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：overlap；该研究整合多机构ICU数据，与公开ICU临床数据方向一致，具体公开性需核对。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：overlap；该研究使用GRU神经网络及TCN、Transformer等深度学习模型。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：partial\_overlap；该研究涉及AKI预测标签，但主要评估跨机构泛化性能而非单一AKI风险模型。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：partial\_overlap；该研究纳入多中心ICU住院记录，人群为ICU患者，与用户泛称患者部分重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：partial\_overlap；该研究关注ICU多机构数据下机器学习预测模型泛化性，涉及AKI与脓毒症预测，但核心问题偏向泛化性评估。 [2]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（待核查） limitations：However, there are issues such as small sample size and insufficient model accuracy. [1]
- 文献事实（待核查） limitations：Finally, 
because data quality among hospitals in eICU can be vari-
able \(8\), we excluded hospitals with no AKI or sepsis cases 
\(two \[1.0%\] hospitals for AKI and 80 \[38.5%\] for sepsis\). [2]
- 推断（待核查） uncertain；可比性：两项研究均涉及ICU患者AKI预测，但人群限定、数据规模与建模方法不同，直接性能比较受限。；前者聚焦急性胰腺炎合并脓毒症亚群并使用堆叠集成模型，后者关注多机构泛化性并使用GRU等深度学习模型，任务与评估重点不完全一致。 [1] [2]
  待验证：复核两侧研究设计、人群与结局
- 待验证假设（待核查） 现有AKI预测研究多聚焦特定亚群（如急性胰腺炎合并脓毒症）或泛化性评估，针对更广泛ICU人群的通用AKI风险预测仍可能缺乏充分验证。；推理：该研究自述在特定亚群中存在研究空白，提示更广人群的预测研究可能仍有空间，但仅为推断。；范围：ICU人群AKI风险预测研究现状 [1] [1]
  待验证：需系统检索确认是否存在覆盖广泛ICU人群的公开数据AKI预测研究。
- 待验证假设（待核查） 传统逻辑回归方法可能过度简化非线性关系并受多重共线性影响，深度学习模型在ICU AKI预测中的增益仍需对照验证。；推理：该研究指出传统方法局限，但未提供深度学习相对传统方法的系统比较证据。；范围：建模方法比较 [1] [1]
  待验证：需在相同数据与划分下比较传统模型与深度学习模型的性能差异。
- 待验证假设（待核查） 多机构ICU数据存在质量差异，可能影响模型泛化与外部验证结果。；推理：该研究因数据质量差异排除部分医院，提示数据异质性可能构成挑战。；范围：数据质量与泛化性 [2]
  待验证：需评估目标数据集中各机构数据完整性与AKI标签一致性。
- 推断（待核查） 可行性（data；conditional）：已有研究整合了334,812次ICU住院数据，提示公开ICU临床数据可用于AKI相关建模。；下一步核查：确认目标公开ICU数据库（如MIMIC/eICU）的获取许可与数据使用协议，并制定AKI标签与变量提取方案。 [2]
  待验证：需核实用户拟用数据集的访问权限、伦理审批、AKI标签定义与缺失值处理方案。
- 推断（待核查） 可行性（methods；conditional）：已有研究采用GRU神经网络及堆叠集成机器学习等方法构建ICU预测模型，方法上具备可复现基础。；下一步核查：搭建逻辑回归或梯度提升基线模型，并与深度学习模型在同一数据划分下比较。 [2]
  待验证：需确认用户团队是否具备时序数据处理与模型调参能力，以及是否建立可复现基线。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估本地或云端GPU资源能否支持在目标数据规模上训练GRU/Transformer模型。 
- 推断（待核查） 可行性（validation；conditional）：已有研究采用重复随机子抽样划分训练、验证与测试集，并使用AUROC、AUPRC等指标评估。；下一步核查：设计训练/验证/测试划分与外部验证集，预先注册主要评价指标。 [2]
  待验证：需确认用户是否具备独立外部验证数据及预先设定的评估方案。
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
待调查：Study e815bd5b-b7c6-5ff5-ac73-1a5b124add65: not reported/unknown: effects, evaluation\_metrics, intervention, quality\_signals, sample\_size, time\_window
待调查：Study a8b3b9b1-5d1c-5b61-9171-fb690d1ea6a2: not reported/unknown: comparison, effects, intervention, population, quality\_signals, results, time\_window
## 7. 可供考虑的研究方向
- 待验证假设（待核查） 可供进一步调查的方向：现有AKI预测研究多聚焦特定亚群（如急性胰腺炎合并脓毒症）或泛化性评估，针对更广泛ICU人群的通用AKI风险预测仍可能缺乏充分验证。 [1] [1]
  待验证：需系统检索确认是否存在覆盖广泛ICU人群的公开数据AKI预测研究。
- 待验证假设（待核查） 可供进一步调查的方向：传统逻辑回归方法可能过度简化非线性关系并受多重共线性影响，深度学习模型在ICU AKI预测中的增益仍需对照验证。 [1] [1]
  待验证：需在相同数据与划分下比较传统模型与深度学习模型的性能差异。
- 待验证假设（待核查） 可供进一步调查的方向：多机构ICU数据存在质量差异，可能影响模型泛化与外部验证结果。 [2]
  待验证：需评估目标数据集中各机构数据完整性与AKI标签一致性。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
## 8. 可追溯文献引用及证据支持状态
[1] Predicting the risk of acute kidney injury in patients with acute pancreatitis complicated by sepsis using a stacked ensemble machine learning model: a retrospective study based on the MIMIC database；作者：FuYuan Li、Zhanjin Wang、Ruiling Bian、Zhangtuo Xue、Junjie Cai、Ying Zhou、Zhan Wang；日期：2025-02-01；期刊：BMJ Open
DOI：10.1136/bmjopen-2024-087427
URL：https://openalex.org/W4407953913
证据范围：已获取并引用的全文段落
https://doi.org/10.1136/bmjopen-2024-087427
[2] The Impact of Multi-Institution Datasets on the Generalizability of Machine Learning Prediction Models in the ICU；作者：Patrick Rockenschaub、Adam Hilbert、Tabea Kossen、Paul Elbers、Falk von Dincklage、Vince I. Madai、Dietmar Frey；日期：2024-07-03；期刊：Critical Care Medicine
DOI：10.1097/ccm.0000000000006359
URL：https://openalex.org/W4400283511
证据范围：已获取并引用的全文段落
https://doi.org/10.1097/ccm.0000000000006359
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。
支持度审核批次不可用或响应无效，未审核条目保持 uncertain。