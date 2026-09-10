# recorded UI 自动化用例计划

> 状态：**已确认** — 用户确认前禁止生成 pages/data/specs 代码

## 基本信息

- 场景：recorded
- 语言：python
- 录制文件：tests/recorded/recorded.py
- 目标 URL：http://mall.lemonban.com:3344/
- 生成时间：2026-08-13 23:26:44

## 页面与 Page Object 规划

| 页面 | 类名 | 主要方法 | 输出文件 |
|------|------|----------|----------|
| 登录页 | LoginPage | `goto_login()`、`login(username, password)`、`fill_username()`、`fill_password()`、`submit()` | tests/pages/login_page.py |
| 购物车页 | CartPage | `open_cart()`、`increase_quantity()`、`delete_item(index)`、`select_item(index)`、`go_to_checkout()` | tests/pages/cart_page.py |
| 订单确认页 | OrderPage | `submit_order()` | tests/pages/order_page.py |

## 用例文件规划

| 功能模块 | Test 类 | 用例 ID 范围 | 输出文件 |
|----------|---------|--------------|----------|
| 登录 | TestLogin | TC-001 ~ TC-003 | tests/specs/test_login.py |
| 购物车 | TestCart | TC-004 ~ TC-005 | tests/specs/test_cart.py |
| 下单 | TestOrder | TC-006 ~ TC-007 | tests/specs/test_order.py |

规则：一功能模块一 specs 文件；与 page 模块对齐；禁止多个 Test* 写入同一文件。

## 数据与造数规划

| 字段 | 来源 | 说明 |
|------|------|------|
| 用户名（手机号） | .env | `LEMONBAN_USERNAME`，录制值为 15183871603 |
| 密码 | .env | `LEMONBAN_PASSWORD`，录制值为 123456 |
| 商品/购物车数据 | fixtures | 依赖已有账号环境，无额外造数 |
| 登录态 | fixtures | 通过登录用例或 storage_state 复用，避免重复登录 |

## 用例清单

| ID | 类型 | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 | 是否生成 |
|----|------|----------|----------|------|----------|--------|----------|
| TC-001 | 正向 | 正确账号密码登录成功 | 打开首页，未登录 | 1. 点击首页「登录」链接 2. 输入正确用户名 3. 输入正确密码 4. 点击登录按钮 | 登录成功，URL 离开登录页，页面显示用户已登录状态 | P0 | 是 |
| TC-002 | 负向 | 错误密码登录失败 | 打开登录页 | 1. 输入正确用户名 2. 输入错误密码 3. 点击登录 | 提示密码错误，仍停留在登录页 | P0 | 是 |
| TC-003 | 边界 | 空用户名登录 | 打开登录页 | 1. 用户名留空 2. 输入密码 3. 点击登录 | 提示请输入手机号/用户名，不提交 | P1 | 是 |
| TC-004 | 正向 | 购物车增加商品数量 | 已登录，购物车有商品 | 1. 点击「购物车」 2. 点击商品行的「+」按钮 | 商品数量增加 1，合计金额更新 | P0 | 是 |
| TC-005 | 正向 | 删除购物车商品 | 已登录，购物车有商品 | 1. 进入购物车 2. 点击商品对应「删除」链接 | 商品从购物车移除 | P1 | 是 |
| TC-006 | 正向 | 从购物车结算并提交订单 | 已登录，购物车已有选中商品 | 1. 勾选商品 2. 点击「结算」 3. 点击「提交订单」 | 进入支付/订单成功页，订单提交成功 | P0 | 是 |
| TC-007 | 权限 | 未登录直接访问购物车跳转登录 | 未登录，打开首页 | 1. 直接点击「购物车」入口 2. 尝试结算 | 跳转或提示需先登录 | P1 | 是 |

## 选择器优化建议

| 原选择器（录制） | 建议优化 |
|------------------|----------|
| `page.get_by_text("购物车 2")` | 使用固定名称或图标定位，如 `get_by_role("link", name="购物车")`，避免数量变化导致匹配失败 |
| `page.get_by_role("link", name="删除").first` / `.nth(3)` | 为购物车商品行增加 `data-testid` 或使用基于商品名称的 locator，避免顺序变化 |
| `page.get_by_text("+")` | 限定在商品行内，如 `row_locator.get_by_text("+")`，避免误点其他 `+` 元素 |
| `page.get_by_role("checkbox").nth(1)` | 在商品行内定位 checkbox，或添加 `data-testid` 属性 |
| 登录按钮 `get_by_role("link", name="登录").nth(1)` | 确认首页链接与登录页提交按钮冲突时，提交按钮改用 `button` role 或 `data-testid` |

## 待确认项

- [ ] 用例覆盖是否完整
- [ ] 造数方式是否可行
- [ ] 是否需要 API 前置造数（如准备购物车商品）
- [ ] Page Object 拆分是否合理
- [ ] 用例是否按模块拆分到独立 specs 文件

## 确认记录

- 确认人：
- 确认时间：
- 备注：