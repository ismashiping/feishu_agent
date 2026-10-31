# 37项逐项归因

分类编号沿用任务：1真实回归；2测试与已确认当前契约不一致；3其他未验收改动；4环境；5未能确定最终契约。代码因果与规范归因分开，不凭测试名认定。

| # | 原失败 nodeid | 分类 | 已核查的因果依据/处理 |
|---|---|---|---|
| 1 | `tests/integration/test_api.py::test_question_contract_correlation_and_empty_success` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 2 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[retrieval_failed-503]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 3 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[retrieval_timeout-504]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 4 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[retrieval_corrupt-500]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 5 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[generation_failed-503]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 6 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[generation_timeout-504]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 7 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[model_output_invalid-502]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 8 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[citation_invalid-502]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 9 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[context_limit-422]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 10 | `tests/integration/test_api.py::test_error_mapping_never_publishes_raw_exception[unknown-500]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 11 | `tests/integration/test_api.py::test_full_answer_source_fields_preserved` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 12 | `tests/integration/test_api.py::test_busy_rejects_without_blocking_health_and_recovers` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 13 | `tests/integration/test_api.py::test_wrong_answer_id_is_internal_error` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 14 | `tests/integration/test_pubmed_online.py::test_online_graph_keeps_provenance_and_never_calls_local` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 15 | `tests/integration/test_pubmed_online.py::test_online_cli_api_and_feishu_render_empty_search` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 16 | `tests/unit/test_command_cli.py::test_ask_reuses_dto_and_preserves_unicode` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 17 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra0]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 18 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra1]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 19 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra2]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 20 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra3]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 21 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra4]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 22 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra5]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 23 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra7]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 24 | `tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources[extra8]` | 3 | CLI工作区门禁先于QuestionRequest/RetrievalOptions验证；参数化非法输入被抢先返回1。移动到校验后；保留所有断言，专项复验。 |
| 25 | `tests/unit/test_command_cli.py::test_ask_errors_are_closed_and_sanitized[retrieval]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 26 | `tests/unit/test_command_cli.py::test_ask_errors_are_closed_and_sanitized[generation]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 27 | `tests/unit/test_command_cli.py::test_ask_errors_are_closed_and_sanitized[unknown]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 28 | `tests/unit/test_command_cli.py::test_answered_cli_preserves_all_claim_and_citation_fields` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 29 | `tests/unit/test_evidence_analysis.py::test_evidence_analysis_cli_and_http` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 30 | `tests/unit/test_exploratory_discovery.py::test_online_dispatch_receives_plan_even_without_local_hits[None-online]` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 31 | `tests/unit/test_exploratory_discovery.py::test_online_dispatch_receives_plan_even_without_local_hits[None-hybrid]` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 32 | `tests/unit/test_exploratory_discovery.py::test_online_dispatch_receives_plan_even_without_local_hits[pubmed_timeout-online]` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 33 | `tests/unit/test_exploratory_discovery.py::test_online_dispatch_receives_plan_even_without_local_hits[pubmed_timeout-hybrid]` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 34 | `tests/unit/test_exploratory_discovery.py::test_online_dispatch_receives_plan_even_without_local_hits[pubmed_failed-online]` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 35 | `tests/unit/test_exploratory_discovery.py::test_online_dispatch_receives_plan_even_without_local_hits[pubmed_failed-hybrid]` | 2 | 实际fixture注入PubMedRetrievalService；Scout拒绝application.pubmed类型，发生于HTTP MockTransport/搜索替身执行前。当前架构明确Works为唯一发现源、摘要不得作科研证据；旧P4/探索测试仍断言PubMed摘要/合并/错误。保留旧记录，未重定义测试或恢复旧链路。 |
| 36 | `tests/unit/test_hybrid_default.py::test_cli_passes_default_or_explicit_scope[local]` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |
| 37 | `tests/unit/test_hybrid_retrieval.py::test_cli_api_and_graph_keep_keyword_strategy` | 5 | 实际请求scope=local，API/CLI门禁在注入服务调用前拒绝；测试通过factory绕过科研runtime，非共享装配或真实依赖失败。当前架构排除历史摘要，但旧SPEC01/P4/05及公开schema仍支持local；排除所有本地PDF是否在已确认契约内无法证明。保留门禁/断言，等待范围决策。 |

## 共同证据

- 原失败栈：`.artifacts/architecture-regression.txt`；本次最新结果见full.txt/full.xml。
- `git diff -- src/clinical_agent/{api,cli}.py src/clinical_agent/application/agents.py`显示上述门禁和PubMed分派均为共享装配之前已有工作区增量；上一轮架构报告明确列出了其改动文件，不包含这些业务门禁。
- API setup_api直接注入ServiceBundle和合成Research；CLI通过research_factory直接注入；探索测试直接构造ResearchService/PubMedRetrievalService，故无需真实数据库、Redis、模型或远端网络即可到达该错误。
- 当前docs/current/architecture.md明确OpenAlex-only及摘要不作证据；docs/specs/01-mvp.md、tasks/p4-01-pubmed-online.md仍记载local/online/hybrid。已确认的发现源替换与未明确的全部local入口禁用不能混为一谈。
- 类别5的21项失败技术触发点已定位；未确认的是门禁覆盖全部本地PDF的业务授权边界。不能为绿灯撤销门禁或把旧断言改成502。
- 数量：{5: 21, 2: 8, 3: 8}。没有证据将这37项归为共享装配回归或外部依赖问题。其他未验收改动的8项验证顺序问题已最小修复。
