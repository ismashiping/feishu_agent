# 第二阶段补验任务冻结范围（2026-10-29）

目标：一次真实混合检索→现有生成→引用门禁验证，以及独立医学复核材料准备。不是第三阶段。复用运行中的API容器环境、只读已有文献库和/app/model；在独立/tmp目录载入工作区源码，不改服务镜像，不迁移或发布文献，不重启，不发飞书消息。该任务不代替独立医学签署。

输入：固定问题“肝脏分割最新研究有哪些？”，现有runtime与环境，已保存live-check.json的公开候选。输出：独立保存实际问答JSON/飞书可读文本、耗时、来源范围/引用核验和失败码；复核包隐藏模型标签/排名/入选状态，按稳定hash打散。复核决定初始null、签署初始null，不由Agent代填。

异常：真实依赖失败记录稳定code，不打印凭据或SDK异常；上下文/超时/无证据保持原契约，不自动改成成功。补验脚本关闭此次新建ResearchService实例的全文补充，明确只能证明第二阶段摘要链路；服务原实例不变。现有库只读，不执行会清空表的数据库测试。

验收断言：actual runtime装配OpenAlex；local/online/hybrid范围正确；模型输入与回答citation由现有门禁验证；输出保留真实ID/日期/摘要证据；没有全文却声称全文的检查由人工逐句复核，不能拿门禁代替。部署配置补齐OpenAlex及LLM输出预算的环境透传，并用compose解析验证，不展示解析后的环境内容。测试脚本不新增业务框架。

命令：docker只读ps/exec前提检查；docker cp工作区src与独立补验脚本到新建/tmp目录；docker exec以PYTHONPATH运行该脚本，结果docker cp回docs/openalex-stage2/followup/；本地python scripts/prepare_openalex_review.py；ruff check受影响脚本；Docker Compose config --quiet（需要已有容器环境里的DB密码，不能把密码打印）。不满足真实前提则逐项记录未验证，其他可做任务继续。

## 第二阶段补验中的来源展示修复

真实混合回答证明renderer默认/audit/超长降级来源名写死PubMed。该错误属于科研来源真实性要求，纳入本阶段修复；先加强OpenAlex往返测试，按可信provenance类型显示来源名。修复不改引用内容或模型结论。实际受影响113项测试通过，见followup/acceptance.md。
