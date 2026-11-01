# 运行与排错

退出1：冻结合成集故意包含模型失败、未知引用和无支持claim。检查results.json.samples而不是降低门槛。退出2：存在不可比较基线、无分母或缺标注；补齐真实证据后建立新版本。输入校验异常：检查重复case_id、缺观察、未知相关chunk、错拼metric名称。

依赖导入失败时使用项目.venv及-I隔离解释器。不得把密钥、患者数据或.env复制到评价包。输出目录要在冻结包之外。比较baseline时选择独立目录，原报告不覆盖。

性能字段python_peak_bytes仅表示tracemalloc跟踪的Python内存，不能替代RSS或GPU峰值。1/2/4线程都是暖输入微基准，吞吐下降可以反映解释器竞争，不能直接推断生产饱和点。所有real_model、external、medical_review、service_load默认记录为未执行；本地回放通过也不改变这些状态。
