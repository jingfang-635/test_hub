<template>
  <div class="device-management">
    <div class="device-header">
      <h3>设备管理</h3>
      <div class="device-actions">
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="refreshing"
          @click="refreshDevices"
        >
          刷新
        </el-button>
        <el-button
          type="success"
          :icon="Plus"
          @click="showAddRemoteDialog"
        >
          新建设备
        </el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="devices"
      class="device-table"
      :empty-text="emptyText"
      stripe
    >
      <el-table-column prop="name" label="设备名称" min-width="140">
        <template #default="{ row }">
          <span class="cell-text">{{ row.name || row.device_id }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="device_id" label="设备ID" min-width="160">
        <template #default="{ row }">
          <span class="cell-text mono">{{ row.device_id }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <span class="status-pill" :class="getStatusClass(row.status)">
            {{ getStatusText(row.status) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="locked_by" label="使用人" width="110" align="center">
        <template #default="{ row }">
          <span class="cell-muted">{{ row.locked_by_name || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="locked_at" label="最后使用时间" min-width="170" align="center">
        <template #default="{ row }">
          <span class="cell-muted">
            {{ row.locked_at ? formatDate(row.locked_at) : '-' }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="android_version" label="平台版本" width="100" align="center">
        <template #default="{ row }">
          <span class="cell-text">{{ row.android_version || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="connection_type" label="平台" width="120" align="center">
        <template #default="{ row }">
          <span class="platform-pill" :class="getPlatformClass(row.connection_type)">
            {{ getConnectionTypeName(row.connection_type) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="ip_address" label="IP地址" width="140" align="center">
        <template #default="{ row }">
          <span class="cell-muted">{{ row.ip_address || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="usage_count" label="使用次数" width="100" align="center">
        <template #default="{ row }">
          <span class="cell-muted">{{ row.usage_count ?? '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" min-width="280" fixed="right">
        <template #default="{ row }">
          <div class="action-links">
            <el-button
              v-if="canRemoteConnect(row)"
              link
              type="primary"
              :icon="Monitor"
              @click="openRemoteControl(row)"
            >
              远程连接
            </el-button>
            <el-button
              v-if="row.status !== 'locked'"
              link
              type="primary"
              @click="lockDevice(row)"
            >
              绑定
            </el-button>
            <el-button
              v-if="row.status === 'locked'"
              link
              type="success"
              @click="unlockDevice(row)"
            >
              解绑
            </el-button>
            <el-button
              v-if="isRemoteDevice(row.connection_type) && row.status === 'offline'"
              link
              type="warning"
              :loading="reconnectingDevices[row.id]"
              @click="reconnectDevice(row)"
            >
              重连
            </el-button>
            <el-button
              link
              type="primary"
              @click="viewDeviceInfo(row)"
            >
              详情
            </el-button>
            <el-button
              v-if="isRemoteDevice(row.connection_type) && (row.status === 'online' || row.status === 'available')"
              link
              type="warning"
              @click="disconnectDevice(row)"
            >
              断开
            </el-button>
            <el-button
              link
              type="danger"
              @click="handleDeleteDevice(row)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加远程设备对话框 -->
    <el-dialog
      v-model="addRemoteDialogVisible"
      title="新建设备"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="remoteDeviceFormRef"
        :model="remoteDeviceForm"
        :rules="remoteDeviceRules"
        label-width="100px"
      >
        <el-form-item label="IP地址" prop="ip_address">
          <el-input
            v-model="remoteDeviceForm.ip_address"
            placeholder="请输入远程设备IP地址"
          />
        </el-form-item>

        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="remoteDeviceForm.port"
            :min="1"
            :max="65535"
            placeholder="默认5555"
            style="width: 100%"
          />
        </el-form-item>

        <el-alert
          title="提示"
          type="info"
          :closable="false"
          style="margin-top: 10px"
        >
          <div>请确保：</div>
          <div>1. 远程设备已开启ADB调试</div>
          <div>2. 远程设备已开启网络ADB（adb tcpip 5555）</div>
          <div>3. 网络连接正常</div>
        </el-alert>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="addRemoteDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="connecting"
            @click="connectRemoteDevice"
          >
            连接
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 设备详情对话框 -->
    <el-dialog
      v-model="deviceInfoDialogVisible"
      title="设备详情"
      width="600px"
    >
      <el-descriptions v-if="selectedDevice" :column="2" border>
        <el-descriptions-item label="设备名称">
          {{ selectedDevice.name || selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item label="设备ID">
          {{ selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <span class="status-pill" :class="getStatusClass(selectedDevice.status)">
            {{ getStatusText(selectedDevice.status) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="使用人">
          {{ selectedDevice.locked_by_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="最后使用时间">
          {{ selectedDevice.locked_at ? formatDate(selectedDevice.locked_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="平台版本">
          {{ selectedDevice.android_version || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="平台">
          <span class="platform-pill" :class="getPlatformClass(selectedDevice.connection_type)">
            {{ getConnectionTypeName(selectedDevice.connection_type) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">
          {{ selectedDevice.ip_address || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="端口">
          {{ selectedDevice.port || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="使用次数">
          {{ selectedDevice.usage_count ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(selectedDevice.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDate(selectedDevice.updated_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="deviceInfoDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Monitor } from '@element-plus/icons-vue'
import {
  getDeviceList,
  discoverDevices,
  lockDevice as apiLockDevice,
  unlockDevice as apiUnlockDevice,
  connectDevice,
  disconnectDevice as apiDisconnectDevice,
  deleteDevice
} from '@/api/app-automation'
import { getDeviceStatusText, formatDateTime } from '@/utils/app-automation-helpers'

const router = useRouter()

const remoteDeviceFormRef = ref(null)

const devices = ref([])
const loading = ref(false)
const refreshing = ref(false)
const connecting = ref(false)
const reconnectingDevices = ref({})
const addRemoteDialogVisible = ref(false)
const deviceInfoDialogVisible = ref(false)
const selectedDevice = ref(null)
const emptyText = ref('暂无设备，请点击刷新或新建设备')
const refreshTimer = ref(null)

const remoteDeviceForm = ref({
  ip_address: '',
  port: 5555
})

const remoteDeviceRules = {
  ip_address: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    {
      pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
      message: '请输入有效的IP地址',
      trigger: 'blur'
    }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ]
}

const canRemoteConnect = (row) => {
  return row && row.status && row.status !== 'offline'
}

const openRemoteControl = (row) => {
  if (!canRemoteConnect(row)) {
    ElMessage.warning('设备离线，无法远程连接')
    return
  }
  router.push(`/app-automation/devices/${row.id}/remote`)
}

const getDevices = async () => {
  loading.value = true
  try {
    const res = await getDeviceList({ page: 1, page_size: 1000 })
    devices.value = res.data.results || []
    if (devices.value.length === 0) {
      emptyText.value = '暂无设备，请点击刷新或新建设备'
    }
  } catch (error) {
    console.error('获取设备列表失败:', error)
    ElMessage.error('获取设备列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const refreshDevices = async () => {
  refreshing.value = true
  try {
    const res = await discoverDevices()
    if (res.data.success) {
      devices.value = res.data.devices || []
      ElMessage.success(res.data.message || '设备列表已刷新')
    } else {
      ElMessage.error(res.data.message || '刷新设备列表失败')
    }
  } catch (error) {
    console.error('刷新设备列表失败:', error)
    ElMessage.error('刷新设备列表失败: ' + (error.message || '未知错误'))
  } finally {
    refreshing.value = false
  }
}

const showAddRemoteDialog = () => {
  addRemoteDialogVisible.value = true
  remoteDeviceForm.value = {
    ip_address: '',
    port: 5555
  }
  if (remoteDeviceFormRef.value) {
    remoteDeviceFormRef.value.clearValidate()
  }
}

const connectRemoteDevice = async () => {
  if (!remoteDeviceFormRef.value) return

  remoteDeviceFormRef.value.validate(async (valid) => {
    if (!valid) return

    connecting.value = true
    try {
      const res = await connectDevice({
        ip_address: remoteDeviceForm.value.ip_address,
        port: remoteDeviceForm.value.port
      })

      if (res.data.success) {
        ElMessage.success(res.data.message || '远程设备连接成功')
        addRemoteDialogVisible.value = false
        await getDevices()
      } else {
        ElMessage.error(res.data.message || '连接远程设备失败')
      }
    } catch (error) {
      console.error('连接远程设备失败:', error)
      ElMessage.error('连接远程设备失败: ' + (error.message || '未知错误'))
    } finally {
      connecting.value = false
    }
  })
}

const reconnectDevice = async (device) => {
  if (!device.ip_address || !device.port) {
    ElMessage.error('设备信息不完整，无法重连')
    return
  }

  reconnectingDevices.value[device.id] = true

  try {
    const res = await connectDevice({
      ip_address: device.ip_address,
      port: device.port
    })

    if (res.data.success) {
      ElMessage.success('设备重连成功')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '设备重连失败，请检查设备网络连接')
    }
  } catch (error) {
    console.error('设备重连失败:', error)
    ElMessage.error('设备重连失败，请检查设备网络连接')
  } finally {
    reconnectingDevices.value[device.id] = false
  }
}

const disconnectDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要断开设备 ${device.name || device.device_id} 的连接吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiDisconnectDevice(device.id)

    if (res.data.success) {
      ElMessage.success('设备已断开')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '断开设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('断开设备失败:', error)
      ElMessage.error('断开设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const viewDeviceInfo = (device) => {
  selectedDevice.value = device
  deviceInfoDialogVisible.value = true
}

const lockDevice = async (device) => {
  if (device.status === 'offline') {
    ElMessage.warning('设备离线，无法绑定')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要绑定设备 ${device.name || device.device_id} 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiLockDevice(device.id)

    if (res.data.success) {
      ElMessage.success('设备已绑定')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '绑定设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('绑定设备失败:', error)
      ElMessage.error('绑定设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const unlockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要解绑设备 ${device.name || device.device_id} 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await apiUnlockDevice(device.id)

    if (res.data.success) {
      ElMessage.success('设备已解绑')
      await getDevices()
    } else {
      ElMessage.error(res.data.message || '解绑设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('解绑设备失败:', error)
      ElMessage.error('解绑设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const handleDeleteDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备 ${device.name || device.device_id} 吗？删除后将无法恢复。`,
      '删除设备',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )

    const res = await deleteDevice(device.id)

    if (res.status === 204 || res.status === 200) {
      ElMessage.success('设备已删除')
      await getDevices()
    } else {
      ElMessage.error(res.data?.message || '删除设备失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除设备失败:', error)
      ElMessage.error('删除设备失败: ' + (error.message || '未知错误'))
    }
  }
}

const formatDate = formatDateTime
const getStatusText = getDeviceStatusText

const getStatusClass = (status) => {
  const map = {
    available: 'ok',
    online: 'ok',
    locked: 'warn',
    offline: 'err'
  }
  return map[status] || 'info'
}

const getPlatformClass = (type) => {
  if (type === 'usb' || type === 'real_device') return 'usb'
  if (type === 'emulator') return 'local'
  return 'remote'
}

const getConnectionTypeName = (type) => {
  const typeMap = {
    emulator: '本地模拟器',
    remote_emulator: '远程模拟器',
    remote: '远程设备',
    usb: 'USB设备',
    real_device: 'USB设备'
  }
  return typeMap[type] || type || '-'
}

const isRemoteDevice = (type) => {
  return type === 'remote_emulator' || type === 'remote'
}

onMounted(() => {
  getDevices()

  refreshTimer.value = setInterval(() => {
    getDevices()
  }, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<style scoped lang="scss">
.device-management {
  padding: 20px 24px;
  background: #fff;
  min-height: 100%;
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #1f2329;
  }
}

.device-actions {
  display: flex;
  gap: 12px;
}

.device-table {
  width: 100%;

  :deep(.el-table__header th) {
    background: #f5f7fa;
    color: #606266;
    font-weight: 600;
    font-size: 13px;
  }

  :deep(.el-table__row td) {
    padding: 14px 0;
    font-size: 13px;
    color: #303133;
  }

  :deep(.el-table__empty-text) {
    color: #909399;
  }
}

.cell-text {
  color: #303133;
}

.cell-text.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.cell-muted {
  color: #909399;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 20px;
  background: #f0f2f5;
  color: #606266;
}

.status-pill.ok {
  background: #f0f9eb;
  color: #67c23a;
}

.status-pill.warn {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-pill.err {
  background: #fef0f0;
  color: #f56c6c;
}

.status-pill.info {
  background: #f4f4f5;
  color: #909399;
}

.platform-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 20px;
  background: #ecf5ff;
  color: #409eff;
}

.platform-pill.usb {
  background: #ecf5ff;
  color: #409eff;
}

.platform-pill.local {
  background: #f0f9eb;
  color: #67c23a;
}

.platform-pill.remote {
  background: #fdf6ec;
  color: #e6a23c;
}

.action-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 8px;

  :deep(.el-button) {
    margin: 0;
    padding: 0;
    height: auto;
    font-size: 13px;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
  }

  :deep(.el-button:hover),
  :deep(.el-button:focus),
  :deep(.el-button:active),
  :deep(.el-button:focus-visible) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
  }

  :deep(.el-button::before),
  :deep(.el-button::after) {
    display: none !important;
  }

  :deep(.el-button .el-icon) {
    margin-right: 2px;
  }
}

.dialog-footer {
  text-align: right;
}
</style>
