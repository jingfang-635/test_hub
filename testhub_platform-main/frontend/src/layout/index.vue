<template>
  <div class="layout" :class="{ 'is-dark': appStore.isDark }">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside :width="sidebarWidth">
        <div class="logo" @click="router.push('/home')">
          <span class="logo-text">testhub</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          class="side-menu"
        >
          <!-- AI用例生成模块菜单 -->
          <template v-if="currentModule === 'ai-generation' && appStore.isModuleEnabled('ai-generation')">
            <el-sub-menu v-if="appStore.isAnyEnabled(['/ai-generation/requirement-analysis', '/ai-generation/generated-testcases'])" index="requirement">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.intelligentCaseGeneration') }}</span>
              </template>
              <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/requirement-analysis')" index="/ai-generation/requirement-analysis">{{ $t('menu.aiCaseGeneration') }}</el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/generated-testcases')" index="/ai-generation/generated-testcases">{{ $t('menu.aiGeneratedTestcases') }}</el-menu-item>
            </el-sub-menu>
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/projects')" index="/ai-generation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectAndVersion') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/testcases')" index="/ai-generation/testcases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.testCases') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/knowledge-base')" index="/ai-generation/knowledge-base">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.knowledgeBaseManage') }}</span>
            </el-menu-item>
            <el-sub-menu v-if="appStore.isAnyEnabled(['/ai-generation/reviews', '/ai-generation/review-templates'])" index="reviews">
              <template #title>
                <el-icon><Check /></el-icon>
                <span>{{ $t('menu.reviewManagement') }}</span>
              </template>
              <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/reviews')" index="/ai-generation/reviews">{{ $t('menu.reviewList') }}</el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/review-templates')" index="/ai-generation/review-templates">{{ $t('menu.reviewTemplates') }}</el-menu-item>
            </el-sub-menu>

            <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/executions')" index="/ai-generation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.testPlan') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-generation/reports')" index="/ai-generation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
          </template>

          <!-- 接口测试模块菜单 -->
          <template v-else-if="currentModule === 'api-testing' && appStore.isModuleEnabled('api-testing')">
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/dashboard')" index="/api-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/projects')" index="/api-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectAndVersion') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/interfaces')" index="/api-testing/interfaces">
              <el-icon><Link /></el-icon>
              <span>{{ $t('menu.interfaceManagement') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/automation')" index="/api-testing/automation">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.automationTesting') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/history')" index="/api-testing/history">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.requestHistory') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/environments')" index="/api-testing/environments">
              <el-icon><Setting /></el-icon>
              <span>{{ $t('menu.environmentManagement') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/reports')" index="/api-testing/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/scheduled-tasks')" index="/api-testing/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/api-testing/notification-logs')" index="/api-testing/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- UI自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'ui-automation' && appStore.isModuleEnabled('ui-automation')">
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/dashboard')" index="/ui-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/projects')" index="/ui-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectAndVersion') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/ai-testing')" index="/ui-automation/ai-testing">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.aiIntelligentTesting') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/elements-enhanced')" index="/ui-automation/elements-enhanced">
              <el-icon><Aim /></el-icon>
              <span>{{ $t('menu.elementManagement') }}</span>
            </el-menu-item>
            <el-sub-menu v-if="appStore.isAnyEnabled(['/ui-automation/test-cases', '/ui-automation/scripts-enhanced', '/ui-automation/playwright-recording', '/ui-automation/scripts'])" index="ui-cases-scripts">
              <template #title>
                <el-icon><Document /></el-icon>
                <span>{{ $t('menu.casesAndScripts') }}</span>
              </template>
              <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/test-cases')" index="/ui-automation/test-cases">{{ $t('menu.caseManagement') }}</el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/scripts-enhanced')" index="/ui-automation/scripts-enhanced">{{ $t('menu.scriptGeneration') }}</el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/playwright-recording')" index="/ui-automation/playwright-recording">{{ $t('menu.playwrightScriptRecording') }}</el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/scripts')" index="/ui-automation/scripts">{{ $t('menu.scriptList') }}</el-menu-item>
            </el-sub-menu>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/suites')" index="/ui-automation/suites">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.suiteManagement') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/executions')" index="/ui-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.executionRecords') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/reports')" index="/ui-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/scheduled-tasks')" index="/ui-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ui-automation/notification-logs')" index="/ui-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- APP自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'app-automation' && appStore.isModuleEnabled('app-automation')">
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/dashboard')" index="/app-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/projects')" index="/app-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectAndVersion') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/devices')" index="/app-automation/devices">
              <el-icon><Cellphone /></el-icon>
              <span>设备管理</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/packages')" index="/app-automation/packages">
              <el-icon><Collection /></el-icon>
              <span>包名管理</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/elements')" index="/app-automation/elements">
              <el-icon><Aim /></el-icon>
              <span>元素管理</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/scene-builder')" index="/app-automation/scene-builder">
              <el-icon><Connection /></el-icon>
              <span>用例编排</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/test-cases')" index="/app-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>测试用例</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/test-suites')" index="/app-automation/test-suites">
              <el-icon><FolderOpened /></el-icon>
              <span>测试套件</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/executions')" index="/app-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>执行记录</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/reports')" index="/app-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/scheduled-tasks')" index="/app-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/app-automation/notification-logs')" index="/app-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>通知列表</span>
            </el-menu-item>
          </template>

          <!-- AI 智能模式模块菜单 -->
          <template v-else-if="currentModule === 'ai-intelligent-mode' && appStore.isModuleEnabled('ai-intelligent-mode')">
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-intelligent-mode/projects')" index="/ai-intelligent-mode/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectAndVersion') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-intelligent-mode/cases')" index="/ai-intelligent-mode/cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.aiCaseManagement') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/ai-intelligent-mode/exploration')" index="/ai-intelligent-mode/exploration">
              <el-icon><Compass /></el-icon>
              <span>AI探索测试</span>
            </el-menu-item>

          </template>

          <!-- 配置中心模块菜单 -->
          <template v-else-if="currentModule === 'configuration' && appStore.isModuleEnabled('configuration')">
            <el-sub-menu v-if="appStore.isAnyEnabled(['/configuration/ai-model', '/configuration/prompt-config', '/configuration/generation-config'])" index="ai-case-generation">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.aiCaseGenerationConfig') }}</span>
              </template>
              <el-menu-item v-if="appStore.isMenuEnabled('/configuration/ai-model')" index="/configuration/ai-model">
                <el-icon><Cpu /></el-icon>
                <span>{{ $t('menu.aiModelConfig') }}</span>
              </el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/configuration/prompt-config')" index="/configuration/prompt-config">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('menu.promptConfig') }}</span>
              </el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/configuration/generation-config')" index="/configuration/generation-config">
                <el-icon><Setting /></el-icon>
                <span>{{ $t('menu.generationConfig') }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/knowledge-llm')" index="/configuration/knowledge-llm">
              <el-icon><Connection /></el-icon>
              <span>{{ $t('menu.knowledgeBaseConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/projects')" index="/configuration/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectAndVersion') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/ui-env')" index="/configuration/ui-env">
              <el-icon><Monitor /></el-icon>
              <span>{{ $t('menu.uiEnvConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/app-env')" index="/configuration/app-env">
              <el-icon><Cellphone /></el-icon>
              <span>APP环境配置</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/ai-mode')" index="/configuration/ai-mode">
              <el-icon><MagicStick /></el-icon>
              <span>{{ $t('menu.aiModeConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/skills')" index="/configuration/skills">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.skillsConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/scheduled-task')" index="/configuration/scheduled-task">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.scheduledTaskConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/dify')" index="/configuration/dify">
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ $t('menu.difyConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/mcp-server')" index="/configuration/mcp-server">
              <el-icon><Connection /></el-icon>
              <span>{{ $t('menu.mcpServerConfig') }}</span>
            </el-menu-item>
            <el-menu-item v-if="appStore.isMenuEnabled('/configuration/module-switch')" index="/configuration/module-switch">
              <el-icon><Switch /></el-icon>
              <span>{{ $t('menu.moduleSwitchConfig') }}</span>
            </el-menu-item>
            <el-sub-menu v-if="appStore.isAnyEnabled(['/configuration/performance-stats', '/configuration/request-performance-log', '/configuration/notification-template'])" index="core-module">
              <template #title>
                <el-icon><DataAnalysis /></el-icon>
                <span>{{ $t('menu.coreModule') }}</span>
              </template>
              <el-menu-item v-if="appStore.isMenuEnabled('/configuration/performance-stats')" index="/configuration/performance-stats">
                <el-icon><TrendCharts /></el-icon>
                <span>{{ $t('menu.performanceStats') }}</span>
              </el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/configuration/request-performance-log')" index="/configuration/request-performance-log">
                <el-icon><Document /></el-icon>
                <span>{{ $t('menu.requestPerformanceLog') }}</span>
              </el-menu-item>
              <el-menu-item v-if="appStore.isMenuEnabled('/configuration/notification-template')" index="/configuration/notification-template">
                <el-icon><Bell /></el-icon>
                <span>{{ $t('menu.notificationTemplate') }}</span>
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </el-aside>

      <!-- 主体内容 -->
      <el-container class="main-shell">
        <!-- 顶部导航 -->
        <el-header height="var(--th-header-height)">
          <div class="header-content">
            <div class="header-left">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/home' }">{{ $t('nav.home') }}</el-breadcrumb-item>
                <el-breadcrumb-item v-if="moduleName">{{ moduleName }}</el-breadcrumb-item>
                <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">
              <div class="th-utility-bar header-utility">
                <el-dropdown @command="handleLanguageChange" trigger="click">
                  <button type="button" class="th-utility-btn">
                    <svg class="lang-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M3 12h18M12 3c2.5 2.8 3.8 5.7 3.8 9S14.5 18.2 12 21c-2.5-2.8-3.8-5.7-3.8-9S9.5 5.8 12 3z" />
                    </svg>
                    <span>{{ appStore.language === 'zh-cn' ? 'ZH' : 'EN' }}</span>
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="zh-cn" :disabled="appStore.language === 'zh-cn'">
                        简体中文
                      </el-dropdown-item>
                      <el-dropdown-item command="en" :disabled="appStore.language === 'en'">
                        English
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>

                <button
                  type="button"
                  class="th-utility-btn"
                  :title="appStore.isDark ? '切换浅色模式' : '切换深色模式'"
                  @click="appStore.toggleDark()"
                >
                  <el-icon>
                    <Moon v-if="!appStore.isDark" />
                    <Sunny v-else />
                  </el-icon>
                </button>

                <el-dropdown @command="handleCommand" trigger="click">
                  <button type="button" class="th-utility-btn user-btn">
                    <el-avatar :size="26" :src="userStore.user?.avatar">
                      <el-icon><UserFilled /></el-icon>
                    </el-avatar>
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item disabled>
                        {{ userStore.user?.username || 'User' }}
                      </el-dropdown-item>
                      <el-dropdown-item command="profile">{{ $t('nav.profile') }}</el-dropdown-item>
                      <el-dropdown-item divided command="logout">{{ $t('nav.logout') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </el-header>

        <!-- 页面内容 -->
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Monitor, Folder, Document, Check, Collection, VideoPlay,
  DataAnalysis, ChatDotRound, Link, MagicStick,
  Odometer, Timer, Setting, AlarmClock, Bell, Aim, Edit, Cpu, Cellphone, Connection, FolderOpened, Compass,
  TrendCharts, Moon, Sunny, UserFilled, Switch
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const { t } = useI18n()

const sidebarWidth = 'var(--th-sidebar-width)'

// 加载已启用模块（控制菜单显示）
onMounted(() => {
  appStore.loadEnabledModules()
})

const handleLanguageChange = (lang) => {
  appStore.setLanguage(lang)
  ElMessage.success(lang === 'zh-cn' ? '语言已切换为中文' : 'Language switched to English')
}

const activeMenu = computed(() => {
  // 远程投屏归属设备管理菜单高亮
  if (/^\/app-automation\/devices\/\d+\/remote/.test(route.path)) {
    return '/app-automation/devices'
  }
  // AI 测试详情归属 AI 智能测试菜单高亮
  if (/^\/ui-automation\/ai-testing\/\d+/.test(route.path)) {
    return '/ui-automation/ai-testing'
  }
  return route.path
})

const currentModule = computed(() => {
  if (route.path.startsWith('/ai-generation')) return 'ai-generation'
  if (route.path.startsWith('/api-testing')) return 'api-testing'
  if (route.path.startsWith('/ui-automation')) return 'ui-automation'
  if (route.path.startsWith('/app-automation')) return 'app-automation'
  if (route.path.startsWith('/ai-intelligent-mode')) return 'ai-intelligent-mode'
  if (route.path.startsWith('/configuration')) return 'configuration'
  return ''
})

const moduleName = computed(() => {
  const map = {
    'ai-generation': t('modules.aiGeneration'),
    'api-testing': t('modules.apiTesting'),
    'ui-automation': t('modules.uiAutomation'),
    'app-automation': 'APP自动化测试',
    'ai-intelligent-mode': t('modules.aiIntelligentMode'),
    'configuration': t('modules.configuration')
  }
  return map[currentModule.value] || ''
})

const breadcrumbTitle = computed(() => {
  const routeMap = {
    // AI用例生成
    '/ai-generation/requirement-analysis': t('menu.aiCaseGeneration'),
    '/ai-generation/generated-testcases': t('menu.aiGeneratedTestcases'),
    '/ai-generation/projects': t('menu.projectAndVersion'),
    '/ai-generation/testcases': t('menu.testCases'),
    '/ai-generation/knowledge-base': t('menu.knowledgeBaseManage'),
    '/ai-generation/versions': t('menu.versionManagement'),
    '/ai-generation/reviews': t('menu.reviewList'),
    '/ai-generation/review-templates': t('menu.reviewTemplates'),
    '/ai-generation/testsuites': t('menu.suiteManagement'),
    '/ai-generation/executions': t('menu.executionRecords'),
    '/ai-generation/reports': t('menu.testReport'),

    // 接口测试
    '/api-testing/dashboard': t('menu.dashboard'),
    '/api-testing/projects': t('menu.projectAndVersion'),
    '/api-testing/interfaces': t('menu.interfaceManagement'),
    '/api-testing/automation': t('menu.automationTesting'),
    '/api-testing/history': t('menu.requestHistory'),
    '/api-testing/environments': t('menu.environmentManagement'),
    '/api-testing/reports': t('menu.testReport'),
    '/api-testing/scheduled-tasks': t('menu.scheduledTasks'),
    '/api-testing/notification-logs': t('menu.notificationList'),

    // UI自动化测试
    '/ui-automation/dashboard': t('menu.dashboard'),
    '/ui-automation/projects': t('menu.projectAndVersion'),
    '/ui-automation/elements-enhanced': t('menu.elementManagement'),
    '/ui-automation/test-cases': t('menu.caseManagement'),
    '/ui-automation/scripts-enhanced': t('menu.scriptGeneration'),
    '/ui-automation/playwright-recording': t('menu.playwrightScriptRecording'),
    '/ui-automation/scripts': t('menu.scriptList'),
    '/ui-automation/suites': t('menu.suiteManagement'),
    '/ui-automation/executions': t('menu.executionRecords'),
    '/ui-automation/reports': t('menu.testReport'),
    '/ui-automation/scheduled-tasks': t('menu.scheduledTasks'),
    '/ui-automation/notification-logs': t('menu.notificationList'),
    '/ui-automation/ai-testing': t('menu.aiIntelligentTesting'),

    // APP自动化测试
    '/app-automation/dashboard': '数据看板',
    '/app-automation/projects': t('menu.projectAndVersion'),
    '/app-automation/devices': '设备管理',
    '/app-automation/packages': '包名管理',
    '/app-automation/elements': '元素管理',
    '/app-automation/scene-builder': '用例编排',
    '/app-automation/test-cases': '测试用例',
    '/app-automation/test-suites': '测试套件',
    '/app-automation/scheduled-tasks': '定时任务',
    '/app-automation/notification-logs': '通知列表',
    '/app-automation/executions': '执行记录',
    '/app-automation/reports': '测试报告',

    // AI 智能模式
    '/ai-intelligent-mode/projects': t('menu.projectAndVersion'),
    '/ai-intelligent-mode/cases': t('menu.aiCaseManagement'),
    '/ai-intelligent-mode/execution-records': t('menu.aiExecutionRecords'),
    '/ai-intelligent-mode/exploration': 'AI探索测试',


    // 配置中心
    '/configuration/ai-model': t('menu.aiModelConfig'),
    '/configuration/projects': t('menu.projectAndVersion'),
    '/configuration/prompt-config': t('menu.promptConfig'),
    '/configuration/generation-config': t('menu.generationConfig'),
    '/configuration/knowledge-base': t('menu.knowledgeBaseManage'),
    '/configuration/knowledge-llm': t('menu.knowledgeBaseConfig'),
    '/configuration/ui-env': t('menu.uiEnvConfig'),
    '/configuration/ai-mode': t('menu.aiModeConfig'),
    '/configuration/skills': t('menu.skillsConfig'),
    '/configuration/scheduled-task': t('menu.scheduledTaskConfig'),
    '/configuration/dify': t('menu.difyConfig'),
    '/configuration/mcp-server': t('menu.mcpServerConfig'),
    '/configuration/module-switch': t('menu.moduleSwitchConfig'),
    
    '/profile': t('nav.profile')
  }
  if (/^\/ui-automation\/ai-testing\/\d+/.test(route.path)) {
    return t('menu.aiIntelligentTesting')
  }
  return routeMap[route.path] || route.meta.title || ''
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('退出登录成功')
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/ai-generation/profile')
  }
}
</script>

<style lang="scss" scoped>
.layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--th-bg-page);
}

.layout > .el-container {
  height: 100%;
  overflow: hidden;
}

.logo {
  height: var(--th-header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 20px;
  background: transparent;
  border-bottom: 1px solid var(--th-border);
  flex-shrink: 0;
  cursor: pointer;
  user-select: none;

  .logo-text {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--th-text-primary);
  }
}

.el-aside {
  background: var(--th-bg-sidebar);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--th-border);
  width: var(--th-sidebar-width) !important;
  transition: background-color var(--th-transition), border-color var(--th-transition);

  .side-menu {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 12px 10px 20px;
    border-right: none !important;
    background: transparent !important;

    &::-webkit-scrollbar {
      width: 0;
    }
  }
}

.side-menu {
  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 42px;
    line-height: 42px;
    margin: 2px 0;
    border-radius: 10px;
    color: var(--th-text-secondary) !important;
    font-size: 13.5px;
    font-weight: 500;
    transition: all var(--th-transition);

    .el-icon {
      color: inherit;
      font-size: 17px;
    }

    &:hover {
      background: var(--th-bg-hover) !important;
      color: var(--th-color-primary) !important;
    }
  }

  :deep(.el-menu-item.is-active) {
    background: var(--th-color-primary-soft) !important;
    color: var(--th-color-primary) !important;
    font-weight: 600;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 10px;
      bottom: 10px;
      width: 3px;
      border-radius: 0 3px 3px 0;
      background: var(--th-color-primary);
    }
  }

  :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
    color: var(--th-color-primary) !important;
  }

  :deep(.el-menu) {
    background: transparent !important;
  }

  :deep(.el-sub-menu .el-menu-item) {
    padding-left: 48px !important;
    min-width: auto;
  }
}

.main-shell {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--th-bg-page);
}

.el-header {
  background: var(--th-bg-elevated);
  border-bottom: 1px solid var(--th-border);
  padding: 0;
  flex-shrink: 0;
  height: var(--th-header-height) !important;
  transition: background-color var(--th-transition), border-color var(--th-transition);

  .header-content {
    height: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
    gap: 16px;
  }

  .header-left {
    flex: 1;
    overflow: hidden;
    min-width: 0;

    :deep(.el-breadcrumb) {
      font-size: 13px;
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-utility {
  background: var(--th-bg-muted);
  border: 1px solid var(--th-border);
  box-shadow: none;
  backdrop-filter: none;

  .lang-icon {
    width: 16px;
    height: 16px;
  }

  .user-btn {
    padding: 0 6px;

    :deep(.el-avatar) {
      background: var(--th-color-primary-soft);
      color: var(--th-color-primary);
    }
  }
}

.el-main {
  background: var(--th-bg-page);
  padding: 20px 22px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  transition: background-color var(--th-transition);
}

@media screen and (max-width: 1280px) {
  .el-aside {
    width: 200px !important;
  }

  .el-main {
    padding: 16px;
  }

  .logo .logo-text {
    font-size: 16px;
  }
}

@media screen and (max-width: 1024px) {
  .el-aside {
    width: 72px !important;

    .logo {
      justify-content: center;
      padding: 0;

      .logo-text {
        display: none;
      }
    }

    .side-menu {
      padding: 8px 6px;

      :deep(.el-menu-item),
      :deep(.el-sub-menu__title) {
        padding: 0 !important;
        justify-content: center;

        span,
        .el-sub-menu__icon-arrow {
          display: none;
        }
      }
    }
  }

  .el-main {
    padding: 12px;
  }
}

@media screen and (max-width: 768px) {
  .el-aside {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    width: 232px !important;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    box-shadow: var(--th-shadow-lg);

    &.mobile-open {
      transform: translateX(0);
    }

    .logo .logo-text {
      display: inline;
    }

    .side-menu {
      :deep(.el-menu-item),
      :deep(.el-sub-menu__title) {
        justify-content: flex-start;
        padding-left: 20px !important;

        span {
          display: inline;
        }
      }
    }
  }

  .el-main {
    padding: 10px;
  }

  .el-header .header-left {
    :deep(.el-breadcrumb__item:not(:last-child)) {
      display: none;
    }
  }
}
</style>