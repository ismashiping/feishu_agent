# 通用模型 API 边界调整

日期：2026-10-27，按用户进一步澄清修订。

## 需求与目标
LangGraph 负责 Agent 编排；LangChain 负责标准模型调用。DeepSeek 只是由 URL 配置指定的模型 API 服务商，不保留专属模块、类型、依赖、环境变量或业务分支。

## 功能边界
新增 adapters/llm.py，通过 LangChain ChatOpenAI 接入 OpenAI 兼容 Chat Completions API。需要服务支持标准消息、JSON mode、max_tokens 和非流式响应；不承诺任意供应商私有协议兼容，不读取或依赖推理扩展字段。既有 LangChainAnswerGenerator、LangGraph 状态和领域引用规则保留。

## 输入输出与数据模型
LLMSettings 显式读取 LLM_BASE_URL、LLM_API_KEY、LLM_MODEL，URL/模型/密钥全部必填；可选 LLM_MAX_TOKENS 沿用 1–4096、默认1500。密钥为 SecretStr，不自动读取 .env。URL 支持 HTTPS，自带凭据、查询、fragment 禁止；HTTP 仅支持本地回环调试。URL 路径前缀与 /v1 由配置提供，不绑定供应商域名。

open_llm(settings, transport=...) 上下文创建/关闭受限 HTTPX 客户端，返回供应商无关 LangChainAnswerGenerator。输入 GenerationInput 和 timeout_seconds，输出原始 JSON 字符串交由 parse_draft/build_answer 校验。

## 异常处理
保留 generation_timeout/generation_failed/model_output_invalid、响应128000字节限制、单次调用、禁用追踪/重定向/自动重试/环境代理。并发请求不共享可变超时状态；配置验证先于资源创建。移除旧供应商入口，不提供专属兼容别名。

## 测试场景与验收
先将协议测试改为通用模块并增加两个不同URL/模型可切换的测试，确认模块缺失 RED，再实现 GREEN。覆盖路径前缀、配置必填/密钥隐藏/URL验证、超时/错误/截断/超大响应/资源关闭，运行真实 ChatOpenAI + MockTransport；CLI/API/飞书装配与部署配置全部迁移。运行完整默认回归、Ruff、mypy、锁一致性；不发送付费模型请求。当前源码不再出现 DeepSeek 标识或域名；示例只在 LLM_BASE_URL/LLM_MODEL 中使用供应商值。同步当前文档和学习说明；历史真实调用证据保留时点。
