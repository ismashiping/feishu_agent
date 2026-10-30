# 练习与阶段测试

项目根执行 `.venv/Scripts/python.exe -I docs/learning/phase-06/demo.py`。先观察 design 的引文及其定位，确认其余字段是 not_reported，整体相似性 unknown。

修改练习：把 value 中 20 改成 200，保持 quote 不动，应出现 model_output_invalid。恢复后将一个维度设 overlap 但不提供用户原文定位或文献引文，也应拒绝。记录这说明了什么，以及它不能证明什么。

独立练习：在合成示例中增加第二个不同 hash 的研究，构造双侧比较；再复用相同 hash，观察重复研究门禁。无需网络。

正式阶段末集中命令见 P6-01 SPEC 与阶段记录。核心测试为 `tests/unit/test_evidence_analysis.py`，覆盖来源、未知字段、标签、双侧比较、CLI/API 和模型边界；默认 tests 回归排除的外部项不计通过。练习不新增单次会话测试要求。
