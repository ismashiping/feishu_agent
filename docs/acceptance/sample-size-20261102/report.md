# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:27:25.205488+00:00；生成：2026-11-01T19:27:38.758498+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（有证据支持） 研究设计分类：systematic\_review；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（有证据支持） data\_sources：Public ICU datasets were widely used. [1]
- 文献事实（有证据支持） design：This systematic review comprehensively evaluated the AI models for the prediction of AKI in the ICU. [1]
- 文献事实（有证据支持） evaluation\_metrics：Model performance was primarily evaluated using AUROC, while other metrics and calibration were less reported. [1]
- 推断（有证据支持） outcomes：该综述关注 ICU 中急性肾损伤（AKI）的预测，而非干预效果结局。 [1]
  待验证：需核对原文确认其结局定义与预测时间窗。
- 文献事实（部分支持） population：It provided a detailed overview of current AKI prediction studies on modeling methods, data utilization, and clinical applicability. [1]
- 文献事实（有证据支持） results：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP. [1]
- 文献事实（有证据支持） technical\_methods：Across the 47 included studies, models including LR, RF, XGBoost, and SVM were the most commonly used. [1]
- 推断（有证据支持） time\_window：综述提及实时动态 AKI 预测，但未给出统一的预测时间窗。 [1]
  待验证：需查阅纳入研究以确认各模型的预测时间窗。
## 5. 与用户想法的相似性分析
- 推断（有证据支持） data：overlap；用户计划使用公开 ICU 临床数据，综述指出公开 ICU 数据集被广泛使用。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：partial\_overlap；用户关注机器学习/深度学习，综述报告常用模型包括 LR、RF、XGBoost、SVM，但未在所选句子中明确深度学习。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；用户目标是 AKI 风险预测，综述以 AUROC 等指标评估 AKI 预测模型性能。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（部分支持） population：overlap；用户面向患者，综述聚焦 ICU 中的 AKI 预测人群。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；用户想预测 AKI 风险，该综述正是评估 ICU 中 AKI 预测的 AI 模型。 [1]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（有证据支持） limitations：However, limitations are still present in current studies, including inadequate generalizability and interpretability of models, low proportions of external validation, and barriers to data sharing due to technical and ethical challenges. [1]
- 文献事实（有证据支持） quality\_signals：The PROBAST assessment suggested a high risk of bias in most studies, especially in the analysis domain. [1]
- 推断（有证据支持） 现有 AKI 预测模型的外部验证比例较低，用户研究可考虑将外部或时间切分验证作为设计重点。；推理：综述报告仅 14 项研究进行外部验证，同时指出泛化性局限，提示验证设计是潜在改进方向。；范围：ICU 中 AKI 的 AI 预测模型 [1] [1]
  待验证：需核实综述纳入研究中外部验证的具体定义与比例。
- 推断（有证据支持） 模型可解释性与临床转化仍不充分，用户研究可关注可解释方法与报告规范。；推理：综述指出可解释性不足且完整报告不常见，同时已有 33 项研究使用 SHAP 等工具，说明该方向存在但仍有改进空间。；范围：ICU 中 AKI 的 AI 预测模型 [1] [1]
  待验证：需核实综述对可解释性和 TRIPOD 依从性的具体评估结果。
- 推断（有证据支持） 可行性（data；conditional）：公开 ICU 数据集被广泛使用，提示数据可得性有一定基础。；下一步核查：确认目标公开 ICU 数据集的许可协议、申请流程与 AKI 标签定义是否满足研究需要。 [1]
  待验证：需核实具体公开数据集的访问权限、伦理审批与标注质量，不能假定用户已具备数据使用权。
- 推断（有证据支持） 可行性（methods；conditional）：已有研究常用 LR、RF、XGBoost、SVM 等方法，可作为可复现基线参考。；下一步核查：基于公开数据构建一个 LR 或 XGBoost 基线并复现 AUROC 评估流程。 [1]
  待验证：需确认所选方法在用户数据上的特征工程与预处理可复现性。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：评估所选模型规模与数据量后，确认本地或云端算力是否满足训练与调参需求。 
- 文献事实（有证据支持） 可行性（validation；reported\_barrier）：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP.；下一步核查：规划独立外部验证集或时间切分验证，并预先定义 AUROC 与校准指标。 [1]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
待调查：Study 549385ae-e657-5537-8459-c67ae9e4efe5: not reported/unknown: comparison, effects, intervention, sample\_size
## 7. 可供考虑的研究方向
- 待验证假设（有证据支持） 可供进一步调查的方向：现有 AKI 预测模型的外部验证比例较低，用户研究可考虑将外部或时间切分验证作为设计重点。 [1] [1]
  待验证：需核实综述纳入研究中外部验证的具体定义与比例。
- 待验证假设（有证据支持） 可供进一步调查的方向：模型可解释性与临床转化仍不充分，用户研究可关注可解释方法与报告规范。 [1] [1]
  待验证：需核实综述对可解释性和 TRIPOD 依从性的具体评估结果。
## 8. 可追溯文献引用及证据支持状态
[1] Artificial intelligence models for predicting acute kidney injury in the intensive care unit: a systematic review of modeling methods, data utilization, and clinical applicability；作者：Tongyue Shi、Yu Lin、Huiying Zhao、Guilan Kong；日期：2025-06-14；期刊：JAMIA Open
DOI：10.1093/jamiaopen/ooaf065
URL：https://openalex.org/W4411994860
证据范围：已获取并引用的全文段落
https://doi.org/10.1093/jamiaopen/ooaf065
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。