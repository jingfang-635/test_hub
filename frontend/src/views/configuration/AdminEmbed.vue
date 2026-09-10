<template>
  <div class="admin-embed-page">
    <!-- 标题在模块外层（对齐「创建测试用例」等页面） -->
    <div v-if="pageTitle" class="page-header">
      <h1 class="page-title">{{ pageTitle }}</h1>
      <div class="header-actions">
        <el-button type="primary" :loading="reloading" @click="reload">
          <el-icon><Refresh /></el-icon>
          {{ pageRefreshLabel }}
        </el-button>
      </div>
    </div>

    <div class="content">
      <iframe
        ref="iframeRef"
        :key="iframeKey"
        :src="adminUrl"
        class="admin-iframe"
        frameborder="0"
        allowfullscreen
        @load="onIframeLoad"
      />
    </div>

    <!-- 通知模板：增加 / 编辑弹窗 -->
    <el-dialog
      v-model="tplDialogVisible"
      :title="tplIsEdit ? '编辑通知模板' : '增加通知模板'"
      width="720px"
      :close-on-click-modal="false"
      destroy-on-close
      class="tpl-dialog"
      @closed="resetTplForm"
    >
      <el-form
        ref="tplFormRef"
        :model="tplForm"
        :rules="tplRules"
        label-width="110px"
        class="tpl-form"
      >
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="tplForm.name" placeholder="请输入模板名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="模板类型" prop="template_type">
          <el-select v-model="tplForm.template_type" placeholder="请选择模板类型" style="width: 100%">
            <el-option label="Markdown" value="markdown" />
            <el-option label="HTML" value="html" />
            <el-option label="纯文本" value="text" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮件主题" prop="subject">
          <el-input
            v-model="tplForm.subject"
            :placeholder="'邮件通知使用的主题，支持 {{变量}} 替换'"
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="模板描述" prop="description">
          <el-input
            v-model="tplForm.description"
            type="textarea"
            :rows="2"
            placeholder="对该模板用途的简要描述"
          />
        </el-form-item>
        <el-form-item label="模板内容" prop="content">
          <el-input
            v-model="tplForm.content"
            type="textarea"
            :rows="8"
            :placeholder="'请输入模板内容，支持 {{变量}} 替换'"
          />
          <div class="tpl-help" v-html="tplContentHelpHtml" />
        </el-form-item>
        <el-form-item label="是否默认模板" prop="is_default">
          <el-switch v-model="tplForm.is_default" />
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="tplForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tplDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="tplSubmitting" @click="submitTplForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 性能统计详情弹窗 -->
    <el-dialog
      v-model="statsDialogVisible"
      title="性能统计详情"
      width="640px"
      destroy-on-close
      @closed="statsDetail = null"
    >
      <div v-loading="statsLoading">
        <el-descriptions v-if="statsDetail" :column="2" border>
          <el-descriptions-item label="日期">{{ statsDetail.date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="总请求数">{{ statsDetail.total_requests ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="平均响应时间">
            {{ formatMs(statsDetail.avg_response_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="最大响应时间">
            {{ formatMs(statsDetail.max_response_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="最小响应时间">
            {{ formatMs(statsDetail.min_response_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="错误请求数">{{ statsDetail.error_count ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="慢请求数(>1s)">{{ statsDetail.slow_requests ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误率">{{ formatRate(statsDetail.error_rate) }}</el-descriptions-item>
          <el-descriptions-item label="慢请求率">{{ formatRate(statsDetail.slow_rate) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(statsDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">
            {{ formatDateTime(statsDetail.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button type="primary" @click="statsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 请求性能日志详情弹窗 -->
    <el-dialog
      v-model="logDialogVisible"
      title="日志详情"
      width="720px"
      destroy-on-close
      @closed="logDetail = null"
    >
      <div v-loading="logLoading">
        <el-descriptions v-if="logDetail" :column="2" border>
          <el-descriptions-item label="请求路径" :span="2">
            <span class="mono-text">{{ logDetail.path || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="请求方法">
            <el-tag size="small" effect="plain" type="primary">{{ logDetail.method || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态码">
            <el-tag size="small" :type="statusTagType(logDetail.status_code)">
              {{ logDetail.status_code ?? '-' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            <el-tag size="small" :type="rtTagType(logDetail.response_time)">
              {{ formatMs(logDetail.response_time) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="用户">{{ logDetail.user_display || '-' }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ logDetail.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(logDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="User-Agent" :span="2">
            <span class="mono-text wrap">{{ logDetail.user_agent || '-' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button type="primary" @click="logDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getNotificationTemplateDetail,
  createNotificationTemplate,
  updateNotificationTemplate,
  getRequestPerformanceLogDetail,
  getPerformanceStatisticsDetail
} from '@/api/core'

const props = defineProps({
  // Admin 路径，如 '/admin/core/performancestatistics/'
  path: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  refreshLabel: {
    type: String,
    default: '刷新'
  }
})

const route = useRoute()
const iframeRef = ref(null)
const iframeKey = ref(0)
const reloading = ref(false)

const pageTitle = computed(() => props.title || route.meta?.embedTitle || route.meta?.title || '')
const pageRefreshLabel = computed(() => props.refreshLabel || route.meta?.refreshLabel || '刷新')
const adminPath = computed(() => props.path || route.meta?.adminPath || '')

const adminUrl = computed(() => {
  // 通过 Vite 代理使用同源 URL，避免 iframe 跨域问题
  return adminPath.value
})

const isNotificationTemplate = computed(() =>
  String(adminPath.value || '').includes('notificationtemplate')
)
const isPerformanceStats = computed(() =>
  String(adminPath.value || '').includes('performancestatistics')
)
const isRequestPerfLog = computed(() =>
  String(adminPath.value || '').includes('requestperformancelog')
)

// ---------- 通知模板弹窗 ----------
const tplDialogVisible = ref(false)
const tplIsEdit = ref(false)
const tplEditId = ref(null)
const tplSubmitting = ref(false)
const tplFormRef = ref(null)
const tplForm = reactive({
  name: '',
  template_type: 'markdown',
  subject: '',
  description: '',
  content: '',
  is_default: false,
  is_active: true
})
const tplRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_type: [{ required: true, message: '请选择模板类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }]
}
const tplContentHelpHtml = `
  支持以下变量替换（在模板内容中使用 {{变量名}} 即可）：<br>
  <b>任务相关：</b>
  {{task_name}} 任务名称、{{status_text}} 执行状态、{{execution_time}} 执行时间、{{task_type}} 任务类型<br>
  <b>测试相关：</b>
  {{title}} 测试标题、{{tester}} 测试人员、{{total_cases}} 用例总数、{{passed_cases}} 通过用例数、
  {{failed_cases}} 失败用例数、{{error_cases}} 错误用例数、{{skipped_cases}} 跳过用例数、
  {{runtime}} 执行时长、{{begin_time}} 开始时间
`

function resetTplForm() {
  tplEditId.value = null
  tplIsEdit.value = false
  Object.assign(tplForm, {
    name: '',
    template_type: 'markdown',
    subject: '',
    description: '',
    content: '',
    is_default: false,
    is_active: true
  })
  tplFormRef.value?.clearValidate?.()
}

function openTplCreate() {
  resetTplForm()
  tplIsEdit.value = false
  tplDialogVisible.value = true
}

async function openTplEdit(id) {
  resetTplForm()
  tplIsEdit.value = true
  tplEditId.value = id
  tplDialogVisible.value = true
  try {
    const res = await getNotificationTemplateDetail(id)
    const data = res?.data || res
    Object.assign(tplForm, {
      name: data.name || '',
      template_type: data.template_type || 'markdown',
      subject: data.subject || '',
      description: data.description || '',
      content: data.content || '',
      is_default: !!data.is_default,
      is_active: data.is_active !== false
    })
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载模板失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载模板失败')
    tplDialogVisible.value = false
  }
}

async function submitTplForm() {
  try {
    await tplFormRef.value?.validate?.()
  } catch {
    return
  }
  tplSubmitting.value = true
  try {
    const payload = {
      name: tplForm.name,
      template_type: tplForm.template_type,
      subject: tplForm.subject,
      description: tplForm.description,
      content: tplForm.content,
      is_default: tplForm.is_default,
      is_active: tplForm.is_active
    }
    if (tplIsEdit.value && tplEditId.value) {
      await updateNotificationTemplate(tplEditId.value, payload)
      ElMessage.success('通知模板已更新')
    } else {
      await createNotificationTemplate(payload)
      ElMessage.success('通知模板已创建')
    }
    tplDialogVisible.value = false
    reload()
  } catch (e) {
    const data = e?.response?.data
    let msg = '保存失败'
    if (typeof data === 'string') msg = data
    else if (data?.detail) msg = data.detail
    else if (data && typeof data === 'object') {
      const first = Object.values(data)[0]
      msg = Array.isArray(first) ? first[0] : (first || msg)
    } else if (e?.message) {
      msg = e.message
    }
    ElMessage.error(msg)
  } finally {
    tplSubmitting.value = false
  }
}

/**
 * 通知模板列表：拦截「增加」「编辑」，改为外层弹窗。
 * 若已误入 add/change 表单页，则退回列表。
 */
function bindNotificationTemplateDialog(doc) {
  if (!doc || !isNotificationTemplate.value) return
  const win = doc.defaultView
  if (!win) return

  const href = String(win.location?.href || win.location?.pathname || '')
  const changeMatch = href.match(/\/notificationtemplate\/(\d+)\/change\/?/)
  const isAdd = /\/notificationtemplate\/add\/?/.test(href)
  if (isAdd || changeMatch) {
    // 回到列表，避免在 iframe 内展示整页表单
    const listUrl = adminPath.value.endsWith('/') ? adminPath.value : `${adminPath.value}/`
    win.location.replace(listUrl)
    if (isAdd) {
      openTplCreate()
    } else if (changeMatch?.[1]) {
      openTplEdit(changeMatch[1])
    }
    return
  }

  if (doc.getElementById('th-tpl-dialog-bound')) return
  const flag = doc.createElement('meta')
  flag.id = 'th-tpl-dialog-bound'
  doc.head.appendChild(flag)

  const extractIdFromHref = (hrefVal) => {
    const m = String(hrefVal || '').match(/\/notificationtemplate\/(\d+)\/change\/?/)
    return m?.[1] || null
  }

  doc.addEventListener(
    'click',
    (e) => {
      const target = e.target
      if (!target || !target.closest) return

      // 编辑链接
      const editLink = target.closest('a.th-edit-btn, a[href*="/notificationtemplate/"][href*="/change/"]')
      if (editLink) {
        const id = extractIdFromHref(editLink.getAttribute('href'))
        if (id) {
          e.preventDefault()
          e.stopPropagation()
          openTplEdit(id)
          return
        }
      }

      // 增加按钮（SimpleUI / Django）
      const addBtn = target.closest(
        '.el-button[data-name="add_item"], a.addlink, .object-tools a[href*="/add/"]'
      )
      if (addBtn) {
        e.preventDefault()
        e.stopPropagation()
        openTplCreate()
      }
    },
    true
  )
}

// ---------- 性能统计 / 请求性能日志 详情弹窗 ----------
const statsDialogVisible = ref(false)
const statsLoading = ref(false)
const statsDetail = ref(null)

const logDialogVisible = ref(false)
const logLoading = ref(false)
const logDetail = ref(null)

function formatMs(value) {
  if (value === null || value === undefined || value === '') return '-'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return `${n.toFixed(2)}ms`
}

function formatRate(value) {
  if (value === null || value === undefined || value === '') return '-'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return `${n.toFixed(2)}%`
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return String(value)
    const pad = (x) => String(x).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return String(value)
  }
}

function statusTagType(code) {
  const n = Number(code)
  if (n >= 500) return 'danger'
  if (n >= 400) return 'warning'
  if (n >= 200) return 'success'
  return 'info'
}

function rtTagType(ms) {
  const n = Number(ms)
  if (n > 1000) return 'danger'
  if (n > 500) return 'warning'
  return 'success'
}

async function openStatsDetail(id) {
  statsDialogVisible.value = true
  statsLoading.value = true
  statsDetail.value = null
  try {
    const res = await getPerformanceStatisticsDetail(id)
    statsDetail.value = res?.data || res
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载详情失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载详情失败')
    statsDialogVisible.value = false
  } finally {
    statsLoading.value = false
  }
}

async function openLogDetail(id) {
  logDialogVisible.value = true
  logLoading.value = true
  logDetail.value = null
  try {
    const res = await getRequestPerformanceLogDetail(id)
    logDetail.value = res?.data || res
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载详情失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载详情失败')
    logDialogVisible.value = false
  } finally {
    logLoading.value = false
  }
}

/**
 * 性能统计 / 请求性能日志：拦截详情链接，改为外层弹窗。
 */
function bindReadonlyDetailDialog(doc, options) {
  if (!doc || !options?.enabled) return
  const { modelSlug, flagId, openDetail } = options
  const win = doc.defaultView
  if (!win) return

  const href = String(win.location?.href || win.location?.pathname || '')
  const changeMatch = href.match(new RegExp(`/${modelSlug}/(\\d+)/change/?`))
  if (changeMatch) {
    const listUrl = adminPath.value.endsWith('/') ? adminPath.value : `${adminPath.value}/`
    win.location.replace(listUrl)
    openDetail(changeMatch[1])
    return
  }

  if (doc.getElementById(flagId)) return
  const flag = doc.createElement('meta')
  flag.id = flagId
  doc.head.appendChild(flag)

  const extractIdFromHref = (hrefVal) => {
    const m = String(hrefVal || '').match(new RegExp(`/${modelSlug}/(\\d+)/change/?`))
    return m?.[1] || null
  }

  doc.addEventListener(
    'click',
    (e) => {
      const target = e.target
      if (!target || !target.closest) return
      const link = target.closest(`a[href*="/${modelSlug}/"][href*="/change/"]`)
      if (!link) return
      const id = extractIdFromHref(link.getAttribute('href'))
      if (!id) return
      e.preventDefault()
      e.stopPropagation()
      openDetail(id)
    },
    true
  )
}

/** 与测试报告列表对齐的嵌入主题：隐藏 SimpleUI 壳，统一表格/按钮/标签色 */
const EMBED_THEME_CSS = `
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
`

function injectTheme(doc) {
  if (!doc || !doc.head) return
  const existed = doc.getElementById('th-admin-embed-theme')
  if (existed) existed.remove()
  const style = doc.createElement('style')
  style.id = 'th-admin-embed-theme'
  style.textContent = EMBED_THEME_CSS
  doc.head.appendChild(style)

  // 强制第一列（Django 渲染为 tbody th）黑色，并移除表头排序链接；字段名/值居中
  try {
    doc.querySelectorAll('#result_list thead th, #result_list tbody td, #result_list tbody th').forEach((el) => {
      el.style.setProperty('text-align', 'center', 'important')
      el.style.setProperty('vertical-align', 'middle', 'important')
    })
    doc.querySelectorAll('#result_list thead th .text').forEach((el) => {
      el.style.setProperty('float', 'none', 'important')
      el.style.setProperty('text-align', 'center', 'important')
      el.style.setProperty('display', 'block', 'important')
    })
    doc.querySelectorAll('#result_list tbody th, #result_list tbody th a').forEach((el) => {
      el.style.setProperty('color', '#000000', 'important')
      el.style.setProperty('font-weight', '500', 'important')
      el.style.setProperty('text-decoration', 'none', 'important')
    })
    doc.querySelectorAll('#result_list thead th a').forEach((a) => {
      a.removeAttribute('href')
      a.style.pointerEvents = 'none'
      a.style.cursor = 'default'
      a.style.color = '#303133'
    })
    doc.querySelectorAll('#result_list thead th .sortoptions').forEach((el) => {
      el.style.display = 'none'
    })
  } catch (_) { /* ignore */ }

  // 请求性能日志：表头全选 = 跨页全选（select_across=1）
  if (String(adminPath.value || '').includes('requestperformancelog')) {
    injectRequestLogSelectAcross(doc)
  }

  // 通知模板：增加/编辑改为弹窗
  if (isNotificationTemplate.value) {
    bindNotificationTemplateDialog(doc)
  }

  // 性能统计 / 请求性能日志：详情改为弹窗
  bindReadonlyDetailDialog(doc, {
    enabled: isPerformanceStats.value,
    modelSlug: 'performancestatistics',
    flagId: 'th-stats-detail-bound',
    openDetail: openStatsDetail
  })
  bindReadonlyDetailDialog(doc, {
    enabled: isRequestPerfLog.value,
    modelSlug: 'requestperformancelog',
    flagId: 'th-log-detail-bound',
    openDetail: openLogDetail
  })
}

/**
 * 勾选表头全选时，设置 Django/SimpleUI 的 select_across，
 * 使删除等操作作用于当前筛选条件下的全部记录，而非仅当前页。
 */
function injectRequestLogSelectAcross(doc) {
  const win = doc.defaultView
  if (!win || doc.getElementById('th-select-across-bound')) return

  const flag = doc.createElement('meta')
  flag.id = 'th-select-across-bound'
  doc.head.appendChild(flag)

  const setSelectAcross = (enabled) => {
    const value = enabled ? 1 : 0
    try {
      if (win._action) win._action.select_across = value
    } catch (_) { /* ignore */ }
    doc.querySelectorAll('input[name="select_across"]').forEach((el) => {
      el.value = String(value)
      el.setAttribute('value', String(value))
      // 触发 Vue v-model 更新
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    })
    // 更新提示文案区域显示状态（SimpleUI / Django 模板节点）
    const question = doc.querySelector('.actions .question')
    const clear = doc.querySelector('.actions .clear')
    const all = doc.querySelector('.actions .all')
    if (question) question.style.display = enabled ? 'none' : ''
    if (clear) clear.style.display = enabled ? '' : 'none'
    if (all) all.style.display = enabled ? '' : 'none'
  }

  const bindToggle = () => {
    const toggle = doc.getElementById('action-toggle')
    if (!toggle || toggle.dataset.thAcrossBound === '1') return
    toggle.dataset.thAcrossBound = '1'

    toggle.addEventListener('click', () => {
      // click 时 checked 尚未翻转的浏览器极少；用 setTimeout 取最终状态更稳
      setTimeout(() => {
        if (toggle.checked) {
          if (typeof win.selectAll === 'function') {
            win.selectAll()
          }
          setSelectAcross(true)
        } else {
          if (typeof win.unSelect === 'function') {
            win.unSelect()
          }
          setSelectAcross(false)
        }
      }, 0)
    })

    toggle.addEventListener('change', () => {
      if (toggle.checked) {
        if (typeof win.selectAll === 'function') win.selectAll()
        setSelectAcross(true)
      } else {
        if (typeof win.unSelect === 'function') win.unSelect()
        setSelectAcross(false)
      }
    })
  }

  bindToggle()

  // 取消某一行勾选时，退出“跨页全选”
  doc.addEventListener('change', (e) => {
    const t = e.target
    if (!t || !t.classList || !t.classList.contains('action-select')) return
    if (!t.checked) setSelectAcross(false)
  })

  // SimpleUI / 表格可能延迟渲染，短暂重试绑定
  let tries = 0
  const timer = win.setInterval(() => {
    tries += 1
    bindToggle()
    if (doc.getElementById('action-toggle')?.dataset.thAcrossBound === '1' || tries > 20) {
      win.clearInterval(timer)
    }
  }, 200)
}

function onIframeLoad() {
  reloading.value = false
  try {
    const doc = iframeRef.value?.contentDocument
    injectTheme(doc)
  } catch (e) {
    // 跨域时无法注入；同源代理下不应触发
    console.warn('[AdminEmbed] inject theme failed', e)
  }
}

function reload() {
  reloading.value = true
  iframeKey.value += 1
}
</script>

<style scoped>
.admin-embed-page {
  /* 精确占满主内容区，避免撑出外层滚动条 */
  height: calc(100vh - var(--th-header-height, 56px) - 88px);
  max-height: calc(100vh - var(--th-header-height, 56px) - 88px);
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: transparent;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
}

/* 标题在浅色页面背景上，不在白卡片内 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  margin: 0;
  color: var(--th-text-primary, #303133);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 白色内容模块 */
.content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--th-bg-elevated, #fff);
  border: 1px solid var(--th-border, #ebeef5);
  border-radius: var(--th-radius-lg, 8px);
  box-shadow: var(--th-shadow-xs, 0 1px 2px rgba(0, 0, 0, 0.04));
  padding: 4px 4px 0;
  box-sizing: border-box;
}

.admin-iframe {
  width: 100%;
  height: 100%;
  min-height: 0;
  flex: 1;
  border: none;
  border-radius: 4px;
  background: #fff;
}

.tpl-help {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  line-height: 1.7;
}

.tpl-form :deep(.el-textarea__inner) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}

.mono-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  word-break: break-all;
}

.mono-text.wrap {
  white-space: pre-wrap;
}
</style>
