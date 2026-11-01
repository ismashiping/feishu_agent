# Phase 9 冻结实施契约（2026-10-28）

范围：版本化离线 replay 评价器、逐样本审计、Recall@k/MRR、引用身份/定位/人工支持关系/覆盖率、失败与拒答分类、固定配置基线比较、受控离线并发测量、JSON/Markdown 一次性入口。复用 minimal-v1，历史失败不改标签；合成集仅检验公式。

输入：JSON dataset(version, kind, cases)、observations、thresholds；每个 case 固定问题、相关 chunk、来源身份/定位快照、允许/禁止 claim id、人工支持关系及标注状态。输出保留输入 hash、源码/锁 hash、Python/硬件、配置、全部观察及计数。重复/未知 case、未知相关 chunk、缺观察拒绝；缺医学标注不计通过。失败样本仍在检索及成功率分母；引用指标仅对实际引用，缺失引用由覆盖率和成功率独立约束。零分母 null。

门槛在 evaluation/phase9-v1/thresholds.json 冻结；宏平均 Recall/MRR、微平均引用指标；所有门槛 >=，任何失败 fail，缺值或未运行 scope inconclusive，fail 优先。baseline 必须 dataset/config/threshold/source annotations hash 相同才比较；不自动覆盖 baseline。合成样例支持关系是测试真值，真实医学仅 reviewed 的人工标签可评分。

性能命令只测离线评价函数，线程并发1/2/4，固定次数，计全部失败、p50/p95、吞吐和 tracemalloc Python峰值（不是进程RSS），无生产容量结论。真实模型/外部/服务满载未执行保持 inconclusive。

验收：手算公式、伪造身份/定位、真实来源无支持、无引用、拒答、失败分母、缺标注、重复输入、基线不兼容、确定性输出；运行目标 pytest、默认全量回归、Ruff/mypy、入口与并发命令。真实医学人工复核不能由本阶段自动填充。命令 scripts/evaluate_phase9.py --help。学习文档六份及 demo 交付。完整医学/真实模型/生产性能验收待真实证据。
