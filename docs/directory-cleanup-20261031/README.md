# 目录清理：2026-10-31

后续清理：已删除 `.uv-fulltext-cache/`（2359 文件，97930017 字节），依赖后续可能需要重新下载；清单见 [依赖缓存](dependency-cache-deleted.json)。此前保留的根目录备份与调查文件已迁入 [历史归档](../archive/README.md)，19 个归档文件按 Git 换行过滤规则计算的内容哈希与 HEAD 一致（直接字节比较受 CRLF/LF 差异影响，未通过）。已更新相关验收说明和调查文档中的定位路径，历史 patch 与盘点记录保持原样。下文保留项描述为首轮清理时点。

本次仅治理可重建的测试临时目录和 Python 字节码缓存，不修改业务实现、测试断言和阶段验收状态。

## 删除依据

根目录可访问的 `.pytest_*` 目录均无 Git 跟踪项、无重解析点；活动源码、脚本、CI 和部署配置未引用这些路径。目录内容为 pytest `tmp_path` 生成文件。`test_tampered_evidence_is_not_*` 内证据是 `tests/unit/test_minimal_baseline.py` 从 `evaluation/minimal-v1` 复制的副本；评估输出来自 `tests/integration/test_evaluation.py`，不是正式验收报告。历史文档中的命令仍保留，重跑时可重新生成临时路径。

同时删除 src、tests、scripts、alembic、docs 下无 Git 跟踪的 `__pycache__`。删除前逐个校验解析后的绝对路径位于仓库内、递归读取成功且不存在重解析点。逐目录文件数和字节数见 [删除清单](deleted.json)。补充根 pytest 临时目录忽略规则，避免未来误入版本控制；已跟踪的历史文件不受该规则影响。

## 保留项

- `.pytest_evidence`、`.pytest_plan_diag`：访问被拒绝且有历史 Git 跟踪项，未删除、未修改权限；Git 原有缺失显示不能视为本次删除。
- `.artifacts`、docs、evaluation：含验收原始证据、历史失败和学习文档，保留。
- `.quality-backup`、investigation-baseline.txt、recall-before.txt：历史备份与调查依据，保留。
- `.tools`、`.venv*`、`.research-cache`、`.uv-fulltext-cache`：运行环境或依赖重现资产，保留。
- `.git`、`.github`、`.env`、data、models、迁移、源码与部署文件保留。

## 验证边界

仅执行删除范围、Git 跟踪、路径边界及残留检查，未运行 pytest、外部依赖或阶段验收。仓库已有大量未提交变更，本次不覆盖。此前完整回归失败和未验收事项保持原状。未推进新阶段。
