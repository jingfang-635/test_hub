<template>
  <div class="script-editor-enhanced">
    <div class="page-header">
      <h1 class="page-title">{{ $t('uiAutomation.scriptEditor.title') }}</h1>
      <div class="header-actions">
        <el-select v-model="projectId" :placeholder="$t('uiAutomation.common.selectProject')" style="width: 200px; margin-right: 15px" @change="onProjectChange">
          <el-option :label="$t('uiAutomation.common.allProjects')" value="all" />
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧:���素库(页面树形式) -->
      <div class="left-panel">
        <div class="panel-header">
          <h3>{{ $t('uiAutomation.scriptEditor.elementLibrary') }}</h3>
          <el-input
            v-model="elementFilter"
            :placeholder="$t('uiAutomation.scriptEditor.searchElement')"
            clearable
            size="small"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <div class="panel-content">
          <el-tree
            :data="elementTree"
            :filter-node-method="filterElementNode"
            :props="{ children: 'children', label: 'name' }"
            node-key="id"
            default-expand-all
            @node-click="handleElementClick"
          >
            <template #default="{ data }">
              <div class="tree-node">
                <el-icon class="node-icon">
                  <component :is="getTreeNodeIcon(data.type)" />
                </el-icon>
                <span class="node-label">{{ data.name }}</span>
                <div class="node-actions" v-if="data.type === 'element'">
                  <el-button size="small" text @click.stop="insertElementCode(data)" :title="$t('uiAutomation.scriptEditor.clickToInsert')">
                    <el-icon><Plus /></el-icon>
                  </el-button>
                  <el-button size="small" text @click.stop="showElementDetail(data)">
                    <el-icon><View /></el-icon>
                  </el-button>
                </div>
              </div>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 中间:代码编辑器 -->
      <div class="center-panel">
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <el-button size="small" :loading="recordStarting" @click="openRecordDialog">
              <el-icon><VideoCamera /></el-icon>
              {{ $t('uiAutomation.scriptEditor.recording') }}
            </el-button>
            <el-select v-model="scriptLanguage" size="small" style="width: 120px; margin-left: 10px">
              <el-option label="JavaScript" value="javascript" />
              <el-option label="Python" value="python" />
            </el-select>
            <el-select v-model="scriptFramework" size="small" style="width: 120px; margin-left: 10px">
              <el-option label="Playwright" value="playwright" />
              <el-option label="Selenium" value="selenium" />
            </el-select>
          </div>
          <div class="toolbar-right">
            <el-button size="small" type="success" @click="openReplayDialog" :loading="running">
              <el-icon><VideoPlay /></el-icon>
              {{ $t('uiAutomation.scriptEditor.playback') }}
            </el-button>
            <el-button size="small" @click="formatCode">
              <el-icon><Operation /></el-icon>
              {{ $t('uiAutomation.scriptEditor.format') }}
            </el-button>
            <el-button size="small" @click="clearCode">
              <el-icon><Delete /></el-icon>
              {{ $t('uiAutomation.scriptEditor.clear') }}
            </el-button>
            <el-button size="small" type="primary" @click="saveScript" :loading="saving">
              <el-icon><Check /></el-icon>
              {{ $t('uiAutomation.scriptEditor.saveScript') }}
            </el-button>
          </div>
        </div>

        <!-- 录制中状态条 -->
        <div v-if="recording" class="recording-bar">
          <span class="recording-dot"></span>
          <span class="recording-text">{{ $t('uiAutomation.scriptEditor.recorder.recordingHint') }}</span>
          <el-button size="small" type="danger" plain :loading="recordStopping" @click="stopRecording">
            {{ $t('uiAutomation.scriptEditor.recorder.stopRecord') }}
          </el-button>
        </div>

        <div class="code-editor-container">
          <textarea
            ref="codeEditor"
            v-model="scriptContent"
            class="code-editor"
            :placeholder="$t('uiAutomation.scriptEditor.editorPlaceholder')"
            @focus="handleEditorFocus"
            @blur="handleEditorBlur"
            @input="handleContentChange"
          />
        </div>

        <div class="editor-status">
          <span>{{ $t('uiAutomation.scriptEditor.line') }}: {{ cursorPosition.line }}, {{ $t('uiAutomation.scriptEditor.column') }}: {{ cursorPosition.column }}</span>
          <span>{{ $t('uiAutomation.scriptEditor.characters') }}: {{ scriptContent.length }}</span>
          <span>{{ $t('uiAutomation.scriptEditor.language') }}: {{ scriptLanguage }}</span>
        </div>
      </div>

      <!-- 右侧:执行日志和元素详情 -->
      <div class="right-panel">
        <el-tabs v-model="rightActiveTab" type="border-card">
          <!-- 执行日志 -->
          <el-tab-pane :label="$t('uiAutomation.scriptEditor.executionLogs')" name="logs">
            <div class="panel-content">
              <div class="log-controls">
                <el-button size="small" @click="clearLogs">
                  <el-icon><Delete /></el-icon>
                  {{ $t('uiAutomation.scriptEditor.clearLogs') }}
                </el-button>
              </div>
              <div class="log-output">
                <div
                  v-for="(log, index) in executionLogs"
                  :key="index"
                  class="log-entry"
                  :class="log.level"
                >
                  <span class="log-time">{{ formatTime(log.timestamp) }}</span>
                  <span class="log-level">{{ log.level.toUpperCase() }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 元素详情 -->
          <el-tab-pane :label="$t('uiAutomation.scriptEditor.elementDetail')" name="elementDetail" v-if="selectedElementDetail">
            <div class="panel-content">
              <div class="element-detail">
                <h4>{{ selectedElementDetail.name }}</h4>
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item :label="$t('uiAutomation.scriptEditor.type')">
                    {{ getElementTypeText(selectedElementDetail.element_type) }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('uiAutomation.scriptEditor.page')">
                    {{ selectedElementDetail.page || $t('uiAutomation.element.notSpecified') }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('uiAutomation.scriptEditor.locatorStrategy')">
                    {{ selectedElementDetail.locator_strategy?.name || selectedElementDetail.locator_strategy }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('uiAutomation.scriptEditor.locatorExpression')">
                    <code>{{ selectedElementDetail.locator_value }}</code>
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('uiAutomation.scriptEditor.usageCount')">
                    {{ selectedElementDetail.usage_count || 0 }}
                  </el-descriptions-item>
                </el-descriptions>

                <div class="element-actions" style="margin-top: 15px">
                  <el-button size="small" type="primary" @click="insertElementCode(selectedElementDetail)">
                    {{ $t('uiAutomation.scriptEditor.insertCode') }}
                  </el-button>
                  <el-button size="small" @click="validateElement(selectedElementDetail)">
                    {{ $t('uiAutomation.scriptEditor.validateElement') }}
                  </el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- Playwright 录制脚本弹窗 -->
    <el-dialog
      v-model="recordDialogVisible"
      :title="$t('uiAutomation.scriptEditor.recorder.title')"
      width="560px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-steps :active="0" finish-status="success" align-center class="record-steps">
        <el-step :title="$t('uiAutomation.scriptEditor.recorder.stepConfig')" />
        <el-step :title="$t('uiAutomation.scriptEditor.recorder.stepRecord')" />
        <el-step :title="$t('uiAutomation.scriptEditor.recorder.stepImport')" />
      </el-steps>

      <el-form label-width="92px" class="record-form">
        <el-form-item :label="$t('uiAutomation.scriptEditor.recorder.targetUrl')" required>
          <el-input v-model="recordUrl" placeholder="https://example.com/login" clearable />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.scriptEditor.recorder.language')">
          <el-radio-group v-model="recordLanguage">
            <el-radio value="python" style="margin-right: 20px">{{ $t('uiAutomation.scriptEditor.recorder.pythonOption') }}</el-radio>
            <el-radio value="javascript">{{ $t('uiAutomation.scriptEditor.recorder.jsOption') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.scriptEditor.recorder.browser')">
          <el-select v-model="recordBrowser" style="width: 200px">
            <el-option label="Chromium / Chrome" value="chromium" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.scriptEditor.recorder.saveState')">
          <el-switch v-model="recordSaveState" />
          <span class="save-state-hint">{{ $t('uiAutomation.scriptEditor.recorder.saveStateHint') }}</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="recordDialogVisible = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
        <el-button type="primary" :loading="recordStarting" @click="startRecording">
          {{ $t('uiAutomation.scriptEditor.recorder.startRecord') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 脚本回放弹窗 -->
    <el-dialog
      v-model="replayDialogVisible"
      :title="$t('uiAutomation.scriptEditor.replayDialog.title')"
      width="680px"
      class="replay-dialog"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="replay-header">
        <div class="replay-script-status">
          <span class="replay-label">{{ $t('uiAutomation.scriptEditor.replayDialog.currentScript') }}</span>
          <el-tag :type="replayStatusTagType" size="small">{{ replayStatusText }}</el-tag>
        </div>
        <div class="replay-header-right">
          <el-select v-model="replayBrowser" size="small" style="width: 150px">
            <el-option label="Chromium" value="chromium" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="WebKit" value="webkit" />
          </el-select>
          <el-checkbox v-model="replayHeadless" class="replay-headless">
            {{ $t('uiAutomation.scriptEditor.replayDialog.headless') }}
          </el-checkbox>
          <el-button type="primary" size="small" :loading="replayRunning" @click="startReplay">
            <el-icon style="margin-right: 4px"><VideoPlay /></el-icon>
            {{ $t('uiAutomation.scriptEditor.replayDialog.start') }}
          </el-button>
        </div>
      </div>

      <div class="replay-base-url">
        <span class="replay-base-url-label">Base URL</span>
        <el-input v-model="replayBaseUrl" size="small" placeholder="http://localhost:5175/" clearable />
      </div>

      <div class="replay-logs">
        <div class="replay-logs-header">
          <span>{{ $t('uiAutomation.scriptEditor.replayDialog.executionLogs') }}</span>
          <el-button link size="small" @click="replayLogs = ''">
            {{ $t('uiAutomation.scriptEditor.replayDialog.clear') }}
          </el-button>
        </div>
        <div class="replay-log-body">
          <pre v-if="replayLogs" class="replay-log-pre">{{ replayLogs }}</pre>
          <div v-else class="replay-log-empty">{{ $t('uiAutomation.scriptEditor.replayDialog.notExecuted') }}</div>
        </div>
      </div>

      <template #footer>
        <el-button @click="replayDialogVisible = false">{{ $t('uiAutomation.common.close') }}</el-button>
      </template>
    </el-dialog>

    <!-- 保存脚本弹窗 -->
    <el-dialog
      v-model="saveDialogVisible"
      :title="$t('uiAutomation.scriptEditor.saveDialog.title')"
      width="480px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form label-width="92px" @submit.prevent>
        <el-form-item :label="$t('uiAutomation.scriptEditor.saveDialog.scriptName')" required>
          <el-input
            v-model="saveScriptName"
            :placeholder="$t('uiAutomation.scriptEditor.saveDialog.scriptNamePlaceholder')"
            clearable
            @keyup.enter="confirmSaveScript"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="confirmSaveScript">
          {{ $t('uiAutomation.scriptEditor.saveDialog.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, View, Document, Check, Delete, Operation, Folder, VideoCamera, VideoPlay
} from '@element-plus/icons-vue'

import {
  loadUiAutomationProjects,
  createTestScript,
  getElementTree,
  getElementGroupTree,
  validateElementLocator,
  startCodegenRecording,
  getCodegenStatus,
  stopCodegenRecording,
  getCodegenRecordedContent,
  replayCodegenScript
} from '@/api/ui_automation'

// i18n
const { t } = useI18n()

// 响应式数据
const projects = ref([])
const projectId = ref('all')
const ALL_PROJECTS = 'all'
const isAllProjectsSelected = () => projectId.value === ALL_PROJECTS || projectId.value === ''
const getProjectQueryParams = () => (isAllProjectsSelected() ? {} : { project: projectId.value })
const scriptContent = ref('')
const scriptLanguage = ref('python')
const scriptFramework = ref('playwright')

const elementTree = ref([])
const elementFilter = ref('')
const selectedElementDetail = ref(null)
const executionLogs = ref([])

const cursorPosition = reactive({ line: 1, column: 1 })
const saving = ref(false)
const running = ref(false)

// 保存脚本弹窗
const saveDialogVisible = ref(false)
const saveScriptName = ref('')

// 标签页控制
const rightActiveTab = ref('logs')

// Monaco编辑器实例
const codeEditor = ref(null)

// 方法定义（与「项目与版本」一致：仅已勾选 UI自动化 的主项目）
const loadProjects = async () => {
  try {
    const { projects: list, empty, lastError } = await loadUiAutomationProjects()
    projects.value = list
    if (empty) {
      ElMessage.warning('暂无关联 UI自动化 的项目，请先在「项目与版本」中创建并勾选 UI自动化')
    } else if (list.length === 0) {
      const detail = lastError?.response?.data?.error || lastError?.message || '请确认后端已重启并支持 ensure 接口'
      ElMessage.warning(`项目列表加载失败：${detail}`)
    }
  } catch (error) {
    projects.value = []
    ElMessage.error(t('uiAutomation.scriptEditor.messages.loadProjectsFailed'))
    console.error('Failed to load projects:', error)
  }
}

const loadElementTree = async () => {
  if (!projectId.value) {
    elementTree.value = []
    return
  }

  try {
    const query = getProjectQueryParams()
    // 并行加载页面树和元素
    const [pageGroupResponse, elementsResponse] = await Promise.all([
      getElementGroupTree(query),
      getElementTree(query)
    ])

    // 构建页面节点
    const buildTree = (groups) => {
      return groups.map(group => ({
        ...group,
        type: 'page',
        children: group.children ? buildTree(group.children) : []
      }))
    }

    const pageNodes = buildTree(pageGroupResponse.data || [])

    // 获取所有元素
    const elements = elementsResponse.data?.results || elementsResponse.data || []

    console.log('=== Smart Script Generator - Loading Element Tree ===')
    console.log('Page nodes count:', pageNodes.length)
    console.log('Total elements:', elements.length)

    // 将元素添加到对应页面下
    const attachElementsToPages = (pages) => {
      pages.forEach(page => {
        // 找到属于当前页面的元素
        const pageElements = elements.filter(element => element.group_id === page.id)
        console.log(`Page ${page.name} (ID: ${page.id}) found ${pageElements.length} elements`)

        const elementNodes = pageElements.map(element => ({
          ...element,
          type: 'element'
        }))

        // 将元素添加到页面的子节点中
        page.children = page.children ? [...page.children, ...elementNodes] : [...elementNodes]

        // 递归处理子页面
        if (page.children) {
          attachElementsToPages(page.children.filter(child => child.type === 'page'))
        }
      })
    }

    attachElementsToPages(pageNodes)
    elementTree.value = pageNodes

    addLog('info', t('uiAutomation.scriptEditor.messages.elementsLoaded', { count: countElements(elementTree.value) }))
  } catch (error) {
    console.error('Failed to load element tree:', error)
    addLog('error', t('uiAutomation.scriptEditor.messages.loadElementTreeFailed'))
  }
}

// 统计元素数量
const countElements = (tree) => {
  let count = 0
  const traverse = (nodes) => {
    nodes.forEach(node => {
      if (node.type === 'element') count++
      if (node.children) traverse(node.children)
    })
  }
  traverse(tree)
  return count
}

const handleEditorFocus = () => {
  // 编辑器获得焦点时的处理
}

const handleEditorBlur = () => {
  // 编辑器失去焦点时的处理
}

const handleContentChange = () => {
  // 内容变化时更新状态
  updateCursorPosition()
}

const updateCursorPosition = () => {
  if (codeEditor.value) {
    const textarea = codeEditor.value
    const text = textarea.value
    const selectionStart = textarea.selectionStart

    // 计算行号和列号
    const lines = text.substring(0, selectionStart).split('\n')
    cursorPosition.line = lines.length
    cursorPosition.column = lines[lines.length - 1].length + 1
  }
}

const onProjectChange = async () => {
  selectedElementDetail.value = null

  await loadElementTree()

  // 代码编辑器已更新(使用 textarea)
}

const filterElementNode = (value, data) => {
  if (!value) return true
  return data.name.indexOf(value) !== -1
}

const handleElementClick = (data) => {
  if (data.type === 'element') {
    selectedElementDetail.value = data
    rightActiveTab.value = 'elementDetail'
  }
}

const showElementDetail = (element) => {
  selectedElementDetail.value = element
  rightActiveTab.value = 'elementDetail'
}

const insertElementCode = (element) => {
  if (element.type !== 'element') return

  const code = generateElementCode(element)
  insertCodeAtCursor(code + '\n')  // 自动换行

  addLog('info', `${t('uiAutomation.scriptEditor.messages.insertCode')}: ${element.name}`)
}

const insertCodeAtCursor = (code) => {
  if (!codeEditor.value) return

  const textarea = codeEditor.value
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const text = textarea.value

  // 在光标位置插入代码
  const newText = text.substring(0, start) + code + text.substring(end)
  scriptContent.value = newText

  // 更新光标位置
  setTimeout(() => {
    textarea.focus()
    textarea.setSelectionRange(start + code.length, start + code.length)
    updateCursorPosition()
  }, 0)
}

const generateElementCode = (element) => {
  const locatorValue = element.locator_value || ''
  const locatorStrategy = element.locator_strategy?.name || element.locator_strategy || 'css'

  if (scriptLanguage.value === 'javascript') {
    switch (scriptFramework.value) {
      case 'playwright':
        return `await page.locator('${locatorValue}').click();`
      case 'selenium':
        return `await driver.findElement(By.${locatorStrategy.toUpperCase()}('${locatorValue}')).click();`
      default:
        return `await page.locator('${locatorValue}').click();`
    }
  } else {
    switch (scriptFramework.value) {
      case 'playwright':
        return `page.locator('${locatorValue}').click()`
      case 'selenium':
        return `driver.find_element(By.${locatorStrategy.toUpperCase()}, '${locatorValue}').click()`
      default:
        return `page.locator('${locatorValue}').click()`
    }
  }
}

const saveScript = async () => {
  if (!projectId.value || isAllProjectsSelected()) {
    ElMessage.warning(t('uiAutomation.common.selectSpecificProject'))
    return
  }

  if (!scriptContent.value.trim()) {
    ElMessage.warning(t('uiAutomation.scriptEditor.messages.emptyScript'))
    return
  }

  // 弹出保存弹窗，让用户输入脚本名称
  saveScriptName.value = ''
  saveDialogVisible.value = true
}

const confirmSaveScript = async () => {
  const scriptName = saveScriptName.value.trim()
  if (!scriptName) {
    ElMessage.warning(t('uiAutomation.scriptEditor.saveDialog.nameRequired'))
    return
  }

  try {
    saving.value = true

    await createTestScript({
      name: scriptName,
      project: projectId.value,
      script_type: 'CODE',
      content: scriptContent.value,
      language: scriptLanguage.value,
      framework: scriptFramework.value
    })

    saveDialogVisible.value = false
    ElMessage.success(`${t('uiAutomation.scriptEditor.messages.saveSuccess')}: ${scriptName}`)
    addLog('success', `${t('uiAutomation.scriptEditor.messages.saveSuccess')}: ${scriptName}`)
  } catch (error) {
    console.error('Failed to save script:', error)
    ElMessage.error(t('uiAutomation.scriptEditor.messages.saveFailed'))
    addLog('error', t('uiAutomation.scriptEditor.messages.saveFailed'))
  } finally {
    saving.value = false
  }
}

const validateElement = async (element) => {
  try {
    const response = await validateElementLocator(element.id)
    const result = response.data

    if (result.is_valid) {
      ElMessage.success(t('uiAutomation.scriptEditor.messages.validatePassed'))
      addLog('info', `${t('uiAutomation.scriptEditor.messages.validatePassed')}: ${element.name}`)
    } else {
      ElMessage.error(`${t('uiAutomation.scriptEditor.messages.validateFailed')}: ${result.validation_message}`)
      addLog('error', `${t('uiAutomation.scriptEditor.messages.validateFailed')}: ${element.name} - ${result.validation_message}`)
    }
  } catch (error) {
    console.error('Failed to validate element:', error)
    ElMessage.error(t('uiAutomation.scriptEditor.messages.validateFailed'))
    addLog('error', `${t('uiAutomation.scriptEditor.messages.validateFailed')}: ${element.name}`)
  }
}

const formatCode = () => {
  // 简单的代码格式化
  try {
    if (scriptLanguage.value === 'javascript') {
      let formatted = scriptContent.value
        .replace(/;/g, ';\n')
        .replace(/\{/g, ' {\n')
        .replace(/\}/g, '\n}')
        .replace(/\n\s*\n/g, '\n')

      scriptContent.value = formatted
      addLog('info', t('uiAutomation.scriptEditor.messages.codeFormatted'))
    } else {
      addLog('info', t('uiAutomation.scriptEditor.messages.formatInProgress'))
    }
  } catch (error) {
    addLog('error', t('uiAutomation.scriptEditor.messages.formatFailed'))
  }
}

const clearCode = () => {
  scriptContent.value = ''
  addLog('info', t('uiAutomation.scriptEditor.messages.codeCleared'))
}

// ---- Playwright 录制 ----
const recordDialogVisible = ref(false)
const recordUrl = ref('https://')
const recordScriptName = ref('')
const recordLanguage = ref('python')
const recordBrowser = ref('chromium')
const recordSaveState = ref(false)
const recordStarting = ref(false)
const recordStopping = ref(false)
const recording = ref(false)
let recordPollTimer = null

const openRecordDialog = () => {
  // 默认带入当前项目的 base_url
  const currentProject = projects.value.find(p => p.id === projectId.value)
  if (currentProject?.base_url) {
    recordUrl.value = currentProject.base_url
  } else if (!recordUrl.value || recordUrl.value === 'https://') {
    recordUrl.value = 'https://'
  }
  recordDialogVisible.value = true
}

const clearRecordPoll = () => {
  if (recordPollTimer) {
    clearInterval(recordPollTimer)
    recordPollTimer = null
  }
}

// 将录制得到的脚本内容导入中间栏编辑器
const importRecordedContent = (content) => {
  if (!content || !String(content).trim()) return false
  scriptContent.value = content
  scriptLanguage.value = recordLanguage.value === 'javascript' ? 'javascript' : 'python'
  scriptFramework.value = 'playwright'
  return true
}

const onRecordFinished = async (session) => {
  clearRecordPoll()
  recording.value = false

  const status = session?.status
  if (status === 'failed') {
    const msg = session?.error || t('uiAutomation.scriptEditor.recorder.recordFailed')
    ElMessage.error(msg)
    addLog('error', msg)
    return
  }

  // 优先使用会话内容；没有则按脚本文件名兜底拉取
  let content = session?.content || ''
  if (!content && session?.script_name) {
    try {
      const fileRes = await getCodegenRecordedContent(session.script_name)
      const fileData = fileRes.data || fileRes
      content = fileData.content || ''
    } catch (e) {
      console.error('failed to load recorded content:', e)
    }
  }

  if (importRecordedContent(content)) {
    ElMessage.success(t('uiAutomation.scriptEditor.recorder.importSuccess'))
    addLog('success', t('uiAutomation.scriptEditor.recorder.importSuccess'))
  } else {
    ElMessage.info(t('uiAutomation.scriptEditor.recorder.recordStopped'))
    addLog('info', t('uiAutomation.scriptEditor.recorder.recordStopped'))
  }
}

const applyRecordSession = (session) => {
  if (!session) {
    recording.value = false
    return
  }
  if (['starting', 'recording'].includes(session.status)) {
    recording.value = true
    return
  }
  if (['finished', 'stopped', 'failed'].includes(session.status)) {
    onRecordFinished(session)
  }
}

const pollRecordStatus = async () => {
  try {
    const res = await getCodegenStatus({ include_content: 1 })
    const data = res.data || res
    applyRecordSession(data.session)
  } catch (error) {
    console.error('record status poll failed:', error)
  }
}

const startRecordPolling = () => {
  clearRecordPoll()
  recordPollTimer = setInterval(pollRecordStatus, 2000)
}

const startRecording = async () => {
  const url = (recordUrl.value || '').trim()
  if (!url || ['https://', 'http://'].includes(url)) {
    ElMessage.warning(t('uiAutomation.scriptEditor.recorder.emptyUrl'))
    return
  }

  recordStarting.value = true
  try {
    const res = await startCodegenRecording({
      url,
      browser: recordBrowser.value,
      language: recordLanguage.value,
      project_id: projectId.value === ALL_PROJECTS ? null : projectId.value,
      script_name: recordScriptName.value.trim(),
      auto_login: recordSaveState.value
    })
    const data = res.data || res
    recordDialogVisible.value = false
    recording.value = true
    addLog('info', data.message || t('uiAutomation.scriptEditor.recorder.recordStarted'))
    startRecordPolling()
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.scriptEditor.recorder.recordStartFailed')
    ElMessage.error(msg)
    addLog('error', msg)
  } finally {
    recordStarting.value = false
  }
}

const stopRecording = async () => {
  recordStopping.value = true
  clearRecordPoll()
  try {
    const res = await stopCodegenRecording()
    const data = res.data || res
    await onRecordFinished(data.session)
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.scriptEditor.recorder.recordStopFailed')
    ElMessage.error(msg)
    addLog('error', msg)
    // 结束失败且仍在录制中，恢复轮询
    if (recording.value) startRecordPolling()
  } finally {
    recordStopping.value = false
  }
}

// ---- 脚本回放弹窗 ----
const replayDialogVisible = ref(false)
const replayBrowser = ref('chromium')
const replayHeadless = ref(true)
const replayBaseUrl = ref('')
const replayLogs = ref('')
const replayStatus = ref('idle') // idle | running | success | failed
const replayRunning = ref(false)

const replayStatusText = computed(() => {
  const map = {
    idle: t('uiAutomation.scriptEditor.replayDialog.statusIdle'),
    running: t('uiAutomation.scriptEditor.replayDialog.statusRunning'),
    success: t('uiAutomation.scriptEditor.replayDialog.statusSuccess'),
    failed: t('uiAutomation.scriptEditor.replayDialog.statusFailed')
  }
  return map[replayStatus.value] || map.idle
})

const replayStatusTagType = computed(() => {
  if (replayStatus.value === 'running') return 'warning'
  if (replayStatus.value === 'success') return 'success'
  if (replayStatus.value === 'failed') return 'danger'
  return 'info'
})

const openReplayDialog = () => {
  replayStatus.value = 'idle'
  replayLogs.value = ''
  // 默认带入当前项目的 base_url
  const currentProject = projects.value.find(p => p.id === projectId.value)
  replayBaseUrl.value = currentProject?.base_url || ''
  replayDialogVisible.value = true
}

const startReplay = async () => {
  const content = scriptContent.value?.trim()
  if (!content) {
    ElMessage.warning(t('uiAutomation.scriptEditor.messages.emptyScript'))
    return
  }

  replayStatus.value = 'running'
  replayRunning.value = true
  replayLogs.value = t('uiAutomation.scriptEditor.replayDialog.runningTip')
  try {
    const res = await replayCodegenScript({
      content,
      language: scriptLanguage.value,
      framework: scriptFramework.value,
      browser: replayBrowser.value,
      headless: replayHeadless.value,
      base_url: replayBaseUrl.value.trim(),
      project_id: projectId.value === ALL_PROJECTS ? null : projectId.value
    })
    const data = res.data || res
    const parts = [data.logs, data.stdout, data.stderr, data.error].filter(Boolean)
    replayLogs.value = parts.join('\n') || t('uiAutomation.scriptEditor.replayDialog.notExecuted')
    replayStatus.value = data.status === 'success' ? 'success' : 'failed'
    if (data.status === 'success') {
      ElMessage.success(t('uiAutomation.scriptEditor.replayDialog.replaySuccess'))
      addLog('success', t('uiAutomation.scriptEditor.replayDialog.replaySuccess'))
    } else {
      ElMessage.error(data.error || t('uiAutomation.scriptEditor.replayDialog.replayFailed'))
      addLog('error', data.error || t('uiAutomation.scriptEditor.replayDialog.replayFailed'))
    }
  } catch (error) {
    replayStatus.value = 'failed'
    const msg = error.response?.data?.error || error.message || t('uiAutomation.scriptEditor.replayDialog.replayFailed')
    replayLogs.value = msg
    ElMessage.error(msg)
    addLog('error', msg)
  } finally {
    replayRunning.value = false
  }
}

const clearLogs = () => {
  executionLogs.value = []
}

const addLog = (level, message) => {
  executionLogs.value.push({
    level,
    message,
    timestamp: new Date()
  })

  // 保持最多100条日志
  if (executionLogs.value.length > 100) {
    executionLogs.value = executionLogs.value.slice(-100)
  }
}

// 辅助方法
const getTreeNodeIcon = (type) => {
  return type === 'page' ? Folder : Document
}

const getElementTypeText = (type) => {
  const typeMap = {
    'BUTTON': t('uiAutomation.element.elementTypes.button'),
    'INPUT': t('uiAutomation.element.elementTypes.input'),
    'LINK': t('uiAutomation.element.elementTypes.link'),
    'DROPDOWN': t('uiAutomation.element.elementTypes.dropdown'),
    'CHECKBOX': t('uiAutomation.element.elementTypes.checkbox'),
    'RADIO': t('uiAutomation.element.elementTypes.radio'),
    'TEXT': t('uiAutomation.element.elementTypes.text'),
    'IMAGE': t('uiAutomation.element.elementTypes.image'),
    'CONTAINER': t('uiAutomation.element.elementTypes.container'),
    'TABLE': t('uiAutomation.element.elementTypes.table'),
    'FORM': t('uiAutomation.element.elementTypes.form'),
    'MODAL': t('uiAutomation.element.elementTypes.modal')
  }
  return typeMap[type] || type
}

const formatTime = (timestamp) => {
  return timestamp.toLocaleTimeString()
}

// 监听器
watch(elementFilter, (val) => {
  // 树形筛选会自动处理
})

watch(scriptLanguage, (newLang) => {
  addLog('info', t('uiAutomation.scriptEditor.messages.switchLanguage', { lang: newLang }))
})

// 组件挂载
onMounted(async () => {
  await loadProjects()

  projectId.value = ALL_PROJECTS
  await onProjectChange()

  // 为textarea添加事件监听
  if (codeEditor.value) {
    codeEditor.value.addEventListener('click', updateCursorPosition)
    codeEditor.value.addEventListener('keyup', updateCursorPosition)
  }

  // 恢复进行中的录制会话（如页面刷新后）
  try {
    const res = await getCodegenStatus({ include_content: 0 })
    const data = res.data || res
    if (data.session && ['starting', 'recording'].includes(data.session.status)) {
      recording.value = true
      addLog('info', t('uiAutomation.scriptEditor.recorder.recordStarted'))
      startRecordPolling()
    }
  } catch (error) {
    console.error('restore codegen session failed:', error)
  }
})

onBeforeUnmount(() => {
  clearRecordPoll()
})
</script>

<style scoped>
.script-editor-enhanced {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e6e6e6;
  background: white;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  align-items: center;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  width: 300px;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  background: white;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  padding: 0 15px;
  box-sizing: border-box;
  border-bottom: 1px solid #e6e6e6;
  background-color: #fafafa;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.panel-header .el-input {
  flex: 1;
  min-width: 0;
}

.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e6e6e6;
}

.right-panel {
  width: 350px;
}

.panel-content {
  padding: 15px;
  flex: 1;
  overflow-y: auto;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border-bottom: 1px solid #e6e6e6;
  background-color: #fafafa;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-right .el-button {
  display: flex;
  align-items: center;
  gap: 4px;
}

.recording-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 15px;
  background: #fef0f0;
  border-bottom: 1px solid #fbc4c4;
  font-size: 13px;
  flex-shrink: 0;
}

.recording-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
  animation: recording-blink 1.2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes recording-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.recording-text {
  flex: 1;
  color: #f56c6c;
}

.record-steps {
  margin: 6px 0 22px;
}

.record-form :deep(.el-radio) {
  margin-right: 18px;
}

.save-state-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

/* 脚本回放弹窗 */
.replay-dialog .replay-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.replay-dialog .replay-script-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.replay-dialog .replay-label {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.replay-dialog .replay-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.replay-dialog .replay-headless {
  margin-right: 2px;
}

.replay-dialog .replay-base-url {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.replay-dialog .replay-base-url-label {
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}

.replay-dialog .replay-logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  font-size: 13px;
  color: #303133;
}

.replay-dialog .replay-log-body {
  height: 300px;
  background: #1e1e1e;
  border-radius: 0 0 4px 4px;
  padding: 12px;
  overflow: auto;
}

.replay-dialog .replay-log-pre {
  margin: 0;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}

.replay-dialog .replay-log-empty {
  color: #8a8a8a;
  font-size: 13px;
}

.code-editor-container {
  flex: 1;
  position: relative;
}

.code-editor {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 15px;
  background-color: #1e1e1e;
  color: #d4d4d4;
  tab-size: 2;
}

.editor-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 15px;
  border-top: 1px solid #e6e6e6;
  background-color: #fafafa;
  font-size: 12px;
  color: #666;
}

.tree-node {
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: space-between;
  font-size: 14px;
  padding-right: 8px;
}

.node-icon {
  margin-right: 5px;
  font-size: 16px;
}

.node-label {
  flex: 1;
}

.node-actions {
  display: flex;
  gap: 5px;
}

.log-controls {
  margin-bottom: 10px;
}

.log-output {
  height: 400px;
  overflow-y: auto;
  border: 1px solid #e6e6e6;
  border-radius: 4px;
  padding: 10px;
  background-color: #1e1e1e;
  color: #fff;
  font-family: monospace;
  font-size: 12px;
}

.log-entry {
  margin-bottom: 5px;
  display: flex;
  gap: 10px;
}

.log-time {
  color: #888;
}

.log-level {
  font-weight: bold;
  min-width: 60px;
}

.log-entry.info .log-level {
  color: #67c23a;
}

.log-entry.error .log-level {
  color: #f56c6c;
}

.log-entry.success .log-level {
  color: #67c23a;
}

.element-detail {
  padding: 10px;
}

.element-detail h4 {
  margin: 0 0 15px 0;
  color: #333;
}

.element-actions {
  display: flex;
  gap: 10px;
}
</style>
