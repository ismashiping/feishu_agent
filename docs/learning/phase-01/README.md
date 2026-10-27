# Phase 1 学习导航

适用范围：P1-01–17当前代码；学习材料交付不等于阶段已完成。当前验收结论与未完成门槛见[阶段报告](../../phase1-acceptance.md)，任务事实入口是[开发进度](../../development-plan.md)。

读完后应能自己讲清“文献为什么能回到原始位置”“为什么生成器不能决定文献身份”“为什么HTTP取消不释放实际运行线程的容量”。无需先懂LangGraph或Redis。

| 顺序 | 内容 | 学习产出 |
| --- | --- | --- |
| 1 | [从零教程](tutorial.md) | 理解RAG、向量与来源，运行离线Demo |
| 2 | [代码执行顺序](code-walkthrough.md) | 沿入库、检索、生成、飞书和关闭调用链阅读 |
| 3 | [练习与测试](exercises.md) | 预测失败、修改副本、独立实现小工具 |
| 4 | [排错](troubleshooting.md) | 区分配置、数据库、模型、生成与投递故障 |
| 5 | [面试表达](interview.md) | 用30秒解释取舍与项目边界 |

最小Demo：在仓库根目录执行（已安装当前锁定的开发环境和rag extra）：

```powershell
& .venv/Scripts/python.exe docs/learning/phase-01/demo.py
```

预期JSON包含answered、insufficient_evidence、citation_invalid三个分支，external_calls为0。[demo.py](demo.py)执行真实ResearchService/LangGraph与引用门禁，检索和生成是显式合成替身，不载入E5、不连接数据库、不发送医学文本。它可以从其他工作目录执行，但需使用已安装本项目的解释器。

完整应用依赖及运行入口见[CLI](../../cli.md)、[API](../../api.md)、[飞书](../../feishu-runtime.md)。不要把练习里的合成来源当真实临床研究，不在源码中填写密钥。Phase2功能不属于本教材已经实现的能力。
