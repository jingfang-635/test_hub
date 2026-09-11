<template>
  <div class="element-manager">
    <div class="element-layout">
      <!-- 左侧页面树 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <el-select v-model="selectedProject" :placeholder="$t('uiAutomation.common.selectProject')" @change="onProjectChange">
            <el-option :label="$t('uiAutomation.common.allProjects')" value="all" />
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
          <div class="header-actions">
            <el-button type="primary" size="small" @click="openCreatePageDialog" :title="$t('uiAutomation.element.createPage')">
              <el-icon><Folder /></el-icon>
            </el-button>
            <el-button type="success" size="small" @click="createEmptyElement" :title="$t('uiAutomation.element.addElement')">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="page-tree">
          <el-tree
            ref="treeRef"
            :key="treeKey"
            :data="treeData"
            :props="treeProps"
            node-key="id"
            :expand-on-click-node="false"
            :default-expanded-keys="expandedKeys"
            :draggable="true"
            :allow-drag="allowDrag"
            :allow-drop="allowDrop"
            @node-click="onNodeClick"
            @node-contextmenu="onNodeRightClick"
            @node-expand="onNodeExpand"
            @node-collapse="onNodeCollapse"
            @node-drop="onNodeDrop"
          >
            <template #default="{ node, data }">
              <div class="tree-node" :class="{ 'is-element': data.type === 'element' }">
                <el-icon v-if="data.type === 'page'">
                  <Folder />
                </el-icon>
                <el-icon v-else>
                  <Document />
                </el-icon>

                <!-- 页面名称编辑 -->
                <div v-if="data.type === 'page' && editingNodeId === data.id" class="node-edit">
                  <el-input
                    v-model="editingNodeName"
                    size="small"
                    @blur="savePageName"
                    @keyup.enter="savePageName"
                    @keyup.esc="cancelEdit"
                    ref="editInputRef"
                  />
                </div>

                <!-- 普通显示模式 -->
                <span v-else class="node-label">{{ node.label }}</span>

                <span v-if="data.type === 'element'" class="element-type-tag" :class="data.element_type?.toLowerCase()">
                  {{ getElementTypeLabel(data.element_type) }}
                </span>

                <!-- 元素节点悬浮操作按钮 -->
                <span v-if="data.type === 'element' && data.id !== 'unassigned'" class="node-actions" @click.stop>
                  <el-tooltip :content="$t('uiAutomation.element.nodeActions.copyTooltip')" placement="top">
                    <el-icon class="action-icon copy-icon" @click="copyElementNode(data)">
                      <DocumentCopy />
                    </el-icon>
                  </el-tooltip>
                  <el-tooltip :content="$t('uiAutomation.element.nodeActions.deleteTooltip')" placement="top">
                    <el-icon class="action-icon delete-icon" @click="deleteElementNode(data)">
                      <Delete />
                    </el-icon>
                  </el-tooltip>
                </span>
              </div>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 右侧元素详情 -->
      <div class="main-content">
        <div v-if="!selectedElement" class="empty-state">
          <el-empty :description="$t('uiAutomation.element.emptyElementTip')">
            <el-button type="primary" @click="createEmptyElement">{{ $t('uiAutomation.element.createNewElement') }}</el-button>
          </el-empty>
        </div>

        <div v-else class="element-detail">
          <!-- 元素基本信息 -->
          <div class="element-header">
            <div class="element-info">
              <el-form ref="elementHeaderFormRef" :model="selectedElement" :rules="elementHeaderRules" inline>
                <el-form-item prop="name" :label="$t('uiAutomation.element.elementName')" required>
                  <el-input
                    v-model="selectedElement.name"
                    :placeholder="$t('uiAutomation.element.elementNamePlaceholder')"
                    style="width: 300px"
                    @blur="validateHeaderField('name')"
                  />
                </el-form-item>
                <el-form-item :label="$t('uiAutomation.element.elementType')">
                  <el-select v-model="selectedElement.element_type" :placeholder="$t('uiAutomation.element.elementType')" style="width: 120px;">
                    <el-option :label="$t('uiAutomation.element.elementTypes.button')" value="BUTTON" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.input')" value="INPUT" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.link')" value="LINK" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.dropdown')" value="DROPDOWN" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.checkbox')" value="CHECKBOX" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.radio')" value="RADIO" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.text')" value="TEXT" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.image')" value="IMAGE" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.table')" value="TABLE" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.form')" value="FORM" />
                    <el-option :label="$t('uiAutomation.element.elementTypes.modal')" value="MODAL" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveElement" :loading="saving" ref="saveButtonRef">
                    {{ $t('uiAutomation.common.save') }}
                  </el-button>
                  <el-button
                    v-if="selectedElement.id"
                    class="detail-delete-btn"
                    :loading="deleting"
                    @click="deleteSelectedElement"
                  >
                    {{ $t('uiAutomation.common.delete') }}
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- 元素配置 -->
          <div class="element-form">
            <el-form ref="elementFormRef" :key="formKey" :model="selectedElement" :rules="elementRules" label-width="120px">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item :label="$t('uiAutomation.element.page')">
                    <el-select v-model="selectedElement.page" :placeholder="$t('uiAutomation.element.selectPage')">
                      <el-option
                        v-for="page in pages"
                        :key="page.id"
                        :label="page.name"
                        :value="page.name"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="$t('uiAutomation.element.componentName')">
                    <el-input v-model="selectedElement.component_name" :placeholder="$t('uiAutomation.element.componentNamePlaceholder')" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item :label="$t('uiAutomation.element.waitTimeout')">
                    <el-input-number v-model="selectedElement.wait_timeout" :min="1" :max="60" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="$t('uiAutomation.element.forceAction')">
                    <div class="force-action-row">
                      <el-switch v-model="selectedElement.force_action" />
                      <span class="form-help-text force-action-tip">
                        {{ $t('uiAutomation.element.forceActionTip') }}
                      </span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item :label="$t('uiAutomation.element.elementScreenshot')">
                <div class="element-shot-box">
                  <el-image
                    v-if="selectedElement.screenshot"
                    :src="resolveMediaUrl(selectedElement.screenshot)"
                    fit="contain"
                    :preview-src-list="[resolveMediaUrl(selectedElement.screenshot)]"
                    class="element-shot-img"
                  >
                    <template #error>
                      <span class="element-shot-empty">{{ $t('uiAutomation.element.noElementScreenshot') }}</span>
                    </template>
                  </el-image>
                  <span v-else class="element-shot-empty">{{ $t('uiAutomation.element.noElementScreenshot') }}</span>
                </div>
              </el-form-item>

              <el-form-item :label="$t('uiAutomation.element.primarySelector')" required>
                <div class="locator-editor">
                  <el-form-item prop="locator_strategy_id" class="locator-strategy-item">
                    <el-select
                      v-model="selectedElement.locator_strategy_id"
                      :key="`strategy-${formKey}-${selectedElement.locator_strategy_id || 'null'}`"
                      :placeholder="$t('uiAutomation.element.rules.strategyRequired')"
                      style="width: 140px"
                      @blur="validateField('locator_strategy_id')"
                    >
                      <el-option
                        v-for="strategy in locatorStrategies"
                        :key="strategy.id"
                        :label="strategy.name"
                        :value="strategy.id"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item prop="locator_value" class="locator-value-item">
                    <el-input
                      v-model="selectedElement.locator_value"
                      :placeholder="$t('uiAutomation.element.locatorExpressionPlaceholder')"
                      @blur="validateField('locator_value')"
                    />
                  </el-form-item>
                  <button
                    type="button"
                    class="locator-row-action locator-tip-toggle"
                    :title="$t('uiAutomation.element.locatorTip.toggle')"
                    @click="showLocatorTip = !showLocatorTip"
                  >
                    <el-icon class="locator-tip-toggle-icon" :class="{ expanded: showLocatorTip }">
                      <ArrowDown />
                    </el-icon>
                  </button>
                </div>
                <div v-show="showLocatorTip" class="form-help-text">
                  {{ $t('uiAutomation.element.locatorTip.title') }}<br>
                  - {{ $t('uiAutomation.element.locatorTip.id') }}<br>
                  - {{ $t('uiAutomation.element.locatorTip.css') }}<br>
                  - {{ $t('uiAutomation.element.locatorTip.xpath') }}<br>
                  - {{ $t('uiAutomation.element.locatorTip.other') }}
                </div>
              </el-form-item>

              <el-form-item :label="$t('uiAutomation.element.backupSelectors')">
                <div class="backup-list">
                  <div
                    v-for="(backup, bIdx) in (selectedElement.backup_locators || [])"
                    :key="backup._key || `backup-${bIdx}`"
                    class="locator-editor backup-row"
                  >
                    <el-select
                      v-model="backup.strategy"
                      style="width: 140px"
                      :placeholder="$t('uiAutomation.element.locatorStrategy')"
                    >
                      <el-option
                        v-for="strategy in locatorStrategies"
                        :key="strategy.id"
                        :label="strategy.name"
                        :value="strategy.name"
                      />
                    </el-select>
                    <el-input
                      v-model="backup.value"
                      :placeholder="$t('uiAutomation.element.locatorExpressionPlaceholder')"
                    />
                    <button
                      type="button"
                      class="locator-row-action locator-delete-btn"
                      @click="removeBackupLocator(bIdx)"
                    >
                      <el-icon><Delete /></el-icon>
                    </button>
                  </div>
                  <el-button type="primary" size="small" class="add-backup-btn" @click="addBackupLocator">
                    + {{ $t('uiAutomation.element.addBackupSelector') }}
                  </el-button>
                </div>
              </el-form-item>

              <el-form-item :label="$t('uiAutomation.common.description')">
                <el-input v-model="selectedElement.description" type="textarea" :rows="3" :placeholder="$t('uiAutomation.element.descriptionPlaceholder')" />
              </el-form-item>
            </el-form>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建页面对话框 -->
    <el-dialog v-model="showCreatePageDialog" :title="$t('uiAutomation.element.createPageTitle')" width="500px" :close-on-click-modal="false">
      <el-form ref="pageFormRef" :model="pageForm" :rules="pageRules" label-width="100px">
        <el-form-item :label="$t('uiAutomation.element.pageName')" prop="name">
          <el-input v-model="pageForm.name" :placeholder="$t('uiAutomation.element.pageNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.element.parentPage')">
          <el-select v-model="pageForm.parent_page" :placeholder="$t('uiAutomation.element.selectParentPage')" clearable>
            <el-option
              v-for="page in getAllPages()"
              :key="page.id"
              :label="page.name"
              :value="page.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.common.description')" prop="description">
          <el-input v-model="pageForm.description" type="textarea" :rows="3" :placeholder="$t('uiAutomation.element.descriptionPlaceholder')" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="cancelCreatePage">{{ $t('uiAutomation.common.cancel') }}</el-button>
        <el-button type="primary" @click="createPage">{{ $t('uiAutomation.common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 右键菜单：挂到 body，避免被侧边栏 overflow 裁切 -->
    <Teleport to="body">
      <ul
        ref="contextMenuRef"
        v-show="showContextMenu"
        class="element-context-menu"
        :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
      >
        <li @click="addContextElement">{{ $t('uiAutomation.element.contextMenu.addElement') }}</li>
        <li v-if="rightClickedNode && rightClickedNode.type === 'page'" @click="addSubPage">
          {{ $t('uiAutomation.element.contextMenu.addSubPage') }}
        </li>
        <li v-if="rightClickedNode" @click="editNode">
          {{ $t('uiAutomation.element.contextMenu.edit') }}
        </li>
        <li v-if="rightClickedNode" @click="deleteNode">
          {{ $t('uiAutomation.element.contextMenu.delete') }}
        </li>
      </ul>
    </Teleport>

    <!-- 编辑页面对话框 -->
    <el-dialog v-model="showEditPageDialog" :title="$t('uiAutomation.element.editPageTitle')" width="500px" :close-on-click-modal="false">
      <el-form ref="editPageFormRef" :model="editPageForm" :rules="pageRules" label-width="100px">
        <el-form-item :label="$t('uiAutomation.element.pageName')" prop="name">
          <el-input v-model="editPageForm.name" :placeholder="$t('uiAutomation.element.pageNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.element.parentPage')">
          <el-select v-model="editPageForm.parent_page" :placeholder="$t('uiAutomation.element.selectParentPage')" clearable>
            <el-option
              v-for="page in getAllPagesExceptCurrent(editPageForm.id)"
              :key="page.id"
              :label="page.name"
              :value="page.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.common.description')" prop="description">
          <el-input v-model="editPageForm.description" type="textarea" :rows="3" :placeholder="$t('uiAutomation.element.descriptionPlaceholder')" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEditPageDialog = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
        <el-button type="primary" @click="updatePage">{{ $t('uiAutomation.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, FolderAdd, Document, Search, Edit, Delete,
  Folder, Document as DocumentIcon, Operation, DocumentCopy, ArrowDown
} from '@element-plus/icons-vue'
import {
  loadUiAutomationProjects,
  getElements,
  createElement,
  getElementDetail,
  updateElement,
  deleteElement,
  getElementTree,
  getElementGroupTree,
  getElementGroups,
  createElementGroup,
  updateElementGroup,
  deleteElementGroup,
  getLocatorStrategies,
  validateElementLocator,
  generateElementSuggestions
} from '@/api/ui_automation'

// 国际化
const { t } = useI18n()

// 响应式数据
const projects = ref([])
const selectedProject = ref('all')
const ALL_PROJECTS = 'all'
/** 全部项目模式下，临时指定写入目标项目（如右键在某页面下新建） */
const writeProjectOverride = ref(null)

const isAllProjectsSelected = () => selectedProject.value === ALL_PROJECTS || selectedProject.value === ''

/** 当前写入操作使用的项目 ID（全部项目模式下需指定具体项目） */
const resolveWriteProjectId = (element = null) => {
  if (writeProjectOverride.value) return writeProjectOverride.value
  if (!isAllProjectsSelected()) return selectedProject.value
  return element?.project_id || element?.project?.id || null
}

const ensureWriteProjectSelected = (element = null) => {
  const projectId = resolveWriteProjectId(element)
  if (!projectId) {
    ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
    return null
  }
  return projectId
}

/** 列表/树查询参数：全部项目不传 project */
const getProjectQueryParams = () => (
  isAllProjectsSelected() ? {} : { project: selectedProject.value }
)
const pages = ref([])
const locatorStrategies = ref([])
const treeData = ref([])
const selectedElement = ref(null)
const expandedKeys = ref([])
const firstLoadMap = new Map() // 按项目记录是否首次加载，首次加载默认展开所有页面
const treeKey = ref(0) // 用于强制重新渲染树组件
const formKey = ref(0) // 用于强制重新渲染表单组件

// 表单引用
const treeRef = ref(null)
const pageFormRef = ref(null)
const editPageFormRef = ref(null)
const elementFormRef = ref(null)
const elementHeaderFormRef = ref(null)

// 对话框控制
const showCreatePageDialog = ref(false)
const showEditPageDialog = ref(false)

// 右键菜单
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuRef = ref(null)
const rightClickedNode = ref(null)

// 表单数据
const pageForm = reactive({
  name: '',
  description: '',
  parent_page: null
})

const editPageForm = reactive({
  id: null,
  name: '',
  description: '',
  parent_page: null
})

// 树形组件配置
const treeProps = {
  children: 'children',
  label: 'name'
}

// 表单验证规则
const pageRules = computed(() => ({
  name: [
    { required: true, message: t('uiAutomation.element.rules.pageNameRequired'), trigger: 'blur' }
  ]
}))

// 元素表单头部验证规则（元素名称）
const elementHeaderRules = computed(() => ({
  name: [
    { required: true, message: t('uiAutomation.element.rules.nameRequired'), trigger: 'blur' },
    { min: 1, max: 200, message: t('uiAutomation.element.rules.nameLength'), trigger: 'blur' }
  ]
}))

// 元素表单验证规则
const elementRules = computed(() => ({
  locator_strategy_id: [
    { required: true, message: t('uiAutomation.element.rules.strategyRequired'), trigger: 'change' }
  ],
  locator_value: [
    { required: true, message: t('uiAutomation.element.rules.locatorRequired'), trigger: 'blur' },
    { min: 1, max: 500, message: t('uiAutomation.element.rules.locatorLength'), trigger: 'blur' }
  ]
}))

// 获取元素类型标签
const getElementTypeLabel = (type) => {
  const typeKey = type?.toLowerCase()
  const typeMap = {
    'button': t('uiAutomation.element.elementTypes.button'),
    'input': t('uiAutomation.element.elementTypes.input'),
    'link': t('uiAutomation.element.elementTypes.link'),
    'dropdown': t('uiAutomation.element.elementTypes.dropdown'),
    'checkbox': t('uiAutomation.element.elementTypes.checkbox'),
    'radio': t('uiAutomation.element.elementTypes.radio'),
    'text': t('uiAutomation.element.elementTypes.text'),
    'image': t('uiAutomation.element.elementTypes.image'),
    'table': t('uiAutomation.element.elementTypes.table'),
    'form': t('uiAutomation.element.elementTypes.form'),
    'modal': t('uiAutomation.element.elementTypes.modal')
  }
  return typeMap[typeKey] || type
}

// 获取所有页面
const getAllPages = () => {
  const allPages = []

  const traverse = (nodes) => {
    nodes.forEach(node => {
      if (node.type === 'page') {
        allPages.push({
          id: node.id,
          name: node.name
        })
      }
      if (node.children) {
        traverse(node.children)
      }
    })
  }

  traverse(treeData.value)
  return allPages
}

// 获取所有页面（除了指定ID的页面）
const getAllPagesExceptCurrent = (currentId) => {
  const allPages = []

  const traverse = (nodes) => {
    nodes.forEach(node => {
      if (node.type === 'page' && node.id !== currentId) {
        allPages.push({
          id: node.id,
          name: node.name
        })
      }
      if (node.children) {
        traverse(node.children)
      }
    })
  }

  traverse(treeData.value)
  return allPages
}

// 页面名称编辑相关
const editingNodeId = ref(null)
const editingNodeName = ref('')
const editInputRef = ref(null)

// 状态
const saving = ref(false)
const deleting = ref(false)
const validating = ref(false)
const moving = ref(false) // 拖拽移动锁，防止并发操作
const generating = ref(false)
const suggestions = ref([])
const showLocatorTip = ref(false)


// 将关键变量暴露到window对象，方便在控制台调试
const exposeToWindow = () => {
  if (typeof window !== 'undefined') {
    window.ELEMENTS_DEBUG = {
      treeData,
      projects,
      selectedElement,
      loadElementTree,
      treeRef: typeof treeRef !== 'undefined' ? treeRef : null,
      expandedKeys,
      pages,
      $vm: { // 当前组件实例
        treeData: treeData.value,
        projects: projects.value,
        pages: pages.value,
        expandedKeys: expandedKeys.value
      }
    }
    console.log('=== Vue组件调试信息已暴露 ===')
    console.log('Window可用调试变量已设置')
    console.log('控制台可直接访问:')
    console.log('  window.ELEMENTS_DEBUG.treeData')
    console.log('  window.ELEMENTS_DEBUG.projects')
    console.log('  window.ELEMENTS_DEBUG.selectedElement')
    console.log('==============================')
  }
}

// 组件挂载
onMounted(async () => {
  console.log('=== 组件挂载开始 ===')

  await loadProjects()
  await loadLocatorStrategies()

  console.log('项目数量:', projects.value.length)
  console.log('定位策略:', locatorStrategies.value.length)

  // 默认「全部项目」
  selectedProject.value = ALL_PROJECTS
  await onProjectChange()

  // 暴露调试信息
  exposeToWindow()

  console.log('=== 组件挂载完成 ===')
})

/** 与「项目与版本」一致：仅展示本模块已关联的主项目 */
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
    console.error('获取项目列表失败:', error)
    ElMessage.error('加载项目列表失败')
  }
}

// 提供控制台调试帮助函数
const debugTree = () => {
  if (typeof window !== 'undefined') {
    console.log('=== 树数据调试 ===')
    console.log('treeData:', treeData.value)
    console.log('页面对象:',
      treeData.value.map(p => ({
        id: p.id,
        name: p.name,
        type: p.type,
        children: p.children?.length || 0,
        elementChildren: p.children?.filter(c => c.type === 'element').map(e => e.name) || []
      }))
    )

    // 找出所有元素
    const allElements = []
    const findElements = (nodes, parent) => {
      nodes.forEach(node => {
        if (node.type === 'element') {
          allElements.push({
            name: node.name,
            id: node.id,
            parent: parent
          })
        } else if (node.type === 'page' && node.children) {
          findElements(node.children, node.name)
        }
      })
    }
    findElements(treeData.value, null)
    console.log('所有元素:', allElements)

    // 暴露到window
    window.debugTreeData = debugTree
    console.log('调试函数已挂载到 window.debugTreeData()')
    console.log('===============================')
  }
}

// 加载定位策略
const loadLocatorStrategies = async () => {
  try {
    const response = await getLocatorStrategies()
    locatorStrategies.value = response.data?.results || response.data || []
  } catch (error) {
    console.error('获取定位策略失败:', error)
  }
}

// 加载页面（分组）
const loadPages = async () => {
  if (!selectedProject.value) return

  try {
    const response = await getElementGroups(getProjectQueryParams())
    pages.value = response.data?.results || response.data || []
  } catch (error) {
    console.error('获取页面失败:', error)
  }
}

// 加载页面树结构
const loadPageTree = async () => {
  if (!selectedProject.value) return

  try {
    const response = await getElementGroupTree(getProjectQueryParams())
    // 构建完整的树形结构
    const buildTree = (groups) => {
      return groups.map(group => ({
        ...group,
        type: 'page',
        children: group.children ? buildTree(group.children) : []
      }))
    }

    treeData.value = buildTree(response.data || [])
  } catch (error) {
    console.error('获取页面树失败:', error)
    treeData.value = []
  }
}

// 加载元素树
const loadElementTree = async () => {
  if (!selectedProject.value) {
    treeData.value = []
    return
  }

  try {
    const query = getProjectQueryParams()
    // 并行加载页面树和元素
    const [pageTreeResponse, elementsResponse] = await Promise.all([
      getElementGroupTree(query),
      getElementTree(query)
    ])

    // 构建完整的树形结构
    const buildTree = (groups) => {
      return groups.map(group => ({
        ...group,
        type: 'page',
        children: group.children ? buildTree(group.children) : []
      }))
    }

    const pageNodes = buildTree(pageTreeResponse.data || [])

    // 调试信息 - 检查API返回的完整响应结构
    console.log('=== 加载元素树调试 ===')
    console.log('页面树响应:', pageTreeResponse)
    console.log('元素响应:', elementsResponse)

    // 打印原始数据进行分析
    console.log('页面树原始数据:', JSON.parse(JSON.stringify(pageTreeResponse.data || []), null, 2))

    const elements = elementsResponse.data?.results || elementsResponse.data || []
    console.log('提取的元素列表:', elements)

    // 获取所有页面的ID，用于调试
    const pageIds = pageNodes.map(page => page.id)
    console.log('页面ID列表:', pageIds)

    // 将元素添加到对应页面下
    const attachedElementIds = new Set()

    const attachElementsToPages = (pages) => {
      pages.forEach(page => {
        // 找到属于当前页面的元素
        const pageElements = elements.filter(element => element.group_id === page.id)
        console.log(`页面 ${page.name} (ID: ${page.id}) 找到 ${pageElements.length} 个关联元素`, pageElements)

        const elementNodes = pageElements.map(element => {
          attachedElementIds.add(element.id)
          return {
            ...element,
            type: 'element'
          }
        })

        // 将元素添加到页面的子节点中
        page.children = page.children ? [...page.children, ...elementNodes] : [...elementNodes]
        console.log(`页面 ${page.name} 现在有 ${page.children.filter(c => c.type === 'element').length} 个子元素`)

        // 递归处理子页面
        if (page.children) {
          attachElementsToPages(page.children.filter(child => child.type === 'page'))
        }
      })
    }

    attachElementsToPages(pageNodes)

    // 添加未关联页面的元素到"未关联页面"节点
    // 包括：1. group_id 为 null/undefined 的元素
    //       2. group_id 指向的页面不存在的元素
    const unassignedElements = elements.filter(element => {
      // 如果没有group_id，肯定是未关联的
      if (!element.group_id) {
        return true
      }
      // 如果有group_id但没有被添加到任何页面（页面不存在），也算未关联
      return !attachedElementIds.has(element.id)
    })

    console.log('未关联页面的元素:', unassignedElements)

    if (unassignedElements.length > 0) {
      const firstEl = unassignedElements[0]
      const unassignedPage = {
        id: 'unassigned',
        name: '未关联页面',
        type: 'page',
        // 便于后续“编辑转正”时确定所属项目
        project_id: isAllProjectsSelected()
          ? (firstEl.project_id || firstEl.project?.id || null)
          : selectedProject.value,
        children: unassignedElements.map(element => ({
          ...element,
          type: 'element'
        }))
      }
      pageNodes.unshift(unassignedPage) // 添加到列表最前面
      console.log(`已添加 ${unassignedElements.length} 个未关联元素到"未关联页面"节点`)
    }

    console.log('最终treeData:', pageNodes)
    treeData.value = pageNodes

    // 首次进入项目时默认展开所有页面分组；后续重新加载（增删改元素、切分组）保持用户手动展开/收起的状态
    const isFirstLoad = !firstLoadMap.has(selectedProject.value)
    if (isFirstLoad) {
      // 收集所有 page 节点（含嵌套子页和未关联页面），全部展开
      const allPageIds = []
      const collectPages = (nodes) => {
        nodes.forEach(n => {
          if (n.type === 'page') {
            allPageIds.push(n.id)
            if (n.children && n.children.length) collectPages(n.children)
          }
        })
      }
      collectPages(pageNodes)
      // 去重赋值，不直接 push 避免重复
      expandedKeys.value = Array.from(new Set(allPageIds))
      firstLoadMap.set(selectedProject.value, true)
    }

    // 将treeData暴露到window，方便在控制台调试
    if (typeof window !== 'undefined') {
      window.vue_treeData = treeData.value
      console.log('treeData已挂载到window.vue_treeData，可在控制台查看')
      console.log('当前treeData结构:', JSON.parse(JSON.stringify(treeData.value)).map(p => ({
        name: p.name,
        id: p.id,
        children: p.children?.filter(c => c.type === 'element').length || 0
      })))
    }
  } catch (error) {
    console.error('获取元素树失败:', error)
    treeData.value = []
  }
}

// 项目切换
const onProjectChange = async () => {
  selectedElement.value = null
  suggestions.value = []

  // 切项目时重置该项目的首次加载标记，确保每次切项目都默认展开所有分组
  if (selectedProject.value) {
    firstLoadMap.delete(selectedProject.value)
  }

  console.log('=== 项目切换调试 ===')
  console.log('当前项目ID:', selectedProject.value)

  await Promise.all([
    loadPages(),
    loadElementTree()
  ])

  console.log('项目切换完成，检查treeData:', treeData.value)
  console.log('treeData长度:', treeData.value.length)
  if (treeData.value.length > 0) {
    console.log('第一页信息:', {
      id: treeData.value[0].id,
      name: treeData.value[0].name,
      type: treeData.value[0].type,
      children: treeData.value[0].children?.length || 0
    })
  }

  // 项目切换时强制刷新树
  treeKey.value += 1
}

// 创建空元素
const openCreatePageDialog = () => {
  writeProjectOverride.value = null
  if (isAllProjectsSelected()) {
    ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
    return
  }
  showCreatePageDialog.value = true
}

const cancelCreatePage = () => {
  showCreatePageDialog.value = false
  writeProjectOverride.value = null
}

const createEmptyElement = (preferredProjectId = null) => {
  const projectId = preferredProjectId || resolveWriteProjectId()
  if (!projectId) {
    ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
    return
  }

  selectedElement.value = {
    name: '',
    element_type: 'BUTTON',
    page: '',
    component_name: '',
    screenshot: '',
    locator_strategy_id: null, // 使用null而不是空字符串
    locator_value: '',
    backup_locators: [],
    wait_timeout: 5,
    force_action: false,  // 强制操作选项，默认禁用
    description: '',
    project_id: projectId
  }
}

const resolveMediaUrl = (url) => {
  if (!url) return ''
  if (String(url).startsWith('data:')) return url
  if (/^https?:\/\//i.test(url)) {
    try {
      const u = new URL(url)
      if (u.pathname.startsWith('/media/')) return u.pathname + u.search
      return url
    } catch (e) {
      return url
    }
  }
  if (url.startsWith('/')) return url
  return `/media/${url.replace(/^\/+/, '')}`
}

let backupKeySeq = 0

/** 把策略名对齐到下拉选项的精确 name（大小写不敏感） */
const resolveStrategyName = (name) => {
  const n = (name || '').trim()
  const list = locatorStrategies.value || []
  if (!n) return list[0]?.name || 'CSS'
  const found = list.find(s => s.name === n || s.name.toLowerCase() === n.toLowerCase())
  return found?.name || n
}

const addBackupLocator = () => {
  if (!selectedElement.value) return
  if (!Array.isArray(selectedElement.value.backup_locators)) {
    selectedElement.value.backup_locators = []
  }
  const primaryName = locatorStrategies.value.find(
    s => s.id === selectedElement.value.locator_strategy_id
  )?.name
  selectedElement.value.backup_locators.push({
    _key: ++backupKeySeq,
    strategy: resolveStrategyName(primaryName),
    value: ''
  })
}

const removeBackupLocator = (index) => {
  if (!Array.isArray(selectedElement.value?.backup_locators)) return
  selectedElement.value.backup_locators.splice(index, 1)
}

/** 规范化备用定位器，保证表单可编辑 */
const normalizeBackupLocators = (el) => {
  if (!el) return el
  el.backup_locators = Array.isArray(el.backup_locators)
    ? el.backup_locators.map(b => ({
        _key: ++backupKeySeq,
        strategy: resolveStrategyName(b.strategy),
        value: b.value || ''
      }))
    : []
  return el
}

// 验证单个字段（用于失焦验证）
const validateField = async (field) => {
  if (!elementFormRef.value) return
  try {
    await elementFormRef.value.validateField(field)
  } catch (error) {
    // 验证失败，不需要做任何处理，错误会自动显示
  }
}

// 验证头部表单字段（元素名称）
const validateHeaderField = async (field) => {
  if (!elementHeaderFormRef.value) return
  try {
    await elementHeaderFormRef.value.validateField(field)
  } catch (error) {
    // 验证失败，不需要做任何处理，错误会自动显示
  }
}

// 验证整个元素表单
const validateElementForm = async () => {
  const results = await Promise.allSettled([
    elementHeaderFormRef.value?.validate() ?? Promise.resolve(),
    elementFormRef.value?.validate() ?? Promise.resolve()
  ])

  // 检查是否有验证失败的情况
  const hasFailed = results.some(result => result.status === 'rejected')
  return !hasFailed
}

// 创建页面
const createPage = async () => {
  const projectId = ensureWriteProjectSelected()
  if (!projectId) return

  const validate = await pageFormRef.value.validate()
  if (!validate) return

  try {
    // 构建创建页面的参数，正确处理父页面参数
    const pageData = {
      name: pageForm.name,
      description: pageForm.description,
      project: projectId
    }

    // 只有当父页面ID存在且不为空时才添加parent_group字段
    if (pageForm.parent_page) {
      pageData.parent_group = pageForm.parent_page
    }

    await createElementGroup(pageData)

    ElMessage.success(t('uiAutomation.element.messages.pageCreateSuccess'))
    showCreatePageDialog.value = false
    writeProjectOverride.value = null

    // 重置表单
    Object.assign(pageForm, {
      name: '',
      description: '',
      parent_page: null
    })

    // 重新加载页面和树
    await Promise.all([
      loadPages(),
      loadElementTree()
    ])

    // 强制刷新树组件
    treeKey.value += 1
  } catch (error) {
    console.error('创建页面失败:', error)
    ElMessage.error(t('uiAutomation.element.messages.pageCreateFailed'))
  }
}

// 节点点击：页面行展开/收起，元素行打开详情
const onNodeClick = async (data, node) => {
  if (data.type === 'page') {
    if (node.expanded) {
      node.collapse()
    } else {
      node.expand()
    }
    return
  }

  if (data.type === 'element') {
    try {
      const response = await getElementDetail(data.id)
      selectedElement.value = normalizeBackupLocators(response.data)

      // 强制刷新表单，确保下拉框正确显示
      formKey.value += 1
      console.log('点击节点时formKey更新为:', formKey.value)
    } catch (error) {
      console.error('获取元素详情失败:', error)
    }
  }
}

// 节点右键点击
const onNodeRightClick = (event, data) => {
  console.log('Node right click event:', event, 'Data:', data)
  event.preventDefault()

  // 隐藏现有菜单
  showContextMenu.value = false

  // 设置右键点击的节点
  rightClickedNode.value = data
  console.log('Set right clicked node:', data)

  // 先按点击位置显示，再根据菜单实际尺寸校正，避免底部/右侧被裁切
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  showContextMenu.value = true

  nextTick(() => {
    const menuEl = contextMenuRef.value
    if (!menuEl) return

    const menuRect = menuEl.getBoundingClientRect()
    const padding = 8
    let x = event.clientX
    let y = event.clientY

    if (x + menuRect.width > window.innerWidth - padding) {
      x = Math.max(padding, window.innerWidth - menuRect.width - padding)
    }
    if (y + menuRect.height > window.innerHeight - padding) {
      y = Math.max(padding, window.innerHeight - menuRect.height - padding)
    }

    contextMenuX.value = x
    contextMenuY.value = y
  })

  // 添加全局点击监听器以隐藏菜单
  const hideMenu = () => {
    console.log('Hide context menu')
    showContextMenu.value = false
    document.removeEventListener('click', hideMenu)
  }

  // 延迟添加监听器，避免立即触发
  setTimeout(() => {
    document.addEventListener('click', hideMenu)
  }, 100)
}

// 节点展开
const onNodeExpand = (data) => {
  if (!expandedKeys.value.includes(data.id)) {
    expandedKeys.value.push(data.id)
  }
}

// 节点收起
const onNodeCollapse = (data) => {
  const index = expandedKeys.value.indexOf(data.id)
  if (index > -1) {
    expandedKeys.value.splice(index, 1)
  }
}

// === 拖拽相关 ===
// 是否允许拖拽：只有元素节点可以拖拽
// 注意：el-tree 的 allowDrag 回调参数是 Node 对象，需通过 .data 访问原始数据
const allowDrag = (node) => {
  return node?.data?.type === 'element'
}

// 是否允许放置：
// 1. 元素可以放置到页面节点内部（inner）
// 2. 元素可以放置到其他元素节点的前后（prev/next），表示加入该元素所在的页面
const allowDrop = (draggingNode, dropNode, type) => {
  const dropData = dropNode?.data
  if (!dropData) return false
  // 拖到页面节点内部
  if (type === 'inner' && dropData.type === 'page') return true
  // 拖到元素节点前后（加入该元素所在页面）
  if ((type === 'prev' || type === 'next') && dropData.type === 'element') return true
  return false
}

// 拖拽完成：更新元素的所属分组和所属页面字段
// 注意：node-drop 事件参数为 Node 对象，dropType 为 'before'/'after'/'inner'
// 性能优化：成功时只做本地 treeData 更新（O(树深度)），失败时才全量重载
const onNodeDrop = async (draggingNode, dropNode, dropType) => {
  const dragData = draggingNode?.data
  const dropData = dropNode?.data

  // 仅处理元素拖拽
  if (!dragData || dragData.type !== 'element') return

  // 加锁：防止用户快速连续拖拽导致并发请求和数据错乱
  if (moving.value) return
  moving.value = true

  let targetGroupId
  let targetPageName

  if (dropType === 'inner' && dropData?.type === 'page') {
    // 拖到页面节点内部
    targetGroupId = dropData.id === 'unassigned' ? null : dropData.id
    targetPageName = dropData.id === 'unassigned' ? '' : dropData.name
  } else if ((dropType === 'before' || dropType === 'after') && dropData?.type === 'element') {
    // 拖到元素节点前后，目标页面为该元素所在的页面（父节点）
    const parentNode = dropNode.parent
    const parentData = parentNode?.data
    if (!parentData || parentData.type !== 'page') {
      ElMessage.warning(t('uiAutomation.element.messages.invalidDropTarget'))
      await loadElementTree()
      treeKey.value += 1
      moving.value = false
      return
    }
    targetGroupId = parentData.id === 'unassigned' ? null : parentData.id
    targetPageName = parentData.id === 'unassigned' ? '' : parentData.name
  } else {
    ElMessage.warning(t('uiAutomation.element.messages.invalidDropTarget'))
    await loadElementTree()
    treeKey.value += 1
    moving.value = false
    return
  }

  // 判断所属页面是否实际发生变化，避免无意义的请求
  const originalGroupId = dragData.group_id || null
  const originalPageName = dragData.page || ''
  const pageChanged = (originalGroupId !== targetGroupId) || (originalPageName !== targetPageName)

  if (!pageChanged) {
    // 页面未变化，仅恢复树结构即可（无需 API 调用）
    await loadElementTree()
    treeKey.value += 1
    moving.value = false
    return
  }

  try {
    // 拖动后所属页面有修改，同步更新 group_id 和 page 字段
    await updateElement(dragData.id, {
      group_id: targetGroupId,
      page: targetPageName,
      project_id: resolveWriteProjectId(dragData) || dragData.project_id
    })
    ElMessage.success(t('uiAutomation.element.messages.moveSuccess'))

    // 性能优化：本地更新 treeData 中该元素的 group_id 和 page 字段
    // 避免全量 loadElementTree()（2次API调用）+ treeKey 重建（销毁重建整棵树DOM）
    updateElementInTreeData(dragData.id, targetGroupId, targetPageName)

    // 若当前选中的是被拖拽的元素，同步更新右侧编辑区的 page 字段
    if (selectedElement.value && selectedElement.value.id === dragData.id) {
      selectedElement.value.page = targetPageName
      selectedElement.value.group_id = targetGroupId
      formKey.value += 1
    }
  } catch (error) {
    console.error('元素移动失败:', error)
    ElMessage.error(t('uiAutomation.element.messages.moveFailed'))
    // 失败时全量重载以恢复正确状态
    await loadElementTree()
    treeKey.value += 1
  } finally {
    moving.value = false
  }
}

// 本地更新 treeData 中指定元素的 group_id 和 page 字段（仅改数据，不重建DOM）
const updateElementInTreeData = (elementId, newGroupId, newPageName) => {
  const updateNode = (nodes) => {
    for (const node of nodes) {
      if (node.type === 'element' && node.id === elementId) {
        node.group_id = newGroupId
        node.page = newPageName
        return true
      }
      if (node.children && node.children.length) {
        if (updateNode(node.children)) return true
      }
    }
    return false
  }
  updateNode(treeData.value)
}

// === 一键复制元素 ===
const copyElementNode = async (data) => {
  if (!data || data.type !== 'element') return
  try {
    // 获取完整的元素详情
    const response = await getElementDetail(data.id)
    const src = response.data
    const projectId = resolveWriteProjectId(src) || resolveWriteProjectId(data) || data.project_id || src.project_id
    if (!projectId) {
      ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
      return
    }
    // 优先使用树节点上的 group_id 和 page（列表接口返回的字段），确保所属页面被复制
    const groupId = data.group_id || src.group_id || null
    const pageName = data.page || src.page || ''
    // 构建新元素数据，名称追加" (副本)"后缀，避免重名
    const copyData = {
      name: `${src.name} (副本)`,
      element_type: src.element_type,
      page: pageName,
      component_name: src.component_name || '',
      locator_strategy_id: src.locator_strategy_id,
      locator_value: src.locator_value,
      backup_locators: Array.isArray(src.backup_locators)
        ? src.backup_locators.map(b => ({ strategy: b.strategy || 'css', value: b.value || '' }))
        : [],
      wait_timeout: src.wait_timeout,
      force_action: src.force_action,
      description: src.description || '',
      project_id: projectId
    }
    // 复制所属页面（分组关联）
    if (groupId) {
      copyData.group_id = groupId
    }
    const createRes = await createElement(copyData)
    ElMessage.success(t('uiAutomation.element.messages.copySuccess'))
    // 重新加载树
    await loadElementTree()
    treeKey.value += 1
    // 选中新复制的元素
    if (createRes.data?.id) {
      try {
        const detailRes = await getElementDetail(createRes.data.id)
        selectedElement.value = normalizeBackupLocators(detailRes.data)
        formKey.value += 1
      } catch (e) {
        console.error('获取复制元素详情失败:', e)
      }
    }
  } catch (error) {
    console.error('元素复制失败:', error)
    ElMessage.error(t('uiAutomation.element.messages.copyFailed') + ': ' + (error.response?.data?.message || error.message || ''))
  }
}

// === 一键删除元素 ===
const deleteElementNode = async (data) => {
  if (!data || data.type !== 'element') return
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.element.messages.deleteConfirm', { name: data.name }),
      t('uiAutomation.element.messages.deleteConfirmTitle'),
      {
        type: 'warning',
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel')
      }
    )
    await deleteElement(data.id)
    ElMessage.success(t('uiAutomation.element.messages.deleteSuccess'))
    // 如果当前选中的是被删除的元素，清空选中
    if (selectedElement.value && selectedElement.value.id === data.id) {
      selectedElement.value = null
    }
    // 重新加载树
    await loadElementTree()
    treeKey.value += 1
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除元素失败:', error)
      ElMessage.error(t('uiAutomation.element.messages.deleteFailed'))
    }
  }
}

// 详情面板删除当前元素
const deleteSelectedElement = async () => {
  if (!selectedElement.value?.id) return
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.element.messages.deleteConfirm', { name: selectedElement.value.name }),
      t('uiAutomation.element.messages.deleteConfirmTitle'),
      {
        type: 'warning',
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel')
      }
    )
    deleting.value = true
    const deletedId = selectedElement.value.id
    await deleteElement(deletedId)
    ElMessage.success(t('uiAutomation.element.messages.deleteSuccess'))
    selectedElement.value = null
    await loadElementTree()
    treeKey.value += 1
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除元素失败:', error)
      ElMessage.error(t('uiAutomation.element.messages.deleteFailed'))
    }
  } finally {
    deleting.value = false
  }
}

// 保存元素
const saveElement = async () => {
  if (!selectedElement.value) return

  // 验证表单
  const isValid = await validateElementForm()
  if (!isValid) {
    ElMessage.error(t('uiAutomation.element.messages.saveFailed'))
    return
  }

  try {
    saving.value = true
    console.log('=== 保存元素调试 ===')
    console.log('当前选中的元素:', selectedElement.value)

    if (selectedElement.value.id) {
      const projectId = resolveWriteProjectId(selectedElement.value)
      if (!projectId) {
        ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
        return
      }
      // 更新元素 - 构建正确的API数据格式
      const elementUpdateData = {
        name: selectedElement.value.name,
        element_type: selectedElement.value.element_type,
        page: selectedElement.value.page,
        component_name: selectedElement.value.component_name,
        description: selectedElement.value.description,
        locator_strategy_id: selectedElement.value.locator_strategy_id,
        locator_value: selectedElement.value.locator_value,
        backup_locators: (() => {
          const seen = new Set()
          const list = []
          for (const b of (selectedElement.value.backup_locators || [])) {
            if (!b.strategy || !b.value) continue
            const key = `${String(b.strategy).toLowerCase()}|${b.value}`
            if (seen.has(key)) continue
            seen.add(key)
            list.push({ strategy: b.strategy, value: b.value })
          }
          return list
        })(),
        wait_timeout: selectedElement.value.wait_timeout,
        force_action: selectedElement.value.force_action,
        project_id: projectId
      }

      // 如果元素有分组（页面），确保传递正确的 group_id
      if (selectedElement.value.page) {
        console.log('更新元素 - 元素关联页面名称:', selectedElement.value.page)

        // 通过遍历树形结构查找对应的页面ID
        const findPageIdByName = (nodes, pageName) => {
          for (const node of nodes) {
            if (node.type === 'page' && node.name === pageName) {
              return node.id
            }
            if (node.children) {
              const foundId = findPageIdByName(node.children, pageName)
              if (foundId) return foundId
            }
          }
          return null
        }

        const pageId = findPageIdByName(treeData.value, selectedElement.value.page)
        if (pageId) {
          elementUpdateData.group_id = pageId
        }
      }

      console.log('更新元素数据:', elementUpdateData)
      await updateElement(selectedElement.value.id, elementUpdateData)

      // 重新获取完整的元素详情以确保所有关联字段正确显示
      const detailResponse = await getElementDetail(selectedElement.value.id)
      selectedElement.value = normalizeBackupLocators(detailResponse.data)
      console.log('更新后获取到完整元素详情:', selectedElement.value)
      console.log('locator_strategy_id值:', selectedElement.value.locator_strategy_id, '类型:', typeof selectedElement.value.locator_strategy_id)
      console.log('locator_strategy对象:', selectedElement.value.locator_strategy)
      console.log('当前locatorStrategies:', locatorStrategies.value)
      console.log('locatorStrategies中是否包含id=' + selectedElement.value.locator_strategy_id + ':',
        locatorStrategies.value.find(s => s.id === selectedElement.value.locator_strategy_id))

      // 强制刷新表单，确保下拉框正确显示
      formKey.value += 1
      console.log('formKey更新为:', formKey.value)

      // 使用nextTick确保DOM更新
      await nextTick()
      console.log('DOM已更新，当前下拉框绑定值:', selectedElement.value.locator_strategy_id)

      ElMessage.success(t('uiAutomation.element.messages.saveSuccess'))
    } else {
      // 创建元素
      const projectId = resolveWriteProjectId(selectedElement.value)
      if (!projectId) {
        ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
        return
      }
      // 确保传递正确的字段名 project_id 而不是 project
      const elementData = {
        ...selectedElement.value,
        backup_locators: (() => {
          const seen = new Set()
          const list = []
          for (const b of (selectedElement.value.backup_locators || [])) {
            if (!b.strategy || !b.value) continue
            const key = `${String(b.strategy).toLowerCase()}|${b.value}`
            if (seen.has(key)) continue
            seen.add(key)
            list.push({ strategy: b.strategy, value: b.value })
          }
          return list
        })(),
        project_id: projectId
      }

      // 如果元素有分组（页面），确保传递 group_id
      if (selectedElement.value.page) {
        console.log('元素关联页面名称:', selectedElement.value.page)
        console.log('当前treeData结构:', treeData.value)

        // 通过遍历树形结构查找对应的页面ID
        const findPageIdByName = (nodes, pageName) => {
          console.log(`在 ${nodes.length} 个节点中查找页面名称: ${pageName}`)
          for (const node of nodes) {
            console.log(`检查节点: ${node.name} (ID: ${node.id}, type: ${node.type})`)
            if (node.type === 'page' && node.name === pageName) {
              console.log(`找到页面! ID: ${node.id}`)
              return node.id
            }
            if (node.children) {
              console.log(`检查子节点:`, node.children.map(c => c.name))
              const foundId = findPageIdByName(node.children, pageName)
              if (foundId) return foundId
            }
          }
          console.log('未找到页面')
          return null
        }

        const pageId = findPageIdByName(treeData.value, selectedElement.value.page)
        console.log('找到的页面ID:', pageId)

        if (pageId) {
          elementData.group_id = pageId
          console.log('设置group_id为:', pageId)
        }
      }

      console.log('创建元素的数据:', elementData)
      const response = await createElement(elementData)
      console.log('创建响应:', response)

      // 重新获取完整的元素详情以确保所有关联字段正确显示
      const detailResponse = await getElementDetail(response.data.id)
      selectedElement.value = normalizeBackupLocators(detailResponse.data)
      console.log('获取到完整元素详情:', selectedElement.value)
      console.log('locator_strategy_id值:', selectedElement.value.locator_strategy_id, '类型:', typeof selectedElement.value.locator_strategy_id)
      console.log('locator_strategy对象:', selectedElement.value.locator_strategy)
      console.log('当前locatorStrategies:', locatorStrategies.value)
      console.log('locatorStrategies中是否包含id=' + selectedElement.value.locator_strategy_id + ':',
        locatorStrategies.value.find(s => s.id === selectedElement.value.locator_strategy_id))
      console.log('el-select绑定的值:', selectedElement.value.locator_strategy_id)

      // 强制刷新表单，确保下拉框正确显示
      formKey.value += 1
      console.log('formKey更新为:', formKey.value)

      // 使用nextTick确保DOM更新
      await nextTick()
      console.log('DOM已更新，当前下拉框绑定值:', selectedElement.value.locator_strategy_id)

      ElMessage.success(t('uiAutomation.element.messages.createSuccess'))
    }

    // 重新加载树（loadElementTree 内部会保持展开状态不变）
    console.log('开始重新加载元素树...')
    await loadElementTree()
    console.log('元素树重新加载完成')

    nextTick(() => {
      console.log('树数据更新完成，保持原展开状态不变，当前expandedKeys:', expandedKeys.value)
    })
  } catch (error) {
    console.error('保存元素失败:', error)
    ElMessage.error(t('uiAutomation.element.messages.saveFailed') + ': ' + (error.response?.data?.message || error.message || t('uiAutomation.messages.error.unknown')))
  } finally {
    saving.value = false
  }
}

// 验证元素
const validateElement = async () => {
  if (!selectedElement.value) return

  try {
    validating.value = true
    const response = await validateElementLocator(selectedElement.value.id)
    const result = response.data

    if (result.is_valid) {
      ElMessage.success(t('uiAutomation.element.messages.validateSuccess'))
    } else {
      ElMessage.error(`${t('uiAutomation.element.messages.validateFailed')}: ${result.validation_message}`)
    }
  } catch (error) {
    ElMessage.error(t('uiAutomation.element.messages.validateFailed'))
    console.error('验证元素失败:', error)
  } finally {
    validating.value = false
  }
}

// 生成建议
const generateSuggestions = async () => {
  if (!selectedElement.value) return

  try {
    generating.value = true
    const response = await generateElementSuggestions(selectedElement.value.id)
    suggestions.value = response.data.suggestions
  } catch (error) {
    console.error('生成建议失败:', error)
  } finally {
    generating.value = false
  }
}

// 保存页面名称
const savePageName = () => {
  // TODO: 实现页面名称保存
  editingNodeId.value = null
}

// 取消编辑
const cancelEdit = () => {
  editingNodeId.value = null
}

// 右键菜单操作函数
// 新增元素
const addContextElement = () => {
  console.log('Add context element clicked')
  showContextMenu.value = false

  const pageNode = rightClickedNode.value?.type === 'page' ? rightClickedNode.value : null
  const preferredProjectId = pageNode?.project_id
    || pageNode?.project?.id
    || null
  createEmptyElement(preferredProjectId)

  // 如果右键点击的是页面节点，设置元素的页面
  if (pageNode) {
    // 特殊处理：如果是"未关联页面"节点，不设置page和group_id
    if (pageNode.id === 'unassigned') {
      console.log('在未关联页面节点下添加元素，不设置page和group_id')
      return
    }

    if (selectedElement.value) {
      selectedElement.value.page = pageNode.name
      // 同时设置group_id，确保元素能正确关联到页面
      selectedElement.value.group_id = pageNode.id
      if (preferredProjectId) {
        selectedElement.value.project_id = preferredProjectId
      }
    }
  }
}

// 新增子页面
const addSubPage = () => {
  console.log('Add sub page clicked')
  showContextMenu.value = false

  // 禁止在"未关联页面"节点下创建子页面
  if (rightClickedNode.value && rightClickedNode.value.id === 'unassigned') {
    ElMessage.warning('未关联页面节点下不能创建子页面')
    return
  }

  if (isAllProjectsSelected()) {
    const pageProjectId = rightClickedNode.value?.project_id || rightClickedNode.value?.project?.id
    if (!pageProjectId) {
      ElMessage.warning(t('uiAutomation.element.messages.selectProject'))
      return
    }
    writeProjectOverride.value = pageProjectId
  } else {
    writeProjectOverride.value = null
  }

  showCreatePageDialog.value = true

  // 如果右键点击的是页面节点，设置父页面
  if (rightClickedNode.value && rightClickedNode.value.type === 'page') {
    pageForm.parent_page = rightClickedNode.value.id
  }
}

// 编辑节点
const editNode = async () => {
  console.log('Edit node clicked, rightClickedNode:', rightClickedNode.value)
  showContextMenu.value = false

  if (!rightClickedNode.value) {
    console.log('No right clicked node')
    return
  }

  console.log('Editing node:', rightClickedNode.value)
  console.log('Node type:', rightClickedNode.value.type)

  if (rightClickedNode.value.type === 'page') {
    // 编辑页面（含“未关联页面”虚拟节点：保存时会转为真实分组）
    console.log('Editing page node')
    editPageForm.id = rightClickedNode.value.id
    editPageForm.name = rightClickedNode.value.name
    editPageForm.description = rightClickedNode.value.description || ''
    editPageForm.parent_page = rightClickedNode.value.parent_group || null
    console.log('Set edit page form data:', editPageForm)
    console.log('Setting showEditPageDialog to true')
    showEditPageDialog.value = true
    console.log('showEditPageDialog value:', showEditPageDialog.value)
  } else if (rightClickedNode.value.type === 'element') {
    console.log('Editing element node')
    // 编辑元素 - 通过API获取完整的元素详情，避免使用树节点的复杂数据
    try {
      const response = await getElementDetail(rightClickedNode.value.id)
      selectedElement.value = normalizeBackupLocators(response.data)
      console.log('Set selected element for editing via API:', selectedElement.value)

      // 强制刷新表单，确保下拉框正确显示
      formKey.value += 1
      console.log('编辑时formKey更新为:', formKey.value)
    } catch (error) {
      console.error('获取元素详情失败:', error)
      ElMessage.error(t('uiAutomation.element.messages.getDetailFailed'))
    }
  } else {
    console.log('Unknown node type:', rightClickedNode.value.type)
  }
}

// 删除节点
const deleteNode = async () => {
  console.log('Delete node clicked, rightClickedNode:', rightClickedNode.value)
  showContextMenu.value = false

  if (!rightClickedNode.value) return

  // 禁止删除"未关联页面"节点
  if (rightClickedNode.value.id === 'unassigned') {
    ElMessage.warning('未关联页面节点不能删除')
    return
  }

  try {
    await ElMessageBox.confirm(
      t('uiAutomation.element.messages.confirmDeleteNode', { name: rightClickedNode.value.name }),
      t('uiAutomation.common.confirmDelete'),
      {
        type: 'warning',
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel')
      }
    )

    console.log('Deleting node:', rightClickedNode.value)

    if (rightClickedNode.value.type === 'page') {
      // 删除页面（分组）
      console.log('Calling deleteElementGroup with id:', rightClickedNode.value.id)
      await deleteElementGroup(rightClickedNode.value.id)
      ElMessage.success(t('uiAutomation.element.messages.pageDeleteSuccess'))
    } else if (rightClickedNode.value.type === 'element') {
      // 删除元素
      console.log('Calling deleteElement with id:', rightClickedNode.value.id)
      await deleteElement(rightClickedNode.value.id)
      ElMessage.success(t('uiAutomation.element.messages.deleteSuccess'))
      // 如果当前选中的是被删除的元素，清空选中
      if (selectedElement.value && selectedElement.value.id === rightClickedNode.value.id) {
        selectedElement.value = null
      }
    }

    console.log('Reload data after deletion')

    // 重新加载数据
    await Promise.all([
      loadPages(),
      loadElementTree()
    ])

    // 强制刷新树组件
    treeKey.value += 1
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error(t('uiAutomation.element.messages.deleteFailed'))
    }
  }
}

// 更新页面
const updatePage = async () => {
  console.log('Update page function called')
  console.log('Edit page form ref:', editPageFormRef.value)

  if (!editPageFormRef.value) {
    console.log('No edit page form ref')
    return
  }

  const validate = await editPageFormRef.value.validate()
  console.log('Validation result:', validate)
  if (!validate) {
    console.log('Validation failed')
    return
  }

  console.log('Updating page with data:', editPageForm)

  try {
    // “未关联页面”是虚拟节点：编辑保存时创建真实分组，并把未关联元素迁入
    if (editPageForm.id === 'unassigned') {
      await convertUnassignedPageToGroup()
      return
    }

    // 构建更新页面的参数，正确处理父页面参数
    const pageData = {
      name: editPageForm.name,
      description: editPageForm.description,
      project_id: resolveWriteProjectId(rightClickedNode.value)
        || rightClickedNode.value?.project_id
        || rightClickedNode.value?.project?.id
        || selectedProject.value
    }

    // 只有当父页面ID存在且不为空时才添加parent_group字段
    // 如果父页面ID为null，表示取消父页面关联
    if (editPageForm.parent_page !== undefined) {
      pageData.parent_group = editPageForm.parent_page
    }

    await updateElementGroup(editPageForm.id, pageData)

    ElMessage.success(t('uiAutomation.element.messages.pageUpdateSuccess'))
    showEditPageDialog.value = false

    // 重新加载页面和树
    await Promise.all([
      loadPages(),
      loadElementTree()
    ])

    // 强制刷新树组件
    treeKey.value += 1
  } catch (error) {
    console.error('更新页面失败:', error)
    const detail = error.response?.data
      ? (typeof error.response.data === 'string'
        ? error.response.data
        : (error.response.data.detail || error.response.data.message || JSON.stringify(error.response.data)))
      : (error.message || '')
    ElMessage.error(
      detail
        ? `${t('uiAutomation.element.messages.pageUpdateFailed')}: ${detail}`
        : t('uiAutomation.element.messages.pageUpdateFailed')
    )
  }
}

// 将“未关联页面”虚拟节点转为真实页面分组，并迁移其中的元素
const convertUnassignedPageToGroup = async () => {
  const unassignedNode = treeData.value.find(n => n.id === 'unassigned') || rightClickedNode.value
  const projectId = ensureWriteProjectSelected(unassignedNode)
  if (!projectId) return

  const pageData = {
    name: editPageForm.name,
    description: editPageForm.description,
    project: projectId
  }
  if (editPageForm.parent_page) {
    pageData.parent_group = editPageForm.parent_page
  }

  const createRes = await createElementGroup(pageData)
  const newGroup = createRes.data
  let newGroupId = newGroup?.id

  // 兼容旧后端未返回 id 的情况：按名称回查刚创建的分组
  if (!newGroupId) {
    const listRes = await getElementGroups({ project: projectId, search: editPageForm.name })
    const groups = listRes.data?.results || listRes.data || []
    const matched = groups.find(g => g.name === editPageForm.name)
    newGroupId = matched?.id
  }

  if (!newGroupId) {
    throw new Error('创建页面分组失败：未返回分组 ID')
  }

  const elementNodes = (unassignedNode?.children || []).filter(c => c.type === 'element')
  if (elementNodes.length > 0) {
    await Promise.all(elementNodes.map(el => updateElement(el.id, {
      group_id: newGroupId,
      page: editPageForm.name,
      project_id: el.project_id || el.project?.id || projectId
    })))
  }

  ElMessage.success(t('uiAutomation.element.messages.pageUpdateSuccess'))
  showEditPageDialog.value = false

  await Promise.all([
    loadPages(),
    loadElementTree()
  ])
  treeKey.value += 1
}
</script>

<style scoped>
.element-manager {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.element-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 300px;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.sidebar-header {
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions {
  display: flex;
  gap: 5px;
  margin-left: auto;
}

.page-tree {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 0;
  flex: 1;
}

.tree-node.is-element {
  cursor: grab;
}

.tree-node.is-element:active {
  cursor: grabbing;
}

.node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.element-type-tag {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: #ecf5ff;
  color: #409eff;
}

/* 节点操作按钮（始终显示） */
.node-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding-right: 4px;
}

.action-icon {
  cursor: pointer;
  font-size: 15px;
  color: #909399;
  transition: color 0.2s;
}

.copy-icon:hover {
  color: #409eff;
}

.delete-icon:hover {
  color: #f56c6c;
}

.detail-delete-btn {
  margin-left: 8px;
  background-color: #f56c6c;
  border-color: #f56c6c;
  color: #fff;
}

.detail-delete-btn:hover,
.detail-delete-btn:focus {
  background-color: #f78989;
  border-color: #f78989;
  color: #fff;
}

.detail-delete-btn:active {
  background-color: #dd6161;
  border-color: #dd6161;
  color: #fff;
}

.main-content {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: #f8f9fa;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #fafafa;
}

.element-header {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.element-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.element-form {
  margin-top: 20px;
}

.form-help-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.element-shot-box {
  width: 120px;
  height: 120px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.element-shot-img {
  width: 120px;
  height: 120px;
}

.element-shot-empty {
  font-size: 12px;
  color: #909399;
  text-align: center;
  padding: 4px;
}

.locator-editor {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.locator-strategy-item,
.locator-value-item {
  margin-bottom: 0;
}

.locator-strategy-item {
  flex-shrink: 0;
  width: 140px;
}

.locator-strategy-item :deep(.el-form-item__content) {
  margin-left: 0 !important;
}

.locator-value-item {
  flex: 1;
  min-width: 0;
}

.locator-value-item :deep(.el-form-item__content) {
  width: 100%;
}

.locator-tip-toggle {
  color: #909399;
}

.locator-tip-toggle:hover {
  color: #409eff;
}

.locator-tip-toggle-icon {
  transition: transform 0.2s;
}

.locator-tip-toggle-icon.expanded {
  transform: rotate(180deg);
}

.locator-row-action {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.locator-row-action:hover,
.locator-row-action:focus {
  border: none;
  background: transparent;
  outline: none;
}

.locator-delete-btn {
  color: #f56c6c;
}

.locator-delete-btn:hover {
  color: #f78989;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.backup-row {
  width: 100%;
}

.backup-row .el-input {
  flex: 1;
}

.add-backup-btn {
  align-self: flex-start;
}

.force-action-row {
  display: flex;
  align-items: center;
}

.force-action-tip {
  margin-top: 0;
  margin-left: 2ch;
}

/* 右键菜单样式（Teleport 到 body，需非 scoped 才能命中） */
</style>

<style>
.element-context-menu {
  position: fixed;
  z-index: 9999;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 5px 0;
  margin: 0;
  list-style: none;
  min-width: 120px;
}

.element-context-menu li {
  padding: 8px 15px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
}

.element-context-menu li:hover {
  background-color: #f5f7fa;
  color: #409eff;
}
</style>