/**
 * 需求分析模块相关 API
 */
import request from '@/utils/api'

// ==================== 生成行为配置 ====================

// 获取所有生成行为配置
export function getGenerationConfigs(params) {
  return request({
    url: '/requirement-analysis/generation-config/',
    method: 'get',
    params
  })
}

// 获取生成行为配置详情
export function getGenerationConfigDetail(id) {
  return request({
    url: `/requirement-analysis/generation-config/${id}/`,
    method: 'get'
  })
}

// 创建生成行为配置
export function createGenerationConfig(data) {
  return request({
    url: '/requirement-analysis/generation-config/',
    method: 'post',
    data
  })
}

// 更新生成行为配置
export function updateGenerationConfig(id, data) {
  return request({
    url: `/requirement-analysis/generation-config/${id}/`,
    method: 'put',
    data
  })
}

// 删除生成行为配置
export function deleteGenerationConfig(id) {
  return request({
    url: `/requirement-analysis/generation-config/${id}/`,
    method: 'delete'
  })
}

// 获取活跃的生成行为配置
export function getActiveGenerationConfig() {
  return request({
    url: '/requirement-analysis/generation-config/active/',
    method: 'get'
  })
}

// ==================== AI 模型配置 ====================

// 获取所有 AI 模型配置
export function getAIModelConfigs(params) {
  return request({
    url: '/requirement-analysis/ai-models/',
    method: 'get',
    params
  })
}

// 获取活跃的 AI 模型配置
export function getActiveAIModelConfig(modelType, role) {
  return request({
    url: '/requirement-analysis/ai-models/active/',
    method: 'get',
    params: { model_type: modelType, role }
  })
}

// 创建 AI 模型配置
export function createAIModelConfig(data) {
  return request({
    url: '/requirement-analysis/ai-models/',
    method: 'post',
    data
  })
}

// 更新 AI 模型配置
export function updateAIModelConfig(id, data) {
  return request({
    url: `/requirement-analysis/ai-models/${id}/`,
    method: 'put',
    data
  })
}

// 删除 AI 模型配置
export function deleteAIModelConfig(id) {
  return request({
    url: `/requirement-analysis/ai-models/${id}/`,
    method: 'delete'
  })
}

// ==================== 提示词配置 ====================

// 获取所有提示词配置
export function getPromptConfigs(params) {
  return request({
    url: '/requirement-analysis/prompts/',
    method: 'get',
    params
  })
}

// 获取活跃的提示词配置
export function getActivePromptConfig(promptType) {
  return request({
    url: '/requirement-analysis/prompts/active/',
    method: 'get',
    params: { prompt_type: promptType }
  })
}

// 创建提示词配置
export function createPromptConfig(data) {
  return request({
    url: '/requirement-analysis/prompts/',
    method: 'post',
    data
  })
}

// 更新提示词配置
export function updatePromptConfig(id, data) {
  return request({
    url: `/requirement-analysis/prompts/${id}/`,
    method: 'put',
    data
  })
}

// 删除提示词配置
export function deletePromptConfig(id) {
  return request({
    url: `/requirement-analysis/prompts/${id}/`,
    method: 'delete'
  })
}

// ==================== 知识库管理 ====================

// 获取知识库列表
export function getKnowledgeBases(params) {
  return request({
    url: '/requirement-analysis/knowledge-bases/',
    method: 'get',
    params
  })
}

// 获取知识库详情
export function getKnowledgeBaseDetail(id) {
  return request({
    url: `/requirement-analysis/knowledge-bases/${id}/`,
    method: 'get'
  })
}

// 创建知识库
export function createKnowledgeBase(data) {
  return request({
    url: '/requirement-analysis/knowledge-bases/',
    method: 'post',
    data
  })
}

// 更新知识库
export function updateKnowledgeBase(id, data) {
  return request({
    url: `/requirement-analysis/knowledge-bases/${id}/`,
    method: 'put',
    data
  })
}

// 删除知识库
export function deleteKnowledgeBase(id) {
  return request({
    url: `/requirement-analysis/knowledge-bases/${id}/`,
    method: 'delete'
  })
}

// 获取知识库下的文档
export function getKnowledgeBaseDocuments(id) {
  return request({
    url: `/requirement-analysis/knowledge-bases/${id}/documents/`,
    method: 'get'
  })
}

// 获取知识库文档列表
export function getKnowledgeDocuments(params) {
  return request({
    url: '/requirement-analysis/knowledge-documents/',
    method: 'get',
    params
  })
}

// 上传知识库文档
export function uploadKnowledgeDocument(formData) {
  return request({
    url: '/requirement-analysis/knowledge-documents/',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 删除知识库文档
export function deleteKnowledgeDocument(id) {
  return request({
    url: `/requirement-analysis/knowledge-documents/${id}/`,
    method: 'delete'
  })
}

// 重新提取知识库文档文本
export function extractKnowledgeDocumentText(id) {
  return request({
    url: `/requirement-analysis/knowledge-documents/${id}/extract_text/`,
    method: 'post'
  })
}

// ==================== 知识库大模型配置 ====================

export function getKnowledgeLLMConfig() {
  return request({
    url: '/requirement-analysis/knowledge-llm-config/',
    method: 'get'
  })
}

export function createKnowledgeLLMConfig(data) {
  return request({
    url: '/requirement-analysis/knowledge-llm-config/',
    method: 'post',
    data
  })
}

export function updateKnowledgeLLMConfig(id, data) {
  return request({
    url: `/requirement-analysis/knowledge-llm-config/${id}/`,
    method: 'patch',
    data
  })
}

// ==================== 飞书文档（用户 OAuth） ====================

/** 拉取飞书 docx / wiki 正文 */
export function fetchFeishuDocument(url) {
  return request({
    url: '/requirement-analysis/feishu/fetch/',
    method: 'post',
    data: { url }
  })
}

/** 测试飞书应用凭证 */
export function testFeishuConnection() {
  return request({
    url: '/requirement-analysis/feishu/test-connection/',
    method: 'post'
  })
}

/** 当前用户飞书 OAuth 状态 */
export function getFeishuOAuthStatus() {
  return request({
    url: '/requirement-analysis/feishu/oauth_status/',
    method: 'get'
  })
}

/** 获取飞书授权跳转 URL */
export function getFeishuAuthorizeUrl() {
  return request({
    url: '/requirement-analysis/feishu/oauth_authorize_url/',
    method: 'get'
  })
}

/** 前端中转完成飞书 OAuth（提交 code/state） */
export function completeFeishuOAuth(data) {
  return request({
    url: '/requirement-analysis/feishu/oauth_complete/',
    method: 'post',
    data
  })
}

/** 断开飞书授权 */
export function disconnectFeishuOAuth() {
  return request({
    url: '/requirement-analysis/feishu/oauth_disconnect/',
    method: 'post'
  })
}
