<template>
  <div class="perf-panel">
    <div class="perf-header">
      <div class="perf-title-block">
        <h3>设备性能</h3>
        <p>仅在当前标签激活时轮询，避免给工作台带来额外负担。</p>
      </div>
      <div class="perf-controls">
        <span class="ctrl-label">自动</span>
        <el-switch v-model="autoRefresh" />
        <el-select v-model="intervalSec" size="small" style="width: 72px" :disabled="!autoRefresh">
          <el-option :value="1" label="1s" />
          <el-option :value="2" label="2s" />
          <el-option :value="3" label="3s" />
          <el-option :value="5" label="5s" />
        </el-select>
        <el-button size="small" :loading="manualLoading" @click="manualRefresh">刷新</el-button>
        <el-button size="small" @click="resetHistory">重置</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">CPU</div>
        <div class="metric-value">{{ formatNum(metrics.cpu_percent) }}%</div>
        <div class="metric-sub">核心数 {{ metrics.cpu_cores || '-' }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">内存</div>
        <div class="metric-value">{{ formatNum(metrics.mem_percent) }}%</div>
        <div class="metric-sub">{{ formatNum(metrics.mem_used_mb) }}/{{ formatNum(metrics.mem_total_mb) }} MB</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">下行</div>
        <div class="metric-value">{{ formatSpeed(rxSpeed) }}</div>
        <div class="metric-sub">累计 {{ formatBytes(metrics.net_rx_bytes) }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">上行</div>
        <div class="metric-value">{{ formatSpeed(txSpeed) }}</div>
        <div class="metric-sub">累计 {{ formatBytes(metrics.net_tx_bytes) }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">电池</div>
        <div class="metric-value">{{ metrics.battery_percent ?? '-' }}%</div>
        <div class="metric-sub">
          <span v-if="metrics.battery_temp != null">{{ metrics.battery_temp }}°C</span>
          <span v-if="thermalHint" class="warn-text"> · {{ thermalHint }}</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">存储 / 当前应用</div>
        <div class="metric-value">{{ formatNum(metrics.storage_percent) }}%</div>
        <div class="metric-sub pkg">{{ metrics.foreground_package || '-' }}</div>
      </div>
    </div>

    <div class="chart-row">
      <div class="chart-card">
        <div class="chart-title">系统趋势</div>
        <div ref="sysChartRef" class="chart-box" />
      </div>
      <div class="chart-card">
        <div class="chart-title">网络趋势</div>
        <div ref="netChartRef" class="chart-box" />
      </div>
    </div>

    <div class="info-row">
      <div class="info-card">
        <div class="info-title">设备信息</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="k">品牌/型号</span>
            <span class="v">{{ info.brand || '-' }} / {{ info.model || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="k">Android 版本</span>
            <span class="v">{{ info.android_version || '-' }} / SDK {{ info.sdk || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="k">分辨率/密度</span>
            <span class="v">{{ info.resolution || '-' }} / {{ info.density || '-' }}</span>
          </div>
        </div>
      </div>
      <div class="info-card">
        <div class="info-title">健康状态</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="k">电池状态</span>
            <span class="v">{{ metrics.battery_status || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="k">电池健康</span>
            <span class="v">{{ metrics.battery_health || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="k">温控状态</span>
            <span class="v" :class="{ 'warn-text': !!thermalHint }">{{ metrics.thermal_status || '-' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { getDevicePerformance } from '@/api/app-automation'

const props = defineProps({
  deviceId: { type: [String, Number], required: true },
  active: { type: Boolean, default: false }
})

const manualLoading = ref(false)
const autoRefresh = ref(true)
const intervalSec = ref(2)
const metrics = reactive({
  cpu_percent: 0,
  cpu_cores: 0,
  mem_percent: 0,
  mem_used_mb: 0,
  mem_total_mb: 0,
  net_rx_bytes: 0,
  net_tx_bytes: 0,
  battery_percent: 0,
  battery_temp: null,
  battery_status: '',
  battery_health: '',
  thermal_status: '',
  storage_percent: 0,
  foreground_package: ''
})
const info = reactive({
  brand: '',
  model: '',
  android_version: '',
  sdk: '',
  resolution: '',
  density: ''
})

const history = reactive({
  times: [],
  cpu: [],
  mem: [],
  battery: [],
  rx: [],
  tx: []
})

const rxSpeed = ref(0)
const txSpeed = ref(0)
let lastNet = null
let timer = null
const MAX_POINTS = 30

const sysChartRef = ref(null)
const netChartRef = ref(null)
let sysChart = null
let netChart = null

const thermalHint = computed(() => {
  const t = metrics.thermal_status || ''
  if (!t) return ''
  if (/error|exception|unavailable|失败|denied/i.test(t)) return t.length > 36 ? `${t.slice(0, 36)}…` : t
  return ''
})

function formatNum(n) {
  if (n == null || Number.isNaN(Number(n))) return '-'
  return Number(n).toFixed(1)
}

function formatBytes(bytes) {
  const b = Number(bytes) || 0
  if (b < 1024) return `${b} B`
  if (b < 1024 ** 2) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 ** 3) return `${(b / 1024 ** 2).toFixed(1)} MB`
  return `${(b / 1024 ** 3).toFixed(2)} GB`
}

function formatSpeed(bps) {
  const v = Number(bps) || 0
  if (v < 1024) return `${v.toFixed(1)} B/s`
  if (v < 1024 ** 2) return `${(v / 1024).toFixed(1)} KB/s`
  return `${(v / 1024 ** 2).toFixed(2)} MB/s`
}

function timeLabel(ts = Date.now()) {
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function pushHistory(sample, rxBps, txBps) {
  history.times.push(timeLabel(sample.timestamp || Date.now()))
  history.cpu.push(sample.cpu_percent || 0)
  history.mem.push(sample.mem_percent || 0)
  history.battery.push(sample.battery_percent || 0)
  history.rx.push(Number((rxBps / 1024).toFixed(2)))
  history.tx.push(Number((txBps / 1024).toFixed(2)))
  while (history.times.length > MAX_POINTS) {
    history.times.shift()
    history.cpu.shift()
    history.mem.shift()
    history.battery.shift()
    history.rx.shift()
    history.tx.shift()
  }
}

function applySample(sample) {
  Object.assign(metrics, {
    cpu_percent: sample.cpu_percent,
    cpu_cores: sample.cpu_cores,
    mem_percent: sample.mem_percent,
    mem_used_mb: sample.mem_used_mb,
    mem_total_mb: sample.mem_total_mb,
    net_rx_bytes: sample.net_rx_bytes,
    net_tx_bytes: sample.net_tx_bytes,
    battery_percent: sample.battery_percent,
    battery_temp: sample.battery_temp,
    battery_status: sample.battery_status,
    battery_health: sample.battery_health,
    thermal_status: sample.thermal_status,
    storage_percent: sample.storage_percent,
    foreground_package: sample.foreground_package
  })
  if (sample.device_info) Object.assign(info, sample.device_info)

  const now = sample.timestamp || Date.now()
  let rxBps = 0
  let txBps = 0
  if (lastNet) {
    const dt = Math.max((now - lastNet.ts) / 1000, 0.5)
    rxBps = Math.max((sample.net_rx_bytes - lastNet.rx) / dt, 0)
    txBps = Math.max((sample.net_tx_bytes - lastNet.tx) / dt, 0)
  }
  lastNet = { ts: now, rx: sample.net_rx_bytes, tx: sample.net_tx_bytes }
  rxSpeed.value = rxBps
  txSpeed.value = txBps
  pushHistory(sample, rxBps, txBps)
  renderCharts()
}

async function refreshOnce({ showLoading = false } = {}) {
  if (!props.deviceId) return
  if (showLoading) manualLoading.value = true
  try {
    const { data } = await getDevicePerformance(props.deviceId)
    if (data?.success && data.data) {
      applySample(data.data)
    }
  } catch (e) {
    console.warn('性能采集失败', e)
  } finally {
    if (showLoading) manualLoading.value = false
  }
}

function manualRefresh() {
  return refreshOnce({ showLoading: true })
}

function resetHistory() {
  history.times = []
  history.cpu = []
  history.mem = []
  history.battery = []
  history.rx = []
  history.tx = []
  lastNet = null
  rxSpeed.value = 0
  txSpeed.value = 0
  renderCharts()
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function startTimer() {
  stopTimer()
  if (!props.active || !autoRefresh.value) return
  refreshOnce()
  timer = setInterval(refreshOnce, intervalSec.value * 1000)
}

function ensureCharts() {
  if (sysChartRef.value && !sysChart) {
    sysChart = echarts.init(sysChartRef.value)
  }
  if (netChartRef.value && !netChart) {
    netChart = echarts.init(netChartRef.value)
  }
}

function renderCharts() {
  ensureCharts()
  if (sysChart) {
    sysChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['CPU', '内存', '电池'], top: 0, right: 0, textStyle: { fontSize: 11 } },
      grid: { left: 40, right: 16, top: 32, bottom: 28 },
      xAxis: {
        type: 'category',
        data: history.times,
        boundaryGap: false,
        axisLabel: { fontSize: 10, color: '#909399' }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%', fontSize: 10, color: '#909399' },
        splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } }
      },
      series: [
        { name: 'CPU', type: 'line', smooth: true, showSymbol: true, symbolSize: 5, data: history.cpu, itemStyle: { color: '#409EFF' } },
        { name: '内存', type: 'line', smooth: true, showSymbol: true, symbolSize: 5, data: history.mem, itemStyle: { color: '#E6A23C' } },
        { name: '电池', type: 'line', smooth: true, showSymbol: true, symbolSize: 5, data: history.battery, itemStyle: { color: '#67C23A' } }
      ]
    })
  }
  if (netChart) {
    netChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['下行', '上行'], top: 0, right: 0, textStyle: { fontSize: 11 } },
      grid: { left: 48, right: 16, top: 32, bottom: 28 },
      xAxis: {
        type: 'category',
        data: history.times,
        boundaryGap: false,
        axisLabel: { fontSize: 10, color: '#909399' }
      },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: '{value} KB/s', fontSize: 10, color: '#909399' },
        splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } }
      },
      series: [
        {
          name: '下行',
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.rx,
          itemStyle: { color: '#409EFF' },
          areaStyle: { color: 'rgba(103, 194, 58, 0.18)' }
        },
        {
          name: '上行',
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.tx,
          itemStyle: { color: '#E6A23C' }
        }
      ]
    })
  }
}

function onResize() {
  sysChart?.resize()
  netChart?.resize()
}

watch(
  () => [props.active, autoRefresh.value, intervalSec.value, props.deviceId],
  async ([active]) => {
    if (active) {
      await nextTick()
      ensureCharts()
      renderCharts()
      startTimer()
      onResize()
    } else {
      stopTimer()
    }
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('resize', onResize)
  sysChart?.dispose()
  netChart?.dispose()
  sysChart = null
  netChart = null
})
</script>

<style scoped>
.perf-panel {
  height: 100%;
  overflow: auto;
  padding: 12px 16px 16px;
  box-sizing: border-box;
  background: #fff;
}

.perf-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.perf-title-block h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.perf-title-block p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}

.perf-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.ctrl-label {
  font-size: 13px;
  color: #606266;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.metric-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 10px;
  background: #fff;
  min-width: 0;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.metric-sub {
  margin-top: 6px;
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-sub.pkg {
  color: #606266;
}

.warn-text {
  color: #f56c6c;
}

.chart-row,
.info-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.chart-card,
.info-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  min-width: 0;
}

.chart-title,
.info-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.chart-box {
  width: 100%;
  height: 220px;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.info-item .k {
  color: #909399;
  flex-shrink: 0;
}

.info-item .v {
  color: #303133;
  text-align: right;
  word-break: break-all;
}

@media (max-width: 1400px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .chart-row,
  .info-row {
    grid-template-columns: 1fr;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
