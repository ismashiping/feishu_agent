# Phase 3 P3-01 实现与验收记录

日期：2026-10-28（Asia/Shanghai）。状态：**核心实现、离线验证与学习材料已交付；真实模型与样例人工审定待完成，不标 Phase 3 全部验收。**

按 AGENTS.md.txt / PROJECT.md.txt → 开发进度 → Phase 3 SPEC → 相关服务/模型/装配/引用及测试顺序核查。原仓库没有 PICO；先冻结 [P3-01 SPEC](specs/tasks/p3-01-pico.md) 与三个测试样例，再编写测试，完成实现与教材后集中执行。未运行逐任务 RED，不补造 RED 证据。原有计划文档改动保留，历史验收不改写。

## 交付范围

- `domain/pico.py`：分类/原文 PICO/候选扩展词/span/QueryPlan 校验；保留整个原问题。
- `application/pico.py`：一次有预算的抽取，JSON 重复键/大小/来源区间验证，规划错误与超时明确失败。
- 现有 LangChainAnswerGenerator 复用标准模型/消息/HTTPX 边界；共享 ResearchService 增加 plan/clarify，不重建架构。
- CLI/API/飞书正式装配启用规划；JSON 返回 query_plan，needs_clarification 无结论/来源，飞书安全渲染 PICO 和歧义。继续使用原问题进行本地检索，原引用门禁不放宽。
- [六份学习材料与 Demo](learning/phase-03/README.md)。没有新增依赖、数据库迁移、在线检索或持久异步任务。

默认规划最多 20 秒，受研究剩余期限约束。正式问答新增一次模型调用，即使空库仍先规划；这改变原生产“空库不调用模型”的行为，操作说明已同步。仅缺 comparator 不阻断。独立 ClassificationRequest 保留原文；现有入口去首尾空白后再规划，span 相对返回的 original_question，不相对原 HTTP 字节。preserved_constraints 是保守的原文保留，不代表每条医学限制已被语义过滤。

## 实际集中验证

正式解释器 `.venv/Scripts/python.exe`，Python 3.12.16；未设置 PYTEST_ADDOPTS/PYTEST_PLUGINS。无真实模型、数据库、Redis 或飞书调用。

| 范围 | 实际命令与结果 |
| --- | --- |
| 首次目标测试 | `-I -m pytest tests/unit/test_pico.py tests/integration/test_pico.py -q`：2 collection errors，测试未显式 UTF-8，属测试前置错误，不是功能 RED |
| 编码修复后 | 38 passed /1 failed /1 deselected，6.97 秒；CLI 测试误 patch 了导入后的符号，改用既有 research_factory 注入，不改产品契约 |
| 首批目标通过 | 同目标命令：39 passed /1 deselected，4.05 秒；target-final.txt |
| 完整默认离线回归 | `-I -m pytest tests -q --basetemp=.artifacts/p3-01-20261028/pytest-regression -o cache_dir=.artifacts/p3-01-20261028/cache`：1080 passed /96 deselected /1 既有 SDK 弃用警告，124.93 秒；regression.txt |
| 最终相关联合验证 | `-I -m pytest tests/unit/test_pico.py tests/integration/test_pico.py tests/unit/test_command_runtime.py tests/unit/test_api_runtime.py tests/unit/test_langchain_generation.py tests/unit/test_package.py -q --basetemp=.artifacts/p3-01-20261028/pytest-final-joint -o cache_dir=.artifacts/p3-01-20261028/cache`：111 passed /1 deselected，64.50 秒；final-joint.txt |
| 质量 | `-m ruff check src tests docs/learning/phase-03/demo.py` 通过；`-m ruff format --check src tests docs/learning/phase-03/demo.py` 87 文件已格式化；`-m mypy src --cache-dir .artifacts/p3-01-20261028/mypy-cache` 41 源文件通过 |
| Demo/静态文档 | `-I docs/learning/phase-03/demo.py` 返回合法 partial 计划；新增文档链接/围栏/空白核查通过；`git diff --check` 通过 |

完整回归之后增加了 8 项 PICO 错误映射/阻断/预算/状态测试及装配断言，以上最终联合验证已覆盖；未把这些新增项计入此前 1080，也不虚构最终全量数。首轮 mypy 的错误码 Literal/渲染变量类型问题均已修正并复验。格式检查同时规范了既有模型测试的一处换行。

两个既有 external CLI/API 真实模型/数据库链路测试的 HTTP 替身已适配“先规划后回答”两次调用，仍在默认排除范围，本次未重跑真实 E5/PG；不以其源码修改声称真实服务通过。无存储/Redis算法变化，不重建服务或容器。

## 未验收项

进程环境和本地 .env 均未提供 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL，真实模型三个样例未执行，0 次付费请求；未读取其他供应商密钥来替代配置。tests/integration/test_pico.py 的 external 入口配置缺失会明确失败，不 skip 假装通过。需在用户本地显式配置 LLM_* 后集中运行 `-I -m pytest tests/integration/test_pico.py -m external -q`，最多三个抽取请求，不做生成或自动重试。

固定数据集 pico-cases-v1 是合成开发样例及候选标注，尚无人类审定；真实分类/PICO 语言理解与医学适用性不能由 Fake 或切片校验证明。需人工确认标注及真实输出，才能满足 Phase 3 的真实样例验收。fixtures SHA256：`dba7ef335f89c911c69d278d100a7a96bac9e67a6f763229ad74e0e2868820e1`，未根据跑分修改标签。

Phase 1 医学人工签署及模型接口迁移后容器复验的原缺口保留。本次不进入 Phase 4，不执行延期 Phase 2/8/9，不创建 Git 提交。
