# 科研可行性重构集中验收（2026-10-30）

状态：离线集中检查完成（范围见下）；真实四题及飞书实收进行中，完整阶段未验收，不代表医学通过。

## 命令与实际结果

- 初始新增路由/身份/可行性/worker批次：85 passed、2 failed；失败为旧路由fixture缺新增四维输出，已修复，原输出由会话保留。
- 默认python执行pytest：收集阶段GBK解码失败，122 deselected，不视作业务断言通过。原始输出：[记录](../refactor-test-output.txt)。随后明确使用-X utf8。
- `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.pytest_refactor_full_utf8 --tb=short`：1440 passed、1 failed、122 deselected，181.26秒；失败test_hybrid_default旧替身缺respond。原始输出：[全量记录](../refactor-test-utf8-output.txt)。
- 补齐测试替身后，受影响hybrid_default/intent/identity/feasibility/citation_report/feishu_sender/main/worker批次：250 passed、2 SDK弃用警告，30.02秒。[最终受影响记录](../refactor-final-output.txt)。没有冒称最终全量1441项重跑。
- Ruff check src tests及实时检查脚本通过；format --check通过。先前embedding切片与fulltext测试引号格式问题仅作格式修正，无行为变更。[check](../refactor-ruff-final.txt)、[format](../refactor-format-final.txt)。
- 默认pytest排除external/performance/database/redis；122项未选中不算通过。未重新执行独立负载评测或全套真实数据库/Redis marker测试。

## 实现与验证范围

单次规划task_intent→同图路由；paper_target锚定原文，四HTTP内直接/技术路线/瓶颈查询；DOI/题名匹配与来源支持的方法身份判断区分；四维可行性与候选实验进入原引用/支持度审核。飞书默认报告中文标签、来源与实际证据层级，审计保留内部信息；原分片/租约/投递机制复用。

原四题业务失败与无证据记录仍保留；合成测试不证明模型意图准确或科研/医学质量。

## 部署

基于已锁定依赖镜像使用docs/openalex-stage4/Dockerfile.update离线重装源码；候选镜像config=92aba8536130702c22abd242cf9fb6ba7fe24f50cf85914cbed862e833099e10。旧local config=118c7cd9d85e5d5a054d786c739845911922ac7da32d0340269bed204f355d75另存before-research-refactor-20261030。部署命令为scripts/oa_stage3_deploy.py recreate，不执行迁移或卷重置；实际健康与真实结果追加于下文。

## 教材与未验证范围

[六份学习材料及最小合成Demo](../learning/phase-04/research-feasibility/README.md)。教材面向实际代码，验收未完成不标阶段完成。下一步仅完成本阶段真实四题和用户飞书实收；没有后续阶段开发。
