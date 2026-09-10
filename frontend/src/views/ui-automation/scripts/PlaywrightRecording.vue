<template>
  <div class="playwright-recording">
    <div class="page-header">
      <h1 class="page-title">{{ $t('uiAutomation.playwrightRecording.title') }}</h1>
      <div class="header-actions">
        <el-select
          v-model="projectId"
          :placeholder="$t('uiAutomation.common.selectProject')"
          style="width: 220px"
          :disabled="activeStep > 0"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
      </div>
    </div>

    <div class="main-content">
      <el-steps :active="activeStep" finish-status="success" align-center class="pipeline-steps">
        <el-step :title="$t('uiAutomation.playwrightRecording.stepRecord')" />
        <el-step :title="$t('uiAutomation.playwrightRecording.stepParse')" />
        <el-step :title="$t('uiAutomation.playwrightRecording.stepPlan')" />
        <el-step :title="$t('uiAutomation.playwrightRecording.stepGenerate')" />
      </el-steps>

      <el-alert
        :title="$t('uiAutomation.playwrightRecording.tipTitle')"
        type="info"
        :closable="false"
        show-icon
        class="tip-alert"
      >
        <div>{{ $t('uiAutomation.playwrightRecording.tipContent') }}</div>
        <div class="tip-steps">
          {{ $t('uiAutomation.playwrightRecording.workflow') }}
        </div>
      </el-alert>

      <!-- Step 0: Record -->
      <template v-if="activeStep === 0">
        <el-card shadow="never" class="config-card" v-loading="envLoading">
          <template #header>
            <div class="card-header">
              <span>{{ $t('uiAutomation.playwrightRecording.envTitle') }}</span>
              <el-button text type="primary" @click="loadEnv">{{ $t('uiAutomation.playwrightRecording.refreshEnv') }}</el-button>
            </div>
          </template>
          <div class="env-grid" v-if="envInfo">
            <el-tag :type="envInfo.node?.installed ? 'success' : 'danger'">
              Node {{ envInfo.node?.installed ? envInfo.node.version || 'OK' : 'Missing' }}
            </el-tag>
            <el-tag :type="envInfo.npx?.installed ? 'success' : 'danger'">
              npx {{ envInfo.npx?.installed ? envInfo.npx.version || 'OK' : 'Missing' }}
            </el-tag>
            <el-tag :type="envInfo.python_playwright?.installed ? 'success' : 'info'">
              Python Playwright {{ envInfo.python_playwright?.installed ? envInfo.python_playwright.version || 'OK' : 'N/A' }}
            </el-tag>
            <el-tag :type="envInfo.npx_playwright?.installed ? 'success' : 'info'">
              npx Playwright {{ envInfo.npx_playwright?.installed ? envInfo.npx_playwright.version || 'OK' : 'N/A' }}
            </el-tag>
            <el-tag :type="envInfo.can_start ? 'success' : 'danger'">
              {{ envInfo.can_start ? $t('uiAutomation.playwrightRecording.envReady') : $t('uiAutomation.playwrightRecording.envNotReady') }}
            </el-tag>
          </div>
          <ul v-if="envInfo?.tips?.length" class="env-tips">
            <li v-for="(tip, idx) in envInfo.tips" :key="idx">{{ tip }}</li>
          </ul>
        </el-card>

        <el-card shadow="never" class="config-card">
          <el-form label-width="100px" class="config-form">
            <el-form-item :label="$t('uiAutomation.playwrightRecording.targetUrl')" required>
              <el-input
                v-model="targetUrl"
                :placeholder="$t('uiAutomation.playwrightRecording.targetUrlPlaceholder')"
                clearable
              />
            </el-form-item>
            <el-form-item :label="$t('uiAutomation.playwrightRecording.scriptName')">
              <el-input
                v-model="scriptName"
                :placeholder="$t('uiAutomation.playwrightRecording.scriptNamePlaceholder')"
                clearable
              />
            </el-form-item>
            <el-form-item :label="$t('uiAutomation.playwrightRecording.browser')">
              <el-radio-group v-model="browser" :disabled="isRecording">
                <el-radio-button value="chromium">Chromium</el-radio-button>
                <el-radio-button value="firefox">Firefox</el-radio-button>
                <el-radio-button value="webkit">WebKit</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="$t('uiAutomation.playwrightRecording.language')">
              <el-radio-group v-model="language" :disabled="isRecording">
                <el-radio-button value="python">Python (pytest)</el-radio-button>
                <el-radio-button value="javascript">JavaScript</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="$t('uiAutomation.playwrightRecording.status')">
              <el-tag :type="statusTagType">{{ statusText }}</el-tag>
              <span v-if="session?.command" class="command-inline">{{ session.command }}</span>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="starting"
                :disabled="!envInfo?.can_start || isRecording"
                @click="startRecording"
              >
                {{ $t('uiAutomation.playwrightRecording.startRecording') }}
              </el-button>
              <el-button
                type="danger"
                plain
                :loading="stopping"
                :disabled="!isRecording"
                @click="stopRecording"
              >
                {{ $t('uiAutomation.playwrightRecording.stopRecording') }}
              </el-button>
              <el-button @click="goToScriptList">
                {{ $t('uiAutomation.playwrightRecording.goToScriptList') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" class="script-card">
          <template #header>
            <div class="card-header">
              <span>{{ $t('uiAutomation.playwrightRecording.recordedScript') }}</span>
              <div class="card-actions">
                <el-button @click="clearScript">{{ $t('uiAutomation.playwrightRecording.clear') }}</el-button>
                <el-button type="primary" :loading="saving" @click="saveScript">
                  {{ $t('uiAutomation.playwrightRecording.saveScript') }}
                </el-button>
                <el-button
                  type="success"
                  :loading="parsing"
                  :disabled="!scriptContent.trim()"
                  @click="enterPipeline"
                >
                  {{ $t('uiAutomation.playwrightRecording.enterPipeline') }}
                </el-button>
              </div>
            </div>
          </template>

          <el-input
            v-model="scriptContent"
            type="textarea"
            :rows="18"
            class="script-textarea"
            :placeholder="$t('uiAutomation.playwrightRecording.scriptPlaceholder')"
          />
        </el-card>

        <el-card shadow="never" class="history-card">
          <template #header>
            <div class="card-header">
              <span>{{ $t('uiAutomation.playwrightRecording.historyTitle') }}</span>
              <el-button text type="primary" @click="loadHistory">{{ $t('uiAutomation.playwrightRecording.refreshHistory') }}</el-button>
            </div>
          </template>
          <el-table :data="history" stripe size="small" empty-text="暂无录制文件">
            <el-table-column prop="name" :label="$t('uiAutomation.playwrightRecording.fileName')" min-width="240" show-overflow-tooltip />
            <el-table-column :label="$t('uiAutomation.playwrightRecording.fileSize')" width="120">
              <template #default="{ row }">{{ formatSize(row.size) }}</template>
            </el-table-column>
            <el-table-column :label="$t('uiAutomation.playwrightRecording.updatedAt')" width="180">
              <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('uiAutomation.common.operation')" width="120" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="loadHistoryFile(row.name)">
                  {{ $t('uiAutomation.playwrightRecording.loadFile') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>

      <!-- Step 1: Parse -->
      <template v-else-if="activeStep === 1">
        <el-card shadow="never" class="config-card" v-loading="parsing">
          <template #header>
            <div class="card-header">
              <span>{{ $t('uiAutomation.playwrightRecording.parseTitle') }}</span>
              <el-button text @click="activeStep = 0">{{ $t('uiAutomation.playwrightRecording.backToRecord') }}</el-button>
            </div>
          </template>
          <div v-if="conversion?.parse_result" class="parse-summary">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.parseSteps')">
                {{ conversion.parse_result.step_count || 0 }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.parseCaptcha')">
                {{ conversion.parse_result.has_captcha ? $t('uiAutomation.playwrightRecording.yes') : $t('uiAutomation.playwrightRecording.no') }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.parseMissingAssert')">
                {{ conversion.parse_result.missing_assertions ? $t('uiAutomation.playwrightRecording.yes') : $t('uiAutomation.playwrightRecording.no') }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.parseFragile')">
                {{ (conversion.parse_result.fragile_selectors || []).length }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.parsePages')" :span="2">
                <el-tag
                  v-for="p in (conversion.parse_result.pages || [])"
                  :key="p.name"
                  class="mr-tag"
                  size="small"
                >{{ p.name }} ({{ p.class_name }})</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.parseParams')" :span="2">
                <div v-if="(conversion.parse_result.param_candidates || []).length">
                  <div v-for="(c, i) in conversion.parse_result.param_candidates.slice(0, 8)" :key="i" class="param-line">
                    {{ c.recorded_value }} → {{ c.suggest }}
                  </div>
                </div>
                <span v-else>-</span>
              </el-descriptions-item>
            </el-descriptions>

            <el-table
              v-if="(conversion.parse_result.fragile_selectors || []).length"
              :data="conversion.parse_result.fragile_selectors"
              size="small"
              class="fragile-table"
              stripe
            >
              <el-table-column prop="original" label="原选择器" min-width="280" show-overflow-tooltip />
              <el-table-column prop="suggestion" label="建议" min-width="220" show-overflow-tooltip />
            </el-table>
          </div>
          <div class="step-actions">
            <el-button type="primary" :loading="planning" @click="doGeneratePlan">
              {{ $t('uiAutomation.playwrightRecording.nextGeneratePlan') }}
            </el-button>
          </div>
          <div class="ai-enhance-row">
            <el-switch v-model="useAiEnhance" />
            <span class="ai-enhance-label">{{ $t('uiAutomation.playwrightRecording.useAiEnhance') }}</span>
            <span class="ai-enhance-hint">{{ $t('uiAutomation.playwrightRecording.useAiEnhanceHint') }}</span>
          </div>
        </el-card>
      </template>

      <!-- Step 2: Plan -->
      <template v-else-if="activeStep === 2">
        <el-card shadow="never" class="config-card" v-loading="planning || confirming">
          <template #header>
            <div class="card-header">
              <span>{{ $t('uiAutomation.playwrightRecording.planTitle') }}</span>
              <el-tag :type="conversion?.plan_status === 'confirmed' ? 'success' : 'warning'">
                {{ conversion?.plan_status === 'confirmed' ? '已确认' : '待确认' }}
              </el-tag>
            </div>
          </template>
          <p class="plan-hint">{{ $t('uiAutomation.playwrightRecording.planHint') }}</p>
          <el-form label-width="110px" class="config-form">
            <el-form-item :label="$t('uiAutomation.playwrightRecording.userCases')">
              <el-input
                v-model="userCasesMd"
                type="textarea"
                :rows="4"
                :placeholder="$t('uiAutomation.playwrightRecording.userCasesPlaceholder')"
              />
            </el-form-item>
            <el-form-item label="Plan MD">
              <el-input
                v-model="planMd"
                type="textarea"
                :rows="18"
                class="script-textarea"
              />
            </el-form-item>
          </el-form>
          <div class="step-actions">
            <el-button @click="activeStep = 1">上一步</el-button>
            <el-button :loading="planning" @click="doGeneratePlan">
              {{ $t('uiAutomation.playwrightRecording.regeneratePlan') }}
            </el-button>
            <el-button :loading="savingPlan" @click="doSavePlan">
              {{ $t('uiAutomation.playwrightRecording.savePlan') }}
            </el-button>
            <el-button type="warning" :loading="confirming" @click="doConfirmPlan">
              {{ $t('uiAutomation.playwrightRecording.confirmPlan') }}
            </el-button>
            <el-button
              type="primary"
              :loading="generating"
              :disabled="conversion?.plan_status !== 'confirmed'"
              @click="doGenerateScripts"
            >
              {{ $t('uiAutomation.playwrightRecording.generateScripts') }}
            </el-button>
          </div>
          <div class="ai-enhance-row">
            <el-switch v-model="useAiEnhance" />
            <span class="ai-enhance-label">{{ $t('uiAutomation.playwrightRecording.useAiEnhance') }}</span>
            <span class="ai-enhance-hint">{{ $t('uiAutomation.playwrightRecording.useAiEnhanceHint') }}</span>
          </div>
        </el-card>
      </template>

      <!-- Step 3: Generate result -->
      <template v-else>
        <el-card shadow="never" class="config-card" v-loading="generating">
          <template #header>
            <div class="card-header">
              <span>{{ $t('uiAutomation.playwrightRecording.resultTitle') }}</span>
            </div>
          </template>
          <el-alert
            :title="$t('uiAutomation.playwrightRecording.finishHint')"
            type="success"
            :closable="false"
            show-icon
            class="tip-alert"
          />
          <el-descriptions :column="1" border size="small" class="result-desc">
            <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.resultScripts')">
              {{ (conversion?.generated_script_ids || []).join(', ') || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('uiAutomation.playwrightRecording.resultPageObjects')">
              {{ (conversion?.generated_page_object_ids || []).join(', ') || '-' }}
            </el-descriptions-item>
          </el-descriptions>
          <h4>{{ $t('uiAutomation.playwrightRecording.resultFiles') }}</h4>
          <ul class="file-list">
            <li v-for="(f, idx) in (conversion?.generated_files || [])" :key="idx">{{ f }}</li>
          </ul>
          <div class="step-actions">
            <el-button @click="resetToRecord">{{ $t('uiAutomation.playwrightRecording.backToRecord') }}</el-button>
            <el-button type="primary" @click="goToScriptList">
              {{ $t('uiAutomation.playwrightRecording.goToScriptList') }}
            </el-button>
            <el-button @click="goToPageObjects">
              {{ $t('uiAutomation.playwrightRecording.goToPageObjects') }}
            </el-button>
          </div>
        </el-card>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  createTestScript,
  loadUiAutomationProjects,
  checkCodegenEnv,
  startCodegenRecording,
  getCodegenStatus,
  stopCodegenRecording,
  listCodegenRecorded,
  getCodegenRecordedContent,
  parseCodegenPipeline,
  generateCodegenPlan,
  updateCodegenPlan,
  confirmCodegenPlan,
  generateCodegenScripts
} from '@/api/ui_automation'

const router = useRouter()
const { t } = useI18n()

const projects = ref([])
const projectId = ref(null)
const targetUrl = ref('https://')
const scriptName = ref('')
const browser = ref('chromium')
const language = ref('python')
const scriptContent = ref('')
const saving = ref(false)
const starting = ref(false)
const stopping = ref(false)
const envLoading = ref(false)
const envInfo = ref(null)
const session = ref(null)
const history = ref([])
let pollTimer = null

const activeStep = ref(0)
const conversion = ref(null)
const parsing = ref(false)
const planning = ref(false)
const savingPlan = ref(false)
const confirming = ref(false)
const generating = ref(false)
const useAiEnhance = ref(false)
const planMd = ref('')
const userCasesMd = ref('')

const isRecording = computed(() => ['starting', 'recording'].includes(session.value?.status))

const statusText = computed(() => {
  const status = session.value?.status
  const map = {
    starting: t('uiAutomation.playwrightRecording.statusStarting'),
    recording: t('uiAutomation.playwrightRecording.statusRecording'),
    finished: t('uiAutomation.playwrightRecording.statusFinished'),
    stopped: t('uiAutomation.playwrightRecording.statusStopped'),
    failed: t('uiAutomation.playwrightRecording.statusFailed')
  }
  return map[status] || t('uiAutomation.playwrightRecording.statusIdle')
})

const statusTagType = computed(() => {
  const status = session.value?.status
  if (status === 'recording' || status === 'starting') return 'warning'
  if (status === 'finished') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'stopped') return 'info'
  return 'info'
})

const applyConversion = (next) => {
  conversion.value = next || null
  if (next?.plan_md != null) {
    planMd.value = next.plan_md
  }
  if (next?.user_cases_md != null) {
    userCasesMd.value = next.user_cases_md
  }
}

const loadProjects = async () => {
  try {
    const { projects: list, empty, lastError } = await loadUiAutomationProjects()
    projects.value = list
    if (empty) {
      ElMessage.warning('暂无关联 UI自动化 的项目，请先在「项目与版本」中创建并勾选 UI自动化')
    } else if (list.length === 0) {
      const detail = lastError?.response?.data?.error || lastError?.message || '请确认后端已重启并支持 ensure 接口'
      ElMessage.warning(`项目列表加载失败：${detail}`)
    } else if (!projectId.value) {
      projectId.value = list[0].id
    }
  } catch (error) {
    projects.value = []
    ElMessage.error(t('uiAutomation.playwrightRecording.messages.loadProjectsFailed'))
    console.error(error)
  }
}

const loadEnv = async () => {
  envLoading.value = true
  try {
    const res = await checkCodegenEnv()
    envInfo.value = res.data || res
  } catch (error) {
    console.error(error)
    ElMessage.error(t('uiAutomation.playwrightRecording.messages.envCheckFailed'))
  } finally {
    envLoading.value = false
  }
}

const loadHistory = async () => {
  try {
    const res = await listCodegenRecorded()
    history.value = res.data?.results || res.results || []
  } catch (error) {
    console.error(error)
  }
}

const loadHistoryFile = async (name) => {
  try {
    const res = await getCodegenRecordedContent(name)
    const data = res.data || res
    scriptContent.value = data.content || ''
    scriptName.value = name
    ElMessage.success(t('uiAutomation.playwrightRecording.messages.fileLoaded'))
  } catch (error) {
    ElMessage.error(t('uiAutomation.playwrightRecording.messages.fileLoadFailed'))
    console.error(error)
  }
}

const clearPoll = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const applySession = (nextSession) => {
  session.value = nextSession || null
  if (nextSession?.content) {
    scriptContent.value = nextSession.content
  }
  if (nextSession?.script_name && !scriptName.value) {
    scriptName.value = nextSession.script_name
  }
  if (['finished', 'stopped', 'failed'].includes(nextSession?.status)) {
    clearPoll()
    loadHistory()
    if (nextSession.status === 'finished') {
      ElMessage.success(t('uiAutomation.playwrightRecording.messages.recordFinished'))
    } else if (nextSession.status === 'failed' && nextSession.error) {
      ElMessage.error(nextSession.error)
    }
  }
}

const pollStatus = async () => {
  try {
    const res = await getCodegenStatus({ include_content: 1 })
    const data = res.data || res
    applySession(data.session)
  } catch (error) {
    console.error(error)
  }
}

const startPolling = () => {
  clearPoll()
  pollTimer = setInterval(pollStatus, 2000)
}

const startRecording = async () => {
  if (!targetUrl.value || ['https://', 'http://'].includes(targetUrl.value.trim())) {
    ElMessage.warning(t('uiAutomation.playwrightRecording.messages.emptyUrl'))
    return
  }
  starting.value = true
  try {
    const res = await startCodegenRecording({
      url: targetUrl.value.trim(),
      browser: browser.value,
      language: language.value,
      project_id: projectId.value,
      script_name: scriptName.value
    })
    const data = res.data || res
    applySession(data.session)
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.recordStarted'))
    startPolling()
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.recordStartFailed')
    ElMessage.error(msg)
  } finally {
    starting.value = false
  }
}

const stopRecording = async () => {
  stopping.value = true
  clearPoll()
  try {
    const res = await stopCodegenRecording()
    const data = res.data || res
    applySession(data.session)
    if (data.session?.content) {
      scriptContent.value = data.session.content
    } else if (data.session?.script_name) {
      try {
        const fileRes = await getCodegenRecordedContent(data.session.script_name)
        const fileData = fileRes.data || fileRes
        if (fileData.content) {
          scriptContent.value = fileData.content
        }
      } catch (e) {
        console.error(e)
      }
    }
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.recordStopped'))
    loadHistory()
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.recordStopFailed')
    ElMessage.error(msg)
    if (isRecording.value) {
      startPolling()
    }
  } finally {
    stopping.value = false
  }
}

const clearScript = () => {
  scriptContent.value = ''
}

const goToScriptList = () => {
  router.push('/ui-automation/scripts')
}

const goToPageObjects = () => {
  router.push('/ui-automation/elements')
}

const generateScriptName = () => {
  if (scriptName.value?.trim()) {
    return scriptName.value.trim()
  }
  const currentProject = projects.value.find(p => p.id === projectId.value)
  const projectName = currentProject?.name || 'Script'
  const langLabel = language.value === 'javascript' ? 'JS' : 'Python'
  const date = new Date()
  const dateStr = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`
  const timestamp = Date.now() % 1000
  const extension = language.value === 'javascript' ? 'js' : 'py'
  return `${projectName}_${langLabel}_Playwright_Record_${dateStr}_${timestamp}.${extension}`
}

const saveScript = async () => {
  if (!projectId.value) {
    ElMessage.warning(t('uiAutomation.playwrightRecording.messages.selectProject'))
    return
  }
  if (!scriptContent.value.trim()) {
    ElMessage.warning(t('uiAutomation.playwrightRecording.messages.emptyScript'))
    return
  }

  try {
    saving.value = true
    const name = generateScriptName()
    await createTestScript({
      name,
      project: projectId.value,
      script_type: 'CODE',
      content: scriptContent.value,
      language: language.value === 'javascript' ? 'javascript' : 'python',
      framework: 'playwright'
    })
    ElMessage.success(`${t('uiAutomation.playwrightRecording.messages.saveSuccess')}: ${name}`)
  } catch (error) {
    console.error(error)
    ElMessage.error(t('uiAutomation.playwrightRecording.messages.saveFailed'))
  } finally {
    saving.value = false
  }
}

const enterPipeline = async () => {
  if (!projectId.value) {
    ElMessage.warning(t('uiAutomation.playwrightRecording.messages.selectProject'))
    return
  }
  if (!scriptContent.value.trim()) {
    ElMessage.warning(t('uiAutomation.playwrightRecording.messages.emptyScript'))
    return
  }
  parsing.value = true
  try {
    const res = await parseCodegenPipeline({
      project_id: projectId.value,
      content: scriptContent.value,
      language: language.value,
      scenario: scriptName.value || '',
      recorded_name: scriptName.value || '',
      target_url: targetUrl.value?.startsWith('http') ? targetUrl.value.trim() : ''
    })
    const data = res.data || res
    applyConversion(data.conversion)
    activeStep.value = 1
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.parseSuccess'))
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.parseFailed')
    ElMessage.error(msg)
  } finally {
    parsing.value = false
  }
}

const doGeneratePlan = async () => {
  if (!conversion.value?.id) return
  planning.value = true
  try {
    const res = await generateCodegenPlan(conversion.value.id, {
      user_cases_md: userCasesMd.value,
      use_ai: useAiEnhance.value
    })
    const data = res.data || res
    applyConversion(data.conversion)
    activeStep.value = 2
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.planSuccess'))
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.planFailed')
    ElMessage.error(msg)
  } finally {
    planning.value = false
  }
}

const doSavePlan = async () => {
  if (!conversion.value?.id) return
  savingPlan.value = true
  try {
    const res = await updateCodegenPlan(conversion.value.id, { plan_md: planMd.value })
    const data = res.data || res
    applyConversion(data.conversion)
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.planSaved'))
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.planFailed')
    ElMessage.error(msg)
  } finally {
    savingPlan.value = false
  }
}

const doConfirmPlan = async () => {
  if (!conversion.value?.id) return
  confirming.value = true
  try {
    const res = await confirmCodegenPlan(conversion.value.id, { plan_md: planMd.value })
    const data = res.data || res
    applyConversion(data.conversion)
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.planConfirmed'))
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.planFailed')
    ElMessage.error(msg)
  } finally {
    confirming.value = false
  }
}

const doGenerateScripts = async () => {
  if (!conversion.value?.id) return
  if (conversion.value.plan_status !== 'confirmed') {
    ElMessage.warning(t('uiAutomation.playwrightRecording.messages.confirmRequired'))
    return
  }
  generating.value = true
  try {
    const res = await generateCodegenScripts(conversion.value.id, { use_ai: useAiEnhance.value })
    const data = res.data || res
    applyConversion(data.conversion)
    activeStep.value = 3
    ElMessage.success(data.message || t('uiAutomation.playwrightRecording.messages.generateSuccess'))
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.playwrightRecording.messages.generateFailed')
    ElMessage.error(msg)
  } finally {
    generating.value = false
  }
}

const resetToRecord = () => {
  activeStep.value = 0
}

const formatSize = (size) => {
  if (!size && size !== 0) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

const formatTime = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  return d.toLocaleString()
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadEnv(), loadHistory(), pollStatus()])
})

onBeforeUnmount(() => {
  clearPoll()
})
</script>

<style lang="scss" scoped>
.playwright-recording {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 20px 0;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  align-items: center;
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.pipeline-steps {
  margin-bottom: 16px;
  background: #fff;
  padding: 16px 12px;
  border-radius: 4px;
}

.tip-alert {
  margin-bottom: 16px;
}

.tip-steps {
  margin-top: 6px;
  color: #606266;
  line-height: 1.6;
}

.config-card,
.script-card,
.history-card {
  margin-bottom: 16px;
}

.config-form {
  max-width: 960px;
}

.env-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.env-tips {
  margin: 0;
  padding-left: 18px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.command-inline {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
  word-break: break-all;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.script-textarea :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.parse-summary {
  margin-bottom: 12px;
}

.mr-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}

.param-line {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.fragile-table {
  margin-top: 12px;
}

.step-actions {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-enhance-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: #606266;
  font-size: 13px;
}

.ai-enhance-label {
  color: #303133;
  font-weight: 500;
}

.ai-enhance-hint {
  color: #909399;
}

.plan-hint {
  color: #606266;
  margin: 0 0 12px;
  line-height: 1.6;
}

.result-desc {
  margin: 12px 0;
}

.file-list {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
  max-height: 320px;
  overflow: auto;
}
</style>
