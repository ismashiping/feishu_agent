> 后续用户变更：默认来源改为hybrid，详见[默认来源变更记录](../../hybrid-default-acceptance.md)。下文原冻结local决策保留其历史时点。

# 探索型问题检索修复 SPEC

状态：2026-10-28冻结；历史P3/MA验收不改写。

根因：application/pico.py将uncertain+ambiguities映射为needs_clarification，domain/pico.py再次强制同一规则，research.py的_plan_route据此阻断所有三类入口；MA反馈发生在report之后，无法补救。提示词允许nonblocking ambiguities却未区分阻断项。PICO本身允许四字段为空，并不要求C/O。agents.py已传query_plan至PubMed，但domain/pubmed.py的query_text忽略terms。CLI --scope默认local，API QuestionBody继承RetrievalRequest的local，飞书worker构造QuestionRequest未设置scope，均属入口默认。

最小扩展：ExtractionDraft/StructuredQuestion增加可选blocking_ambiguities（null表示旧契约；新模型必须返回列表）。新列表非空即澄清，不依赖question_type；空列表且有原文锚定PICO或user_text关键词时允许partial检索；只有扩展词不能证明主题已识别。ambiguities保留缺失信息/可选问题，不能单独阻断新契约。旧null仍按旧规则，保留历史输出回放。所有span/来源门禁不变。

提示词要求研究发现不强制PICO、模态或研究设计，不臆造条件；关键主题不可识别或显式条件冲突才阻断。新契约的候选扩展词用于单次PubMed OR查询，各词按字面引用；显式pubmed.query优先，原始问题仍保留。不扩增请求数、期限或名额；不声称候选同义词是严格语义过滤。显式时间/来源过滤不变。

scope默认保持local，兼容既有离线调用及飞书部署；不根据自然语言隐式改成hybrid。CLI/API可显式online/hybrid；飞书现有纯文本仍local，不新增消息命令。本地mode与来源scope独立。答复展示范围；local空结果说明未在线检索。可选问题展示为后续细化方向。

测试：宽泛肝肿瘤输入缺C/O/模态进入检索；无主题阻断；显式阻断优先；旧输出兼容；local零命中不联网、online不调用local、hybrid本地空仍在线；全部空为证据不足；超时保留错误；计划传递及真实查询构造；answer/analyze/report共用路由；已有MA反馈/deadline和入口默认回归。先执行新回归RED，再最小实现GREEN及默认回归。真实PG/PubMed只在可用隔离环境运行，未执行单列。
