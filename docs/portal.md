# 本地来源行为

银发商圈目录列出稳定的 `data-key` 和详情路径；详情需由浏览器导航读取，`楼层`选择改变当前页面状态，`键盘焦点`和`预约预览`是分步出现的可见内容。弹窗键盘焦点与鼠标入口可能不同。详情接口是浏览器页面，不是业务 API；运行时只允许访问环回来源。

`fixtures/portal.json` 提供合成业务资料，不包含真实个人数据。楼层、服务日与服务说明文本均由 fixture 数据驱动：

- `floors` 给出每个楼层的服务日，`时段待公布` 表示该楼层资格或时段未知，巡查记为 `unknown_slot` 而不是“不可达”；
- `keyboard_defect` 为真的服务，键盘打开弹窗时焦点停在触发按钮（不进入弹窗），且键盘与鼠标读到的服务说明文本不同，用于演练“键盘交互阻断核对”；
- `服务说明`弹窗与 `#panel`、`#assistance-preview` 等 `aria-live` 区域的内容是交互后异步出现的，只能读取运行时真实文本，不能用静态卡片文字替代。

`records.save_catalog` 覆盖同一目录身份；`records.save_detail_entries` 以业务键追加入口访问，不把入口访问等同于资格、授权、可预约或正式提交。

## 可达性巡查（`app.patrol.inspect_access`）

巡查用真实 Chromium 沿 目录 → 楼层筛选 → 服务说明（鼠标与键盘两条路径分别记录）→ 异步说明面板 → 预约预览（说明打开前、鼠标核对后、键盘核对后三次）逐楼层观察。每个“服务 × 楼层”产出独立记录，业务键含楼层与服务日，同名服务不同楼层不合并。每条记录包含：

- `floor_filter`：楼层筛选后的真实服务日，以及是否为待公布时段；
- `mouse` / `keyboard`：弹窗是否打开、说明原文、焦点是否进入弹窗、能否仅用键盘关闭，以及阻断步骤（`dialog_not_opened`、`dialog_focus_blocked` 等）；
- `async_panel`：`键盘焦点`维度异步面板的鼠标/键盘原文及占位态是否结束；
- `preview`：预约预览三阶段原文与判定状态；预览只是核对结果，不代表已预约；
- `verdict`：`reachable` / `partially_reachable` / `keyboard_blocked`、未知条件清单、键盘阻断步骤，且 `booking_submitted` 恒为假。

巡查全程只读：只允许 GET 与环回导航，不填写任何个人信息，不点击提交类控件（守卫会直接拒绝并中止），不发起预约。收据写入 `records.save_access_reviews`（按业务键追加），志愿者可读结论由 `review.summarize_access_reviews` 生成。测试均只访问本地环回页面。
