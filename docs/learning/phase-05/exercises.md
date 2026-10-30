# 练习与集中测试

先运行Demo，手算1/61与1/62；把一个chunk从一条通道移除，检查缺失排名为null，不伪造0。再增加同一文献的另一个chunk，观察两个片段都保留。

修改tests/fixtures/hybrid/cases.json的副本做练习，不改变冻结验收标签。用查询aspirin对比keyword/vector/hybrid，解释合成向量为何让analgesic先于aspirin。该例不是模型疗效或召回率评估。

独立练习：加入一篇只有年份的文献，设置完整日期过滤，确认它被排除；再给已有完整日期的文献设置范围，验证两路结果一致。尝试缺GIN列/数据库断开，观察错误而非正常空结果，不以失败通道冒充零命中。

阶段末目标：`.venv/Scripts/python.exe -I -m pytest tests/unit/test_hybrid_retrieval.py tests/integration/test_hybrid_retrieval.py -q`。真实专用库：相同命令加`-m database`；需CLINICAL_AGENT_DB_*指向127.0.0.1的独立clinical_agent_test_数据库并显式ALLOW_TEST_RESET=1，不指向业务库。

CLI示例：`ask --model-dir <现有模型目录> --question "成人用药证据？" --retrieval-mode hybrid --keyword-query aspirin --candidate-limit 50`。API在options内给同名mode/keyword_query/candidate_limit；完整问答仍需既有模型与数据库配置。
