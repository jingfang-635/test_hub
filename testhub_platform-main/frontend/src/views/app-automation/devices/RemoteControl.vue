<template>
  <div class="remote-page" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="remote-workspace">
      <!-- 左侧：实时投屏 -->
      <section ref="mirrorPanelRef" class="mirror-panel">
        <div class="mirror-toolbar">
          <div class="toolbar-left">
            <el-button size="small" :icon="ArrowLeft" @click="goBack">返回</el-button>
            <div class="device-line">
              <span class="device-name">{{ deviceName || deviceSerial || '远程设备' }}</span>
              <span class="app-pkg">当前应用: {{ foregroundApp || '-' }}</span>
            </div>
            <span class="status-pill" :class="statusClass">
              <i class="dot" />
              {{ statusText }}
            </span>
            <span class="session-timer">{{ sessionTimerText }}</span>
          </div>
          <div class="toolbar-right">
            <el-select v-model="quality" size="small" style="width: 130px" @change="onQualityChange">
              <el-option label="流畅" value="low" />
              <el-option label="均衡 (推荐)" value="balanced" />
              <el-option label="高清" value="high" />
            </el-select>
            <el-select v-model="zoom" size="small" style="width: 90px">
              <el-option label="75%" :value="75" />
              <el-option label="100%" :value="100" />
              <el-option label="125%" :value="125" />
              <el-option label="150%" :value="150" />
            </el-select>
            <el-button size="small" :icon="Refresh" :loading="connecting" @click="reconnect" />
            <el-button size="small" @click="toggleFullscreen">全屏</el-button>
            <el-button size="small" type="danger" @click="endSession">结束会话</el-button>
          </div>
        </div>

        <div class="mirror-body">
          <div class="phone-frame" :style="{ transform: `scale(${zoom / 100})` }">
            <div
              ref="screenRef"
              class="phone-screen"
              @pointerdown="onPointerDown"
              @pointermove="onPointerMove"
              @pointerup="onPointerUp"
              @pointercancel="onPointerUp"
              @pointerleave="onPointerUp"
            >
              <img v-if="liveImage" :src="liveImage" class="screen-img" draggable="false" alt="live" />
              <div v-else class="screen-placeholder">
                <el-icon class="is-loading" v-if="connecting || status === 'connected'"><Loading /></el-icon>
                <span>{{ placeholderText }}</span>
              </div>
              <div v-if="touchHint.visible" class="touch-hint" :style="touchHintStyle" />
            </div>
            <div class="soft-keys">
              <button type="button" title="返回" @click="sendKey('BACK')">
                <el-icon><Back /></el-icon>
              </button>
              <button type="button" title="主页" @click="sendKey('HOME')">
                <el-icon><HomeFilled /></el-icon>
              </button>
              <button type="button" title="多任务" @click="sendKey('APP_SWITCH')">
                <el-icon><Menu /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧：功能面板 -->
      <section class="side-panel">
        <el-tabs v-model="activeTab" class="side-tabs">
          <el-tab-pane label="元素创建" name="element">
            <div class="element-create">
              <div class="element-toolbar">
                <el-button size="small" @click="clearFrozenFrame">取消当前画面</el-button>
                <el-button size="small" type="primary" :loading="capturing" @click="captureFromLive">设备截图</el-button>
                <el-button size="small" @click="resetElementForm">重置</el-button>
              </div>

              <div class="element-body">
                <!-- 预览裁剪区 -->
                <div class="preview-col">
                  <div class="preview-tip">拖拽框选目标图片区域，保存时只截取选中部分</div>
                  <div v-if="frozenImage" class="preview-scroll">
                    <div
                      ref="imageWrapper"
                      class="image-wrapper"
                      @mousedown="handleMouseDown"
                      @mousemove="handleMouseMove"
                      @mouseup="handleMouseUp"
                      @mouseleave="handleMouseUp"
                    >
                      <img
                        ref="imageRef"
                        :src="frozenImage"
                        class="capture-image"
                        draggable="false"
                        @load="handleImageLoad"
                      />
                      <div
                        v-if="selection"
                        class="selection-box"
                        :style="selectionStyle"
                        @mousedown.stop="handleSelectionMouseDown"
                      >
                        <button class="selection-close" type="button" @click.stop="clearSelection">×</button>
                        <div class="selection-info">{{ selectionInfo }}</div>
                        <span
                          v-for="handle in resizeHandles"
                          :key="handle"
                          class="resize-handle"
                          :class="`resize-handle-${handle}`"
                          @mousedown.stop="handleResizeStart(handle, $event)"
                        />
                      </div>
                    </div>
                  </div>
                  <div v-else class="preview-empty">
                    <el-empty description="点击「设备截图」冻结当前远控画面后框选" :image-size="80" />
                  </div>
                </div>

                <!-- 配置表单 -->
                <div class="form-col">
                  <div class="source-tag">来源: 远控当前画面</div>
                  <el-form :model="formData" label-position="top" size="small" class="element-form">
                    <el-form-item label="设备">
                      <el-input :model-value="deviceSerial || '-'" disabled />
                    </el-form-item>
                    <el-form-item label="元素名称" required>
                      <el-input v-model="formData.name" placeholder="例如：登录按钮" />
                    </el-form-item>
                    <el-form-item label="所属项目">
                      <el-select v-model="formData.project" placeholder="请选择项目" clearable filterable style="width: 100%">
                        <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="元素类型" required>
                      <el-radio-group v-model="formData.element_type">
                        <el-radio value="image">图片元素</el-radio>
                        <el-radio value="pos">坐标元素</el-radio>
                        <el-radio value="region">区域元素</el-radio>
                      </el-radio-group>
                    </el-form-item>
                    <el-form-item label="标签">
                      <el-select
                        v-model="formData.tags"
                        multiple
                        filterable
                        allow-create
                        default-first-option
                        placeholder="输入标签后回车"
                        style="width: 100%"
                      />
                    </el-form-item>

                    <template v-if="formData.element_type === 'image'">
                      <div class="section-title">图片配置</div>
                      <el-form-item label="图片分类" required>
                        <div class="category-row">
                          <el-select v-model="formData.image_category" filterable style="flex: 1">
                            <el-option v-for="cat in imageCategories" :key="cat" :label="cat" :value="cat" />
                          </el-select>
                          <el-button type="primary" @click="showCreateCategoryDialog">新建分类</el-button>
                        </div>
                      </el-form-item>
                      <el-form-item label="模板文件名" required>
                        <el-input v-model="templateFileName" placeholder="例如：login_btn.png" />
                      </el-form-item>
                      <el-form-item label="截取区域">
                        <div class="hint-text">{{ selectionHint }}</div>
                      </el-form-item>
                      <el-form-item label="保存路径">
                        <el-input :model-value="imageSavePath" readonly />
                      </el-form-item>
                      <el-form-item label="匹配阈值">
                        <el-slider
                          v-model="formData.config.image_threshold"
                          :min="0.5"
                          :max="1"
                          :step="0.05"
                          show-input
                          :show-input-controls="true"
                        />
                      </el-form-item>
                      <el-form-item label="颜色模式">
                        <el-switch
                          v-model="formData.config.rgb"
                          active-text="RGB 彩色"
                          inactive-text="灰度"
                        />
                      </el-form-item>
                    </template>

                    <template v-else-if="formData.element_type === 'pos'">
                      <el-form-item label="坐标 Pos">
                        <el-input :model-value="posValue" readonly placeholder="在左侧画面单击选择坐标" />
                      </el-form-item>
                    </template>

                    <template v-else>
                      <el-form-item label="区域 Region">
                        <el-input :model-value="regionValue" readonly placeholder="在左侧画面拖拽框选区域" />
                      </el-form-item>
                    </template>
                  </el-form>

                  <div class="form-actions">
                    <el-button type="primary" :loading="submitting" :disabled="!canSave" @click="saveElement(false)">
                      保存元素
                    </el-button>
                    <el-button type="primary" plain :loading="submitting" :disabled="!canSave" @click="saveElement(true)">
                      保存后继续
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="APP管理" name="app">
            <div class="placeholder-pane">APP 管理功能将在后续版本提供</div>
          </el-tab-pane>
          <el-tab-pane label="设备性能" name="device-perf">
            <div class="placeholder-pane">设备性能监控将在后续版本提供</div>
          </el-tab-pane>
          <el-tab-pane label="APP性能" name="app-perf">
            <div class="placeholder-pane">APP 性能监控将在后续版本提供</div>
          </el-tab-pane>
          <el-tab-pane label="调试日志" name="logs">
            <div class="debug-logs">
              <div v-for="(line, idx) in debugLogs" :key="idx" class="log-line">{{ line }}</div>
              <div v-if="!debugLogs.length" class="placeholder-pane">暂无日志</div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>

    <el-dialog v-model="createCategoryVisible" title="创建图片分类" width="400px">
      <el-input v-model="newCategoryName" placeholder="如：button, icon, menu" @keyup.enter="handleCreateCategory" />
      <template #footer>
        <el-button @click="createCategoryVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingCategory" @click="handleCreateCategory">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Back,
  HomeFilled,
  Loading,
  Menu,
  Refresh
} from '@element-plus/icons-vue'
import {
  getAppProjects,
  getAppImageCategories,
  createAppImageCategory,
  uploadAppElementImage,
  createAppElement,
  captureDeviceScreenshot,
  getDeviceList
} from '@/api/app-automation'

const route = useRoute()
const router = useRouter()

const devicePk = computed(() => route.params.id)
const deviceName = ref('')
const deviceSerial = ref('')
const foregroundApp = ref('')
const liveImage = ref('')
const frozenImage = ref('')
const status = ref('connecting')
const connecting = ref(false)
const capturing = ref(false)
const submitting = ref(false)
const quality = ref('balanced')
const zoom = ref(100)
const activeTab = ref('element')
const isFullscreen = ref(false)
const ws = ref(null)
const mirrorPanelRef = ref(null)
const screenRef = ref(null)
const imageWrapper = ref(null)
const imageRef = ref(null)
const debugLogs = ref([])
const projectList = ref([])
const imageCategories = ref(['common'])
const templateFileName = ref('')
const createCategoryVisible = ref(false)
const newCategoryName = ref('')
const creatingCategory = ref(false)

const sessionSeconds = ref(0)
let sessionTimer = null
let connectedAt = 0

const formData = reactive({
  name: '',
  element_type: 'image',
  image_category: 'common',
  project: null,
  tags: [],
  config: {
    image_threshold: 0.7,
    rgb: false,
    x: 0,
    y: 0,
    x1: 0,
    y1: 0,
    x2: 0,
    y2: 0,
    image_path: '',
    file_hash: ''
  }
})

const selection = ref(null)
const selecting = ref(false)
const startPoint = ref(null)
const action = ref(null)
const resizeHandle = ref(null)
const moveOffset = ref(null)
const imageSize = ref({ width: 0, height: 0 })
const resizeHandles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

const pointerState = reactive({
  active: false,
  pointerId: null,
  startX: 0,
  startY: 0,
  lastX: 0,
  lastY: 0,
  startTime: 0
})
const touchHint = reactive({ visible: false, x: 0, y: 0 })

const statusText = computed(() => {
  const map = {
    connecting: '连接中',
    connected: '已连接',
    streaming: '已连接',
    warn: '异常',
    error: '已断开',
    closed: '已关闭'
  }
  return map[status.value] || status.value
})

const statusClass = computed(() => {
  if (['connected', 'streaming'].includes(status.value)) return 'ok'
  if (status.value === 'warn') return 'warn'
  if (['error', 'closed'].includes(status.value)) return 'err'
  return 'info'
})

const placeholderText = computed(() => {
  if (['error', 'closed'].includes(status.value)) return '连接已断开'
  return '正在连接设备画面...'
})

const sessionTimerText = computed(() => {
  const s = sessionSeconds.value
  const hh = String(Math.floor(s / 3600)).padStart(2, '0')
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})

const touchHintStyle = computed(() => ({
  left: `${touchHint.x}px`,
  top: `${touchHint.y}px`
}))

const selectionStyle = computed(() => {
  if (!selection.value) return {}
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  const x2 = Math.max(selection.value.x1, selection.value.x2)
  const y2 = Math.max(selection.value.y1, selection.value.y2)
  return {
    left: `${x1}px`,
    top: `${y1}px`,
    width: `${x2 - x1}px`,
    height: `${y2 - y1}px`
  }
})

const selectionInfo = computed(() => {
  if (!selection.value) return ''
  const width = Math.abs(selection.value.x2 - selection.value.x1)
  const height = Math.abs(selection.value.y2 - selection.value.y1)
  return `${Math.round(width)} × ${Math.round(height)}`
})

const selectionHint = computed(() => {
  if (!frozenImage.value) return '请先点击「设备截图」'
  if (!selection.value) return '请在左侧画面中拖拽选中图片区域'
  const n = getSelectionInNatural()
  if (!n) return '请在左侧画面中拖拽选中图片区域'
  return `${n.x1},${n.y1} → ${n.x2},${n.y2}`
})

const imageSavePath = computed(() => {
  const cat = formData.image_category || 'common'
  const filename = templateFileName.value || 'template.png'
  return `Template/${cat}/${filename}`
})

const posValue = computed(() => {
  if (formData.config.x || formData.config.y) {
    return `${formData.config.x},${formData.config.y}`
  }
  return ''
})

const regionValue = computed(() => {
  if (formData.config.x1 || formData.config.y1 || formData.config.x2 || formData.config.y2) {
    return `${formData.config.x1},${formData.config.y1},${formData.config.x2},${formData.config.y2}`
  }
  return ''
})

const canSave = computed(() => {
  if (!formData.name) return false
  if (formData.element_type === 'image') {
    return !!frozenImage.value && !!templateFileName.value && !!formData.image_category
  }
  if (formData.element_type === 'pos') {
    return !!(formData.config.x || formData.config.y)
  }
  if (formData.element_type === 'region') {
    return !!(formData.config.x1 || formData.config.y1 || formData.config.x2 || formData.config.y2)
  }
  return false
})

function pushLog(msg) {
  const ts = new Date().toLocaleTimeString()
  debugLogs.value.unshift(`[${ts}] ${msg}`)
  if (debugLogs.value.length > 200) debugLogs.value.length = 200
}

function goBack() {
  endSession(false)
}

function endSession(confirm = true) {
  const leave = () => {
    disconnectWs()
    router.push('/app-automation/devices')
  }
  if (!confirm) {
    leave()
    return
  }
  ElMessageBox.confirm('确定结束当前远程会话吗？', '结束会话', {
    type: 'warning',
    confirmButtonText: '结束',
    cancelButtonText: '取消'
  }).then(leave).catch(() => {})
}

async function loadMeta() {
  try {
    const [devRes, projRes, catRes] = await Promise.all([
      getDeviceList({ page: 1, page_size: 1000 }),
      getAppProjects({ page_size: 100 }),
      getAppImageCategories()
    ])
    const list = devRes.data?.results || []
    const device = list.find((d) => String(d.id) === String(devicePk.value))
    if (device) {
      deviceName.value = device.name || device.device_id
      deviceSerial.value = device.device_id
      if (device.status === 'offline') {
        status.value = 'error'
        ElMessage.error('设备离线，无法远程连接')
        return false
      }
    }
    projectList.value = projRes.data?.results || projRes.data || []
    const cats = catRes.data?.data || catRes.data || []
    imageCategories.value = Array.isArray(cats)
      ? cats.map((c) => c.name || c).filter(Boolean)
      : ['common']
    if (!imageCategories.value.includes('common')) imageCategories.value.unshift('common')
  } catch (e) {
    console.warn(e)
    pushLog(`加载元数据失败: ${e.message || e}`)
  }
  return true
}

function buildWsUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/app-automation/devices/${devicePk.value}/remote/`
}

function connectWs() {
  disconnectWs()
  connecting.value = true
  status.value = 'connecting'
  pushLog('正在建立 WebSocket 连接...')

  const socket = new WebSocket(buildWsUrl())
  ws.value = socket

  socket.onopen = () => {
    connecting.value = false
    status.value = 'connected'
    connectedAt = Date.now()
    sessionSeconds.value = 0
    pushLog('WebSocket 已连接')
    sendJson({ type: 'set_quality', quality: quality.value })
  }

  socket.onmessage = (event) => {
    try {
      handleMessage(JSON.parse(event.data))
    } catch (err) {
      console.error(err)
    }
  }

  socket.onerror = () => {
    connecting.value = false
    status.value = 'error'
    pushLog('WebSocket 连接失败，请确认后端已通过 Uvicorn 启动')
    ElMessage.error('WebSocket 连接失败，请确认后端已通过 Uvicorn 启动')
  }

  socket.onclose = () => {
    connecting.value = false
    if (status.value !== 'error') status.value = 'closed'
    ws.value = null
    pushLog('远程连接已关闭')
  }
}

function disconnectWs() {
  if (ws.value) {
    try { ws.value.close() } catch (_) { /* ignore */ }
    ws.value = null
  }
}

function handleMessage(data) {
  if (data.type === 'frame' && data.image) {
    liveImage.value = data.image
    status.value = 'streaming'
    return
  }
  if (data.type === 'device_info') {
    deviceName.value = data.name || deviceName.value
    deviceSerial.value = data.device_id || deviceSerial.value
    return
  }
  if (data.type === 'foreground') {
    foregroundApp.value = data.package || ''
    return
  }
  if (data.type === 'status') {
    pushLog(data.message || data.status)
    if (data.status === 'error') {
      status.value = 'error'
      ElMessage.error(data.message || '远程连接失败')
    } else if (data.status === 'warn') {
      status.value = 'warn'
    } else if (data.status === 'connected') {
      status.value = 'connected'
    }
  }
}

function sendJson(payload) {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return false
  ws.value.send(JSON.stringify(payload))
  return true
}

function sendKey(keycode) {
  sendJson({ type: 'key', keycode })
}

function onQualityChange(val) {
  sendJson({ type: 'set_quality', quality: val })
}

async function reconnect() {
  const ok = await loadMeta()
  if (ok) connectWs()
}

function getNormalizedPoint(event) {
  const el = screenRef.value
  if (!el) return null
  const rect = el.getBoundingClientRect()
  if (!rect.width || !rect.height) return null
  return {
    x: Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1),
    y: Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1),
    px: event.clientX - rect.left,
    py: event.clientY - rect.top
  }
}

function onPointerDown(event) {
  if (!liveImage.value) return
  const point = getNormalizedPoint(event)
  if (!point) return
  pointerState.active = true
  pointerState.pointerId = event.pointerId
  pointerState.startX = point.x
  pointerState.startY = point.y
  pointerState.lastX = point.x
  pointerState.lastY = point.y
  pointerState.startTime = Date.now()
  touchHint.visible = true
  touchHint.x = point.px
  touchHint.y = point.py
  try { event.currentTarget.setPointerCapture(event.pointerId) } catch (_) { /* ignore */ }
}

function onPointerMove(event) {
  if (!pointerState.active || pointerState.pointerId !== event.pointerId) return
  const point = getNormalizedPoint(event)
  if (!point) return
  pointerState.lastX = point.x
  pointerState.lastY = point.y
  touchHint.x = point.px
  touchHint.y = point.py
}

function onPointerUp(event) {
  if (!pointerState.active || pointerState.pointerId !== event.pointerId) return
  pointerState.active = false
  touchHint.visible = false
  const dx = pointerState.lastX - pointerState.startX
  const dy = pointerState.lastY - pointerState.startY
  const dist = Math.sqrt(dx * dx + dy * dy)
  const duration = Math.max(50, Date.now() - pointerState.startTime)
  if (dist < 0.015) {
    sendJson({ type: 'tap', x: pointerState.startX, y: pointerState.startY })
  } else {
    sendJson({
      type: 'swipe',
      x1: pointerState.startX,
      y1: pointerState.startY,
      x2: pointerState.lastX,
      y2: pointerState.lastY,
      duration
    })
  }
}

async function captureFromLive() {
  if (liveImage.value) {
    frozenImage.value = liveImage.value
    clearSelection()
    pushLog('已冻结远控当前画面用于创建元素')
    ElMessage.success('已截取当前远控画面')
    return
  }

  // 回退：HTTP 截图
  if (!devicePk.value) {
    ElMessage.warning('设备无效')
    return
  }
  capturing.value = true
  try {
    const { data } = await captureDeviceScreenshot(devicePk.value)
    if (data.success && data.data?.content) {
      frozenImage.value = data.data.content
      clearSelection()
      ElMessage.success('截图成功')
    } else {
      ElMessage.error(data.message || '截图失败')
    }
  } catch (e) {
    ElMessage.error('截图失败')
  } finally {
    capturing.value = false
  }
}

function clearFrozenFrame() {
  frozenImage.value = ''
  clearSelection()
}

function resetElementForm() {
  Object.assign(formData, {
    name: '',
    element_type: 'image',
    image_category: 'common',
    project: formData.project,
    tags: [],
    config: {
      image_threshold: 0.7,
      rgb: false,
      x: 0,
      y: 0,
      x1: 0,
      y1: 0,
      x2: 0,
      y2: 0,
      image_path: '',
      file_hash: ''
    }
  })
  templateFileName.value = ''
  clearSelection()
}

function handleImageLoad() {
  if (imageRef.value) {
    imageSize.value = {
      width: imageRef.value.naturalWidth || imageRef.value.width,
      height: imageRef.value.naturalHeight || imageRef.value.height
    }
  }
}

function getImageRect() {
  if (!imageWrapper.value) return null
  return imageWrapper.value.getBoundingClientRect()
}

function getSelectionInNatural() {
  if (!selection.value || !imageRef.value) return null
  const scaleX = imageSize.value.width / imageRef.value.clientWidth
  const scaleY = imageSize.value.height / imageRef.value.clientHeight
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  const x2 = Math.max(selection.value.x1, selection.value.x2)
  const y2 = Math.max(selection.value.y1, selection.value.y2)
  return {
    x1: Math.round(x1 * scaleX),
    y1: Math.round(y1 * scaleY),
    x2: Math.round(x2 * scaleX),
    y2: Math.round(y2 * scaleY)
  }
}

function updateSelectionValues() {
  const natural = getSelectionInNatural()
  if (!natural) return
  formData.config.x1 = natural.x1
  formData.config.y1 = natural.y1
  formData.config.x2 = natural.x2
  formData.config.y2 = natural.y2
}

function handleMouseDown(e) {
  if (!frozenImage.value || !imageWrapper.value) return
  const rect = getImageRect()
  if (!rect) return
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))
  selecting.value = true
  startPoint.value = { x, y }
  action.value = 'create'
  selection.value = { x1: x, y1: y, x2: x, y2: y }
  e.preventDefault()
}

function handleMouseMove(e) {
  if (!selecting.value || !selection.value || !imageWrapper.value) return
  const rect = getImageRect()
  if (!rect) return
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))
  if (action.value === 'create' && startPoint.value) {
    selection.value = { x1: startPoint.value.x, y1: startPoint.value.y, x2: x, y2: y }
  } else if (action.value === 'move' && moveOffset.value) {
    const width = Math.abs(selection.value.x2 - selection.value.x1)
    const height = Math.abs(selection.value.y2 - selection.value.y1)
    const left = Math.max(0, Math.min(x - moveOffset.value.x, rect.width - width))
    const top = Math.max(0, Math.min(y - moveOffset.value.y, rect.height - height))
    selection.value = { x1: left, y1: top, x2: left + width, y2: top + height }
  } else if (action.value === 'resize' && resizeHandle.value) {
    selection.value = resizeSelection(selection.value, resizeHandle.value, x, y, rect)
  }
  e.preventDefault()
}

function handleMouseUp() {
  if (!selecting.value) return
  if (action.value === 'create' && selection.value) {
    const width = Math.abs(selection.value.x2 - selection.value.x1)
    const height = Math.abs(selection.value.y2 - selection.value.y1)
    if (width < 5 && height < 5) {
      if (imageRef.value) {
        const scaleX = imageSize.value.width / imageRef.value.clientWidth
        const scaleY = imageSize.value.height / imageRef.value.clientHeight
        formData.config.x = Math.round(selection.value.x1 * scaleX)
        formData.config.y = Math.round(selection.value.y1 * scaleY)
      }
      selection.value = null
    } else {
      updateSelectionValues()
    }
  } else if (action.value === 'move' || action.value === 'resize') {
    updateSelectionValues()
  }
  selecting.value = false
  startPoint.value = null
  action.value = null
  resizeHandle.value = null
  moveOffset.value = null
}

function handleSelectionMouseDown(e) {
  if (!imageWrapper.value || !selection.value) return
  const rect = getImageRect()
  if (!rect) return
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  selecting.value = true
  action.value = 'move'
  moveOffset.value = { x: x - x1, y: y - y1 }
  e.preventDefault()
}

function handleResizeStart(handle, e) {
  selecting.value = true
  action.value = 'resize'
  resizeHandle.value = handle
  e.preventDefault()
}

function resizeSelection(sel, handle, x, y, rect) {
  let { x1, y1, x2, y2 } = sel
  const clampX = Math.max(0, Math.min(x, rect.width))
  const clampY = Math.max(0, Math.min(y, rect.height))
  if (handle.includes('n')) y1 = clampY
  if (handle.includes('s')) y2 = clampY
  if (handle.includes('w')) x1 = clampX
  if (handle.includes('e')) x2 = clampX
  return { x1, y1, x2, y2 }
}

function clearSelection() {
  selection.value = null
  action.value = null
  resizeHandle.value = null
  moveOffset.value = null
  formData.config.x1 = 0
  formData.config.y1 = 0
  formData.config.x2 = 0
  formData.config.y2 = 0
}

function base64ToBlob(base64, type = 'image/png') {
  const pure = base64.includes(',') ? base64.split(',')[1] : base64
  const byteCharacters = atob(pure)
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i++) byteNumbers[i] = byteCharacters.charCodeAt(i)
  return new Blob([new Uint8Array(byteNumbers)], { type })
}

async function buildImageBlob() {
  if (!frozenImage.value) return null
  if (selection.value && imageRef.value) {
    const img = imageRef.value
    const sel = selection.value
    const scaleX = imageSize.value.width / img.clientWidth
    const scaleY = imageSize.value.height / img.clientHeight
    const x1 = Math.min(sel.x1, sel.x2)
    const y1 = Math.min(sel.y1, sel.y2)
    const x2 = Math.max(sel.x1, sel.x2)
    const y2 = Math.max(sel.y1, sel.y2)
    const cropX = Math.round(x1 * scaleX)
    const cropY = Math.round(y1 * scaleY)
    const cropWidth = Math.round((x2 - x1) * scaleX)
    const cropHeight = Math.round((y2 - y1) * scaleY)
    if (cropWidth < 2 || cropHeight < 2) return null
    const canvas = document.createElement('canvas')
    canvas.width = cropWidth
    canvas.height = cropHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight)
    return await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
  }
  // 直播帧多为 jpeg dataURL，统一转 png 文件名仍可上传
  const mime = frozenImage.value.startsWith('data:image/jpeg') ? 'image/jpeg' : 'image/png'
  return base64ToBlob(frozenImage.value, mime)
}

async function saveElement(continueAfter) {
  if (!formData.name) {
    ElMessage.warning('请输入元素名称')
    return
  }
  if (formData.element_type === 'image') {
    if (!frozenImage.value) {
      ElMessage.warning('请先截取画面')
      return
    }
    if (!templateFileName.value) {
      ElMessage.warning('请输入模板文件名')
      return
    }
  } else if (formData.element_type === 'pos') {
    if (!(formData.config.x || formData.config.y)) {
      ElMessage.warning('请在画面上单击选择坐标')
      return
    }
  } else if (formData.element_type === 'region') {
    if (!(formData.config.x1 || formData.config.x2)) {
      ElMessage.warning('请框选区域')
      return
    }
  }

  submitting.value = true
  try {
    if (formData.element_type === 'image') {
      const imageBlob = await buildImageBlob()
      if (!imageBlob) {
        ElMessage.error('图片处理失败，请重新框选')
        return
      }
      let filename = templateFileName.value.trim()
      if (!/\.(png|jpg|jpeg)$/i.test(filename)) filename += '.png'
      templateFileName.value = filename
      const file = new File([imageBlob], filename, { type: imageBlob.type || 'image/png' })
      const { data: uploadData } = await uploadAppElementImage(file, formData.image_category || 'common')
      if (!uploadData.success) {
        ElMessage.error(uploadData.message || '上传图片失败')
        return
      }
      formData.config.image_path = uploadData.data.image_path
      formData.config.file_hash = uploadData.data.file_hash
    }

    const submitData = {
      name: formData.name,
      element_type: formData.element_type,
      project: formData.project || null,
      tags: formData.tags,
      config: {
        ...formData.config,
        image_category: formData.image_category || 'common'
      }
    }
    await createAppElement(submitData)
    ElMessage.success('元素创建成功')
    pushLog(`元素已创建: ${formData.name}`)
    if (continueAfter) {
      formData.name = ''
      templateFileName.value = ''
      formData.config.image_path = ''
      formData.config.file_hash = ''
      clearSelection()
    } else {
      resetElementForm()
      clearFrozenFrame()
    }
  } catch (error) {
    console.error(error)
    const data = error.response?.data
    ElMessage.error(data?.message || data?.detail || error.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

function showCreateCategoryDialog() {
  newCategoryName.value = ''
  createCategoryVisible.value = true
}

async function handleCreateCategory() {
  const name = newCategoryName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  creatingCategory.value = true
  try {
    const { data } = await createAppImageCategory(name)
    if (data.success) {
      ElMessage.success('分类创建成功')
      await loadMeta()
      formData.image_category = data.data?.name || name
      createCategoryVisible.value = false
    } else {
      ElMessage.error(data.message || '创建失败')
    }
  } catch (e) {
    ElMessage.error('创建分类失败')
  } finally {
    creatingCategory.value = false
  }
}

function toggleFullscreen() {
  const el = mirrorPanelRef.value
  if (!el) return
  if (!document.fullscreenElement) {
    el.requestFullscreen?.().then(() => { isFullscreen.value = true }).catch(() => {})
  } else {
    document.exitFullscreen?.().then(() => { isFullscreen.value = false }).catch(() => {})
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(async () => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
  sessionTimer = setInterval(() => {
    if (connectedAt) sessionSeconds.value = Math.floor((Date.now() - connectedAt) / 1000)
  }, 1000)
  const ok = await loadMeta()
  if (ok) connectWs()
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (sessionTimer) clearInterval(sessionTimer)
  disconnectWs()
})
</script>

<style scoped>
.remote-page {
  height: calc(100vh - 100px);
  min-height: 640px;
  padding: 12px 14px 16px;
  box-sizing: border-box;
  background: #f5f7fb;
}

.remote-workspace {
  display: flex;
  gap: 12px;
  height: 100%;
  min-height: 0;
}

.mirror-panel {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
}

.mirror-toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #eef0f4;
  background: #fafbfc;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.device-line {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}

.device-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
}

.app-pkg {
  font-size: 12px;
  color: #6b7280;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #eef2ff;
  color: #4338ca;
}

.status-pill .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.status-pill.ok {
  background: #ecfdf5;
  color: #059669;
}

.status-pill.warn {
  background: #fffbeb;
  color: #d97706;
}

.status-pill.err {
  background: #fef2f2;
  color: #dc2626;
}

.session-timer {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: #6b7280;
}

.mirror-body {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: #111827;
  overflow: auto;
}

.phone-frame {
  width: 260px;
  transform-origin: center center;
  transition: transform 0.15s ease;
}

.phone-screen {
  position: relative;
  width: 100%;
  aspect-ratio: 9 / 19.5;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  touch-action: none;
  user-select: none;
  cursor: crosshair;
  border: 1px solid #374151;
}

.screen-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

.screen-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #9ca3af;
  font-size: 13px;
}

.touch-hint {
  position: absolute;
  width: 20px;
  height: 20px;
  margin-left: -10px;
  margin-top: -10px;
  border-radius: 50%;
  border: 2px solid rgba(96, 165, 250, 0.95);
  background: rgba(59, 130, 246, 0.28);
  pointer-events: none;
}

.soft-keys {
  display: flex;
  justify-content: space-around;
  margin-top: 10px;
}

.soft-keys button {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1px solid #4b5563;
  background: #1f2937;
  color: #e5e7eb;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.soft-keys button:hover {
  background: #374151;
}

.side-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.side-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.side-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 12px;
  background: #fafbfc;
}

.side-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.side-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.element-create {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.element-toolbar {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #eef0f4;
}

.element-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
}

.preview-col {
  width: 42%;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f8fafc;
  overflow: hidden;
}

.preview-tip {
  padding: 8px 10px;
  font-size: 12px;
  color: #6b7280;
  border-bottom: 1px solid #eef0f4;
  background: #fff;
}

.preview-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 8px;
}

.image-wrapper {
  position: relative;
  display: inline-block;
  cursor: crosshair;
  max-width: 100%;
}

.capture-image {
  max-width: 100%;
  height: auto;
  display: block;
  user-select: none;
}

.preview-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.selection-box {
  position: absolute;
  border: 2px solid #409eff;
  background: rgba(64, 158, 255, 0.12);
  cursor: move;
}

.selection-info {
  position: absolute;
  top: -24px;
  left: 0;
  background: #409eff;
  color: #fff;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
}

.selection-close {
  position: absolute;
  top: -10px;
  right: -10px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: #f56c6c;
  color: #fff;
  cursor: pointer;
  line-height: 1;
  z-index: 2;
}

.resize-handle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #409eff;
  border: 1px solid #fff;
  border-radius: 50%;
  z-index: 2;
}

.resize-handle-nw { top: -5px; left: -5px; cursor: nwse-resize; }
.resize-handle-n { top: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
.resize-handle-ne { top: -5px; right: -5px; cursor: nesw-resize; }
.resize-handle-e { top: 50%; right: -5px; transform: translateY(-50%); cursor: ew-resize; }
.resize-handle-se { bottom: -5px; right: -5px; cursor: nwse-resize; }
.resize-handle-s { bottom: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
.resize-handle-sw { bottom: -5px; left: -5px; cursor: nesw-resize; }
.resize-handle-w { top: 50%; left: -5px; transform: translateY(-50%); cursor: ew-resize; }

.form-col {
  flex: 1;
  min-width: 280px;
  overflow: auto;
  padding-right: 4px;
}

.source-tag {
  display: inline-block;
  margin-bottom: 8px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
}

.section-title {
  margin: 4px 0 10px;
  font-weight: 600;
  color: #374151;
  font-size: 13px;
}

.category-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.hint-text {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.form-actions {
  display: flex;
  gap: 10px;
  padding: 12px 0 4px;
  position: sticky;
  bottom: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), #fff 35%);
}

.placeholder-pane {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 14px;
}

.debug-logs {
  height: 100%;
  overflow: auto;
  padding: 12px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: #374151;
  background: #f8fafc;
}

.log-line {
  padding: 2px 0;
  border-bottom: 1px dashed #e5e7eb;
}

.remote-page.is-fullscreen .mirror-panel {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

@media (max-width: 1200px) {
  .remote-workspace {
    flex-direction: column;
  }

  .mirror-panel {
    width: 100%;
    height: 420px;
  }

  .element-body {
    flex-direction: column;
    overflow: auto;
  }

  .preview-col {
    width: 100%;
    min-height: 320px;
  }
}
</style>
