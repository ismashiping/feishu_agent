# 修改与独立练习

先运行demo.py，再读`tests/unit/test_research_quality_v2.py`。policy.json是冻结的工程验收期望，合成论文只用于控制逻辑，绝不能展示为医学引用。

调试命令：

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/unit/test_research_quality_v2.py tests/unit/test_openalex.py tests/unit/test_oa_fulltext.py tests/unit/test_answer_synthesis.py -q --basetemp=.pytest_openalex_learning4
```

修改练习：将“采集方案”换成“研究局限”，观察section_priority如何改变顺序。只修改问题，不修改真实正文。然后构造只有一个直接研究、其余partial的合成筛选器，检查第二轮结束后仍只保留一个，而不是凑五个。

独立实现练习：不看retrieve，写一个小函数按DOI及题名摘要的精确指纹去重，记录duplicate_identity和duplicate_study。给出不同DOI相同工作、相同题名不同摘要、完全不同论文三类案例；不要用模糊题名相似度直接合并。

解释练习：为什么三篇实际获取尝试不等于三篇成功下载？为什么HTTP200和引用ID匹配不能证明研究结论正确？为缺少直接证据的问题写一句真实、简短的范围说明，不暗示领域不存在研究。
