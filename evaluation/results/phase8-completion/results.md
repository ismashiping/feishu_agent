# 最小评价基线 v1

模式：冻结历史证据的离线复算；没有新的模型/外部调用。

| 指标 | 结果 |
| --- | --- |
| 最新fresh端到端报告 | 0/2 |
| 真实来源XML/身份/摘要回放一致 | 4/4 |
| 历史模型调用 | 5；本次新增0 |
| 回放续验 | 1，不计入fresh成功率 |
| 方法/相似性/缺口/论断医学质量 | 未评价（null）；无有效报告、无人工签署 |

## 最新完整启动记录

| 想法 | 状态 | 停止原因 | 耗时秒 |
| --- | --- | --- | --- |
| blood-pressure | failed | context_limit | 3.69 |
| sepsis | failed | context_limit | 3.27 |

## 边界

- Historical attempts span uncommitted revisions; not a controlled before/after experiment.
- Captured official sources are not a recall benchmark or medical ground truth.
- Local database unavailable; hybrid/local end-to-end unverified.
- No successful report; semantic quality and full report citations unverified.

退出码1表示真实基线仍未达验收门槛；不是复算工具错误，也不是医学质量通过。
