# 银发商圈的辅助服务可达性巡查

这是银发商圈资料的本地演练门户与目录采集器。演练数据仅在环回地址提供，不会操作真实用户、订单或商户。当前 `app.capture.read_catalog` 读取目录；`app.capture.read_detail_entry` 走卡片到详情并接收可选业务选择，`app.domain.interpret_entry` 确认业务身份，`app.records.save_detail_entries` 追加详情入口收据。`app.patrol.inspect_access` 用真实 Chromium 沿目录、楼层筛选、服务说明（鼠标/键盘双路径）和预约预览逐楼层记录真实可达条件，能指出资格或时段未知以及键盘交互阻断的具体步骤；全程只读，不提交预约、不填写个人信息，同名服务不同楼层分别出记录。志愿者可读结论见 `app.review.summarize_access_reviews`。

站点约定见 `docs/portal.md`；测试时从本地任意空闲端口启动演练站点。安装锁定依赖并准备 Chromium 后：

- `python -m unittest discover -s tests -v`：运行基线浏览器与可达性巡查测试。
- `python -m compileall -q app tests`：检查代码。
- `python -m app.site`：启动本地演练站点。
- `python -m app.cli`：另一个终端观察目录输出；`python -m app.cli patrol` 观察逐楼层巡查结论。

两个终端命令用于人工演示，自动测试不依赖固定端口。
