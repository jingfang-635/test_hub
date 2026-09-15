<template>
  <div class="ai-model-config">
    <!-- 配置列表 -->
    <div class="configs-section">
      <div class="section-header">
        <div class="section-title">
          <h2>{{ $t('configuration.aiModel.configList') }}</h2>
          <span class="count-badge">{{ configs.length }}</span>
        </div>
        <div class="section-actions">
          <button
            class="add-config-btn"
            @click.stop="openAddModal"
            type="button">
            {{ $t('configuration.aiModel.addConfig') }}
          </button>
        </div>
      </div>

      <div v-if="configs.length" class="configs-grid">
        <template v-for="config in configs" :key="config?.id || 'unknown'">
          <article v-if="config && config.id" class="config-card">
            <div class="card-header">
              <h3 class="config-name" :title="configTitle(config)">
                {{ config.name || $t('configuration.common.unnamed') }}
                <template v-if="config.model_name">
                  <span class="name-sep">:</span>
                  <span class="name-model">{{ config.model_name }}</span>
                </template>
              </h3>
              <div class="badges">
                <span class="badge model-badge" :class="config.model_type">
                  {{ $t('configuration.aiModel.modelTypes.' + config.model_type) }}
                </span>
                <el-switch
                  class="status-switch"
                  :model-value="!!config.is_active"
                  :loading="togglingConfigId === config.id"
                  @change="toggleActive(config, $event)" />
              </div>
            </div>

            <div class="config-details">
              <div class="detail-item detail-span detail-inline">
                <label>{{ $t('configuration.aiModel.baseUrl') }}</label>
                <span class="detail-sep">：</span>
                <span class="detail-value" :title="config.base_url">{{ config.base_url }}</span>
              </div>

              <div v-if="multiList(config.role).length" class="detail-group detail-span">
                <label>{{ $t('configuration.aiModel.role') }}</label>
                <div class="tag-list">
                  <span v-for="rl in multiList(config.role)" :key="'role-' + rl" class="tag-pill tag-role">
                    {{ $t('configuration.aiModel.roles.' + rl) }}
                  </span>
                </div>
              </div>

              <div v-if="multiList(config.scenario).length" class="detail-group detail-span">
                <label>{{ $t('configuration.aiModel.scenario') }}</label>
                <div class="tag-list">
                  <span v-for="sc in multiList(config.scenario)" :key="'scenario-' + sc" class="tag-pill">
                    {{ $t('configuration.aiModel.scenarios.' + sc) }}
                  </span>
                </div>
              </div>
            </div>

            <div class="card-footer">
              <div class="footer-actions">
                <button
                  class="action-btn test-btn"
                  @click="testConnection(config)"
                  :disabled="isTestingConnection">
                  {{ $t('configuration.aiModel.testConnection') }}
                </button>
                <button class="action-btn" @click="editConfig(config)">{{ $t('configuration.common.edit') }}</button>
                <button class="action-btn danger" @click="deleteConfig(config.id)">{{ $t('configuration.common.delete') }}</button>
              </div>
            </div>
          </article>
        </template>
      </div>

      <div v-else class="empty-state">
        <h3>{{ $t('configuration.aiModel.emptyTitle') }}</h3>
        <button
          class="add-config-btn"
          @click.stop="openAddModal"
          type="button">
          {{ $t('configuration.aiModel.addFirstConfig') }}
        </button>
      </div>
    </div>

    <!-- 添加/编辑配置弹窗 -->
    <el-dialog
      :model-value="shouldShowModal"
      :title="isEditing ? $t('configuration.aiModel.editConfig') : $t('configuration.aiModel.addConfigTitle')"
      width="600px"
      :close-on-click-modal="false"
      @update:model-value="onModalVisibleChange">
      <el-form :model="configForm" label-width="110px" @submit.prevent="saveConfig">
        <el-form-item :label="$t('configuration.aiModel.configName')" required>
          <el-input
            v-model="configForm.name"
            :placeholder="$t('configuration.aiModel.configNamePlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.modelType')" required>
          <el-select
            v-model="configForm.model_type"
            style="width: 100%"
            :placeholder="$t('configuration.aiModel.selectModelType')"
            @change="onModelTypeChange(configForm.model_type)">
            <el-option :label="$t('configuration.aiModel.modelTypes.deepseek')" value="deepseek" />
            <el-option :label="$t('configuration.aiModel.modelTypes.qwen')" value="qwen" />
            <el-option :label="$t('configuration.aiModel.modelTypes.siliconflow')" value="siliconflow" />
            <el-option :label="$t('configuration.aiModel.modelTypes.zhipu')" value="zhipu" />
            <el-option :label="$t('configuration.aiModel.modelTypes.other')" value="other" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.modelName')" required>
          <el-input
            v-model="configForm.model_name"
            :placeholder="$t('configuration.aiModel.modelNamePlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.baseUrl')" required>
          <el-input
            v-model="configForm.base_url"
            :placeholder="$t('configuration.aiModel.baseUrlPlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.apiKey')" required>
          <el-input
            v-model="configForm.api_key"
            type="password"
            show-password
            :placeholder="isEditing ? $t('configuration.aiModel.apiKeyPlaceholderEdit') : $t('configuration.aiModel.apiKeyPlaceholder')" />
          <small
            v-if="isEditing && configForm.api_key && configForm.api_key.includes('*')"
            class="form-hint">
            {{ $t('configuration.aiModel.apiKeyMaskHint') }}
          </small>
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.role')" required>
          <el-checkbox-group v-model="configForm.roles">
            <el-checkbox
              v-for="roleOption in roleOptions"
              :key="roleOption"
              :label="roleOption">
              {{ $t('configuration.aiModel.roles.' + roleOption) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.scenario')" required>
          <el-checkbox-group v-model="configForm.scenarios">
            <el-checkbox
              v-for="scenarioOption in scenarioOptions"
              :key="scenarioOption"
              :label="scenarioOption">
              {{ $t('configuration.aiModel.scenarios.' + scenarioOption) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item :label="$t('configuration.aiModel.enableConfig')">
          <el-switch v-model="configForm.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeModals">{{ $t('configuration.common.cancel') }}</el-button>
        <el-button type="primary" :loading="isSaving" @click="saveConfig">
          {{ $t('configuration.aiModel.saveConfig') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 连接测试结果弹窗 -->
    <el-dialog
      v-model="showTestResult"
      :title="$t('configuration.aiModel.testResult')"
      width="520px"
      class="test-result-dialog"
      align-center>
      <div class="test-result" :class="{ success: testResult.success, error: !testResult.success }">
        <div class="result-banner">
          <div class="result-icon" aria-hidden="true">
            <svg v-if="testResult.success" viewBox="0 0 24 24" width="24" height="24">
              <path d="M20 6.5 9.5 17 4 11.5" fill="none" stroke="currentColor"
                stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="24" height="24">
              <path d="M18 6 6 18M6 6l12 12" fill="none" stroke="currentColor"
                stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="result-heading">
            <h4>{{ testResult.success ? $t('configuration.aiModel.connectionSuccess') : $t('configuration.aiModel.connectionFailed') }}</h4>
            <p class="result-message">
              {{ testResult.success
                ? $t('configuration.aiModel.connectionReply', { reply: testResult.response || testResult.message })
                : testResult.message }}
            </p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'

export default {
  name: 'AIModelConfig',
  setup() {
    const { t } = useI18n()
    return { t }
  },
  data() {
    return {
      configs: [], // 确保初始化为空数组
      showAddModal: false,
      showEditModal: false,
      showTestResult: false,
      isEditing: false,
      isSaving: false,
      isTestingConnection: false,
      testingConfigId: null,
      togglingConfigId: null,
      editingConfigId: null,
      configForm: {
        name: '',
        model_type: '',
        roles: [],
        scenarios: [],
        api_key: '',
        base_url: '',
        model_name: '',
        is_active: true
      },
      // 角色选项（文案取自 i18n: configuration.aiModel.roles.*）
      roleOptions: [
        'writer',
        'reviewer',
        'browser_use_text',
        'browser_use_vision',
        'code_generator',
        'test_oracle'
      ],
      // 场景选项（文案取自 i18n: configuration.aiModel.scenarios.*）
      scenarioOptions: [
        'testcase_generation',
        'ui_automation',
        'api_testing',
        'code_generation',
        'other'
      ],
      // 模型类型与API Base URL的映射关系
      modelBaseUrlMap: {
        deepseek: 'https://api.deepseek.com',
        qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        siliconflow: 'https://api.siliconflow.cn/v1',
        zhipu: 'https://open.bigmodel.cn/api/paas/v4',
        other: ''
      },
      testResult: {
        success: false,
        message: '',
        response: ''
      }
    }
  },

  computed: {
    shouldShowModal() {
      return this.showAddModal || this.showEditModal
    }
  },

  mounted() {
    // 确保组件初始状态正确
    this.initializeComponent()

    this.loadConfigs()
  },

  methods: {
    // 模板中用于渲染 role / scenario 多值标签
    multiList(value) {
      return this.normalizeMultiValue(value)
    },

    // 卡片标题：配置名称 + 模型名称
    configTitle(config) {
      const name = config.name || this.$t('configuration.common.unnamed')
      return config.model_name ? `${name}: ${config.model_name}` : name
    },

    /**
     * 卡片开关：启用/禁用配置。
     * 启用前校验「角色有交集 且 场景有交集」的活跃配置是否已存在（禁用时不校验）。
     */
    async toggleActive(config, value) {
      if (value) {
        const roles = this.normalizeMultiValue(config.role)
        const scenarios = this.normalizeMultiValue(config.scenario)
        const conflict = this.configs.find(other => {
          if (other.id === config.id || other.is_active !== true) return false
          const otherRoles = this.normalizeMultiValue(other.role)
          const otherScenarios = this.normalizeMultiValue(other.scenario)
          return otherRoles.some(r => roles.includes(r))
            && otherScenarios.some(sc => scenarios.includes(sc))
        })
        if (conflict) {
          ElMessage.error(this.t('configuration.aiModel.messages.duplicateConfig', { name: conflict.name }))
          return
        }
      }

      this.togglingConfigId = config.id
      const action = value ? 'enable' : 'disable'
      try {
        await api.post(`/requirement-analysis/ai-models/${config.id}/${action}/`)
        config.is_active = value
        ElMessage.success(this.t(value
          ? 'configuration.aiModel.messages.enableSuccess'
          : 'configuration.aiModel.messages.disableSuccess'))
      } catch (error) {
        console.error('Failed to toggle config:', error)
        ElMessage.error(this.t('configuration.aiModel.messages.toggleFailedDetail', {
          error: error.response?.data?.error || error.message
        }))
      } finally {
        this.togglingConfigId = null
      }
    },

    // 当模型类型改变时自动填充API Base URL
    onModelTypeChange(modelType) {
      // 根据选择的模型类型自动填充base_url
      if (this.modelBaseUrlMap[modelType]) {
        this.configForm.base_url = this.modelBaseUrlMap[modelType]
      }
    },

    // el-dialog 关闭（点击遮罩/关闭按钮）时同步内部状态
    onModalVisibleChange(visible) {
      if (!visible) {
        this.closeModals()
      }
    },

    initializeComponent() {
      // 强制重置所有状态
      this.showAddModal = false
      this.showEditModal = false
      this.showTestResult = false
      this.isEditing = false
      this.isSaving = false
      this.isTestingConnection = false
      this.testingConfigId = null
      this.editingConfigId = null
    },
    async loadConfigs() {
      try {
        console.log('Loading configs...')
        const response = await api.get('/requirement-analysis/ai-models/')
        console.log('API response:', response.data)
        
        // 处理分页API响应格式 {count: 1, next: null, previous: null, results: [...]}
        if (response.data && response.data.results && Array.isArray(response.data.results)) {
          this.configs = response.data.results.filter(config => config && config.id)
          console.log('Loaded configs from results:', this.configs)
        } else if (response.data && Array.isArray(response.data)) {
          // 直接数组格式的fallback
          this.configs = response.data.filter(config => config && config.id)
          console.log('Loaded configs from direct array:', this.configs)
        } else {
          console.warn('Unexpected API response format:', response.data)
          this.configs = []
        }
        
        console.log('Final configs count:', this.configs.length)
      } catch (error) {
        console.error('Failed to load configs:', error)
        this.configs = [] // 确保configs始终是数组

        if (error.response?.status === 401) {
          ElMessage.error(this.t('configuration.aiModel.messages.pleaseLogin'))
        } else {
          ElMessage.error(this.t('configuration.aiModel.messages.loadFailedDetail', { error: error.response?.data?.error || error.message }))
        }
      }
    },

    openAddModal() {
      this.resetForm()
      this.isEditing = false
      this.showAddModal = true
    },

    resetForm() {
      // 使用Object.assign确保响应式
      Object.assign(this.configForm, {
        name: '',
        model_type: '',
        roles: [],
        scenarios: [],
        api_key: '',
        base_url: '',
        model_name: '',
        is_active: true
      })
    },

    /**
     * 归一化多选值为数组，兼容历史单值字符串与逗号串
     * （role / scenario 均为多值字段）
     */
    normalizeMultiValue(value) {
      if (Array.isArray(value)) {
        return value.filter(Boolean)
      }
      if (typeof value === 'string' && value.trim()) {
        return value.split(',').map(s => s.trim()).filter(Boolean)
      }
      return []
    },

    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      this.configForm = {
        name: config.name,
        model_type: config.model_type,
        roles: this.normalizeMultiValue(config.role),
        scenarios: this.normalizeMultiValue(config.scenario),
        api_key: config.api_key_masked || '',
        base_url: config.base_url,
        model_name: config.model_name,
        // 以下参数不在弹窗中展示，编辑时保留原值
        max_tokens: config.max_tokens ?? 4096,
        temperature: config.temperature ?? 0.7,
        top_p: config.top_p ?? 0.9,
        is_active: config.is_active
      }
      this.showEditModal = true
    },
    async saveConfig() {
      console.log('Saving config with data:', this.configForm)

      // role / scenario 均为多选，各至少选择一个
      const roles = this.normalizeMultiValue(this.configForm.roles)
      const scenarios = this.normalizeMultiValue(this.configForm.scenarios)

      // 验证必填字段
      const requiredFields = [
        { name: 'name', value: this.configForm.name },
        { name: 'model_type', value: this.configForm.model_type },
        { name: 'role', value: roles.length ? 'selected' : '' },
        { name: 'scenario', value: scenarios.length ? 'selected' : '' },
        { name: 'api_key', value: this.configForm.api_key },
        { name: 'base_url', value: this.configForm.base_url },
        { name: 'model_name', value: this.configForm.model_name }
      ]
      const emptyFields = requiredFields.filter(field => !field.value || field.value.trim() === '')
      
      if (emptyFields.length > 0) {
        console.log('Empty fields:', emptyFields)
        ElMessage.error(this.t('configuration.aiModel.messages.fillRequired', { fields: emptyFields.map(f => f.name).join(', ') }))
        return
      }
      
      // 检查唯一约束冲突（仅在创建新配置且is_active为true时）
      // 约定：同一 (role, scenario) 组合只能有一个 active 配置，
      // 因此「角色有交集 且 场景有交集」即视为重复。
      if (!this.isEditing && this.configForm.is_active) {
        const existingConfig = this.configs.find(config => {
          if (config.is_active !== true) return false
          if (config.model_type !== this.configForm.model_type) return false
          const existingRoles = this.normalizeMultiValue(config.role)
          const existingScenarios = this.normalizeMultiValue(config.scenario)
          const roleOverlap = existingRoles.some(r => roles.includes(r))
          const scenarioOverlap = existingScenarios.some(sc => scenarios.includes(sc))
          return roleOverlap && scenarioOverlap
        })
        
        if (existingConfig) {
          ElMessage.error(this.t('configuration.aiModel.messages.duplicateConfig', { name: existingConfig.name }))
          return
        }
      }
      
      this.isSaving = true
      
      try {
        // 准备提交的数据
        const submitData = {
          name: this.configForm.name,
          model_type: this.configForm.model_type,
          role: roles,
          scenario: scenarios,
          api_key: this.configForm.api_key,
          base_url: this.configForm.base_url,
          model_name: this.configForm.model_name,
          is_active: this.configForm.is_active
        }
        
        if (this.isEditing) {
          // 编辑时，如果API Key是掩码格式或为空，则不更新它
          if (!submitData.api_key || submitData.api_key.includes('*')) {
            delete submitData.api_key
          }

          console.log('Updating with data:', submitData)
          await api.patch(`/requirement-analysis/ai-models/${this.editingConfigId}/`, submitData)
          ElMessage.success(this.$t('configuration.aiModel.messages.updateSuccess'))
        } else {
          console.log('Creating with data:', submitData)
          await api.post('/requirement-analysis/ai-models/', submitData)
          ElMessage.success(this.$t('configuration.aiModel.messages.saveSuccess'))
        }
        
        this.closeModals()
        
        // 等待模态框关闭后再刷新数据
        await this.$nextTick()
        await this.loadConfigs()
        
        // 强制重新渲染确保列表更新
        this.$forceUpdate()
        
        console.log('Config saved and list refreshed, total configs:', this.configs.length)
      } catch (error) {
        console.error('Failed to save config:', error)
        console.error('Error response:', error.response?.data)

        if (error.response?.data) {
          const errors = error.response.data
          let errorMessage = this.t('configuration.aiModel.messages.saveFailed') + ': '

          // 处理唯一约束错误
          if (errors.non_field_errors) {
            const uniqueConstraintError = errors.non_field_errors.find(err =>
              err.includes('唯一集合') || err.includes('unique')
            )
            if (uniqueConstraintError) {
              errorMessage = this.t('configuration.aiModel.messages.conflictError')
            } else {
              errorMessage += errors.non_field_errors.join(', ')
            }
          } else {
            // 处理字段特定错误
            Object.keys(errors).forEach(field => {
              if (Array.isArray(errors[field])) {
                errorMessage += `${field}: ${errors[field].join(', ')}; `
              } else {
                errorMessage += `${field}: ${errors[field]}; `
              }
            })
          }

          ElMessage.error(errorMessage)
        } else {
          ElMessage.error(this.t('configuration.aiModel.messages.saveFailedDetail', { error: error.message }))
        }
      } finally {
        this.isSaving = false
      }
    },

    async deleteConfig(configId) {
      try {
        await ElMessageBox.confirm(
          this.t('configuration.aiModel.messages.deleteConfirm'),
          this.t('configuration.aiModel.messages.deleteTitle'),
          {
            confirmButtonText: this.t('configuration.common.confirm'),
            cancelButtonText: this.t('configuration.common.cancel'),
            type: 'warning'
          }
        )
      } catch {
        return
      }

      try {
        await api.delete(`/requirement-analysis/ai-models/${configId}/`)
        ElMessage.success(this.t('configuration.aiModel.messages.deleteSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to delete config:', error)
        ElMessage.error(this.t('configuration.aiModel.messages.deleteFailedDetail', { error: error.response?.data?.error || error.message }))
      }
    },

    async testConnection(config) {
      this.isTestingConnection = true
      this.testingConfigId = config.id

      try {
        const response = await api.post(`/requirement-analysis/ai-models/${config.id}/test_connection/`)
        this.testResult = response.data
        this.showTestResult = true
      } catch (error) {
        console.error('Failed to test connection:', error)
        this.testResult = {
          success: false,
          message: error.response?.data?.message || error.message,
          response: ''
        }
        this.showTestResult = true
      } finally {
        this.isTestingConnection = false
        this.testingConfigId = null
      }
    },

    closeModals() {
      this.showAddModal = false
      this.showEditModal = false
      this.isEditing = false
      this.editingConfigId = null
      this.resetForm()
    }
  }
}
</script>

<style scoped>
.ai-model-config {
  padding: 20px 24px 32px;
  max-width: 1480px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--th-text-primary, #1f2937);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: var(--th-color-primary, #6c5ce7);
  font-size: 13px;
  font-weight: 600;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.add-config-btn {
  background: var(--th-color-primary, #6c5ce7);
  border: 1px solid var(--th-color-primary, #6c5ce7);
  color: #fff;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-config-btn:hover {
  filter: brightness(1.05);
}

.configs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px;
}

.config-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.config-card:hover {
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.config-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  line-height: 1.4;
  word-break: break-word;
}

.name-sep {
  color: #9ca3af;
  font-weight: 600;
}

.name-model {
  color: #6b7280;
  font-weight: 500;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.model-badge {
  background: #f3f4f6;
  color: #4b5563;
}

.model-badge.deepseek {
  background: #eef2ff;
  color: #4f46e5;
}

.model-badge.qwen {
  background: #f5f3ff;
  color: #7c3aed;
}

.model-badge.siliconflow {
  background: #ecfeff;
  color: #0e7490;
}

.model-badge.zhipu {
  background: #eff6ff;
  color: #1d4ed8;
}

.status-switch {
  flex-shrink: 0;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
}

.tag-pill.tag-role {
  background: #f4f2ff;
  color: var(--th-color-primary, #6c5ce7);
}

.config-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
  padding-top: 12px;
  border-top: 1px solid #f1f2f6;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.detail-span {
  grid-column: 1 / -1;
}

/* URL 行：字段名与值同行显示，中间以「：」分隔 */
.detail-inline {
  flex-direction: row;
  align-items: baseline;
  gap: 0;
}

.detail-inline label {
  flex-shrink: 0;
}

.detail-sep {
  flex-shrink: 0;
  color: #6b7280;
  font-size: 12px;
}

.detail-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.config-details label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.detail-value {
  color: #111827;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: auto;
  padding-top: 14px;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover:not(:disabled) {
  border-color: #9ca3af;
}

.action-btn.test-btn:hover:not(:disabled) {
  border-color: var(--th-color-primary, #6c5ce7);
  color: var(--th-color-primary, #6c5ce7);
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-btn.danger {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fff;
}

.action-btn.danger:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #f87171;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  background: #fff;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
}

.empty-state h3 {
  margin: 0 0 20px;
  color: #111827;
  font-size: 16px;
  font-weight: 600;
}

.form-hint {
  display: block;
  margin-top: 5px;
  color: #999;
  font-size: 0.85rem;
}

/* 连接测试结果弹窗（弹窗骨架见文件末尾全局样式） */
.test-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-banner {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px;
  border-radius: var(--th-radius-md, 12px);
  border: 1px solid var(--th-border, #e8ecf4);
  background: var(--th-bg-muted, #f7f8fc);
}

.test-result.success .result-banner {
  border-color: rgba(108, 92, 231, 0.3);
  background: linear-gradient(135deg, rgba(108, 92, 231, 0.14), rgba(108, 92, 231, 0.05));
}

.test-result.error .result-banner {
  border-color: rgba(239, 68, 68, 0.28);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.03));
}

.result-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: 12px;
  color: #fff;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
}

.test-result.success .result-icon {
  background: linear-gradient(135deg, var(--th-color-primary-light, #8b7cf0), var(--th-color-primary, #6c5ce7));
}

.test-result.error .result-icon {
  background: linear-gradient(135deg, #f87171, #ef4444);
}

.result-heading {
  min-width: 0;
}

.result-heading h4 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 650;
  color: var(--th-text-primary, #1f2937);
}

.test-result.success .result-heading h4 {
  color: var(--th-color-primary, #6c5ce7);
}

.test-result.error .result-heading h4 {
  color: #dc2626;
}

.result-message {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--th-text-secondary, #6b7280);
  word-break: break-word;
}

.test-result.success .result-message {
  color: var(--th-color-primary-dark, #5a4bd1);
}

/* 深色模式：选择器挂在弹窗类上，避免污染其它页面的同名类 */
:global(html.dark .test-result-dialog .test-result.success .result-heading h4) {
  color: var(--th-color-primary-light, #a99af5);
}

:global(html.dark .test-result-dialog .test-result.error .result-heading h4) {
  color: #f87171;
}

:global(html.dark .test-result-dialog .test-result.success .result-message) {
  color: var(--th-color-primary, #8b7cf0);
}

:global(html.dark .test-result-dialog .result-icon) {
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.35);
}

@media (max-width: 960px) {
  .configs-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .config-details {
    grid-template-columns: 1fr;
  }
}

:global(.is-dark) .config-card,
:global(.is-dark) .action-btn,
:global(.is-dark) .empty-state {
  background: var(--th-bg-elevated, #1f2430);
  border-color: var(--th-border, #2f3645);
  color: var(--th-text-primary, #e8ecf4);
}

:global(.is-dark) .config-name,
:global(.is-dark) .section-title h2,
:global(.is-dark) .detail-value,
:global(.is-dark) .empty-state h3 {
  color: var(--th-text-primary, #e8ecf4);
}

:global(.is-dark) .name-model {
  color: var(--th-text-secondary, #9aa3b2);
}

:global(.is-dark) .config-details label,
:global(.is-dark) .detail-sep {
  color: var(--th-text-secondary, #9aa3b2);
}

:global(.is-dark) .config-details {
  border-top-color: var(--th-border, #2f3645);
}

:global(.is-dark) .tag-pill {
  background: #2a3140;
  color: var(--th-text-secondary, #9aa3b2);
}

:global(.is-dark) .tag-pill.tag-role {
  background: rgba(139, 124, 240, 0.18);
  color: #a99af5;
}

:global(.is-dark) .model-badge {
  background: #2a3140;
  color: var(--th-text-secondary, #9aa3b2);
}

:global(.is-dark) .count-badge {
  background: rgba(108, 92, 231, 0.2);
}
</style>

<style>
/* 连接测试结果弹窗：弹窗骨架节点由 el-dialog 内部渲染，须用全局样式覆盖 */
.el-dialog.test-result-dialog {
  border-radius: var(--th-radius-lg, 16px);
  overflow: hidden;
  box-shadow: var(--th-shadow-lg, 0 16px 40px rgba(31, 41, 55, 0.1));
}

.el-dialog.test-result-dialog .el-dialog__header {
  margin-right: 0;
  padding: 18px 22px 16px;
  background: transparent;
  border-bottom: 1px solid var(--th-border, #e8ecf4);
}

.el-dialog.test-result-dialog .el-dialog__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--th-text-primary, #1f2937);
}

.el-dialog.test-result-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: var(--th-color-primary, #6c5ce7);
}

.el-dialog.test-result-dialog .el-dialog__body {
  padding: 20px 22px 24px;
}

html.dark .el-dialog.test-result-dialog .el-dialog__header {
  border-bottom-color: var(--th-border, #2a3142);
}

html.dark .el-dialog.test-result-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: var(--th-color-primary-light, #a99af5);
}
</style>
