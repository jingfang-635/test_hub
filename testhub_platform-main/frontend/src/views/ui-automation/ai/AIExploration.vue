<template>
  <div class="exploration-page">
    <!-- 顶部 -->
    <div class="page-header">
      <template v-if="!currentTask">
        <h1 class="page-title">AI探索测试</h1>
        <div class="header-actions">
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon> 新建测试
          </el-button>
          <el-button @click="loadTasks">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      <template v-else>
        <div class="exec-header">
          <el-button size="small" :icon="ArrowLeft" circle @click="exitTask" title="返回列表" />
          <span class="exec-title" :title="currentTask.name">{{ currentTask.name }}</span>
          <el-button
            v-if="currentTask.status === 'running'"
            class="exec-stop"
            size="small"
            type="danger"
            @click="stopTask(currentTask)"
          >停止执行</el-button>
        </div>
      </template>
    </div>

    <!-- 任务列表视图 -->
    <div v-if="!currentTask" class="task-list-wrap">
      <el-table :data="tasks" border stripe v-loading="loadingTasks">
        <el-table-column prop="name" label="任务名称" min-width="140" />
        <el-table-column prop="start_url" label="起始URL" min-width="200" show-overflow-tooltip />
        <el-table-column prop="data_source_display" label="数据来源" min-width="140" />
        <el-table-column prop="ai_model_name" label="AI模型" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.ai_model_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="intent_content" label="自然语言意图" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.intent_content || '-' }}</template>
        </el-table-column>
        <el-table-column prop="environment" label="环境" min-width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长(秒)" width="90">
          <template #default="{ row }">{{ row.duration ? row.duration.toFixed(1) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="enterTask(row)">查看</el-button>
            <el-button v-if="row.status !== 'running'" size="small" type="primary" @click="startTask(row)">启动</el-button>
            <el-button v-else size="small" type="danger" @click="stopTask(row)">停止</el-button>
            <el-button v-if="row.status !== 'running'" size="small" type="danger" plain @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loadingTasks && tasks.length === 0" class="empty-tip">暂无探索任务，点击"新建测试"开始</div>
    </div>

    <!-- 执行视图 -->
    <div v-else class="execution-view">
      <el-row :gutter="16">
        <!-- 左：投屏区（第一阶段显示最新步骤截图，第二阶段接入WebSocket实时画面） -->
        <el-col :span="14">
          <div class="panel screen-panel">
            <div class="section-title">实时画面（投屏）</div>
            <div class="screen-area" ref="screenAreaRef">
              <img v-if="liveScreenshot" :src="liveScreenshot" class="screen-img" ref="screenImgRef" @load="onScreenImgLoad" />
              <img v-else-if="latestScreenshot" :src="latestScreenshot" class="screen-img" :key="latestScreenshot" ref="screenImgRef" @load="onScreenImgLoad" />
              <div v-else class="empty-screen">
                <el-icon class="is-loading" v-if="currentTask.status === 'running'"><Loading /></el-icon>
                <span>{{ currentTask.status === 'running' ? '等待采集画面...' : '暂无画面' }}</span>
              </div>
              <!-- 当前步骤元素高亮框 -->
              <div
                v-if="activeStep && activeStep.rect && activeStep.rect.x != null && screenScale.x"
                class="active-rect-box"
                :style="activeRectStyle"
              >
                <span class="active-rect-label">{{ activeStep.action_type }} → {{ activeStep.element_text || activeStep.action_description }}</span>
              </div>
            </div>
            <div class="logs-box">
              <div class="logs-title">执行日志</div>
              <pre class="logs-content">{{ currentTask.logs || '暂无日志' }}</pre>
            </div>
          </div>
        </el-col>

        <!-- 右：用例矩阵 + 实时探索步骤 -->
        <el-col :span="10">
          <div class="panel cases-panel">
            <!-- 用例矩阵（AI 规划完成、探索前展示） -->
            <div v-if="casePlan.length > 0" class="plan-section">
              <div class="section-title">
                用例矩阵（AI 规划）
                <el-tag size="small" type="info">{{ casePlan.length }} 条用例</el-tag>
              </div>
              <div class="plan-list">
                <div v-for="(pc, idx) in casePlan" :key="idx" class="plan-case">
                  <div class="plan-case-header">
                    <span class="plan-case-name" :title="caseDisplayName(pc.name, idx)">{{ caseDisplayName(pc.name, idx) }}</span>
                    <span class="plan-step-count">{{ pc.step_count || (pc.steps || []).length }} 步</span>
                  </div>
                  <div class="plan-steps">
                    <div v-for="ps in (pc.steps || [])" :key="ps.order" class="plan-step">
                      <span class="plan-step-order">{{ ps.order }}</span>
                      <span class="plan-step-action" :class="`step-type-${ps.action}`">{{ ps.action }}</span>
                      <span class="plan-step-target" :title="ps.target">{{ ps.target }}</span>
                      <span v-if="ps.value" class="plan-step-value">= "{{ ps.value }}"</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 实时探索步骤 -->
            <div class="section-title" style="margin-top: 12px;">
              实时探索步骤
              <el-tag v-if="currentTask.status === 'running'" size="small" type="warning">执行中</el-tag>
            </div>
            <div class="cases-list">
              <div v-if="cases.length === 0 && casePlan.length === 0" class="empty-tip">
                <el-icon class="is-loading" v-if="currentTask.status === 'running'"><Loading /></el-icon>
                {{ currentTask.status === 'running' ? 'AI 正在规划用例...' : '暂无用例' }}
              </div>
              <div v-for="(c, cIdx) in cases" :key="c.id" class="case-item" :class="{ 'case-active': activeCaseId === c.id }">
                <div class="case-header" @click="toggleExpand(c.id)">
                  <el-icon><Document /></el-icon>
                  <span class="case-name">{{ caseDisplayName(c.name, cIdx) }}</span>
                  <el-tag size="small" :type="statusTagType(c.status)">{{ statusText(c.status) }}</el-tag>
                  <span class="step-count">{{ (c.steps || []).length }} 步</span>
                  <el-button size="small" type="primary" link class="expand-btn" @click.stop="toggleExpand(c.id)">
                    {{ isExpanded(c.id) ? '收起' : '展开' }}
                    <el-icon class="expand-icon"><CaretBottom v-if="isExpanded(c.id)" /><CaretRight v-else /></el-icon>
                  </el-button>
                </div>
                <div v-show="isExpanded(c.id)" class="steps-list">
                  <div
                    v-for="s in (c.steps || [])"
                    :key="s.id || s.order"
                    class="step-item"
                    :class="{ 'step-active': activeStep && activeCaseId === c.id && activeStep.order === s.order }"
                  >
                    <span class="step-order">{{ s.order }}</span>
                    <span class="step-type" :class="`step-type-${s.action_type}`">{{ s.action_type }}</span>
                    <span class="step-desc" :title="s.action_description">{{ s.action_description }}</span>
                    <span v-if="s.locator_strategy" class="step-locator" :title="`${s.locator_strategy}: ${s.locator_value}`">
                      [{{ s.locator_strategy }}]
                    </span>
                    <span v-if="s.rect && s.rect.x != null" class="step-coord" :title="`元素框 ${formatCoord(s.rect)}`">
                      [{{ Math.round(s.rect.x) }},{{ Math.round(s.rect.y) }}]
                    </span>
                    <span v-if="s.status === 'failed'" class="step-fail">✗</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 探索用例输出（playwright-explore-to-test 最终产物） -->
      <div v-if="currentTask.generated_code" class="panel code-panel">
        <div class="section-title">
          探索用例输出（Playwright Test）
          <el-button size="small" type="primary" link @click="copyCode">复制代码</el-button>
        </div>
        <pre class="code-block">{{ currentTask.generated_code }}</pre>
      </div>
    </div>

    <!-- 新建测试弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建探索测试" width="620px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="起始URL" required>
          <el-input v-model="createForm.start_url" placeholder="https://example.com（必须是完整网址，账号密码请填到下方意图中）" />
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="createForm.environment" placeholder="请选择项目环境" clearable filterable style="width: 100%">
            <el-option
              v-for="env in environmentOptions"
              :key="env.id"
              :label="env.label"
              :value="env.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="AI模型">
          <el-select v-model="createForm.ai_model_id" placeholder="请选择AI模型" clearable filterable style="width: 100%">
            <el-option
              v-for="model in aiModelOptions"
              :key="model.id"
              :label="model.label"
              :value="model.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据来源">
          <el-radio-group v-model="createForm.data_source">
            <el-radio label="autonomous">自主探索（AI从页面规划）</el-radio>
            <el-radio label="case_driven">功能用例驱动</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="功能用例" v-if="createForm.data_source === 'case_driven'">
          <div class="case-upload-wrap">
            <el-upload
              ref="caseUploadRef"
              class="case-upload"
              drag
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls,.xmind,.md,.markdown,.txt"
              :on-change="handleCaseFileChange"
              :disabled="uploadingCases"
            >
              <div class="upload-inner">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">点击或拖拽上传用例文件</div>
                <div class="upload-hint">支持 Excel（.xlsx/.xls）、XMind（.xmind）、Markdown（.md/.txt）</div>
              </div>
            </el-upload>
            <div v-if="uploadingCases" class="case-upload-tip">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在解析用例文件...</span>
            </div>
            <div v-else-if="caseFile.parsed" class="case-upload-result case-upload-ok">
              <el-icon><Check /></el-icon>
              <span class="result-filename" :title="caseFile.name">{{ caseFile.name }}</span>
              <el-tag size="small" type="success">解析出 {{ caseFile.caseCount }} 条用例</el-tag>
              <el-button link type="primary" size="small" @click.prevent="casePreviewVisible = true">预览</el-button>
              <el-button link type="danger" size="small" @click.prevent="clearCaseFile">移除</el-button>
            </div>
            <div v-else-if="caseFile.error" class="case-upload-result case-upload-err">
              <el-icon><CircleClose /></el-icon>
              <span class="result-filename" :title="caseFile.name">{{ caseFile.name }}</span>
              <span class="err-msg">{{ caseFile.error }}</span>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="自然语言意图">
          <el-input
            v-model="createForm.intent_content"
            type="textarea"
            :rows="3"
            placeholder="如：登录并验证首页核心功能。账号、密码等登录信息填在这里，如：登录，账号 15183871603，密码 123456"
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

    <!-- 用例文件解析结果预览 -->
    <el-dialog v-model="casePreviewVisible" title="用例文件解析结果" width="640px" append-to-body>
      <div class="case-preview-meta">
        <span>文件：{{ caseFile.name }}</span>
        <el-tag size="small" type="success">共 {{ caseFile.caseCount }} 条用例</el-tag>
      </div>
      <pre class="case-preview-text">{{ caseFile.text }}</pre>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, ArrowLeft, Document, Loading, Check, UploadFilled, CircleClose } from '@element-plus/icons-vue'
import api from '@/utils/api'
import {
  getAIExplorationTasks,
  getAIExplorationTaskDetail,
  createAIExplorationTask,
  startAIExplorationTask,
  stopAIExplorationTask,
  deleteAIExplorationTask,
  getAIExplorationProgress,
  updateAIExplorationStepCoords,
  uploadAIExplorationCaseFile
} from '@/api/ui_automation'

// 任务列表
const tasks = ref([])
const loadingTasks = ref(false)
const currentTask = ref(null)
const cases = ref([])
const latestScreenshot = ref('')
const liveScreenshot = ref('')
const wsSocket = ref(null)
// 实时步骤高亮（WS step_update 推送）
const activeStep = ref(null) // 当前执行的步骤信息（含 rect、click_point）
const activeCaseId = ref(null) // 当前正在执行的用例 ID
const casePlan = ref([]) // LLM 规划的用例矩阵（探索前推送）

// 用例步骤展开/收起状态（默认收起）
const expandedCaseIds = ref({})
function isExpanded(id) {
  return !!expandedCaseIds.value[id]
}
function toggleExpand(id) {
  expandedCaseIds.value[id] = !expandedCaseIds.value[id]
}

/** 用例名若为空或纯数字（LLM 常写成 1/2），显示为「用例N」 */
function caseDisplayName(name, idx) {
  const n = (name || '').trim()
  if (!n || /^\d+$/.test(n)) return `用例${(idx ?? 0) + 1}`
  return n
}

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
      } else if (data.type === 'plan_update') {
        // 用例矩阵规划完成（探索前展示）
        handlePlanUpdate(data)
      } else if (data.type === 'step_update') {
        // 实时收到单步执行结果
        handleStepUpdate(data)
      } else if (data.type === 'case_update') {
        // 用例完成
        handleCaseUpdate(data)
      } else if (data.type === 'test_result') {
        // 探索完成，显示最终用例
        handleTestResult(data)
      } else if (data.type === 'log_update') {
        // 实时日志
        if (currentTask.value) {
          currentTask.value.logs = (currentTask.value.logs || '') + data.log + '\n'
        }
      } else if (data.type === 'status') {
        // 任务状态变更
        if (data.status === 'finished' || data.status === 'failed') {
          reloadTaskDetail()
        }
      }
    } catch (err) {
      console.error('投屏 WS 消息解析失败', err)
    }
  }
  ws.onerror = () => { /* 静默处理，回退到轮询截图 */ }
  wsSocket.value = ws
}

// 处理用例矩阵推送：在右边展示规划好的用例
function handlePlanUpdate(data) {
  casePlan.value = data.cases || []
}

// 处理单步实时推送：右边显示点击元素 + 高亮坐标框
function handleStepUpdate(data) {
  const step = data.step
  if (!step) return
  activeCaseId.value = data.case_id
  activeStep.value = step

  // 实时将步骤插入 cases 列表（如果用例还不存在则创建）
  let caseItem = cases.value.find(c => c.id === data.case_id)
  if (!caseItem) {
    caseItem = {
      id: data.case_id,
      name: data.case_name || '探索用例',
      status: 'running',
      steps: []
    }
    cases.value.push(caseItem)
  }
  // 追加步骤（避免重复）
  if (!caseItem.steps.some(s => s.order === step.order)) {
    caseItem.steps.push(step)
  }

  // 更新投屏为该步骤截图（如果有）
  if (step.screenshot) {
    // 步骤截图是相对路径，需拼接
    const ss = step.screenshot.startsWith('http') ? step.screenshot : step.screenshot
    latestScreenshot.value = ss
  }
}

// 处理用例完成推送
function handleCaseUpdate(data) {
  const caseItem = cases.value.find(c => c.id === data.case_id)
  if (caseItem) {
    caseItem.status = data.status
  }
  activeStep.value = null
}

// 处理最终测试结果推送
function handleTestResult(data) {
  if (data.generated_code && currentTask.value) {
    currentTask.value.generated_code = data.generated_code
  }
  // 刷新完整数据（不重连 WS）
  reloadTaskDetail()
}

// 重新加载任务详情（不重连 WS，用于 WS 完成后同步数据）
async function reloadTaskDetail() {
  if (!currentTask.value) return
  try {
    const res = await getAIExplorationTaskDetail(currentTask.value.id)
    currentTask.value = { ...currentTask.value, ...res.data }
    // 仅在 cases 为空或新数据更多时覆盖（避免覆盖实时步骤）
    const incoming = res.data.cases || []
    if (!cases.value.length || incoming.length >= cases.value.length) {
      cases.value = incoming.map(ic => {
        // 接口未返回步骤时保留现有步骤（兼容旧后端/时序问题），避免步骤被清空
        const existing = cases.value.find(c => c.id === ic.id)
        if ((ic.steps || []).length === 0 && existing && (existing.steps || []).length > 0) {
          return { ...ic, steps: existing.steps }
        }
        return ic
      })
    }
  } catch {
    // 静默
  }
}

function disconnectWebSocket() {
  if (wsSocket.value) {
    try { wsSocket.value.close() } catch {}
    wsSocket.value = null
  }
  liveScreenshot.value = ''
  activeStep.value = null
  activeCaseId.value = null
  casePlan.value = []
}

// 创建弹窗
const showCreateDialog = ref(false)
const creating = ref(false)
const environmentOptions = ref([])
const aiModelOptions = ref([])
const createForm = reactive({
  name: '',
  start_url: '',
  environment: '',
  ai_model_id: null,
  data_source: 'autonomous',
  data_content: '',
  intent_content: ''
})

// 功能用例文件上传（功能用例驱动模式）
const CASE_FILE_ACCEPTS = ['xlsx', 'xls', 'xmind', 'md', 'markdown', 'txt']
const caseUploadRef = ref(null)
const uploadingCases = ref(false)
const casePreviewVisible = ref(false)
const caseFile = ref({
  name: '',
  parsed: false,
  error: '',
  caseCount: 0,
  text: ''
})

function resetCaseFile() {
  caseFile.value = { name: '', parsed: false, error: '', caseCount: 0, text: '' }
  createForm.data_content = ''
  // 清空 el-upload 内部文件列表，保证同名文件可再次触发选择
  if (caseUploadRef.value) {
    try { caseUploadRef.value.clearFiles() } catch { /* ignore */ }
  }
}

// 选择文件后立即上传解析
async function handleCaseFileChange(uploadFile) {
  const raw = uploadFile && uploadFile.raw
  if (!raw) return
  const ext = (raw.name.includes('.') ? raw.name.slice(raw.name.lastIndexOf('.') + 1) : '').toLowerCase()
  if (!CASE_FILE_ACCEPTS.includes(ext)) {
    ElMessage.error('仅支持 Excel（.xlsx/.xls）、XMind（.xmind）、Markdown（.md/.txt）文件')
    return
  }
  uploadingCases.value = true
  caseFile.value = { name: raw.name, parsed: false, error: '', caseCount: 0, text: '' }
  try {
    const fd = new FormData()
    fd.append('file', raw)
    const res = await uploadAIExplorationCaseFile(fd)
    const text = res.data.text || ''
    if (!text) {
      throw new Error('解析结果为空')
    }
    createForm.data_content = text
    caseFile.value = {
      name: res.data.filename || raw.name,
      parsed: true,
      error: '',
      caseCount: res.data.case_count || 0,
      text
    }
    ElMessage.success(`用例文件解析成功，共 ${res.data.case_count || 0} 条用例`)
  } catch (e) {
    const msg = e.response?.data?.error || e.message || '解析失败'
    caseFile.value = { name: raw.name, parsed: false, error: msg, caseCount: 0, text: '' }
    createForm.data_content = ''
    ElMessage.error('用例文件解析失败：' + msg)
  } finally {
    uploadingCases.value = false
  }
}

function clearCaseFile() {
  resetCaseFile()
}

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

// 投屏区图片缩放（用于实时高亮框）
const screenScale = ref({ x: 1, y: 1 })
const screenImgRef = ref(null)
const screenAreaRef = ref(null)

function onScreenImgLoad(e) {
  const img = e.target
  if (img && img.naturalWidth) {
    screenScale.value = { x: img.clientWidth / img.naturalWidth, y: img.clientHeight / img.naturalHeight }
  }
}

// 实时步骤高亮框样式
const activeRectStyle = computed(() => {
  const r = activeStep.value && activeStep.value.rect
  if (!r || r.x == null || !screenScale.value.x) return {}
  return {
    left: (r.x * screenScale.value.x) + 'px',
    top: (r.y * screenScale.value.y) + 'px',
    width: (r.width * screenScale.value.x) + 'px',
    height: (r.height * screenScale.value.y) + 'px'
  }
})

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

// 加载环境选项（从项目配置的环境获取）
async function loadEnvironmentOptions() {
  try {
    const res = await api.get('/projects/')
    const projects = res.data || []
    const options = []
    projects.forEach(project => {
      const envs = project.environments || []
      envs.forEach(env => {
        options.push({
          id: env.id,
          label: `${project.name} - ${env.name}`,
          value: env.base_url
        })
      })
    })
    environmentOptions.value = options
  } catch (e) {
    console.error('加载环境列表失败', e)
  }
}

// 加载AI模型选项（从AI智能模式配置获取）
async function loadAIModelOptions() {
  try {
    const res = await api.get('/ui-automation/ai-models/')
    const configs = res.data || []
    aiModelOptions.value = configs.map(config => ({
      id: config.id,
      label: `${config.name} (${config.model_name})`
    }))
  } catch (e) {
    console.error('加载AI模型列表失败', e)
  }
}

// 打开创建弹窗
async function openCreateDialog() {
  createForm.name = ''
  createForm.start_url = ''
  createForm.environment = ''
  createForm.ai_model_id = null
  createForm.data_source = 'autonomous'
  createForm.data_content = ''
  createForm.intent_content = ''
  resetCaseFile()
  casePreviewVisible.value = false
  showCreateDialog.value = true
  loadEnvironmentOptions()
  loadAIModelOptions()
}

// 确认创建并启动
async function confirmCreate() {
  if (!createForm.start_url) {
    ElMessage.error('请填写起始URL')
    return
  }
  if (createForm.data_source === 'case_driven') {
    if (uploadingCases.value) {
      ElMessage.warning('用例文件正在解析中，请稍候')
      return
    }
    if (!createForm.data_content) {
      ElMessage.error('请上传功能用例文件（Excel / XMind / Markdown）')
      return
    }
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

// 删除任务
async function deleteTask(task) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${task.name}」吗？删除后不可恢复`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await deleteAIExplorationTask(task.id)
    ElMessage.success('删除成功')
    loadTasks()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.error || e.message))
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
    casePlan.value = []
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
      // 保留 WS 实时推送的 logs，仅更新状态字段
      const wsLogs = currentTask.value?.logs || ''
      currentTask.value = { ...res.data, logs: wsLogs || res.data.logs }
      // 仅当 WS 未实时推送 cases 时才用轮询数据覆盖
      if (!cases.value.length || cases.value.length < (res.data.cases || []).length) {
        cases.value = res.data.cases || []
      }
      // 最新步骤截图作为投屏占位（WS 未推送截图时）
      if (!liveScreenshot.value) {
        const allSteps = cases.value.flatMap(c => c.steps || [])
        latestScreenshot.value = allSteps.length ? allSteps[allSteps.length - 1].screenshot : latestScreenshot.value
      }
      if (['passed', 'failed', 'stopped'].includes(currentTask.value.status)) {
        stopPolling()
        // 最终刷新完整数据
        reloadTaskDetail()
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

function copyCode() {
  if (!currentTask.value || !currentTask.value.generated_code) return
  navigator.clipboard.writeText(currentTask.value.generated_code).then(() => {
    ElMessage.success('代码已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
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
  .exec-header {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0; /* 允许在 page-header 内收缩，避免把状态标签挤出视口 */
    .exec-title {
      flex: 1;
      min-width: 0;
      font-size: 16px;
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .exec-stop {
      flex-shrink: 0;
    }
  }
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
/* 功能用例文件上传 */
.case-upload-wrap {
  width: 100%;
}
.case-upload {
  width: 100%;
}
.case-upload :deep(.el-upload),
.case-upload :deep(.el-upload-dragger) {
  width: 100%;
}
.case-upload :deep(.el-upload-dragger) {
  padding: 20px;
  border-radius: 6px;
  border: 1px dashed #dcdfe6;
  background: #fafafa;
  &:hover {
    border-color: var(--el-color-primary);
  }
  &.is-disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
}
.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  .upload-icon {
    font-size: 32px;
    color: #c0c4cc;
  }
  .upload-text {
    font-size: 13px;
    color: #606266;
  }
  .upload-hint {
    font-size: 12px;
    color: #909399;
  }
}
.case-upload-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: #409eff;
}
.case-upload-result {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
  flex-wrap: wrap;
  &.case-upload-ok {
    background: #f0f9eb;
    color: #67c23a;
  }
  &.case-upload-err {
    background: #fef0f0;
    color: #f56c6c;
  }
  .result-filename {
    font-weight: 600;
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #303133;
  }
  .err-msg {
    color: #f56c6c;
    flex-basis: 100%;
    word-break: break-all;
  }
}
.case-preview-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #606266;
}
.case-preview-text {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 420px;
  overflow: auto;
  font-size: 13px;
  font-family: Consolas, Monaco, monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
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
    position: relative;
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
    .active-rect-box {
      position: absolute;
      border: 2px solid #f56c6c;
      background: rgba(245, 108, 108, 0.15);
      border-radius: 2px;
      pointer-events: none;
      animation: pulse-highlight 1.5s ease-out infinite;
      .active-rect-label {
        position: absolute;
        top: -22px;
        left: 0;
        background: #f56c6c;
        color: #fff;
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 2px;
        white-space: nowrap;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
  @keyframes pulse-highlight {
    0%, 100% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4); }
    50% { box-shadow: 0 0 0 6px rgba(245, 108, 108, 0); }
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
/* 用例矩阵（AI 规划） */
.plan-section {
  margin-bottom: 8px;
  .plan-list {
    max-height: 300px;
    overflow-y: auto;
  }
  .plan-case {
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    margin-bottom: 8px;
    overflow: hidden;
    .plan-case-header {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 8px;
      background: #f5f7fa;
      .plan-case-id { color: #409eff; font-size: 12px; font-weight: 600; font-family: Consolas, monospace; flex-shrink: 0; }
      .plan-case-name { flex: 1; font-size: 13px; font-weight: 600; color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .plan-step-count { color: #909399; font-size: 11px; flex-shrink: 0; }
    }
    .plan-steps { padding: 4px 8px; }
    .plan-step {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 3px 0;
      font-size: 12px;
      border-bottom: 1px dashed #f0f0f0;
      &:last-child { border-bottom: none; }
      .plan-step-order { width: 16px; height: 16px; border-radius: 50%; background: #dcdfe6; color: #606266; font-size: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
      .plan-step-action { font-size: 11px; flex-shrink: 0; &.step-type-click { color: #e6a23c; } &.step-type-fill { color: #409eff; } &.step-type-navigate { color: #909399; } &.step-type-assert { color: #67c23a; } &.step-type-select { color: #9c27b0; } }
      .plan-step-target { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #606266; }
      .plan-step-value { color: #e6a23c; font-size: 11px; font-family: Consolas, monospace; flex-shrink: 0; }
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
    transition: border-color 0.3s;
    &.case-active { border-color: #f56c6c; box-shadow: 0 0 6px rgba(245, 108, 108, 0.2); }
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
      .expand-btn { flex-shrink: 0; .expand-icon { margin-left: 2px; } }
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
      &.step-active { background: #fdf6ec; border-radius: 3px; padding-left: 4px; padding-right: 4px; }
      .step-order {
        width: 20px; height: 20px; border-radius: 50%;
        background: #409eff; color: #fff; font-size: 11px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }
      .step-type { color: #409eff; font-size: 12px; flex-shrink: 0; &.step-type-click { color: #e6a23c; } &.step-type-fill { color: #409eff; } &.step-type-navigate { color: #909399; } &.step-type-assert { color: #67c23a; } &.step-type-select { color: #9c27b0; } }
      .step-desc { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #606266; }
      .step-locator { color: #67c23a; font-size: 11px; font-family: Consolas, monospace; flex-shrink: 0; background: #f0f9eb; padding: 1px 4px; border-radius: 2px; }
      .step-coord { color: #e6a23c; font-size: 12px; font-family: Consolas, monospace; flex-shrink: 0; }
      .step-fail { color: #f56c6c; font-weight: bold; flex-shrink: 0; }
    }
  }
}
.code-panel {
  margin-top: 16px;
  .section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .code-block {
    background: #1e1e1e;
    color: #d4d4d4;
    border-radius: 4px;
    padding: 12px;
    max-height: 400px;
    overflow-y: auto;
    font-size: 13px;
    font-family: Consolas, Monaco, monospace;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 0;
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
