# 飞书普通问答默认格式验收

## SPEC 与根因
普通 answer 使用 feishu.sender.render_answer，将查询计划、chunk/document/hash 与科研正文一起输出；report 的展示设置不影响该入口。本次只改展示，不改变生成、检索或引用门禁。
默认按原 claim 顺序输出科研内容、编号引用与必要局限；保留推断和不确定标签，参考文献显示标题、年份、PMID（无 PMID 时 DOI）、安全来源链接与内容范围。来源关联警示保留。内部标识及计划仍可通过 include_audit=True 输出，结构化 ResearchAnswer 不变。检索范围以匹配总数和返回候选数分别描述，未将候选数声称为 EFetch 成功数。

## RED → GREEN → 回归
新增默认展示测试修改前失败（red.txt：1 failed），修改后 sender + pico 115 passed（green.txt）。飞书所有单元模块及 pico：374 passed，2 个既有 SDK DeprecationWarning（regression.txt）。补强多文献引用顺序与审计 UUID 关联测试：1 passed。Ruff check 通过。
旧精确位置、作者和内部标识断言迁到显式审计模式，未删除；默认模式保留安全 URL、转义、整段超限回退与大小门禁测试。

## 变更及保护
生产代码仅 src/feishu/sender.py；测试 tests/unit/test_feishu_sender.py。修改前副本和 SHA256 位于 .quality-backup/feishu-readable-20261029。未修改模型调用、查询规则、请求预算和消息字节上限。
固定 Compose 项目 clinical-agent-e2e 复用 feishu_bot 容器并 restart，无构建、无新建容器、无数据卷变更。其余服务未重启。

## 验证边界
离线测试证明格式与引用关联；没有新增真实 LLM/PubMed 调用，不代表医学语义质量提高。已生成 claim 文本中的模型措辞不会被展示层改写，仍保留逐条必要局限。需以新的飞书问答查看用户端最终呈现。
