# Docker真实端到端验收尝试

日期：2026-10-29。本轮仅新增日志与本记录，未修改生产源码、Compose、Provider配置、查询规则或测试；未重跑1097项unit。既有工作区、备份和卷保留。

## 实际执行及Docker资源

项目固定为`clinical-agent-e2e`。初始容器0；只启动postgres，最终容器1、healthy；没有启动redis、API或bot，因真实LLM配置缺失，启动它们不能完成科研验收。

启动命令：`docker compose -p clinical-agent-e2e --env-file .artifacts/docker-e2e/compose.env up -d --wait postgres`。重复执行一次核验幂等复用，前后ID均为`9c92ff7c8f34`，名称`clinical-agent-e2e-postgres-1`。详细身份见containers-before.json、containers-after.json；全局列表all-containers.txt只有此容器。compose-start.txt、compose-reuse.txt、health.txt保留原输出。

复用现有固定digest的pgvector/pgvector:0.8.7-pg16镜像，未build、force-recreate、down、prune。首次创建该项目网络及独立命名卷clinical-agent-e2e_postgres_data，旧卷未删除或重建。旧卷属于其他项目、密码未知，未直接挂入以免修改原数据。新卷为空时Postgres正常首次初始化；不是清空旧数据库。

独立数据库clinical_agent_e2e，127.0.0.1:55432。因未配置数据库密码，为本次全新隔离数据库生成随机密码，仅保存在git忽略的`.artifacts/docker-e2e/compose.env`，不写入验收日志、不修改生产凭据。该文件同时供后续复用服务使用，不应删除后另造密码。

psql只读检查current_database及to_regclass('public.alembic_version')：迁移表不存在，见migration.txt。未无条件执行迁移或reset。LLM阻塞时没有实际工作流消费数据库，因此未继续做schema写入。保留服务正常运行。

## LLM配置真实诊断

config.json仅记录是否存在及脱敏地址/模型；结果：当前进程和本地.env均无LLM_API_KEY、LLM_BASE_URL、LLM_MODEL。Database password初始也不存在。项目.env.example明确仅为示例且应用不自动加载.env；其中deepseek示例不能当成用户已配置Provider。

实际代码adapters/llm.py采用OpenAI-compatible接口，三个字段均必需，env_file=None。Compose将这些字段从调用环境/.env插值到API环境，当前缺失会成为空值，无法通过LLMSettings。未启动一个必然缺少配置的API服务，也未发付费验证请求。实际Provider、模型、URL未知，不能报告示例值为实际服务。没有切换Provider或向其他账号索取密钥。

当前clinical-literature-agent:local镜像ID为013d6909cef814039ea1f610e5bd4f4c1f60fc65e683714d2bde603266e50a9c，创建于2026-10-27，早于第二阶段修复。直接使用它不能证明当前工作区实现通过验收。鉴于凭据阻塞，本轮未无故重建镜像；恢复凭据后还需明确采用当前源码镜像或只读源码挂载，并记录版本身份。

## 中英文真实检索、回答及成本

两题均not_executed：实际QueryPlan、ESearch query_text、querytranslation、匹配数、返回PMID、过滤/选择/引用去向均unknown。没有使用Mock、手写查询、指定PMID或旧镜像结果冒充。没有自然检索，因此不能判定三个已知PMID在候选中是否出现。

上轮独立真实摘要仍在上级independent-pmids.json；本轮没有重复获取，也没有将其注入证据。没有实际生成的科研回答，故研究对象、方法、引用支持、过度推断及正文可读性均未验收。

本轮LLM请求0，模型token消耗0（没有模型调用），PubMed HTTP请求0，真实工作流执行0。没有调整90秒deadline、24000字符、top_k、max_results、HTTP尝试数或新增调用节点。没有运行report，累计反馈及核验请求路径未验证。

## 结论和后续必要条件

通过：真实Docker PostgreSQL启动、健康检查、固定项目名复用、容器ID稳定、无重复容器、旧数据保留。

阻塞：有效LLM Provider配置缺失；真实Docker应用服务、真实中英文科研端到端验收未完成。数据库尚未迁移；应用镜像早于当前修复，恢复验收时需处理当前源码运行身份。必要输入为用户既有Provider的有效LLM_API_KEY、LLM_BASE_URL、LLM_MODEL，需通过既有安全配置方式提供，不能贴进审计文档。

本轮没有把环境健康等同于科研能力通过，也没有将上轮unit通过或独立PMID获取等同于本轮端到端成功。
