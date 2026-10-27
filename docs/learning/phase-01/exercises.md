# 修改练习、独立实现与测试

所有修改均在练习副本进行，不是本次产品新增功能。先写预期，再跑RED，然后最小修改取得GREEN；不能通过删断言完成练习。

## 阅读练习
运行[Demo](demo.py)前预测：检索空时generate调用次数是多少？未知UUID为什么不是insufficient_evidence？给一个存在的chunk引用错误医学结论能否通过结构门禁？第三问答案是可能通过，说明你需要人工审核而不是把UUID存在当成语义正确。

记录每题输入、预期分支、实际输出和函数位置。用[ResearchService](../../../src/clinical_agent/application/research.py)和[citations](../../../src/clinical_agent/domain/citations.py)逐步调试，检查deadline和set(cited)，不要只打印最终答案。

## 修改练习一：证据不足也不补常识
在demo副本增加Generator会在调用时抛异常的模式，让Retriever返回空列表；先添加断言服务返回空claims/sources且调用次数为0。再将Retriever改为有命中，证明相同生成器产生generation_failed。通过标准：两种输入不能得到同一结果，错误信息不泄露异常原文。

## 修改练习二：边界与切片
复制[分块测试](../../../tests/unit/test_chunking.py)中的一个来源单元，增加中文、emoji、长句和第二页。先写“每块不跨页，source[start:end]==chunk.text，完整前缀输入不超过token预算”断言，再调chunking policy观察结果。不能用len(text)替换真实tokenizer来宣称E5验证通过；真实模型测试见[外部测试](../../../tests/integration/test_embedding_real.py)。

## 修改练习三：容量和关闭
阅读[worker测试](../../../tests/unit/test_feishu_worker.py)，让研究线程等待Event；容量设1，第二条应busy，close(timeout_seconds=0)应False。释放Event后再close应True。加一个重复message_id，解释容量耗尽时可能先得到busy，而有空位才会检查Redis duplicate。通过标准：busy不创建租约，线程未结束不释放槽位。

## 独立实现练习
不引用产品内部私有函数，写一个只读JSON命令：接收ResearchAnswer文件，输出每个claim_id及对应chunk_id、页码/章节和[start,end)。先用合成答案编写正常、缺chunk、重复chunk、未知字段的测试，再实现；利用ResearchAnswer.model_validate_json做共享契约校验。禁止联网、修改数据库或给答案增加医学事实。

完成后独立解释：为什么不能据此声称医学结论正确？预期是“这里只验证可追溯关联；仍须比较原文的人群、干预、结局、数字、限制与论断”。

## 实际测试命令
在仓库根目录、已同步锁定开发依赖后：

```powershell
& .venv/Scripts/python.exe -m pytest tests/integration/test_phase1_acceptance.py -k learning
& .venv/Scripts/python.exe -m pytest tests/unit/test_research.py
& .venv/Scripts/python.exe -m pytest
& .venv/Scripts/python.exe -m ruff check src tests alembic
& .venv/Scripts/python.exe -m mypy src
```

默认pytest排除external/performance/database/redis，默认通过不能算真实服务通过。真实测试前提和显式选择见[排错](troubleshooting.md)。修改练习的结果不是本项目本轮验收结果。
