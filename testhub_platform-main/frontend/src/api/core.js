/**
 * 核心功能模块相关 API
 */
import request from '@/utils/api'

// ==================== 统一通知配置 ====================

// 获取所有通知配置
export function getUnifiedNotificationConfigs(params) {
  return request({
    url: '/core/notification-configs/',
    method: 'get',
    params
  })
}

// 获取通知配置详情
export function getUnifiedNotificationConfigDetail(id) {
  return request({
    url: `/core/notification-configs/${id}/`,
    method: 'get'
  })
}

// 创建通知配置
export function createUnifiedNotificationConfig(data) {
  return request({
    url: '/core/notification-configs/',
    method: 'post',
    data
  })
}

// 更新通知配置
export function updateUnifiedNotificationConfig(id, data) {
  return request({
    url: `/core/notification-configs/${id}/`,
    method: 'put',
    data
  })
}

// 删除通知配置
export function deleteUnifiedNotificationConfig(id) {
  return request({
    url: `/core/notification-configs/${id}/`,
    method: 'delete'
  })
}

// 设置为默认配置
export function setDefaultNotificationConfig(id) {
  return request({
    url: `/core/notification-configs/${id}/set_default/`,
    method: 'post'
  })
}

// 获取所有启用的配置
export function getActiveNotificationConfigs() {
  return request({
    url: '/core/notification-configs/active_configs/',
    method: 'get'
  })
}

// ==================== 通知模板 ====================

export function getNotificationTemplates(params) {
  return request({
    url: '/core/notification-templates/',
    method: 'get',
    params
  })
}

export function getNotificationTemplateDetail(id) {
  return request({
    url: `/core/notification-templates/${id}/`,
    method: 'get'
  })
}

export function createNotificationTemplate(data) {
  return request({
    url: '/core/notification-templates/',
    method: 'post',
    data
  })
}

export function updateNotificationTemplate(id, data) {
  return request({
    url: `/core/notification-templates/${id}/`,
    method: 'put',
    data
  })
}

export function deleteNotificationTemplate(id) {
  return request({
    url: `/core/notification-templates/${id}/`,
    method: 'delete'
  })
}

// ==================== 请求性能日志 / 性能统计（详情） ====================

export function getRequestPerformanceLogDetail(id) {
  return request({
    url: `/core/request-performance-logs/${id}/`,
    method: 'get'
  })
}

export function getPerformanceStatisticsDetail(id) {
  return request({
    url: `/core/performance-statistics/${id}/`,
    method: 'get'
  })
}

// ==================== Skills 技能配置 ====================

export function getSkills(params) {
  return request({
    url: '/core/skills/',
    method: 'get',
    params
  })
}

export function getSkillDetail(id) {
  return request({
    url: `/core/skills/${id}/`,
    method: 'get'
  })
}

export function createSkill(data) {
  return request({
    url: '/core/skills/',
    method: 'post',
    data
  })
}

export function updateSkill(id, data) {
  return request({
    url: `/core/skills/${id}/`,
    method: 'put',
    data
  })
}

export function patchSkill(id, data) {
  return request({
    url: `/core/skills/${id}/`,
    method: 'patch',
    data
  })
}

export function deleteSkill(id) {
  return request({
    url: `/core/skills/${id}/`,
    method: 'delete'
  })
}

export function toggleSkill(id, isEnabled) {
  return request({
    url: `/core/skills/${id}/toggle/`,
    method: 'post',
    data: { is_enabled: isEnabled }
  })
}

export function exportSkill(id) {
  return request({
    url: `/core/skills/${id}/export/`,
    method: 'get',
    responseType: 'blob'
  })
}

export function importSkillMd(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/core/skills/import_md/',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// ==================== MCP 服务器配置 ====================

export function getMCPServers(params) {
  return request({
    url: '/core/mcp-servers/',
    method: 'get',
    params
  })
}

export function getMCPServerDetail(id) {
  return request({
    url: `/core/mcp-servers/${id}/`,
    method: 'get'
  })
}

export function createMCPServer(data) {
  return request({
    url: '/core/mcp-servers/',
    method: 'post',
    data
  })
}

export function updateMCPServer(id, data) {
  return request({
    url: `/core/mcp-servers/${id}/`,
    method: 'put',
    data
  })
}

export function deleteMCPServer(id) {
  return request({
    url: `/core/mcp-servers/${id}/`,
    method: 'delete'
  })
}

export function toggleMCPServer(id, isEnabled) {
  return request({
    url: `/core/mcp-servers/${id}/toggle/`,
    method: 'post',
    data: { is_enabled: isEnabled }
  })
}

export function testMCPServerConnection(id) {
  return request({
    url: `/core/mcp-servers/${id}/test_connection/`,
    method: 'post',
    timeout: 60000
  })
}

export function reconnectAllMCPServers() {
  return request({
    url: '/core/mcp-servers/reconnect_all/',
    method: 'post',
    timeout: 120000
  })
}

export function getMCPStatusSummary() {
  return request({
    url: '/core/mcp-servers/status_summary/',
    method: 'get'
  })
}

export function getMCPPresets() {
  return request({
    url: '/core/mcp-servers/presets/',
    method: 'get'
  })
}

export function addMCPPreset(key) {
  return request({
    url: '/core/mcp-servers/add_preset/',
    method: 'post',
    data: { key },
    timeout: 60000
  })
}

// ==================== 功能模块开关 ====================

export async function getModuleSwitches(params) {
  const res = await request({
    url: '/core/module-switches/',
    method: 'get',
    params
  })
  return res.data
}

export function getModuleSwitchDetail(id) {
  return request({
    url: `/core/module-switches/${id}/`,
    method: 'get'
  })
}

export function createModuleSwitch(data) {
  return request({
    url: '/core/module-switches/',
    method: 'post',
    data
  })
}

export function updateModuleSwitch(id, data) {
  return request({
    url: `/core/module-switches/${id}/`,
    method: 'put',
    data
  })
}

export function deleteModuleSwitch(id) {
  return request({
    url: `/core/module-switches/${id}/`,
    method: 'delete'
  })
}

export function toggleModuleSwitch(id, isEnabled) {
  return request({
    url: `/core/module-switches/${id}/toggle/`,
    method: 'post',
    data: { is_enabled: isEnabled }
  })
}

export async function getEnabledModuleSwitches() {
  const res = await request({
    url: '/core/module-switches/enabled/',
    method: 'get'
  })
  return res.data
}

// 按 key 切换开关状态（不存在则自动创建），用于尚未落库的菜单项
export function toggleModuleSwitchByKey(key, isEnabled, extra = {}) {
  return request({
    url: '/core/module-switches/toggle_by_key/',
    method: 'post',
    data: { key, is_enabled: isEnabled, ...extra }
  })
}
