<template>
  <div class="kb-llm-config">
    <div class="page-header">
      <h1>{{ $t('configuration.knowledgeLLM.title') }}</h1>
      <p>{{ $t('configuration.knowledgeLLM.description') }}</p>
    </div>

    <div class="config-layout">
      <el-card class="config-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>{{ $t('configuration.knowledgeLLM.apiConfig') }}</span>
            <el-tag v-if="currentConfig" type="success" size="small">
              {{ $t('configuration.common.configured') }}
            </el-tag>
            <el-tag v-else type="info" size="small">
              {{ $t('configuration.common.notConfigured') }}
            </el-tag>
          </div>
        </template>

        <el-form
          ref="configFormRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="config-form"
          v-loading="loading"
        >
          <!-- Embedding -->
          <div class="form-section">
            <h3 class="section-title">
              {{ $t('configuration.knowledgeLLM.embeddingTitle') }}
            </h3>
            <p class="section-tip">{{ $t('configuration.knowledgeLLM.bailianOnlyTip') }}</p>
            <el-form-item label="API Key" prop="embedding_api_key">
              <el-input
                v-model="form.embedding_api_key"
                type="password"
                show-password
                clearable
                autocomplete="off"
                :placeholder="apiKeyPlaceholder"
              />
            </el-form-item>
            <el-form-item :label="$t('configuration.knowledgeLLM.baseUrl')" prop="embedding_base_url">
              <el-input v-model="form.embedding_base_url" clearable />
            </el-form-item>
            <el-form-item :label="$t('configuration.knowledgeLLM.modelName')" prop="embedding_model_name">
              <el-input
                v-model="form.embedding_model_name"
                clearable
                :placeholder="$t('configuration.knowledgeLLM.embeddingModelPlaceholder')"
              />
            </el-form-item>
          </div>

          <el-divider />

          <!-- Refiner -->
          <div class="form-section">
            <h3 class="section-title">
              {{ $t('configuration.knowledgeLLM.refinerTitle') }}
            </h3>
            <p class="section-tip">{{ $t('configuration.knowledgeLLM.bailianOnlyTip') }}</p>
            <el-form-item label="API Key" prop="refiner_api_key">
              <el-input
                v-model="form.refiner_api_key"
                type="password"
                show-password
                clearable
                autocomplete="off"
                :placeholder="apiKeyPlaceholder"
              />
            </el-form-item>
            <el-form-item :label="$t('configuration.knowledgeLLM.baseUrl')" prop="refiner_base_url">
              <el-input v-model="form.refiner_base_url" clearable />
            </el-form-item>
            <el-form-item :label="$t('configuration.knowledgeLLM.modelName')" prop="refiner_model_name">
              <el-input
                v-model="form.refiner_model_name"
                clearable
                :placeholder="$t('configuration.knowledgeLLM.refinerModelPlaceholder')"
              />
            </el-form-item>
            <div class="inline-fields">
              <el-form-item
                :label="$t('configuration.knowledgeLLM.maxTokens')"
                prop="refiner_max_tokens"
                class="inline-field"
              >
                <el-input-number
                  v-model="form.refiner_max_tokens"
                  :min="256"
                  :max="128000"
                  :step="256"
                  controls-position="right"
                />
              </el-form-item>
              <el-form-item
                :label="$t('configuration.knowledgeLLM.temperature')"
                prop="refiner_temperature"
                class="inline-field temperature-field"
              >
                <div class="temperature-control">
                  <el-slider
                    v-model="form.refiner_temperature"
                    :min="0"
                    :max="2"
                    :step="0.1"
                    :show-tooltip="true"
                  />
                  <el-input-number
                    v-model="form.refiner_temperature"
                    :min="0"
                    :max="2"
                    :step="0.1"
                    :precision="1"
                    controls-position="right"
                    class="temperature-input"
                  />
                </div>
              </el-form-item>
            </div>
          </div>

          <el-divider />

          <!-- Vision -->
          <div class="form-section">
            <h3 class="section-title">
              {{ $t('configuration.knowledgeLLM.visionTitle') }}
            </h3>
            <el-alert
              type="info"
              :closable="false"
              show-icon
              class="section-alert"
              :title="$t('configuration.knowledgeLLM.visionTip')"
            />
            <el-form-item :label="$t('configuration.knowledgeLLM.provider')" prop="vision_provider">
              <el-radio-group v-model="form.vision_provider" @change="onVisionProviderChange">
                <el-radio value="zhipu">
                  {{ $t('configuration.knowledgeLLM.providers.zhipu') }}
                </el-radio>
                <el-radio value="openai_compatible">
                  {{ $t('configuration.knowledgeLLM.providers.openai_compatible') }}
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="API Key" prop="vision_api_key">
              <el-input
                v-model="form.vision_api_key"
                type="password"
                show-password
                clearable
                autocomplete="off"
                :placeholder="apiKeyPlaceholder"
              />
            </el-form-item>
            <el-form-item
              v-if="form.vision_provider === 'openai_compatible'"
              :label="$t('configuration.knowledgeLLM.baseUrl')"
              prop="vision_base_url"
            >
              <el-input
                v-model="form.vision_base_url"
                clearable
                :placeholder="$t('configuration.knowledgeLLM.visionBaseUrlPlaceholder')"
              />
            </el-form-item>
            <el-form-item :label="$t('configuration.knowledgeLLM.modelName')" prop="vision_model_name">
              <el-input
                v-model="form.vision_model_name"
                clearable
                :placeholder="$t('configuration.knowledgeLLM.visionModelPlaceholder')"
              />
              <div class="form-tip">
                {{ $t('configuration.knowledgeLLM.visionModelHint') }}
              </div>
            </el-form-item>
          </div>

          <el-form-item class="form-actions">
            <el-button type="primary" native-type="button" :loading="saving" @click="saveConfig">
              {{ $t('configuration.common.save') }}
            </el-button>
            <el-button native-type="button" @click="resetForm">
              {{ $t('configuration.common.reset') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="info-card" shadow="never" v-if="currentConfig">
        <template #header>
          <span>{{ $t('configuration.knowledgeLLM.currentConfig') }}</span>
        </template>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item :label="$t('configuration.knowledgeLLM.embeddingApiKey')">
            {{ currentConfig.embedding_api_key_masked || '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.knowledgeLLM.refinerApiKey')">
            {{ currentConfig.refiner_api_key_masked || '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.knowledgeLLM.visionApiKey')">
            {{ currentConfig.vision_api_key_masked || '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.createdAt')">
            {{ formatDate(currentConfig.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.updatedAt')">
            {{ formatDate(currentConfig.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  getKnowledgeLLMConfig,
  createKnowledgeLLMConfig,
  updateKnowledgeLLMConfig
} from '@/api/requirement-analysis'

const DASHSCOPE_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
const ZHIPU_BASE_URL = 'https://open.bigmodel.cn/api/paas/v4'

const { t, locale } = useI18n()

const configFormRef = ref(null)
const currentConfig = ref(null)
const loading = ref(false)
const saving = ref(false)

const form = reactive({
  embedding_api_key: '',
  embedding_base_url: DASHSCOPE_BASE_URL,
  embedding_model_name: 'text-embedding-v3',
  refiner_api_key: '',
  refiner_base_url: DASHSCOPE_BASE_URL,
  refiner_model_name: 'qwen-plus',
  refiner_max_tokens: 8192,
  refiner_temperature: 0.3,
  vision_provider: 'openai_compatible',
  vision_api_key: '',
  vision_base_url: ZHIPU_BASE_URL,
  vision_model_name: 'glm-4.6v'
})

const apiKeyPlaceholder = computed(() => t('configuration.knowledgeLLM.apiKeyPlaceholder'))

const rules = computed(() => ({
  embedding_base_url: [
    { required: true, message: t('configuration.knowledgeLLM.validation.baseUrlRequired'), trigger: 'blur' }
  ],
  embedding_model_name: [
    { required: true, message: t('configuration.knowledgeLLM.validation.modelNameRequired'), trigger: 'blur' }
  ],
  refiner_base_url: [
    { required: true, message: t('configuration.knowledgeLLM.validation.baseUrlRequired'), trigger: 'blur' }
  ],
  refiner_model_name: [
    { required: true, message: t('configuration.knowledgeLLM.validation.modelNameRequired'), trigger: 'blur' }
  ],
  vision_provider: [
    { required: true, message: t('configuration.knowledgeLLM.validation.providerRequired'), trigger: 'change' }
  ],
  vision_base_url: [
    {
      validator: (_rule, value, callback) => {
        if (form.vision_provider === 'openai_compatible' && !value) {
          callback(new Error(t('configuration.knowledgeLLM.validation.baseUrlRequired')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  vision_model_name: [
    { required: true, message: t('configuration.knowledgeLLM.validation.modelNameRequired'), trigger: 'blur' }
  ]
}))

const formatDate = (dateString) => {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleString(locale.value === 'zh-cn' ? 'zh-CN' : 'en-US')
}

const formatApiError = (error) => {
  const data = error?.response?.data
  if (!data) return t('configuration.knowledgeLLM.messages.saveFailed')
  if (typeof data === 'string') return data
  if (data.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
  if (data.error) return data.error
  if (data.message) return data.message
  const parts = Object.entries(data)
    .map(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join('; ') : String(messages)
      return `${field}: ${text}`
    })
  return parts.length ? parts.join(' | ') : t('configuration.knowledgeLLM.messages.saveFailed')
}

const assignForm = (data = {}) => {
  // 回填完整 Key，密码框点「显示」可查看明文；右侧信息区仍用掩码字段
  form.embedding_api_key = data.embedding_api_key || ''
  form.embedding_base_url = data.embedding_base_url || DASHSCOPE_BASE_URL
  form.embedding_model_name = data.embedding_model_name || 'text-embedding-v3'
  form.refiner_api_key = data.refiner_api_key || ''
  form.refiner_base_url = data.refiner_base_url || DASHSCOPE_BASE_URL
  form.refiner_model_name = data.refiner_model_name || 'qwen-plus'
  form.refiner_max_tokens = data.refiner_max_tokens ?? 8192
  form.refiner_temperature = data.refiner_temperature ?? 0.3
  form.vision_provider = data.vision_provider || 'openai_compatible'
  form.vision_api_key = data.vision_api_key || ''
  form.vision_base_url = data.vision_base_url || ZHIPU_BASE_URL
  form.vision_model_name = data.vision_model_name || 'glm-4.6v'
}

const resetFormToDefault = () => {
  assignForm({})
  form.embedding_api_key = ''
  form.refiner_api_key = ''
  form.vision_api_key = ''
}

const loadConfig = async () => {
  loading.value = true
  try {
    const response = await getKnowledgeLLMConfig()
    currentConfig.value = response.data
    assignForm(response.data)
  } catch (error) {
    if (error.response?.status !== 404) {
      console.error(t('configuration.knowledgeLLM.messages.loadFailed'), error)
      ElMessage.error(t('configuration.knowledgeLLM.messages.loadFailed'))
    } else {
      currentConfig.value = null
      resetFormToDefault()
    }
  } finally {
    loading.value = false
  }
}

const onVisionProviderChange = (provider) => {
  if (provider === 'zhipu') {
    if (!form.vision_model_name) form.vision_model_name = 'glm-4.6v'
  } else if (provider === 'openai_compatible') {
    if (!form.vision_base_url) form.vision_base_url = ZHIPU_BASE_URL
    if (!form.vision_model_name) form.vision_model_name = 'glm-4.6v'
  }
}

const buildPayload = () => {
  const payload = {
    embedding_base_url: (form.embedding_base_url || '').trim(),
    embedding_model_name: (form.embedding_model_name || '').trim(),
    refiner_base_url: (form.refiner_base_url || '').trim(),
    refiner_model_name: (form.refiner_model_name || '').trim(),
    refiner_max_tokens: Number(form.refiner_max_tokens) || 8192,
    refiner_temperature: Number(form.refiner_temperature) || 0,
    vision_provider: form.vision_provider,
    vision_base_url: (form.vision_base_url || '').trim() || ZHIPU_BASE_URL,
    vision_model_name: (form.vision_model_name || '').trim()
  }

  // 有值则提交；留空则后端保留原 Key
  if (form.embedding_api_key?.trim()) {
    payload.embedding_api_key = form.embedding_api_key.trim()
  }
  if (form.refiner_api_key?.trim()) {
    payload.refiner_api_key = form.refiner_api_key.trim()
  }
  if (form.vision_api_key?.trim()) {
    payload.vision_api_key = form.vision_api_key.trim()
  }

  return payload
}

const saveConfig = async () => {
  if (!configFormRef.value || saving.value) return

  try {
    await configFormRef.value.validate()
  } catch {
    ElMessage.warning(t('configuration.knowledgeLLM.messages.validationFailed'))
    return
  }

  const payload = buildPayload()
  const isCreate = !currentConfig.value?.id

  if (isCreate) {
    const missingKeys = []
    if (!payload.embedding_api_key) missingKeys.push('Embedding')
    if (!payload.refiner_api_key) missingKeys.push('Refiner')
    if (!payload.vision_api_key) missingKeys.push('Vision')
    if (missingKeys.length) {
      ElMessage.error(t('configuration.knowledgeLLM.messages.apiKeyRequired', {
        keys: missingKeys.join(' / ')
      }))
      return
    }
  }

  saving.value = true
  try {
    let response
    if (currentConfig.value?.id) {
      response = await updateKnowledgeLLMConfig(currentConfig.value.id, payload)
      ElMessage.success(t('configuration.knowledgeLLM.messages.updateSuccess'))
    } else {
      response = await createKnowledgeLLMConfig(payload)
      ElMessage.success(t('configuration.knowledgeLLM.messages.saveSuccess'))
    }

    // 优先用保存响应回填完整 Key
    if (response?.data?.id) {
      currentConfig.value = response.data
      assignForm(response.data)
    } else {
      await loadConfig()
    }
  } catch (error) {
    console.error(t('configuration.knowledgeLLM.messages.saveFailed'), error)
    ElMessage.error(formatApiError(error))
  } finally {
    saving.value = false
  }
}

const resetForm = () => {
  if (currentConfig.value) {
    assignForm(currentConfig.value)
  } else {
    resetFormToDefault()
  }
  configFormRef.value?.clearValidate()
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped lang="scss">
.kb-llm-config {
  padding: 20px 24px 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 28px;

  h1 {
    font-size: 1.75rem;
    color: #1f2d3d;
    margin: 0 0 10px;
    font-weight: 600;
  }

  p {
    color: #909399;
    font-size: 0.95rem;
    margin: 0;
  }
}

.config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: start;
}

.config-card,
.info-card {
  border-radius: 8px;

  :deep(.el-card__header) {
    padding: 14px 20px;
    border-bottom: 1px solid #ebeef5;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.config-form {
  padding: 4px 4px 0;
}

.form-section {
  margin-bottom: 8px;
}

.section-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.section-tip {
  margin: 0 0 14px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.section-alert {
  margin-bottom: 16px;

  :deep(.el-alert__title) {
    font-size: 13px;
    line-height: 1.5;
  }
}

.inline-fields {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 24px;
}

.temperature-control {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;

  .el-slider {
    flex: 1;
  }

  .temperature-input {
    width: 120px;
  }
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.form-actions {
  margin-top: 8px;
  margin-bottom: 0;
}

@media (max-width: 960px) {
  .config-layout {
    grid-template-columns: 1fr;
  }

  .inline-fields {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
