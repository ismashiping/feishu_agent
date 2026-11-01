# 第四阶段使用与复现

保持原API/飞书入口，普通提问直接使用新筛选和写作流程。默认top_k仍为5；API需要更宽综述时可以显式设8。它是最大选择数量，相关研究不足时不会填满。

```powershell
$requestBody = @{
    question = '肝脏分割最新研究有哪些？'
    scope = 'hybrid'
    options = @{ top_k = 8 }
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri 'http://127.0.0.1:18080/v1/questions' `
    -Method Post -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($requestBody)) -TimeoutSec 120
```

scope=hybrid表示本地与OpenAlex来源；options.mode默认为vector，不能与只支持ASCII关键词的本地hybrid模式混淆。问题语言不改变原日期/对象/任务要求。

默认回答显示技术方向、真实引用和简短范围说明；API保留完整provenance，离线需要排查可`render_answer(answer, include_audit=True)`。新增section/study_role字段向后兼容旧内部数据，旧模型输出可不带section；实际模型是否遵守综述风格必须读生成结果验证。

复现脚本：`scripts/oa_quality_check.py ROOT replay`用冻结来源重新生成，`live`重新发现；可附`3,4`这样的案例索引。ROOT需包含input/qN-request.json与qN-response.json以及当前源码运行环境、真实模型/数据库配置。脚本会调用真实供应商、可能写合法全文缓存；不是免费离线单元测试。默认拒绝覆盖批次目录。输出context/draft/screening原文用于定位失败，不保存密钥。

部署复用第三阶段已核验的依赖基线，使用本目录Dockerfile.update离线重装当前项目wheel；不是从旧源码启动，也不更新依赖锁。实际容器镜像与源码hash、测试结果及失败样例见[验收](acceptance.md)。本轮没有新Schema迁移，不主动发送飞书消息，先前unknown发送确认缺口保持开放。
