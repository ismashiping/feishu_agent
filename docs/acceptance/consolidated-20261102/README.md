# 当前源码集中验收结论（2026-11-02）

## 判定
**限定范围内的核心技术链路验收通过；科研质量与项目整体正式验收仍部分通过。**
当前源码可以从用户原始想法，经真实OpenAlex检索、实际全文RAG、已有研究比较、
四维条件式可行性、多批模型审核，返回带可追溯引用的最终Markdown报告。
两轮均在默认180秒内返回，实际缓存命中、完整审核覆盖已核查。
不要求把证据不足变为verified；本次两报告均partial/verification_incomplete。
不能据此证明检全、创新性、真实实验可行性或医学语义正确。

## 范围、版本、环境
范围在运行前冻结于 [SCOPE.md](SCOPE.md)。
[manifest-final.json](manifest-final.json)冻结活动源码/测试/pyproject/锁文件内容哈希，
不是仅使用Git HEAD推断有未提交修改的工作区。两次真实运行后哈希再次校验未变。
环境详见 [environment.json](environment.json)：本机Python3.12、仓库.venv、
真实DeepSeek配置、OpenAlex、本地multilingual-e5-base、Docker PG/pgvector0.8.7，
独立库clinical_agent_test_context_20261102、迁移oa3003_0011。
没有删除数据、安装依赖、部署API或发送飞书消息。凭据仅进程使用，未写入验收记录。
运行起点有11篇缓存511向量，因此不是空库冷启动；E5加载49.5秒单独计时。

## 离线实际结果
| 门槛 | 结果 | 原始输出 |
|---|---|---|
| 全套默认离线pytest首轮 | 3 failed /1632 passed /100 deselected | [pytest.txt](pytest.txt) |
| 受影响修正回归 | 46 passed，15.80秒 | [affected.txt](affected.txt) |
| 全套默认离线最终 | **1635 passed /100 deselected /1警告，205.45秒** | [pytest-final.txt](pytest-final.txt) |
| Ruff src/tests | 通过 | [ruff-final.txt](ruff-final.txt) |
| mypy src | 77个源码文件通过 | [mypy-final.txt](mypy-final.txt) |
| uv lock --check --offline | 139包解析通过 | [lock.txt](lock.txt) |
| 学习Demo | online接受，local在运行前拒绝 | 见下方命令 |

本批仅修改3个测试文件，业务源码未改：两个OpenAPI断言显式接受已授权的
ConceptRelation.required字段说明，其他完整比较保留，历史快照未改；
compact_context测试改为按分批ID完整覆盖、无重复无遗漏验证，不再断言只调用一次。
变更列表及首轮哈希保存在manifest.json/manifest-final.json，不将首次失败覆盖。
SDK弃用警告来自飞书依赖；未宣称已修复。
默认排除external/performance/database/redis共100项，不能记通过；本表真实验证
只覆盖下述业务，不替代全套数据库/Redis或性能验收。

## 两轮真实业务
入口：当前源码open_research_service → ResearchService.report，原中文公开ICU数据
机器学习/深度学习预测AKI想法。无Mock、没有修改模型输出、没有无限重跑挑结果。
[完整时序](live/events.json)、[独立覆盖核查](audit.json)。

| 指标 | first | repeat |
|---|---:|---:|
| 规划 | 4.297s | 4.578s |
| 检索含筛选 | 18.140s | 20.844s |
| 全文RAG | 22.516s | 1.985s |
| 研究分析 | 11.453s | 16.422s |
| 报告组装含逐批审核 | 9.391s | 13.719s |
| **总耗时** | **65.922s** | **57.656s** |
| 选中论文/有效全文/片段 | 3/2/6 | 5/3/9 |
| 最终论断/实际审核批次 | 34/6 | 49/9 |
| supported/partial/uncertain | 23/7/4 | 35/9/5 |
| 每批恰好覆盖且最终无漏审 | 通过 | 通过 |
| 全文引用原句核查 | 39/39匹配 | 57/57匹配 |
| 实际缓存命中 | 1 | 3 |
| 索引/向量 前→后 | 11/511→12/562 | 12/562→12/562 |

所有批次输入<=32000字符且<=6论断，响应ID与请求集合相同，无重复，最终basis均非
not_reviewed；无审核输出截断或失败批次。原始逐批输入和响应保存在live目录。
片段均为fulltext，未以摘要替代全文。阶段为嵌套时序，不能重复相加。

first新增doi:10.1101/2020.01.27.20019091实际下载/解析/编码入库51块；
doi:10.6084/m9.figshare.32869405无全文候选，未作为证据。
两轮均命中doi:10.1093/jamiaopen/ooaf065；repeat另外命中
 doi:10.1080/0886022x.2026.2690700、doi:10.1080/0886022x.2025.2611198。
同key命中后向量检索、没有重新下载，才作为复用依据，不用总时间下降推断。
repeat有两个invalid_file失败，保留为未获得全文。
repeat首次候选筛选真实发生finish_reason=length、output_tokens1500的失败，
补充筛选成功，provenance partial/openalex_screening_failed如实保留。
这不是审核截断；不能把该筛选尝试记通过。

## 输出内容复核与状态解释
[第一轮报告](live/first-report.md) / [第二轮报告](live/repeat-report.md)。
两轮均有研究方法、相似性/差异性、候选缺口和数据/方法/算力/验证四维评估。
两轮data/methods为conditional，compute unknown，validation reported_barrier；
reported_barrier是论文报告的限制，不表示用户一定受到相同限制。
样本量均not_reported，未再次把综述篇数或被引研究表格行放入综述自身sample_size。
这只覆盖本样例，不保证所有抽取语义都正确。

模型审核有理由支持或质疑各条目：例如cohort分类缺少直接原文说明，数据维度
unknown、算力缺失；候选创新方向仍是待验证假设。审核全部执行并不要求全部支持。
first反馈no_actionable_feedback；repeat因检索partial希望追加scout，但剩余约122秒
小于135秒准入门槛，feedback_stop=budget_limit。该停止发生在完整审核之后，
不是总期限耗尽或未审核，不将其变成verified。
本轮是代码/原文一致性与明显语义问题的静态复核，不是独立医学专家签署。
所有引用可追溯不等于综述偏倚评估或论断语义全部正确。

## 剩余项
- P0核心阻断：本批未出现最终入口失败、引用丢失或漏审；不外推为所有输入无缺陷。
- P1：候选筛选仍可输出截断；受限补充流程本次继续成功但会影响覆盖可靠性。
  研究类型判定、相似性/推断仍有证据不足，需保留partial/unknown和人工复核。
- P2：性能、HTTP部署、飞书实收及非核心优化本批不推进。
- 未完成：独立医学人工签署、全套真实依赖回归、远端CI、部署验收。

## 如何复现
以下命令从仓库根执行，真实服务使用已有配置（付费调用需授权；本会话已授权）。
输出目录必须新建且不能已存在；脚本拒绝覆盖，不需要也不允许清空旧数据。
环境检查脚本不输出凭据。数据库必须已显式迁移，业务入口不会自动迁移。

```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/consolidated-20261102/check_environment.py
.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/consolidated-replay -o cache_dir=.artifacts/tmp/consolidated-replay-cache
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
.venv/Scripts/uv.exe --cache-dir .artifacts/tmp/consolidated-replay-uv lock --check --offline
.venv/Scripts/python.exe -X utf8 docs/learning/current/demo.py
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_consolidated.py docs/acceptance/consolidated-replay-NEW/live
```

原始本批live命令没有最后路径参数，使用当前记录目录。重跑应换NEW目录后缀；
勿复用同一pytest basetemp，以免pytest清理上次临时产物。
在线数据、模型及选中论文可变化，“可复现”指代码/步骤/断言和记录可核查，
不承诺逐字相同。复核可用audit_live.py，当前默认读取本批live，复跑需显式改路径。
学习说明：[验收学习导航](../../learning/current/acceptance.md)。
本轮结束，未推进下一Phase，没有将项目整体标为完成。
