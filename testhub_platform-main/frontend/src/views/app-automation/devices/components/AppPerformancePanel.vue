<template>
  <div class="perf-panel">
    <div class="perf-header">
      <div class="perf-controls">
        <span class="ctrl-label">跟随前台</span>
        <el-switch v-model="followForeground" />
        <span class="ctrl-label">自动</span>
        <el-switch v-model="autoRefresh" />
        <el-select v-model="intervalSec" size="small" class="interval-select" :disabled="!autoRefresh">
          <el-option :value="1" label="1s" />
          <el-option :value="2" label="2s" />
          <el-option :value="3" label="3s" />
          <el-option :value="5" label="5s" />
        </el-select>
        <el-select
          v-model="selectedPackage"
          size="small"
          class="pkg-select"
          filterable
          allow-create
          default-first-option
          :disabled="followForeground"
          placeholder="选择包名"
        >
          <el-option v-for="p in packageList" :key="p" :label="p" :value="p" />
        </el-select>
        <el-button size="small" :loading="pkgLoading" @click="refreshPackages">刷新包列表</el-button>
        <el-button size="small" :loading="manualLoading" @click="manualRefresh">刷新指标</el-button>
        <el-button size="small" @click="resetHistory">重置采样</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">包名</div>
        <div class="metric-value pkg-value" :title="metrics.package || '-'">
          {{ metrics.package || '-' }}
        </div>
        <div class="metric-sub">当前采样目标</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">应用 CPU</div>
        <div class="metric-value">{{ formatNum(metrics.cpu_percent) }}%</div>
        <div class="metric-sub">CPU 占用</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">PSS 内存</div>
        <div class="metric-value">{{ formatNum(metrics.pss_mb) }} MB</div>
        <div class="metric-sub">RSS {{ formatNum(metrics.rss_mb) }} MB</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">线程 / FD</div>
        <div class="metric-value">{{ metrics.threads || 0 }}</div>
        <div class="metric-sub">FD {{ metrics.fd_count || 0 }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">FPS</div>
        <div class="metric-value">{{ formatNum(metrics.fps) }}</div>
        <div class="metric-sub">总帧数 {{ metrics.total_frames || 0 }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">卡顿率</div>
        <div class="metric-value">{{ formatNum(metrics.jank_percent) }}%</div>
        <div class="metric-sub">卡顿帧 {{ metrics.jank_count || 0 }}</div>
      </div>
    </div>

    <div class="chart-row">
      <div class="chart-card">
        <div class="chart-title">CPU / 内存趋势</div>
        <div ref="cpuMemChartRef" class="chart-box" />
      </div>
      <div class="chart-card">
        <div class="chart-title">渲染趋势</div>
        <div ref="renderChartRef" class="chart-box" />
      </div>
    </div>

    <div class="info-row">
      <div class="info-card">
        <div class="info-title">进程信息</div>
        <el-table :data="processRows" size="small" stripe class="info-table">
          <el-table-column prop="pid" label="PID" width="90" />
          <el-table-column prop="activity" label="当前 Activity" min-width="160" show-overflow-tooltip />
        </el-table>
      </div>
      <div class="info-card">
        <div class="info-title">帧耗时分位数</div>
        <div class="percentile-grid">
          <div class="percentile-item">
            <span class="k">P50</span>
            <span class="v">{{ formatNum(metrics.p50_ms) }} ms</span>
          </div>
          <div class="percentile-item">
            <span class="k">P90</span>
            <span class="v">{{ formatNum(metrics.p90_ms) }} ms</span>
          </div>
          <div class="percentile-item">
            <span class="k">总帧数</span>
            <span class="v">{{ metrics.total_frames || 0 }}</span>
          </div>
          <div class="percentile-item">
            <span class="k">卡顿帧</span>
            <span class="v">{{ metrics.jank_count || 0 }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { getAppPackages, getAppPerformance } from '@/api/app-automation'

const props = defineProps({
  deviceId: { type: [String, Number], required: true },
  active: { type: Boolean, default: false },
  foregroundPackage: { type: String, default: '' }
})

const manualLoading = ref(false)
const pkgLoading = ref(false)
const autoRefresh = ref(true)
const followForeground = ref(true)
const intervalSec = ref(2)
const selectedPackage = ref('')
const packageList = ref([])

const metrics = reactive({
  package: '',
  pid: 0,
  activity: '',
  cpu_percent: 0,
  pss_mb: 0,
  rss_mb: 0,
  threads: 0,
  fd_count: 0,
  fps: 0,
  jank_percent: 0,
  jank_count: 0,
  total_frames: 0,
  p50_ms: 0,
  p90_ms: 0
})

const history = reactive({
  times: [],
  cpu: [],
  pss: [],
  fps: [],
  jank: [],
  fd: []
})

let timer = null
const MAX_POINTS = 30

const cpuMemChartRef = ref(null)
const renderChartRef = ref(null)
let cpuMemChart = null
let renderChart = null

const processRows = computed(() => {
  if (!metrics.package && !metrics.pid) return []
  return [
    {
      pid: metrics.pid || '-',
      activity: metrics.activity || '-'
    }
  ]
})

const targetPackage = computed(() => {
  if (followForeground.value) {
    return props.foregroundPackage || selectedPackage.value || ''
  }
  return selectedPackage.value || ''
})

function formatNum(n) {
  if (n == null || Number.isNaN(Number(n))) return '-'
  return Number(n).toFixed(1)
}

function timeLabel(ts = Date.now()) {
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function pushHistory(sample) {
  history.times.push(timeLabel(sample.timestamp || Date.now()))
  history.cpu.push(sample.cpu_percent || 0)
  history.pss.push(sample.pss_mb || 0)
  history.fps.push(sample.fps || 0)
  history.jank.push(sample.jank_percent || 0)
  history.fd.push(sample.fd_count || 0)
  while (history.times.length > MAX_POINTS) {
    history.times.shift()
    history.cpu.shift()
    history.pss.shift()
    history.fps.shift()
    history.jank.shift()
    history.fd.shift()
  }
}

function applySample(sample) {
  Object.assign(metrics, {
    package: sample.package || '',
    pid: sample.pid || 0,
    activity: sample.activity || '',
    cpu_percent: sample.cpu_percent,
    pss_mb: sample.pss_mb,
    rss_mb: sample.rss_mb,
    threads: sample.threads,
    fd_count: sample.fd_count,
    fps: sample.fps,
    jank_percent: sample.jank_percent,
    jank_count: sample.jank_count,
    total_frames: sample.total_frames,
    p50_ms: sample.p50_ms,
    p90_ms: sample.p90_ms
  })
  if (sample.package && !packageList.value.includes(sample.package)) {
    packageList.value = [sample.package, ...packageList.value]
  }
  if (followForeground.value && sample.package) {
    selectedPackage.value = sample.package
  }
  pushHistory(sample)
  renderCharts()
}

async function refreshPackages() {
  if (!props.deviceId) return
  pkgLoading.value = true
  try {
    const { data } = await getAppPackages(props.deviceId)
    if (data?.success && data.data) {
      packageList.value = data.data.packages || []
      const fg = data.data.foreground || props.foregroundPackage || ''
      if (fg && !packageList.value.includes(fg)) {
        packageList.value = [fg, ...packageList.value]
      }
      if (followForeground.value && fg) {
        selectedPackage.value = fg
      } else if (!selectedPackage.value && fg) {
        selectedPackage.value = fg
      } else if (!selectedPackage.value && packageList.value.length) {
        selectedPackage.value = packageList.value[0]
      }
    }
  } catch (e) {
    console.warn('刷新包列表失败', e)
  } finally {
    pkgLoading.value = false
  }
}

async function refreshOnce({ showLoading = false } = {}) {
  if (!props.deviceId) return
  if (followForeground.value && props.foregroundPackage) {
    selectedPackage.value = props.foregroundPackage
  }
  const pkg = targetPackage.value
  if (!pkg) {
    // 尚无包名时先拉列表
    await refreshPackages()
  }
  const packageName = targetPackage.value
  if (!packageName) return

  if (showLoading) manualLoading.value = true
  try {
    const { data } = await getAppPerformance(props.deviceId, { package: packageName })
    if (data?.success && data.data) {
      applySample(data.data)
    }
  } catch (e) {
    console.warn('应用性能采集失败', e)
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
  history.pss = []
  history.fps = []
  history.jank = []
  history.fd = []
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
  if (cpuMemChartRef.value && !cpuMemChart) {
    cpuMemChart = echarts.init(cpuMemChartRef.value)
  }
  if (renderChartRef.value && !renderChart) {
    renderChart = echarts.init(renderChartRef.value)
  }
}

function renderCharts() {
  ensureCharts()
  if (cpuMemChart) {
    cpuMemChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['应用 CPU', 'PSS 内存'],
        top: 0,
        right: 0,
        textStyle: { fontSize: 11 }
      },
      grid: { left: 44, right: 48, top: 32, bottom: 28 },
      xAxis: {
        type: 'category',
        data: history.times,
        boundaryGap: false,
        axisLabel: { fontSize: 10, color: '#909399' }
      },
      yAxis: [
        {
          type: 'value',
          name: '',
          min: 0,
          axisLabel: { formatter: '{value}%', fontSize: 10, color: '#909399' },
          splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } }
        },
        {
          type: 'value',
          name: '',
          min: 0,
          axisLabel: { formatter: '{value} MB', fontSize: 10, color: '#909399' },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: '应用 CPU',
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.cpu,
          itemStyle: { color: '#409EFF' }
        },
        {
          name: 'PSS 内存',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.pss,
          itemStyle: { color: '#722ED1' }
        }
      ]
    })
  }
  if (renderChart) {
    renderChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['FPS', '卡顿率', 'FD'],
        top: 0,
        right: 0,
        textStyle: { fontSize: 11 }
      },
      grid: { left: 40, right: 48, top: 32, bottom: 28 },
      xAxis: {
        type: 'category',
        data: history.times,
        boundaryGap: false,
        axisLabel: { fontSize: 10, color: '#909399' }
      },
      yAxis: [
        {
          type: 'value',
          min: 0,
          axisLabel: { fontSize: 10, color: '#909399' },
          splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } }
        },
        {
          type: 'value',
          min: 0,
          max: 100,
          axisLabel: { formatter: '{value}%', fontSize: 10, color: '#909399' },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: 'FPS',
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.fps,
          itemStyle: { color: '#67C23A' }
        },
        {
          name: '卡顿率',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.jank,
          itemStyle: { color: '#F56C6C' }
        },
        {
          name: 'FD',
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbolSize: 5,
          data: history.fd,
          itemStyle: { color: '#E6A23C' }
        }
      ]
    })
  }
}

function onResize() {
  cpuMemChart?.resize()
  renderChart?.resize()
}

watch(
  () => props.foregroundPackage,
  (pkg) => {
    if (!pkg) return
    if (!packageList.value.includes(pkg)) {
      packageList.value = [pkg, ...packageList.value]
    }
    if (followForeground.value) {
      selectedPackage.value = pkg
    }
  }
)

watch(
  () => [props.active, autoRefresh.value, intervalSec.value, props.deviceId, followForeground.value],
  async ([active]) => {
    if (active) {
      await nextTick()
      ensureCharts()
      renderCharts()
      if (!packageList.value.length) {
        await refreshPackages()
      }
      startTimer()
      onResize()
    } else {
      stopTimer()
    }
  },
  { immediate: true }
)

watch(selectedPackage, () => {
  if (props.active && !followForeground.value) {
    refreshOnce()
  }
})

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('resize', onResize)
  cpuMemChart?.dispose()
  renderChart?.dispose()
  cpuMemChart = null
  renderChart = null
})
</script>

<style scoped>
.perf-panel {
  height: 100%;
  overflow: auto;
  padding: 12px 16px 16px;
  box-sizing: border-box;
  background: #f5f7f9;
}

.perf-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.perf-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

.ctrl-label {
  font-size: 13px;
  color: #606266;
}

.interval-select {
  width: 72px;
}

.pkg-select {
  width: 220px;
  min-width: 160px;
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
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
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

.metric-value.pkg-value {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-sub {
  margin-top: 6px;
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
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

.info-table {
  width: 100%;
}

.percentile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 8px 0;
}

.percentile-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
}

.percentile-item .k {
  color: #909399;
}

.percentile-item .v {
  color: #303133;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
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
