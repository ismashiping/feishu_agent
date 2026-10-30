# 最小评价基线 v1

2026-10-28。已建立冻结的真实失败基线，未完成医学质量金标准，也不表示Phase7验收通过。仅离线复算，无新增模型/网络/数据库调用。

项目根执行：

```powershell
.venv/Scripts/python.exe -X utf8 -I scripts/evaluate_minimal_baseline.py
```

输出 [结果表](results/minimal-v1/results.md) 和 results/minimal-v1/results.json。当前退出码 **1** 是预期：既有系统在真实fresh端到端中失败、医学未审；证据损坏或来源复核失效退出2。v1不自动授予医学验收通过。

冻结包 minimal-v1/ 包含两条真实科研想法、4篇真实PubMed元数据/摘要/XML、首次与修正后fresh记录、单列的规划回放续验、5次历史调用账本和原始规划响应；没有复制.env或凭据。manifest.json校验每份证据、人工待标模板和冻结时源码状态。结果文件置于包外，防止覆盖证据。

最新fresh观察基线0/2，来源离线回放4/4；方法准确/遗漏、相似性错误、无依据缺口/创新宣称、支持度精确率/召回均为null。没有有效报告，不能把报告引用分母0计为100%，也不能用模型自评分替代人工。human-labels.json仅为待标注表，审查人和日期为空，尚未形成可评分金标准。具体停止节点与耗时见结果JSON，不将不足2例的耗时称为性能基准。

历史尝试跨多个未提交源码版本，source-state.json只保存冻结时的源码hash和Git HEAD，不能倒推每次历史运行版本。因此v1是可审计观察基线，不是严格受控的改造效果实验。后续改造前须补齐合格人工标签/阈值和可重复的真实成功报告，再冻结新版本。

比较候选版本时复制schema至新目录，登记真实运行与源码hash，命令使用 `--bundle <新包目录> --output <新结果目录>`；新证据必须建立独立manifest，不能修改v1冒充改进。脚本只做最小结构/来源复算，不实施评价平台或完整Phase9。不能自动填充医学标签。

本次验证：4项基线目标测试通过，Ruff/格式检查仅覆盖新增脚本和测试；没有重复旧全量。规格见 [任务SPEC](../docs/specs/tasks/minimal-evaluation-baseline.md)。后续顺序仍为最小评价基线 → 增量Multi-Agent → Phase8 → 完整Phase9，Phase7待审项独立保留。本次不进入任何后续阶段。

Phase9入口：`.venv/Scripts/python.exe -I scripts/evaluate_phase9.py --output evaluation/results/my-run`，`--performance`可增加评价函数微基准，`--baseline <results.json>`显式比较。新公式集/真实历史集分开，详见[阶段报告](../docs/phase9-acceptance.md)。合成公式集默认退出1，完整医学与真实服务范围仍未验收。
