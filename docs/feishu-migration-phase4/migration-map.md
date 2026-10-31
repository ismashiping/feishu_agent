# 飞书结构迁移映射

唯一实现位于 `clinical_agent.channels.feishu`。旧 `feishu` 包继续随 wheel 发布，并以同一模块对象提供兼容导入。

- `feishu.main` → `clinical_agent.channels.feishu.main`
- `feishu.events` → `clinical_agent.channels.feishu.events`
- `feishu.dedup` → `clinical_agent.channels.feishu.dedup`
- `feishu.worker` → `clinical_agent.channels.feishu.worker`
- `feishu.sender` → `clinical_agent.channels.feishu.sender`

`clinical-feishu` 控制台命令指向 `clinical_agent.channels.feishu.main:main`。`python -m feishu.main` 与 `python -m clinical_agent.channels.feishu.main` 均保留。

迁移没有合并五个职责文件，也没有改变事件过滤、Redis Lua 租约、工作池、发送队列、HTTP 超时、SDK 生命周期或资源关闭顺序。Docker Compose 暂时继续使用旧模块入口，作为兼容部署路径；本阶段不删除旧包。
