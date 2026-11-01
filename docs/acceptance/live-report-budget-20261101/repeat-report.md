# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T12:04:36.672639+00:00；生成：2026-11-01T12:05:45.227468+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（待核查） 研究设计分类：systematic\_review；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
- 推断（待核查） 研究设计分类：cohort；判定来源：model\_inference [2]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 推断（待核查） data\_sources：该综述纳入的模型多基于 ICU 人群开发，提示公开 ICU 临床数据可能是相关研究常见的数据来源，但综述摘要未明确列出具体数据库名称。 [1]
  待验证：需查阅综述全文确认纳入研究实际使用的数据库（如 MIMIC、eICU）及数据获取与使用许可。
- 文献事实（待核查） design：We followed the Preferred
Reporting Items for Systematic Reviews and Meta-analyses
\(PRISMA\) guidelines \[31\]. [1]
- 文献事实（待核查） evaluation\_metrics：Althoughallstudiesprovidedmodeldiscrimination,equallyim-
portantmeasuresofcalibrationwererare. [1]
- 文献事实（待核查） outcomes：Study inclusion
We included studies that \(i\) developed or validated prediction
models for AKI and \(ii\) used ML models. [1]
- 文献事实（待核查） population：Models were mostly developed
for the ICU population, followed by the general hospital and
\(cardiac\) surgery populations. [1]
- 文献事实（待核查） technical\_methods：Although deep-learning models
have emerged since 2014,more traditional,flexible ML methods
\(random forest and gradient-boosted trees\) are still widely used
to predict AKI. [1]
- 推断（待核查） data\_sources：该研究以 ICU 患者每小时尿量序列作为模型输入，提示其数据来源为 ICU 床旁连续监测数据，但摘要未说明是否为公开数据库。 [2]
  待验证：需查阅全文确认数据来源、样本量及是否使用公开 ICU 数据库。
- 文献事实（待核查） evaluation\_metrics：Here, two methods were used and compared: the deep learning model obtained the highest sensitivity and specificity of 82% with an AUC of 0.89. [2]
- 文献事实（待核查） intervention：Our study applies a machine learning method to the determination of the risk of AKI development considering urine output, and consequently evaluating the algorithm to define an electronic alert. [2]
- 文献事实（待核查） outcomes：The output of this model corresponds to the probability of developing AKI stage 2/3 starting from the sixth hour from prediction onwards. [2]
- 文献事实（待核查） population：Sequences of 12 h of hourly urine output recordings were used as input of our deep learning model. [2]
- 文献事实（待核查） results：Here, two methods were used and compared: the deep learning model obtained the highest sensitivity and specificity of 82% with an AUC of 0.89. [2]
- 文献事实（待核查） technical\_methods：Sequences of 12 h of hourly urine output recordings were used as input of our deep learning model. [2]
- 文献事实（待核查） time\_window：The output of this model corresponds to the probability of developing AKI stage 2/3 starting from the sixth hour from prediction onwards. [2]
## 5. 与用户想法的相似性分析
- 推断（待核查） data：unknown；Not reported in the supplied evidence. 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：overlap；综述讨论传统机器学习与深度学习模型用于 AKI 预测，与用户提出的方法方向重叠。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：overlap；综述关注 AKI 预测模型的开发与验证，与用户预测 AKI 风险的目标一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：partial\_overlap；综述指出模型多针对 ICU 人群开发，与用户关注的 ICU 患者部分重叠，但综述也涵盖普通住院和手术人群。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；该综述纳入开发或验证 AKI 预测模型并使用机器学习模型的研究，与用户关注的问题方向一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） data：unknown；摘要仅说明使用 ICU 每小时尿量序列，未说明是否为公开 ICU 数据库。 
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） methods：partial\_overlap；研究使用深度学习模型并与逻辑回归比较，与用户方法方向部分重叠，但输入仅限尿量序列。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） outcomes：partial\_overlap；研究预测 AKI 2/3 期发生概率，与用户预测 AKI 风险部分重叠，但限定为重度 AKI 和特定时间窗。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） population：overlap；研究基于 ICU 住院患者的每小时尿量记录，与用户关注的 ICU 患者重叠。 [2]
  待验证：结合用户原始约束及文献复核相似性
- 推断（待核查） question：overlap；该研究应用机器学习方法评估 ICU 患者发生 AKI 的风险，与用户问题方向一致。 [2]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（待核查） limitations：Mostmodelswerenot
externally validated. [1]
- 推断（待核查） supports；可比性：两者均涉及 AKI 预测与机器学习方法，但一篇为系统综述，另一篇为单一深度学习模型研究，证据层级不同。；综述指出深度学习模型已用于 AKI 预测且传统机器学习仍广泛使用，单一研究则报告深度学习模型在尿量序列上的预测表现，方向一致但不可直接比较性能。 [1] [2]
  待验证：复核两侧研究设计、人群与结局
- 推断（待核查） 现有 AKI 机器学习预测模型多缺乏外部验证，提示在公开 ICU 数据上开展可复现的外部验证研究可能具有价值。；推理：综述指出多数模型未经外部验证，同时也有少数研究仅做外部验证，说明外部验证并非完全空白，需进一步核实。；范围：AKI 机器学习预测模型的验证策略 [1] [1]
  待验证：需核实综述纳入研究的具体外部验证情况，并确认目标公开数据库是否适合作为外部验证集。
- 推断（待核查） 现有研究报告判别力较多而校准评估较少，提示在公开 ICU 数据研究中系统报告校准可能补充证据。；推理：综述指出所有研究均报告判别力，但校准指标少见，提示校准报告可能是可补充的方向。；范围：AKI 预测模型的评估指标 [1]
  待验证：需核实综述纳入研究中校准报告的实际情况，并确认目标研究的评估方案。
- 推断（待核查） 现有研究在缺失数据处理与变量选择上做法不一，提示在公开 ICU 数据研究中明确并比较预处理策略可能减少方法差异。；推理：综述显示部分研究未说明缺失数据处理，部分使用 MICE 等方法，提示预处理策略存在差异。；范围：AKI 预测模型的数据预处理与变量选择 [1] [1]
  待验证：需核实综述中缺失数据处理与变量选择的具体分布，并确认目标数据的缺失模式。
- 推断（待核查） 可行性（data；conditional）：综述显示 AKI 机器学习预测模型多针对 ICU 人群开发，提示公开 ICU 临床数据可能具备研究基础，但数据可用性、权限与标注质量需自行核实。；下一步核查：查阅目标公开 ICU 数据库的官方数据使用协议与 AKI 定义文档，评估可获取变量与标注可行性。 [1]
  待验证：需确认拟用公开 ICU 数据库的访问申请流程、使用许可、AKI 结局标注（如 KDIGO 标准）与缺失数据处理方案。
- 推断（待核查） 可行性（methods；conditional）：综述指出传统机器学习方法仍被广泛使用，深度学习模型自 2014 年出现，提示方法选择有先例可循，但需建立可复现基线。；下一步核查：基于目标数据库构建逻辑回归或梯度提升树基线，并记录预处理与变量选择流程。 [1]
  待验证：需确认具体特征工程、缺失值插补与变量选择流程，并复现至少一个基线模型。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估目标数据规模与候选模型（如梯度提升树、循环神经网络）的训练资源需求，确认本地或云端算力是否满足。 
- 文献事实（待核查） 可行性（validation；reported\_barrier）：Mostmodelswerenot
externally validated.；下一步核查：设计训练/内部验证/时间外部验证划分，并预先确定判别力与校准指标。 [1]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
待调查：Study 346f40e2-fcd7-5023-bd38-c1df77f0aaa2: not reported/unknown: comparison, effects, intervention, quality\_signals, results, sample\_size, time\_window
待调查：Study c5fd1adf-eb20-573b-916e-d2ccc98a5606: not reported/unknown: comparison, design, effects, limitations, quality\_signals, sample\_size
## 7. 可供考虑的研究方向
- 待验证假设（待核查） 可供进一步调查的方向：现有 AKI 机器学习预测模型多缺乏外部验证，提示在公开 ICU 数据上开展可复现的外部验证研究可能具有价值。 [1] [1]
  待验证：需核实综述纳入研究的具体外部验证情况，并确认目标公开数据库是否适合作为外部验证集。
- 待验证假设（待核查） 可供进一步调查的方向：现有研究报告判别力较多而校准评估较少，提示在公开 ICU 数据研究中系统报告校准可能补充证据。 [1]
  待验证：需核实综述纳入研究中校准报告的实际情况，并确认目标研究的评估方案。
- 待验证假设（待核查） 可供进一步调查的方向：现有研究在缺失数据处理与变量选择上做法不一，提示在公开 ICU 数据研究中明确并比较预处理策略可能减少方法差异。 [1] [1]
  待验证：需核实综述中缺失数据处理与变量选择的具体分布，并确认目标数据的缺失模式。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
## 8. 可追溯文献引用及证据支持状态
[1] Machine learning models for predicting acute kidney injury: a systematic review and critical appraisal；作者：Iacopo Vagliano、Nicholas C Chesnaye、Jan Hendrik Leopold、Kitty J. Jager、Ameen Abu–Hanna、Martijn C. Schut；日期：2022-08-02；期刊：Clinical Kidney Journal
DOI：10.1093/ckj/sfac181
URL：https://openalex.org/W4289519525
证据范围：已获取并引用的全文段落
https://doi.org/10.1093/ckj/sfac181
[2] A deep-learning model to continuously predict severe acute kidney injury based on urine output changes in critically ill patients；作者：Francesca Alfieri、Andrea Ancona、Giovanni Luigi Tripepi、DARIO B. CROSETTO、Vincenzo Randazzo、Annunziata Paviglianiti、Eros Gian Alessandro Pasero、Luigi Vecchi、Valentina Cauda、Riccardo Maria Fagugli；日期：2021-04-26；期刊：Journal of Nephrology
DOI：10.1007/s40620-021-01046-6
URL：https://openalex.org/W3159479990
证据范围：已获取并引用的全文段落
https://doi.org/10.1007/s40620-021-01046-6
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。
支持度审核上下文超预算，所有条目保持 uncertain。