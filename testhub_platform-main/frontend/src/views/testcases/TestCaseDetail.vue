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
        <el-tab-pane :label="$t('testcase.tabBasic')" name="basic">
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
          <div class="tab-actions">
            <el-button size="small" type="primary" @click="editTestCase">{{ $t('testcase.edit') }}</el-button>
            <el-button size="small" type="success" :loading="aiGenerating" @click="handleAiGenerateSteps('ui')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
          </div>
          <div v-if="uiSteps.length > 0" class="ui-steps">
            <div class="ui-steps-header">
              <el-tag type="success" size="small">{{ $t('testcase.aiGeneratedSteps') }}</el-tag>
              <span class="ui-steps-tip">{{ $t('testcase.aiGeneratedStepsTip') }}</span>
            </div>
            <!-- 只读步骤卡片（样式与 UI自动化-用例管理 详情一致，仅展示不可编辑） -->
            <div class="readonly-steps">
              <div class="steps-header">
                <h4>{{ $t('uiAutomation.testCase.testSteps') }}</h4>
                <el-button size="small" text @click="toggleAllSteps">
                  {{ allStepsExpanded ? $t('uiAutomation.testCase.foldAll') : $t('uiAutomation.testCase.expandAll') }}
                </el-button>
              </div>
              <div
                v-for="(step, index) in uiSteps"
                :key="step.step_number ?? index"
                class="step-item"
                :class="{ expanded: stepExpanded[index] }"
              >
                <div class="step-header" @click="toggleStep(index)">
                  <div class="step-desc-row">
                    <span class="step-number">{{ index + 1 }}</span>
                    <span class="step-desc-pill">{{ step.action }}</span>
                  </div>
                  <span class="step-right">
                    <el-icon><component :is="stepExpanded[index] ? ArrowUp : ArrowDown" /></el-icon>
                  </span>
                </div>
                <div v-if="stepExpanded[index]" class="step-content">
                  <div class="step-param">
                    <label>{{ $t('testcase.steps') }}</label>
                    <span class="step-param-text">{{ step.action }}</span>
                  </div>
                  <div v-if="detailFor(index).action_type" class="step-param">
                    <label>{{ actionTypeLabel(detailFor(index).action_type) }}</label>
                    <span class="step-param-text">{{ detailFor(index).description }}</span>
                  </div>
                  <div v-if="detailFor(index).page_filter" class="step-param">
                    <label>{{ $t('uiAutomation.testCase.selectPage') }}</label>
                    <span class="step-param-text">{{ detailFor(index).page_filter }}</span>
                  </div>
                  <div v-if="detailFor(index).element" class="step-param">
                    <label>{{ $t('uiAutomation.testCase.selectElement') }}</label>
                    <span class="step-param-text">{{ detailFor(index).element.name }}</span>
                  </div>
                  <div v-if="detailFor(index).element" class="step-param">
                    <label>{{ $t('uiAutomation.testCase.selector') }}</label>
                    <span class="step-param-text">
                      {{ detailFor(index).element.locator_strategy }}：{{ detailFor(index).element.locator_value }}
                    </span>
                  </div>
                  <div v-if="detailFor(index).element && detailFor(index).element.backup_locators && detailFor(index).element.backup_locators.length" class="step-param">
                    <label>{{ $t('uiAutomation.testCase.backupSelectors') }}</label>
                    <span class="step-param-text">
                      {{ detailFor(index).element.backup_locators.map(b => `${b.strategy}：${b.value}`).join('；') }}
                    </span>
                  </div>
                  <div v-if="detailFor(index).input_value" class="step-param">
                    <label>{{ detailFor(index).action_type === 'fill' ? $t('uiAutomation.testCase.textValue') : $t('uiAutomation.testCase.inputValue') }}</label>
                    <span class="step-param-text">{{ detailFor(index).input_value }}</span>
                  </div>
                  <div v-if="detailFor(index).assert_type" class="step-param">
                    <label>{{ $t('uiAutomation.testCase.assertType') }}</label>
                    <span class="step-param-text">{{ assertTypeLabel(detailFor(index).assert_type) }}：{{ detailFor(index).assert_value }}</span>
                  </div>
                  <div v-if="step.expected" class="step-param">
                    <label>{{ $t('testcase.expectedResult') }}</label>
                    <span class="step-param-text">{{ step.expected }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else :description="$t('testcase.tabEmpty')" />
          <div v-if="uiSteps.length > 0" class="tab-updated-at">{{ $t('testcase.updatedAt') }}：{{ formatUpdatedAt(testcase.updated_at) }}</div>
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
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

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

// UI自动化 tab 展示的回显步骤（AI 智能测试完成后写入 TestCaseStep.step_details）
const uiSteps = computed(() => {
  const steps = testcase.value?.step_details
  if (Array.isArray(steps) && steps.length > 0) {
    return [...steps].sort((a, b) => (a.step_number ?? 0) - (b.step_number ?? 0))
  }
  return []
})

// 结构化步骤详情（来自 UI自动化模块的用例步骤，只读）：动作类型/页面/元素/选择器/输入值等
const uiDetailSteps = ref([])
const detailFor = (index) => {
  const s = uiSteps.value[index]
  const n = s?.step_number ?? index + 1
  return uiDetailSteps.value.find(d => d.step_number === n) || {}
}
const actionTypeLabel = (v) => {
  const map = {
    click: t('uiAutomation.testCase.actionClick'),
    fill: t('uiAutomation.testCase.actionFill'),
    getText: t('uiAutomation.testCase.actionGetText'),
    waitFor: t('uiAutomation.testCase.actionWaitFor'),
    hover: t('uiAutomation.testCase.actionHover'),
    scroll: t('uiAutomation.testCase.actionScroll'),
    screenshot: t('uiAutomation.testCase.actionScreenshot'),
    assert: t('uiAutomation.testCase.actionAssert'),
    wait: t('uiAutomation.testCase.actionWait'),
    switchTab: t('uiAutomation.testCase.actionSwitchTab'),
    navigateUrl: t('uiAutomation.testCase.actionNavigateUrl'),
  }
  return map[v] || v
}
const assertTypeLabel = (v) => {
  const map = {
    textContains: t('uiAutomation.testCase.assertTextContains'),
    textEquals: t('uiAutomation.testCase.assertTextEquals'),
    isVisible: t('uiAutomation.testCase.assertIsVisible'),
    exists: t('uiAutomation.testCase.assertExists'),
    hasAttribute: t('uiAutomation.testCase.assertHasAttribute'),
    urlContains: t('uiAutomation.testCase.assertUrlContains'),
  }
  return map[v] || v
}

// 拉取结构化步骤详情（无 UI 自动化数据时静默忽略）
const fetchUiDetailSteps = async () => {
  if (!route.params.id) return
  try {
    const response = await api.get(`/testcases/${route.params.id}/ui_step_details/`)
    uiDetailSteps.value = response.data?.steps || []
  } catch (error) {
    uiDetailSteps.value = []
  }
}

// 只读步骤卡片：展开/折叠状态（默认折叠，仅展开查看详情，不可编辑）
const stepExpanded = ref({})
const allStepsExpanded = computed(() => {
  return uiSteps.value.length > 0 && uiSteps.value.every((_, i) => stepExpanded.value[i])
})
const toggleStep = (index) => {
  stepExpanded.value[index] = !stepExpanded.value[index]
}
const toggleAllSteps = () => {
  const target = !allStepsExpanded.value
  const next = {}
  uiSteps.value.forEach((_, i) => { next[i] = target })
  stepExpanded.value = next
}

const fetchTestCase = async () => {
  try {
    const response = await api.get(`/testcases/${route.params.id}/`)
    testcase.value = response.data
    fetchUiDetailSteps()
  } catch (error) {
    ElMessage.error(t('testcase.fetchDetailFailed'))
  }
}

const editTestCase = () => {
  router.push(`/ai-generation/testcases/${route.params.id}/edit`)
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

const handleAiGenerateSteps = async () => {
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
  margin-top: 8px;

  .ui-steps-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;

    .ui-steps-tip {
      font-size: 12px;
      color: #909399;
    }
  }
}

// ===== 只读步骤卡片（样式对齐 UI自动化-用例管理 详情页，仅展示不可编辑） =====
.readonly-steps {
  margin-top: 4px;

  .steps-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;

    h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: #303133;
    }
  }

  .step-item {
    border: 1px solid #e6e6e6;
    border-radius: 6px;
    margin-bottom: 10px;
    background: white;
    transition: all 0.3s;
  }

  .step-item:hover {
    border-color: #409eff;
  }

  .step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 15px;
    background: #fafafa;
    border-radius: 6px;
    gap: 8px;
    cursor: pointer;
  }

  .step-item.expanded .step-header {
    border-radius: 6px 6px 0 0;
  }

  .step-desc-row {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex: 1;
  }

  .step-number {
    background: #409eff;
    color: white;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    flex-shrink: 0;
  }

  // 描述胶囊：白底圆角边框，只读时与编辑态视觉一致
  .step-desc-pill {
    display: inline-block;
    max-width: 100%;
    padding: 5px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 16px;
    background: #fff;
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    line-height: 20px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .step-right {
    display: flex;
    align-items: center;
    gap: 5px;
    color: #909399;
    flex-shrink: 0;
  }

  .step-content {
    padding: 15px;
    border-top: 1px solid #e6e6e6;
  }

  .step-param {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    gap: 10px;

    &:last-child {
      margin-bottom: 0;
    }

    label {
      width: 120px;
      flex-shrink: 0;
      font-weight: 500;
      color: #333;
      line-height: 24px;
    }
  }

  .step-param-text {
    flex: 1;
    color: #303133;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-all;
  }
}
</style>