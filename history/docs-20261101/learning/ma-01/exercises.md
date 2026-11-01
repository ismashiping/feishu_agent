# 修改与验证练习

运行Demo，观察角色顺序和两条PMID，与冻结blood-pressure快照比较。将state.deadline设为0，应在调用依赖前拒绝，不能得到伪造空结果。

把回放规划响应换成model-response-1.txt，观察旧的数组span依然拒绝。这说明迁移没有修复或掩盖历史模型错误。独立练习：为一个返回错误scope的Scout依赖写案例，确认结果不能进入报告。

正式目标为tests/unit/test_agent_roles.py及MA-01 SPEC列出的受影响回归。只在本增量末集中执行；真实模型/服务与医学人工验收单独记录，不能用Demo代替。
