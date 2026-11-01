# 科研选题现状调研报告
内容：部分证据；审核：尚未完整核验
核验完成仅表示规定检查完成；模型支持度建议需人工复核，不证明创新性或临床结论。
## 1. 用户科研想法与研究问题
我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
研究问题：我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。
## 2. 检索范围、策略和时间
开始：2026-11-01T19:08:49.149447+00:00；生成：2026-11-01T19:10:21.745184+00:00
实际检索来源范围：在线
本次实际检索范围有限；无命中不代表空白或创新。
## 3. 已有相关研究
- 推断（有证据支持） 研究设计分类：systematic\_review；判定来源：text [1]
  待验证：核对出版类型与研究设计原文
## 4. 研究方法与技术路线对比
- 文献事实（有证据支持） data\_sources：Public ICU datasets were widely used. [1]
- 文献事实（有证据支持） design：This systematic review comprehensively evaluated the AI models for the prediction of AKI in the ICU. [1]
- 文献事实（有证据支持） evaluation\_metrics：Model performance was primarily evaluated using AUROC, while other metrics and calibration were less reported. [1]
- 推断（有证据支持） outcomes：该综述关注 ICU 中急性肾损伤（AKI）预测模型的建模方法、数据利用与临床适用性，而非单一模型的效应估计。 [1]
  待验证：需核对原文纳入标准与结局定义，确认是否统一采用 AKI 诊断标准。
- 文献事实（有证据支持） population：This systematic review comprehensively evaluated the AI models for the prediction of AKI in the ICU. [1]
- 文献事实（有证据支持） results：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP. [1]
- 文献事实（部分支持） sample\_size：Across the 47 included studies, models including LR, RF, XGBoost, and SVM were the most commonly used. [1]
- 文献事实（有证据支持） technical\_methods：Across the 47 included studies, models including LR, RF, XGBoost, and SVM were the most commonly used. [1]
## 5. 与用户想法的相似性分析
- 推断（有证据支持） data：overlap；用户拟使用公开 ICU 临床数据，综述指出公开 ICU 数据集被广泛使用。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） methods：partial\_overlap；用户提出机器学习或深度学习，综述报告常用模型包括 LR、RF、XGBoost、SVM，深度学习并非唯一主流。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） outcomes：overlap；用户目标是 AKI 风险预测，综述报告模型性能主要以 AUROC 评估，结局评价方向一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） population：overlap；用户面向患者人群，综述聚焦 ICU 场景下的 AKI 预测，人群场景相符。 [1]
  待验证：结合用户原始约束及文献复核相似性
- 推断（有证据支持） question：overlap；用户关注 ICU 患者 AKI 风险预测，该综述系统评估 ICU 中 AKI 的 AI 预测模型，问题方向一致。 [1]
  待验证：结合用户原始约束及文献复核相似性
## 6. 已有研究局限及候选研究缺口
- 文献事实（有证据支持） limitations：Overall, although progress in modeling approaches is evident, limitations in generalizability, transparency, and clinical translation remain. [1]
- 文献事实（有证据支持） quality\_signals：The PROBAST assessment suggested a high risk of bias in most studies, especially in the analysis domain. [1]
- 推断（有证据支持） 现有 ICU AKI 预测研究外部验证比例有限，用户可考虑在公开 ICU 数据上设计更充分的外部或时间切分验证。；推理：综述报告仅 14 项研究开展外部验证，同时公开 ICU 数据集被广泛使用，二者结合提示验证设计存在改进空间，但需核实数据可比性。；范围：ICU 中 AKI 的 AI 预测模型研究 [1] [1]
  待验证：需核实目标公开数据集之间的人群、变量定义与时间跨度是否可比，避免将不可比数据当作外部验证。
- 推断（有证据支持） 现有研究报告的评估指标以 AUROC 为主，校准与其他指标报告较少，用户可考虑补充校准与多指标评估。；推理：综述指出模型性能主要用 AUROC 评估，其他指标与校准报告较少，提示评估维度可扩展。；范围：ICU 中 AKI 的 AI 预测模型评估 [1]
  待验证：需核实目标研究场景对校准与临床决策阈值评估的具体要求。
- 推断（有证据支持） 现有研究在泛化性、可解释性与临床转化方面仍存在局限，用户可考虑在建模同时纳入可解释性分析。；推理：综述指出泛化性、透明度与临床转化局限，同时报告部分研究已使用 SHAP 等解释工具，提示可解释性仍有改进空间。；范围：ICU 中 AKI 的 AI 预测模型研究 [1] [1]
  待验证：需核实可解释性方法在目标数据集上的稳定性与临床可解释性。
- 推断（有证据支持） 可行性（data；conditional）：公开 ICU 数据集被广泛使用，提示数据可得性有先例；但用户具体可访问的数据集、使用许可与标注质量未在证据中说明。；下一步核查：查阅目标公开 ICU 数据集的官方文档与数据使用协议，核对 AKI 结局变量与关键特征的可获得性。 [1]
  待验证：需确认拟用公开 ICU 数据集的具体名称、访问申请流程、数据使用协议及 AKI 标签定义与缺失情况。
- 推断（部分支持） 可行性（methods；conditional）：综述报告 LR、RF、XGBoost、SVM 为最常用模型，特征选择以 LASSO 与专家驱动为主，可作为方法适配与基线构建的参考。；下一步核查：在目标数据集上复现一个 LR 或 XGBoost 基线，并记录预处理与特征选择流程。 [1]
  待验证：需确认用户所选模型与特征工程方案在目标数据集上的可复现性，并建立可复现基线。
- 文献事实（待核查） 可行性（compute；unknown）：证据不足，条件待确认；下一步核查：证据未提供算力或成本信息；需评估目标数据集规模与所选模型训练所需资源后再判断。 
- 文献事实（有证据支持） 可行性（validation；reported\_barrier）：Only 14 studies conducted external validation, and 33 applied interpretation tools, mainly SHAP.；下一步核查：确认是否存在可用的独立 ICU 数据集用于外部验证，或设计严格的内部留出与时间切分评估方案。 [1]
局限：Evidence pointers are checked; medical meaning, completeness and candidate gaps require human review.
待调查：Study 549385ae-e657-5537-8459-c67ae9e4efe5: not reported/unknown: comparison, effects, intervention, time\_window
## 7. 可供考虑的研究方向
- 待验证假设（有证据支持） 可供进一步调查的方向：现有 ICU AKI 预测研究外部验证比例有限，用户可考虑在公开 ICU 数据上设计更充分的外部或时间切分验证。 [1] [1]
  待验证：需核实目标公开数据集之间的人群、变量定义与时间跨度是否可比，避免将不可比数据当作外部验证。
- 待验证假设（有证据支持） 可供进一步调查的方向：现有研究报告的评估指标以 AUROC 为主，校准与其他指标报告较少，用户可考虑补充校准与多指标评估。 [1]
  待验证：需核实目标研究场景对校准与临床决策阈值评估的具体要求。
- 待验证假设（有证据支持） 可供进一步调查的方向：现有研究在泛化性、可解释性与临床转化方面仍存在局限，用户可考虑在建模同时纳入可解释性分析。 [1] [1]
  待验证：需核实可解释性方法在目标数据集上的稳定性与临床可解释性。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
待评估方案：待确认数据可得性、研究对象、设计和评价指标；不从摘要补造方案参数。
## 8. 可追溯文献引用及证据支持状态
[1] Artificial intelligence models for predicting acute kidney injury in the intensive care unit: a systematic review of modeling methods, data utilization, and clinical applicability；作者：Tongyue Shi、Yu Lin、Huiying Zhao、Guilan Kong；日期：2025-06-14；期刊：JAMIA Open
DOI：10.1093/jamiaopen/ooaf065
URL：https://openalex.org/W4411994860
证据范围：已获取并引用的全文段落
https://doi.org/10.1093/jamiaopen/ooaf065
支持度是模型审核建议；引用有效不等于结论正确，候选缺口与方向需要人工验证。