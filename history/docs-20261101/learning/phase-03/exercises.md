# 练习与验证

先运行 README 的 Demo，打印 `original_question` 和每个字段的 span，再用 Python 切片核对字段。

1. 修改 Demo 问题并同步字段文字/区间；只改区间末尾，观察 extraction_failed。
2. 删除 comparison，改为 null，确认 partial 仍可继续。将同义词放入 terms 并设置 query_expansion，确认不会成为 PICO 原文。
3. 独立增加一个 diagnosis 固定响应，用实际问题文本标注字段；实现后对照 tests/fixtures/pico/questions.json 的规则自查。
4. 阅读 tests/unit/test_pico.py 的澄清分支测试，解释为什么不应调用 retriever/generator。尝试为超时添加一次受控时钟样例，不使用 sleep。

阶段末集中执行：`.venv/Scripts/python.exe -I -m pytest tests/unit/test_pico.py tests/integration/test_pico.py -q`；完整离线回归 `.venv/Scripts/python.exe -I -m pytest tests -q`。不要把未执行的 external 标记当作通过。真实模型测试需显式配置 LLM_*，当前三个开发候选标注也需人工确认；最多三个固定抽取请求，会使用服务额度，结果应单列。
