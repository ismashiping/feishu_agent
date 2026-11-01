# 回归归因与临时文件治理：2026-10-31

本任务为专项归因/治理，不是新业务阶段。未更改证据门禁、引用规则、测试断言、数据库、模型或部署。

## 逐项归因与修复

[37项逐项归因](failures.md)逐行列出原nodeid、分类、调用者/fixture及代码因果。分类3共8项：其他未验收增量使CLI local业务拒绝早于输入验证，已将拒绝移至QuestionRequest/检索参数验证之后。有效local仍返回local_corpus_not_evidence，非法输入返回invalid_arguments/退出2，且不装配资源。未将该业务改动归咎于共享科研装配。

分类2共8项：测试实际注入PubMedRetrievalService，当前Scout在其搜索调用前拒绝；当前架构明确Works唯一发现源、摘要只筛选。旧PubMed摘要回答和混合本地/在线分派断言已与该当前契约冲突。保留历史测试，未改断言或恢复PubMed科研证据路径。

分类5共21项：API/CLI真实调用在local门禁处终止，完全不进入所注入服务。触发原因已确定，但旧MVP/P4/混合检索SPEC及公开Schema允许local，当前文档排除历史摘要，并不足以自动证明所有本地PDF都应被禁用。此范围决策仍阻塞；不撤门禁、不假改测试。本轮未发现37项中可确认的共享装配真实回归，也没有证据将它们归为外部环境故障。

## 目录治理

[完整逐目录盘点](directories.json)记录全部根隐藏目录以及build/data/models：文件类型、样本路径、Git跟踪、仓库引用及读取错误。工具/环境/模型/数据仅查看顶层，不读取秘密内容，不遍历资产内部。Git目录仅查看顶层，跟踪统计不表示Git内部文件可删除。

实际删除：11个无文件、无Git跟踪、无仓库引用且无读取错误的旧pytest目录（含空子目录），清单见[删除目录](deleted-empty-directories.txt)；3个自带工具生成标识的旧缓存目录（.pytest_cache/.ruff_cache/.mypy_cache），见[缓存清单](deleted-caches.txt)；build仅包含64个lib下Python副本，每个均有对应src文件，无Git跟踪、无其他文件、无重解析点，作为可重建包产物删除，见[构建清单](deleted-build.txt)。删除前均检查解析后绝对路径位于当前仓库内。

保留：.artifacts混有原验收记录和临时数据（且有读取错误），禁止整目录删除；.pytest_evidence/.pytest_plan_diag各有200个Git条目及读取错误，禁止删除；被历史命令引用的pytest目录保留，未引用但非空的旧测试目录未证实退出条件也保留。.quality-backup为受跟踪备份；.research-cache含研究/离线依赖重现资产，.uv-fulltext-cache为依赖缓存，均保留；.tools及全部.venv*为运行环境；.git/.github及data/models保留。没有把不可访问目录误记为空。

## 测试产物统一

pyproject将pytest/ruff/mypy缓存统一至.artifacts/tmp下。新pytest运行使用原生--basetemp=.artifacts/tmp/<独立运行名>；先创建父目录，每个并行进程独占路径，xdist仍用pytest原生worker隔离。未在pytest addopts硬编码共用basetemp，避免并发互删。

长期日志/JUnit/报告保存docs/<任务>/<批次>，不放basetemp中；本轮证据位于本目录。.gitignore说明生成区与长期证据边界，未忽略docs或tests/fixtures、未用忽略规则隐藏失败。历史SPEC/验收命令不改写；脚本/CI未发现活动basetemp需迁移，CI原生临时路径保留。操作约定已追加至[测试策略](../testing-strategy.md)。

## 真实验证

环境：Windows/PowerShell，仓库.venv Python3.12，使用-X utf8；默认pytest标记排除external/performance/database/redis。

1. 首次专项因未创建嵌套basetemp父目录：49 passed、14 errors；首次完整：1176 passed、18 failed、315 errors、122 deselected。此为本轮命令环境准备错误，已保留targeted-missing-parent.txt及full-missing-parent.{txt,xml}，不能用于判断业务回归。
2. 创建.artifacts/tmp父目录后受影响专项：**63 passed、0 failed、0 skipped**，见[targeted.txt](targeted.txt)。包含9个非法输入参数用例、runtime和全文等原断言。
3. **最新完整离线回归：1480 passed、29 failed、122 deselected、0 skipped、0 errors、1 SDK弃用警告，159.04秒**，见[full.txt](full.txt)和[full.xml](full.xml)。与旧1468/41结果分开，未把修复前日志当最新结果。余29项均为表中的8项旧PubMed契约及21项local范围冲突；没有本轮新增失败。
4. 配置调整后再次使用新cache/basetemp验证：9 passed，见[config-check.txt](config-check.txt)。完整回归执行期间只调整缓存目录配置，业务源码未再修改；缓存配置另经该专项验证，未再次全量执行。
5. Ruff src/tests通过；CLI格式检查通过；本轮文件git diff --check通过。Ruff含scripts仍有17个E402，来源为原已禁用的两个PubMed脚本顶部SystemExit后的历史import，保留已存在的用户改动，不借本任务重写脚本。

### 实际命令

```text
.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources tests/unit/test_api_runtime.py tests/unit/test_command_runtime.py tests/unit/test_oa_fulltext.py tests/unit/test_fulltext_rag.py tests/unit/test_research_quality_v2.py -q --tb=short --basetemp=.artifacts/tmp/attribution-targeted
.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/attribution-full --junitxml=docs/regression-attribution/full.xml
.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_command_cli.py::test_invalid_input_never_assembles_resources -q --basetemp=.artifacts/tmp/attribution-config
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/ruff.exe check src tests scripts
.venv/Scripts/ruff.exe format --check src/clinical_agent/cli.py
git diff --check -- src/clinical_agent/cli.py pyproject.toml .gitignore docs/testing-strategy.md
```

## 未完成与边界

local业务范围需明确：是否保留本地PDF研究入口，或正式退休全部local公开能力；之后才能统一SPEC、schema和测试。旧PubMed工作流测试是否迁为历史范围/新OpenAlex测试也需按契约处理，本任务不静默删除测试。真实数据库/Redis、模型、飞书、在线下载、远端CI及医学人工审查均未运行，122项排除不计通过。完整离线回归仍未通过；不进入新Phase或继续框架迁移。
