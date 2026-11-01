# 按四个批次读真实改动

## 1. Agents

测试和教材从 `application.workflow` / `application.agents` 切到 `agents.state` / `agents.nodes`，随后删除两个别名文件。`ResearchService`、Graph 组装、节点名、边和 State 类型没有重写。

## 2. API

旧 `api_runtime.py` 曾把三个职责重新聚合：Schema、WorkerPool 和资源 runtime。调用方按真实职责改为：

- `api.schemas`：`ApiSettings`、请求响应 DTO。
- `api.execution`：`WorkerPool`、`BusyError`。
- `api.runtime`：`ServiceBundle`、`open_api_runtime`。

`clinical_agent.api:create_app` 继续由包入口提供，旧同名 `api.py` 和聚合 wrapper 删除。

## 3. RAG / Integrations / DB

测试 patch 目标和可运行文档改到 Phase 3 的 canonical 模块。随后一次性删除 adapters 映射树，避免半数旧、半数新造成双重模块状态。领域和 application 用例不删除，Alembic 仍导入 `clinical_agent.db`。

## 4. 飞书与发布入口

测试改用 `clinical_agent.channels.feishu`。Dockerfile、Compose、console metadata 和 setuptools 包发现切到 canonical 路径后，顶层 `feishu` 包删除。`feishu.*` logger 名称保留，因为它是日志路由契约，不是 Python 导入路径。

```mermaid
flowchart LR
  Audit[引用与入口审计] --> Tests[先写删除契约]
  Tests --> Callers[迁移活动调用方]
  Callers --> Delete[删除映射内兼容文件]
  Delete --> Targeted[分批专项验证]
  Targeted --> Full[完整回归与 wheel 检查]
  Full --> Docs[验收和学习文档]
```

回滚以批次为单位恢复别名文件和对应入口配置，不回滚 canonical 实现，也不覆盖其他未提交修改。
