<template>
  <div class="debug-panel">
    <div class="toolbar">
      <div class="mode-switch">
        <button
          type="button"
          class="mode-btn"
          :class="{ active: logMode === 'device' }"
          @click="logMode = 'device'"
        >
          设备日志
        </button>
        <button
          type="button"
          class="mode-btn"
          :class="{ active: logMode === 'app' }"
          @click="logMode = 'app'"
        >
          App 日志
        </button>
      </div>

      <el-select
        v-if="logMode === 'app'"
        v-model="selectedPackage"
        size="small"
        class="pkg-select"
        filterable
        clearable
        allow-create
        default-first-option
        placeholder="选择包名"
      >
        <el-option v-for="p in packageList" :key="p" :label="p" :value="p" />
      </el-select>

      <el-select v-model="levelFilter" size="small" class="level-select" clearable placeholder="级别">
        <el-option label="Verbose" value="V" />
        <el-option label="Debug" value="D" />
        <el-option label="Info" value="I" />
        <el-option label="Warn" value="W" />
        <el-option label="Error" value="E" />
        <el-option label="Fatal" value="F" />
      </el-select>

      <el-input
        v-model="keyword"
        size="small"
        class="keyword-input"
        clearable
        placeholder="关键字过滤"
        @keyup.enter="refreshLogs"
      />

      <el-select v-model="lineLimit" size="small" class="lines-select">
        <el-option :value="100" label="100 行" />
        <el-option :value="200" label="200 行" />
        <el-option :value="500" label="500 行" />
        <el-option :value="1000" label="1000 行" />
      </el-select>

      <el-button size="small" @click="copyLogs">复制</el-button>
      <el-button size="small" @click="exportLogs">导出</el-button>
      <el-button size="small" class="clear-device-btn" :loading="clearing" @click="clearDeviceLogBuffer">
        清空设备日志
      </el-button>
      <el-button size="small" @click="emit('clear-events')">清空工作台事件</el-button>
    </div>

    <div class="split-view">
      <section class="events-pane">
        <div class="pane-header">
          <span class="pane-title">工作台事件</span>
          <span class="pane-badge">{{ events.length }} 条</span>
        </div>
        <div class="events-list">
          <div v-for="(ev, idx) in events" :key="idx" class="event-item">
            <div class="event-top">
              <span class="event-title">{{ ev.title || '远程控制' }}</span>
              <span class="event-time">{{ ev.time }}</span>
            </div>
            <div class="event-msg">{{ ev.message }}</div>
          </div>
          <div v-if="!events.length" class="empty-tip">暂无工作台事件</div>
        </div>
      </section>

      <section class="logs-pane">
        <div class="pane-header">
          <span class="pane-title">{{ logMode === 'app' ? 'App 日志' : '设备日志' }}</span>
          <span class="pane-status">
            {{ logEntries.length }} 行 ·
            <template v-if="streamConnected">实时流已连接</template>
            <template v-else-if="loading">拉取中...</template>
            <template v-else>未连接</template>
          </span>
        </div>
        <div ref="logListRef" class="log-list">
          <div
            v-for="(row, idx) in logEntries"
            :key="idx"
            class="log-row"
            :class="levelClass(row.level)"
          >
            <span class="col-time">{{ row.time || '--' }}</span>
            <span class="col-level">{{ row.level || '-' }}</span>
            <span class="col-tag" :title="row.tag">{{ row.tag || '-' }}</span>
            <span class="col-msg">{{ row.message }}</span>
          </div>
          <div v-if="!logEntries.length && !loading" class="empty-tip">
            {{ emptyHint }}
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { clearDeviceLogs, getAppPackages, getDeviceLogs } from '@/api/app-automation'

const props = defineProps({
  deviceId: { type: [String, Number], required: true },
  active: { type: Boolean, default: false },
  foregroundPackage: { type: String, default: '' },
  events: { type: Array, default: () => [] }
})

const emit = defineEmits(['clear-events'])

const logMode = ref('app')
const selectedPackage = ref('')
const packageList = ref([])
const levelFilter = ref('')
const keyword = ref('')
const lineLimit = ref(200)
const logEntries = ref([])
const loading = ref(false)
const clearing = ref(false)
const streamConnected = ref(false)
const logListRef = ref(null)

let pollTimer = null
let keywordTimer = null
let pkgLoaded = false

const emptyHint = computed(() => {
  if (logMode.value === 'app' && !selectedPackage.value) {
    return '请选择包名后查看 App 日志'
  }
  return '暂无日志'
})

function levelClass(level) {
  const lv = (level || '').toUpperCase()
  if (lv === 'E' || lv === 'F') return 'lv-e'
  if (lv === 'W') return 'lv-w'
  if (lv === 'I') return 'lv-i'
  if (lv === 'D') return 'lv-d'
  if (lv === 'V') return 'lv-v'
  return ''
}

async function refreshPackages() {
  if (!props.deviceId) return
  try {
    const { data } = await getAppPackages(props.deviceId)
    const list = data?.data?.packages || []
    const fg = data?.data?.foreground || props.foregroundPackage || ''
    packageList.value = Array.from(new Set([...(fg ? [fg] : []), ...list].filter(Boolean)))
    if (!selectedPackage.value && fg) {
      selectedPackage.value = fg
    }
    pkgLoaded = true
  } catch (e) {
    console.warn(e)
  }
}

async function refreshLogs() {
  if (!props.deviceId || !props.active) return
  if (logMode.value === 'app' && !selectedPackage.value) {
    logEntries.value = []
    streamConnected.value = false
    return
  }

  loading.value = true
  try {
    const { data } = await getDeviceLogs(props.deviceId, {
      lines: lineLimit.value,
      package: logMode.value === 'app' ? selectedPackage.value : '',
      level: levelFilter.value || '',
      keyword: keyword.value || ''
    })
    if (data?.success === false) {
      streamConnected.value = false
      ElMessage.error(data.msg || '获取日志失败')
      return
    }
    logEntries.value = data?.data?.lines || []
    streamConnected.value = true
    await nextTick()
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  } catch (e) {
    streamConnected.value = false
    console.warn(e)
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    refreshLogs()
  }, 2500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function logsAsText() {
  return logEntries.value
    .map((r) => r.raw || `${r.time} ${r.level}/${r.tag}: ${r.message}`)
    .join('\n')
}

async function copyLogs() {
  const text = logsAsText()
  if (!text) {
    ElMessage.warning('暂无日志可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (_) {
    ElMessage.error('复制失败')
  }
}

function exportLogs() {
  const text = logsAsText()
  if (!text) {
    ElMessage.warning('暂无日志可导出')
    return
  }
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const mode = logMode.value === 'app' ? 'app' : 'device'
  a.href = url
  a.download = `${mode}-logcat-${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function clearDeviceLogBuffer() {
  if (!props.deviceId) return
  clearing.value = true
  try {
    const { data } = await clearDeviceLogs(props.deviceId)
    if (data?.success === false) {
      ElMessage.error(data.msg || '清空失败')
      return
    }
    logEntries.value = []
    ElMessage.success(data?.msg || '已清空设备日志')
    await refreshLogs()
  } catch (e) {
    ElMessage.error('清空设备日志失败')
  } finally {
    clearing.value = false
  }
}

watch(
  () => props.foregroundPackage,
  (pkg) => {
    if (!pkg) return
    if (!packageList.value.includes(pkg)) {
      packageList.value = [pkg, ...packageList.value]
    }
    if (logMode.value === 'app' && !selectedPackage.value) {
      selectedPackage.value = pkg
    }
  }
)

watch(
  () => [props.active, props.deviceId, logMode.value, selectedPackage.value, levelFilter.value, lineLimit.value],
  async ([active]) => {
    if (active) {
      if (!pkgLoaded) await refreshPackages()
      await refreshLogs()
      startPolling()
    } else {
      stopPolling()
      streamConnected.value = false
    }
  },
  { immediate: true }
)

watch(keyword, () => {
  if (!props.active) return
  if (keywordTimer) clearTimeout(keywordTimer)
  stopPolling()
  keywordTimer = setTimeout(() => {
    refreshLogs()
    startPolling()
  }, 400)
})

onBeforeUnmount(() => {
  stopPolling()
  if (keywordTimer) clearTimeout(keywordTimer)
})
</script>

<style scoped>
.debug-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #f5f7f9;
  box-sizing: border-box;
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
}

.mode-switch {
  display: inline-flex;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.mode-btn {
  border: none;
  background: transparent;
  padding: 5px 14px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  line-height: 1.4;
}

.mode-btn + .mode-btn {
  border-left: 1px solid #dcdfe6;
}

.mode-btn.active {
  background: #409eff;
  color: #fff;
}

.pkg-select {
  width: 200px;
}

.level-select {
  width: 96px;
}

.keyword-input {
  width: 160px;
}

.lines-select {
  width: 100px;
}

.clear-device-btn {
  --el-button-bg-color: #f5a623;
  --el-button-border-color: #f5a623;
  --el-button-text-color: #fff;
  --el-button-hover-bg-color: #e69512;
  --el-button-hover-border-color: #e69512;
  --el-button-hover-text-color: #fff;
  --el-button-active-bg-color: #d6870d;
  --el-button-active-border-color: #d6870d;
  --el-button-active-text-color: #fff;
  background: #f5a623;
  border-color: #f5a623;
  color: #fff;
}

.clear-device-btn:hover,
.clear-device-btn:focus {
  background: #e69512;
  border-color: #e69512;
  color: #fff;
}

.split-view {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
}

.events-pane {
  width: 32%;
  min-width: 220px;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-right: 1px solid #eef0f4;
}

.logs-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #eef0f4;
  flex-shrink: 0;
}

.pane-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.pane-badge {
  font-size: 12px;
  color: #909399;
  background: #f2f3f5;
  padding: 1px 8px;
  border-radius: 10px;
}

.pane-status {
  font-size: 12px;
  color: #909399;
}

.events-list,
.log-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.event-item {
  padding: 12px 14px;
  border-bottom: 1px solid #f0f2f5;
}

.event-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.event-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.event-time {
  font-size: 12px;
  color: #909399;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.event-msg {
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  word-break: break-all;
}

.log-list {
  font-family: Consolas, 'Courier New', Monaco, monospace;
  font-size: 12px;
  line-height: 1.55;
}

.log-row {
  display: grid;
  grid-template-columns: 148px 22px minmax(90px, 160px) 1fr;
  gap: 8px;
  padding: 4px 12px;
  border-bottom: 1px solid #f5f7fa;
  color: #606266;
  align-items: start;
}

.log-row.lv-e {
  background: #fff1f0;
  color: #a8071a;
}

.log-row.lv-w {
  background: #fffbe6;
  color: #ad6800;
}

.log-row.lv-i {
  background: #e6f4ff;
  color: #0958d9;
}

.log-row.lv-d {
  background: #fff;
  color: #595959;
}

.log-row.lv-v {
  background: #fafafa;
  color: #8c8c8c;
}

.col-time {
  white-space: nowrap;
  color: inherit;
  opacity: 0.85;
}

.col-level {
  text-align: center;
  font-weight: 700;
}

.col-tag {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.col-msg {
  white-space: pre-wrap;
  word-break: break-all;
}

.empty-tip {
  padding: 40px 16px;
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
  font-family: inherit;
}

@media (max-width: 1100px) {
  .split-view {
    flex-direction: column;
  }

  .events-pane {
    width: 100%;
    max-width: none;
    max-height: 180px;
    border-right: none;
    border-bottom: 1px solid #eef0f4;
  }
}
</style>
