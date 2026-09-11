<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('testcase.detail') }}</h1>
      <div>
        <el-button @click="$router.back()">{{ $t('common.back') }}</el-button>
      </div>
    </div>

    <div class="card-container" v-if="testcase">
      <el-tabs v-model="activeTab">
        <!-- 基础信息 ↔ 手工(manual)；UI自动化 ↔ UI；接口自动化 ↔ 接口(api) -->
        <el-tab-pane v-if="caseTypes.includes('manual')" :label="$t('testcase.tabBasic')" name="basic">
          <div class="detail-actions">
            <el-button type="primary" @click="editTestCase">{{ $t('common.edit') }}</el-button>
            <el-button type="danger" @click="deleteTestCase">{{ $t('common.delete') }}</el-button>
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="$t('testcase.caseTitle')" :span="2">{{ testcase.title }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.priority')">
              <el-tag :class="`priority-tag ${testcase.priority}`">{{ getPriorityText(testcase.priority) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.testType')">{{ getTypeText(testcase.test_type) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.caseType')">{{ getCaseTypeText(testcase.case_type) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.project')">{{ testcase.project?.name || $t('testcase.noProject') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.relatedVersions')" :span="2">
              <div v-if="testcase.versions && testcase.versions.length > 0" class="version-tags">
                <el-tag
                  v-for="version in testcase.versions"
                  :key="version.id"
                  size="small"
                  :type="version.is_baseline ? 'warning' : 'info'"
                  class="version-tag"
                >
                  {{ version.name }}
                </el-tag>
              </div>
              <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.author')">{{ testcase.author?.username }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.createdAt')" :span="2">{{ formatDate(testcase.created_at) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l1')">{{ testcase.l1 || $t('testcase.none') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l2')">{{ testcase.l2 || $t('testcase.none') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l3')" :span="2">{{ testcase.l3 || $t('testcase.none') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.caseDescription')" :span="2">{{ testcase.description || $t('testcase.noDescription') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.preconditions')" :span="2">
              <div v-html="testcase.preconditions || $t('testcase.none')"></div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.steps')" :span="2">
              <div class="steps-content" v-html="testcase.steps || $t('testcase.none')"></div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.expectedResult')" :span="2">
              <div v-html="testcase.expected_result || $t('testcase.none')"></div>
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane v-if="caseTypes.includes('ui')" :label="$t('testcase.tabUi')" name="ui">
          <div v-if="uiDetailSteps.length > 0" class="ui-steps">
            <UiAutomationStepsReadonly :steps="uiDetailSteps">
              <template #actions>
                <el-button size="small" type="primary" @click="editUiAutomationCase">{{ $t('testcase.edit') }}</el-button>
                <el-button size="small" type="success" :loading="aiGenerating" @click="handleAiGenerateSteps('ui')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
              </template>
            </UiAutomationStepsReadonly>
          </div>
          <template v-else>
            <div class="tab-actions">
              <el-button size="small" type="primary" @click="editUiAutomationCase">{{ $t('testcase.edit') }}</el-button>
              <el-button size="small" type="success" :loading="aiGenerating" @click="handleAiGenerateSteps('ui')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
            </div>
            <el-empty :description="$t('testcase.tabEmpty')" />
          </template>
          <div v-if="uiDetailSteps.length > 0" class="tab-updated-at">{{ $t('testcase.updatedAt') }}：{{ formatUpdatedAt(testcase.updated_at) }}</div>
        </el-tab-pane>
        <el-tab-pane v-if="caseTypes.includes('api')" :label="$t('testcase.tabApi')" name="api">
          <div class="tab-actions">
            <el-button size="small" type="primary" @click="editTestCase">{{ $t('testcase.edit') }}</el-button>
            <el-button size="small" type="success" :loading="aiGenerating" @click="handleAiGenerateSteps('api')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
          </div>
          <el-empty :description="$t('testcase.tabEmpty')" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'
import UiAutomationStepsReadonly from '@/components/UiAutomationStepsReadonly.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const testcase = ref(null)
const activeTab = ref('basic')
const aiGenerating = ref(false)

// 从测试用例的 case_type 解析出勾选的用例类型列表（手工 manual / UI ui / 接口 api）
const caseTypes = computed(() => {
  const raw = testcase.value?.case_type
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string' && raw.trim()) {
    return raw.split(/[,，、;；]/).map(v => v.trim()).filter(Boolean)
  }
  return []
})

// 按已选类型决定默认激活的 Tab：基础信息↔manual，UI自动化↔ui，接口自动化↔api
const resolveDefaultTab = (types) => {
  if (types.includes('manual')) return 'basic'
  if (types.includes('ui')) return 'ui'
  if (types.includes('api')) return 'api'
  return 'basic'
}

// 关联的 UI自动化用例步骤（只读）
const uiDetailSteps = ref([])
const uiCaseId = ref(null)

// 拉取结构化步骤详情（无 UI 自动化数据时静默忽略）
const fetchUiDetailSteps = async () => {
  if (!route.params.id) return
  try {
    const response = await api.get(`/testcases/${route.params.id}/ui_step_details/`)
    uiDetailSteps.value = response.data?.steps || []
    uiCaseId.value = response.data?.ui_case_id || null
  } catch (error) {
    uiDetailSteps.value = []
    uiCaseId.value = null
  }
}

const fetchTestCase = async () => {
  try {
    const response = await api.get(`/testcases/${route.params.id}/`)
    testcase.value = response.data
    activeTab.value = resolveDefaultTab(caseTypes.value)
    fetchUiDetailSteps()
  } catch (error) {
    ElMessage.error(t('testcase.fetchDetailFailed'))
  }
}

const editTestCase = () => {
  router.push(`/ai-generation/testcases/${route.params.id}/edit`)
}

// UI自动化 Tab：跳转到用例管理并展开关联用例
const editUiAutomationCase = () => {
  const query = {}
  if (uiCaseId.value) query.id = uiCaseId.value
  router.push({ path: '/ui-automation/test-cases', query })
}

const deleteTestCase = async () => {
  if (!testcase.value) return
  try {
    await ElMessageBox.confirm(t('testcase.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    await api.delete(`/testcases/${route.params.id}/`)
    ElMessage.success(t('testcase.deleteSuccess'))
    router.push('/ai-generation/testcases')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('testcase.deleteFailed'))
    }
  }
}

// 将当前用例解析为 AI 任务描述
const buildTaskDescription = () => {
  const parts = []
  if (testcase.value?.title) parts.push(`测试用例：${testcase.value.title}`)
  if (testcase.value?.description) parts.push(`用例描述：${testcase.value.description}`)
  if (testcase.value?.preconditions) parts.push(`前置条件：${testcase.value.preconditions}`)
  if (testcase.value?.steps) parts.push(`操作步骤：\n${testcase.value.steps}`)
  if (testcase.value?.expected_result) parts.push(`预期结果：${testcase.value.expected_result}`)
  return parts.join('\n')
}

const confirmReuseAuth = async () => {
  try {
    await ElMessageBox.confirm(
      t('testcase.aiGenerateStepsReuseAuthHint'),
      t('testcase.aiGenerateStepsReuseAuthTitle'),
      {
        confirmButtonText: t('testcase.aiGenerateStepsReuseAuthYes'),
        cancelButtonText: t('testcase.aiGenerateStepsReuseAuthNo'),
        distinguishCancelAndClose: true,
        dangerouslyUseHTMLString: true,
        type: 'info',
      }
    )
    return true
  } catch (action) {
    if (action === 'cancel') return false
    return null // close / Esc：中止
  }
}

const handleAiGenerateSteps = async (target = 'ui') => {
  if (target === 'api') {
    ElMessage.info(t('testcase.aiGenerateStepsTodo'))
    return
  }

  // UI 自动化：弹窗确认是否复用登录态
  const autoLogin = await confirmReuseAuth()
  if (autoLogin === null) return

  aiGenerating.value = true
  try {
    // 校验是否已配置 AI 智能模式模型
    const modelRes = await api.get('/ui-automation/ai-models/')
    const configs = Array.isArray(modelRes.data) ? modelRes.data : []
    const hasActive = configs.some((c) => c.is_active)
    if (!hasActive) {
      let goConfig = false
      await ElMessageBox.confirm(
        t('uiAutomation.ai.messages.noModelConfigured'),
        t('uiAutomation.ai.tip'),
        {
          confirmButtonText: t('uiAutomation.ai.messages.goToConfig'),
          cancelButtonText: t('common.cancel'),
          type: 'warning',
        }
      ).then(() => { goConfig = true }).catch(() => {})
      if (goConfig) router.push('/configuration/ai-mode')
      return
    }
    const taskName = `${testcase.value?.title || '用例'}-AI生成步骤`
    const taskDescription = buildTaskDescription() || testcase.value?.title || ''

    // 调用 UI自动化模块的 AI 智能测试流程（run_adhoc 后台线程执行）
    const response = await api.post('/ui-automation/ai-execution-records/run_adhoc/', {
      task_name: taskName,
      task_source: 'text',
      task_description: taskDescription,
      execution_mode: 'text',
      enable_gif: false,
      hub_testcase_id: route.params.id,
      auto_login: autoLogin,
    })
    const executionId = response?.data?.execution_id
    // 跳转到 AI 智能测试执行详情页实时查看执行/回显
    if (executionId) {
      router.push(`/ui-automation/ai-testing/${executionId}`)
    } else {
      ElMessage.success(t('testcase.aiGenerateStepsStarted'))
      // 等待后台执行后回显，回到详情页刷新
      fetchTestCase()
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || t('testcase.aiGenerateStepsFailed'))
  } finally {
    aiGenerating.value = false
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

const getCaseTypeText = (caseType) => {
  const textMap = {
    manual: t('testcase.caseTypeManual'),
    ui: t('testcase.caseTypeUi'),
    api: t('testcase.caseTypeApi')
  }
  const values = Array.isArray(caseType)
    ? caseType
    : (typeof caseType === 'string' && caseType.trim()
      ? caseType.split(/[,，、;；]/).map(v => v.trim()).filter(Boolean)
      : [])
  if (!values.length) return '-'
  return values.map(v => textMap[v] || v).join('、')
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 更新时间：日期与时分之间留2个空格的间隔
const formatUpdatedAt = (dateString) => {
  const d = dayjs(dateString)
  if (!dateString || !d.isValid()) return ''
  return `${d.format('YYYY-MM-DD')}\u00A0\u00A0${d.format('HH:mm')}`
}

onMounted(() => {
  fetchTestCase()
})
</script>

<style lang="scss" scoped>
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

.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  .version-tag {
    margin: 0;
  }
}

.no-version {
  color: #909399;
  font-size: 14px;
  font-style: italic;
}

.steps-content {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #303133;
  font-family: inherit;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 16px;
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

.tab-updated-at {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
}

.ui-steps {
  margin-top: 0;
}
</style>