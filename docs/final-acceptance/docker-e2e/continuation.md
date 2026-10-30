# 别名配置确认后的继续验收（2026-10-29）

本记录补充并取代acceptance.md中“没有现有Provider配置”的阻塞判断：用户说明后重新检查，项目.env存在DEEPSEEK_*和NCBI_API_KEY，先前只查LLM_*导致没有识别。未将用户消息中的密钥复制进日志。

## 已完成

将现有DEEPSEEK_API_KEY/BASE_URL/MODEL映射到LLM_*，NCBI_API_KEY映射到PUBMED_API_KEY，仅写入git忽略的隔离.artifacts/docker-e2e/compose.env。实际Provider为DeepSeek，模型deepseek-chat。没有使用其他Provider；没有采用用户旧PUBMED_MAX_RESULTS=100或Embedding参数覆盖当前预算/模型契约。

对全新clinical_agent_e2e数据库执行现有Alembic upgrade head，成功；没有清空旧库。已有PostgreSQL容器继续复用。

应用服务首次启动失败：宿主8000端口已占用，隔离配置改用18080。随后API返回startup_failed。通过容器CLI调用真实command_runtime.open_research定位ModuleNotFoundError.name=langchain_openai，原local和p117-py31216两份已有镜像均缺少该已声明依赖。没有为此修改源码或依赖清单。

实际使用固定Compose项目clinical-agent-e2e，只有postgres和api两个服务，无多个项目重复实例。应用服务因端口和镜像配置变化发生必要替换；没有把这些环境修正宣称为“两题容器身份复用成功”。CLI诊断期间应用服务使用sleep命令保持可exec，健康检查关闭；这不是健康API。

override.yml保存当前只读src/alembic挂载、审计目录及线程数配置。未修改生产Compose；API命令/镜像变化均只在验收override。模型目录仍使用当前项目现有multilingual-e5快照。

## 最终阻塞

按现有Dockerfile及锁文件构建应用镜像，以补齐既有依赖。安装阶段成功（80.2秒），层导出128秒完成，写入local标签后在unpacking阶段失败：`rpc error: code = Unavailable ... EOF`，见build.txt。

随后只读docker image inspect/ps亦挂起，尚未到达真实工作流exec。该等待命令已中断，避免后台恢复后意外产生付费请求。没有重启Docker Desktop、杀死Docker后台、prune或删除任何资源。

最终引擎可达性、local标签是否完整可用、容器健康状态未知。最后已知容器2个（postgres和CLI诊断api），无多项目重复；无法在引擎失联后确认最终身份。现有镜像重建更改了local标签的导出状态，不能继续用旧镜像ID代表最终镜像。

## 真实工作流和成本

actual_workflow.py已准备为容器内真实open_research → ResearchService.answer。仅增加验收包装采集真实QueryPlan、PubMed响应、生成上下文、Provider usage及底层HTTP尝试数，不改结果，不注入候选。中英文各一次，未执行report。summarize.py用于后处理。

但是本轮尚未执行这两次流程：actual-zh.json、actual-en.json不存在，未得到真实模型结果。LLM请求0、PubMed请求0、实际token使用0。不能证明API Key有效、模型服务可达，也不能提供实际query_text、命中数量、候选或科研回答。没有以容器健康检查/独立PMID快照冒充端到端。

## 保留状态与恢复条件

需要先恢复Docker引擎可达性，再核对镜像完整性及服务状态。不要直接重跑已付费问题：先查actual-*.json和进程，确认此前工作流未运行。本轮生产源码未改，1097项unit无需重跑。

本轮通过项限于变量别名映射、隔离数据库迁移、容器内缺失依赖根因定位。真实Docker科研端到端未通过，当前阻塞由凭据命名不匹配转为Docker镜像解包/引擎连接故障。
