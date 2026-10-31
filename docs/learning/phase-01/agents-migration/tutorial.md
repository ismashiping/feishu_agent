# 从状态到执行图

## 是什么
LangGraph StateGraph 将具名节点及条件边编译为可执行流程。TypedDict 描述共享状态；节点返回 patch，框架把 patch 合入该次调用的状态。

## 为什么需要
本项目有普通问答、证据分析、报告及有界反馈。把组装代码从业务服务中提取后，读者可单独检查拓扑；业务入口仍由ResearchService负责。不增加新的Agent框架或资源容器。

## 底层原理
agents/state.py 的WorkflowState保留request和deadline两个必需字段，其余使用NotRequired。这里没有新增Annotated reducer。角色通过steps生成新的执行记录列表。ResearchService每次调用创建新state并复制请求；编译图可复用不等于共享会话状态。

## 最小Demo
运行同目录demo.py，查看有/无Planner两种节点和边。object只用于构造时占位，禁止对该Demo调用answer/respond等业务方法，因为它没有实现检索和生成契约。

## 工程取舍
build_research_graph接收既有ResearchService并注册绑定方法，是内部装配接口；它知道服务的私有节点，避免新增只转发参数的接口层。若未来确有第二种装配者，再基于真实需要评估解耦。TYPE_CHECKING让类型检查器看见服务类型，运行时不反向导入研究模块；LangGraph仍在调用构建函数时导入。
