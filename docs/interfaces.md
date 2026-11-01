# HTTP 与命令行契约

HTTP 工厂：clinical_agent.api:create_app。具体 JSON schema 由运行实例 /openapi.json 提供。

| HTTP 路由 | 输入与行为 |
| --- | --- |
| GET /health/live | 进程存活 |
| GET /health/ready | runtime 是否完成装配，不代表外部医学链路已通过 |
| POST /v1/documents/import | source_type=pdf、relative_path；限制在服务端 import_root 内 |
| POST /v1/questions | question、scope、options，生成带来源回答 |
| POST /v1/analyses | 同类输入，返回结构化分析 |
| POST /v1/reports | 同类输入，返回审查后的报告结果 |

公开 scope 仅 online / hybrid，默认 hybrid。两者在当前生产装配中均通过 OpenAlex 发现论文，hybrid 保留为现有协议值，不代表本地联合召回。local 在 API 输入校验返回 422，CLI 参数解析退出 2，不进入科研服务。

请求可带 X-Request-ID；返回 request_id 与响应头关联。HTTP 有请求体上限、错误脱敏、运行就绪门禁和有界并发。超时映射 504，资源忙映射 503；具体错误映射见 api/execution.py。不要将输入不合法解释为上游故障。

CLI 参数以 `clinical-agent ask --help` 为准。旧 PubMed 参数仍有明确退休拒绝逻辑；非 vector 查询模式不属于当前科研能力，不应用作本地召回入口。入库与问答是两个独立用途。
