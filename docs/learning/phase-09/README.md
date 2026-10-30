# Phase 9 学习导航

按 tutorial → code-walkthrough → exercises → troubleshooting → interview 阅读。先运行 `python docs/learning/phase-09/demo.py`，再运行项目根 `.venv/Scripts/python.exe -I scripts/evaluate_phase9.py --output evaluation/results/my-run`。预置数据含故障，退出1符合预期。

评价器回答“冻结输入下有哪些可测的错误”。合成样例演示计算，不是医学数据集。真实失败记录在 evaluation/minimal-v1，复算入口 evaluate_minimal_baseline.py；不能把这两个包混算成医疗质量分。
