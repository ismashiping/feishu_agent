# 开发、运行与部署

适用范围：当前入口及操作导航。具体参数以CLI help、源码和下列专门指南为准；历史实验不能当成当前环境验证。

| 任务 | 权威操作说明 |
| --- | --- |
| Python 3.12准备/工程基础 | [Phase0教材](../learning/phase-00/README.md)、[原环境与wheel实验快照](../archive/readme-before-governance.md) |
| CLI安装、导入、问答/分析/报告 | [CLI指南](../cli.md) |
| API配置、路由、错误与容量 | [API指南](../api.md) |
| 共享镜像、Compose迁移与启动、飞书SDK | [运行时部署指南](../feishu-runtime.md) |
| 数据库模型与迁移 | [PostgreSQL](../postgres.md) |
| 本地模型与身份校验 | [Embedding](../local-embedding.md) |
| 模型调用及通用供应商配置 | [RAG指南](../basic-rag.md)、[模型边界契约](../specs/tasks/langchain-model-boundary.md) |
| 测试标记及外部前提 | [测试策略](../testing-strategy.md) |
| 知识版本、治理、同步、重建 | [Phase8操作导航](../learning/phase-08/README.md) |
| 评价复算 | [evaluation说明](../../evaluation/README.md)、[Phase9教材](../learning/phase-09/README.md) |

基础开发使用根README的`uv sync --frozen --all-extras`；仅安装core时不应执行依赖extras的全量测试。保留已有.env并对照示例补充，勿覆盖有效配置。外部服务测试按各冻结SPEC准备隔离资源，不能指向业务库。运行前先阅读 [当前状态](../development-plan.md)，区分工程通过和医学待审。
