<template>
  <div class="exploration-page">
    <!-- 顶部 -->
    <div class="page-header">
      <h1 class="page-title">AI探索测试</h1>
      <div class="header-actions">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建测试
        </el-button>
        <el-button @click="loadTasks" v-if="!currentTask">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 任务列表视图 -->
    <div v-if="!currentTask" class="task-list-wrap">
      <el-table :data="tasks" border stripe v-loading="loadingTasks">
        <el-table-column prop="name" label="任务名称" min-width="140" />
        <el-table-column prop="start_url" label="起始URL" min-width="200" show-overflow-tooltip />
        <el-table-column prop="data_source_display" label="数据来源" min-width="140" />
        <el-table-column prop="environment" label="环境" min-width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长(秒)" width="90">
          <template #default="{ row }">{{ row.duration ? row.duration.toFixed(1) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="enterTask(row)">查看</el-button>
            <el-button v-if="row.status !== 'running'" size="small" type="primary" @click="startTask(row)">启动</el-button>
            <el-button v-else size="small" type="danger" @click="stopTask(row)">停止</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loadingTasks && tasks.length === 0" class="empty-tip">暂无探索任务，点击"新建测试"开始</div>
    </div>

    <!-- 执行视图 -->
    <div v-else class="execution-view">
      <div class="exec-header">
        <el-button size="small" @click="exitTask">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <span class="exec-title">{{ currentTask.name }}</span>
        <el-tag :type="statusTagType(currentTask.status)" size="small">{{ statusText(currentTask.status) }}</el-tag>
        <el-button v-if="currentTask.status === 'running'" size="small" type="danger" @click="stopTask(currentTask)">停止执行</el-button>
      </div>

      <el-row :gutter="16">
        <!-- 左：投屏区（第一阶段显示最新步骤截图，第二阶段接入WebSocket实时画面） -->
        <el-col :span="14">
          <div class="panel screen-panel">
            <div class="section-title">实时画面（投屏）</div>
            <div class="screen-area">
              <img v-if="liveScreenshot" :src="liveScreenshot" class="screen-img" />
              <img v-else-if="latestScreenshot" :src="latestScreenshot" class="screen-img" :key="latestScreenshot" />
              <div v-else class="empty-screen">
                <el-icon class="is-loading" v-if="currentTask.status === 'running'"><Loading /></el-icon>
                <span>{{ currentTask.status === 'running' ? '等待采集画面...' : '暂无画面' }}</span>
              </div>
            </div>
            <div class="logs-box">
              <div class="logs-title">执行日志</div>
              <pre class="logs-content">{{ currentTask.logs || '暂无日志' }}</pre>
            </div>
          </div>
        </el-col>

        <!-- 右：正在执行的用例（动态加载） -->
        <el-col :span="10">
          <div class="panel cases-panel">
            <div class="section-title">正在执行的用例（动态加载）</div>
            <div class="cases-list">
              <div v-if="cases.length === 0" class="empty-tip">
                <el-icon class="is-loading" v-if="currentTask.status === 'running'"><Loading /></el-icon>
                {{ currentTask.status === 'running' ? 'AI 正在规划用例...' : '暂无用例' }}
              </div>
              <div v-for="c in cases" :key="c.id" class="case-item">
                <div class="case-header" @click="openOrchestration(c)">
                  <el-icon><Document /></el-icon>
                  <span class="case-name">{{ c.name }}</span>
                  <el-tag size="small" :type="statusTagType(c.status)">{{ statusText(c.status) }}</el-tag>
                  <span class="step-count">{{ (c.steps || []).length }} 步</span>
                  <el-button size="small" type="primary" link>可视化编排 ›</el-button>
                </div>
                <div class="steps-list">
                  <div v-for="s in (c.steps || [])" :key="s.id" class="step-item">
                    <span class="step-order">{{ s.order }}</span>
                    <span class="step-type">{{ s.action_type }}</span>
                    <span class="step-desc" :title="s.action_description">{{ s.action_description }}</span>
                    <span v-if="s.rect && s.rect.x != null" class="step-coord" :title="`元素框 ${formatCoord(s.rect)}`">
                      [{{ Math.round(s.rect.x) }},{{ Math.round(s.rect.y) }}]
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 新建测试弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建探索测试" width="620px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="起始URL" required>
          <el-input v-model="createForm.start_url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="环境">
          <el-input v-model="createForm.environment" placeholder="如：测试环境 / 生产环境" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-radio-group v-model="createForm.data_source">
            <el-radio label="autonomous">自主探索（AI从页面规划）</el-radio>
            <el-radio label="case_driven">功能用例驱动</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="功能用例" v-if="createForm.data_source === 'case_driven'">
          <el-input
            v-model="createForm.data_content"
            type="textarea"
            :rows="4"
            placeholder="请输入功能用例描述，每行一条"
          />
        </el-form-item>
        <el-divider content-position="left">补充信息（可选，可与数据来源组合）</el-divider>
        <el-form-item label="自然语言意图">
          <el-input
            v-model="createForm.intent_content"
            type="textarea"
            :rows="3"
            placeholder="如：登录并验证首页核心功能"
          />
        </el-form-item>
        <el-form-item label="代码仓库">
          <el-input
            v-model="createForm.repo_content"
            type="textarea"
            :rows="3"
            placeholder="代码仓库路径/模块说明等参考信息"
          />
        </el-form-item>
        <el-form-item label="任务名称">
          <el-input v-model="createForm.name" placeholder="可选，默认'探索测试'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmCreate" :loading="creating">确定</el-button>
      </template>
    </el-dialog>

    <!-- 可视化编排弹窗 -->
    <el-dialog v-model="showOrchestration" title="可视化编排 - 修改元素坐标" width="900px" top="5vh" :close-on-click-modal="false">
      <div class="orchestration">
        <div class="orch-toolbar">
          <span class="orch-case-name">用例：{{ orchestrationCase?.name }}</span>
          <el-select v-model="currentStepId" placeholder="选择步骤" size="small" style="width: 320px;" @change="selectStep">
            <el-option
              v-for="s in orchestrationSteps"
              :key="s.id"
              :label="`步骤${s.order}：${s.action_description.slice(0, 40)}`"
              :value="s.id"
            />
          </el-select>
          <el-button size="small" type="success" @click="saveCoords" :loading="savingCoords">
            <el-icon><Check /></el-icon> 保存坐标
          </el-button>
        </div>
        <div class="orch-canvas" ref="canvasRef">
          <img
            v-if="currentStep && currentStep.screenshot"
            :src="currentStep.screenshot"
            class="orch-img"
            ref="orchImg"
            @load="onImgLoad"
            draggable="false"
          />
          <div v-else class="empty">该步骤无截图</div>
          <!-- 元素边界框 -->
          <div
            v-if="currentStep && currentStep.rect && currentStep.rect.x != null && imgScale.x"
            class="rect-box"
            :style="rectStyle"
            @mousedown.stop.prevent="startDragRect"
          >
            <span class="rect-label">元素框</span>
          </div>
          <!-- 点击点 -->
          <div
            v-if="currentStep && currentStep.click_point && currentStep.click_point.x != null && imgScale.x"
            class="click-point"
            :style="pointStyle"
            @mousedown.stop.prevent="startDragPoint"
          ></div>
        </div>
        <div class="orch-info" v-if="currentStep">
          <div><b>动作：</b>{{ currentStep.action_description }}</div>
          <div><b>元素框：</b>{{ formatCoord(currentStep.rect) }}</div>
          <div><b>点击点：</b>{{ formatCoord(currentStep.click_point) }}</div>
          <div class="tip">提示：拖拽方框或圆点调整坐标，点击"保存坐标"生效</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, ArrowLeft, Document, Loading, Check } from '@element-plus/icons-vue'
import {
  getAIExplorationTasks,
  getAIExplorationTaskDetail,
  createAIExplorationTask,
  startAIExplorationTask,
  stopAIExplorationTask,
  getAIExplorationProgress,
  updateAIExplorationStepCoords
} from '@/api/ui_automation'

// 任务列表
const tasks = ref([])
const loadingTasks = ref(false)
const currentTask = ref(null)
const cases = ref([])
const latestScreenshot = ref('')
const liveScreenshot = ref('')
const wsSocket = ref(null)

// ===== 实时投屏 WebSocket =====
function connectWebSocket(taskId) {
  disconnectWebSocket()
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${protocol}://${window.location.host}/ws/ui-automation/exploration/${taskId}/`
  const ws = new WebSocket(wsUrl)
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'screenshot' && data.image) {
        liveScreenshot.value = data.image
      }
    } catch (err) {
      console.error('投屏 WS 消息解析失败', err)
    }
  }
  ws.onerror = () => { /* 静默处理，回退到轮询截图 */ }
  wsSocket.value = ws
}

function disconnectWebSocket() {
  if (wsSocket.value) {
    try { wsSocket.value.close() } catch {}
    wsSocket.value = null
  }
  liveScreenshot.value = ''
}

// 创建弹窗
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = reactive({
  name: '',
  start_url: '',
  environment: '',
  data_source: 'autonomous',
  data_content: '',
  intent_content: '',
  repo_content: ''
})

// 可视化编排
const showOrchestration = ref(false)
const orchestrationCase = ref(null)
const orchestrationSteps = ref([])
const currentStepId = ref(null)
const currentStep = ref(null)
const imgScale = ref({ x: 1, y: 1 })
const savingCoords = ref(false)
const canvasRef = ref(null)
const orchImg = ref(null)

// 拖拽状态
const dragging = ref(null)
const dragStart = ref({ mx: 0, my: 0, origRect: null, origPoint: null })

const rectStyle = computed(() => {
  const r = currentStep.value && currentStep.value.rect
  if (!r || r.x == null || !imgScale.value.x) return {}
  return {
    left: (r.x * imgScale.value.x) + 'px',
    top: (r.y * imgScale.value.y) + 'px',
    width: (r.width * imgScale.value.x) + 'px',
    height: (r.height * imgScale.value.y) + 'px'
  }
})

const pointStyle = computed(() => {
  const p = currentStep.value && currentStep.value.click_point
  if (!p || p.x == null || !imgScale.value.x) return {}
  return {
    left: (p.x * imgScale.value.x - 7) + 'px',
    top: (p.y * imgScale.value.y - 7) + 'px'
  }
})

// 状态映射
function statusText(s) {
  return { pending: '等待中', running: '执行中', passed: '成功', failed: '失败', stopped: '已停止', skipped: '已跳过' }[s] || s
}
function statusTagType(s) {
  return { pending: 'info', running: 'warning', passed: 'success', failed: 'danger', stopped: 'info', skipped: 'info' }[s] || 'info'
}
function formatCoord(c) {
  if (!c || c.x == null) return '无'
  return `x=${c.x.toFixed(0)}, y=${c.y.toFixed(0)}${c.width != null ? `, w=${c.width.toFixed(0)}, h=${c.height.toFixed(0)}` : ''}`
}

// 加载任务列表
async function loadTasks() {
  loadingTasks.value = true
  try {
    const res = await getAIExplorationTasks()
    tasks.value = res.data || []
  } catch (e) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loadingTasks.value = false
  }
}

// 打开创建弹窗
function openCreateDialog() {
  createForm.name = ''
  createForm.start_url = ''
  createForm.environment = ''
  createForm.data_source = 'autonomous'
  createForm.data_content = ''
  createForm.intent_content = ''
  createForm.repo_content = ''
  showCreateDialog.value = true
}

// 确认创建并启动
async function confirmCreate() {
  if (!createForm.start_url) {
    ElMessage.error('请填写起始URL')
    return
  }
  creating.value = true
  try {
    const res = await createAIExplorationTask({ ...createForm })
    const taskId = res.data.id
    await startAIExplorationTask(taskId)
    ElMessage.success('探索任务已创建并启动')
    showCreateDialog.value = false
    await enterTask({ id: taskId })
    loadTasks()
  } catch (e) {
    ElMessage.error('创建失败：' + (e.response?.data?.error || e.message))
  } finally {
    creating.value = false
  }
}

// 启动任务
async function startTask(task) {
  try {
    await startAIExplorationTask(task.id)
    ElMessage.success('已启动')
    await enterTask({ id: task.id })
    loadTasks()
  } catch (e) {
    ElMessage.error('启动失败：' + (e.response?.data?.error || e.message))
  }
}

// 停止任务
async function stopTask(task) {
  try {
    await stopAIExplorationTask(task.id)
    ElMessage.warning('已发送停止信号')
    if (currentTask.value && currentTask.value.id === task.id) {
      currentTask.value = { ...currentTask.value, status: 'stopped' }
    }
    loadTasks()
  } catch (e) {
    ElMessage.error('停止失败')
  }
}

// 进入执行视图
async function enterTask(task) {
  try {
    const res = await getAIExplorationTaskDetail(task.id)
    currentTask.value = res.data
    cases.value = res.data.cases || []
    latestScreenshot.value = ''
    liveScreenshot.value = ''
    connectWebSocket(task.id)
    startPolling()
  } catch (e) {
    ElMessage.error('加载任务详情失败')
  }
}

function exitTask() {
  stopPolling()
  disconnectWebSocket()
  currentTask.value = null
  cases.value = []
  latestScreenshot.value = ''
  liveScreenshot.value = ''
  loadTasks()
}

// 轮询进度
let pollTimer = null
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!currentTask.value) return
    try {
      const res = await getAIExplorationProgress(currentTask.value.id)
      currentTask.value = res.data
      cases.value = res.data.cases || []
      // 最新步骤截图作为投屏占位
      const allSteps = cases.value.flatMap(c => c.steps || [])
      latestScreenshot.value = allSteps.length ? allSteps[allSteps.length - 1].screenshot : latestScreenshot.value
      if (['passed', 'failed', 'stopped'].includes(currentTask.value.status)) {
        stopPolling()
      }
    } catch (e) {
      console.error('轮询进度失败', e)
    }
  }, 2000)
}
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ===== 可视化编排 =====
function openOrchestration(c) {
  orchestrationCase.value = c
  orchestrationSteps.value = (c.steps || []).filter(s => s.screenshot)
  if (orchestrationSteps.value.length === 0) {
    ElMessage.warning('该用例暂无含截图的步骤，无法编排')
    return
  }
  currentStepId.value = orchestrationSteps.value[0].id
  currentStep.value = JSON.parse(JSON.stringify(orchestrationSteps.value[0]))
  imgScale.value = { x: 1, y: 1 }
  showOrchestration.value = true
}

function selectStep(id) {
  const s = orchestrationSteps.value.find(x => x.id === id)
  if (s) {
    currentStep.value = JSON.parse(JSON.stringify(s))
    imgScale.value = { x: 1, y: 1 }
  }
}

function onImgLoad(e) {
  const img = e.target
  if (img.naturalWidth) {
    imgScale.value = { x: img.clientWidth / img.naturalWidth, y: img.clientHeight / img.naturalHeight }
  }
}

function startDragRect(e) {
  if (!currentStep.value) return
  dragging.value = 'rect'
  dragStart.value = {
    mx: e.clientX, my: e.clientY,
    origRect: { ...currentStep.value.rect },
    origPoint: { ...currentStep.value.click_point }
  }
}
function startDragPoint(e) {
  if (!currentStep.value) return
  dragging.value = 'point'
  dragStart.value = {
    mx: e.clientX, my: e.clientY,
    origRect: { ...currentStep.value.rect },
    origPoint: { ...currentStep.value.click_point }
  }
}
function onWindowMouseMove(e) {
  if (!dragging.value || !imgScale.value.x || !currentStep.value) return
  const dx = (e.clientX - dragStart.value.mx) / imgScale.value.x
  const dy = (e.clientY - dragStart.value.my) / imgScale.value.y
  if (dragging.value === 'rect') {
    const r = dragStart.value.origRect
    currentStep.value.rect = { x: r.x + dx, y: r.y + dy, width: r.width, height: r.height }
    // 同步点击点为框中心
    currentStep.value.click_point = { x: r.x + dx + r.width / 2, y: r.y + dy + r.height / 2 }
  } else {
    const p = dragStart.value.origPoint
    currentStep.value.click_point = { x: p.x + dx, y: p.y + dy }
  }
}
function onWindowMouseUp() {
  dragging.value = null
}

async function saveCoords() {
  if (!currentStep.value) return
  savingCoords.value = true
  try {
    await updateAIExplorationStepCoords(currentStep.value.id, {
      rect: currentStep.value.rect,
      click_point: currentStep.value.click_point
    })
    ElMessage.success('坐标已保存')
    // 同步回列表数据
    const orig = orchestrationSteps.value.find(s => s.id === currentStep.value.id)
    if (orig) {
      orig.rect = { ...currentStep.value.rect }
      orig.click_point = { ...currentStep.value.click_point }
    }
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.error || e.message))
  } finally {
    savingCoords.value = false
  }
}

onMounted(() => {
  loadTasks()
  window.addEventListener('mousemove', onWindowMouseMove)
  window.addEventListener('mouseup', onWindowMouseUp)
})
onUnmounted(() => {
  stopPolling()
  disconnectWebSocket()
  window.removeEventListener('mousemove', onWindowMouseMove)
  window.removeEventListener('mouseup', onWindowMouseUp)
})
</script>

<style lang="scss" scoped>
.exploration-page {
  padding: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  .page-title { font-size: 20px; font-weight: 600; margin: 0; }
  .header-actions { display: flex; gap: 8px; }
}
.task-list-wrap {
  background: #fff;
  border-radius: 4px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.empty-tip {
  text-align: center;
  color: #909399;
  padding: 30px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.execution-view {
  .exec-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    .exec-title { font-size: 16px; font-weight: 600; }
  }
}
.panel {
  background: #fff;
  border-radius: 4px;
  padding: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}
.screen-panel {
  .screen-area {
    background: #1e1e1e;
    border-radius: 4px;
    min-height: 360px;
    max-height: 520px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    .screen-img { max-width: 100%; max-height: 520px; object-fit: contain; }
    .empty-screen {
      color: #909399;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      .el-icon { font-size: 24px; }
      .screen-tip { font-size: 12px; color: #666; margin-top: 6px; max-width: 360px; }
    }
  }
  .logs-box {
    margin-top: 10px;
    .logs-title { font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #606266; }
    .logs-content {
      background: #f5f7fa;
      border-radius: 4px;
      padding: 8px;
      max-height: 140px;
      overflow-y: auto;
      font-size: 12px;
      font-family: Consolas, Monaco, monospace;
      white-space: pre-wrap;
      word-wrap: break-word;
      margin: 0;
    }
  }
}
.cases-panel {
  max-height: calc(100vh - 180px);
  display: flex;
  flex-direction: column;
  .cases-list { overflow-y: auto; flex: 1; }
  .case-item {
    border: 1px solid #ebeef5;
    border-radius: 4px;
    margin-bottom: 10px;
    overflow: hidden;
    .case-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: #f5f7fa;
      cursor: pointer;
      &:hover { background: #ecf5ff; }
      .case-name { font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .step-count { color: #909399; font-size: 12px; }
    }
    .steps-list { padding: 4px 10px; }
    .step-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 5px 0;
      font-size: 13px;
      border-bottom: 1px dashed #f0f0f0;
      &:last-child { border-bottom: none; }
      .step-order {
        width: 20px; height: 20px; border-radius: 50%;
        background: #409eff; color: #fff; font-size: 11px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }
      .step-type { color: #409eff; font-size: 12px; flex-shrink: 0; }
      .step-desc { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #606266; }
      .step-coord { color: #e6a23c; font-size: 12px; font-family: Consolas, monospace; flex-shrink: 0; }
    }
  }
}
.orchestration {
  .orch-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
    .orch-case-name { font-weight: 600; }
  }
  .orch-canvas {
    position: relative;
    background: #1e1e1e;
    border-radius: 4px;
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    user-select: none;
    .orch-img { max-width: 100%; max-height: 560px; display: block; }
    .empty { color: #909399; padding: 40px; }
    .rect-box {
      position: absolute;
      border: 2px solid #409eff;
      background: rgba(64, 158, 255, 0.15);
      cursor: move;
      .rect-label {
        position: absolute;
        top: -20px; left: 0;
        background: #409eff;
        color: #fff;
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 2px;
        white-space: nowrap;
      }
    }
    .click-point {
      position: absolute;
      width: 14px; height: 14px;
      border-radius: 50%;
      background: #f56c6c;
      border: 2px solid #fff;
      cursor: move;
      box-shadow: 0 0 4px rgba(0,0,0,0.5);
    }
  }
  .orch-info {
    margin-top: 10px;
    font-size: 13px;
    color: #606266;
    line-height: 1.8;
    .tip { color: #e6a23c; margin-top: 4px; }
  }
}
</style>
