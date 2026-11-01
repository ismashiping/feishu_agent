# 第二阶段补验结果（2026-10-29）

## 本轮完成

1. 在现有API容器中新建 `/tmp/openalex_stage2_followup_20261029_1`，将当前工作区src复制到独立目录，通过PYTHONPATH使用它。复用容器模型/LLM/数据库环境，不覆盖/app、不重启/重建API或机器人，不迁移或发布文献，不发送飞书消息。独立ResearchService实例关闭全文补充，避免全文缓存写入。
2. 实际执行“肝脏分割最新研究有哪些？”：真实本地检索、OpenAlex、规划/筛选/生成及引用门禁，状态answered，引用4篇OpenAlex论文，retrieval_scope=hybrid，warnings为空。耗时79.094秒，含独立实例模型校验/加载，不是服务稳态延迟或P95。
3. 真实结果暴露来源展示缺陷：默认渲染/audit/超长降级中写死PubMed。先加强引用往返测试，再按已校验provenance类型输出真实来源名称；历史PubMed回放展示保持原语义。不修改生成正文，不将重复免责声明当作已解决。
4. Compose共享environment补齐OPENALEX_API_KEY、OPENALEX_RECENT_MONTHS与LLM_MAX_TOKENS透传，输出预算默认4096。配置解析通过；当前运行容器未重启，这些配置尚未应用到现有进程。
5. 从旧的五题公开快照生成106条盲化复核项，保留ID、日期、摘要、hash和原问题，隐藏模型判断/排名/入选状态；人工决定和签署全部null。工程师/Agent不代签医学验收。

## 证据与可复现命令

- `hybrid/summary.json`：实际状态、来源范围和耗时。
- `hybrid/answer.json`：完整真实回答及可信引用快照。
- `hybrid/answer.txt`：修复前默认渲染，保留实际故障。
- `hybrid/answer-rendered-fixed.txt`：用修复后的renderer重放同一answer.json，不是又一次真实LLM生成。
- `review/README.md`：复核步骤；items.json、decisions.json、signoff.json：材料与空白待签署。
- `tests.txt`：`.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_openalex.py tests/unit/test_feishu_sender.py tests/unit/test_answer_synthesis.py -q --basetemp=.pytest_openalex_followup`，113 passed，5.98秒。
- `ruff.txt`：`ruff check src tests scripts/openalex_hybrid_check.py scripts/prepare_openalex_review.py`，通过。
- `docker compose config --quiet`：使用非真实占位DB密码完成结构解析，退出0，未打印实际环境值，不代表密码或部署已验证。
- `python scripts/prepare_openalex_review.py`：生成106项；检查review_id唯一、模型标签未混入、人工决定/签署为空，通过。脚本拒绝覆盖已有复核批次，重新生成应另选输出目录/批次。

实际容器执行命令：

```powershell
docker exec -e PYTHONPATH=/tmp/openalex_stage2_followup_20261029_1/src -e LLM_MAX_TOKENS=4096 -e OMP_NUM_THREADS=2 clinical-agent-e2e-api-1 python /tmp/openalex_stage2_followup_20261029_1/check.py /tmp/openalex_stage2_followup_20261029_1/result
docker cp clinical-agent-e2e-api-1:/tmp/openalex_stage2_followup_20261029_1/result docs/openalex-stage2/followup/hybrid
```

本轮只在已运行容器上验证，不调用带表清空逻辑的数据库测试。没有把本地生产库当可重置测试库。网络与Docker访问在沙箱外授权后执行，没有申请或执行重启、飞书发送。

## 这次结果能与不能证明什么

hybrid链路正常完成，说明本地检索路径和在线路径都可运行；但最终4个来源全部来自OpenAlex，不能据此声称复用了某篇本地缓存论文。空warnings只描述这次调用，不证明服务稳定性。

回答具有真实论文来源、日期和定位、引用标识门禁通过，但语义支持/关键数值/研究代表性尚未获独立医学签署。正文仍偏逐篇复述，存在摘要与截断免责声明重复，作为第四阶段的真实负面样例保留。未在第二阶段提前重写综合回答逻辑。

没有测试真实飞书发送、全文、向量化更新、冷/热缓存性能或Token账单；没有把旧的五题计数当Recall。人工复核还未完成，所以第二阶段完整科研质量验收仍开放，不自动进入第三阶段。

## 修改范围与下一步

新增scripts/openalex_hybrid_check.py、scripts/prepare_openalex_review.py和本目录材料；修改docker-compose.yml、src/feishu/sender.py、tests/unit/test_openalex.py，补验SPEC为../integration-spec.md。后续先由独立复核者填写review/中的判断与签署，按失败项修复/复验；真实飞书收发需在明确的测试会话中进行，本轮未向任何人发消息。

## AI证据复核增量（2026-10-29）

[106条AI复核意见](review/ai-review.md)已交付，34条直接/36条部分相关/19条不相关/17条不确定。不是独立专家签署，专家决定文件仍空白。发现同标题同摘要不同DOI双重入选及历史论文支撑“目前”不足，AI建议修订后再验收；不因17条入选主题相关就标医学通过。生产代码本轮未改，不进入全文阶段。
