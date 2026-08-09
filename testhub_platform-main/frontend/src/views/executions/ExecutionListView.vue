<template>
  <div class="execution-list">
    <div class="header">
      <h1>{{ $t('execution.testPlan') }}</h1>
      <div class="header-actions">
        <el-button
          v-if="selectedPlans.length > 0"
          type="danger"
          :icon="Delete"
          @click="batchDeletePlans"
          :disabled="isDeleting">
          {{ $t('execution.batchDelete') }} ({{ selectedPlans.length }})
        </el-button>
        <el-button type="primary" @click="openCreatePlanDialog">
          <el-icon><Plus /></el-icon>
          {{ $t('execution.newPlan') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true">
        <el-form-item :label="$t('execution.project')">
          <el-select v-model="filters.project" :placeholder="$t('execution.selectProject')" clearable style="width: 200px">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.status')">
          <el-select v-model="filters.is_active" :placeholder="$t('execution.selectStatus')" clearable style="width: 120px">
            <el-option :label="$t('execution.filterActive')" :value="true"></el-option>
            <el-option :label="$t('execution.filterClosed')" :value="false"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">{{ $t('common.search') }}</el-button>
          <el-button @click="resetFilters">{{ $t('common.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table
      :data="testPlans"
      style="width: 100%"
      v-loading="loading"
      @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column
        type="index"
        :label="$t('execution.serialNumber')"
        width="80"
        :index="getSerialNumber" />
      <el-table-column prop="name" :label="$t('execution.planName')" min-width="200">
        <template #default="scope">
          <el-link type="primary" @click="viewPlan(scope.row.id)">
            {{ scope.row.name }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="projects" :label="$t('execution.projects')" width="200">
        <template #default="scope">
          <span v-if="scope.row.projects && scope.row.projects.length > 0">
            {{ scope.row.projects.join(', ') }}
          </span>
          <span v-else>{{ $t('execution.noData') }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="version" :label="$t('execution.version')" width="120"></el-table-column>
      <el-table-column prop="creator.username" :label="$t('execution.creator')" width="120"></el-table-column>
      <el-table-column :label="$t('execution.status')" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">
            {{ scope.row.is_active ? $t('execution.active') : $t('execution.closed') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="$t('execution.createdAt')" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('execution.actions')" width="300" fixed="right">
        <template #default="scope">
          <el-button size="small" type="success" @click="openAssignTestcases(scope.row)">
            {{ $t('execution.assignCases') }}
          </el-button>
          <el-button size="small" type="primary" @click="viewPlan(scope.row.id)">
            {{ $t('execution.viewExecution') }}
          </el-button>
          <el-button size="small" type="warning" @click="editPlan(scope.row)">
            {{ $t('common.edit') }}
          </el-button>
          <el-button size="small" type="danger" @click="deletePlan(scope.row)">
            {{ $t('common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :small="false"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 创建测试计划对话框 -->
    <el-dialog :title="$t('execution.createPlanDialog')" v-model="isCreatePlanDialogOpen" width="600px" :close-on-click-modal="false">
      <el-form :model="newPlanForm" :rules="planRules" ref="planFormRef" label-width="100px">
        <el-form-item :label="$t('execution.planName')" prop="name">
          <el-input v-model="newPlanForm.name" :placeholder="$t('execution.planNamePlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.planDescription')">
          <el-input
            v-model="newPlanForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('execution.planDescriptionPlaceholder')">
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedProjects')" prop="projects">
          <el-select
            v-model="newPlanForm.projects"
            multiple
            :placeholder="$t('execution.selectProjects')"
            style="width: 100%"
            @change="handleProjectChange">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedVersion')">
          <el-select
            v-model="newPlanForm.version"
            :placeholder="!newPlanForm.projects || newPlanForm.projects.length === 0 ? $t('execution.selectVersionDisabled') : $t('execution.selectVersion')"
            style="width: 100%"
            :disabled="!newPlanForm.projects || newPlanForm.projects.length === 0"
            :loading="loadingVersions"
            clearable>
            <el-option-group
              v-for="group in versionGroups"
              :key="group.projectId"
              :label="group.projectName">
              <el-option
                v-for="item in group.versions"
                :key="`${group.projectId}-${item.id}`"
                :label="item.name"
                :value="item.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.assignees')">
          <el-select v-model="newPlanForm.assignees" multiple :placeholder="$t('execution.selectAssignees')" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isCreatePlanDialogOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="createPlan" :loading="creating">{{ $t('execution.createPlan') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 选择测试用例对话框 -->
    <el-dialog
      :title="$t('execution.testcaseSelectorTitle')"
      v-model="isTestcaseSelectorOpen"
      width="900px"
      :close-on-click-modal="false"
      class="testcase-selector-dialog"
      @closed="onTestcaseSelectorClosed">
      <div class="testcase-selector-filters">
        <el-form :inline="true" @submit.prevent>
          <el-form-item :label="$t('execution.keyword')">
            <el-input
              v-model="testcaseFilters.keyword"
              :placeholder="$t('execution.keywordPlaceholder')"
              clearable
              style="width: 180px"
              @keyup.enter="applyTestcaseFilters" />
          </el-form-item>
          <el-form-item :label="$t('execution.priority')">
            <el-select v-model="testcaseFilters.priority" :placeholder="$t('execution.allPriority')" clearable style="width: 140px">
              <el-option :label="$t('execution.allPriority')" value="" />
              <el-option label="P0" value="P0" />
              <el-option label="P1" value="P1" />
              <el-option label="P2" value="P2" />
              <el-option label="P3" value="P3" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('execution.testType')">
            <el-select v-model="testcaseFilters.test_type" :placeholder="$t('execution.allTestType')" clearable style="width: 140px">
              <el-option :label="$t('execution.allTestType')" value="" />
              <el-option :label="$t('testcase.functional')" value="functional" />
              <el-option :label="$t('testcase.integration')" value="integration" />
              <el-option :label="$t('testcase.api')" value="api" />
              <el-option :label="$t('testcase.ui')" value="ui" />
              <el-option :label="$t('testcase.performance')" value="performance" />
              <el-option :label="$t('testcase.security')" value="security" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="applyTestcaseFilters">{{ $t('common.search') }}</el-button>
            <el-button @click="resetTestcaseFilters">{{ $t('common.reset') }}</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        ref="testcaseTableRef"
        :data="paginatedTestcases"
        v-loading="loadingTestcases"
        row-key="id"
        max-height="400"
        @selection-change="handleTestcaseSelectionChange">
        <el-table-column type="selection" width="48" reserve-selection />
        <el-table-column :label="$t('execution.caseNumber')" width="70" align="center">
          <template #default="{ $index }">
            {{ (testcasePage - 1) * testcasePageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="title" :label="$t('execution.caseTitle')" min-width="220" show-overflow-tooltip />
        <el-table-column prop="priority" :label="$t('execution.priority')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :class="`priority-tag ${row.priority}`" size="small" effect="light">
              {{ getPriorityText(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="test_type" :label="$t('execution.testType')" width="110" align="center">
          <template #default="{ row }">
            {{ getTypeText(row.test_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="project__name" :label="$t('execution.belongsToProject')" width="140" show-overflow-tooltip />
      </el-table>

      <div class="testcase-selector-pagination">
        <el-pagination
          v-model:current-page="testcasePage"
          v-model:page-size="testcasePageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredSelectorTestcases.length"
          layout="total, sizes, prev, pager, next"
          @size-change="handleTestcaseSizeChange"
          @current-change="handleTestcasePageChange" />
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isTestcaseSelectorOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="confirmTestcaseSelection" :loading="assigning">
            {{ $t('execution.confirmSelect') }} ({{ tempSelectedTestcases.length }})
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑测试计划对话框 -->
    <el-dialog :title="$t('execution.editPlanDialog')" v-model="isEditPlanDialogOpen" width="600px" :close-on-click-modal="false">
      <el-form :model="editPlanForm" :rules="planRules" ref="editPlanFormRef" label-width="100px">
        <el-form-item :label="$t('execution.planName')" prop="name">
          <el-input v-model="editPlanForm.name" :placeholder="$t('execution.planNamePlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.planDescription')">
          <el-input
            v-model="editPlanForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('execution.planDescriptionPlaceholder')">
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedProjects')" prop="projects">
          <el-select
            v-model="editPlanForm.projects"
            multiple
            :placeholder="$t('execution.selectProjects')"
            style="width: 100%"
            @change="handleEditProjectChange">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedVersion')">
          <el-select
            v-model="editPlanForm.version"
            :placeholder="!editPlanForm.projects || editPlanForm.projects.length === 0 ? $t('execution.selectVersionDisabled') : $t('execution.selectVersion')"
            style="width: 100%"
            :disabled="!editPlanForm.projects || editPlanForm.projects.length === 0"
            :loading="loadingVersions"
            clearable>
            <el-option-group
              v-for="group in versionGroups"
              :key="group.projectId"
              :label="group.projectName">
              <el-option
                v-for="item in group.versions"
                :key="`${group.projectId}-${item.id}`"
                :label="item.name"
                :value="item.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.assignees')">
          <el-select v-model="editPlanForm.assignees" multiple :placeholder="$t('execution.selectAssignees')" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.planStatus')">
          <el-switch v-model="editPlanForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isEditPlanDialogOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="updatePlan" :loading="updating">{{ $t('execution.updatePlan') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testPlans = ref([])
const projects = ref([])
const versions = ref([])
const filteredTestcases = ref([])
const loadingTestcases = ref(false)
const versionGroups = ref([])
const loadingVersions = ref(false)
const users = ref([])
const selectedPlans = ref([])
const isDeleting = ref(false)

// 测试用例选择弹窗
const isTestcaseSelectorOpen = ref(false)
const testcaseTableRef = ref()
const tempSelectedTestcases = ref([])
const syncingTestcaseSelection = ref(false)
const assigning = ref(false)
const assigningPlanId = ref(null)
const testcasePage = ref(1)
const testcasePageSize = ref(20)
const testcaseFilters = reactive({
  keyword: '',
  priority: '',
  test_type: ''
})
const appliedTestcaseFilters = reactive({
  keyword: '',
  priority: '',
  test_type: ''
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const filters = reactive({
  project: null,
  is_active: null
})

// 表单
const isCreatePlanDialogOpen = ref(false)
const isEditPlanDialogOpen = ref(false)
const planFormRef = ref()
const editPlanFormRef = ref()
const currentEditingPlan = ref(null)
const newPlanForm = reactive({
  name: '',
  description: '',
  projects: [], // 改为数组
  version: null,
  assignees: []
})

const editPlanForm = reactive({
  id: null,
  name: '',
  description: '',
  projects: [],
  version: null,
  assignees: [],
  is_active: true
})

const planRules = {
  name: [
    { required: true, message: computed(() => t('execution.planNameRequired')), trigger: 'blur' }
  ],
  projects: [
    { required: true, message: computed(() => t('execution.projectsRequired')), trigger: 'change' }
  ]
}

const filteredSelectorTestcases = computed(() => {
  let list = filteredTestcases.value || []
  const keyword = (appliedTestcaseFilters.keyword || '').trim().toLowerCase()
  if (keyword) {
    list = list.filter(item => {
      const title = (item.title || '').toLowerCase()
      const idText = String(item.id || '')
      return title.includes(keyword) || idText.includes(keyword)
    })
  }
  if (appliedTestcaseFilters.priority) {
    list = list.filter(item => item.priority === appliedTestcaseFilters.priority)
  }
  if (appliedTestcaseFilters.test_type) {
    list = list.filter(item => item.test_type === appliedTestcaseFilters.test_type)
  }
  return list
})

const paginatedTestcases = computed(() => {
  const start = (testcasePage.value - 1) * testcasePageSize.value
  return filteredSelectorTestcases.value.slice(start, start + testcasePageSize.value)
})

const fetchTestPlans = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ...filters
    }
    // 过滤掉空值
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })

    const response = await api.get('/executions/plans/', { params })
    testPlans.value = response.data.results || response.data || []
    total.value = response.data.count || testPlans.value.length
  } catch (error) {
    ElMessage.error(t('execution.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const fetchBasicData = async () => {
  try {
    const [projectsRes, versionsRes, usersRes] = await Promise.all([
      // 与「项目与版本」一致：仅显示关联了 AI用例生成 的项目
      api.get('/projects/', { params: { project_type: 'ai_generation', page_size: 100 } }),
      api.get('/versions/'),
      api.get('/users/users/') // 修正用户API路径
    ])
    
    projects.value = (projectsRes.data.results || projectsRes.data || []).filter(item => item !== null && item !== undefined)
    versions.value = (versionsRes.data.results || versionsRes.data || []).filter(item => item !== null && item !== undefined)
    users.value = (usersRes.data.results || usersRes.data || []).filter(item => item !== null && item !== undefined)
  } catch (error) {
    console.error('获取基础数据失败:', error)
  }
}

// 根据选中的项目加载版本（按项目分组）
const loadVersionsByProjects = async (projectIds, form = newPlanForm) => {
  if (!projectIds || projectIds.length === 0) {
    versionGroups.value = []
    return
  }

  loadingVersions.value = true
  try {
    const groups = await Promise.all(
      projectIds.map(async (projectId) => {
        const project = projects.value.find(p => p.id === projectId)
        const response = await api.get(`/versions/projects/${projectId}/versions/`)
        const list = (response.data.results || response.data || []).filter(item => item != null)
        return {
          projectId,
          projectName: project?.name || String(projectId),
          versions: list
        }
      })
    )
    versionGroups.value = groups

    // 若当前选中版本已不在可选列表中，则清空
    const availableIds = new Set(groups.flatMap(group => group.versions.map(v => v.id)))
    if (form.version && !availableIds.has(form.version)) {
      form.version = null
    }
  } catch (error) {
    console.error('Load versions error:', error)
    versionGroups.value = []
    ElMessage.error(t('execution.fetchVersionsFailed'))
  } finally {
    loadingVersions.value = false
  }
}

const findVersionIdByName = (versionName) => {
  if (!versionName) return null
  const fromGroups = versionGroups.value
    .flatMap(group => group.versions)
    .find(v => v.name === versionName)
  if (fromGroups) return fromGroups.id
  return versions.value.find(v => v.name === versionName)?.id || null
}

// 根据选中的项目加载测试用例
const loadTestcasesByProjects = async (projectIds) => {
  if (!projectIds || projectIds.length === 0) {
    filteredTestcases.value = []
    return
  }

  loadingTestcases.value = true

  try {
    const params = new URLSearchParams()
    projectIds.forEach(id => params.append('project_ids', id))

    console.log('API URL:', `/executions/plans/testcases_by_projects/?${params.toString()}`)

    const response = await api.get(`/executions/plans/testcases_by_projects/?${params.toString()}`)
    console.log('API Response:', response.data)

    filteredTestcases.value = response.data.results || []
    console.log('Filtered testcases:', filteredTestcases.value)
  } catch (error) {
    console.error('Load testcases error:', error)
    if (error.response?.status === 400) {
      ElMessage.warning(error.response.data.detail || t('execution.selectProjectFirst'))
    } else if (error.response?.status === 401) {
      ElMessage.error(t('auth.loginFailed'))
    } else {
      ElMessage.error(t('execution.fetchTestcasesFailed') + ': ' + (error.response?.data?.detail || error.message))
    }
    filteredTestcases.value = []
  } finally {
    loadingTestcases.value = false
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    P0: t('testcase.p0'),
    P1: t('testcase.p1'),
    P2: t('testcase.p2'),
    P3: t('testcase.p3'),
    high: t('testcase.high'),
    medium: t('testcase.medium'),
    low: t('testcase.low'),
    critical: t('testcase.critical')
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
  return textMap[type] || type || '-'
}

const syncTestcaseTableSelection = async () => {
  await nextTick()
  const table = testcaseTableRef.value
  if (!table) return
  syncingTestcaseSelection.value = true
  table.clearSelection()
  const selectedIds = new Set(tempSelectedTestcases.value.map(item => item.id))
  filteredTestcases.value.forEach(row => {
    if (selectedIds.has(row.id)) {
      table.toggleRowSelection(row, true)
    }
  })
  await nextTick()
  syncingTestcaseSelection.value = false
}

const openAssignTestcases = async (plan) => {
  try {
    assigningPlanId.value = plan.id
    loadingTestcases.value = true

    const assignedRes = await api.get(`/executions/plans/${plan.id}/assigned_testcases/`)
    const projectIds = assignedRes.data.project_ids || []
    const assignedIds = new Set(assignedRes.data.testcase_ids || [])

    if (!projectIds.length) {
      ElMessage.warning(t('execution.assignNeedProject'))
      assigningPlanId.value = null
      return
    }

    await loadTestcasesByProjects(projectIds)

    testcasePage.value = 1
    Object.assign(testcaseFilters, { keyword: '', priority: '', test_type: '' })
    Object.assign(appliedTestcaseFilters, { keyword: '', priority: '', test_type: '' })
    tempSelectedTestcases.value = filteredTestcases.value.filter(item => assignedIds.has(item.id))

    isTestcaseSelectorOpen.value = true
    await syncTestcaseTableSelection()
  } catch (error) {
    console.error('Open assign testcases failed:', error)
    ElMessage.error(t('execution.fetchTestcasesFailed'))
    assigningPlanId.value = null
  } finally {
    loadingTestcases.value = false
  }
}

const applyTestcaseFilters = () => {
  Object.assign(appliedTestcaseFilters, { ...testcaseFilters })
  testcasePage.value = 1
}

const resetTestcaseFilters = () => {
  Object.assign(testcaseFilters, { keyword: '', priority: '', test_type: '' })
  Object.assign(appliedTestcaseFilters, { keyword: '', priority: '', test_type: '' })
  testcasePage.value = 1
}

const handleTestcaseSelectionChange = (selection) => {
  if (syncingTestcaseSelection.value) return
  // 客户端分页时 selection 通常仅含当前页，需与跨页已选合并
  const currentPageIds = new Set(paginatedTestcases.value.map(item => item.id))
  const kept = tempSelectedTestcases.value.filter(item => !currentPageIds.has(item.id))
  const merged = [...kept]
  selection.forEach(item => {
    if (!merged.some(existing => existing.id === item.id)) {
      merged.push(item)
    }
  })
  tempSelectedTestcases.value = merged
}

const handleTestcaseSizeChange = () => {
  testcasePage.value = 1
}

const handleTestcasePageChange = () => {
  // 分页切换后保留勾选状态由 reserve-selection 处理
}

const confirmTestcaseSelection = async () => {
  if (!assigningPlanId.value) {
    isTestcaseSelectorOpen.value = false
    return
  }
  if (!tempSelectedTestcases.value.length) {
    ElMessage.warning(t('execution.testcasesRequired'))
    return
  }

  assigning.value = true
  try {
    const response = await api.post(`/executions/plans/${assigningPlanId.value}/assign_testcases/`, {
      testcases: tempSelectedTestcases.value.map(item => item.id)
    })
    const addedCount = response.data?.added_count ?? 0
    ElMessage.success(t('execution.assignSuccess', { count: addedCount }))
    isTestcaseSelectorOpen.value = false
  } catch (error) {
    const detail = error.response?.data?.detail || error.response?.data?.error
    ElMessage.error(detail || t('execution.assignFailed'))
  } finally {
    assigning.value = false
  }
}

const onTestcaseSelectorClosed = () => {
  tempSelectedTestcases.value = []
  assigningPlanId.value = null
  filteredTestcases.value = []
}

// 处理项目选择变化
const handleProjectChange = (selectedProjects) => {
  newPlanForm.version = null

  if (selectedProjects && selectedProjects.length > 0) {
    loadVersionsByProjects(selectedProjects, newPlanForm)
  } else {
    versionGroups.value = []
  }
}

const handleEditProjectChange = (selectedProjects) => {
  editPlanForm.version = null
  if (selectedProjects && selectedProjects.length > 0) {
    loadVersionsByProjects(selectedProjects, editPlanForm)
  } else {
    versionGroups.value = []
  }
}

const createPlan = async () => {
  try {
    await planFormRef.value.validate()
    creating.value = true

    await api.post('/executions/plans/', newPlanForm)
    ElMessage.success(t('execution.createSuccess'))
    isCreatePlanDialogOpen.value = false
    resetPlanForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error(t('execution.createFailed'))
    }
  } finally {
    creating.value = false
  }
}

const viewPlan = (id) => {
  router.push(`/ai-generation/executions/${id}`)
}

const editPlan = async (plan) => {
  try {
    // 获取完整的测试计划详情
    const response = await api.get(`/executions/plans/${plan.id}/`)
    const planDetail = response.data

    // 设置当前编辑的计划
    currentEditingPlan.value = planDetail

    const projectIds = planDetail.projects?.map(p => {
      // 如果是字符串，需要找到对应的项目ID
      const project = projects.value.find(proj => proj.name === p)
      return project ? project.id : p
    }) || []

    // 填充编辑表单数据
    Object.assign(editPlanForm, {
      id: planDetail.id,
      name: planDetail.name,
      description: planDetail.description || '',
      projects: projectIds,
      version: null,
      assignees: planDetail.assignees || [],
      is_active: planDetail.is_active
    })

    // 按关联项目加载版本分组后再回填版本
    await loadVersionsByProjects(projectIds, editPlanForm)
    editPlanForm.version = findVersionIdByName(planDetail.version)

    isEditPlanDialogOpen.value = true
  } catch (error) {
    ElMessage.error(t('execution.fetchDetailFailed'))
  }
}

const updatePlan = async () => {
  try {
    await editPlanFormRef.value.validate()
    updating.value = true

    const updateData = {
      name: editPlanForm.name,
      description: editPlanForm.description,
      projects: editPlanForm.projects,
      version: editPlanForm.version,
      assignees: editPlanForm.assignees,
      is_active: editPlanForm.is_active
    }

    await api.put(`/executions/plans/${editPlanForm.id}/`, updateData)
    ElMessage.success(t('execution.updateSuccess'))
    isEditPlanDialogOpen.value = false
    resetEditForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error(t('execution.updateFailed'))
    }
  } finally {
    updating.value = false
  }
}

const resetEditForm = () => {
  Object.assign(editPlanForm, {
    id: null,
    name: '',
    description: '',
    projects: [],
    version: null,
    assignees: [],
    is_active: true
  })
  versionGroups.value = []
  loadingVersions.value = false
  currentEditingPlan.value = null
  editPlanFormRef.value?.resetFields()
}

const deletePlan = async (plan) => {
  try {
    await ElMessageBox.confirm(
      t('execution.deleteConfirm', { name: plan.name }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/executions/plans/${plan.id}/`)
    ElMessage.success(t('execution.deleteSuccess'))
    fetchTestPlans()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('execution.deleteFailed'))
    }
  }
}

const openCreatePlanDialog = () => {
  resetPlanForm()
  isCreatePlanDialogOpen.value = true
}

const resetPlanForm = () => {
  Object.assign(newPlanForm, {
    name: '',
    description: '',
    projects: [], // 改为数组
    version: null,
    assignees: []
  })
  versionGroups.value = []
  loadingVersions.value = false
  planFormRef.value?.resetFields()
}

const applyFilters = () => {
  currentPage.value = 1
  fetchTestPlans()
}

const resetFilters = () => {
  Object.assign(filters, {
    project: null,
    is_active: null
  })
  currentPage.value = 1
  fetchTestPlans()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTestPlans()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTestPlans()
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedPlans.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeletePlans = async () => {
  if (selectedPlans.value.length === 0) {
    ElMessage.warning(t('execution.selectFirst'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('execution.batchDeleteConfirm', { count: selectedPlans.value.length }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    for (const plan of selectedPlans.value) {
      try {
        await api.delete(`/executions/plans/${plan.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除测试计划 ${plan.id} 失败:`, error)
        failCount++
      }
    }

    if (successCount > 0) {
      if (failCount > 0) {
        ElMessage.success(t('execution.batchDeletePartialSuccess', { successCount, failCount }))
      } else {
        ElMessage.success(t('execution.batchDeleteSuccess', { successCount }))
      }
    } else {
      ElMessage.error(t('execution.batchDeleteFailed'))
    }

    selectedPlans.value = []
    fetchTestPlans()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(t('execution.batchDeleteFailed'))
    }
  } finally {
    isDeleting.value = false
  }
}

onMounted(() => {
  fetchTestPlans()
  fetchBasicData()
})
</script>

<style scoped>
.execution-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.testcase-selector-filters {
  margin-bottom: 12px;
}

.testcase-selector-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.priority-tag.P0,
.priority-tag.critical {
  color: #e6a23c;
  background: #fdf6ec;
  border-color: #f5dab1;
}

.priority-tag.P1,
.priority-tag.high {
  color: #e6a23c;
  background: #fdf6ec;
  border-color: #f5dab1;
}

.priority-tag.P2,
.priority-tag.medium {
  color: #67c23a;
  background: #f0f9eb;
  border-color: #c2e7b0;
}

.priority-tag.P3,
.priority-tag.low {
  color: #909399;
  background: #f4f4f5;
  border-color: #d3d4d6;
}
</style>
