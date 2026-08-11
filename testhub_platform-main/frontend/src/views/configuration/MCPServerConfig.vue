<template>
  <div class="mcp-config" v-loading="loading">
    <div class="page-header">
      <h1>{{ $t('configuration.mcp.title') }}</h1>
      <p>{{ $t('configuration.mcp.description') }}</p>
    </div>

    <div class="status-card">
      <h3 class="card-title">{{ $t('configuration.mcp.runningStatus') }}</h3>
      <div class="status-grid">
        <div class="status-item">
          <div class="status-label">{{ $t('configuration.mcp.connectedServers') }}</div>
          <div class="status-value">{{ summary.connected }}/{{ summary.total }}</div>
        </div>
        <div class="status-item">
          <div class="status-label">{{ $t('configuration.mcp.availableTools') }}</div>
          <div class="status-value">{{ summary.tools }}</div>
        </div>
      </div>
      <div class="status-actions">
        <button class="outline-btn" type="button" :disabled="reconnecting" @click="onReconnectAll">
          {{ reconnecting ? $t('configuration.mcp.reconnecting') : $t('configuration.mcp.reconnectAll') }}
        </button>
        <button class="outline-btn" type="button" :disabled="loading" @click="refreshAll">
          {{ $t('configuration.mcp.refresh') }}
        </button>
      </div>
    </div>

    <div class="list-card">
      <div class="list-header">
        <h3 class="card-title">{{ $t('configuration.mcp.serverList') }}</h3>
        <button class="add-btn" type="button" @click="openAddModal">
          {{ $t('configuration.mcp.addServer') }}
        </button>
      </div>

      <div v-if="availablePresets.length" class="preset-box">
        <div class="preset-title">{{ $t('configuration.mcp.quickAdd') }}</div>
        <div
          v-for="preset in availablePresets"
          :key="preset.key"
          class="preset-row"
        >
          <div class="preset-info">
            <div class="preset-name">{{ preset.label }}</div>
            <div class="preset-desc">{{ preset.description }}</div>
          </div>
          <button
            class="preset-btn"
            type="button"
            :disabled="addingPreset === preset.key"
            @click="onAddPreset(preset)"
          >
            {{ addingPreset === preset.key ? $t('configuration.mcp.adding') : $t('configuration.mcp.oneClickAdd') }}
          </button>
        </div>
      </div>

      <div v-if="servers.length" class="server-list">
        <div v-for="server in servers" :key="server.id" class="server-card">
          <div class="server-top">
            <div class="server-main">
              <div class="server-title-row">
                <h4 class="server-name">{{ server.name }}</h4>
                <div class="badges">
                  <span
                    class="badge"
                    :class="server.is_enabled ? 'badge-enabled' : 'badge-disabled'"
                  >
                    {{ server.is_enabled ? $t('configuration.common.enabled') : $t('configuration.common.disabled') }}
                  </span>
                  <span class="badge badge-transport">{{ server.transport }}</span>
                </div>
              </div>
              <p class="server-desc">
                {{ server.description || $t('configuration.mcp.noDescription') }}
              </p>
              <div class="tools-meta">
                <span
                  class="status-dot"
                  :class="{
                    ok: server.connection_status === 'connected',
                    err: server.connection_status === 'error',
                    warn: server.connection_status === 'disconnected' || server.connection_status === 'unknown'
                  }"
                />
                <span class="tools-text">
                  {{ statusText(server) }}
                  <template v-if="(server.tools || []).length">
                    · {{ (server.tools || []).length }} tools
                    <button
                      class="link-btn"
                      type="button"
                      @click="toggleTools(server.id)"
                    >
                      {{ expandedMap[server.id] ? $t('configuration.mcp.collapseTools') : $t('configuration.mcp.expandTools') }}
                    </button>
                  </template>
                </span>
              </div>
              <div v-if="expandedMap[server.id] && (server.tools || []).length" class="tools-panel">
                <span v-for="tool in server.tools" :key="tool" class="tool-pill">{{ tool }}</span>
              </div>
            </div>
          </div>

          <div class="server-footer">
            <el-switch
              :model-value="server.is_enabled"
              :loading="server.toggling"
              @change="(val) => onToggle(server, val)"
            />
            <div class="footer-actions">
              <button class="action-btn" type="button" @click="openEditModal(server)">
                {{ $t('configuration.common.edit') }}
              </button>
              <button
                class="action-btn"
                type="button"
                :disabled="server.testing"
                @click="onTest(server)"
              >
                {{ server.testing ? $t('configuration.mcp.testing') : $t('configuration.mcp.testConnection') }}
              </button>
              <button class="action-btn danger" type="button" @click="onDelete(server)">
                {{ $t('configuration.common.delete') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!loading" class="empty-state">
        <h3>{{ $t('configuration.mcp.emptyTitle') }}</h3>
        <p>{{ $t('configuration.mcp.emptyDescription') }}</p>
      </div>
    </div>

    <el-dialog
      v-model="showModal"
      :title="isEditing ? $t('configuration.mcp.editServer') : $t('configuration.mcp.addServer')"
      width="640px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item :label="$t('configuration.mcp.name')" prop="name">
          <el-input
            v-model="form.name"
            :disabled="isEditing"
            :placeholder="$t('configuration.mcp.namePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('configuration.mcp.serverDescription')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            :placeholder="$t('configuration.mcp.descriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('configuration.mcp.transport')" prop="transport">
          <el-select v-model="form.transport" style="width: 100%">
            <el-option label="stdio" value="stdio" />
            <el-option label="SSE" value="sse" />
            <el-option label="HTTP" value="http" />
          </el-select>
        </el-form-item>
        <template v-if="form.transport === 'stdio'">
          <el-form-item :label="$t('configuration.mcp.command')" prop="command">
            <el-input v-model="form.command" :placeholder="$t('configuration.mcp.commandPlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('configuration.mcp.args')" prop="argsText">
            <el-input
              v-model="form.argsText"
              type="textarea"
              :rows="2"
              :placeholder="$t('configuration.mcp.argsPlaceholder')"
            />
          </el-form-item>
          <el-form-item :label="$t('configuration.mcp.env')" prop="envText">
            <el-input
              v-model="form.envText"
              type="textarea"
              :rows="3"
              :placeholder="$t('configuration.mcp.envPlaceholder')"
            />
          </el-form-item>
        </template>
        <el-form-item v-else :label="$t('configuration.mcp.url')" prop="url">
          <el-input v-model="form.url" :placeholder="$t('configuration.mcp.urlPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('configuration.mcp.enabled')">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModal = false">{{ $t('configuration.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="saveServer">
          {{ $t('configuration.common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addMCPPreset,
  createMCPServer,
  deleteMCPServer,
  getMCPPresets,
  getMCPServers,
  getMCPStatusSummary,
  reconnectAllMCPServers,
  testMCPServerConnection,
  toggleMCPServer,
  updateMCPServer
} from '@/api/core'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)
const reconnecting = ref(false)
const addingPreset = ref('')
const servers = ref([])
const presets = ref([])
const summary = reactive({ connected: 0, total: 0, tools: 0 })
const expandedMap = reactive({})
const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  description: '',
  transport: 'stdio',
  command: '',
  argsText: '',
  envText: '',
  url: '',
  is_enabled: true
})

const rules = computed(() => ({
  name: [
    { required: true, message: t('configuration.mcp.nameRequired'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && /\s/.test(value)) {
          callback(new Error(t('configuration.mcp.nameNoSpace')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  transport: [{ required: true, message: t('configuration.mcp.transportRequired'), trigger: 'change' }],
  command: [
    {
      validator: (_rule, value, callback) => {
        if (form.transport === 'stdio' && !(value || '').trim()) {
          callback(new Error(t('configuration.mcp.commandRequired')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  url: [
    {
      validator: (_rule, value, callback) => {
        if (form.transport !== 'stdio' && !(value || '').trim()) {
          callback(new Error(t('configuration.mcp.urlRequired')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}))

const unwrapData = (res) => res?.data ?? res

const unwrapList = (res) => {
  const data = unwrapData(res)
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.data)) return data.data
  return []
}

const availablePresets = computed(() => {
  const names = new Set(servers.value.map((s) => s.name))
  return presets.value.filter((p) => !names.has(p.name))
})

function statusText(server) {
  const map = {
    connected: t('configuration.mcp.statusConnected'),
    disconnected: t('configuration.mcp.statusDisconnected'),
    error: t('configuration.mcp.statusError'),
    unknown: t('configuration.mcp.statusUnknown')
  }
  return map[server.connection_status] || map.unknown
}

function parseArgs(text) {
  const raw = (text || '').trim()
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed.map(String)
  } catch {
    // fallthrough
  }
  return raw.split(/\s+/).filter(Boolean)
}

function parseEnv(text) {
  const raw = (text || '').trim()
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return Object.fromEntries(Object.entries(parsed).map(([k, v]) => [String(k), String(v)]))
    }
  } catch {
    // KEY=VALUE lines
  }
  const env = {}
  raw.split(/\r?\n/).forEach((line) => {
    const idx = line.indexOf('=')
    if (idx > 0) {
      env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
    }
  })
  return env
}

function updateSummaryFromLocal() {
  const enabled = servers.value.filter((s) => s.is_enabled)
  summary.total = servers.value.length
  summary.connected = enabled.filter((s) => s.connection_status === 'connected').length
  summary.tools = enabled
    .filter((s) => s.connection_status === 'connected')
    .reduce((acc, s) => acc + (s.tools || []).length, 0)
}

async function loadSummary() {
  try {
    const data = unwrapData(await getMCPStatusSummary())
    summary.connected = data.connected || 0
    summary.total = data.total || 0
    summary.tools = data.tools || 0
  } catch {
    updateSummaryFromLocal()
  }
}

async function loadServers() {
  loading.value = true
  try {
    const list = unwrapList(await getMCPServers())
    servers.value = list.map((item) => ({
      ...item,
      toggling: false,
      testing: false
    }))
    servers.value.forEach((s) => {
      if (s.connection_status === 'connected' && (s.tools || []).length && expandedMap[s.id] === undefined) {
        expandedMap[s.id] = true
      }
    })
    await loadSummary()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.mcp.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadPresets() {
  try {
    presets.value = unwrapList(await getMCPPresets())
  } catch {
    presets.value = []
  }
}

async function refreshAll() {
  await Promise.all([loadServers(), loadPresets()])
}

function toggleTools(id) {
  expandedMap[id] = !expandedMap[id]
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.transport = 'stdio'
  form.command = ''
  form.argsText = ''
  form.envText = ''
  form.url = ''
  form.is_enabled = true
  isEditing.value = false
  editingId.value = null
}

function openAddModal() {
  resetForm()
  showModal.value = true
}

function openEditModal(server) {
  isEditing.value = true
  editingId.value = server.id
  form.name = server.name
  form.description = server.description || ''
  form.transport = server.transport || 'stdio'
  form.command = server.command || ''
  form.argsText = Array.isArray(server.args) ? JSON.stringify(server.args) : ''
  form.envText = server.env && Object.keys(server.env).length ? JSON.stringify(server.env, null, 2) : ''
  form.url = server.url || ''
  form.is_enabled = !!server.is_enabled
  showModal.value = true
}

async function saveServer() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  const payload = {
    name: form.name.trim(),
    description: form.description || '',
    transport: form.transport,
    command: form.transport === 'stdio' ? form.command.trim() : '',
    args: form.transport === 'stdio' ? parseArgs(form.argsText) : [],
    env: form.transport === 'stdio' ? parseEnv(form.envText) : {},
    url: form.transport !== 'stdio' ? form.url.trim() : '',
    is_enabled: form.is_enabled
  }

  saving.value = true
  try {
    if (isEditing.value) {
      await updateMCPServer(editingId.value, payload)
      ElMessage.success(t('configuration.mcp.messages.updateSuccess'))
    } else {
      await createMCPServer(payload)
      ElMessage.success(t('configuration.mcp.messages.createSuccess'))
    }
    showModal.value = false
    await refreshAll()
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.detail ||
      error?.response?.data?.name?.[0] ||
      t('configuration.mcp.messages.saveFailed')
    )
  } finally {
    saving.value = false
  }
}

async function onToggle(server, val) {
  server.toggling = true
  try {
    const data = unwrapData(await toggleMCPServer(server.id, val))
    Object.assign(server, data, { toggling: false, testing: false })
    updateSummaryFromLocal()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.mcp.messages.toggleFailed'))
  } finally {
    server.toggling = false
  }
}

async function onTest(server) {
  server.testing = true
  try {
    const data = unwrapData(await testMCPServerConnection(server.id))
    if (data?.server) {
      Object.assign(server, data.server, { testing: false })
    }
    expandedMap[server.id] = true
    updateSummaryFromLocal()
    ElMessage.success(data?.message || t('configuration.mcp.messages.testSuccess', { count: data?.tools_count || 0 }))
  } catch (error) {
    const detail = error?.response?.data?.detail || t('configuration.mcp.messages.testFailed')
    if (error?.response?.data?.server) {
      Object.assign(server, error.response.data.server, { testing: false })
    }
    updateSummaryFromLocal()
    ElMessage.error(detail)
  } finally {
    server.testing = false
  }
}

async function onDelete(server) {
  try {
    await ElMessageBox.confirm(
      t('configuration.mcp.messages.deleteConfirm', { name: server.name }),
      t('configuration.mcp.messages.deleteTitle'),
      {
        type: 'warning',
        confirmButtonText: t('configuration.common.delete'),
        cancelButtonText: t('configuration.common.cancel')
      }
    )
    await deleteMCPServer(server.id)
    ElMessage.success(t('configuration.mcp.messages.deleteSuccess'))
    await refreshAll()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error?.response?.data?.detail || t('configuration.mcp.messages.deleteFailed'))
  }
}

async function onAddPreset(preset) {
  addingPreset.value = preset.key
  try {
    const data = unwrapData(await addMCPPreset(preset.key))
    ElMessage.success(
      t('configuration.mcp.messages.presetAdded', {
        name: preset.label,
        count: (data.tools || []).length
      })
    )
    await refreshAll()
    if (data?.id) expandedMap[data.id] = true
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.mcp.messages.presetFailed'))
  } finally {
    addingPreset.value = ''
  }
}

async function onReconnectAll() {
  reconnecting.value = true
  try {
    const data = unwrapData(await reconnectAllMCPServers())
    ElMessage.success(
      t('configuration.mcp.messages.reconnectDone', {
        connected: data.connected || 0,
        total: data.total || 0,
        tools: data.tools || 0
      })
    )
    await refreshAll()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.mcp.messages.reconnectFailed'))
  } finally {
    reconnecting.value = false
  }
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.mcp-config {
  max-width: 1100px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.page-header p {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
}

.status-card,
.list-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0 16px;
}

.status-item {
  background: #f9fafb;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 16px 18px;
}

.status-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}

.status-value {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
}

.status-actions {
  display: flex;
  gap: 10px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.outline-btn,
.action-btn,
.add-btn,
.preset-btn {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.outline-btn,
.action-btn {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
  padding: 8px 14px;
}

.outline-btn:hover,
.action-btn:hover {
  border-color: var(--th-color-primary, #6c5ce7);
  color: var(--th-color-primary, #6c5ce7);
}

.add-btn,
.preset-btn {
  background: var(--th-color-primary, #6c5ce7);
  border: 1px solid var(--th-color-primary, #6c5ce7);
  color: #fff;
  padding: 8px 16px;
}

.add-btn:hover,
.preset-btn:hover {
  filter: brightness(1.05);
}

.action-btn.danger {
  border-color: #fca5a5;
  color: #dc2626;
  background: #fff5f5;
}

.action-btn.danger:hover {
  background: #fee2e2;
  border-color: #f87171;
}

.outline-btn:disabled,
.action-btn:disabled,
.add-btn:disabled,
.preset-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.preset-box {
  border: 1px dashed #93c5fd;
  background: #f0f7ff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.preset-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d4ed8;
  margin-bottom: 10px;
}

.preset-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 12px 14px;
}

.preset-name {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.preset-desc {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}

.server-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.server-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 18px;
  background: #fff;
}

.server-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.server-name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.badge-enabled {
  background: #dcfce7;
  color: #15803d;
}

.badge-disabled {
  background: #f3f4f6;
  color: #6b7280;
}

.badge-transport {
  background: #f3f4f6;
  color: #4b5563;
}

.server-desc {
  margin: 8px 0 10px;
  font-size: 13px;
  color: #6b7280;
}

.tools-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
  flex-shrink: 0;
}

.status-dot.ok {
  background: #22c55e;
}

.status-dot.err {
  background: #ef4444;
}

.status-dot.warn {
  background: #f59e0b;
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--th-color-primary, #6c5ce7);
  cursor: pointer;
  padding: 0;
  margin-left: 4px;
  font-size: 13px;
}

.tools-panel {
  margin-top: 12px;
  background: #f3f4f6;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tool-pill {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #374151;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.server-footer {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-state {
  text-align: center;
  padding: 36px 16px 20px;
  color: #6b7280;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #111827;
}

.empty-state p {
  margin: 0;
  font-size: 13px;
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .server-footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
