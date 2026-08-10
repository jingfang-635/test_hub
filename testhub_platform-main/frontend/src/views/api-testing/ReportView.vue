<template>
  <div class="report-view">
    <div class="header">
      <h3>{{ $t('apiTesting.report.title') }}</h3>
      <div class="actions">
        <el-button type="primary" @click="refreshReports">{{ $t('apiTesting.report.refreshReport') }}</el-button>
      </div>
    </div>

    <div class="content">
      <el-table :data="reports" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="test_suite_name" :label="$t('apiTesting.report.testSuite')" min-width="90" />
        <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="110">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_requests" :label="$t('apiTesting.report.totalRequests')" width="100" />
        <el-table-column prop="passed_requests" :label="$t('apiTesting.report.passedCount')" width="90">
          <template #default="scope">
            <span style="color: #67c23a">{{ scope.row.passed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed_requests" :label="$t('apiTesting.report.failedCount')" width="90">
          <template #default="scope">
            <span style="color: #f56c6c">{{ scope.row.failed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by.username" :label="$t('apiTesting.report.executor')" width="110" />
        <el-table-column prop="created_at" :label="$t('apiTesting.report.executionTime')" width="180" class-name="no-wrap-cell">
          <template #default="scope">
            <span class="datetime-text">{{ formatDate(scope.row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.common.operation')" width="320" fixed="right">
          <template #default="scope">
            <el-button link class="op-btn op-simple" @click="openSimpleReport(scope.row)">
              {{ $t('apiTesting.report.simpleReport') }}
            </el-button>
            <el-button link class="op-btn op-online" :loading="onlineLoadingId === scope.row.id" @click="openOnlineReport(scope.row)">
              {{ $t('apiTesting.report.onlineReport') }}
            </el-button>
            <el-button link class="op-btn op-download" :loading="downloadLoadingId === scope.row.id" @click="downloadOfflineReport(scope.row)">
              {{ $t('apiTesting.report.downloadOfflineReport') }}
            </el-button>
            <el-button link class="op-btn op-delete" @click="deleteReport(scope.row)">
              {{ $t('apiTesting.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 简易报告弹窗 -->
    <el-dialog
      v-model="showSimpleDialog"
      :title="$t('apiTesting.report.executionDetail')"
      width="900px"
      :close-on-click-modal="false"
      class="simple-report-dialog"
      destroy-on-close
    >
      <div v-if="currentReport" class="simple-report">
        <div class="report-hero">
          <div class="hero-top">
            <div class="hero-title">
              <el-icon class="hero-icon"><Document /></el-icon>
              <span>{{ currentReport.test_suite_name || '-' }}</span>
            </div>
            <el-tag class="hero-status" effect="dark" round>
              {{ getStatusText(currentReport.status) }}
            </el-tag>
          </div>
          <div class="hero-meta">
            <div class="meta-item">
              <div class="meta-label">{{ $t('apiTesting.report.belongProject') }}</div>
              <div class="meta-value">{{ currentReport.project_name || '-' }}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">{{ $t('apiTesting.report.executionEnvironment') }}</div>
              <div class="meta-value">{{ currentReport.environment_name || $t('apiTesting.report.noEnvironment') }}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">{{ $t('apiTesting.report.executor') }}</div>
              <div class="meta-value">{{ currentReport.executed_by?.username || '-' }}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">{{ $t('apiTesting.report.executionTime') }}</div>
              <div class="meta-value">{{ formatDate(currentReport.created_at) }}</div>
            </div>
          </div>
        </div>

        <div class="stat-cards">
          <div class="stat-card">
            <div class="stat-label">{{ $t('apiTesting.report.totalRequests') }}</div>
            <div class="stat-value total">{{ currentReport.total_requests || 0 }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ $t('apiTesting.report.passedCount') }}</div>
            <div class="stat-value passed">{{ currentReport.passed_requests || 0 }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ $t('apiTesting.report.failedCount') }}</div>
            <div class="stat-value failed">{{ currentReport.failed_requests || 0 }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ $t('apiTesting.report.skippedCount') }}</div>
            <div class="stat-value skipped">{{ skippedCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ $t('apiTesting.report.passRate') }}</div>
            <div class="stat-value passed">{{ passRate }}%</div>
          </div>
        </div>

        <div class="result-section">
          <h4>{{ $t('apiTesting.report.requestResults') }}</h4>
          <el-table :data="requestResults" border style="width: 100%">
            <el-table-column prop="name" :label="$t('apiTesting.report.requestName')" min-width="180" show-overflow-tooltip />
            <el-table-column prop="method" :label="$t('apiTesting.report.method')" width="90">
              <template #default="{ row }">
                <el-tag :type="getMethodType(row.method)" size="small">{{ row.method || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status_code" :label="$t('apiTesting.report.statusCode')" width="90" />
            <el-table-column prop="response_time" :label="$t('apiTesting.report.responseTime')" width="110">
              <template #default="{ row }">
                {{ formatResponseTime(row.response_time) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('apiTesting.report.result')" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.skipped" type="warning" size="small">{{ $t('apiTesting.report.resultSkipped') }}</el-tag>
                <el-tag v-else :type="row.passed ? 'success' : 'danger'" size="small">
                  {{ row.passed ? $t('apiTesting.report.resultPassed') : $t('apiTesting.report.resultFailed') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error" :label="$t('apiTesting.report.error')" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.error || '-' }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button @click="showSimpleDialog = false">{{ $t('apiTesting.common.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()
const reports = ref([])
const loading = ref(false)
const showSimpleDialog = ref(false)
const currentReport = ref(null)
const onlineLoadingId = ref(null)
const downloadLoadingId = ref(null)

const requestResults = computed(() => {
  const results = currentReport.value?.results
  return Array.isArray(results) ? results : []
})

const skippedCount = computed(() =>
  requestResults.value.filter(r => r.skipped).length
)

const passRate = computed(() => {
  const total = currentReport.value?.total_requests || 0
  if (!total) return 0
  const passed = currentReport.value?.passed_requests || 0
  return ((passed / total) * 100).toFixed(0)
})

const loadReports = async () => {
  loading.value = true
  try {
    const response = await api.get('/api-testing/test-executions/')
    reports.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadReports'))
  } finally {
    loading.value = false
  }
}

const refreshReports = async () => {
  await loadReports()
}

const openSimpleReport = async (report) => {
  try {
    const response = await api.get(`/api-testing/test-executions/${report.id}/`)
    currentReport.value = response.data
    showSimpleDialog.value = true
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadFailed'))
  }
}

const ensureAllureReportUrl = async (report) => {
  if (report.report_url) {
    return report.report_url.startsWith('http')
      ? report.report_url
      : `${window.location.origin}${report.report_url}`
  }
  const response = await api.post(`/api-testing/test-executions/${report.id}/generate-allure-report/`)
  const url = response.data.allure_report_url || response.data.report_url
  if (!url) throw new Error('report url missing')
  return url.startsWith('http') ? url : `${window.location.origin}${url}`
}

const openOnlineReport = async (report) => {
  onlineLoadingId.value = report.id
  try {
    const fullUrl = await ensureAllureReportUrl(report)
    window.open(fullUrl, '_blank')
    await loadReports()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.reportGenerateFailed'))
  } finally {
    onlineLoadingId.value = null
  }
}

const downloadOfflineReport = async (report) => {
  downloadLoadingId.value = report.id
  try {
    const response = await api.get(
      `/api-testing/test-executions/${report.id}/download-allure-report/`,
      { responseType: 'blob' }
    )

    const disposition = response.headers['content-disposition'] || ''
    let filename = `allure_report_${report.id}.html`
    const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)/i)
    if (match?.[1]) {
      filename = decodeURIComponent(match[1])
    }
    if (!filename.toLowerCase().endsWith('.html')) {
      filename = `${filename}.html`
    }

    const blob = new Blob([response.data], { type: 'text/html;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success(t('apiTesting.messages.success.reportDownloaded'))
    await loadReports()
  } catch (error) {
    let message = t('apiTesting.messages.error.reportDownloadFailed')
    const data = error?.response?.data
    if (data instanceof Blob) {
      try {
        const text = await data.text()
        const json = JSON.parse(text)
        if (json.error) message = json.error
      } catch (_) { /* ignore */ }
    } else if (data?.error) {
      message = data.error
    }
    ElMessage.error(message)
  } finally {
    downloadLoadingId.value = null
  }
}

const deleteReport = async (report) => {
  try {
    await ElMessageBox.confirm(
      t('apiTesting.report.confirmDelete'),
      t('apiTesting.common.tip'),
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )
    await api.delete(`/api-testing/test-executions/${report.id}/`)
    ElMessage.success(t('apiTesting.messages.success.delete'))
    await loadReports()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.deleteFailed'))
    }
  }
}

const getStatusType = (status) => {
  const typeMap = {
    PENDING: 'info',
    RUNNING: 'warning',
    COMPLETED: 'success',
    FAILED: 'danger',
    CANCELLED: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusKey = {
    PENDING: 'pending',
    RUNNING: 'running',
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELLED: 'cancelled'
  }[status]
  return statusKey ? t(`apiTesting.report.status.${statusKey}`) : status
}

const getMethodType = (method) => {
  const typeMap = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return typeMap[method] || 'info'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const formatResponseTime = (ms) => {
  if (ms == null || ms === '') return '-'
  return `${Math.round(Number(ms))}ms`
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.report-view {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.content {
  flex: 1;
  overflow: auto;
}

.datetime-text {
  white-space: nowrap;
  display: inline-block;
}

:deep(.no-wrap-cell .cell) {
  white-space: nowrap;
}

.op-btn {
  font-size: 12px !important;
  height: auto !important;
  padding: 0 4px !important;
  text-shadow: none !important;
  box-shadow: none !important;
  filter: none !important;
  background: transparent !important;
}

.op-btn:hover,
.op-btn:focus,
.op-btn:active {
  text-shadow: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

.op-simple,
.op-simple:hover,
.op-simple:focus {
  color: #67c23a !important;
}

.op-online,
.op-online:hover,
.op-online:focus {
  color: #9b59b6 !important;
}

.op-download,
.op-download:hover,
.op-download:focus {
  color: #e6a23c !important;
}

.op-delete,
.op-delete:hover,
.op-delete:focus {
  color: #f56c6c !important;
}

.simple-report {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-hero {
  background: linear-gradient(135deg, #4f7cff 0%, #6a5af9 55%, #8b5cf6 100%);
  border-radius: 12px;
  padding: 22px 24px;
  color: #fff;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
}

.hero-icon {
  font-size: 22px;
}

.hero-status {
  background: rgba(255, 255, 255, 0.22) !important;
  border: none !important;
  color: #fff !important;
}

.hero-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.meta-item {
  min-width: 0;
}

.meta-label {
  font-size: 12px;
  opacity: 0.85;
  margin-bottom: 4px;
}

.meta-value {
  font-size: 14px;
  font-weight: 500;
  word-break: break-all;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.stat-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 14px 12px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.stat-label {
  color: #909399;
  font-size: 13px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-value.total {
  color: #409eff;
}

.stat-value.passed {
  color: #67c23a;
}

.stat-value.failed {
  color: #f56c6c;
}

.stat-value.skipped {
  color: #e6a23c;
}

.result-section h4 {
  margin: 0 0 12px;
  color: #303133;
  font-size: 15px;
}

@media (max-width: 900px) {
  .hero-meta,
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
