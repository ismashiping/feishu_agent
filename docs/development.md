# 开发与运行

## 环境

Python 3.12；依赖版本见 pyproject.toml 与 uv.lock。执行 `.venv/Scripts/uv.exe sync --frozen --all-extras` 安装全部可选依赖；首次下载需要网络。ML 组含 E5 运行依赖，模型快照需预先放在 models 中。不要将模型目录当作代码删除。

配置的准确字段与限制见 config.py、db/connection.py、integrations/llm.py、integrations/openalex.py 和 api/schemas.py。数据库、LLM、API 和飞书 Settings 不自动读取 .env，OpenAlexSettings 显式读取 .env；Compose 会读其插值环境，本地运行请显式注入环境变量，不打印密钥。

主要变量：CLINICAL_AGENT_DB_HOST/PORT/NAME/USER/PASSWORD；LLM_API_KEY/BASE_URL/MODEL；OPENALEX_API_KEY/RECENT_MONTHS；CLINICAL_AGENT_API_MODEL_DIR/IMPORT_ROOT/SNAPSHOT_DIR。飞书配置见 channels/feishu/main.py。

## 入口

- `clinical-agent doctor`：本地环境检查。
- `clinical-agent ingest --source-type pdf --path <文件> --allowed-root <允许目录> --snapshot-dir <快照目录> --model-dir <模型目录>`。
- `clinical-agent ask --scope online --question "研究问题" --model-dir <模型目录>`；--analyze、--report 选择输出形式。
- `uvicorn clinical_agent.api:create_app --factory`。
- `python -m clinical_agent.channels.feishu.main` 或 clinical-feishu。

docker-compose.yml 定义 PostgreSQL、Redis、API 和飞书，API/bot 用 profile 选择。启动前配置密码和模型路径。生产环境升级前先备份并检查迁移：oa3002_0010 会删除历史 PubMed 行及旧全文表，降级不能恢复删掉的数据。不要把“迁移文件存在”当成“业务库已升级”。

## 修改流程

先写 SPEC 与验收场景，再写测试和最小实现。边界数据用 Pydantic 校验；可信内部通过准确注解或契约收窄表达类型，不重复添加 isinstance/None 检查。cast 只用于上游契约已经保证的条件，不提供运行时验证。动态外部 JSON 仍必须按其实际风险校验。

mypy 使用标准规则、check_untyped_defs、无效 ignore/冗余 cast 检查；取消 strict 的全函数注解要求。未注解函数体仍检查，但 Any 的静态保障有限，不能替代测试。仅 defusedxml 的无类型第三方导入允许缺少 stubs，不忽略任何项目模块。

验证命令与真实结果见状态表。外部测试必须用独立数据库与命名空间；部分旧数据库测试有历史 Schema 假设，不能直接拿生产库跑。长期证据与可清理缓存分开。
