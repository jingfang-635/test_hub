<template>
  <div class="response-viewer">
    <el-tabs v-model="activeTab" class="response-viewer-tabs">
      <el-tab-pane :label="$t('apiTesting.interface.responseBody')" name="body">
        <div class="response-body-panel">
          <div class="body-toolbar">
            <div class="view-toggle">
              <button
                type="button"
                class="toggle-btn"
                :class="{ active: bodyViewMode === 'tree' }"
                :disabled="!isJsonResponse"
                @click="bodyViewMode = 'tree'"
              >
                <el-icon><Menu /></el-icon>
                <span>{{ $t('apiTesting.interface.responseTreeView') }}</span>
              </button>
              <button
                type="button"
                class="toggle-btn"
                :class="{ active: bodyViewMode === 'raw' }"
                @click="bodyViewMode = 'raw'"
              >
                <el-icon><Document /></el-icon>
                <span>{{ $t('apiTesting.interface.responseRawView') }}</span>
              </button>
            </div>

            <div class="jsonpath-bar" v-if="isJsonResponse">
              <el-input
                v-model="jsonPathExpression"
                size="small"
                clearable
                :placeholder="$t('apiTesting.interface.jsonPathQueryPlaceholder')"
                @keyup.enter="runJsonPathQuery"
              />
              <el-button type="primary" size="small" @click="runJsonPathQuery">
                {{ $t('apiTesting.interface.jsonPathQuery') }}
              </el-button>
              <el-tooltip :content="$t('apiTesting.interface.jsonPathHelp')" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>

            <el-button
              size="small"
              class="copy-btn"
              @click="copyJsonPathExpression"
              :disabled="!isJsonResponse || !(jsonPathExpression || '').trim()"
            >
              <el-icon><CopyDocument /></el-icon>
              {{ $t('apiTesting.interface.copy') }}
            </el-button>
          </div>

          <div v-if="jsonPathQueried" class="jsonpath-result-panel">
            <div class="jsonpath-result-header" @click="jsonPathResultExpanded = !jsonPathResultExpanded">
              <span>
                {{ $t('apiTesting.interface.jsonPathQueryResult') }}
                <el-tag size="small" type="info" class="type-tag">{{ jsonPathResultType }}</el-tag>
              </span>
              <el-icon class="expand-icon" :class="{ expanded: jsonPathResultExpanded }">
                <ArrowDown />
              </el-icon>
            </div>
            <div v-show="jsonPathResultExpanded" class="jsonpath-result-body" :class="{ error: !!jsonPathError }">
              <pre>{{ jsonPathError || jsonPathResultText }}</pre>
            </div>
          </div>

          <div v-if="bodyViewMode === 'tree' && isJsonResponse" class="json-tree-panel">
            <div class="json-tree-toolbar">
              <el-input
                v-model="treeSearchKeyword"
                size="small"
                clearable
                :placeholder="$t('apiTesting.interface.responseTreeSearch')"
                :prefix-icon="Search"
              />
              <el-button size="small" @click="expandAllTree">{{ $t('apiTesting.interface.expandAll') }}</el-button>
              <el-button size="small" @click="collapseAllTree">{{ $t('apiTesting.interface.collapseAll') }}</el-button>
            </div>

            <el-tree
              :key="treeRenderKey"
              ref="jsonTreeRef"
              class="json-tree"
              :data="filteredTreeData"
              node-key="id"
              :props="treeProps"
              :default-expanded-keys="expandedKeys"
              :expand-on-click-node="false"
            >
              <template #default="{ data }">
                <div class="json-tree-node-content">
                  <span class="json-key" v-if="data.keyLabel !== undefined">"{{ data.keyLabel }}"</span>
                  <span class="json-colon" v-if="data.keyLabel !== undefined">:</span>
                  <span v-if="data.nodeType === 'object'" class="json-meta">{ }</span>
                  <span v-else-if="data.nodeType === 'array'" class="json-meta">[ {{ data.childCount }} ]</span>
                  <span v-else class="json-value" :class="data.valueType">{{ formatLeafValue(data.value) }}</span>
                  <el-icon
                    class="node-copy"
                    :title="$t('apiTesting.interface.copyJsonPathExpression')"
                    @click.stop="copyNodeJsonPath(data)"
                  >
                    <CopyDocument />
                  </el-icon>
                </div>
              </template>
            </el-tree>
          </div>

          <div v-else class="raw-panel">
            <pre class="raw-content" v-html="highlightedRawBody"></pre>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="headersTabLabel" name="headers">
        <div class="response-headers-panel">
          <el-input
            v-model="headerSearchKeyword"
            size="small"
            clearable
            class="headers-search"
            :placeholder="$t('apiTesting.interface.searchResponseHeaders')"
            :prefix-icon="Search"
          />
          <el-table
            :data="filteredHeaders"
            size="small"
            stripe
            class="headers-table"
            empty-text="—"
          >
            <el-table-column prop="key" label="Key" min-width="180" show-overflow-tooltip />
            <el-table-column prop="value" label="Value" min-width="320" show-overflow-tooltip />
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane
        v-if="assertionsResults?.length"
        :label="$t('apiTesting.interface.assertionResults')"
        name="assertions"
      >
        <slot name="assertions" />
      </el-tab-pane>

      <el-tab-pane
        v-if="extractorsResults?.length"
        :label="$t('apiTesting.interface.extractorResults')"
        name="extractors-results"
      >
        <slot name="extractors" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, CopyDocument, Document, Menu, QuestionFilled, Search } from '@element-plus/icons-vue'
import { JSONPath } from 'jsonpath-plus'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  responseData: {
    type: Object,
    default: null
  },
  assertionsResults: {
    type: Array,
    default: () => []
  },
  extractorsResults: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: String,
    default: 'body'
  }
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const activeTab = computed({
  get: () => props.modelValue || 'body',
  set: (val) => emit('update:modelValue', val)
})

const bodyViewMode = ref('tree')
const jsonPathExpression = ref('')
const jsonPathQueried = ref(false)
const jsonPathResultExpanded = ref(true)
const jsonPathResultValue = ref(null)
const jsonPathError = ref('')
const treeSearchKeyword = ref('')
const headerSearchKeyword = ref('')
const jsonTreeRef = ref(null)
const expandedKeys = ref([])
const treeRenderKey = ref(0)
const treeProps = { children: 'children', label: 'label' }

let nodeIdSeed = 0

const responseJson = computed(() => {
  const data = props.responseData
  if (!data) return null
  if (data.json != null) return data.json
  if (typeof data.body === 'string' && data.body.trim()) {
    try {
      return JSON.parse(data.body)
    } catch (e) {
      return null
    }
  }
  return null
})

const isJsonResponse = computed(() => responseJson.value !== null && responseJson.value !== undefined)

const rawBodyText = computed(() => {
  if (responseJson.value !== null && responseJson.value !== undefined) {
    try {
      return JSON.stringify(responseJson.value, null, 2)
    } catch (e) {
      return String(props.responseData?.body || '')
    }
  }
  return props.responseData?.body || ''
})

const highlightedRawBody = computed(() => {
  if (!rawBodyText.value) return ''
  try {
    return rawBodyText.value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"([^"]+)"\s*:/g, '<span class="tok-key">"$1"</span>:')
      .replace(/:\s*"([^"]*)"/g, ': <span class="tok-string">"$1"</span>')
      .replace(/:\s*(true|false|null)/g, ': <span class="tok-literal">$1</span>')
      .replace(/:\s*(-?\d+(?:\.\d+)?)/g, ': <span class="tok-number">$1</span>')
  } catch (e) {
    return rawBodyText.value
  }
})

const buildJsonPath = (parentPath, keyLabel) => {
  if (keyLabel === undefined || keyLabel === null) return parentPath || '$'
  const key = String(keyLabel)
  if (/^\d+$/.test(key)) return `${parentPath}[${key}]`
  if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
    return parentPath === '$' ? `$.${key}` : `${parentPath}.${key}`
  }
  const escaped = key.replace(/\\/g, '\\\\').replace(/'/g, "\\'")
  return `${parentPath}['${escaped}']`
}

const buildTreeNodes = (value, keyLabel, parentPath = '$') => {
  const id = `n-${++nodeIdSeed}`
  const jsonPath = buildJsonPath(parentPath, keyLabel)
  if (value !== null && typeof value === 'object') {
    if (Array.isArray(value)) {
      return {
        id,
        keyLabel,
        label: keyLabel ?? '[]',
        nodeType: 'array',
        childCount: value.length,
        value,
        jsonPath,
        children: value.map((item, index) => buildTreeNodes(item, String(index), jsonPath))
      }
    }
    const keys = Object.keys(value)
    return {
      id,
      keyLabel,
      label: keyLabel ?? '{}',
      nodeType: 'object',
      childCount: keys.length,
      value,
      jsonPath,
      children: keys.map((key) => buildTreeNodes(value[key], key, jsonPath))
    }
  }

  let valueType = 'string'
  if (value === null) valueType = 'null'
  else if (typeof value === 'number') valueType = 'number'
  else if (typeof value === 'boolean') valueType = 'boolean'

  return {
    id,
    keyLabel,
    label: keyLabel ?? String(value),
    nodeType: 'leaf',
    valueType,
    value,
    jsonPath,
    children: undefined
  }
}

const treeData = computed(() => {
  if (!isJsonResponse.value) return []
  nodeIdSeed = 0
  const root = responseJson.value
  if (root !== null && typeof root === 'object' && !Array.isArray(root)) {
    return Object.keys(root).map((key) => buildTreeNodes(root[key], key))
  }
  return [buildTreeNodes(root, undefined)]
})

const collectExpandableIds = (nodes, acc = []) => {
  ;(nodes || []).forEach((node) => {
    if (node.children?.length) {
      acc.push(node.id)
      collectExpandableIds(node.children, acc)
    }
  })
  return acc
}

const nodeMatchesSearch = (node, keyword) => {
  if (!keyword) return true
  const keyText = String(node.keyLabel ?? '')
  const valueText = node.nodeType === 'leaf' ? String(node.value) : ''
  if (keyText.toLowerCase().includes(keyword) || valueText.toLowerCase().includes(keyword)) {
    return true
  }
  return (node.children || []).some((child) => nodeMatchesSearch(child, keyword))
}

const filterTreeNodes = (nodes, keyword) => {
  if (!keyword) return nodes
  return (nodes || [])
    .map((node) => {
      if (!nodeMatchesSearch(node, keyword)) return null
      if (!node.children?.length) return node
      return {
        ...node,
        children: filterTreeNodes(node.children, keyword)
      }
    })
    .filter(Boolean)
}

const filteredTreeData = computed(() => {
  const keyword = treeSearchKeyword.value.trim().toLowerCase()
  return filterTreeNodes(treeData.value, keyword)
})

const remountTree = (keys = []) => {
  expandedKeys.value = keys
  treeRenderKey.value += 1
}

watch(
  () => [responseJson.value, bodyViewMode.value],
  async () => {
    if (!isJsonResponse.value) {
      bodyViewMode.value = 'raw'
      return
    }
    if (bodyViewMode.value === 'tree') {
      await nextTick()
      remountTree(collectExpandableIds(treeData.value).slice(0, 40))
    }
  },
  { immediate: true }
)

watch(treeSearchKeyword, async () => {
  await nextTick()
  if (treeSearchKeyword.value.trim()) {
    remountTree(collectExpandableIds(filteredTreeData.value))
  }
})

const expandAllTree = () => {
  remountTree(collectExpandableIds(filteredTreeData.value))
}

const collapseAllTree = () => {
  remountTree([])
}

const formatLeafValue = (value) => {
  if (value === null) return 'null'
  if (typeof value === 'string') return JSON.stringify(value)
  return String(value)
}

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('apiTesting.interface.copiedToClipboard') || '已复制到剪贴板')
  } catch (e) {
    ElMessage.error(t('apiTesting.interface.copyFailed') || '复制失败')
  }
}

const copyJsonPathExpression = () => {
  const expr = (jsonPathExpression.value || '').trim()
  if (!expr) {
    ElMessage.warning(t('apiTesting.interface.jsonPathEmpty'))
    return
  }
  copyText(expr)
}

const copyNodeJsonPath = (data) => {
  const expr = (data?.jsonPath || '').trim()
  if (!expr) return
  jsonPathExpression.value = expr
  copyText(expr)
}

const jsonPathResultType = computed(() => {
  if (jsonPathError.value) return 'error'
  const value = jsonPathResultValue.value
  if (value === null) return 'null'
  if (Array.isArray(value)) return 'array'
  return typeof value
})

const jsonPathResultText = computed(() => {
  if (jsonPathError.value) return jsonPathError.value
  const value = jsonPathResultValue.value
  if (typeof value === 'string') return JSON.stringify(value)
  try {
    return JSON.stringify(value, null, 2)
  } catch (e) {
    return String(value)
  }
})

const runJsonPathQuery = () => {
  jsonPathQueried.value = true
  jsonPathResultExpanded.value = true
  jsonPathError.value = ''
  jsonPathResultValue.value = null

  if (!isJsonResponse.value) {
    jsonPathError.value = t('apiTesting.interface.jsonPathNeedJson')
    return
  }
  const expr = (jsonPathExpression.value || '').trim()
  if (!expr) {
    jsonPathError.value = t('apiTesting.interface.jsonPathEmpty')
    return
  }

  try {
    const matches = JSONPath({ path: expr, json: responseJson.value })
    if (!Array.isArray(matches) || matches.length === 0) {
      jsonPathResultValue.value = null
      jsonPathError.value = t('apiTesting.interface.jsonPathNoMatch')
      return
    }
    jsonPathResultValue.value = matches.length === 1 ? matches[0] : matches
  } catch (e) {
    jsonPathError.value = e?.message || t('apiTesting.interface.jsonPathInvalid')
  }
}

const headerRows = computed(() => {
  const headers = props.responseData?.headers || {}
  return Object.keys(headers).map((key) => ({
    key,
    value: headers[key]
  }))
})

const filteredHeaders = computed(() => {
  const keyword = headerSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return headerRows.value
  return headerRows.value.filter(
    (row) =>
      String(row.key).toLowerCase().includes(keyword) ||
      String(row.value).toLowerCase().includes(keyword)
  )
})

const headersTabLabel = computed(() => {
  const count = headerRows.value.length
  return count > 0 ? `Headers (${count})` : 'Headers'
})

watch(
  () => props.responseData,
  () => {
    jsonPathQueried.value = false
    jsonPathError.value = ''
    jsonPathResultValue.value = null
    treeSearchKeyword.value = ''
    headerSearchKeyword.value = ''
    if (isJsonResponse.value) {
      bodyViewMode.value = 'tree'
    } else {
      bodyViewMode.value = 'raw'
    }
  }
)
</script>

<style scoped>
.response-viewer {
  padding: 0 8px 12px;
}

.body-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.view-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: #909399;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.toggle-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.toggle-btn.active {
  color: #5046e5;
  font-weight: 600;
}

.toggle-btn:not(:disabled):hover {
  background: #f5f7fa;
}

.jsonpath-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 260px;
}

.jsonpath-bar .el-input {
  flex: 0 1 50%;
  width: 50%;
  max-width: 50%;
}

.help-icon {
  color: #909399;
  cursor: help;
  font-size: 16px;
}

.copy-btn {
  flex-shrink: 0;
}

.jsonpath-result-panel {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  margin-bottom: 12px;
  overflow: hidden;
}

.jsonpath-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fafafa;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
}

.type-tag {
  margin-left: 8px;
}

.expand-icon {
  transition: transform 0.2s ease;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.jsonpath-result-body {
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
  background: #fcfcfc;
}

.jsonpath-result-body.error {
  color: #f56c6c;
}

.jsonpath-result-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  color: #303133;
}

.json-tree-panel {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  min-height: 280px;
  max-height: 520px;
  overflow: auto;
}

.json-tree-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.json-tree-toolbar .el-input {
  flex: 1;
}

.json-tree {
  background: transparent;
}

.json-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 28px;
  align-items: center;
}

.json-tree-node-content {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  min-width: 0;
  padding-right: 8px;
}

.json-key {
  color: #92278f;
}

.json-colon {
  color: #909399;
}

.json-meta {
  color: #909399;
}

.json-value.string {
  color: #3ab54a;
}

.json-value.number {
  color: #25aae2;
}

.json-value.boolean {
  color: #f98280;
}

.json-value.null {
  color: #aaa;
}

.node-copy {
  margin-left: 6px;
  color: #c0c4cc;
  cursor: pointer;
  font-size: 13px;
  flex-shrink: 0;
}

.node-copy:hover {
  color: #5046e5;
}

.raw-panel {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  min-height: 280px;
  max-height: 520px;
  overflow: auto;
}

.raw-content {
  margin: 0;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
}

.raw-content :deep(.tok-key) {
  color: #92278f;
}

.raw-content :deep(.tok-string) {
  color: #3ab54a;
}

.raw-content :deep(.tok-literal) {
  color: #f98280;
}

.raw-content :deep(.tok-number) {
  color: #25aae2;
}

.response-headers-panel {
  padding: 4px 8px 12px;
}

.headers-search {
  margin-bottom: 12px;
}

.headers-table {
  width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.headers-table :deep(.el-table__header th) {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

.headers-table :deep(.el-table__row td) {
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}
</style>
