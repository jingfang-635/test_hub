import{_ as yt,O as xt,r as g,c as V,P as vt,d as y,a0 as wt,e as E,f as L,g as D,t as m,h as o,w as n,j as kt,ap as St,i as p,A as O,J as ot,B as at,aT as Vt,G as q,aU as Et,aV as At,aW as Dt,aX as qt}from"./index-DgmMiakf.js";const jt={class:"admin-embed-page"},Tt={key:0,class:"page-header"},It={class:"page-title"},Lt={class:"header-actions"},Nt={class:"content"},Pt=["src"],Ut={class:"mono-text"},Ct={class:"mono-text wrap"},zt=`
  支持以下变量替换（在模板内容中使用 {{变量名}} 即可）：<br>
  <b>任务相关：</b>
  {{task_name}} 任务名称、{{status_text}} 执行状态、{{execution_time}} 执行时间、{{task_type}} 任务类型<br>
  <b>测试相关：</b>
  {{title}} 测试标题、{{tester}} 测试人员、{{total_cases}} 用例总数、{{passed_cases}} 通过用例数、
  {{failed_cases}} 失败用例数、{{error_cases}} 错误用例数、{{skipped_cases}} 跳过用例数、
  {{runtime}} 执行时长、{{begin_time}} 开始时间
`,$t=`
:root {
  --th-embed-primary: #6c5ce7;
  --th-embed-primary-soft: rgba(108, 92, 231, 0.12);
  --th-embed-success: #67c23a;
  --th-embed-success-bg: #f0f9eb;
  --th-embed-danger: #f56c6c;
  --th-embed-danger-bg: #fef0f0;
  --th-embed-warning: #e6a23c;
  --th-embed-warning-bg: #fdf6ec;
  --th-embed-info: #9b59b6;
  --th-embed-info-bg: #f3e8ff;
  --th-embed-text: #303133;
  --th-embed-muted: #909399;
  --th-embed-border: #ebeef5;
  --th-embed-header-bg: #f5f7fa;
  --th-embed-check: #6c5ce7;
  --th-embed-check-soft: rgba(108, 92, 231, 0.045);
}

/* 勾选框：紫色主题（表头全选 + 行选择） */
#result_list input[type="checkbox"],
#action-toggle,
.action-select,
.action-checkbox input[type="checkbox"],
input.action-select {
  accent-color: var(--th-embed-check) !important;
  width: 16px !important;
  height: 16px !important;
  cursor: pointer !important;
}

/* Element UI 勾选（SimpleUI 若使用） */
.el-checkbox__inner {
  border-radius: 3px !important;
  border-color: #dcdfe6 !important;
}
.el-checkbox__inner:hover {
  border-color: var(--th-embed-check) !important;
}
.el-checkbox__input.is-checked .el-checkbox__inner,
.el-checkbox__input.is-indeterminate .el-checkbox__inner {
  background-color: var(--th-embed-check) !important;
  border-color: var(--th-embed-check) !important;
}
.el-checkbox__input.is-focus .el-checkbox__inner {
  border-color: var(--th-embed-check) !important;
}
.el-checkbox__input.is-checked .el-checkbox__inner::after {
  border-color: #fff !important;
}
.el-checkbox__input.is-checked + .el-checkbox__label {
  color: var(--th-embed-check) !important;
}

/* 选中行：浅紫背景 */
#result_list tbody tr.selected,
#result_list tbody tr.selected th,
#result_list tbody tr.selected td,
#result_list tbody tr:has(input.action-select:checked),
#result_list tbody tr:has(input.action-select:checked) th,
#result_list tbody tr:has(input.action-select:checked) td,
.el-table__body tr.el-table__row.current-row > td.el-table__cell,
.el-table__body tr:has(.el-checkbox__input.is-checked) > td.el-table__cell {
  background: var(--th-embed-check-soft) !important;
}
#result_list tbody tr.selected:hover th,
#result_list tbody tr.selected:hover td,
#result_list tbody tr:has(input.action-select:checked):hover th,
#result_list tbody tr:has(input.action-select:checked):hover td {
  background: rgba(108, 92, 231, 0.08) !important;
}

/* 隐藏“选中了 X 条”等操作计数文案 */
.actions .action-counter,
.actions .all,
.actions .question,
.actions .clear,
.actions .small.quiet,
#changelist .actions .action-counter,
#changelist .actions span.action-counter,
#changelist .actions span.all,
#changelist .actions span.question,
#changelist .actions span.clear {
  display: none !important;
}

/* 隐藏 SimpleUI / Admin 导航壳，只保留内容区 */
.menu,
.navbar,
.logo-wrap,
.breadcrumb,
.simpleui-header,
header.el-header,
aside.el-aside,
.el-aside,
#header,
.header .logo,
.float-right > .el-dropdown,
.navbar-right,
.navbar-custom-menu { display: none !important; }

html, body, #app {
  height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  background: #fff !important;
}

.el-container {
  height: 100% !important;
  min-height: 0 !important;
}

.el-main,
.content-wrapper,
#content,
.main,
.content-container {
  margin: 0 !important;
  padding: 4px 8px 12px !important;
  background: #fff !important;
  width: 100% !important;
  max-width: 100% !important;
  height: 100% !important;
  max-height: 100% !important;
  overflow: auto !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}

/* 隐藏 iframe 内横向滚动条，避免列表下方出现横条 */
* {
  scrollbar-width: thin;
}
.el-table,
#result_list,
.results {
  overflow-x: auto !important;
}

/* 页面标题（Admin 内置）弱化，外层 Vue 已有标题 */
#content > h1,
.content-title,
.breadcrumb-container { display: none !important; }

/* 隐藏列表右上角：隐藏搜索 / 刷新 / 新窗口(全屏类) 模块 */
.actions .btn-group {
  display: none !important;
}

/* 搜索栏整体 */
#toolbar {
  margin: 0 0 12px !important;
  padding: 12px 14px !important;
  background: #f7f8fa !important;
  border: 1px solid var(--th-embed-border) !important;
  border-radius: 8px !important;
  box-sizing: border-box !important;
}
.simpleui-form {
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 10px !important;
}

/* 搜索框 / 下拉：白底、浅灰边、圆角；聚焦紫色 */
.simpleui-form .simpleui-form-item,
.simpleui-form .el-select,
.simpleui-form .el-input,
.simpleui-form .el-date-editor {
  margin: 0 !important;
}
.simpleui-form .el-input__inner,
.simpleui-form .el-range-input {
  background: #fff !important;
  border: 1px solid #dcdfe6 !important;
  border-radius: 6px !important;
  color: #606266 !important;
  height: 32px !important;
  line-height: 32px !important;
  box-shadow: none !important;
}
.simpleui-form .el-input__inner::placeholder,
.simpleui-form .el-range-input::placeholder {
  color: #c0c4cc !important;
}
.simpleui-form .el-input.is-focus .el-input__inner,
.simpleui-form .el-select .el-input.is-focus .el-input__inner,
.simpleui-form .el-input__inner:focus,
.simpleui-form .el-range-editor.is-active,
.simpleui-form .el-range-editor.is-active:hover {
  border-color: var(--th-embed-primary) !important;
  box-shadow: 0 0 0 1px rgba(108, 92, 231, 0.15) !important;
}
.simpleui-form .el-input__suffix,
.simpleui-form .el-select .el-input .el-select__caret {
  color: #c0c4cc !important;
}

/* 操作区按钮：增加 / 删除 / 查询 */
.actions {
  margin: 0 0 12px !important;
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 8px !important;
}
.object-tools {
  display: none !important; /* SimpleUI 已把“增加”放到 actions */
}

/* 查询、增加：紫色主按钮 + 轻阴影（对齐图片“搜索”） */
#toolbar .el-button--primary,
.actions .el-button--primary,
.actions .el-button[data-name="add_item"],
.object-tools a,
.object-tools a:link,
.object-tools a:visited,
button.default,
input[type="submit"].default,
.button.default {
  background: var(--th-embed-primary) !important;
  border: 1px solid var(--th-embed-primary) !important;
  color: #fff !important;
  border-radius: 6px !important;
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.32) !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  height: auto !important;
}
#toolbar .el-button--primary:hover,
.actions .el-button--primary:hover,
.actions .el-button[data-name="add_item"]:hover {
  background: #8b7cf0 !important;
  border-color: #8b7cf0 !important;
  color: #fff !important;
}

/* 删除：红底白字 */
.actions .el-button--danger,
.actions .el-button[data-name="delete_selected"] {
  background: #f56c6c !important;
  border: 1px solid #f56c6c !important;
  color: #fff !important;
  border-radius: 6px !important;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.28) !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  height: auto !important;
}
.actions .el-button--danger:hover,
.actions .el-button[data-name="delete_selected"]:hover {
  background: #f78989 !important;
  border-color: #f78989 !important;
  color: #fff !important;
}

/* 其他默认小按钮（次要） */
.actions .el-button--default,
#toolbar .el-button--default {
  background: #fff !important;
  border: 1px solid #dcdfe6 !important;
  color: #606266 !important;
  border-radius: 6px !important;
  box-shadow: none !important;
}

/* 表格对齐 Element Plus / 测试报告列表 */
#result_list,
.results table,
table#result_list {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  border: 1px solid var(--th-embed-border) !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  background: #fff !important;
}
#result_list thead th,
.results thead th {
  background: var(--th-embed-header-bg) !important;
  color: var(--th-embed-text) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  border-bottom: 1px solid var(--th-embed-border) !important;
  border-right: none !important;
  padding: 12px 14px !important;
  text-align: center !important;
  vertical-align: middle !important;
}
#result_list thead th .text,
#result_list thead th .text a,
#result_list thead th .text span {
  text-align: center !important;
  display: block !important;
  float: none !important;
}
/* 取消表头点击排序：禁用链接并隐藏排序图标 */
#result_list thead th a,
#result_list thead th .text a {
  color: var(--th-embed-text) !important;
  pointer-events: none !important;
  cursor: default !important;
  text-decoration: none !important;
}
#result_list thead th .sortoptions,
#result_list thead th a.sortremove,
#result_list thead th a.toggle {
  display: none !important;
}
#result_list tbody td,
#result_list tbody th,
.results tbody td,
.results tbody th {
  border-bottom: 1px solid var(--th-embed-border) !important;
  border-right: none !important;
  padding: 12px 14px !important;
  color: #606266 !important;
  font-size: 13px !important;
  vertical-align: middle !important;
  background: transparent !important;
  font-weight: 400 !important;
  text-align: center !important;
}
/* Django 把带链接的第一列数据渲染为 tbody > th，必须单独设黑 */
#result_list tbody th,
#result_list tbody th a,
#result_list tbody th a:link,
#result_list tbody th a:visited,
#result_list tbody th a:hover,
#result_list tbody th a:active,
#result_list tbody td.field-name,
#result_list tbody td.field-name a,
#result_list tbody td.field-path,
#result_list tbody td.field-path a,
#result_list tbody td.field-date,
#result_list tbody td.field-date a,
#result_list tbody tr td.action-checkbox + td,
#result_list tbody tr td.action-checkbox + td a,
#result_list tbody tr td.action-checkbox + th,
#result_list tbody tr td.action-checkbox + th a {
  color: #000000 !important;
  font-weight: 500 !important;
  text-decoration: none !important;
}
#result_list tbody tr:hover td,
#result_list tbody tr:hover th,
.results tbody tr:hover td,
.results tbody tr:hover th {
  background: rgba(108, 92, 231, 0.04) !important;
}
#result_list tbody tr:last-child td,
#result_list tbody tr:last-child th {
  border-bottom: none !important;
}

/* SimpleUI 使用 el-table 时的样式 */
.el-table {
  border: 1px solid var(--th-embed-border) !important;
  border-radius: 8px !important;
  overflow: hidden !important;
}
.el-table th.el-table__cell {
  background: var(--th-embed-header-bg) !important;
  color: var(--th-embed-text) !important;
  font-weight: 600 !important;
}
.el-table td.el-table__cell {
  color: #606266 !important;
}
.el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell {
  background: rgba(108, 92, 231, 0.04) !important;
}
.el-table .el-button--text,
.el-table .el-button.is-link {
  font-size: 12px !important;
}
.el-table .el-button--text.el-button--primary,
.el-table .el-button.is-link.el-button--primary {
  color: #67c23a !important;
}
.el-table .el-button--text.el-button--danger,
.el-table .el-button.is-link.el-button--danger {
  color: #f56c6c !important;
}
.el-tag--success { background: var(--th-embed-success-bg) !important; color: var(--th-embed-success) !important; border-color: transparent !important; }
.el-tag--danger { background: var(--th-embed-danger-bg) !important; color: var(--th-embed-danger) !important; border-color: transparent !important; }
.el-tag--warning { background: var(--th-embed-warning-bg) !important; color: var(--th-embed-warning) !important; border-color: transparent !important; }
.el-tag--info { background: var(--th-embed-info-bg) !important; color: var(--th-embed-info) !important; border-color: transparent !important; }
.el-tag { border-radius: 999px !important; }

/* 行内操作链接配色；勿用 th a 全局选择器（Django 第一列也是 th） */
#result_list a,
.results a {
  text-decoration: none !important;
}
a.viewsitelink,
a.changelink,
td.field-__str__ a {
  color: var(--th-embed-success) !important;
}
#result_list thead th a {
  color: var(--th-embed-text) !important;
}
#result_list tbody td:not(.field-name):not(.field-path):not(.field-date) a:not(.deletelink) {
  color: var(--th-embed-success) !important;
}
/* 通知模板列表「编辑」操作按钮 */
#result_list tbody td.field-edit_action,
#result_list tbody td.field-edit_action a.th-edit-btn,
a.th-edit-btn,
a.th-edit-btn:link,
a.th-edit-btn:visited {
  color: var(--th-embed-primary) !important;
  font-weight: 500 !important;
  text-decoration: none !important;
  cursor: pointer !important;
}
a.th-edit-btn:hover {
  color: #8b7cf0 !important;
  text-decoration: underline !important;
}
a.deletelink,
.deletelink {
  color: var(--th-embed-danger) !important;
}

/* 分页 */
.paginator,
.pagination {
  margin-top: 16px !important;
  color: var(--th-embed-muted) !important;
}
.paginator a,
.pagination a,
.el-pagination button:hover {
  color: var(--th-embed-primary) !important;
}
.el-pager li.is-active,
.el-pager li.active {
  background: var(--th-embed-primary) !important;
  color: #fff !important;
}

/* 通用标签（后端 format_html 输出） */
.th-pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 20px;
  font-weight: 500;
  white-space: nowrap;
}
.th-pill-success { background: var(--th-embed-success-bg); color: var(--th-embed-success); }
.th-pill-danger { background: var(--th-embed-danger-bg); color: var(--th-embed-danger); }
.th-pill-warning { background: var(--th-embed-warning-bg); color: var(--th-embed-warning); }
.th-pill-info { background: var(--th-embed-info-bg); color: var(--th-embed-info); }
.th-pill-primary { background: var(--th-embed-primary-soft); color: var(--th-embed-primary); }
.th-pill-muted { background: #f4f4f5; color: #909399; }

.th-rate {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--th-embed-text);
}
.th-rate-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.th-num-success { color: var(--th-embed-success); font-weight: 600; }
.th-num-danger { color: var(--th-embed-danger); font-weight: 600; }
.th-num-warning { color: var(--th-embed-warning); font-weight: 600; }
.th-num-normal { color: var(--th-embed-success); font-weight: 600; }

/* ========== 通知模板 新增/编辑表单（对齐用例表单风格） ========== */
body.model-notificationtemplate.change-form,
body.model-notificationtemplate.add-form {
  background: #f5f7fa !important;
}
body.model-notificationtemplate.change-form .el-main,
body.model-notificationtemplate.add-form .el-main,
body.model-notificationtemplate.change-form #content,
body.model-notificationtemplate.add-form #content,
body.model-notificationtemplate.change-form .content-container,
body.model-notificationtemplate.add-form .content-container {
  background: #f5f7fa !important;
  padding: 16px 20px 24px !important;
  overflow: auto !important;
}
body.model-notificationtemplate .form-main,
body.model-notificationtemplate #content-main.form-main {
  background: #fff !important;
  border-radius: 12px !important;
  padding: 28px 32px 24px !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
  border: 1px solid #ebeef5 !important;
  max-width: 960px !important;
  margin: 0 auto !important;
  box-sizing: border-box !important;
}
body.model-notificationtemplate .page-header {
  margin: 0 0 20px !important;
  padding: 0 0 12px !important;
  border-bottom: 1px solid #ebeef5 !important;
}
body.model-notificationtemplate .page-header .el-page-header__content {
  color: #303133 !important;
  font-size: 16px !important;
  font-weight: 600 !important;
}
body.model-notificationtemplate .page-header .el-page-header__left .el-icon-back,
body.model-notificationtemplate .page-header .el-page-header__title {
  color: #606266 !important;
}
body.model-notificationtemplate .object-tools,
body.model-notificationtemplate .historylink {
  display: none !important;
}
body.model-notificationtemplate fieldset.module {
  background: transparent !important;
  border: none !important;
  margin: 0 !important;
  padding: 0 !important;
  box-shadow: none !important;
}
body.model-notificationtemplate fieldset.module > h2 {
  display: none !important;
}
body.model-notificationtemplate .form-row {
  display: block !important;
  margin: 0 0 20px !important;
  padding: 0 !important;
  border: none !important;
  overflow: visible !important;
}
body.model-notificationtemplate .form-row > div:not(.help):not(.errorlist) {
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: flex-start !important;
  width: 100% !important;
}
body.model-notificationtemplate .form-row label,
body.model-notificationtemplate .form-row .checkbox-row label {
  float: none !important;
  display: inline-block !important;
  flex: 0 0 100px !important;
  width: 100px !important;
  min-width: 100px !important;
  margin: 0 12px 0 0 !important;
  padding: 0 !important;
  color: #606266 !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 32px !important;
  text-align: right !important;
  vertical-align: top !important;
}
body.model-notificationtemplate .form-row .checkbox-row {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}
body.model-notificationtemplate .form-row .checkbox-row label {
  flex: 0 0 auto !important;
  width: auto !important;
  text-align: left !important;
  line-height: 1.4 !important;
}
body.model-notificationtemplate .form-row label.required::before,
body.model-notificationtemplate .form-row .required label::before,
body.model-notificationtemplate label.required:before {
  content: '*' !important;
  color: #f56c6c !important;
  margin-right: 4px !important;
  font-weight: 600 !important;
}
/* 输入控件：浅灰边、圆角、聚焦紫色 */
body.model-notificationtemplate .form-row input[type="text"],
body.model-notificationtemplate .form-row input[type="url"],
body.model-notificationtemplate .form-row input[type="email"],
body.model-notificationtemplate .form-row input[type="number"],
body.model-notificationtemplate .form-row input[type="password"],
body.model-notificationtemplate .form-row select,
body.model-notificationtemplate .form-row textarea,
body.model-notificationtemplate .el-input,
body.model-notificationtemplate .el-textarea,
body.model-notificationtemplate .el-select,
body.model-notificationtemplate .el-input__inner,
body.model-notificationtemplate .el-textarea__inner {
  flex: 1 1 auto !important;
  width: auto !important;
  max-width: calc(100% - 112px) !important;
  box-sizing: border-box !important;
  background: #fff !important;
  border: 1px solid #dcdfe6 !important;
  border-radius: 4px !important;
  color: #606266 !important;
  font-size: 14px !important;
  padding: 8px 12px !important;
  min-height: 32px !important;
  line-height: 1.5 !important;
  box-shadow: none !important;
  transition: border-color .2s !important;
  vertical-align: top !important;
}
body.model-notificationtemplate .el-input,
body.model-notificationtemplate .el-textarea,
body.model-notificationtemplate .el-select {
  border: none !important;
  padding: 0 !important;
  max-width: calc(100% - 112px) !important;
}
body.model-notificationtemplate .el-input .el-input__inner,
body.model-notificationtemplate .el-textarea .el-textarea__inner {
  max-width: 100% !important;
  width: 100% !important;
}
body.model-notificationtemplate .form-row textarea,
body.model-notificationtemplate .el-textarea__inner {
  min-height: 120px !important;
  resize: vertical !important;
}
body.model-notificationtemplate .form-row.field-content textarea,
body.model-notificationtemplate .form-row.field-content .el-textarea__inner {
  min-height: 180px !important;
}
body.model-notificationtemplate .form-row input:focus,
body.model-notificationtemplate .form-row select:focus,
body.model-notificationtemplate .form-row textarea:focus,
body.model-notificationtemplate .el-input.is-focus .el-input__inner,
body.model-notificationtemplate .el-textarea__inner:focus {
  border-color: #6c5ce7 !important;
  outline: none !important;
  box-shadow: 0 0 0 1px rgba(108, 92, 231, 0.15) !important;
}
body.model-notificationtemplate .form-row input::placeholder,
body.model-notificationtemplate .form-row textarea::placeholder {
  color: #c0c4cc !important;
}
body.model-notificationtemplate .form-row .help,
body.model-notificationtemplate .form-row .help-block {
  margin: 6px 0 0 112px !important;
  color: #909399 !important;
  font-size: 12px !important;
  line-height: 1.6 !important;
  width: calc(100% - 120px) !important;
}
body.model-notificationtemplate .form-row .errorlist {
  margin: 4px 0 4px 112px !important;
  color: #f56c6c !important;
  list-style: none !important;
  padding: 0 !important;
}
/* 布尔勾选：紫色 */
body.model-notificationtemplate .form-row input[type="checkbox"] {
  width: 16px !important;
  height: 16px !important;
  min-height: 16px !important;
  accent-color: #6c5ce7 !important;
  margin-top: 8px !important;
}
/* 底部按钮：紫主按钮 + 白次按钮 */
body.model-notificationtemplate .submit-row {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  gap: 12px !important;
  margin: 8px 0 0 !important;
  padding: 20px 0 0 !important;
  border-top: 1px solid #ebeef5 !important;
  background: transparent !important;
  text-align: left !important;
}
body.model-notificationtemplate .submit-row .other-wrap,
body.model-notificationtemplate .submit-row .delete-wrap {
  float: none !important;
  display: inline-flex !important;
  gap: 12px !important;
}
body.model-notificationtemplate .submit-row .el-button--primary,
body.model-notificationtemplate .submit-row button[name="_save"],
body.model-notificationtemplate .submit-row input[name="_save"] {
  background: #6c5ce7 !important;
  border: 1px solid #6c5ce7 !important;
  color: #fff !important;
  border-radius: 4px !important;
  padding: 10px 20px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  height: auto !important;
  box-shadow: 0 4px 12px rgba(108, 92, 231, 0.28) !important;
  cursor: pointer !important;
}
body.model-notificationtemplate .submit-row .el-button--primary:hover,
body.model-notificationtemplate .submit-row button[name="_save"]:hover {
  background: #8b7cf0 !important;
  border-color: #8b7cf0 !important;
}
body.model-notificationtemplate .submit-row .el-button--default,
body.model-notificationtemplate .submit-row .el-button.is-plain,
body.model-notificationtemplate .page-header .el-button {
  background: #fff !important;
  border: 1px solid #dcdfe6 !important;
  color: #606266 !important;
  border-radius: 4px !important;
  box-shadow: none !important;
}
body.model-notificationtemplate .submit-row .el-button--danger,
body.model-notificationtemplate .deletelink {
  display: none !important;
}
`,Bt={__name:"AdminEmbed",props:{path:{type:String,default:""},title:{type:String,default:""},refreshLabel:{type:String,default:"刷新"}},setup(nt){const C=nt,N=xt(),W=g(null),X=g(0),z=g(!1),G=V(()=>C.title||N.meta?.embedTitle||N.meta?.title||""),it=V(()=>C.refreshLabel||N.meta?.refreshLabel||"刷新"),x=V(()=>C.path||N.meta?.adminPath||""),rt=V(()=>x.value),J=V(()=>String(x.value||"").includes("notificationtemplate")),lt=V(()=>String(x.value||"").includes("performancestatistics")),dt=V(()=>String(x.value||"").includes("requestperformancelog")),S=g(!1),j=g(!1),P=g(null),$=g(!1),B=g(null),d=vt({name:"",template_type:"markdown",subject:"",description:"",content:"",is_default:!1,is_active:!0}),st={name:[{required:!0,message:"请输入模板名称",trigger:"blur"}],template_type:[{required:!0,message:"请选择模板类型",trigger:"change"}],content:[{required:!0,message:"请输入模板内容",trigger:"blur"}]};function R(){P.value=null,j.value=!1,Object.assign(d,{name:"",template_type:"markdown",subject:"",description:"",content:"",is_default:!1,is_active:!0}),B.value?.clearValidate?.()}function K(){R(),j.value=!1,S.value=!0}async function Y(e){R(),j.value=!0,P.value=e,S.value=!0;try{const t=await At(e),a=t?.data||t;Object.assign(d,{name:a.name||"",template_type:a.template_type||"markdown",subject:a.subject||"",description:a.description||"",content:a.content||"",is_default:!!a.is_default,is_active:a.is_active!==!1})}catch(t){const a=t?.response?.data?.detail||t?.message||"加载模板失败";q.error(typeof a=="string"?a:"加载模板失败"),S.value=!1}}async function pt(){try{await B.value?.validate?.()}catch{return}$.value=!0;try{const e={name:d.name,template_type:d.template_type,subject:d.subject,description:d.description,content:d.content,is_default:d.is_default,is_active:d.is_active};j.value&&P.value?(await Vt(P.value,e),q.success("通知模板已更新")):(await Et(e),q.success("通知模板已创建")),S.value=!1,tt()}catch(e){const t=e?.response?.data;let a="保存失败";if(typeof t=="string")a=t;else if(t?.detail)a=t.detail;else if(t&&typeof t=="object"){const i=Object.values(t)[0];a=Array.isArray(i)?i[0]:i||a}else e?.message&&(a=e.message);q.error(a)}finally{$.value=!1}}function mt(e){if(!e||!J.value)return;const t=e.defaultView;if(!t)return;const a=String(t.location?.href||t.location?.pathname||""),i=a.match(/\/notificationtemplate\/(\d+)\/change\/?/),_=/\/notificationtemplate\/add\/?/.test(a);if(_||i){const l=x.value.endsWith("/")?x.value:`${x.value}/`;t.location.replace(l),_?K():i?.[1]&&Y(i[1]);return}if(e.getElementById("th-tpl-dialog-bound"))return;const u=e.createElement("meta");u.id="th-tpl-dialog-bound",e.head.appendChild(u);const k=l=>String(l||"").match(/\/notificationtemplate\/(\d+)\/change\/?/)?.[1]||null;e.addEventListener("click",l=>{const c=l.target;if(!c||!c.closest)return;const w=c.closest('a.th-edit-btn, a[href*="/notificationtemplate/"][href*="/change/"]');if(w){const r=k(w.getAttribute("href"));if(r){l.preventDefault(),l.stopPropagation(),Y(r);return}}c.closest('.el-button[data-name="add_item"], a.addlink, .object-tools a[href*="/add/"]')&&(l.preventDefault(),l.stopPropagation(),K())},!0)}const T=g(!1),M=g(!1),f=g(null),I=g(!1),F=g(!1),h=g(null);function U(e){if(e==null||e==="")return"-";const t=Number(e);return Number.isNaN(t)?String(e):`${t.toFixed(2)}ms`}function Q(e){if(e==null||e==="")return"-";const t=Number(e);return Number.isNaN(t)?String(e):`${t.toFixed(2)}%`}function H(e){if(!e)return"-";try{const t=new Date(e);if(Number.isNaN(t.getTime()))return String(e);const a=i=>String(i).padStart(2,"0");return`${t.getFullYear()}-${a(t.getMonth()+1)}-${a(t.getDate())} ${a(t.getHours())}:${a(t.getMinutes())}:${a(t.getSeconds())}`}catch{return String(e)}}function ct(e){const t=Number(e);return t>=500?"danger":t>=400?"warning":t>=200?"success":"info"}function ut(e){const t=Number(e);return t>1e3?"danger":t>500?"warning":"success"}async function ft(e){T.value=!0,M.value=!0,f.value=null;try{const t=await Dt(e);f.value=t?.data||t}catch(t){const a=t?.response?.data?.detail||t?.message||"加载详情失败";q.error(typeof a=="string"?a:"加载详情失败"),T.value=!1}finally{M.value=!1}}async function bt(e){I.value=!0,F.value=!0,h.value=null;try{const t=await qt(e);h.value=t?.data||t}catch(t){const a=t?.response?.data?.detail||t?.message||"加载详情失败";q.error(typeof a=="string"?a:"加载详情失败"),I.value=!1}finally{F.value=!1}}function Z(e,t){if(!e||!t?.enabled)return;const{modelSlug:a,flagId:i,openDetail:_}=t,u=e.defaultView;if(!u)return;const l=String(u.location?.href||u.location?.pathname||"").match(new RegExp(`/${a}/(\\d+)/change/?`));if(l){const b=x.value.endsWith("/")?x.value:`${x.value}/`;u.location.replace(b),_(l[1]);return}if(e.getElementById(i))return;const c=e.createElement("meta");c.id=i,e.head.appendChild(c);const w=b=>String(b||"").match(new RegExp(`/${a}/(\\d+)/change/?`))?.[1]||null;e.addEventListener("click",b=>{const r=b.target;if(!r||!r.closest)return;const v=r.closest(`a[href*="/${a}/"][href*="/change/"]`);if(!v)return;const A=w(v.getAttribute("href"));A&&(b.preventDefault(),b.stopPropagation(),_(A))},!0)}function ht(e){if(!e||!e.head)return;const t=e.getElementById("th-admin-embed-theme");t&&t.remove();const a=e.createElement("style");a.id="th-admin-embed-theme",a.textContent=$t,e.head.appendChild(a);try{e.querySelectorAll("#result_list thead th, #result_list tbody td, #result_list tbody th").forEach(i=>{i.style.setProperty("text-align","center","important"),i.style.setProperty("vertical-align","middle","important")}),e.querySelectorAll("#result_list thead th .text").forEach(i=>{i.style.setProperty("float","none","important"),i.style.setProperty("text-align","center","important"),i.style.setProperty("display","block","important")}),e.querySelectorAll("#result_list tbody th, #result_list tbody th a").forEach(i=>{i.style.setProperty("color","#000000","important"),i.style.setProperty("font-weight","500","important"),i.style.setProperty("text-decoration","none","important")}),e.querySelectorAll("#result_list thead th a").forEach(i=>{i.removeAttribute("href"),i.style.pointerEvents="none",i.style.cursor="default",i.style.color="#303133"}),e.querySelectorAll("#result_list thead th .sortoptions").forEach(i=>{i.style.display="none"})}catch{}String(x.value||"").includes("requestperformancelog")&&gt(e),J.value&&mt(e),Z(e,{enabled:lt.value,modelSlug:"performancestatistics",flagId:"th-stats-detail-bound",openDetail:ft}),Z(e,{enabled:dt.value,modelSlug:"requestperformancelog",flagId:"th-log-detail-bound",openDetail:bt})}function gt(e){const t=e.defaultView;if(!t||e.getElementById("th-select-across-bound"))return;const a=e.createElement("meta");a.id="th-select-across-bound",e.head.appendChild(a);const i=l=>{const c=l?1:0;try{t._action&&(t._action.select_across=c)}catch{}e.querySelectorAll('input[name="select_across"]').forEach(v=>{v.value=String(c),v.setAttribute("value",String(c)),v.dispatchEvent(new Event("input",{bubbles:!0})),v.dispatchEvent(new Event("change",{bubbles:!0}))});const w=e.querySelector(".actions .question"),b=e.querySelector(".actions .clear"),r=e.querySelector(".actions .all");w&&(w.style.display=l?"none":""),b&&(b.style.display=l?"":"none"),r&&(r.style.display=l?"":"none")},_=()=>{const l=e.getElementById("action-toggle");!l||l.dataset.thAcrossBound==="1"||(l.dataset.thAcrossBound="1",l.addEventListener("click",()=>{setTimeout(()=>{l.checked?(typeof t.selectAll=="function"&&t.selectAll(),i(!0)):(typeof t.unSelect=="function"&&t.unSelect(),i(!1))},0)}),l.addEventListener("change",()=>{l.checked?(typeof t.selectAll=="function"&&t.selectAll(),i(!0)):(typeof t.unSelect=="function"&&t.unSelect(),i(!1))}))};_(),e.addEventListener("change",l=>{const c=l.target;!c||!c.classList||!c.classList.contains("action-select")||c.checked||i(!1)});let u=0;const k=t.setInterval(()=>{u+=1,_(),(e.getElementById("action-toggle")?.dataset.thAcrossBound==="1"||u>20)&&t.clearInterval(k)},200)}function _t(){z.value=!1;try{const e=W.value?.contentDocument;ht(e)}catch(e){console.warn("[AdminEmbed] inject theme failed",e)}}function tt(){z.value=!0,X.value+=1}return(e,t)=>{const a=y("el-icon"),i=y("el-button"),_=y("el-input"),u=y("el-form-item"),k=y("el-option"),l=y("el-select"),c=y("el-switch"),w=y("el-form"),b=y("el-dialog"),r=y("el-descriptions-item"),v=y("el-descriptions"),A=y("el-tag"),et=wt("loading");return E(),L("div",jt,[G.value?(E(),L("div",Tt,[D("h1",It,m(G.value),1),D("div",Lt,[o(i,{type:"primary",loading:z.value,onClick:tt},{default:n(()=>[o(a,null,{default:n(()=>[o(kt(St))]),_:1}),p(" "+m(it.value),1)]),_:1},8,["loading"])])])):O("",!0),D("div",Nt,[(E(),L("iframe",{ref_key:"iframeRef",ref:W,key:X.value,src:rt.value,class:"admin-iframe",frameborder:"0",allowfullscreen:"",onLoad:_t},null,40,Pt))]),o(b,{modelValue:S.value,"onUpdate:modelValue":t[8]||(t[8]=s=>S.value=s),title:j.value?"编辑通知模板":"增加通知模板",width:"720px","close-on-click-modal":!1,"destroy-on-close":"",class:"tpl-dialog",onClosed:R},{footer:n(()=>[o(i,{onClick:t[7]||(t[7]=s=>S.value=!1)},{default:n(()=>[...t[15]||(t[15]=[p("取消",-1)])]),_:1}),o(i,{type:"primary",loading:$.value,onClick:pt},{default:n(()=>[...t[16]||(t[16]=[p("保存",-1)])]),_:1},8,["loading"])]),default:n(()=>[o(w,{ref_key:"tplFormRef",ref:B,model:d,rules:st,"label-width":"110px",class:"tpl-form"},{default:n(()=>[o(u,{label:"模板名称",prop:"name"},{default:n(()=>[o(_,{modelValue:d.name,"onUpdate:modelValue":t[0]||(t[0]=s=>d.name=s),placeholder:"请输入模板名称",maxlength:"100"},null,8,["modelValue"])]),_:1}),o(u,{label:"模板类型",prop:"template_type"},{default:n(()=>[o(l,{modelValue:d.template_type,"onUpdate:modelValue":t[1]||(t[1]=s=>d.template_type=s),placeholder:"请选择模板类型",style:{width:"100%"}},{default:n(()=>[o(k,{label:"Markdown",value:"markdown"}),o(k,{label:"HTML",value:"html"}),o(k,{label:"纯文本",value:"text"})]),_:1},8,["modelValue"])]),_:1}),o(u,{label:"邮件主题",prop:"subject"},{default:n(()=>[o(_,{modelValue:d.subject,"onUpdate:modelValue":t[2]||(t[2]=s=>d.subject=s),placeholder:"邮件通知使用的主题，支持 {{变量}} 替换",maxlength:"200"},null,8,["modelValue"])]),_:1}),o(u,{label:"模板描述",prop:"description"},{default:n(()=>[o(_,{modelValue:d.description,"onUpdate:modelValue":t[3]||(t[3]=s=>d.description=s),type:"textarea",rows:2,placeholder:"对该模板用途的简要描述"},null,8,["modelValue"])]),_:1}),o(u,{label:"模板内容",prop:"content"},{default:n(()=>[o(_,{modelValue:d.content,"onUpdate:modelValue":t[4]||(t[4]=s=>d.content=s),type:"textarea",rows:8,placeholder:"请输入模板内容，支持 {{变量}} 替换"},null,8,["modelValue"]),D("div",{class:"tpl-help",innerHTML:zt})]),_:1}),o(u,{label:"是否默认模板",prop:"is_default"},{default:n(()=>[o(c,{modelValue:d.is_default,"onUpdate:modelValue":t[5]||(t[5]=s=>d.is_default=s)},null,8,["modelValue"])]),_:1}),o(u,{label:"是否启用",prop:"is_active"},{default:n(()=>[o(c,{modelValue:d.is_active,"onUpdate:modelValue":t[6]||(t[6]=s=>d.is_active=s)},null,8,["modelValue"])]),_:1})]),_:1},8,["model"])]),_:1},8,["modelValue","title"]),o(b,{modelValue:T.value,"onUpdate:modelValue":t[10]||(t[10]=s=>T.value=s),title:"性能统计详情",width:"640px","destroy-on-close":"",onClosed:t[11]||(t[11]=s=>f.value=null)},{footer:n(()=>[o(i,{type:"primary",onClick:t[9]||(t[9]=s=>T.value=!1)},{default:n(()=>[...t[17]||(t[17]=[p("关闭",-1)])]),_:1})]),default:n(()=>[ot((E(),L("div",null,[f.value?(E(),at(v,{key:0,column:2,border:""},{default:n(()=>[o(r,{label:"日期"},{default:n(()=>[p(m(f.value.date||"-"),1)]),_:1}),o(r,{label:"总请求数"},{default:n(()=>[p(m(f.value.total_requests??"-"),1)]),_:1}),o(r,{label:"平均响应时间"},{default:n(()=>[p(m(U(f.value.avg_response_time)),1)]),_:1}),o(r,{label:"最大响应时间"},{default:n(()=>[p(m(U(f.value.max_response_time)),1)]),_:1}),o(r,{label:"最小响应时间"},{default:n(()=>[p(m(U(f.value.min_response_time)),1)]),_:1}),o(r,{label:"错误请求数"},{default:n(()=>[p(m(f.value.error_count??"-"),1)]),_:1}),o(r,{label:"慢请求数(>1s)"},{default:n(()=>[p(m(f.value.slow_requests??"-"),1)]),_:1}),o(r,{label:"错误率"},{default:n(()=>[p(m(Q(f.value.error_rate)),1)]),_:1}),o(r,{label:"慢请求率"},{default:n(()=>[p(m(Q(f.value.slow_rate)),1)]),_:1}),o(r,{label:"创建时间"},{default:n(()=>[p(m(H(f.value.created_at)),1)]),_:1}),o(r,{label:"更新时间",span:2},{default:n(()=>[p(m(H(f.value.updated_at)),1)]),_:1})]),_:1})):O("",!0)])),[[et,M.value]])]),_:1},8,["modelValue"]),o(b,{modelValue:I.value,"onUpdate:modelValue":t[13]||(t[13]=s=>I.value=s),title:"日志详情",width:"720px","destroy-on-close":"",onClosed:t[14]||(t[14]=s=>h.value=null)},{footer:n(()=>[o(i,{type:"primary",onClick:t[12]||(t[12]=s=>I.value=!1)},{default:n(()=>[...t[18]||(t[18]=[p("关闭",-1)])]),_:1})]),default:n(()=>[ot((E(),L("div",null,[h.value?(E(),at(v,{key:0,column:2,border:""},{default:n(()=>[o(r,{label:"请求路径",span:2},{default:n(()=>[D("span",Ut,m(h.value.path||"-"),1)]),_:1}),o(r,{label:"请求方法"},{default:n(()=>[o(A,{size:"small",effect:"plain",type:"primary"},{default:n(()=>[p(m(h.value.method||"-"),1)]),_:1})]),_:1}),o(r,{label:"状态码"},{default:n(()=>[o(A,{size:"small",type:ct(h.value.status_code)},{default:n(()=>[p(m(h.value.status_code??"-"),1)]),_:1},8,["type"])]),_:1}),o(r,{label:"响应时间"},{default:n(()=>[o(A,{size:"small",type:ut(h.value.response_time)},{default:n(()=>[p(m(U(h.value.response_time)),1)]),_:1},8,["type"])]),_:1}),o(r,{label:"用户"},{default:n(()=>[p(m(h.value.user_display||"-"),1)]),_:1}),o(r,{label:"IP地址"},{default:n(()=>[p(m(h.value.ip_address||"-"),1)]),_:1}),o(r,{label:"创建时间"},{default:n(()=>[p(m(H(h.value.created_at)),1)]),_:1}),o(r,{label:"User-Agent",span:2},{default:n(()=>[D("span",Ct,m(h.value.user_agent||"-"),1)]),_:1})]),_:1})):O("",!0)])),[[et,F.value]])]),_:1},8,["modelValue"])])}}},Mt=yt(Bt,[["__scopeId","data-v-b185d549"]]);export{Mt as default};
