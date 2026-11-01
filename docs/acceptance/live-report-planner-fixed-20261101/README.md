# 规划修复后的真实验收（2026-11-01）

结论：规划修复通过；科研全链路部分通过，最终完整验收未通过，热缓存复用未证实。

## 修改与回归
真实失败响应保存在 ../planner-20261101/raw-before.json；模型把risk prediction标为
related_concept且required=true。修改 domain/pico.py 的模型schema字段说明与提示词，
明确哪些关系可作为锚点，保留QueryPlan原校验。无静默改写响应、无删除用户约束。
新增 tests/unit/test_planner_live_contract.py 三项回归；先1 failed/1 passed，
最终受影响回归89 passed，Ruff通过、mypy 77文件通过、修改范围diff检查通过。
任务SPEC见 ../../specs/tasks/planner-contract.md。

## 实际入口与命令
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/capture_planner.py
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_reports_planner_fixed.py
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_reports_hot.py
```
同一中文ICU/AKI科研想法，真实DeepSeek、OpenAlex、E5、独立测试库，正式ResearchService.report。
只转发原实现的测量包装，无Mock。总预算90秒、反馈上限及引用规则不变。
首次两轮后已建立缓存，为核查热复用又补跑一次；没有清空数据库。

| 指标 | 冷运行 | 第二次运行 | 有缓存后的补跑 |
|---|---:|---:|---:|
| 规划秒数 | 5.172 | 5.063 | 5.954 |
| 首次检索+筛选秒数（包含HTTP/模型） | 19.890 | 15.343 | 15.641 |
| 首次全文RAG秒数（包含解析/分块/编码/DB） | 36.031 | 41.016 | 40.453 |
| 首次有效全文论文/片段 | 0/0 | 1/3 | 1/3 |
| 首次分析秒数 | 0.078（无证据直接返回） | 14.500 | 10.828 |
| 首次报告构建/审核秒数 | 1.468 | 5.750 | 6.656 |
| 总秒数（包含反馈） | 83.531 | 90.328 | 90.203 |
| 最终结果 | 证据不足报告 | research_timeout | generation_timeout |
| 库中索引/向量 | 0/0 | 1/33 | 2/81 |

阶段计时有嵌套，不能重复相加。解析与分块未分别测量，下载+解析合并记录。
最终两次超时均在首轮分析和报告构建完成后的反馈流程，不应写成第一次分析失败。

## 实际全文与分析
冷运行成功下载解析 W4289519525（24个正文单元），后续编码超时；其余受阶段期限限制。
第二轮 W4400283511 两个地址失败（invalid_file/download_failed）；
W4280556240 成功解析25个单元，33块Embedding成功、入库成功、向量检索成功；
W4289519525再次解析成功但Embedding超时。
对应论文：Machine learning for the prediction of acute kidney injury in patients with sepsis，
DOI 10.1186/s12967-022-03364-0。
repeat-analysis.json 包含1项研究、partial_overlap比较、2个候选缺口；
数据/方法/验证为conditional，compute为unknown。方法、数据、指标、结果、局限等有提取；
不是专家确认或可行性证明。
补跑成功处理 W4411994860（DOI 10.1093/jamiaopen/ooaf065），48块入库并检索3片段；
W7166805379成功解析56单元但Embedding超时。
补跑analysis保存于 ../live-report-planner-hot-20261101/hot-analysis.json。

## 缓存与最终报告
第二轮之前仍为空库，不是热运行。补跑前库有1篇33向量，但选中其他论文，
所有实际cache_load仍为miss。补跑后有2篇81向量，不能称热缓存复用通过。
选中论文受真实规划/筛选输出影响；没有为命中缓存强制换结果。
唯一正式返回的Markdown为 cold-report.md：insufficient_evidence、verification_incomplete、
没有可支持结论的引用。后两次虽中间报告构建返回，但最终ResearchService.report抛出，
没有最终Markdown，不得把中间步骤当作整体通过。

## 剩余阻断
P0：当前默认预算下，反馈流程在已有分析后耗尽期限，导致最终结果丢失；
全文阶段也多次在Embedding中用尽剩余时间。需下一任务根据已测阶段耗时设计
有界预算/反馈停止条件，再单独测试；本轮未扩大范围修改。
P1：规划虽三次通过仍产生不同词面检索式，直接查询有时0命中、补充查询有命中；
发生过openalex_assessment_invalid；PDF解析有fontTools缺失警告，未安装依赖，
成功解析不证明字体/正文质量全面正确。
原始模型响应已保存，后续可回放。提示澄清不保证未来所有模型输出有效。
历史失败记录保留，未宣布任何Phase或整体正式验收通过。
