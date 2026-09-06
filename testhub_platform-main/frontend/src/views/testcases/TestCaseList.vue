<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('testcase.title') }}</h1>
      <div class="header-actions">
        <el-button type="success" @click="exportToExcel">
          <el-icon><Download /></el-icon>
          {{ $t('testcase.exportExcel') }}
        </el-button>
        <el-button type="warning" @click="triggerImport" :loading="importing">
          <el-icon><Upload /></el-icon>
          {{ $t('testcase.importExcel') }}
        </el-button>
        <input
          ref="importInputRef"
          type="file"
          accept=".xlsx,.xls"
          style="display: none"
          @change="handleImportFile"
        />
        <el-button type="primary" @click="$router.push('/ai-generation/testcases/create')">
          <el-icon><Plus /></el-icon>
          {{ $t('testcase.newCase') }}
        </el-button>
      </div>
    </div>

    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="5">
            <el-input
              v-model="searchText"
              :placeholder="$t('testcase.searchPlaceholder')"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="projectFilter" :placeholder="$t('testcase.relatedProject')" clearable @change="handleFilter">
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="priorityFilter" :placeholder="$t('testcase.priorityFilter')" clearable @change="handleFilter">
              <el-option :label="$t('testcase.p0')" value="P0" />
              <el-option :label="$t('testcase.p1')" value="P1" />
              <el-option :label="$t('testcase.p2')" value="P2" />
              <el-option :label="$t('testcase.p3')" value="P3" />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="caseTypeFilter" :placeholder="$t('testcase.caseTypeFilter')" clearable @change="handleFilter">
              <el-option :label="$t('testcase.caseTypeManual')" value="manual" />
              <el-option :label="$t('testcase.caseTypeUi')" value="ui" />
              <el-option :label="$t('testcase.caseTypeApi')" value="api" />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-button @click="resetFilters">{{ $t('common.reset') }}</el-button>
          </el-col>
        </el-row>
      </div>

      <div class="tree-detail-container" v-loading="loading">
        <!-- 左侧：L1-L2-L3-用例标题 树 -->
        <div class="tree-panel">
          <div
            class="all-projects-node"
            :class="{ 'is-active': allProjectsActive }"
            @click="showAllCases"
          >
            <span class="node-label">{{ $t('testcase.allProjects') }}</span>
            <span class="node-count">{{ t('testcase.caseCount', { count: allTestcases.length }) }}</span>
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
                <span v-if="data.isCase" class="node-priority" :class="`priority-tag ${data.case.priority}`">
                  {{ getPriorityText(data.case.priority) }}
                </span>
                <span v-else class="node-count">{{ t('testcase.caseCount', { count: data.count }) }}</span>
              </span>
            </template>
          </el-tree>
        </div>

        <!-- 右侧：用例列表 / 详情 -->
        <div class="detail-panel">
          <!-- 列表模式：默认展示全部用例，或点击某层后展示该层下符合条件的用例 -->
          <template v-if="viewMode === 'list'">
            <div class="list-header">
              <h2 class="list-title">{{ listTitle }}</h2>
              <span class="list-count">{{ t('testcase.caseCount', { count: listCases.length }) }}</span>
            </div>
            <div class="list-table-wrapper">
              <el-table
                :data="pagedCases"
                style="width: 100%"
                height="100%"
                @row-click="viewCaseDetail"
                @selection-change="handleSelectionChange"
              >
                <el-table-column type="selection" width="45" />
                <el-table-column prop="id" :label="$t('testcase.caseNumber')" width="100" />
                <el-table-column prop="title" :label="$t('testcase.caseTitle')" min-width="220">
                  <template #default="{ row }">
                    <el-link type="primary" @click.stop="viewCaseDetail(row)">{{ row.title }}</el-link>
                  </template>
                </el-table-column>
                <el-table-column prop="priority" :label="$t('testcase.priority')" width="90">
                  <template #default="{ row }">
                    <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="test_type" :label="$t('testcase.testType')" width="110">
                  <template #default="{ row }">{{ getTypeText(row.test_type) }}</template>
                </el-table-column>
                <el-table-column prop="case_type" :label="$t('testcase.caseType')" width="90">
                  <template #default="{ row }">{{ getCaseTypeText(row.case_type) }}</template>
                </el-table-column>
                <el-table-column prop="project.name" :label="$t('testcase.relatedProject')" width="140">
                  <template #default="{ row }">{{ row.project?.name || '-' }}</template>
                </el-table-column>
                <el-table-column prop="l1" :label="$t('testcase.l1')" width="120">
                  <template #default="{ row }">{{ row.l1 || '-' }}</template>
                </el-table-column>
                <el-table-column prop="l2" :label="$t('testcase.l2')" width="120">
                  <template #default="{ row }">{{ row.l2 || '-' }}</template>
                </el-table-column>
                <el-table-column prop="l3" :label="$t('testcase.l3')" width="120">
                  <template #default="{ row }">{{ row.l3 || '-' }}</template>
                </el-table-column>
                <el-table-column :label="$t('project.actions')" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" @click.stop="editTestCase(row)">{{ $t('common.edit') }}</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="pagination-wrapper">
              <span class="selection-tip" v-if="selectedRows.length > 0">
                {{ t('testcase.selectedCount', { count: selectedRows.length }) }}
              </span>
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="listCases.length"
                layout="total, sizes, prev, pager, next, jumper"
                background
                small
              />
            </div>
          </template>

          <!-- 详情模式：点击单个用例后展示 -->
          <template v-else-if="viewMode === 'detail' && selectedCase">
            <div class="detail-header">
              <div class="detail-title-wrap">
                <el-button class="back-btn" :icon="ArrowLeft" circle size="small" @click="backToList" />
                <h2 class="detail-title">{{ selectedCase.id }}：{{ selectedCase.title }}</h2>
              </div>
              <div class="detail-actions">
                <el-button size="small" @click="editTestCase(selectedCase)">{{ $t('common.edit') }}</el-button>
                <el-button size="small" type="danger" @click="deleteTestCase(selectedCase)">{{ $t('common.delete') }}</el-button>
              </div>
            </div>
            <div class="detail-body">
              <el-tabs v-model="detailActiveTab">
                <el-tab-pane :label="$t('testcase.tabBasic')" name="basic">
                  <el-descriptions :column="2" border size="small">
                    <el-descriptions-item :label="$t('testcase.preconditions')" :span="2">
                      <div class="html-content" v-html="selectedCase.preconditions || $t('testcase.none')"></div>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.steps')" :span="2">
                      <div class="html-content" v-html="selectedCase.steps || $t('testcase.none')"></div>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.expectedResult')" :span="2">
                      <div class="html-content" v-html="selectedCase.expected_result || $t('testcase.none')"></div>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.caseRemark')" :span="2">{{ selectedCase.description || $t('testcase.noDescription') }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.priority')" :span="2">
                      <el-tag :class="`priority-tag ${selectedCase.priority}`">{{ getPriorityText(selectedCase.priority) }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.testType')" :span="2">{{ getTypeText(selectedCase.test_type) }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.caseType')" :span="2">{{ getCaseTypeText(selectedCase.case_type) }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.relatedProject')" :span="2">{{ selectedCase.project?.name || $t('testcase.noProject') }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.relatedVersions')" :span="2">
                      <span v-if="selectedCase.versions && selectedCase.versions.length">
                        {{ selectedCase.versions.map(v => v.name).join('、') }}
                      </span>
                      <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.l1')" :span="2">{{ selectedCase.l1 || $t('testcase.none') }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.l2')" :span="2">{{ selectedCase.l2 || $t('testcase.none') }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.l3')" :span="2">{{ selectedCase.l3 || $t('testcase.none') }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('testcase.createdAt')" :span="2">{{ formatDate(selectedCase.created_at) }}</el-descriptions-item>
                  </el-descriptions>
                </el-tab-pane>
                <el-tab-pane :label="$t('testcase.tabUi')" name="ui">
                  <div class="tab-actions">
                    <el-button type="primary" @click="editTestCase(selectedCase)">{{ $t('testcase.goEdit') }}</el-button>
                    <el-button @click="handleAiGenerateSteps('ui')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
                  </div>
                  <el-empty :description="$t('testcase.tabEmpty')" />
                </el-tab-pane>
                <el-tab-pane :label="$t('testcase.tabApi')" name="api">
                  <div class="tab-actions">
                    <el-button type="primary" @click="editTestCase(selectedCase)">{{ $t('testcase.goEdit') }}</el-button>
                    <el-button @click="handleAiGenerateSteps('api')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
                  </div>
                  <el-empty :description="$t('testcase.tabEmpty')" />
                </el-tab-pane>
              </el-tabs>
            </div>
          </template>

          <el-empty v-else :description="$t('testcase.selectCaseTip')" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Download, Upload, ArrowLeft } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import * as XLSX from 'xlsx'

const { t } = useI18n()
const router = useRouter()
const loading = ref(false)
const allTestcases = ref([])
const projects = ref([])
const searchText = ref('')
const projectFilter = ref('')
const priorityFilter = ref('')
const caseTypeFilter = ref('')
const selectedCase = ref(null)
const detailActiveTab = ref('basic')
// 右侧视图：'list' 列表 | 'detail' 单条详情
const viewMode = ref('list')
const listCases = ref([])
const listTitle = ref('')
const importing = ref(false)
const importInputRef = ref(null)
const treeRef = ref(null)
// "全部项目"是否处于选中状态
const allProjectsActive = ref(true)
// 列表勾选的用例(用于导出)
const selectedRows = ref([])
// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 当前页数据(前端分页)
const pagedCases = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return listCases.value.slice(start, start + pageSize.value)
})

// 勾选变化
const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const treeProps = { label: 'label', children: 'children' }

// 抓取全部用例（分页循环），用于构建树
const fetchTestCases = async () => {
  loading.value = true
  try {
    const pageSize = 100 // 后端允许的最大值
    let page = 1
    let hasMore = true
    let allData = []

    while (hasMore) {
      const response = await api.get('/testcases/', {
        params: {
          page,
          page_size: pageSize,
          search: searchText.value,
          project: projectFilter.value,
          priority: priorityFilter.value,
          case_type: caseTypeFilter.value,
        }
      })
      const results = response.data.results || []
      allData.push(...results)
      if (results.length < pageSize) {
        hasMore = false
      } else {
        page++
      }
    }

    allTestcases.value = allData
    // 默认展示全部用例
    listCases.value = allData
    listTitle.value = t('testcase.allCases')
    viewMode.value = 'list'
    selectedCase.value = null
    // 重置分页与勾选
    currentPage.value = 1
    selectedRows.value = []
    // 搜索/筛选后默认回到"全部项目"视图
    allProjectsActive.value = true
    // 取消树节点高亮
    treeRef.value && treeRef.value.setCurrentKey(null)
  } catch (error) {
    ElMessage.error(t('testcase.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

// 根据 l1/l2/l3 构建树
const treeData = computed(() => {
  const root = {} // l1 -> { l2 -> { l3 -> [cases] } }
  allTestcases.value.forEach(c => {
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
            label: c.title,
            level: 4,
            isCase: true,
            case: c
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

const handleSearch = () => {
  fetchTestCases()
}

const handleFilter = () => {
  fetchTestCases()
}

// 一键重置筛选条件，并回到「全部项目」列表
const resetFilters = () => {
  showAllCases()
}

// 递归收集某节点下所有用例叶节点
const collectCases = (node) => {
  if (!node) return []
  if (node.isCase) return [node.case]
  if (!node.children || node.children.length === 0) return []
  return node.children.reduce((acc, child) => acc.concat(collectCases(child)), [])
}

// 点击树节点：用例叶节点 -> 右侧展示详情；分组节点 -> 右侧展示该层下符合条件的用例列表
const handleNodeClick = (data) => {
  // 点击树节点时取消"全部项目"高亮
  allProjectsActive.value = false
  if (data.isCase) {
    selectedCase.value = data.case
    detailActiveTab.value = 'basic'
    viewMode.value = 'detail'
  } else {
    listCases.value = collectCases(data)
    listTitle.value = data.label
    viewMode.value = 'list'
    selectedCase.value = null
    // 切换列表数据源时重置分页与勾选
    currentPage.value = 1
    selectedRows.value = []
  }
}

// 点击"全部项目"：取消所有筛选并显示全部用例
const showAllCases = () => {
  searchText.value = ''
  projectFilter.value = ''
  priorityFilter.value = ''
  allProjectsActive.value = true
  caseTypeFilter.value = ''
  // 取消树节点高亮
  treeRef.value && treeRef.value.setCurrentKey(null)
  fetchTestCases()
}

// 从列表点击某条用例 -> 进入详情
const viewCaseDetail = (row) => {
  selectedCase.value = row
  detailActiveTab.value = 'basic'
  viewMode.value = 'detail'
}

// 返回列表
const backToList = () => {
  viewMode.value = 'list'
  selectedCase.value = null
}

const editTestCase = (testcase) => {
  router.push(`/ai-generation/testcases/${testcase.id}/edit`)
}

const handleAiGenerateSteps = () => {
  ElMessage.info(t('testcase.aiGenerateStepsTodo'))
}

const deleteTestCase = async (testcase) => {
  try {
    await ElMessageBox.confirm(t('testcase.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })

    await api.delete(`/testcases/${testcase.id}/`)
    ElMessage.success(t('testcase.deleteSuccess'))
    if (selectedCase.value && selectedCase.value.id === testcase.id) {
      selectedCase.value = null
    }
    fetchTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('testcase.deleteFailed'))
    }
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    P0: t('testcase.p0'),
    P1: t('testcase.p1'),
    P2: t('testcase.p2'),
    P3: t('testcase.p3')
  }
  return textMap[priority] || priority
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
  return textMap[type] || '-'
}

const getCaseTypeText = (type) => {
  const textMap = {
    manual: t('testcase.caseTypeManual'),
    ui: t('testcase.caseTypeUi'),
    api: t('testcase.caseTypeApi')
  }
  return textMap[type] || '-'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 将HTML的<br>标签转换为换行符（用于Excel导出）
const convertBrToNewline = (text) => {
  if (!text) return ''
  return text.replace(/<br\s*\/?>/gi, '\n')
}

const exportToExcel = async () => {
  try {
    loading.value = true

    // 优先导出勾选的用例,否则导出当前列表全部用例
    const testCasesToExport = selectedRows.value.length > 0 ? selectedRows.value : listCases.value

    if (testCasesToExport.length === 0) {
      ElMessage.warning(t('testcase.noDataToExport'))
      loading.value = false
      return
    }

    const workbook = XLSX.utils.book_new()
    const worksheetData = [
      [t('testcase.excelNumber'), t('testcase.excelTitle'), t('testcase.excelPreconditions'), t('testcase.excelSteps'), t('testcase.excelExpectedResult'), t('testcase.excelRemark'), t('testcase.excelPriority'), t('testcase.excelTestType'), t('testcase.excelCaseType'), t('testcase.excelProject'), t('testcase.excelVersions'), t('testcase.l1'), t('testcase.l2'), t('testcase.l3')]
    ]

    testCasesToExport.forEach((testcase) => {
      const versions = testcase.versions && testcase.versions.length > 0
        ? testcase.versions.map(v => v.name + (v.is_baseline ? '(' + t('testcase.baseline') + ')' : '')).join('、')
        : t('testcase.noVersion')

      worksheetData.push([
        testcase.id,
        testcase.title || '',
        convertBrToNewline(testcase.preconditions || ''),
        convertBrToNewline(testcase.steps || ''),
        convertBrToNewline(testcase.expected_result || ''),
        testcase.description || '',
        getPriorityText(testcase.priority),
        getTypeText(testcase.test_type),
        getCaseTypeText(testcase.case_type),
        testcase.project?.name || '',
        versions,
        testcase.l1 || '',
        testcase.l2 || '',
        testcase.l3 || ''
      ])
    })

    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)
    worksheet['!cols'] = [
      { wch: 12 }, { wch: 30 }, { wch: 30 }, { wch: 40 }, { wch: 30 }, { wch: 20 },
      { wch: 10 }, { wch: 15 }, { wch: 10 }, { wch: 20 }, { wch: 25 }, { wch: 15 }, { wch: 15 }, { wch: 15 }
    ]

    XLSX.utils.book_append_sheet(workbook, worksheet, t('testcase.excelSheetName'))
    const fileName = t('testcase.excelFileName', { date: new Date().toISOString().slice(0, 10) })
    XLSX.writeFile(workbook, fileName)

    ElMessage.success(t('testcase.exportSuccess'))
  } catch (error) {
    console.error('Export test cases failed:', error)
    ElMessage.error(t('testcase.exportFailed') + ': ' + (error.message || t('common.error')))
  } finally {
    loading.value = false
  }
}

// ===== Excel 导入 =====
const HEADER_FIELD_MAP = {
  '测试用例编号': 'case_number', '用例编号': 'case_number', 'Test Case ID': 'case_number', 'Case ID': 'case_number',
  '用例标题': 'title', '标题': 'title', 'Case Title': 'title',
  '用例描述': 'description', '描述': 'description', '备注': 'description', 'Remark': 'description', 'Case Description': 'description',
  '归属项目': 'project_name', '关联项目': 'project_name', '项目': 'project_name', 'Related Project': 'project_name',
  '关联版本': 'versions', '版本': 'versions', 'Related Versions': 'versions',
  '优先级': 'priority', 'Priority': 'priority',
  '测试类型': 'test_type', 'Test Type': 'test_type',
  '用例类型': 'case_type', 'Case Type': 'case_type',
  '前置条件': 'preconditions', 'Preconditions': 'preconditions',
  '操作步骤': 'steps', '步骤': 'steps', 'Steps': 'steps',
  '预期结果': 'expected_result', 'Expected Result': 'expected_result',
  'L1': 'l1', 'l1': 'l1',
  'L2': 'l2', 'l2': 'l2',
  'L3': 'l3', 'l3': 'l3',
}

const triggerImport = () => {
  importInputRef.value && importInputRef.value.click()
}

const handleImportFile = async (event) => {
  const file = event.target.files && event.target.files[0]
  if (!file) return

  importing.value = true
  try {
    const data = await file.arrayBuffer()
    const workbook = XLSX.read(data, { type: 'array' })
    const firstSheetName = workbook.SheetNames[0]
    if (!firstSheetName) {
      ElMessage.error(t('testcase.importInvalidFile'))
      return
    }
    const sheet = workbook.Sheets[firstSheetName]
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
    if (!rows || rows.length < 2) {
      ElMessage.error(t('testcase.importNoValidRows'))
      return
    }

    const headers = rows[0].map(h => String(h).trim())
    const colMap = {}
    headers.forEach((h, idx) => {
      if (HEADER_FIELD_MAP[h]) colMap[HEADER_FIELD_MAP[h]] = idx
    })

    if (colMap.title === undefined) {
      ElMessage.error(t('testcase.importInvalidFile'))
      return
    }

    const cases = []
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i]
      if (!row || row.every(c => c === '' || c === null || c === undefined)) continue
      const getVal = (field) => {
        const idx = colMap[field]
        return idx === undefined ? '' : String(row[idx] ?? '').trim()
      }
      cases.push({
        case_number: getVal('case_number'),
        title: getVal('title'),
        description: getVal('description'),
        project_name: getVal('project_name'),
        versions: getVal('versions'),
        priority: getVal('priority'),
        test_type: getVal('test_type'),
        preconditions: getVal('preconditions'),
        steps: getVal('steps'),
        case_type: getVal('case_type'),
        expected_result: getVal('expected_result'),
        l1: getVal('l1'),
        l2: getVal('l2'),
        l3: getVal('l3'),
      })
    }

    if (cases.length === 0) {
      ElMessage.error(t('testcase.importNoValidRows'))
      return
    }

    const response = await api.post('/testcases/import/', { cases })
    const result = response.data || {}
    const successCount = result.success_count || 0
    const createdCount = result.created_count || 0
    const updatedCount = result.updated_count || 0

    ElMessage.success(
      t('testcase.importSuccess', { successCount }) +
      (updatedCount > 0 ? `(新增 ${createdCount} / 更新 ${updatedCount})` : '')
    )
    fetchTestCases()
  } catch (error) {
    console.error('Import test cases failed:', error)
    const result = error.response?.data || {}
    const errors = result.errors || []
    if (errors.length > 0) {
      const lines = errors.map(err => {
        const rowPart = err.row ? t('testcase.importErrorRow', { row: err.row }) : ''
        const titlePart = err.title ? `「${err.title}」` : ''
        return `${rowPart}${titlePart}${err.message || ''}`
      })
      const detail = lines.join('\n')
      await ElMessageBox.alert(detail, t('testcase.importBlockedTitle'), {
        type: 'error',
        confirmButtonText: t('common.confirm'),
        customClass: 'import-error-box'
      })
    } else {
      ElMessage.error(
        t('testcase.importFailed') + ': ' +
        (result.detail || error.message || t('common.error'))
      )
    }
  } finally {
    importing.value = false
    if (importInputRef.value) importInputRef.value.value = ''
  }
}

const fetchProjects = async () => {
  // 与「项目与版本」一致：仅显示关联了 AI用例生成 的项目
  try {
    const response = await api.get('/projects/', {
      params: { project_type: 'ai_generation', page_size: 100 }
    })
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(t('testcase.fetchProjectsFailed'))
  }
}

onMounted(() => {
  fetchProjects()
  fetchTestCases()
})
</script>

<style lang="scss" scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.card-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.filter-bar {
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.tree-detail-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 16px;
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

  // 树节点选中高亮（点击其他地方不消失）
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
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 12px;
  flex-shrink: 0;

  .selection-tip {
    color: #409eff;
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

.detail-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  word-break: break-all;
}

.detail-actions {
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

.back-btn {
  flex-shrink: 0;
}

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

.tab-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 8px 0;

  .el-button--primary {
    box-shadow: none;
  }
}

.html-content {
  white-space: pre-wrap;
  line-height: 1.6;
  word-break: break-all;
}

.priority-tag {
  &.P0 { color: #f56c6c; font-weight: bold; }
  &.P1 { color: #f56c6c; }
  &.P2 { color: #e6a23c; }
  &.P3 { color: #67c23a; }
  /* 兼容旧值（迁移前的数据） */
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.critical { color: #f56c6c; font-weight: bold; }
}

.no-version {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

@media (max-width: 1200px) {
  .page-container {
    height: auto;
    min-height: 100vh;
    overflow-y: auto;
  }

  .tree-detail-container {
    flex-direction: column;
  }

  .tree-panel {
    width: 100%;
    max-height: 360px;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 10px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .header-actions {
    width: 100%;
  }

  .filter-bar {
    padding: 15px;
  }
}
</style>

<style>
.import-error-box .el-message-box__message {
  white-space: pre-line;
  max-height: 400px;
  overflow-y: auto;
  text-align: left;
  line-height: 1.6;
}
</style>
