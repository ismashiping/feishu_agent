# Docker恢复与真实审核验收（2026-11-02）

## 环境恢复事实
Docker desktop-linux/default两上下文均无旧容器、镜像和卷，无法声称恢复旧缓存。
找到 .artifacts/docker-e2e/compose.env 原验收配置；只在进程内使用，未输出凭据。
使用锁定Compose PostgreSQL镜像恢复服务，创建新独立数据库
clinical_agent_test_context_20261102，显式Alembic upgrade head到oa3003_0011。
未删除卷或旧数据、未改密钥。数据库库与缓存为新建，不冒充旧库恢复。
本轮恢复数据库依赖并使用本地当前源码正式ResearchService.report装配科研运行服务；
未构建API容器、未恢复飞书机器人、不声称HTTP部署验收。

```powershell
docker compose --env-file .artifacts/docker-e2e/compose.env up -d postgres
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/restore_test_db.py
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_reports_restored.py
```
拉取既有Compose锁定镜像，不安装/升级Python依赖。恢复脚本拒绝复用未知已有库。
原同一中文ICU/AKI想法，真实模型/OpenAlex/E5，正式报告入口，无Mock，预算180s。
E5冷加载103.563s发生在Graph计时前。

## 真实结果
| 阶段 | cold | repeat |
|---|---:|---:|
| 规划 | 4.531s | 4.406s |
| 检索含筛选 | 22.703s | 12.610s |
| 全文RAG | 61.844s | 61.969s |
| 分析 | 9.750s | 9.484s |
| 报告组装和支持度审核 | 5.172s | 4.094s |
| 总时间 | 104.156s | 92.641s |
| 完整报告 | 返回 | 返回 |
| 状态 | partial / verification_incomplete | partial / verification_incomplete |
| feedback_stop | budget_limit | no_actionable_feedback |
| 真实模型审核论断数 | 23/23 | 26/26 |
| supported / partially_supported / uncertain | 9/10/4 | 23/2/1 |
| 证据指针原句检查 | 26/26通过 | 29/29通过 |
| 实际cache_load命中 | 0 | 0 |
| 索引/向量 前→后 | 0/0→1/27 | 1/27→2/75 |

首轮使用 DOI10.1136/bmjopen-2021-054092 全文，解析21单元、27块入库。
第二轮使用 DOI10.1093/jamiaopen/ooaf065 全文，解析41单元、48块入库。
两轮均有另一篇已解析但Embedding阶段期限耗尽，后续未处理项警告保留。
本次全文60秒为协作期限，编码调用完成后检查可能使阶段实际略超60秒；
总调用仍在180秒内，不声称严格抢占式60秒。
首轮候选筛选有一次model_output_invalid，补充筛选成功，记录保留。

## 审核与边界
最终Markdown和JSON：cold-report.md/json、repeat-report.md/json；
原始检索、规划、分析、时序和审核摘要同时保存。
分批审核实现的真实模型路径已执行，所有论断有审核basis，无上下文跳过提示。
本轮没有单独记录每个review_claims子调用，因此不声称真实运行必然拆成多个批次；
多批上限和恰好覆盖由前轮离线回归验证。
两轮四维可行性均存在；compute unknown，其他为conditional或reported_barrier，
后者仅指论文报告限制，不证明用户条件相同。模型支持度不是独立医学人工签署。

结论：Docker数据库依赖和当前源码正式科研服务已恢复，真实分析、审核、最终报告返回
通过运行验证；部分支持/不确定项如实保留，整体正式医学质量验收不标完整通过。
实际热缓存未命中：在线规划/筛选本次选择了不同论文，未强制替换结果。
新库最终保留2篇75向量，后续可继续验证正式入口实际复用。
HTTP部署、机器人实收、原数据恢复、全套离线回归本轮未执行。
