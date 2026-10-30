# 练习与测试

先运行demo.py，再使用项目虚拟环境运行 `python -m pytest tests/unit/test_oa_fulltext.py tests/unit/test_fulltext_rag.py -q --basetemp=.pytest_oa_exercise`。真实XML/PDF保存在tests/fixtures/oa_fulltext/，manifest含来源与hash，不能随意覆盖。

修改练习：把合成JATS的DOI换掉，应失败回摘要；把CC BY改为不支持的许可，应拒绝；将重定向指向127.0.0.1，应在发请求前拒绝。把缓存段落的paper_key或字符位置改错，不能进入回答。

缓存练习：先冷加载再热加载，对比文段编码调用数；问题编码仍需要执行。将TTL设过期但正文保持相同，验证续期不编码；再用明确标为合成的正文变更测试索引替换，不用虚构临床结论测试。

独立实现：对另一份允许再利用的真实论文保存原文件、许可及身份依据，逐段核对页码/章节/位置；把文字提取缺失或数字格式错误记成未验证，不修补成自己猜测的原文。不要通过绕过访问控制取得测试样例。

隔离库验证脚本scripts/oa_fulltext_integration.py会检查测试库命名前缀；只允许在显式创建的测试库执行，不能对业务库运行清空/回滚实验。
