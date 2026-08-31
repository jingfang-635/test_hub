// 侧边栏完整菜单注册表：作为「功能模块开关」配置页的单一数据源
//
// key 约定：
//   - 模块级入口 = 模块 key（如 ai-generation / data-factory）
//   - 页面菜单项 = 路由路径（如 /ai-generation/requirement-analysis）
//
// nameKey 为 i18n 键（zh-cn/en 的 nav.js），name 为中文兜底文本。

export const MODULE_GROUPS = [
  { key: 'ai-generation', nameKey: 'modules.aiGeneration', fallbackName: 'AI用例生成' },
  { key: 'api-testing', nameKey: 'modules.apiTesting', fallbackName: '接口测试' },
  { key: 'ui-automation', nameKey: 'modules.uiAutomation', fallbackName: 'UI自动化测试' },
  { key: 'app-automation', nameKey: 'modules.appAutomation', fallbackName: 'APP自动化测试' },
  { key: 'ai-intelligent-mode', nameKey: 'modules.aiIntelligentMode', fallbackName: 'AI智能模式' },
  { key: 'configuration', nameKey: 'modules.configuration', fallbackName: '配置中心' }
]

// 首页入口（location = home）
export const HOME_ENTRIES = [
  { key: 'data-factory', module: 'data-factory', name: '数据工厂', location: 'home', sort: 1 },
  { key: 'assistant', module: 'assistant', name: 'AI评测师', location: 'home', sort: 2 }
]

// 所有侧边栏页面菜单项 + 首页入口
export const MENU_ITEMS = [
  // ===== AI用例生成 =====
  { key: '/ai-generation/requirement-analysis', module: 'ai-generation', nameKey: 'menu.aiCaseGeneration', sort: 1 },
  { key: '/ai-generation/generated-testcases', module: 'ai-generation', nameKey: 'menu.aiGeneratedTestcases', sort: 2 },
  { key: '/ai-generation/projects', module: 'ai-generation', nameKey: 'menu.projectAndVersion', sort: 3 },
  { key: '/ai-generation/testcases', module: 'ai-generation', nameKey: 'menu.testCases', sort: 4 },
  { key: '/ai-generation/knowledge-base', module: 'ai-generation', nameKey: 'menu.knowledgeBaseManage', sort: 5 },
  { key: '/ai-generation/reviews', module: 'ai-generation', nameKey: 'menu.reviewList', sort: 6 },
  { key: '/ai-generation/review-templates', module: 'ai-generation', nameKey: 'menu.reviewTemplates', sort: 7 },
  { key: '/ai-generation/executions', module: 'ai-generation', nameKey: 'menu.testPlan', sort: 8 },
  { key: '/ai-generation/reports', module: 'ai-generation', nameKey: 'menu.testReport', sort: 9 },

  // ===== 接口测试 =====
  { key: '/api-testing/dashboard', module: 'api-testing', nameKey: 'menu.dashboard', sort: 1 },
  { key: '/api-testing/projects', module: 'api-testing', nameKey: 'menu.projectAndVersion', sort: 2 },
  { key: '/api-testing/interfaces', module: 'api-testing', nameKey: 'menu.interfaceManagement', sort: 3 },
  { key: '/api-testing/automation', module: 'api-testing', nameKey: 'menu.automationTesting', sort: 4 },
  { key: '/api-testing/history', module: 'api-testing', nameKey: 'menu.requestHistory', sort: 5 },
  { key: '/api-testing/environments', module: 'api-testing', nameKey: 'menu.environmentManagement', sort: 6 },
  { key: '/api-testing/reports', module: 'api-testing', nameKey: 'menu.testReport', sort: 7 },
  { key: '/api-testing/scheduled-tasks', module: 'api-testing', nameKey: 'menu.scheduledTasks', sort: 8 },
  { key: '/api-testing/notification-logs', module: 'api-testing', nameKey: 'menu.notificationList', sort: 9 },

  // ===== UI自动化测试 =====
  { key: '/ui-automation/dashboard', module: 'ui-automation', nameKey: 'menu.dashboard', sort: 1 },
  { key: '/ui-automation/projects', module: 'ui-automation', nameKey: 'menu.projectAndVersion', sort: 2 },
  { key: '/ui-automation/elements-enhanced', module: 'ui-automation', nameKey: 'menu.elementManagement', sort: 3 },
  { key: '/ui-automation/test-cases', module: 'ui-automation', nameKey: 'menu.caseManagement', sort: 4 },
  { key: '/ui-automation/scripts-enhanced', module: 'ui-automation', nameKey: 'menu.scriptGeneration', sort: 5 },
  { key: '/ui-automation/playwright-recording', module: 'ui-automation', nameKey: 'menu.playwrightScriptRecording', sort: 6 },
  { key: '/ui-automation/scripts', module: 'ui-automation', nameKey: 'menu.scriptList', sort: 7 },
  { key: '/ui-automation/suites', module: 'ui-automation', nameKey: 'menu.suiteManagement', sort: 8 },
  { key: '/ui-automation/executions', module: 'ui-automation', nameKey: 'menu.executionRecords', sort: 9 },
  { key: '/ui-automation/reports', module: 'ui-automation', nameKey: 'menu.testReport', sort: 10 },
  { key: '/ui-automation/scheduled-tasks', module: 'ui-automation', nameKey: 'menu.scheduledTasks', sort: 11 },
  { key: '/ui-automation/notification-logs', module: 'ui-automation', nameKey: 'menu.notificationList', sort: 12 },

  // ===== APP自动化测试 =====
  { key: '/app-automation/dashboard', module: 'app-automation', name: '数据看板', sort: 1 },
  { key: '/app-automation/projects', module: 'app-automation', nameKey: 'menu.projectAndVersion', sort: 2 },
  { key: '/app-automation/devices', module: 'app-automation', name: '设备管理', sort: 3 },
  { key: '/app-automation/packages', module: 'app-automation', name: '包名管理', sort: 4 },
  { key: '/app-automation/elements', module: 'app-automation', name: '元素管理', sort: 5 },
  { key: '/app-automation/scene-builder', module: 'app-automation', name: '用例编排', sort: 6 },
  { key: '/app-automation/test-cases', module: 'app-automation', name: '测试用例', sort: 7 },
  { key: '/app-automation/test-suites', module: 'app-automation', name: '测试套件', sort: 8 },
  { key: '/app-automation/executions', module: 'app-automation', name: '执行记录', sort: 9 },
  { key: '/app-automation/reports', module: 'app-automation', name: '测试报告', sort: 10 },
  { key: '/app-automation/scheduled-tasks', module: 'app-automation', name: '定时任务', sort: 11 },
  { key: '/app-automation/notification-logs', module: 'app-automation', name: '通知列表', sort: 12 },

  // ===== AI 智能模式 =====
  { key: '/ai-intelligent-mode/projects', module: 'ai-intelligent-mode', nameKey: 'menu.projectAndVersion', sort: 1 },
  { key: '/ai-intelligent-mode/testing', module: 'ai-intelligent-mode', nameKey: 'menu.aiIntelligentTesting', sort: 2 },
  { key: '/ai-intelligent-mode/cases', module: 'ai-intelligent-mode', nameKey: 'menu.aiCaseManagement', sort: 3 },
  { key: '/ai-intelligent-mode/execution-records', module: 'ai-intelligent-mode', nameKey: 'menu.aiExecutionRecords', sort: 4 },
  { key: '/ai-intelligent-mode/exploration', module: 'ai-intelligent-mode', name: 'AI探索测试', sort: 5 },

  // ===== 配置中心 =====
  { key: '/configuration/ai-model', module: 'configuration', nameKey: 'menu.aiModelConfig', sort: 1 },
  { key: '/configuration/prompt-config', module: 'configuration', nameKey: 'menu.promptConfig', sort: 2 },
  { key: '/configuration/generation-config', module: 'configuration', nameKey: 'menu.generationConfig', sort: 3 },
  { key: '/configuration/knowledge-llm', module: 'configuration', nameKey: 'menu.knowledgeBaseConfig', sort: 4 },
  { key: '/configuration/projects', module: 'configuration', nameKey: 'menu.projectAndVersion', sort: 5 },
  { key: '/configuration/ui-env', module: 'configuration', nameKey: 'menu.uiEnvConfig', sort: 6 },
  { key: '/configuration/app-env', module: 'configuration', name: 'APP环境配置', sort: 7 },
  { key: '/configuration/ai-mode', module: 'configuration', nameKey: 'menu.aiModeConfig', sort: 8 },
  { key: '/configuration/skills', module: 'configuration', nameKey: 'menu.skillsConfig', sort: 9 },
  { key: '/configuration/scheduled-task', module: 'configuration', nameKey: 'menu.scheduledTaskConfig', sort: 10 },
  { key: '/configuration/dify', module: 'configuration', nameKey: 'menu.difyConfig', sort: 11 },
  { key: '/configuration/mcp-server', module: 'configuration', nameKey: 'menu.mcpServerConfig', sort: 12 },
  { key: '/configuration/module-switch', module: 'configuration', nameKey: 'menu.moduleSwitchConfig', sort: 13 },
  { key: '/configuration/performance-stats', module: 'configuration', nameKey: 'menu.performanceStats', sort: 14 },
  { key: '/configuration/request-performance-log', module: 'configuration', nameKey: 'menu.requestPerformanceLog', sort: 15 },
  { key: '/configuration/notification-template', module: 'configuration', nameKey: 'menu.notificationTemplate', sort: 16 },

  ...HOME_ENTRIES
]

// 获取某分组下的菜单项（按 sort 升序）
export const menuItemsByModule = (moduleKey) =>
  MENU_ITEMS
    .filter((item) => item.module === moduleKey)
    .sort((a, b) => (a.sort || 0) - (b.sort || 0))

// 菜单项显示名：优先 i18n，缺失时用中文兜底
export const itemName = (item, t) => {
  if (item.nameKey) {
    const translated = t(item.nameKey)
    if (translated && translated !== item.nameKey) return translated
  }
  return item.name || item.nameKey || item.key
}
