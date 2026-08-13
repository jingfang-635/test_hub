# {{ScenarioName}} UI 自动化用例计划

> 状态：**待确认** — 用户确认前禁止生成 pages/data/specs 代码

## 基本信息

- 场景：{{scenario}}
- 语言：{{language}}
- 录制文件：tests/recorded/{{recorded_file}}
- 目标 URL：{{target_url}}
- 生成时间：{{generated_at}}

## 页面与 Page Object 规划

| 页面 | 类名 | 主要方法 | 输出文件 |
|------|------|----------|----------|
| {{page_name}} | {{PageClassName}} | {{methods}} | tests/pages/{{page_file}} |

## 用例文件规划

| 功能模块 | Test 类 | 用例 ID 范围 | 输出文件 |
|----------|---------|--------------|----------|
| {{feature}} | {{TestClassName}} | {{tc_range}} | tests/specs/{{spec_file}} |

规则：一功能模块一 specs 文件；与 page 模块对齐；禁止多个 Test* 写入同一文件。

## 数据与造数规划

| 字段 | 来源 | 说明 |
|------|------|------|
| {{field}} | {{source}} | {{note}} |

来源可选：`faker` / `.env` / `api_setup` / `fixtures` / `ddddocr` / `manual`（有头人工）

含图形验证码时必须有一行，二选一或并列说明：
- `captcha | ddddocr（CAPTCHA_MODE=ocr）| 禁止写死录制值`
- `captcha | 人工有头（CAPTCHA_MODE=manual）| 会话填一次后写 auth.json`

## 用例清单

| ID | 类型 | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 | 是否生成 |
|----|------|----------|----------|------|----------|--------|----------|
| TC-001 | 正向 | {{case_name}} | {{precondition}} | {{steps}} | {{expected}} | P0 | 是 |

类型：`正向` / `负向` / `边界` / `权限`

## 选择器优化建议

| 原选择器（录制） | 建议优化 |
|------------------|----------|
| {{original_selector}} | {{suggested_selector}} |

## 待确认项

- [ ] 用例覆盖是否完整
- [ ] 造数方式是否可行
- [ ] 是否需要 API 前置造数
- [ ] Page Object 拆分是否合理
- [ ] 用例是否按模块拆分到独立 specs 文件

## 确认记录

- 确认人：
- 确认时间：
- 备注：
