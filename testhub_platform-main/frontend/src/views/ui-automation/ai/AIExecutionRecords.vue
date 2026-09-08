<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('uiAutomation.ai.executionRecords.title') }}</h1>
      <div class="header-actions">
        <el-button
          type="danger"
          :disabled="selectedRecords.length === 0"
          @click="batchDeleteRecords"
          :loading="isDeleting"
        >
          <el-icon><Delete /></el-icon>
          {{ $t('uiAutomation.common.batchDelete') }}
        </el-button>
        <el-button type="primary" @click="openTaskDialog">
          <el-icon><Plus /></el-icon>
          {{ $t('uiAutomation.ai.newTest') }}
        </el-button>
      </div>
    </div>

    <div class="card-container">
      <el-table
        :data="records"
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        ref="tableRef"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column :label="$t('uiAutomation.ai.executionRecords.serialNumber')" width="80">
          <template #default="{ $index }">
            {{ getSerialNumber($index) }}
          </template>
        </el-table-column>
        <el-table-column prop="task_name" :label="$t('uiAutomation.ai.executionRecords.taskName')" min-width="150" show-overflow-tooltip />

        <el-table-column prop="task_source" :label="$t('uiAutomation.ai.executionRecords.taskSource')" width="120">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="openTaskSourceDetail(row)">
              {{ getTaskSourceText(row.task_source) }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="status" :label="$t('uiAutomation.ai.executionRecords.status')" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" :label="$t('uiAutomation.ai.executionRecords.durationSeconds')" width="120">
          <template #default="{ row }">
            {{ row.duration ? row.duration.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="start_time" :label="$t('uiAutomation.ai.executionRecords.startTime')" width="180" :formatter="formatDate" />
        <el-table-column :label="$t('uiAutomation.common.operation')" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              {{ $t('uiAutomation.ai.executionRecords.viewDetail') }}
            </el-button>
            <el-button size="small" type="success" @click="viewReport(row)">
              {{ $t('uiAutomation.ai.executionRecords.viewReport') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 新建测试弹窗 -->
    <el-dialog
      v-model="showTaskDialog"
      :title="$t('uiAutomation.ai.newTest')"
      width="620px"
      :close-on-click-modal="false"
    >
      <el-form :model="taskForm" label-position="top">
        <el-form-item :label="$t('uiAutomation.ai.taskName')" required>
          <el-input
            v-model="taskForm.taskName"
            :placeholder="$t('uiAutomation.ai.taskNamePlaceholder')"
            maxlength="200"
          />
        </el-form-item>

        <el-form-item :label="$t('uiAutomation.ai.taskSource')" label-position="left">
          <el-radio-group v-model="taskForm.taskSource">
            <el-radio label="text">{{ $t('uiAutomation.ai.taskSourceText') }}</el-radio>
            <el-radio label="file">{{ $t('uiAutomation.ai.taskSourceFile') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="taskForm.taskSource === 'text'"
          :label="$t('uiAutomation.ai.taskDescription')"
          required
        >
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="8"
            :placeholder="$t('uiAutomation.ai.taskPlaceholder')"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>

        <el-form-item v-else :label="$t('uiAutomation.ai.caseFile')" required>
          <div class="case-upload-wrap">
            <el-upload
              ref="caseUploadRef"
              class="case-upload"
              drag
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="handleCaseFileChange"
              :disabled="uploadingCases"
            >
              <div class="upload-inner">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">{{ $t('uiAutomation.ai.uploadText') }}</div>
              </div>
            </el-upload>
            <div v-if="uploadingCases" class="case-upload-tip">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>{{ $t('uiAutomation.ai.uploading') }}</span>
            </div>
            <div v-else-if="caseFile.parsed" class="case-upload-result case-upload-ok">
              <el-icon><Check /></el-icon>
              <span class="result-filename" :title="caseFile.name">{{ caseFile.name }}</span>
              <el-tag size="small" type="success">{{ $t('uiAutomation.ai.parsedCount') }} {{ caseFile.caseCount }}</el-tag>
              <span class="preview-spacer"></span>
              <el-button class="preview-btn" link type="primary" size="small" @click.prevent="casePreviewVisible = true">{{ $t('uiAutomation.ai.preview') }}</el-button>
              <el-button link type="danger" size="small" @click.prevent="clearCaseFile">{{ $t('uiAutomation.ai.remove') }}</el-button>
            </div>
            <div v-else-if="caseFile.error" class="case-upload-result case-upload-err">
              <el-icon><CircleClose /></el-icon>
              <span class="result-filename" :title="caseFile.name">{{ caseFile.name }}</span>
              <span class="err-msg">{{ caseFile.error }}</span>
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <span style="margin-right: 10px;">{{ $t('uiAutomation.ai.gifRecording') }}</span>
          <el-switch v-model="taskForm.enableGif" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">
            {{ $t('uiAutomation.ai.gifTip') }}
          </span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showTaskDialog = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
        <el-button
          type="primary"
          @click="handleRun"
          :loading="starting"
          :disabled="!canRun"
        >
          <el-icon><VideoPlay /></el-icon>
          {{ $t('uiAutomation.ai.startExecution') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="casePreviewVisible" :title="$t('uiAutomation.ai.casePreviewTitle')" width="640px" append-to-body>
      <div class="case-preview-meta">
        <span>{{ $t('uiAutomation.ai.caseFile') }}：{{ caseFile.name }}</span>
        <el-tag size="small" type="success">{{ $t('uiAutomation.ai.parsedCount') }} {{ caseFile.caseCount }}</el-tag>
      </div>
      <pre class="case-preview-text">{{ caseFile.text }}</pre>
    </el-dialog>

    <!-- 任务来源详情弹窗 -->
    <el-dialog
      v-model="taskSourceDetailVisible"
      :title="$t('uiAutomation.ai.executionRecords.taskSourceDetail')"
      width="640px"
      append-to-body
    >
      <template v-if="taskSourceDetail">
        <div class="task-source-meta">
          <el-tag size="small" :type="taskSourceDetail.task_source === 'file' ? 'warning' : 'info'">
            {{ getTaskSourceText(taskSourceDetail.task_source) }}
          </el-tag>
          <span v-if="taskSourceDetail.task_name" class="task-source-name">{{ taskSourceDetail.task_name }}</span>
        </div>
        <pre class="task-source-content">{{ taskSourceDetail.task_description || $t('uiAutomation.ai.executionRecords.noContent') }}</pre>
      </template>
      <template #footer>
        <el-button @click="taskSourceDetailVisible = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
        <el-button
          v-if="taskSourceDetail && taskSourceDetail.task_description"
          type="primary"
          @click="downloadTaskSource"
        >
          <el-icon>
            <Download v-if="taskSourceDetail.task_source === 'file'" />
            <CopyDocument v-else />
          </el-icon>
          {{ taskSourceDetail.task_source === 'file'
            ? $t('uiAutomation.ai.executionRecords.downloadDocument')
            : $t('uiAutomation.ai.executionRecords.downloadText') }}
        </el-button>
      </template>
    </el-dialog>

    <AIExecutionReport
      v-model="showReportDialog"
      :record-id="reportRecordId"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, VideoPlay, UploadFilled, Check, CircleClose, Loading, Download, CopyDocument } from '@element-plus/icons-vue'
import api from '@/utils/api'
import {
  getAIExecutionRecords,
  batchDeleteAIExecutionRecords,
  runAdhocAITask,
  uploadAIExplorationCaseFile
} from '@/api/ui_automation'
import AIExecutionReport from './AIExecutionReport.vue'

const { t } = useI18n()
const router = useRouter()
const records = ref([])
const loading = ref(false)
const total = ref(0)
const pagination = reactive({
  currentPage: 1,
  pageSize: 20
})

let pollTimer = null

const selectedRecords = ref([])
const isDeleting = ref(false)
const tableRef = ref(null)

const showReportDialog = ref(false)
const reportRecordId = ref(null)

// —— 新建测试 ——
const showTaskDialog = ref(false)
const starting = ref(false)
const taskForm = reactive({
  taskName: '',
  description: '',
  taskSource: 'text',
  enableGif: true
})
const caseUploadRef = ref(null)
const uploadingCases = ref(false)
const casePreviewVisible = ref(false)
const caseFile = ref({
  name: '',
  raw: null,
  parsed: false,
  error: '',
  caseCount: 0,
  text: '',
  cases: []
})

const canRun = computed(() => {
  if (!taskForm.taskName) return false
  if (taskForm.taskSource === 'file') {
    return caseFile.value.parsed && !!caseFile.value.text
  }
  return !!taskForm.description
})

function openTaskDialog() {
  taskForm.taskName = ''
  taskForm.description = ''
  taskForm.taskSource = 'text'
  taskForm.enableGif = true
  clearCaseFile()
  showTaskDialog.value = true
}

const ensureAIModelConfigured = async () => {
  try {
    const res = await api.get('/ui-automation/ai-models/')
    const configs = Array.isArray(res.data) ? res.data : []
    const hasActive = configs.some(c => c.is_active)
    if (hasActive) return true

    await ElMessageBox.confirm(
      t('uiAutomation.ai.messages.noModelConfigured'),
      t('uiAutomation.ai.tip'),
      {
        confirmButtonText: t('uiAutomation.ai.messages.goToConfig'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )
    router.push('/configuration/ai-mode')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('检查模型配置失败:', error)
      ElMessage.error(t('uiAutomation.ai.messages.checkModelFailed'))
    }
  }
  return false
}

const handleRun = async () => {
  const modelReady = await ensureAIModelConfigured()
  if (!modelReady) return

  starting.value = true
  const effectiveDescription = taskForm.taskSource === 'file'
    ? caseFile.value.text
    : taskForm.description

  try {
    const payload = {
      task_name: taskForm.taskName,
      task_source: taskForm.taskSource,
      task_description: effectiveDescription,
      execution_mode: 'text',
      enable_gif: taskForm.enableGif
    }
    if (taskForm.taskSource === 'file' && caseFile.value.cases?.length) {
      payload.parsed_cases = caseFile.value.cases
    }
    let response
    if (taskForm.taskSource === 'file' && caseFile.value.raw) {
      // 文件模式：以 multipart 上传原始 Excel，供后端保存并支持下载
      const fd = new FormData()
      Object.entries(payload).forEach(([k, v]) => {
        if (v !== undefined && v !== null) fd.append(k, typeof v === 'object' ? JSON.stringify(v) : v)
      })
      fd.append('source_file', caseFile.value.raw)
      response = await runAdhocAITask(fd, true)
    } else {
      response = await runAdhocAITask(payload)
    }
    const executionId = response.data.execution_id
    showTaskDialog.value = false
    ElMessage.success(t('uiAutomation.ai.messages.startSuccess'))
    router.push(`/ui-automation/ai-testing/${executionId}`)
  } catch (error) {
    console.error('执行失败:', error)
    ElMessage.error(t('uiAutomation.ai.messages.startFailed') + ': ' + (error.response?.data?.error || error.message))
  } finally {
    starting.value = false
  }
}

const handleCaseFileChange = async (uploadFile) => {
  const raw = uploadFile && uploadFile.raw
  if (!raw || uploadingCases.value) return

  if (caseFile.value.parsed) {
    caseFile.value = { name: '', raw: null, parsed: false, error: '', caseCount: 0, text: '', cases: [] }
  }

  uploadingCases.value = true
  caseFile.value = { name: raw.name, raw, parsed: false, error: '', caseCount: 0, text: '', cases: [] }

  try {
    const fd = new FormData()
    fd.append('file', raw)
    const res = await uploadAIExplorationCaseFile(fd)
    caseFile.value = {
      name: raw.name,
      raw,
      parsed: true,
      error: '',
      caseCount: res.data.case_count || 0,
      text: res.data.text || '',
      cases: res.data.cases || []
    }
    ElMessage.success(`${t('uiAutomation.ai.caseParsed')}${res.data.case_count || 0}${t('uiAutomation.ai.cases')}`)
  } catch (error) {
    const msg = error.response?.data?.error || error.message || '解析失败'
    caseFile.value = { name: raw.name, raw: null, parsed: false, error: msg, caseCount: 0, text: '', cases: [] }
    ElMessage.error(msg)
  } finally {
    uploadingCases.value = false
  }
}

const clearCaseFile = () => {
  caseFile.value = { name: '', raw: null, parsed: false, error: '', caseCount: 0, text: '', cases: [] }
  if (caseUploadRef.value?.clearFiles) caseUploadRef.value.clearFiles()
}

// —— 列表 ——
const loadRecords = async () => {
  loading.value = true
  try {
    const response = await getAIExecutionRecords({
      page: pagination.currentPage,
      page_size: pagination.pageSize
    })
    records.value = response.data.results || []
    total.value = response.data.count || 0
    if (tableRef.value) tableRef.value.clearSelection()
  } catch (error) {
    console.error('获取执行记录失败:', error)
    ElMessage.error(t('uiAutomation.ai.executionRecords.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

const handleSizeChange = () => {
  pagination.currentPage = 1
  loadRecords()
}

const handleCurrentChange = () => {
  loadRecords()
}

const viewDetail = (row) => {
  router.push(`/ui-automation/ai-testing/${row.id}`)
}

const viewReport = (row) => {
  reportRecordId.value = row.id
  showReportDialog.value = true
}

const getStatusTag = (status) => {
  const map = {
    pending: 'info',
    running: 'warning',
    passed: 'success',
    failed: 'danger',
    stopped: 'warning'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    pending: t('uiAutomation.status.pending'),
    running: t('uiAutomation.status.running'),
    passed: t('uiAutomation.status.success'),
    failed: t('uiAutomation.status.failed'),
    stopped: t('uiAutomation.status.stopped')
  }
  return map[status] || status
}

const getTaskSourceText = (source) => {
  const map = {
    text: t('uiAutomation.ai.taskSourceText'),
    file: t('uiAutomation.ai.taskSourceFile')
  }
  return map[source] || source || '-'
}

// —— 任务来源详情 ——
const taskSourceDetailVisible = ref(false)
const taskSourceDetail = ref(null)

const openTaskSourceDetail = (row) => {
  taskSourceDetail.value = row
  taskSourceDetailVisible.value = true
}

const downloadTaskSource = () => {
  const detail = taskSourceDetail.value
  if (!detail) return

  // 文件模式：下载原始上传的 Excel 文档
  if (detail.task_source === 'file') {
    if (detail.source_file_url) {
      const a = document.createElement('a')
      a.href = detail.source_file_url
      a.download = ''
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } else {
      ElMessage.warning(t('uiAutomation.ai.executionRecords.noSourceFile'))
    }
    return
  }

  // 文本模式：复制任务描述文本到剪贴板
  if (!detail.task_description) return
  const content = detail.task_description
  const copyToClipboard = (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text)
    }
    // 降级方案：兼容非安全上下文
    return new Promise((resolve, reject) => {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      try {
        document.execCommand('copy')
        resolve()
      } catch (e) {
        reject(e)
      } finally {
        document.body.removeChild(textarea)
      }
    })
  }
  copyToClipboard(content)
    .then(() => {
      ElMessage.success(t('uiAutomation.ai.executionRecords.copySuccess'))
    })
    .catch(() => {
      ElMessage.error(t('uiAutomation.ai.executionRecords.copyFailed'))
    })
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString()
}

const getSerialNumber = (index) => {
  return (pagination.currentPage - 1) * pagination.pageSize + index + 1
}

const handleSelectionChange = (selection) => {
  selectedRecords.value = selection
}

const batchDeleteRecords = async () => {
  if (selectedRecords.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      t('uiAutomation.ai.executionRecords.messages.batchDeleteConfirm', { count: selectedRecords.value.length }),
      t('uiAutomation.ai.executionRecords.messages.batchDeleteTitle'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    const ids = selectedRecords.value.map(item => item.id)
    await batchDeleteAIExecutionRecords(ids)
    ElMessage.success(t('uiAutomation.ai.executionRecords.messages.deleteSuccess'))

    if (records.value.length === ids.length && pagination.currentPage > 1) {
      pagination.currentPage--
    }
    loadRecords()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(t('uiAutomation.ai.executionRecords.messages.batchDeleteFailed'))
    }
  } finally {
    isDeleting.value = false
  }
}

const startPolling = () => {
  pollTimer = setInterval(() => {
    if (pagination.currentPage !== 1 || loading.value) return
    const hasActiveTasks = records.value.some(r => r.status === 'running' || r.status === 'pending')
    if (!hasActiveTasks) return

    getAIExecutionRecords({
      page: 1,
      page_size: pagination.pageSize
    }).then(response => {
      if (selectedRecords.value.length === 0) {
        records.value = response.data.results || []
        total.value = response.data.count || 0
      }
    }).catch(console.error)
  }, 5000)
}

onMounted(() => {
  loadRecords()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .page-title {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.card-container {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.case-upload-wrap {
  width: 100%;
}

.case-upload {
  width: 100%;

  :deep(.el-upload),
  :deep(.el-upload-dragger) { width: 100%; }

  :deep(.el-upload-dragger) {
    padding: 16px;
    border: 1px dashed #d9d9d9;
    transition: border-color 0.2s;

    &:hover { border-color: #409eff; }
  }
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #606266;

  .upload-icon { font-size: 26px; color: #409eff; }
  .upload-text { font-size: 13px; color: #303133; }
}

.case-upload-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  margin-top: 10px;
  color: #409eff;
  font-size: 13px;
}

.case-upload-result {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;

  .result-filename {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &.case-upload-ok { color: #67c23a; }
  &.case-upload-err {
    color: #f56c6c;
    .err-msg { color: #f56c6c; }
  }

  .preview-spacer {
    width: 4ch;
    flex-shrink: 0;
  }

  .preview-btn {
    box-shadow: none !important;
    padding: 0;
  }
}

.case-preview-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 14px;
}

.case-preview-text {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.6;
}

.task-source-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;

  .task-source-name {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }
}

.task-source-content {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.6;
}
</style>
