# 修改与独立实现练习

先运行tests/unit/test_agents_migration.py，观察双拓扑、State字段、旧新对象身份和公开签名对比；再阅读test_feedback_agents.py和test_research.py中的超时、并发隔离与引用场景。

修改练习（仅在练习分支）：把反馈边methods错误指向retrieve，运行拓扑与反馈测试，解释为何节点存在断言无法发现所有错误。完成后恢复练习改动，不更新冻结fixture来掩盖错误。

独立实现：在独立临时脚本使用StateGraph实现input→validate→END以及validate→reject→END，不改项目生产图；测试两个分支及两次调用不共享状态。

验收标准：能解释编译与invoke的差异、请求状态的归属、反馈计数与递归限制的不同职责。历史29项失败不属于该练习的修复范围。
