<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('project.projectDetail') }}</h1>
      <el-button type="primary" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        {{ $t('common.back') }}
      </el-button>
    </div>

    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="$t('project.projectInfo')" name="info">
          <div v-if="project">
            <!-- 查看模式 -->
            <template v-if="!isEditing">
              <div class="info-header">
                <el-button type="primary" @click="startEdit">
                  <el-icon><Edit /></el-icon>
                  {{ $t('common.edit') }}
                </el-button>
                <el-button type="danger" :loading="deleting" @click="deleteProject">
                  <el-icon><Delete /></el-icon>
                  {{ $t('common.delete') }}
                </el-button>
              </div>
              <el-descriptions :column="2" border>
                <el-descriptions-item :label="$t('project.projectName')" :span="2">{{ project.name }}</el-descriptions-item>
                <el-descriptions-item :label="$t('project.projectDescription')" :span="2">{{ project.description || $t('project.noDescription') }}</el-descriptions-item>
                <el-descriptions-item :label="$t('project.status')" :span="2">
                  <el-tag :type="getStatusTagType(project.status)" size="small">
                    {{ getStatusLabel(project.status) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('project.createdAt')" :span="2">{{ formatDate(project.created_at) }}</el-descriptions-item>
                <el-descriptions-item :label="$t('project.projectTypesColumn')" :span="2">
                  <div v-if="project.project_types?.length" class="module-tags">
                    <el-tag
                      v-for="type in project.project_types"
                      :key="type"
                      size="small"
                      effect="plain"
                      :type="getProjectTypeTagType(type)"
                    >
                      {{ getProjectTypeLabel(type) }}
                    </el-tag>
                  </div>
                  <span v-else class="no-modules">{{ $t('project.noProjectTypes') }}</span>
                </el-descriptions-item>
              </el-descriptions>

              <!-- 模块内容 -->
              <div class="modules-section">
                <div class="modules-section-header">
                  <el-icon><Setting /></el-icon>
                  <span>{{ $t('project.moduleContent') }}</span>
                </div>
                <div v-if="project.project_types?.length" class="module-cards">
                  <div
                    v-for="type in project.project_types"
                    :key="type"
                    class="module-card"
                  >
                    <div
                      class="module-card-icon"
                      :style="{ background: getProjectTypeOption(type)?.bg, color: getProjectTypeOption(type)?.color }"
                    >
                      <el-icon :size="24">
                        <component :is="getProjectTypeOption(type)?.icon" />
                      </el-icon>
                    </div>
                    <div class="module-card-body">
                      <div class="module-card-title">{{ getProjectTypeLabel(type) }}</div>
                      <div class="module-card-desc">{{ getProjectTypeDesc(type) }}</div>
                    </div>
                    <el-button
                      v-if="getProjectTypeRoute(type)"
                      class="enter-module-btn"
                      type="primary"
                      @click="goToModule(type)"
                    >
                      {{ $t('project.enterModule') }}
                    </el-button>
                  </div>
                </div>
                <el-empty v-else :description="$t('project.noProjectTypes')" :image-size="80" />
              </div>
            </template>

            <!-- 编辑模式 -->
            <template v-else>
              <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px" class="edit-project-form">
                <el-form-item :label="$t('project.projectName')" prop="name">
                  <el-input v-model="editForm.name" />
                </el-form-item>
                <el-form-item :label="$t('project.projectDescription')" prop="description">
                  <el-input v-model="editForm.description" type="textarea" :rows="4" />
                </el-form-item>
                <el-form-item :label="$t('project.status')" prop="status">
                  <el-select v-model="editForm.status" style="width: 200px">
                    <el-option :label="$t('project.active')" value="active" />
                    <el-option :label="$t('project.paused')" value="paused" />
                    <el-option :label="$t('project.completed')" value="completed" />
                    <el-option :label="$t('project.archived')" value="archived" />
                  </el-select>
                </el-form-item>
                <el-form-item :label="$t('project.projectTypesColumn')" prop="project_types">
                  <div class="project-type-grid">
                    <div
                      v-for="opt in projectTypeOptions"
                      :key="opt.value"
                      class="project-type-card"
                      :class="{ selected: editForm.project_types.includes(opt.value) }"
                      @click="toggleProjectType(opt.value)"
                    >
                      <div class="type-icon-wrap" :style="{ background: opt.bg }">
                        <el-icon :size="22" :style="{ color: opt.color }">
                          <component :is="opt.icon" />
                        </el-icon>
                      </div>
                      <div class="type-card-title">{{ opt.label }}</div>
                      <el-button
                        size="small"
                        :type="editForm.project_types.includes(opt.value) ? 'primary' : 'default'"
                        @click.stop="toggleProjectType(opt.value)"
                      >
                        {{ editForm.project_types.includes(opt.value) ? $t('project.typeSelected') : $t('project.typeSelect') }}
                      </el-button>
                    </div>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="saving" @click="saveProject">{{ $t('common.save') }}</el-button>
                  <el-button @click="cancelEdit">{{ $t('common.cancel') }}</el-button>
                </el-form-item>
              </el-form>
            </template>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="$t('project.environments')" name="environments">
          <div class="environments-section">
            <div class="env-header">
              <el-button type="primary" @click="openEnvDialog">{{ $t('project.addEnvironment') }}</el-button>
            </div>
            <el-table :data="project?.environments || []" style="width: 100%; margin-top: 20px;">
              <el-table-column prop="name" :label="$t('project.environmentName')" />
              <el-table-column prop="base_url" :label="$t('project.baseUrl')" />
              <el-table-column prop="description" :label="$t('project.description')" />
              <el-table-column prop="is_default" :label="$t('project.defaultEnvironment')">
                <template #default="{ row }">
                  <el-tag v-if="row.is_default" type="success">{{ $t('project.yes') }}</el-tag>
                  <span v-else>{{ $t('project.no') }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('project.actions')" width="150" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" link @click="openEditEnvDialog(row)">{{ $t('common.edit') }}</el-button>
                  <el-button size="small" type="danger" link @click="deleteEnvironment(row)">{{ $t('common.delete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 添加/编辑环境对话框 -->
    <el-dialog v-model="envDialogVisible" :title="envIsEdit ? $t('project.editEnvironment') : $t('project.addEnvironment')" width="500px">
      <el-form ref="envFormRef" :model="envForm" :rules="envRules" label-width="100px">
        <el-form-item :label="$t('project.environmentName')" prop="name">
          <el-input v-model="envForm.name" :placeholder="$t('project.environmentName')" />
        </el-form-item>
        <el-form-item :label="$t('project.baseUrl')" prop="base_url">
          <el-input v-model="envForm.base_url" :placeholder="$t('project.baseUrl')" />
        </el-form-item>
        <el-form-item :label="$t('project.description')" prop="description">
          <el-input v-model="envForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item :label="$t('project.defaultEnvironment')" prop="is_default">
          <el-switch v-model="envForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="envDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="envSaving" @click="saveEnvironment">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Edit, Delete, ArrowLeft, Setting, Folder, MagicStick,
  DocumentCopy, Monitor, Iphone
} from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const project = ref(null)
const activeTab = ref('info')
const isEditing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const editFormRef = ref(null)
const envDialogVisible = ref(false)
const envSaving = ref(false)
const envFormRef = ref(null)
const envIsEdit = ref(false)
const editingEnvId = ref(null)

const editForm = reactive({
  name: '',
  description: '',
  status: 'active',
  project_types: []
})

const editRules = {
  name: [{ required: true, message: t('project.projectNameRequired'), trigger: 'blur' }],
  project_types: [
    {
      type: 'array',
      required: true,
      min: 1,
      message: t('project.projectTypesRequired'),
      trigger: 'change'
    }
  ]
}

const projectTypeOptions = computed(() => [
  {
    value: 'ai_generation',
    label: t('project.typeAiGeneration'),
    desc: t('project.typeAiGenerationDesc'),
    icon: Folder,
    color: '#7C3AED',
    bg: 'rgba(124, 58, 237, 0.12)',
    route: '/ai-generation/requirement-analysis'
  },
  {
    value: 'ai_intelligent',
    label: t('project.typeAiIntelligent'),
    desc: t('project.typeAiIntelligentDesc'),
    icon: MagicStick,
    color: '#EC4899',
    bg: 'rgba(236, 72, 153, 0.12)',
    route: '/ai-intelligent-mode/projects'
  },
  {
    value: 'api_testing',
    label: t('project.typeApiTesting'),
    desc: t('project.typeApiTestingDesc'),
    icon: DocumentCopy,
    color: '#4F46E5',
    bg: 'rgba(79, 70, 229, 0.12)',
    route: '/api-testing/projects'
  },
  {
    value: 'ui_automation',
    label: t('project.typeUiAutomation'),
    desc: t('project.typeUiAutomationDesc'),
    icon: Monitor,
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    route: '/ui-automation/projects'
  },
  {
    value: 'app_automation',
    label: t('project.typeAppAutomation'),
    desc: t('project.typeAppAutomationDesc'),
    icon: Iphone,
    color: '#06B6D4',
    bg: 'rgba(6, 182, 212, 0.12)',
    route: '/app-automation/projects'
  }
])

const envForm = reactive({
  name: '',
  base_url: '',
  description: '',
  is_default: false
})

const envRules = {
  name: [{ required: true, message: t('project.environmentNameRequired'), trigger: 'blur' }],
  base_url: [{ required: true, message: t('project.baseUrlRequired'), trigger: 'blur' }]
}

const getProjectTypeOption = (type) => projectTypeOptions.value.find(o => o.value === type)
const getProjectTypeLabel = (type) => getProjectTypeOption(type)?.label || type
const getProjectTypeDesc = (type) => getProjectTypeOption(type)?.desc || ''
const getProjectTypeRoute = (type) => getProjectTypeOption(type)?.route || ''

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

const getStatusLabel = (status) => {
  const map = {
    active: t('project.active'),
    paused: t('project.paused'),
    completed: t('project.completed'),
    archived: t('project.archived')
  }
  return map[status] || status
}

const getStatusTagType = (status) => {
  const map = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return map[status] || 'info'
}

const toggleProjectType = (type) => {
  const idx = editForm.project_types.indexOf(type)
  if (idx >= 0) {
    editForm.project_types.splice(idx, 1)
  } else {
    editForm.project_types.push(type)
  }
  editFormRef.value?.validateField?.('project_types')
}

const goToModule = (type) => {
  const path = getProjectTypeRoute(type)
  if (path) router.push(path)
}

const fetchProject = async () => {
  try {
    const response = await api.get(`/projects/${route.params.id}/`)
    project.value = response.data
  } catch (error) {
    ElMessage.error(t('project.fetchDetailFailed'))
  }
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const startEdit = () => {
  editForm.name = project.value?.name || ''
  editForm.description = project.value?.description || ''
  editForm.status = project.value?.status || 'active'
  editForm.project_types = [...(project.value?.project_types || [])]
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
}

const getProjectsListPath = () => {
  const path = route.path || ''
  if (path.startsWith('/configuration')) return '/configuration/projects'
  if (path.startsWith('/api-testing')) return '/api-testing/projects'
  if (path.startsWith('/ui-automation')) return '/ui-automation/projects'
  if (path.startsWith('/app-automation')) return '/app-automation/projects'
  if (path.startsWith('/ai-generation')) return '/ai-generation/projects'
  if (path.startsWith('/ai-intelligent')) return '/ai-intelligent/projects'
  return '/configuration/projects'
}

const deleteProject = async () => {
  if (!project.value || deleting.value) return
  try {
    await ElMessageBox.confirm(
      t('project.deleteConfirmWithVersions', { name: project.value.name }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    deleting.value = true
    await api.delete(`/projects/${route.params.id}/`)
    ElMessage.success(t('project.deleteSuccess'))
    router.push(getProjectsListPath())
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || error.response?.data?.error || t('project.deleteFailed'))
    }
  } finally {
    deleting.value = false
  }
}

const saveProject = async () => {
  if (!editFormRef.value) return
  try {
    await editFormRef.value.validate()
    saving.value = true
    await api.put(`/projects/${route.params.id}/`, {
      name: editForm.name,
      description: editForm.description,
      status: editForm.status,
      project_types: editForm.project_types
    })
    ElMessage.success(t('project.updateSuccess'))
    isEditing.value = false
    fetchProject()
  } catch (error) {
    if (error.response?.data) {
      const errors = Object.values(error.response.data).flat()
      ElMessage.error(errors[0] || t('project.updateFailed'))
    } else if (error !== 'cancel') {
      ElMessage.error(t('project.updateFailed'))
    }
  } finally {
    saving.value = false
  }
}

const openEnvDialog = () => {
  envIsEdit.value = false
  editingEnvId.value = null
  envForm.name = ''
  envForm.base_url = ''
  envForm.description = ''
  envForm.is_default = false
  envDialogVisible.value = true
}

const openEditEnvDialog = (row) => {
  envIsEdit.value = true
  editingEnvId.value = row.id
  envForm.name = row.name || ''
  envForm.base_url = row.base_url || ''
  envForm.description = row.description || ''
  envForm.is_default = row.is_default || false
  envDialogVisible.value = true
}

const saveEnvironment = async () => {
  if (!envFormRef.value) return
  try {
    await envFormRef.value.validate()
    envSaving.value = true
    const payload = {
      name: envForm.name,
      base_url: envForm.base_url,
      description: envForm.description,
      is_default: envForm.is_default
    }
    if (envIsEdit.value) {
      await api.put(`/projects/${route.params.id}/environments/${editingEnvId.value}/`, payload)
      ElMessage.success(t('project.environmentUpdateSuccess'))
    } else {
      await api.post(`/projects/${route.params.id}/environments/`, payload)
      ElMessage.success(t('project.environmentAddSuccess'))
    }
    envDialogVisible.value = false
    fetchProject()
  } catch (error) {
    if (error.response?.data) {
      const errors = Object.values(error.response.data).flat()
      ElMessage.error(errors[0] || t('project.environmentSaveFailed'))
    } else if (error !== 'cancel') {
      ElMessage.error(t('project.environmentSaveFailed'))
    }
  } finally {
    envSaving.value = false
  }
}

const deleteEnvironment = async (row) => {
  try {
    await ElMessageBox.confirm(
      t('project.environmentDeleteConfirm'),
      t('common.confirm'),
      { type: 'warning' }
    )
    await api.delete(`/projects/${route.params.id}/environments/${row.id}/`)
    ElMessage.success(t('project.environmentDeleteSuccess'))
    fetchProject()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('project.environmentDeleteFailed'))
    }
  }
}

onMounted(() => {
  fetchProject()
})
</script>

<style lang="scss" scoped>
.info-header {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.module-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.no-modules {
  color: #909399;
}

.modules-section {
  margin-top: 24px;
  padding: 16px 18px;
  background: #f0f7ff;
  border: 1px solid #d6e8ff;
  border-radius: 10px;
}

.modules-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;

  .el-icon {
    color: #409eff;
  }
}

.module-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.module-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.module-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.module-card-body {
  flex: 1;
  min-width: 0;
}

.module-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.module-card-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.4;
}

.enter-module-btn {
  flex-shrink: 0;
  min-width: 78px;
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
}

.edit-project-form {
  max-width: 820px;
}

.project-type-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  width: 100%;
}

.project-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 8px 12px;
  border: 1.5px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;

  &:hover {
    border-color: #79bbff;
  }

  &.selected {
    border-color: #409eff;
    background: #ecf5ff;
  }

  .type-icon-wrap {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .type-card-title {
    font-size: 12px;
    font-weight: 500;
    color: #303133;
    text-align: center;
    min-height: 32px;
    display: flex;
    align-items: center;
  }
}

.environments-section {
  padding: 20px 0;
}

.env-header {
  display: flex;
  justify-content: flex-end;
}

@media screen and (max-width: 900px) {
  .project-type-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media screen and (max-width: 600px) {
  .project-type-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .module-card {
    flex-wrap: wrap;
  }
}
</style>
