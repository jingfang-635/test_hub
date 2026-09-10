<template>
  <div class="run-case-container" v-loading="loading">
    <!-- 左侧：L1-L2-L3-用例 分组树 -->
    <div class="tree-panel">
      <div
        class="all-projects-node"
        :class="{ 'is-active': allCasesActive }"
        @click="showAllCases"
      >
        <span class="node-label">{{ $t('testcase.allCases') }}</span>
        <span class="node-count">{{ t('testcase.caseCount', { count: localCases.length }) }}</span>
      </div>
      <el-tree
        ref="treeRef"
        :data="treeData"
        node-key="id"
        :props="treeProps"
        :default-expand-all="false"
        :expand-on-click-node="true"
        highlight-current
        :empty-text="$t('testcase.noDataToExport')"
        @node-click="handleNodeClick"
      >
        <template #default="{ data }">
          <span class="tree-node">
            <span
              class="node-label"
              :class="{ 'case-node': data.isCase }"
            >
              {{ data.label }}
            </span>
            <span v-if="data.isCase" class="node-priority" :class="`priority-tag ${data.caseData.case_priority}`">
              {{ getPriorityText(data.caseData.case_priority) }}
            </span>
            <span v-else class="node-count">{{ t('testcase.caseCount', { count: data.count }) }}</span>
          </span>
        </template>
      </el-tree>
    </div>

    <!-- 右侧：用例列表 / 执行详情 -->
    <div class="detail-panel">
      <!-- 列表模式 -->
      <template v-if="viewMode === 'list'">
        <div class="list-header">
          <h2 class="list-title">{{ listTitle }}</h2>
          <span class="list-count">{{ t('testcase.caseCount', { count: filteredCases.length }) }}</span>
        </div>
        <div class="list-table-wrapper">
          <el-table
            :data="pagedCases"
            style="width: 100%"
            height="100%"
            @row-click="viewCaseDetail"
          >
            <el-table-column prop="testcase_id" :label="$t('testcase.caseNumber')" width="100" />
            <el-table-column prop="testcase" :label="$t('testcase.caseTitle')" min-width="220">
              <template #default="{ row }">
                <el-link type="primary" @click.stop="viewCaseDetail(row)">{{ row.testcase }}</el-link>
              </template>
            </el-table-column>
            <el-table-column :label="$t('execution.version')" width="120">
              <template #default="{ row }">
                <span v-if="row.versions && row.versions.length">
                  {{ row.versions.map(v => v.name).join('、') }}
                </span>
                <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="case_priority" :label="$t('testcase.priority')" width="90">
              <template #default="{ row }">
                <el-tag :class="`priority-tag ${row.case_priority}`">{{ getPriorityText(row.case_priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="test_type" :label="$t('testcase.testType')" width="110">
              <template #default="{ row }">{{ getTypeText(row.test_type) }}</template>
            </el-table-column>
            <el-table-column :label="$t('execution.comments')" min-width="200">
              <template #default="{ row }">
                <el-input
                  v-model="row.comments"
                  :placeholder="$t('execution.commentsPlaceholder')"
                  type="textarea"
                  :rows="1"
                  autosize
                  size="small"
                  @click.stop
                  @blur="updateCaseDetails(row)"
                />
              </template>
            </el-table-column>
            <el-table-column prop="l1" :label="$t('testcase.l1')" width="140">
              <template #default="{ row }">{{ row.l1 || '-' }}</template>
            </el-table-column>
            <el-table-column prop="l2" :label="$t('testcase.l2')" width="140">
              <template #default="{ row }">{{ row.l2 || '-' }}</template>
            </el-table-column>
            <el-table-column prop="l3" :label="$t('testcase.l3')" width="140">
              <template #default="{ row }">{{ row.l3 || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('execution.viewHistory')" width="120">
              <template #default="{ row }">
                <el-button size="small" type="primary" :icon="Clock" @click.stop="viewCaseHistory(row)">
                  {{ $t('execution.viewHistory') }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column :label="$t('execution.executionStatus')" prop="status" min-width="110" fixed="right">
              <template #default="{ row }">
                <el-select
                  v-model="row.status"
                  size="small"
                  :class="`status-select status-${row.status || 'untested'}`"
                  :style="{ color: getStatusColor(row.status) }"
                  @click.stop
                  @change="updateCaseStatus(row)"
                >
                  <el-option :label="$t('execution.untested')" value="untested" />
                  <el-option :label="$t('execution.passed')" value="passed" />
                  <el-option :label="$t('execution.failed')" value="failed" />
                  <el-option :label="$t('execution.blocked')" value="blocked" />
                  <el-option :label="$t('execution.retest')" value="retest" />
                  <el-option :label="$t('execution.na')" value="na" />
                </el-select>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredCases.length"
            layout="total, sizes, prev, pager, next, jumper"
            background
            small
          />
        </div>
      </template>

      <!-- 详情模式 -->
      <template v-else-if="viewMode === 'detail' && selectedCase">
        <div class="detail-header">
          <div class="detail-title-wrap">
            <el-button class="back-btn" :icon="ArrowLeft" circle size="small" @click="backToList" />
            <h2 class="detail-title">{{ selectedCase.testcase_id }}：{{ selectedCase.testcase }}</h2>
          </div>
          <div class="detail-actions">
            <el-button
              size="small"
              type="primary"
              :icon="Edit"
              @click="editCase"
            >{{ $t('common.edit') }}</el-button>
            <el-button
              size="small"
              type="primary"
              :icon="Clock"
              @click="viewCaseHistory(selectedCase)"
            >{{ $t('execution.viewHistory') }}</el-button>
          </div>
        </div>
        <div class="detail-body">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="$t('execution.executionStatus')">
              <el-select
                v-model="selectedCase.status"
                :class="`status-select status-${selectedCase.status || 'untested'}`"
                :style="{ color: getStatusColor(selectedCase.status) }"
                @change="updateCaseStatus(selectedCase)"
                size="default">
                <el-option :label="$t('execution.untested')" value="untested" />
                <el-option :label="$t('execution.passed')" value="passed" />
                <el-option :label="$t('execution.failed')" value="failed" />
                <el-option :label="$t('execution.blocked')" value="blocked" />
                <el-option :label="$t('execution.retest')" value="retest" />
                <el-option :label="$t('execution.na')" value="na" />
              </el-select>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.priority')">
              <el-tag :class="`priority-tag ${selectedCase.case_priority}`">
                {{ getPriorityText(selectedCase.case_priority) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.preconditions')" :span="2">
              <div class="html-content">{{ selectedCase.preconditions || $t('testcase.none') }}</div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.steps')" :span="2">
              <div class="html-content">{{ selectedCase.steps || $t('testcase.none') }}</div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.expectedResult')" :span="2">
              <div class="html-content">{{ selectedCase.expected_result || $t('testcase.none') }}</div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('execution.comments')" :span="2">
              <el-input
                v-model="selectedCase.comments"
                :placeholder="$t('execution.commentsPlaceholder')"
                type="textarea"
                :rows="3"
                @blur="updateCaseDetails(selectedCase)"
              />
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.testType')">
              {{ getTypeText(selectedCase.test_type) }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.relatedProject')">
              {{ selectedCase.project_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('execution.version')" :span="2">
              <span v-if="selectedCase.versions && selectedCase.versions.length">
                {{ selectedCase.versions.map(v => v.name).join('、') }}
              </span>
              <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l1')">
              {{ selectedCase.l1 || $t('testcase.ungrouped') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l2')">
              {{ selectedCase.l2 || $t('testcase.ungrouped') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l3')" :span="2">
              {{ selectedCase.l3 || $t('testcase.ungrouped') }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 上一条/下一条 切换测试计划分配的用例 -->
        <div class="detail-nav">
          <el-button :icon="ArrowLeft" :disabled="currentCaseIndex <= 0" @click="goToPrevCase">
            {{ $t('execution.prevCase') }}
          </el-button>
          <span class="nav-indicator">{{ currentCaseIndex + 1 }} / {{ localCases.length }}</span>
          <el-button :icon="ArrowRight" :disabled="currentCaseIndex >= localCases.length - 1" @click="goToNextCase">
            {{ $t('execution.nextCase') }}
          </el-button>
        </div>
      </template>

      <el-empty v-else :description="$t('testcase.selectCaseTip')" />
    </div>

    <!-- 历史记录对话框 -->
    <el-dialog
      :title="$t('execution.executionHistory')"
      v-model="historyDialogVisible"
      width="80%">
      <el-table :data="currentCaseHistory" style="width: 100%">
        <el-table-column prop="version" :label="$t('execution.version')" width="120" />
        <el-table-column prop="status" :label="$t('execution.status')" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comments" :label="$t('execution.comments')" show-overflow-tooltip />
        <el-table-column prop="executed_at" :label="$t('execution.executedAt')" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.executed_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Clock, Edit } from '@element-plus/icons-vue'
import axios from 'axios'

const props = defineProps({
  cases: { type: Array, default: () => [] },
  // 筛选条件由父组件（测试计划详情页）传入，筛选栏显示在进度条与用例列表之间
  filterCaseNumber: { type: String, default: '' },
  filterCaseTitle: { type: String, default: '' },
  filterPriority: { type: String, default: '' },
  filterStatus: { type: String, default: '' }
})
const emit = defineEmits(['changed'])

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const localCases = ref([])
const treeRef = ref(null)
const allCasesActive = ref(true)
const selectedCase = ref(null)
const viewMode = ref('list')
const listCases = ref([])
const listTitle = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const historyDialogVisible = ref(false)
const currentCaseHistory = ref([])

const filteredCases = computed(() => {
  return listCases.value.filter(c => {
    if (props.filterCaseNumber) {
      const num = String(c.testcase_id || '')
      if (!num.toLowerCase().includes(props.filterCaseNumber.toLowerCase())) return false
    }
    if (props.filterCaseTitle) {
      const title = String(c.testcase || '')
      if (!title.toLowerCase().includes(props.filterCaseTitle.toLowerCase())) return false
    }
    if (props.filterPriority && c.case_priority !== props.filterPriority) return false
    if (props.filterStatus && (c.status || 'untested') !== props.filterStatus) return false
    return true
  })
})

// 筛选条件变化时重置到第一页
watch([() => props.filterCaseNumber, () => props.filterCaseTitle, () => props.filterPriority, () => props.filterStatus], () => {
  currentPage.value = 1
})

watch(() => props.cases, (val) => {
  const newCases = val || []
  const wasDetail = viewMode.value === 'detail' && selectedCase.value
  const prevSelectedId = selectedCase.value ? selectedCase.value.id : null
  localCases.value = newCases
  if (newCases.length > 0) {
    allCasesActive.value = true
    treeRef.value && treeRef.value.setCurrentKey(null)
    listCases.value = [...newCases]
    listTitle.value = t('testcase.allCases')
    currentPage.value = 1
    if (wasDetail) {
      // 详情模式下自动暂存后保持停留在当前用例详情页
      const updated = newCases.find(c => c.id === prevSelectedId)
      selectedCase.value = updated || newCases[0]
      viewMode.value = 'detail'
    } else {
      viewMode.value = 'list'
      selectedCase.value = null
    }
  } else {
    listCases.value = []
    viewMode.value = 'list'
    selectedCase.value = null
  }
}, { immediate: true })

const treeProps = { label: 'label', children: 'children' }

const treeData = computed(() => {
  const root = {}
  localCases.value.forEach(c => {
    const l1 = (c.l1 || '').trim() || t('testcase.ungrouped')
    const l2 = (c.l2 || '').trim() || t('testcase.ungrouped')
    const l3 = (c.l3 || '').trim() || t('testcase.ungrouped')
    if (!root[l1]) root[l1] = {}
    if (!root[l1][l2]) root[l1][l2] = {}
    if (!root[l1][l2][l3]) root[l1][l2][l3] = []
    root[l1][l2][l3].push(c)
  })

  const tree = []
  Object.keys(root).sort().forEach(l1 => {
    const l1Node = { id: `l1/${l1}`, label: l1, level: 1, count: 0, children: [] }
    Object.keys(root[l1]).sort().forEach(l2 => {
      const l2Node = { id: `l1/${l1}/l2/${l2}`, label: l2, level: 2, count: 0, children: [] }
      Object.keys(root[l1][l2]).sort().forEach(l3 => {
        const cases = root[l1][l2][l3]
        const l3Node = {
          id: `l1/${l1}/l2/${l2}/l3/${l3}`,
          label: l3,
          level: 3,
          count: cases.length,
          children: cases.map(c => ({
            id: `case/${c.id}`,
            label: c.testcase,
            level: 4,
            isCase: true,
            caseData: c
          }))
        }
        l2Node.count += cases.length
        l2Node.children.push(l3Node)
      })
      l1Node.count += l2Node.count
      l1Node.children.push(l2Node)
    })
    tree.push(l1Node)
  })
  return tree
})

const collectCases = (node) => {
  if (!node) return []
  if (node.isCase) return [node.caseData]
  if (!node.children || node.children.length === 0) return []
  return node.children.reduce((acc, child) => acc.concat(collectCases(child)), [])
}

const handleNodeClick = (data) => {
  allCasesActive.value = false
  if (data.isCase) {
    selectedCase.value = data.caseData
    viewMode.value = 'detail'
  } else {
    listCases.value = collectCases(data)
    listTitle.value = data.label
    viewMode.value = 'list'
    selectedCase.value = null
    currentPage.value = 1
  }
}

const showAllCases = () => {
  allCasesActive.value = true
  treeRef.value && treeRef.value.setCurrentKey(null)
  listCases.value = [...localCases.value]
  listTitle.value = t('testcase.allCases')
  viewMode.value = 'list'
  selectedCase.value = null
  currentPage.value = 1
}

const viewCaseDetail = (row) => {
  selectedCase.value = row
  viewMode.value = 'detail'
}

const backToList = () => {
  viewMode.value = 'list'
  selectedCase.value = null
}

// 当前选中用例在测试计划分配用例列表中的索引（用于上一条/下一条切换）
const currentCaseIndex = computed(() => {
  if (!selectedCase.value) return -1
  return localCases.value.findIndex(c => c.id === selectedCase.value.id)
})

const goToPrevCase = () => {
  const idx = currentCaseIndex.value
  if (idx > 0) {
    selectedCase.value = localCases.value[idx - 1]
  }
}

const goToNextCase = () => {
  const idx = currentCaseIndex.value
  if (idx >= 0 && idx < localCases.value.length - 1) {
    selectedCase.value = localCases.value[idx + 1]
  }
}

const editCase = () => {
  if (!selectedCase.value) return
  router.push({ name: 'EditTestCase', params: { id: selectedCase.value.testcase_id } })
}

const pagedCases = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredCases.value.slice(start, start + pageSize.value)
})

const getPriorityText = (priority) => {
  const textMap = {
    P0: t('testcase.p0'),
    P1: t('testcase.p1'),
    P2: t('testcase.p2'),
    P3: t('testcase.p3')
  }
  return textMap[priority] || priority || '-'
}

const getTypeText = (type) => {
  const textMap = {
    functional: t('testcase.functional'),
    integration: t('testcase.integration'),
    api: t('testcase.api'),
    ui: t('testcase.ui'),
    performance: t('testcase.performance'),
    security: t('testcase.security')
  }
  return textMap[type] || type || '-'
}

const updateCaseStatus = async (runCase) => {
  try {
    await axios.patch(`/api/executions/run_cases/${runCase.id}/update_status/`, {
      status: runCase.status,
      comments: runCase.comments || ''
    })
    ElMessage.success(t('execution.statusUpdateSuccess'))
    emit('changed')
  } catch (error) {
    ElMessage.error(t('execution.statusUpdateFailed'))
  }
}

const updateCaseDetails = async (runCase) => {
  try {
    await axios.patch(`/api/executions/run_cases/${runCase.id}/update_status/`, {
      status: runCase.status,
      comments: runCase.comments || ''
    })
    ElMessage.success(t('execution.detailsUpdateSuccess'))
    emit('changed')
  } catch (error) {
    ElMessage.error(t('execution.detailsUpdateFailed'))
  }
}

const viewCaseHistory = async (runCase) => {
  try {
    const response = await axios.get(`/api/executions/run_cases/${runCase.id}/history/`)
    currentCaseHistory.value = response.data
    historyDialogVisible.value = true
  } catch (error) {
    ElMessage.error(t('execution.fetchHistoryFailed'))
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

const getStatusType = (status) => {
  const map = { untested: 'info', passed: 'success', failed: 'danger', blocked: 'warning', retest: 'primary', na: 'info' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    untested: t('execution.untested'),
    passed: t('execution.passed'),
    failed: t('execution.failed'),
    blocked: t('execution.blocked'),
    retest: t('execution.retest'),
    na: t('execution.na')
  }
  return map[status] || status
}

// 执行状态文字颜色：通过绿 / 失败橙 / 阻塞红 / 重测蓝 / NA 紫，未测试不设颜色
const getStatusColor = (status) => {
  switch (status) {
    case 'passed':  return 'var(--el-color-success)'
    case 'failed':  return 'var(--el-color-warning)'
    case 'blocked': return 'var(--el-color-danger)'
    case 'retest':  return '#409eff'
    case 'na':      return '#8e44ad'
    default:        return ''
  }
}
</script>

<style lang="scss" scoped>
.run-case-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 0;
  gap: 16px;
}

.tree-panel {
  width: 360px;
  flex-shrink: 0;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px;

  :deep(.el-tree-node__content) {
    height: 32px;
    min-width: 0;
  }

  :deep(.el-tree) {
    overflow: hidden;
  }

  :deep(.el-tree-node.is-current > .el-tree-node__content) {
    background-color: #ecf5ff;
    color: #409eff;
    font-weight: 600;
  }
}

.all-projects-node {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;

  &:hover {
    background-color: #f5f7fa;
  }

  &.is-active {
    background-color: #ecf5ff;
    color: #409eff;
    font-weight: 600;
  }

  .node-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-count {
    color: #909399;
    font-size: 12px;
  }
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  width: 100%;

  .node-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .case-node {
    color: #409eff;
    cursor: pointer;
  }

  .node-count {
    color: #909399;
    font-size: 12px;
    flex-shrink: 0;
    white-space: nowrap;
  }

  .node-priority {
    font-size: 12px;
    flex-shrink: 0;
    white-space: nowrap;
  }
}

.priority-tag {
  &.P0 { color: #f56c6c; font-weight: bold; }
  &.P1 { color: #f56c6c; }
  &.P2 { color: #e6a23c; }
  &.P3 { color: #67c23a; }
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.critical { color: #f56c6c; font-weight: bold; }
}

.detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 16px;
  background: #fafafa;
}

.list-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-shrink: 0;

  .list-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
  }

  .list-count {
    color: #909399;
    font-size: 13px;
  }
}

.list-table-wrapper {
  flex: 1;
  overflow: hidden;

  :deep(.el-table) {
    height: 100% !important;
  }

  // 表头排序箭头与标题不换行，保持同一行显示
  :deep(.el-table__header-wrapper th .cell) {
    white-space: nowrap;
  }
}

// 执行状态下拉框文本颜色：通过绿 / 失败橙 / 阻塞红 / 重测蓝 / NA 紫，未测试保持默认
.status-select {
  --status-color: var(--el-text-color-regular);
  color: var(--status-color);

  :deep(.el-select__wrapper) {
    color: var(--status-color);
  }
  :deep(.el-select__selected-item),
  :deep(.el-select__placeholder),
  :deep(.el-select__tags-text) {
    color: var(--status-color) !important;
  }

  &.status-passed {
    --status-color: var(--el-color-success);
  }
  &.status-failed {
    --status-color: var(--el-color-warning);
  }
  &.status-blocked {
    --status-color: var(--el-color-danger);
  }
  &.status-retest {
    --status-color: #409eff;
  }
  &.status-na {
    --status-color: #8e44ad;
  }
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 12px;
  flex-shrink: 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.detail-title-wrap {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.back-btn { flex-shrink: 0; }

.detail-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  word-break: break-all;
}

.detail-actions { flex-shrink: 0; }

.detail-body {
  flex: 1;
  overflow: auto;

  :deep(.el-descriptions__label) {
    width: 160px;
    min-width: 160px;
  }

  :deep(.el-descriptions) {
    background: #fff;
  }
}

.html-content {
  white-space: pre-wrap;
  line-height: 1.6;
  word-break: break-all;
}

.no-version {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

.detail-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
  flex-shrink: 0;

  .nav-indicator {
    color: #606266;
    font-size: 13px;
  }
}
</style>
