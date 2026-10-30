# Phase 9 执行与验收（2026-10-28）

## 本轮交付

离线核心开发完成，完整Phase9尚未验收。实现范围按[冻结契约](specs/tasks/p9-evaluation.md)：

- application/evaluation.py：逐题校验、Recall@k/MRR宏平均、引用身份/定位、人工支持/覆盖、允许结论召回/禁止结论比例、拒答/失败分类、空分母null、门槛/基线兼容和回归delta。
- scripts/evaluate_phase9.py：一次性离线命令、JSON/Markdown、输入/源码/锁hash、运行配置/平台、run_id、只读baseline与输入目录保护。
- evaluation/phase9-v1：三条明确标记合成的公式样例和预先冻结门槛。不是医学标注集。minimal-v1历史真实包原样保留。
- tests/unit/test_evaluation.py、tests/integration/test_evaluation.py：手算、假引用、无支持/无引用、缺标签、重复/缺失输入、失败分母、错误拒答、错定位、基线不兼容与回归、脚本真实执行和benchmark异常计数。
- .github/workflows/evaluation.yml：仅小型确定性评价测试；未运行远端CI，不声称CI已绿。
- docs/learning/phase-09：六份初学者文档及可运行demo。

## 可重复命令

```powershell
.venv/Scripts/python.exe -I -m pytest tests/unit/test_evaluation.py tests/integration/test_evaluation.py -q
.venv/Scripts/python.exe -I scripts/evaluate_phase9.py --output evaluation/results/phase9-final --performance
.venv/Scripts/python.exe -I scripts/evaluate_minimal_baseline.py --output evaluation/results/phase9-historical
.venv/Scripts/python.exe -I docs/learning/phase-09/demo.py
```

合成公式报告故意fail（退出1）：Recall=0.5、MRR=0.25、身份=0.5、定位=0.5、支持=0、覆盖=0.5，模型失败1、正确拒答1。失败用例通过测试断言表示检测机制正确，不表示其业务输出合格。历史真实复算同样退出1/baseline_not_accepted：fresh0/2、来源4/4、新模型调用0。没有将失败样例排除或覆盖旧基线。

性能输出为固定100次、线程1/2/4的暖输入评价函数微基准，保存全体耗时、异常、吞吐和Python跟踪内存。此处fail是指标检测到质量问题，benchmark failures仅统计评价函数执行异常，二者含义不同。报告不声明生产容量，没有RSS/GPU/服务超时和满载证据。

质量检查：新增实现mypy通过，五个Python文件Ruff及格式通过；demo运行得到fail及MRR0.25，符合手算。git diff --check通过（已有CRLF提示）。全量与最终目标批次结果补记见下文；此前7/11/12项目标通过均为实际中间批次，不加总。

## 不能自动完成的验收

完整SPEC09的P9-T05真实固定模型评价与合格人工复核未运行；P9-T06仅做评价函数微基准，没有真实服务并发饱和、RSS预算及超时释放实验。未冻结真实医学/生产性能预算，合成阈值仅用于公式测试。Phase7 fresh0/2与人工签署缺口保留。未把模型自评分作为金标准、未新增网络或付费调用。

因此所有报告保留real_model/external/medical_review/service_load为未执行，整体状态即使offline_status通过也最多inconclusive；存在确定失败则fail优先。下一步需取得独立医学标注，建立真实固定模型的可评分输出，再冻结真实环境预算执行模型/服务验收；本轮不自动进入其他Phase。

## 最终目标批次

`.venv/Scripts/python.exe -I -m pytest tests/unit/test_evaluation.py tests/integration/test_evaluation.py -q --basetemp=.artifacts/phase9/verified-target-tmp -o cache_dir=.artifacts/phase9/cache`：**13 passed in 1.98s**，日志 `.artifacts/phase9/target.txt`。最后补测的是身份正确但定位错误、错误拒答、以及离线通过时未执行真实范围仍inconclusive。

## 默认离线回归

实际命令（本轮进程OMP_NUM_THREADS=2、MKL_NUM_THREADS=2）：

```powershell
.venv/Scripts/python.exe -I -m pytest -q --tb=short --basetemp=.artifacts/phase9/full-tmp -o cache_dir=.artifacts/phase9/cache
```

结果 **1252 passed / 122 deselected / 1既有飞书SDK弃用警告，300.06秒**；日志 `.artifacts/phase9/full.txt`，退出0。被marker排除的external/database/redis/performance不算通过。本批在最终新增目标测试及offline_status/overall_status范围修正前启动，保留原计数；最终Phase9修改由后续13项目标批次验证，不将两批加总冒充最终全量。未修改既有生产业务模块，不重复执行数据库迁移/联网/付费测试。

本轮离线核心、文档、CI配置交付；完整Phase9按上述缺口保持待验收。保留原工作区未提交改动，未创建提交或进入其他阶段。
