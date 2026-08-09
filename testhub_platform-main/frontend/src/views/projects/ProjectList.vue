<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('menu.projectAndVersion') }}</h1>
      <div class="header-actions">
        <el-button type="primary" @click="handleCreateProject">
          <el-icon><Plus /></el-icon>
          {{ $t('project.newProject') }}
        </el-button>
        <el-button type="success" @click="addVersion()">
          <el-icon><Plus /></el-icon>
          {{ $t('version.newVersion') }}
        </el-button>
      </div>
    </div>

    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input
              v-model="searchText"
              :placeholder="$t('project.searchPlaceholder')"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="statusFilter" :placeholder="$t('version.status')" clearable @change="handleFilter">
              <el-option :label="$t('version.statusDraft')" value="draft" />
              <el-option :label="$t('version.statusInProgress')" value="in_progress" />
              <el-option :label="$t('version.statusReleased')" value="released" />
              <el-option :label="$t('version.statusDeprecated')" value="deprecated" />
            </el-select>
          </el-col>
        </el-row>
      </div>

      <!-- 项目-版本层级表格 -->
      <el-table
        :data="tableData"
        :span-method="spanMethod"
        :row-class-name="getRowClass"
        v-loading="loading"
        style="width: 100%"
        border
      >
        <el-table-column :label="$t('project.projectName')" min-width="200">
          <template #default="{ row }">
            <span v-if="row.rowType === 'project'" class="project-name">
              <el-link @click="goToProject(row.project.id)" type="primary">{{ row.project.name }}</el-link>
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.projectTypesColumn')" min-width="260">
          <template #default="{ row }">
            <div v-if="row.rowType === 'project'" class="project-type-tags">
              <template v-if="row.project.project_types?.length">
                <el-tag
                  v-for="type in row.project.project_types"
                  :key="type"
                  size="small"
                  :type="getProjectTypeTagType(type)"
                  effect="plain"
                >
                  {{ getProjectTypeLabel(type) }}
                </el-tag>
              </template>
              <span v-else class="no-types">{{ $t('project.noProjectTypes') }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('version.versionName')" min-width="200">
          <template #default="{ row }">
            <div v-if="row.rowType === 'version'" class="version-name">
              <span>{{ row.version.name }}</span>
              <el-tag v-if="row.version.is_baseline" type="warning" size="small" class="baseline-tag">{{ $t('version.baseline') }}</el-tag>
            </div>
            <span v-else-if="!hasVersions(row.projectId)">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('version.status')" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.rowType === 'version'" :type="getVersionStatusType(row.version.status)">{{ getVersionStatusText(row.version.status) }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('version.owner')" width="120">
          <template #default="{ row }">
            <span v-if="row.rowType === 'version'">{{ row.version.owner || row.version.created_by?.username || '-' }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.actions')" width="200" fixed="right">
          <template #default="{ row }">
            <template v-if="row.rowType === 'version'">
              <el-button size="small" @click="editVersion(row.version)">{{ $t('common.edit') }}</el-button>
              <el-button size="small" type="danger" @click="deleteVersion(row.version)">{{ $t('common.delete') }}</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog
      :title="isEdit ? $t('project.editProject') : $t('project.createProject')"
      v-model="showCreateDialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      width="860px"
      class="create-project-dialog"
      @close="handleDialogClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" class="create-project-form">
        <!-- 基本信息 -->
        <div class="dialog-section section-basic">
          <div class="section-header">
            <el-icon class="section-icon"><Document /></el-icon>
            <span class="section-title">{{ $t('project.basicInfo') }}</span>
          </div>
          <el-form-item :label="$t('project.projectName')" prop="name">
            <el-input v-model="form.name" :placeholder="$t('project.projectNamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('project.projectDescription')" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              :placeholder="$t('project.projectDescriptionPlaceholder')"
            />
          </el-form-item>
          <el-form-item :label="$t('project.status')" prop="status">
            <el-select v-model="form.status" :placeholder="$t('project.selectStatus')" style="width: 200px">
              <el-option :label="$t('project.active')" value="active" />
              <el-option :label="$t('project.paused')" value="paused" />
              <el-option :label="$t('project.completed')" value="completed" />
              <el-option :label="$t('project.archived')" value="archived" />
            </el-select>
          </el-form-item>
        </div>

        <!-- 项目类型 -->
        <div class="dialog-section section-types">
          <div class="section-header">
            <el-icon class="section-icon"><Connection /></el-icon>
            <span class="section-title">{{ $t('project.projectTypes') }}</span>
            <span class="section-hint">{{ $t('project.projectTypesHint') }}</span>
          </div>
          <el-form-item prop="project_types" label-width="0" class="type-form-item">
            <div class="project-type-grid">
              <div
                v-for="opt in projectTypeOptions"
                :key="opt.value"
                class="project-type-card"
                :class="{ selected: form.project_types.includes(opt.value) }"
                @click="toggleProjectType(opt.value)"
              >
                <div class="type-icon-wrap" :style="{ background: opt.bg }">
                  <el-icon :size="28" :style="{ color: opt.color }">
                    <component :is="opt.icon" />
                  </el-icon>
                </div>
                <div class="type-card-title">{{ opt.label }}</div>
                <el-button
                  size="small"
                  :type="form.project_types.includes(opt.value) ? 'primary' : 'default'"
                  class="type-select-btn"
                  @click.stop="toggleProjectType(opt.value)"
                >
                  {{ form.project_types.includes(opt.value) ? $t('project.typeSelected') : $t('project.typeSelect') }}
                </el-button>
              </div>
            </div>
          </el-form-item>
        </div>

        <!-- 模块配置（随选择动态展示） -->
        <div v-if="form.project_types.length" class="dialog-section section-modules">
          <div class="section-header">
            <el-icon class="section-icon"><Setting /></el-icon>
            <span class="section-title">{{ $t('project.moduleConfig') }}</span>
          </div>
          <div class="module-config-list">
            <div
              v-for="type in form.project_types"
              :key="type"
              class="module-config-item"
            >
              <div class="module-item-left">
                <div
                  class="module-item-icon"
                  :style="{ background: getProjectTypeOption(type)?.bg, color: getProjectTypeOption(type)?.color }"
                >
                  <el-icon :size="16">
                    <component :is="getProjectTypeOption(type)?.icon" />
                  </el-icon>
                </div>
                <span>{{ getProjectTypeLabel(type) }}</span>
              </div>
              <el-icon class="module-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? $t('project.update') : $t('project.createProject') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 版本表单对话框 -->
    <el-dialog
      v-model="versionDialogVisible"
      :title="versionIsEdit ? $t('version.editVersion') : $t('version.newVersion')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="versionForm" :rules="versionRules" ref="versionFormRef" label-width="120px">
        <el-form-item :label="$t('version.versionName')" prop="name">
          <el-input v-model="versionForm.name" :placeholder="$t('version.versionNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('version.status')" prop="status">
          <el-select v-model="versionForm.status" :placeholder="$t('version.selectStatus')">
            <el-option :label="$t('version.statusDraft')" value="draft" />
            <el-option :label="$t('version.statusInProgress')" value="in_progress" />
            <el-option :label="$t('version.statusReleased')" value="released" />
            <el-option :label="$t('version.statusDeprecated')" value="deprecated" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('version.owner')" prop="owner">
          <el-input v-model="versionForm.owner" :placeholder="$t('version.selectOwner')" />
        </el-form-item>
        <el-form-item :label="$t('version.relatedProject')" prop="project_id">
          <el-select
            v-model="versionForm.project_id"
            :placeholder="$t('version.selectProject')"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="project in allProjectsForVersion"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('version.versionDescription')">
          <el-input
            v-model="versionForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('version.versionDescriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="versionForm.is_baseline">{{ $t('version.setAsBaseline') }}</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="versionDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveVersion" :loading="versionSaving">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Document, Connection, Setting, ArrowRight, Folder, MagicStick, DocumentCopy, Monitor, Iphone } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const loading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
const isEdit = ref(false)
const formRef = ref()

const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const statusFilter = ref('')

// 版本数据
const allVersions = ref([])
const allProjectsForVersion = ref([])
const versionDialogVisible = ref(false)
const versionFormRef = ref()
const versionSaving = ref(false)
const versionIsEdit = ref(false)
const editingVersionId = ref(null)

/** 路径前缀 → 项目类型；配置中心不设过滤，展示全部 */
const MODULE_TYPE_MAP = {
  '/api-testing': 'api_testing',
  '/ui-automation': 'ui_automation',
  '/app-automation': 'app_automation',
  '/ai-intelligent-mode': 'ai_intelligent',
  '/ai-generation': 'ai_generation'
}

const currentModuleType = computed(() => {
  for (const [prefix, type] of Object.entries(MODULE_TYPE_MAP)) {
    if (route.path.startsWith(prefix)) return type
  }
  return null
})

const projectsBasePath = computed(() => {
  for (const prefix of Object.keys(MODULE_TYPE_MAP)) {
    if (route.path.startsWith(prefix)) return `${prefix}/projects`
  }
  if (route.path.startsWith('/configuration')) return '/configuration/projects'
  return '/configuration/projects'
})

const form = reactive({
  id: null,
  name: '',
  description: '',
  status: 'active',
  project_types: []
})

const projectTypeOptions = computed(() => [
  {
    value: 'ai_generation',
    label: t('project.typeAiGeneration'),
    icon: Folder,
    color: '#7C3AED',
    bg: 'rgba(124, 58, 237, 0.12)'
  },
  {
    value: 'ai_intelligent',
    label: t('project.typeAiIntelligent'),
    icon: MagicStick,
    color: '#EC4899',
    bg: 'rgba(236, 72, 153, 0.12)'
  },
  {
    value: 'api_testing',
    label: t('project.typeApiTesting'),
    icon: DocumentCopy,
    color: '#4F46E5',
    bg: 'rgba(79, 70, 229, 0.12)'
  },
  {
    value: 'ui_automation',
    label: t('project.typeUiAutomation'),
    icon: Monitor,
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.12)'
  },
  {
    value: 'app_automation',
    label: t('project.typeAppAutomation'),
    icon: Iphone,
    color: '#06B6D4',
    bg: 'rgba(6, 182, 212, 0.12)'
  }
])

const rules = {
  name: [
    { required: true, message: computed(() => t('project.projectNameRequired')), trigger: 'blur' },
    { min: 2, max: 200, message: computed(() => t('project.projectNameLength')), trigger: 'blur' }
  ],
  project_types: [
    {
      type: 'array',
      required: true,
      min: 1,
      message: computed(() => t('project.projectTypesRequired')),
      trigger: 'change'
    }
  ]
}

const versionForm = reactive({
  name: '',
  status: 'draft',
  owner: '',
  description: '',
  project_id: null,
  is_baseline: false
})

const versionRules = {
  name: [{ required: true, message: computed(() => t('version.versionNameRequired')), trigger: 'blur' }],
  status: [{ required: true, message: computed(() => t('version.selectStatus')), trigger: 'change' }],
  owner: [{ required: true, message: computed(() => t('version.ownerRequired')), trigger: 'blur' }],
  project_id: [{ required: true, message: computed(() => t('version.projectRequired')), trigger: 'change' }]
}

// 按项目分组版本（支持版本状态筛选）
const projectVersionsMap = computed(() => {
  const map = {}
  allVersions.value.forEach(v => {
    // 若选择了版本状态筛选，只包含匹配状态的版本
    if (statusFilter.value && v.status !== statusFilter.value) return
    ;(v.projects || []).forEach(p => {
      if (!map[p.id]) map[p.id] = []
      map[p.id].push(v)
    })
  })
  return map
})

// 扁平化表格数据：项目行 + 版本行
const tableData = computed(() => {
  const rows = []
  projects.value.forEach(p => {
    const vers = projectVersionsMap.value[p.id] || []
    // 若选择了版本状态筛选，且该项目没有匹配的版本，则跳过该项目
    if (statusFilter.value && vers.length === 0) return
    rows.push({ rowType: 'project', projectId: p.id, project: p, version: null })
    vers.forEach(v => {
      rows.push({ rowType: 'version', projectId: p.id, project: p, version: v })
    })
  })
  return rows
})

// 合并同一项目的单元格：项目名、项目类型纵向合并所有版本行
const spanMethod = ({ row, rowIndex, columnIndex }) => {
  const rows = tableData.value
  const getProjectSpan = (startIndex, projectId) => {
    let span = 1
    let i = startIndex + 1
    while (i < rows.length && rows[i].projectId === projectId) {
      span++
      i++
    }
    return span
  }

  if (row.rowType === 'project') {
    const span = getProjectSpan(rowIndex, row.projectId)
    // 项目名称、关联类型列纵向合并
    if (columnIndex === 0 || columnIndex === 1) {
      return { rowspan: span, colspan: 1 }
    }
    // 有版本时，项目行的其余列由版本行展示
    if (span > 1) {
      return { rowspan: 0, colspan: 0 }
    }
    return { rowspan: 1, colspan: 1 }
  }
  // 版本行：前两列被项目行合并
  if (columnIndex === 0 || columnIndex === 1) {
    return { rowspan: 0, colspan: 0 }
  }
}

const hasVersions = (projectId) => {
  return (projectVersionsMap.value[projectId] || []).length > 0
}

const toggleProjectType = (type) => {
  const idx = form.project_types.indexOf(type)
  // 子模块新建时，当前模块类型默认勾选且不可取消，保证项目会出现在本模块
  if (
    idx >= 0 &&
    !isEdit.value &&
    currentModuleType.value &&
    type === currentModuleType.value
  ) {
    return
  }
  if (idx >= 0) {
    form.project_types.splice(idx, 1)
  } else {
    form.project_types.push(type)
  }
  formRef.value?.validateField?.('project_types')
}

const getProjectTypeOption = (type) => {
  return projectTypeOptions.value.find(o => o.value === type)
}

const getProjectTypeLabel = (type) => {
  const found = getProjectTypeOption(type)
  return found ? found.label : type
}

const getProjectTypeTagType = (type) => {
  const map = {
    ai_generation: 'primary',
    ai_intelligent: 'success',
    api_testing: 'warning',
    ui_automation: '',
    app_automation: 'danger'
  }
  return map[type] || 'info'
}

// 以项目板块为单位隔行变色：同一项目的项目行+版本行整体同色，相邻项目交替灰白
const getRowClass = ({ row }) => {
  const projectIndex = projects.value.findIndex(p => p.id === row.projectId)
  if (projectIndex === -1) return ''
  return projectIndex % 2 === 1 ? 'stripe-project-row' : ''
}

const buildProjectParams = (extra = {}) => {
  const params = { ...extra }
  if (currentModuleType.value) {
    params.project_type = currentModuleType.value
  }
  return params
}

const fetchProjects = async () => {
  loading.value = true
  try {
    const params = buildProjectParams({
      page: currentPage.value,
      search: searchText.value
    })
    const response = await api.get('/projects/', { params })
    projects.value = response.data.results
    total.value = response.data.count
  } catch (error) {
    ElMessage.error(t('project.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

// 拉取全部版本（分页循环）并加载全部项目供版本关联选择
const fetchAllVersions = async () => {
  try {
    const size = 100
    let page = 1
    let hasMore = true
    let all = []
    while (hasMore) {
      const res = await api.get('/versions/', { params: { page, page_size: size } })
      const results = res.data.results || []
      all.push(...results)
      if (results.length < size) hasMore = false
      else page++
    }
    allVersions.value = all
  } catch (error) {
    // 静默处理
  }
}

const fetchAllProjects = async () => {
  try {
    const size = 100
    let page = 1
    let hasMore = true
    let all = []
    while (hasMore) {
      const res = await api.get('/projects/', {
        params: buildProjectParams({ page, page_size: size })
      })
      const results = res.data.results || []
      all.push(...results)
      if (results.length < size) hasMore = false
      else page++
    }
    allProjectsForVersion.value = all
  } catch (error) {
    // 静默处理
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchProjects()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchProjects()
}

const handlePageChange = () => {
  fetchProjects()
}

const goToProject = (id) => {
  router.push(`${projectsBasePath.value}/${id}`)
}

const handleCreateProject = () => {
  resetForm()
  // 子模块新建时预选当前模块类型
  if (currentModuleType.value) {
    form.project_types = [currentModuleType.value]
  }
  showCreateDialog.value = true
}

const editProject = (project) => {
  isEdit.value = true
  form.id = project.id
  form.name = project.name
  form.description = project.description
  form.status = project.status || 'active'
  form.project_types = [...(project.project_types || [])]
  showCreateDialog.value = true
}

const handleDialogClose = () => {
  resetForm()
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.description = ''
  form.status = 'active'
  form.project_types = []
  isEdit.value = false
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await api.put(`/projects/${form.id}/`, form)
          ElMessage.success(t('project.updateSuccess'))
        } else {
          await api.post('/projects/', form)
          ElMessage.success(t('project.createSuccess'))
        }
        showCreateDialog.value = false
        resetForm()
        fetchProjects()
        fetchAllProjects()
      } catch (error) {
        ElMessage.error(isEdit.value ? t('project.updateFailed') : t('project.createFailed'))
      } finally {
        submitting.value = false
      }
    }
  })
}

const deleteProject = async (project) => {
  try {
    await ElMessageBox.confirm(t('project.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })

    await api.delete(`/projects/${project.id}/`)
    ElMessage.success(t('project.deleteSuccess'))
    fetchProjects()
    fetchAllProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('project.deleteFailed'))
    }
  }
}

// ===== 版本 CRUD =====
const addVersion = () => {
  versionIsEdit.value = false
  resetVersionForm()
  versionDialogVisible.value = true
}

const editVersion = (version) => {
  versionIsEdit.value = true
  editingVersionId.value = version.id
  versionForm.name = version.name
  versionForm.status = version.status || 'draft'
  versionForm.owner = version.owner || ''
  versionForm.description = version.description
  versionForm.project_id = version.projects?.[0]?.id || null
  versionForm.is_baseline = version.is_baseline
  versionDialogVisible.value = true
}

const saveVersion = async () => {
  if (!versionFormRef.value) return
  try {
    await versionFormRef.value.validate()
    versionSaving.value = true
    const payload = {
      name: versionForm.name,
      status: versionForm.status,
      owner: versionForm.owner,
      description: versionForm.description,
      project_ids: [versionForm.project_id],
      is_baseline: versionForm.is_baseline
    }
    if (versionIsEdit.value) {
      await api.put(`/versions/${editingVersionId.value}/`, payload)
      ElMessage.success(t('version.updateSuccess'))
    } else {
      await api.post('/versions/', payload)
      ElMessage.success(t('version.createSuccess'))
    }
    versionDialogVisible.value = false
    fetchAllVersions()
  } catch (error) {
    if (error.response?.data) {
      const errors = Object.values(error.response.data).flat()
      ElMessage.error(errors[0] || t('version.saveFailed'))
    } else if (error !== 'cancel') {
      ElMessage.error(t('version.saveFailed'))
    }
  } finally {
    versionSaving.value = false
  }
}

const deleteVersion = async (version) => {
  try {
    await ElMessageBox.confirm(t('version.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    await api.delete(`/versions/${version.id}/`)
    ElMessage.success(t('version.deleteSuccess'))
    fetchAllVersions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('version.deleteFailed'))
    }
  }
}

const resetVersionForm = () => {
  versionForm.name = ''
  versionForm.status = 'draft'
  versionForm.owner = ''
  versionForm.description = ''
  versionForm.project_id = null
  versionForm.is_baseline = false
  editingVersionId.value = null
}

const getVersionStatusType = (status) => {
  const typeMap = {
    draft: 'info',
    in_progress: 'warning',
    released: 'success',
    deprecated: 'danger'
  }
  return typeMap[status] || 'info'
}

const getVersionStatusText = (status) => {
  const textMap = {
    draft: t('version.statusDraft'),
    in_progress: t('version.statusInProgress'),
    released: t('version.statusReleased'),
    deprecated: t('version.statusDeprecated')
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchProjects()
  fetchAllProjects()
  fetchAllVersions()
})
</script>

<style lang="scss" scoped>
.filter-bar {
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

// 以项目板块为整体隔行变色
:deep(.stripe-project-row) > td {
  background-color: var(--th-bg-muted);
}

:deep(.stripe-project-row:hover) > td {
  background-color: var(--th-color-primary-softer);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.project-name {
  font-weight: 600;
}

.project-type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;

  .no-types {
    color: #909399;
    font-size: 13px;
  }
}

.create-project-form {
  .dialog-section {
    border-radius: 10px;
    padding: 16px 18px 8px;
    margin-bottom: 14px;
  }

  .section-basic {
    background: #fff;
    border: 1px solid #ebeef5;
  }

  .section-types {
    background: var(--th-color-primary-softer);
    border: 1px solid var(--el-color-primary-light-8);
  }

  .section-modules {
    background: #fff8f0;
    border: 1px solid #ffe4c4;
    padding-bottom: 16px;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    flex-wrap: wrap;

    .section-icon {
      color: var(--th-color-primary);
      font-size: 18px;
    }

    .section-title {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
    }

    .section-hint {
      margin-left: 4px;
      font-size: 13px;
      color: #909399;
    }
  }

  .type-form-item {
    margin-bottom: 8px;

    :deep(.el-form-item__content) {
      display: block;
      margin-left: 0 !important;
    }

    :deep(.el-form-item__error) {
      padding-top: 8px;
    }
  }
}

.project-type-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  width: 100%;
}

.project-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 16px 10px 14px;
  border: 1.5px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;

  &:hover {
    border-color: #79bbff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
  }

  &.selected {
    border-color: #409eff;
    background: #ecf5ff;
    box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.15);
  }

  .type-icon-wrap {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .type-card-title {
    font-size: 13px;
    font-weight: 500;
    color: #303133;
    text-align: center;
    line-height: 1.3;
    min-height: 34px;
    display: flex;
    align-items: center;
  }

  .type-select-btn {
    min-width: 72px;
  }
}

.module-config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.module-config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;

  .module-item-left {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    color: #303133;
  }

  .module-item-icon {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .module-arrow {
    color: #c0c4cc;
  }
}

.version-name {
  display: flex;
  align-items: center;
  gap: 8px;

  .baseline-tag {
    font-size: 12px;
  }
}

@media screen and (max-width: 1024px) {
  .filter-bar {
    :deep(.el-row) {
      flex-direction: column;

      .el-col {
        width: 100%;
        margin-bottom: 10px;
      }
    }
  }

  .project-type-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media screen and (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  :deep(.el-dialog) {
    width: 95% !important;
    margin: 0 auto;
  }

  .project-type-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
