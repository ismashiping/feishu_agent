# 修改练习和验证

先运行 README 的离线 Demo，找到八部分，解释为什么 content_status 是 partial、核验是 verification_incomplete。找到一条 claim 的精确引文、来源编号和原始定位。

修改练习：把审查替身从 uncertain 改成 supported，观察源快照不可用时仍不会 verified；再把实际引用 chunk_id 改成不存在的 UUID，观察来源门禁。不要为了通过验收关闭门禁。

独立练习：构造两个方法不同的合成研究与一个有双侧证据的候选缺口。输出待调查方向并保留 hypothesis 和 verification_needed；让其中一个支持度为 unsupported，检查整份报告 rejected 且原结论仍可供审查。

正式阶段末命令见 P7-01 与验收记录，目标 tests/unit/test_citation_report.py；默认 tests 排除项不计通过。真实模型、官方联网、隔离数据库及独立医学标注需单独集中补验。此练习不增加单次会话测试策略。
