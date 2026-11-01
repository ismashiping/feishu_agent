# 真实环境预检与验收阻断记录（2026-11-01）

## 结论
环境检查部分通过；完整科研业务闭环因付费模型调用未获本轮授权而无法验证。
用户明确要求遇到付费 API 停止相关操作。现有配置为 api.deepseek.com，官方定价说明
模型调用按 token 收费：https://api-docs.deepseek.com/quick_start/pricing/
因此没有发送模型请求，不能判断密钥有效性、余额或模型响应契约。
未修改业务代码、安装依赖、修改数据库、执行迁移或改变密钥。

## 实际命令与产物
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/check_environment.py
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/check_openalex.py
.venv/Scripts/uv.exe --cache-dir .artifacts/tmp/live-preflight-uv lock --check --offline
.venv/Scripts/python.exe -X utf8 -m alembic heads
```
只读 docker ps/inspect 用于读取既有验收容器状态与在进程内使用配置。沙箱内 Docker
访问被系统权限拒绝，提升权限后只读检查成功。未输出密钥或完整连接串。
环境详情见 environment.json；真实查询详情见 openalex.json。

## 环境
- Python 3.12.16，关键包版本可读取；锁文件离线校验解析139个包成功。
- 现有 PostgreSQL/API/Redis 容器健康；健康不等于当前工作区已部署。
- 独立验收库 clinical_agent_test_governance_20261101_retry1 只读连接成功。
- pgvector 0.8.7；数据库版本 oa3003_0011 与当前 Alembic head 一致。
- oa_fulltext_indexes 与 oa_fulltext_vectors 均为0行；没有删除数据。
- 真实本地 E5 加载79.938秒，查询向量编码0.250秒，维度768。
- LLM配置通过Pydantic校验；OpenAlex密钥存在，但未用其执行请求。

## 在线查询
使用现有 OpenAlexClient.search，真实网络、无账户密钥；不是Mock。
人工诊断查询：acute kidney injury machine learning MIMIC ICU。
耗时1.782秒，返回10条，总命中数4238，无解析警告，记录快照一致性校验通过。
6条记录具有候选直链（分别1、3、3、3、3、3个），4条无候选直链。
9条有摘要、1条缺摘要。结果包括AKI发生预测、死亡风险及其他不同终点，
不能将它们全部视为直接相关研究。未模型筛选，不报告“筛选后数量”。

## 未执行
用户指定中文科研想法未进入正式 ResearchService.report 或 /v1/reports，
因为规划、筛选、分析和审核均依赖付费模型。
全文下载/身份解析/候选回退、正文Embedding、缓存写入、向量检索、冷/热缓存复用、
研究比较、四维可行性、Markdown科研报告和引用审核均未在本轮执行。
成功/失败下载数量均为“不适用（未尝试）”，不能记成获取失败或通过。
无最终科研报告，也无报告审核状态。

## 时间预算
总预算默认90秒；规划约20秒上限，在线检索阶段最多45秒（含筛选预算），
全文截止时间还预留30秒用于后续阶段。分析器180秒配置不能突破全流程期限。
E5在正式服务装配阶段加载，不应把79.938秒加载时间计作Graph内部90秒预算消耗，
但应计入进程冷启动体验。当前没有全链路阶段耗时或实际超时，不能断言90秒已失败。
下一步经授权运行原始默认预算，分别记录冷启动、Graph运行、筛选/网络/下载/
解析/编码/分析/审核耗时，再按实测决定有界预算调整；不取消超时。

## 剩余问题与恢复条件
P0验收阻断：付费模型调用按用户要求暂停。需要明确允许现有DeepSeek账户付费调用
及费用/运行次数上限，然后验证模型认证和正式报告入口。
P1未验证：真实全文可达性、身份解析、数据库写入/向量检索、缓存复用及90秒预算。
已观察4/10记录无直链，属于该次返回数据情况，不代表论文没有全文。
P2：本轮未引入或评估新增功能。
完整验收恢复后应使用同一中文科研想法，通过正式入口记录真实冷/热两轮；
不得把本次人工搜索或本地查询向量成功替代完整验收。
