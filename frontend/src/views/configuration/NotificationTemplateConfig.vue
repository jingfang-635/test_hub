<template>
  <div class="page-container notification-template-page">
    <div class="page-header">
      <h1 class="page-title">通知模板列表</h1>
      <div class="header-actions">
        <el-button
          v-if="selectedRows.length > 0"
          type="danger"
          :icon="Delete"
          :disabled="deleting"
          @click="batchDelete"
        >
          批量删除 ({{ selectedRows.length }})
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建通知模板</el-button>
      </div>
    </div>

    <div class="list-card">
      <div class="filter-bar">
        <el-form :inline="true" @submit.prevent>
          <el-form-item>
            <el-input
              v-model="filters.search"
              placeholder="请输入模板名称"
              clearable
              style="width: 220px"
              @keyup.enter="applyFilters"
              @change="applyFilters"
              @clear="applyFilters"
            />
          </el-form-item>
          <el-form-item>
            <el-select
              v-model="filters.template_type"
              placeholder="选择模板类型"
              clearable
              style="width: 180px"
              @change="applyFilters"
            >
              <el-option label="Markdown" value="markdown" />
              <el-option label="HTML" value="html" />
              <el-option label="纯文本" value="text" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select
              v-model="filters.is_active"
              placeholder="选择状态"
              clearable
              style="width: 140px"
              @change="applyFilters"
            >
              <el-option label="启用" :value="true" />
              <el-option label="停用" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        class="template-table"
        :data="templates"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="name" label="模板名称" min-width="180">
          <template #default="scope">
            <span class="name-text">{{ scope.row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="模板类型" width="130" align="center">
          <template #default="scope">
            <el-tag class="type-tag" :type="typeTag(scope.row.template_type)" effect="light">
              {{ scope.row.template_type_display || typeLabel(scope.row.template_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="邮件主题" min-width="180" show-overflow-tooltip>
          <template #default="scope">
            {{ scope.row.subject || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="模板描述" min-width="200" show-overflow-tooltip>
          <template #default="scope">
            {{ scope.row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="是否默认" width="110" align="center">
          <template #default="scope">
            <el-tag class="status-tag" :type="scope.row.is_default ? 'warning' : 'info'" effect="light">
              {{ scope.row.is_default ? '默认' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否启用" width="110" align="center">
          <template #default="scope">
            <el-tag class="status-tag" :type="scope.row.is_active ? 'success' : 'danger'" effect="light">
              {{ scope.row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180" align="center">
          <template #default="scope">
            {{ formatDateTime(scope.row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openEdit(scope.row.id)">编辑</el-button>
            <el-button link type="danger" @click="removeOne(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchList"
        />
      </div>
    </div>

    <!-- 通知模板：新增 / 编辑弹窗（字段保持不变） -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑通知模板' : '增加通知模板'"
      width="720px"
      align-center
      :close-on-click-modal="false"
      destroy-on-close
      class="tpl-dialog"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="tpl-form">
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入模板名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="模板类型" prop="template_type">
          <el-select v-model="form.template_type" placeholder="请选择模板类型" style="width: 100%">
            <el-option label="Markdown" value="markdown" />
            <el-option label="HTML" value="html" />
            <el-option label="纯文本" value="text" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮件主题" prop="subject">
          <el-input
            v-model="form.subject"
            placeholder="邮件通知使用的主题，支持 {{变量}} 替换"
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="模板描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="对该模板用途的简要描述"
          />
        </el-form-item>
        <el-form-item label="模板内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            placeholder="请输入模板内容，支持 {{变量}} 替换"
          />
          <el-collapse v-model="contentHelpActive" class="tpl-help-collapse">
            <el-collapse-item title="可用变量说明（点击展开）" name="help">
              <div class="tpl-help" v-html="contentHelpHtml" />
            </el-collapse-item>
          </el-collapse>
        </el-form-item>
        <el-form-item label="是否默认模板" prop="is_default">
          <el-switch v-model="form.is_default" />
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Delete, Plus, RefreshLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getNotificationTemplates,
  getNotificationTemplateDetail,
  createNotificationTemplate,
  updateNotificationTemplate,
  deleteNotificationTemplate
} from '@/api/core'

const loading = ref(false)
const templates = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedRows = ref([])
const deleting = ref(false)

const filters = reactive({
  search: '',
  template_type: null,
  is_active: null
})

const TYPE_LABELS = { markdown: 'Markdown', html: 'HTML', text: '纯文本' }
const TYPE_TAGS = { markdown: 'info', html: 'primary', text: 'info' }

const contentHelpActive = ref([])

const contentHelpHtml = `
  <b>任务相关：</b>
  {{task_name}} 任务名称、{{status_text}} 执行状态、{{execution_time}} 执行时间、{{task_type}} 任务类型<br>
  <b>测试相关：</b>
  {{title}} 测试标题、{{tester}} 测试人员、{{total_cases}} 用例总数、{{passed_cases}} 通过用例数、
  {{failed_cases}} 失败用例数、{{error_cases}} 错误用例数、{{skipped_cases}} 跳过用例数、
  {{runtime}} 执行时长、{{begin_time}} 开始时间
`

function typeLabel(type) {
  return TYPE_LABELS[type] || type || '-'
}

function typeTag(type) {
  return TYPE_TAGS[type] || 'info'
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

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: (filters.search || '').trim() || undefined,
      template_type: filters.template_type || undefined,
      is_active: filters.is_active === null || filters.is_active === '' ? undefined : filters.is_active
    }
    const res = await getNotificationTemplates(params)
    const data = res?.data || res || {}
    templates.value = data.results || (Array.isArray(data) ? data : [])
    total.value = data.count ?? templates.value.length
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载通知模板失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载通知模板失败')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  currentPage.value = 1
  fetchList()
}

function resetFilters() {
  filters.search = ''
  filters.template_type = null
  filters.is_active = null
  currentPage.value = 1
  fetchList()
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

// ---------- 新增 / 编辑 ----------
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const form = reactive({
  name: '',
  template_type: 'markdown',
  subject: '',
  description: '',
  content: '',
  is_default: false,
  is_active: true
})
const rules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_type: [{ required: true, message: '请选择模板类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }]
}

function resetForm() {
  editId.value = null
  isEdit.value = false
  Object.assign(form, {
    name: '',
    template_type: 'markdown',
    subject: '',
    description: '',
    content: '',
    is_default: false,
    is_active: true
  })
  formRef.value?.clearValidate?.()
}

function openCreate() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}

async function openEdit(id) {
  resetForm()
  isEdit.value = true
  editId.value = id
  dialogVisible.value = true
  try {
    const res = await getNotificationTemplateDetail(id)
    const data = res?.data || res || {}
    Object.assign(form, {
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
    dialogVisible.value = false
  }
}

async function submitForm() {
  try {
    await formRef.value?.validate?.()
  } catch {
    return
  }
  submitting.value = true
  try {
    const payload = {
      name: form.name,
      template_type: form.template_type,
      subject: form.subject,
      description: form.description,
      content: form.content,
      is_default: form.is_default,
      is_active: form.is_active
    }
    if (isEdit.value && editId.value) {
      await updateNotificationTemplate(editId.value, payload)
      ElMessage.success('通知模板已更新')
    } else {
      await createNotificationTemplate(payload)
      ElMessage.success('通知模板已创建')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    const data = e?.response?.data
    let msg = '保存失败'
    if (typeof data === 'string') msg = data
    else if (data?.detail) msg = data.detail
    else if (data && typeof data === 'object') {
      const first = Object.values(data)[0]
      msg = Array.isArray(first) ? first[0] : first || msg
    } else if (e?.message) {
      msg = e.message
    }
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

// ---------- 删除 ----------
async function removeOne(row) {
  try {
    await ElMessageBox.confirm(`确定删除通知模板「${row.name}」吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await deleteNotificationTemplate(row.id)
    ElMessage.success('删除成功')
    if (templates.value.length === 1 && currentPage.value > 1) currentPage.value -= 1
    fetchList()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function batchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的模板')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRows.value.length} 个通知模板吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  deleting.value = true
  let successCount = 0
  let failCount = 0
  for (const row of selectedRows.value) {
    try {
      await deleteNotificationTemplate(row.id)
      successCount += 1
    } catch {
      failCount += 1
    }
  }
  deleting.value = false
  if (successCount > 0 && failCount === 0) {
    ElMessage.success(`成功删除 ${successCount} 个通知模板`)
  } else if (successCount > 0) {
    ElMessage.warning(`删除完成：成功 ${successCount} 个，失败 ${failCount} 个`)
  } else {
    ElMessage.error('删除失败')
  }
  selectedRows.value = []
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.notification-template-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.page-header .page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--th-text-primary);
  letter-spacing: -0.02em;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.list-card {
  background: #ffffff;
  border: 1px solid #e4e9f2;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(31, 45, 92, 0.04);
}

.filter-bar {
  margin-bottom: 20px;
  padding: 14px 16px;
  border-radius: 10px;
}

.filter-bar :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-bar :deep(.el-input__wrapper),
.filter-bar :deep(.el-select__wrapper) {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 0 0 1px #d6e0f0 inset;
}

.filter-bar :deep(.el-input__wrapper.is-focus),
.filter-bar :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #7ea6f0 inset;
}

.filter-bar :deep(.el-button) {
  border-radius: 18px;
}

/* 表格：卡片式圆角、浅蓝表头、白色行 */
.template-table {
  border-radius: 10px;
  overflow: hidden;
}

.template-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.template-table :deep(th.el-table__cell) {
  background-color: #eef2fa;
  color: #4a5568;
  font-weight: 600;
  border-bottom: 1px solid #e0e6f0;
}

.template-table :deep(.el-table__header th) {
  background-color: #eef2fa;
}

.template-table :deep(.el-table__row) {
  background-color: #ffffff;
}

.template-table :deep(.el-table__row:hover > td.el-table__cell) {
  background-color: #f5f8fd;
}

.template-table :deep(td.el-table__cell) {
  border-bottom: 1px solid #eef1f6;
}

.template-table :deep(.name-text) {
  color: var(--th-text-primary);
  font-weight: 500;
}

.template-table :deep(.el-button--primary.is-link) {
  box-shadow: none;
}

.template-table :deep(.type-tag),
.template-table :deep(.status-tag) {
  border-radius: 14px;
  padding: 0 12px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.tpl-help-collapse {
  margin-top: 8px;
  border: none;
}

.tpl-help-collapse :deep(.el-collapse-item__header) {
  height: auto;
  line-height: 1.5;
  padding: 0;
  border: none;
  color: #909399;
  font-size: 12px;
  font-weight: normal;
  background: transparent;
}

.tpl-help-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  background: transparent;
}

.tpl-help-collapse :deep(.el-collapse-item__content) {
  padding: 0;
}

.tpl-help {
  color: #909399;
  font-size: 12px;
  line-height: 1.7;
}

.tpl-form :deep(.el-textarea__inner) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
</style>

<style>
/* 仅改弹窗本体高度；居中交给 align-center，勿改 overlay，否则蒙层易残留 */
.el-dialog.tpl-dialog {
  height: 700px;
  display: flex;
  flex-direction: column;
}

.el-dialog.tpl-dialog .el-dialog__header,
.el-dialog.tpl-dialog .el-dialog__footer {
  flex-shrink: 0;
}

.el-dialog.tpl-dialog .el-dialog__body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}
</style>
