<template>
  <div class="page-container request-performance-log-page">
    <div class="page-header">
      <h1 class="page-title">请求性能日志</h1>
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
        <el-button :icon="Refresh" :loading="loading" @click="fetchList">刷新列表</el-button>
      </div>
    </div>

    <div class="list-card">
      <div class="filter-bar">
        <el-form :inline="true" @submit.prevent>
          <el-form-item>
            <el-input
              v-model="filters.search"
              placeholder="请输入请求路径 / IP"
              clearable
              style="width: 220px"
              @keyup.enter="applyFilters"
              @change="applyFilters"
              @clear="applyFilters"
            />
          </el-form-item>
          <el-form-item>
            <el-select
              v-model="filters.method"
              placeholder="选择请求方法"
              clearable
              style="width: 180px"
              @change="applyFilters"
            >
              <el-option v-for="item in methodOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select
              v-model="filters.status_code"
              placeholder="选择状态码"
              clearable
              style="width: 160px"
              @change="applyFilters"
            >
              <el-option v-for="item in statusOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-date-picker
              v-model="filters.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              clearable
              style="width: 260px"
              @change="applyFilters"
            />
          </el-form-item>
          <el-form-item>
            <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        class="log-table"
        :data="logs"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="path" label="请求路径" min-width="260">
          <template #default="scope">
            <el-link type="primary" class="path-link" @click="openDetail(scope.row.id)">
              {{ scope.row.path || '-' }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="请求方法" width="120" align="center">
          <template #default="scope">
            <el-tag class="type-tag" type="info" effect="light">
              {{ scope.row.method || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="响应时间" width="140" align="center">
          <template #default="scope">
            <el-tag class="status-tag" :type="rtTagType(scope.row.response_time)" effect="light">
              {{ formatMs(scope.row.response_time) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态码" width="120" align="center">
          <template #default="scope">
            <el-tag class="status-tag" :type="statusTagType(scope.row.status_code)" effect="light">
              {{ scope.row.status_code ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用户" width="140" align="center">
          <template #default="scope">
            {{ scope.row.user_display || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180" align="center">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openDetail(scope.row.id)">详情</el-button>
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

    <!-- 日志详情弹窗（字段与内嵌 Admin 保持一致） -->
    <el-dialog
      v-model="detailVisible"
      title="日志详情"
      width="720px"
      destroy-on-close
      @closed="detail = null"
    >
      <div v-loading="detailLoading">
        <el-descriptions v-if="detail" :column="2" border>
          <el-descriptions-item label="请求路径" :span="2">
            <span class="mono-text">{{ detail.path || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="请求方法">
            <el-tag size="small" effect="plain" type="primary">{{ detail.method || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态码">
            <el-tag size="small" :type="statusTagType(detail.status_code)">
              {{ detail.status_code ?? '-' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            <el-tag size="small" :type="rtTagType(detail.response_time)">
              {{ formatMs(detail.response_time) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="用户">{{ detail.user_display || '-' }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ detail.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="User-Agent" :span="2">
            <span class="mono-text wrap">{{ detail.user_agent || '-' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button type="primary" @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Delete, Refresh, RefreshLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getRequestPerformanceLogs,
  getRequestPerformanceLogFilterOptions,
  getRequestPerformanceLogDetail,
  deleteRequestPerformanceLog
} from '@/api/core'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedRows = ref([])
const deleting = ref(false)

const methodOptions = ref([])
const statusOptions = ref([])

const filters = reactive({
  search: '',
  method: null,
  status_code: null,
  dateRange: null
})

function formatMs(value) {
  if (value === null || value === undefined || value === '') return '-'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return `${n.toFixed(2)}ms`
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

async function fetchFilterOptions() {
  try {
    const res = await getRequestPerformanceLogFilterOptions()
    const data = res?.data || res || {}
    methodOptions.value = data.methods || []
    statusOptions.value = data.status_codes || []
  } catch {
    // 候选值加载失败不阻塞列表展示
    methodOptions.value = []
    statusOptions.value = []
  }
}

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: (filters.search || '').trim() || undefined,
      method: filters.method || undefined,
      status_code: filters.status_code === null || filters.status_code === ''
        ? undefined
        : filters.status_code,
      start_date: filters.dateRange?.[0] || undefined,
      end_date: filters.dateRange?.[1] || undefined
    }
    const res = await getRequestPerformanceLogs(params)
    const data = res?.data || res || {}
    logs.value = data.results || (Array.isArray(data) ? data : [])
    total.value = data.count ?? logs.value.length
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载请求性能日志失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载请求性能日志失败')
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
  filters.method = null
  filters.status_code = null
  filters.dateRange = null
  currentPage.value = 1
  fetchList()
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

// ---------- 详情 ----------
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

async function openDetail(id) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const res = await getRequestPerformanceLogDetail(id)
    detail.value = res?.data || res
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载详情失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

// ---------- 删除 ----------
async function removeOne(row) {
  try {
    await ElMessageBox.confirm(`确定删除该条请求性能日志「${row.path || row.id}」吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await deleteRequestPerformanceLog(row.id)
    ElMessage.success('删除成功')
    if (logs.value.length === 1 && currentPage.value > 1) currentPage.value -= 1
    fetchList()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function batchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的日志')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRows.value.length} 条请求性能日志吗？`,
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
      await deleteRequestPerformanceLog(row.id)
      successCount += 1
    } catch {
      failCount += 1
    }
  }
  deleting.value = false
  if (successCount > 0 && failCount === 0) {
    ElMessage.success(`成功删除 ${successCount} 条请求性能日志`)
  } else if (successCount > 0) {
    ElMessage.warning(`删除完成：成功 ${successCount} 条，失败 ${failCount} 条`)
  } else {
    ElMessage.error('删除失败')
  }
  selectedRows.value = []
  fetchList()
}

onMounted(() => {
  fetchFilterOptions()
  fetchList()
})
</script>

<style scoped>
.request-performance-log-page {
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
.log-table {
  border-radius: 10px;
  overflow: hidden;
}

.log-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.log-table :deep(th.el-table__cell) {
  background-color: #eef2fa;
  color: #4a5568;
  font-weight: 600;
  border-bottom: 1px solid #e0e6f0;
}

.log-table :deep(.el-table__header th) {
  background-color: #eef2fa;
}

.log-table :deep(.el-table__row) {
  background-color: #ffffff;
}

.log-table :deep(.el-table__row:hover > td.el-table__cell) {
  background-color: #f5f8fd;
}

.log-table :deep(td.el-table__cell) {
  border-bottom: 1px solid #eef1f6;
}

.log-table :deep(.path-link) {
  font-weight: 500;
  word-break: break-all;
}

.log-table :deep(.el-button--primary.is-link) {
  box-shadow: none;
}

.log-table :deep(.type-tag),
.log-table :deep(.status-tag) {
  border-radius: 14px;
  padding: 0 12px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
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
