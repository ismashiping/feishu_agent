# 查询入口与学习文档治理 SPEC

2026-11-01，专项任务，待验收。

目标：公开 API/CLI 不再接受 local；保留 PDF 入库与 OpenAlex 全文缓存。online/hybrid 暂保留现有在线发现行为，不新增联合检索。内部历史 DTO/测试替身暂不扩大重构。
输入输出：local 在请求校验处拒绝，API 422、CLI 2，不创建业务资源；合法在线输入和响应结构不变。错误不得含原始输入/密钥。
类型：使用 mypy 标准检查并检查未注解函数体，保留 Pydantic、外部响应校验、引用真实性、事务、超时；不忽略项目模块。
文档：旧 docs 移至 history/docs-20261101，保留历史证据与测试样例；重建 docs，基于实际入口、调用顺序和数据生命周期。
测试先明确：本地参数拒绝；API/CLI 正常在线响应；真实流水线不再要求本地问答成功；完整离线回归、ruff、mypy、离线 lock。真实依赖测试按标记单独运行，记录缺少条件、失败与跳过；人工医学验收不可由自动检查替代。
命令：python -X utf8 -m pytest -q --basetemp=.artifacts/tmp/governance；ruff check src tests；python -m mypy src；uv lock --check --offline。
验收标准：技术检查通过、现行文档可导航、无公开 local 选项；真实服务及医学验收分别报告，不以排除项冒充通过。不自动迁移业务库或部署。
