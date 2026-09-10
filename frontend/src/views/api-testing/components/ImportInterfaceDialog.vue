<template>
  <el-dialog
    :model-value="modelValue"
    :title="$t('apiTesting.interface.importInterfaces')"
    width="720px"
    :close-on-click-modal="false"
    class="import-interface-dialog"
    destroy-on-close
    @update:model-value="onVisibleChange"
  >
    <!-- Step 1: 上传 -->
    <div v-if="step === 'upload'" class="import-step upload-step">
      <div class="form-row">
        <div class="form-label">{{ $t('apiTesting.interface.importFormat') }}</div>
        <div class="format-tabs">
          <button
            v-for="item in formatOptions"
            :key="item.value"
            type="button"
            class="format-tab"
            :class="{ active: format === item.value }"
            @click="onFormatChange(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>

      <div class="form-row">
        <div class="form-label">
          {{ format === 'curl' ? $t('apiTesting.interface.importContent') : $t('apiTesting.interface.importFile') }}
        </div>

        <el-input
          v-if="format === 'curl'"
          v-model="curlText"
          type="textarea"
          :rows="10"
          :placeholder="$t('apiTesting.interface.pasteCurlCommand')"
        />

        <el-upload
          v-else
          class="upload-area"
          drag
          :auto-upload="false"
          :show-file-list="false"
          :accept="acceptTypes"
          :on-change="onFileChange"
        >
          <div class="upload-inner">
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">{{ $t('apiTesting.interface.dragOrClickUpload') }}</div>
            <div v-if="selectedFileName" class="upload-filename">{{ selectedFileName }}</div>
          </div>
        </el-upload>
        <div class="upload-hint">{{ formatHint }}</div>
      </div>

      <div class="form-row">
        <div class="form-label">{{ $t('apiTesting.interface.targetProject') }}</div>
        <el-select v-model="targetHubProjectId" :placeholder="$t('apiTesting.common.selectProject')" style="width: 100%">
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
      </div>
    </div>

    <!-- Step 2: 预览勾选 -->
    <div v-else-if="step === 'preview'" class="import-step preview-step">
      <div class="preview-summary">
        <el-icon><InfoFilled /></el-icon>
        <span>{{ previewName }} - {{ $t('apiTesting.interface.totalInterfaces', { count: previewTotal }) }}</span>
      </div>

      <div class="preview-list">
        <div v-for="group in previewGroups" :key="group.name" class="preview-group">
          <div class="group-header">
            <el-checkbox
              :model-value="isGroupChecked(group)"
              :indeterminate="isGroupIndeterminate(group)"
              @change="(val) => toggleGroup(group, val)"
            >
              <span class="group-name">{{ group.name }}</span>
              <span class="group-count">{{ group.items.length }}</span>
            </el-checkbox>
          </div>
          <div class="group-items">
            <div v-for="item in group.items" :key="item.temp_id" class="preview-item">
              <el-checkbox
                :model-value="selectedIds.has(item.temp_id)"
                @change="(val) => toggleItem(item.temp_id, val)"
              >
                <span class="item-method" :class="(item.method || 'GET').toLowerCase()">{{ item.method }}</span>
                <span class="item-name">{{ item.name }}</span>
                <span class="item-url" :title="item.url">{{ item.url }}</span>
              </el-checkbox>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3: 成功 -->
    <div v-else class="import-step success-step">
      <div class="success-icon">
        <el-icon><CircleCheckFilled /></el-icon>
      </div>
      <div class="success-title">{{ $t('apiTesting.interface.importSuccess') }}</div>
      <div class="success-desc">
        {{ $t('apiTesting.interface.importSuccessDetail', { collections: result.collection_count, requests: result.request_count }) }}
      </div>
    </div>

    <template #footer>
      <el-button v-if="step === 'preview'" @click="step = 'upload'">{{ $t('apiTesting.common.cancel') }}</el-button>
      <el-button v-else @click="close">{{ $t('apiTesting.common.cancel') }}</el-button>
      <el-button v-if="step === 'upload'" type="primary" :loading="parsing" @click="parsePreview">
        {{ $t('apiTesting.interface.parsePreview') }}
      </el-button>
      <el-button v-else-if="step === 'preview'" type="primary" :loading="importing" @click="confirmImport">
        {{ $t('apiTesting.interface.confirmImport') }}
      </el-button>
      <el-button v-else type="primary" @click="finish">
        {{ $t('apiTesting.interface.finish') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, InfoFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projects: { type: Array, default: () => [] },
  /** 当前主项目（hub project）id */
  currentHubProjectId: { type: [Number, String], default: null },
})

const emit = defineEmits(['update:modelValue', 'imported'])

const { t } = useI18n()

const step = ref('upload') // upload | preview | success
const format = ref('postman')
const curlText = ref('')
const fileContent = ref('')
const selectedFileName = ref('')
const targetHubProjectId = ref(null)
const parsing = ref(false)
const importing = ref(false)

const previewName = ref('')
const previewGroups = ref([])
const previewTotal = ref(0)
const selectedIds = ref(new Set())
const result = ref({ collection_count: 0, request_count: 0 })

const formatOptions = computed(() => [
  { value: 'swagger', label: 'Swagger/OpenAPI' },
  { value: 'postman', label: 'Postman' },
  { value: 'curl', label: 'cURL' },
  { value: 'har', label: 'HAR' },
])

const acceptTypes = computed(() => {
  if (format.value === 'swagger') return '.json,.yaml,.yml,application/json,text/yaml'
  if (format.value === 'har') return '.har,.json,application/json'
  return '.json,application/json'
})

const formatHint = computed(() => {
  const map = {
    swagger: 'Swagger / OpenAPI (JSON / YAML)',
    postman: 'Postman Collection v2.1 (JSON)',
    curl: 'cURL Command',
    har: 'HTTP Archive (HAR)',
  }
  return map[format.value] || ''
})

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      resetState()
      targetHubProjectId.value = props.currentHubProjectId
    }
  }
)

const resetState = () => {
  step.value = 'upload'
  format.value = 'postman'
  curlText.value = ''
  fileContent.value = ''
  selectedFileName.value = ''
  parsing.value = false
  importing.value = false
  previewName.value = ''
  previewGroups.value = []
  previewTotal.value = 0
  selectedIds.value = new Set()
  result.value = { collection_count: 0, request_count: 0 }
}

const resolveApiProjectId = async (hubProjectId) => {
  const response = await api.post('/api-testing/projects/ensure/', {
    hub_project_id: hubProjectId,
  })
  return response.data?.id
}

const onVisibleChange = (val) => {
  emit('update:modelValue', val)
}

const close = () => {
  emit('update:modelValue', false)
}

const onFormatChange = (val) => {
  format.value = val
  fileContent.value = ''
  selectedFileName.value = ''
  curlText.value = ''
}

const onFileChange = (uploadFile) => {
  const raw = uploadFile?.raw
  if (!raw) return
  selectedFileName.value = raw.name
  const reader = new FileReader()
  reader.onload = () => {
    fileContent.value = String(reader.result || '')
  }
  reader.onerror = () => {
    ElMessage.error(t('apiTesting.interface.readFileFailed'))
  }
  reader.readAsText(raw)
}

const parsePreview = async () => {
  if (!targetHubProjectId.value) {
    ElMessage.warning(t('apiTesting.common.selectProject'))
    return
  }
  const content = format.value === 'curl' ? curlText.value : fileContent.value
  if (!content || !String(content).trim()) {
    ElMessage.warning(
      format.value === 'curl'
        ? t('apiTesting.interface.pasteCurlCommand')
        : t('apiTesting.interface.pleaseUploadFile')
    )
    return
  }

  try {
    parsing.value = true
    // 提前确保目标项目可用
    await resolveApiProjectId(targetHubProjectId.value)
    const response = await api.post('/api-testing/requests/parse-import/', {
      format: format.value,
      content,
    })
    const data = response.data || {}
    previewName.value = data.name || t('apiTesting.interface.importInterfaces')
    previewGroups.value = data.groups || []
    previewTotal.value = data.total || 0

    const ids = new Set()
    previewGroups.value.forEach((g) => {
      ;(g.items || []).forEach((item) => ids.add(item.temp_id))
    })
    selectedIds.value = ids

    if (!previewTotal.value) {
      ElMessage.warning(t('apiTesting.interface.noInterfaceParsed'))
      return
    }
    step.value = 'preview'
  } catch (error) {
    const msg = error?.response?.data?.detail || t('apiTesting.interface.parseFailed')
    ElMessage.error(msg)
  } finally {
    parsing.value = false
  }
}

const isGroupChecked = (group) => {
  const items = group.items || []
  return items.length > 0 && items.every((item) => selectedIds.value.has(item.temp_id))
}

const isGroupIndeterminate = (group) => {
  const items = group.items || []
  const selected = items.filter((item) => selectedIds.value.has(item.temp_id)).length
  return selected > 0 && selected < items.length
}

const toggleGroup = (group, checked) => {
  const next = new Set(selectedIds.value)
  ;(group.items || []).forEach((item) => {
    if (checked) next.add(item.temp_id)
    else next.delete(item.temp_id)
  })
  selectedIds.value = next
}

const toggleItem = (tempId, checked) => {
  const next = new Set(selectedIds.value)
  if (checked) next.add(tempId)
  else next.delete(tempId)
  selectedIds.value = next
}

const confirmImport = async () => {
  if (!targetHubProjectId.value) {
    ElMessage.warning(t('apiTesting.common.selectProject'))
    return
  }
  const groups = []
  previewGroups.value.forEach((group) => {
    const items = (group.items || []).filter((item) => selectedIds.value.has(item.temp_id))
    if (items.length) {
      groups.push({ name: group.name, items })
    }
  })
  if (!groups.length) {
    ElMessage.warning(t('apiTesting.interface.pleaseSelectInterfaces'))
    return
  }

  try {
    importing.value = true
    const apiProjectId = await resolveApiProjectId(targetHubProjectId.value)
    const response = await api.post('/api-testing/requests/bulk-import/', {
      project_id: apiProjectId,
      groups,
    })
    result.value = {
      collection_count: response.data?.collection_count || 0,
      request_count: response.data?.request_count || 0,
      hubProjectId: targetHubProjectId.value,
      apiProjectId,
    }
    step.value = 'success'
  } catch (error) {
    const msg = error?.response?.data?.detail || t('apiTesting.interface.importFailed')
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

const finish = () => {
  emit('imported', { ...result.value })
  emit('update:modelValue', false)
}
</script>

<style scoped>
.import-step {
  min-height: 320px;
}

.form-row {
  margin-bottom: 20px;
}

.form-label {
  font-size: 14px;
  color: #303133;
  margin-bottom: 10px;
  font-weight: 500;
}

.format-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  width: fit-content;
  max-width: 100%;
}

.format-tab {
  border: none;
  background: #fff;
  color: #606266;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  border-right: 1px solid #dcdfe6;
  transition: all 0.2s ease;
}

.format-tab:last-child {
  border-right: none;
}

.format-tab:hover {
  color: var(--el-color-primary);
}

.format-tab.active {
  background: var(--el-color-primary);
  color: #fff;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 36px 20px;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  background: #fafafa;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
}

.upload-text {
  color: #606266;
  font-size: 14px;
}

.upload-filename {
  color: var(--el-color-primary);
  font-size: 13px;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.preview-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f5f7fa;
  border-radius: 6px;
  color: #606266;
  font-size: 13px;
  margin-bottom: 12px;
}

.preview-list {
  max-height: 420px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.preview-group + .preview-group {
  border-top: 1px solid #ebeef5;
}

.group-header {
  padding: 8px 12px;
  background: #eef3ff;
}

.group-name {
  font-weight: 600;
  color: #303133;
  margin-right: 8px;
}

.group-count {
  display: inline-block;
  min-width: 18px;
  padding: 0 6px;
  height: 18px;
  line-height: 18px;
  border-radius: 9px;
  background: #d9e4ff;
  color: #3a6ff7;
  font-size: 12px;
  text-align: center;
}

.group-items {
  background: #fff;
}

.preview-item {
  padding: 8px 12px 8px 28px;
  border-top: 1px solid #f2f3f5;
}

.preview-item :deep(.el-checkbox__label) {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: calc(100% - 20px);
  vertical-align: middle;
}

.item-method {
  display: inline-block;
  min-width: 48px;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
  padding: 2px 6px;
  color: #fff;
  flex-shrink: 0;
}

.item-method.get { background: #61affe; }
.item-method.post { background: #e6a23c; }
.item-method.put { background: #fca130; }
.item-method.delete { background: #f93e3e; }
.item-method.patch { background: #50e3c2; }
.item-method.head { background: #9013fe; }
.item-method.options { background: #0ebeff; }

.item-name {
  color: #3a6ff7;
  font-size: 13px;
  flex-shrink: 0;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-url {
  color: #909399;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.success-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
}

.success-icon {
  font-size: 72px;
  color: #67c23a;
  line-height: 1;
  margin-bottom: 16px;
}

.success-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.success-desc {
  font-size: 14px;
  color: #909399;
}
</style>
