# 两轮真实正式报告入口验收（2026-11-01）

## 结论：未通过
用户已解除付费调用阻断。使用现有真实DeepSeek/OpenAlex配置、真实本地E5与独立验收库，
通过当前源码 open_research_service → ResearchService.report 执行两次同一科研想法。
没有Mock、没有改写模型输出、没有修改业务代码或超时配置。
两轮均在真实模型返回后的QueryPlan校验失败，未进入在线检索或全文阶段。
第二轮仅是重复执行：第一轮没有形成缓存，不能标为热缓存验证。

## 命令与证据
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_reports.py
```
脚本只在独立库 clinical_agent_test_governance_20261101_retry1 上配置缓存写入；
实际两轮未到达写入阶段，前后缓存索引及向量均为0。
完整样例和时序结果见 events.json。脚本使用只转发原始实现的测量包装，
不改变返回值或流程；已有输出目录会阻止无意覆盖，复跑需使用新的产物目录。

## 实际结果
| 环节 | 冷缓存调用 | 第二次调用 |
|---|---:|---:|
| 规划 | 失败，4.609秒 | 失败，3.985秒 |
| 报告入口总耗时 | 4.625秒 | 4.000秒 |
| 错误码 | extraction_failed | extraction_failed |
| 缓存索引/向量 前→后 | 0/0 → 0/0 | 0/0 → 0/0 |
| 检索/筛选/全文/RAG/分析/报告审核 | 未执行 | 未执行 |

本次E5加载32.610秒，在Graph总期限开始前完成。正式预算仍为90秒，
生成预算60秒；本次不是超时，没有依据扩大预算。
没有最终Markdown科研报告，也没有报告审核状态。

## 诊断（执行终端观察到的安全日志）
两轮均为 stage=plan, failure_kind=plan_validation,
rule_code=expansion_not_anchor, field_paths=concept_relations.required。
响应摘要：
- 冷：14637d825f2d4a7e8034390661a96849bc77053c88427356f8dd295c7db6c993
- 重复：fbe8c4a5dde28affcc4d2a4189b3f14dcf169df9ff504db039f1623c7b117576
这些诊断从本次工具执行输出转录；原始模型响应未保存，不能确定具体哪个概念被错标。

src/clinical_agent/domain/pico.py:validate_provenance 在 required=true 且 relation为
narrower_concept/broader_concept/related_concept/optional_constraint 时拒绝计划。
因此已确认真实模型输出与既有检索计划契约不一致，而非认证失败或下载失败。
未放宽该门禁，未用人工计划绕过。

## 后续最小工作建议
P0：另行修复规划输出与契约的不一致。先安全保存失败结构化响应供复现，
为扩展关系不得成为required锚点编写回归，检查提示词/输出schema的一致性；
如确有必要再增加有界纠错，不能静默把必需约束删除或放宽现有校验。
P1：规划修复后重新执行同样例真实两轮，验证下载、缓存复用、证据分析与报告；
此时才能测量90秒预算是否合理。
本轮不进入代码修复，不以此前离线通过替代本次真实失败。
