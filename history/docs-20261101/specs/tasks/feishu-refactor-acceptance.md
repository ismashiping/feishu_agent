# 飞书呈现与端到端集中验收

2026-10-30。范围：复用现有有界分片与Sender，报告默认仅展示研究问题、已有工作/路线/相似性/瓶颈与机会、中文事实/推断/假设及支持状态、待验证项、可点击来源与实际证据层级；审计输出保留计划/检索JSON、内部ID与hash。拒绝发布和证据不足须明显保留。分片完整且保留引用，不新增发送重试。

先补默认呈现/审计分离、引用/证据层级与拒绝状态测试，再实现。集中验收覆盖前3个任务新增测试、worker/sender/main、pico/OpenAlex/analysis/report/反馈和默认离线回归；Ruff全src/tests。失败修复后重跑受影响范围，保留首次失败。默认排除external/performance/database/redis，不视作通过。

通过离线门槛后，复用Dockerfile.update离线安装锁定依赖，备份当前local镜像标签，重建API/机器人，不迁移/清卷。真实四题通过同容器open_research.respond与飞书渲染检查，记录输出、意图、耗时、错误码、引用与内容局限；同容器回放不等于真实飞书实收。用户在飞书发送四题后核对request_id接纳/处理/投递与用户完整实收。未收到确认、真实失败或医学未签署保持开放。

命令：项目Python -m pytest（默认markers），Ruff check src tests及format --check src tests。受影响新测试批次见各任务SPEC。真实脚本scripts/research_refactor_live.py复制入机器人容器后执行，逐题保存独立结果，不覆盖旧证据。容器操作需Docker权限；凭据只从已配置环境读取，不打印。新增学习文档基于本轮真实代码和实际结果，不声称尚未通过的范围已验收。
