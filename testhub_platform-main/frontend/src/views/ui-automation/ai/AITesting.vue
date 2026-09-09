<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button class="back-btn" @click="goBack" text>
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1 class="page-title">{{ pageTitle }}</h1>
      </div>
      <div class="header-actions">
        <el-button
          type="danger"
          @click="handleStop"
          :disabled="!running || analyzing"
          v-if="running"
        >
          <el-icon><SwitchButton /></el-icon>
          {{ $t('uiAutomation.ai.stopExecution') }}
        </el-button>
      </div>
    </div>

    <div class="card-container">
      <el-row :gutter="20">
        <el-col :span="14">
          <div class="screen-panel">
            <div class="section-title">{{ $t('uiAutomation.ai.screencast') }}</div>
            <div class="screen-area" ref="screenAreaRef">
              <img
                v-if="liveScreenshot"
                :src="liveScreenshot"
                class="screen-img"
                ref="screenImgRef"
                @load="onScreenImgLoad"
              />
              <div v-else class="empty-screen">
                <el-icon
                  v-if="running && !isCaseConversion && screencastStatus !== 'error'"
                  class="is-loading"
                ><Loading /></el-icon>
                <span>{{ screenPlaceholderText }}</span>
              </div>
            </div>
          </div>

          <div class="section-title" style="margin-top: 16px;">{{ $t('uiAutomation.ai.executionLogs') }}</div>
          <div class="log-container" ref="logContainer">
            <div v-if="!logs && !running" class="empty-logs">
              {{ $t('uiAutomation.ai.noLogs') }}
            </div>
            <pre v-else class="log-content">{{ logs }}</pre>
          </div>
        </el-col>

        <el-col :span="10">
          <div class="section-title">
            {{ showParsedCases ? $t('uiAutomation.ai.caseDetails') : $t('uiAutomation.ai.taskDetails') }}
          </div>
          <div class="task-list-container">
            <div v-if="showParsedCases">
              <div
                v-for="c in displayCases"
                :key="c.id"
                class="case-group"
                :class="c.status"
              >
                <div class="case-header">
                  <div class="task-status-icon">
                    <el-icon v-if="c.status === 'completed'" color="#67C23A"><CircleCheckFilled /></el-icon>
                    <el-icon v-else-if="c.status === 'in_progress'" class="is-loading" color="#409EFF"><Loading /></el-icon>
                    <el-icon v-else-if="c.status === 'failed'" color="#F56C6C"><CircleClose /></el-icon>
                    <el-icon v-else color="#909399"><DocumentAdd /></el-icon>
                  </div>
                  <div class="case-header-text">
                    <div class="case-name" :class="c.status">{{ c.id }}. {{ c.name }}</div>
                    <div v-if="c.precondition" class="case-meta">{{ $t('uiAutomation.ai.precondition') }}：{{ c.precondition }}</div>
                    <div v-if="c.expected" class="case-meta">{{ $t('uiAutomation.ai.expectedResult') }}：{{ c.expected }}</div>
                  </div>
                </div>
                <div
                  v-for="(task, tIdx) in c.tasks"
                  :key="task.id"
                  class="task-item nested"
                  :class="task.status"
                >
                  <div class="task-status-icon">
                    <el-icon v-if="task.status === 'completed'" color="#67C23A"><CircleCheckFilled /></el-icon>
                    <el-icon v-else-if="task.status === 'in_progress'" class="is-loading" color="#409EFF"><Loading /></el-icon>
                    <el-icon v-else-if="task.status === 'failed'" color="#F56C6C"><CircleClose /></el-icon>
                    <el-icon v-else color="#909399"><CircleCheck /></el-icon>
                  </div>
                  <div class="task-content">
                    <span class="task-id">{{ tIdx + 1 }}.</span>
                    <span class="task-desc">{{ task.description }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="analyzing" class="analyzing-state">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>{{ $t('uiAutomation.ai.analyzing') }}</span>
            </div>
            <div v-else-if="plannedTasks.length > 0">
              <div
                v-for="task in plannedTasks"
                :key="task.id"
                class="task-item"
                :class="task.status"
              >
                <div class="task-status-icon">
                  <el-icon v-if="task.status === 'completed'" color="#67C23A"><CircleCheckFilled /></el-icon>
                  <el-icon v-else-if="task.status === 'in_progress'" class="is-loading" color="#409EFF"><Loading /></el-icon>
                  <el-icon v-else color="#909399"><CircleCheck /></el-icon>
                </div>
                <div class="task-content">
                  <span class="task-id">{{ task.id }}.</span>
                  <span class="task-desc">{{ task.description }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-tasks">
              {{ $t('uiAutomation.ai.noTasks') }}
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, CircleCheckFilled, CircleCheck, Loading,
  SwitchButton, CircleClose, DocumentAdd
} from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { getAIExecutionRecordDetail, stopAITask } from '@/api/ui_automation'
import {
  buildDisplayCases as buildCaseList,
  syncDisplayCasesStatus as syncCaseStatus
} from '@/utils/ai-task-progress'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const running = ref(false)
const analyzing = ref(false)
const logs = ref('')
const plannedTasks = ref([])
const displayCases = ref([])
const caseName = ref('')
const taskName = ref('')
const currentExecutionId = ref(null)
const logContainer = ref(null)
const isCaseConversion = ref(false) // 用例转换任务：执行中无需投屏
let pollInterval = null

const wsSocket = ref(null)
const liveScreenshot = ref('')
const screencastStatus = ref('idle') // idle | connecting | connected | error
const screenAreaRef = ref(null)
const screenImgRef = ref(null)
const screenScale = ref({ x: 1, y: 1 })

const pageTitle = computed(() => taskName.value || caseName.value || t('uiAutomation.ai.title'))
const showParsedCases = computed(() => displayCases.value.length > 0)
const screenPlaceholderText = computed(() => {
  if (isCaseConversion.value) return t('uiAutomation.ai.noScreen')
  if (!running.value) return t('uiAutomation.ai.noScreen')
  if (screencastStatus.value === 'error') return t('uiAutomation.ai.screencastWsError')
  return t('uiAutomation.ai.waitingScreen')
})

const buildDisplayCases = (cases) => buildCaseList(cases, (k) => t(`uiAutomation.ai.${k}`))

const syncDisplayCasesStatus = (planned) => {
  syncCaseStatus(displayCases.value, planned)
}

function goBack() {
  router.push('/ui-automation/ai-testing')
}

function connectScreencast(executionId) {
  disconnectScreencast()
  screencastStatus.value = 'connecting'
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${protocol}://${window.location.host}/ws/ui-automation/ai-screencast/${executionId}/`
  const ws = new WebSocket(wsUrl)
  ws.onopen = () => {
    screencastStatus.value = 'connected'
  }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'screenshot' && data.image) {
        liveScreenshot.value = data.image
        screencastStatus.value = 'connected'
      }
    } catch (err) {
      console.error('AI投屏 WS 消息解析失败', err)
    }
  }
  ws.onerror = () => {
    screencastStatus.value = 'error'
  }
  ws.onclose = () => {
    if (!liveScreenshot.value && running.value) {
      screencastStatus.value = 'error'
    }
  }
  wsSocket.value = ws
}

function disconnectScreencast() {
  if (wsSocket.value) {
    try { wsSocket.value.close() } catch {}
    wsSocket.value = null
  }
  liveScreenshot.value = ''
  screencastStatus.value = 'idle'
}

function onScreenImgLoad(e) {
  const img = e.target
  if (img && img.naturalWidth) {
    screenScale.value = { x: img.clientWidth / img.naturalWidth, y: img.clientHeight / img.naturalHeight }
  }
}

const handleStop = async () => {
  if (!currentExecutionId.value) return
  try {
    await stopAITask(currentExecutionId.value)
    ElMessage.warning(t('uiAutomation.ai.messages.stopping'))
  } catch (error) {
    console.error('停止失败:', error)
    ElMessage.error(t('uiAutomation.ai.messages.stopFailed'))
  }
}

const applyRecord = (record) => {
  logs.value = record.logs || ''
  plannedTasks.value = record.planned_tasks || []
  caseName.value = record.case_name || ''
  taskName.value = record.task_name || ''
  isCaseConversion.value = record.task_source === 'case_conversion'

  // 文件模式：用后端保存的用例树还原右侧用例明细（与执行时一致）
  const parsedCases = Array.isArray(record.parsed_cases) ? record.parsed_cases : []
  if (parsedCases.length) {
    displayCases.value = buildDisplayCases(parsedCases)
  }

  if (showParsedCases.value) {
    syncDisplayCasesStatus(plannedTasks.value)
    analyzing.value = false
  } else if (plannedTasks.value.length > 0) {
    analyzing.value = false
  }

  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })

  const terminal = ['passed', 'failed', 'stopped'].includes(record.status)
  if (terminal) {
    stopPolling()
    running.value = false
    analyzing.value = false
    disconnectScreencast()
  }
  return terminal
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const startPolling = () => {
  stopPolling()
  pollInterval = setInterval(async () => {
    if (!currentExecutionId.value) {
      stopPolling()
      return
    }
    try {
      const response = await getAIExecutionRecordDetail(currentExecutionId.value)
      const terminal = applyRecord(response.data)
      if (terminal) {
        const status = response.data.status
        if (status === 'passed') {
          ElMessage.success(t('uiAutomation.ai.messages.executionSuccess'))
        } else if (status === 'stopped') {
          ElMessage.warning(t('uiAutomation.ai.messages.taskStopped'))
        } else {
          ElMessage.error(t('uiAutomation.ai.messages.executionFailed'))
        }
      }
    } catch (error) {
      console.error('获取日志失败:', error)
    }
  }, 2000)
}

const loadExecution = async () => {
  const id = route.params.id
  if (!id) {
    goBack()
    return
  }
  currentExecutionId.value = id

  try {
    const response = await getAIExecutionRecordDetail(id)
    const record = response.data
    const terminal = applyRecord(record)

    if (!terminal && (record.status === 'running' || record.status === 'pending')) {
      running.value = true
      analyzing.value = !showParsedCases.value && plannedTasks.value.length === 0
      // 用例转换任务：执行中无需投屏，直接轮询日志/状态
      if (!isCaseConversion.value) {
        connectScreencast(id)
      }
      startPolling()
    } else {
      running.value = false
      analyzing.value = false
    }
  } catch (error) {
    console.error('加载执行详情失败:', error)
    ElMessage.error(t('uiAutomation.ai.executionRecords.messages.loadFailed'))
    goBack()
  }
}

onMounted(() => {
  loadExecution()
})

onBeforeUnmount(() => {
  stopPolling()
  disconnectScreencast()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;

    .back-btn {
      padding: 0;
      margin: 0;
      font-size: 20px;
      height: auto;
    }
  }

  .page-title {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.card-container {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  min-height: calc(100vh - 140px);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  padding-left: 10px;
  border-left: 4px solid #409eff;
}

.screen-panel {
  .screen-area {
    background: #1e1e1e;
    border-radius: 4px;
    min-height: 400px;
    max-height: 560px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;

    .screen-img {
      max-width: 100%;
      max-height: 560px;
      object-fit: contain;
      display: block;
    }

    .empty-screen {
      color: #909399;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      .el-icon { font-size: 24px; }
    }
  }
}

.task-list-container {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  height: calc(100vh - 200px);
  overflow-y: auto;

  .case-group {
    margin-bottom: 12px;
    background: #fff;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    overflow: hidden;

    &:last-child { margin-bottom: 0; }
    &.completed { border-color: #c2e7b0; }
    &.in_progress { border-color: #b3d8ff; }
    &.failed { border-color: #fbc4c4; }

    .case-header {
      display: flex;
      align-items: center;
      padding: 10px 12px;
      background: #fafafa;
      border-bottom: 1px solid #ebeef5;

      .task-status-icon {
        margin-right: 10px;
        margin-top: 2px;
        font-size: 16px;
        display: flex;
        align-items: flex-start;
      }

      .case-header-text {
        flex: 1;
        min-width: 0;
      }

      .case-name {
        font-weight: 600;
        &.completed { color: #67c23a; text-decoration: line-through; }
        &.in_progress { color: #409eff; }
        &.failed { color: #f56c6c; }
      }
    }

    .case-meta {
      margin-top: 4px;
      font-size: 12px;
      color: #909399;
      line-height: 1.4;
      word-break: break-word;
    }
  }

  .task-item {
    display: flex;
    align-items: flex-start;
    padding: 10px;
    border-bottom: 1px solid #e4e7ed;
    transition: all 0.3s;

    &.nested {
      padding-left: 28px;
      border-bottom-color: #f0f2f5;
      &:last-child { border-bottom: none; }
    }

    &:last-child { border-bottom: none; }

    &.completed {
      background-color: #f0f9eb;
      .task-desc { color: #67c23a; text-decoration: line-through; }
    }

    &.in_progress {
      background-color: #ecf5ff;
      .task-desc { color: #409eff; font-weight: bold; }
    }

    &.failed {
      background-color: #fef0f0;
      .task-desc { color: #f56c6c; }
    }

    .task-status-icon {
      margin-right: 10px;
      margin-top: 2px;
      font-size: 16px;
    }

    .task-content {
      flex: 1;
      line-height: 1.5;
      .task-id { font-weight: bold; margin-right: 5px; }
    }
  }
}

.empty-tasks {
  color: #909399;
  text-align: center;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.analyzing-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #409eff;
  .el-icon { font-size: 24px; margin-bottom: 10px; }
}

.log-container {
  background-color: #1e1e1e;
  border-radius: 4px;
  height: 220px;
  overflow-y: auto;
  padding: 15px;
  color: #fff;
  font-family: 'Consolas', 'Monaco', monospace;

  .empty-logs {
    color: #909399;
    text-align: center;
    margin-top: 70px;
  }

  .log-content {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.5;
  }
}
</style>
