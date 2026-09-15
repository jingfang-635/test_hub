<template>
  <div class="page-container performance-stats-page">
    <div class="page-header">
      <h1 class="page-title">性能统计</h1>
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
            <el-date-picker
              v-model="filters.date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              clearable
              style="width: 200px"
              @change="applyFilters"
            />
          </el-form-item>
          <el-form-item>
            <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        class="stats-table"
        :data="statsList"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column label="日期" min-width="180">
          <template #default="scope">
            <el-link type="primary" class="date-link" @click="openDetail(scope.row.id)">
              {{ scope.row.date || '-' }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="总请求数" width="140" align="center">
          <template #default="scope">
            <span class="num-success">{{ scope.row.total_requests ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="平均响应时间" width="160" align="center">
          <template #default="scope">
            <el-tag class="status-tag" :type="rtTagType(scope.row.avg_response_time)" effect="light">
              {{ formatMs(scope.row.avg_response_time) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误率" width="140" align="center">
          <template #default="scope">
            <span class="rate-cell">
              <i class="rate-dot" :style="{ background: errorRateColor(scope.row) }" />
              {{ errorRateText(scope.row) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="慢请求率" width="140" align="center">
          <template #default="scope">
            <span class="rate-cell">
              <i class="rate-dot" :style="{ background: slowRateColor(scope.row) }" />
              {{ slowRateText(scope.row) }}
            </span>
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

    <!-- 性能统计详情弹窗（字段与内嵌 Admin 保持一致） -->
    <el-dialog
      v-model="detailVisible"
      title="性能统计详情"
      width="640px"
      destroy-on-close
      @closed="detail = null"
    >
      <div v-loading="detailLoading">
        <el-descriptions v-if="detail" :column="2" border>
          <el-descriptions-item label="日期">{{ detail.date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="总请求数">{{ detail.total_requests ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="平均响应时间">
            {{ formatMs(detail.avg_response_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="最大响应时间">
            {{ formatMs(detail.max_response_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="最小响应时间">
            {{ formatMs(detail.min_response_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="错误请求数">{{ detail.error_count ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="慢请求数(>1s)">{{ detail.slow_requests ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误率">{{ formatRate(detail.error_rate) }}</el-descriptions-item>
          <el-descriptions-item label="慢请求率">{{ formatRate(detail.slow_rate) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">
            {{ formatDateTime(detail.updated_at) }}
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
  getPerformanceStatisticsList,
  getPerformanceStatisticsDetail,
  deletePerformanceStatistics
} from '@/api/core'

const loading = ref(false)
const statsList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedRows = ref([])
const deleting = ref(false)

const filters = reactive({
  date: null
})

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

function rtTagType(ms) {
  const n = Number(ms)
  if (n > 1000) return 'danger'
  if (n > 500) return 'warning'
  return 'success'
}

/** 错误率 = 错误请求数 / 总请求数，颜色阈值与 Admin 一致：>5% 红，>1% 橙，其余绿 */
function errorRateValue(row) {
  const totalCount = intOrZero(row.total_requests)
  if (totalCount === 0) return null
  return (intOrZero(row.error_count) / totalCount) * 100
}

/** 慢请求率 = 慢请求数 / 总请求数，颜色阈值与 Admin 一致：>10% 红，>5% 橙，其余绿 */
function slowRateValue(row) {
  const totalCount = intOrZero(row.total_requests)
  if (totalCount === 0) return null
  return (intOrZero(row.slow_requests) / totalCount) * 100
}

function intOrZero(value) {
  const n = Number(value)
  return Number.isNaN(n) ? 0 : n
}

function errorRateColor(row) {
  const rate = errorRateValue(row)
  if (rate === null) return '#c0c4cc'
  if (rate > 5) return '#f56c6c'
  if (rate > 1) return '#e6a23c'
  return '#67c23a'
}

function slowRateColor(row) {
  const rate = slowRateValue(row)
  if (rate === null) return '#c0c4cc'
  if (rate > 10) return '#f56c6c'
  if (rate > 5) return '#e6a23c'
  return '#67c23a'
}

function errorRateText(row) {
  const rate = errorRateValue(row)
  return rate === null ? '0%' : `${rate.toFixed(2)}%`
}

function slowRateText(row) {
  const rate = slowRateValue(row)
  return rate === null ? '0%' : `${rate.toFixed(2)}%`
}

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      date: filters.date || undefined
    }
    const res = await getPerformanceStatisticsList(params)
    const data = res?.data || res || {}
    statsList.value = data.results || (Array.isArray(data) ? data : [])
    total.value = data.count ?? statsList.value.length
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '加载性能统计失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载性能统计失败')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  currentPage.value = 1
  fetchList()
}

function resetFilters() {
  filters.date = null
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
    const res = await getPerformanceStatisticsDetail(id)
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
    await ElMessageBox.confirm(`确定删除「${row.date}」的性能统计吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await deletePerformanceStatistics(row.id)
    ElMessage.success('删除成功')
    if (statsList.value.length === 1 && currentPage.value > 1) currentPage.value -= 1
    fetchList()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function batchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的统计记录')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRows.value.length} 条性能统计吗？`,
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
      await deletePerformanceStatistics(row.id)
      successCount += 1
    } catch {
      failCount += 1
    }
  }
  deleting.value = false
  if (successCount > 0 && failCount === 0) {
    ElMessage.success(`成功删除 ${successCount} 条性能统计`)
  } else if (successCount > 0) {
    ElMessage.warning(`删除完成：成功 ${successCount} 条，失败 ${failCount} 条`)
  } else {
    ElMessage.error('删除失败')
  }
  selectedRows.value = []
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.performance-stats-page {
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
.stats-table {
  border-radius: 10px;
  overflow: hidden;
}

.stats-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.stats-table :deep(th.el-table__cell) {
  background-color: #eef2fa;
  color: #4a5568;
  font-weight: 600;
  border-bottom: 1px solid #e0e6f0;
}

.stats-table :deep(.el-table__header th) {
  background-color: #eef2fa;
}

.stats-table :deep(.el-table__row) {
  background-color: #ffffff;
}

.stats-table :deep(.el-table__row:hover > td.el-table__cell) {
  background-color: #f5f8fd;
}

.stats-table :deep(td.el-table__cell) {
  border-bottom: 1px solid #eef1f6;
}

.stats-table :deep(.date-link) {
  font-weight: 500;
}

.stats-table :deep(.el-button--primary.is-link) {
  box-shadow: none;
}

.stats-table :deep(.status-tag) {
  border-radius: 14px;
  padding: 0 12px;
}

.num-success {
  color: #67c23a;
  font-weight: 600;
}

/* 比率：圆点 + 文本（对齐 Admin 的 _rate_dot 展示） */
.rate-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--th-text-primary);
}

.rate-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
