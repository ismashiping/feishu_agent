# 2026-10-31 仓库架构收敛契约

目标：删除 API 与命令入口重复的科研服务装配；保留外部接口、索引签名、数据库历史、检索排序/阈值、引用校验和网络安全边界。

输入仍为各入口已验证配置；输出仍为 ResearchService / ServiceBundle。共享装配接收已有 engine、embedder、LLMSettings、OpenAlexSettings；上下文独占并关闭模型 HTTP、发现 HTTP、全文 HTTP，不关闭调用者的 engine。配置失败仍先于模型加载。API 入库和研究共用一个 engine/embedder。

不迁移持久化数据，不部署，不推进业务阶段。不把离线 source-unit-v1 切分替换为 OA SentenceSplitter：两者位置及版本语义不同。无证据证明无用的依赖、维护入口和历史验收保留。

验证：既有 runtime 测试覆盖单模型/engine、关闭顺序、失败退出；默认离线 pytest 回归覆盖 API、工作流、全文、权限和引用；Ruff 检查本次源码。外部模型、真实数据库/Redis/飞书单独列未验证，不使用默认跳过推定通过。
