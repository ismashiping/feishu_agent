# 练习与测试

1. 运行demo，手算 recall=0.5、MRR=0.25、身份=0.5、定位=0.5、覆盖=0.5、支持=0。
2. 将伪造引用的source_id改成真实但chunk仍未知，确认身份仍失败。来源必须和片段同时对应。
3. 将 annotation_status 改为unknown，检查医学指标变null。恢复文件，避免在原冻结集上调参。
4. 复制数据包为新版本，增加一条正确引用和人工支持的合成claim，检查微平均分母变化；保持原包不动。
5. 独立实现手算nDCG并设计重复相关结果的反例，先不要接入当前门槛；将其公式与Recall/MRR比较。

实际测试命令：`.venv/Scripts/python.exe -I -m pytest tests/unit/test_evaluation.py tests/integration/test_evaluation.py -q`。单元覆盖指标、零分母、重复/缺失输入、缺标签、基线不兼容和回归；集成调用隔离解释器验证真实脚本输出，并注入TimeoutError验证性能错误计数。
