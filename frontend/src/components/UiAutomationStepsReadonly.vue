<template>
  <div class="readonly-steps">
    <div class="steps-toolbar">
      <div class="steps-toolbar-left">
        <h4>{{ t('uiAutomation.testCase.testSteps') }}</h4>
        <button type="button" class="expand-all-btn" @click.stop="toggleAllSteps">
          <span>{{ allStepsExpanded ? t('uiAutomation.testCase.foldAll') : t('uiAutomation.testCase.expandAll') }}</span>
          <el-icon>
            <component :is="allStepsExpanded ? ArrowUp : ArrowDown" />
          </el-icon>
        </button>
      </div>
      <div class="steps-toolbar-right">
        <slot name="actions" />
      </div>
    </div>
    <div class="steps-list">
      <div
        v-for="(step, index) in steps"
        :key="step.id ?? step.step_number ?? index"
        class="step-item"
        :class="{ expanded: stepExpanded[index] }"
      >
        <div class="step-header" @click="toggleStep(index)">
          <div class="step-desc-row">
            <el-icon class="drag-handle"><Rank /></el-icon>
            <span class="step-number">{{ index + 1 }}</span>
            <div class="step-desc-sizer">
              <span class="step-desc-mirror">{{ step.description || ' ' }}</span>
              <el-input
                :model-value="step.description || ''"
                size="small"
                class="step-desc-input"
                readonly
                @click.stop
              />
            </div>
          </div>
          <span class="step-right">
            <el-icon><component :is="stepExpanded[index] ? ArrowUp : ArrowDown" /></el-icon>
          </span>
        </div>

        <div v-if="stepExpanded[index]" class="step-content">
          <div class="step-action-row">
            <el-select :model-value="step.action_type" size="small" style="width: 120px" disabled>
              <el-option
                v-for="opt in actionTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-select
              v-if="needsElement(step.action_type)"
              :model-value="step.page_filter || ''"
              size="small"
              style="width: 150px"
              disabled
            >
              <el-option
                v-if="step.page_filter"
                :label="step.page_filter"
                :value="step.page_filter"
              />
            </el-select>
            <el-select
              v-if="needsElement(step.action_type)"
              :model-value="elementSelectValue(step)"
              size="small"
              style="width: 220px"
              disabled
            >
              <el-option
                v-if="elementSelectValue(step)"
                :label="formatElementLabel(step)"
                :value="elementSelectValue(step)"
              />
            </el-select>
            <el-button
              v-if="needsElement(step.action_type)"
              size="small"
              type="primary"
              plain
              class="pick-btn"
              disabled
            >
              {{ t('uiAutomation.testCase.pickElement') }}
            </el-button>
          </div>

          <template v-if="needsElement(step.action_type) && (step.element || step.element_id)">
            <div class="step-param step-element-shot">
              <label>{{ t('uiAutomation.testCase.elementScreenshot') }}</label>
              <div class="element-shot-box">
                <el-image
                  v-if="step.element?.screenshot"
                  :src="resolveMediaUrl(step.element.screenshot)"
                  fit="contain"
                  :preview-src-list="[resolveMediaUrl(step.element.screenshot)]"
                  class="element-shot-img"
                >
                  <template #error>
                    <span class="element-shot-empty">{{ t('uiAutomation.testCase.noElementScreenshot') }}</span>
                  </template>
                </el-image>
                <span v-else class="element-shot-empty">{{ t('uiAutomation.testCase.noElementScreenshot') }}</span>
              </div>
            </div>

            <div class="step-param">
              <label>{{ t('uiAutomation.testCase.waitTimeout') }}</label>
              <el-input-number
                :model-value="step.element?.wait_timeout ?? 5"
                :min="1"
                :max="60"
                size="small"
                disabled
              />
            </div>

            <div class="step-param step-locator-row">
              <label>{{ t('uiAutomation.testCase.selector') }}</label>
              <div class="locator-editor">
                <el-select
                  :model-value="step.element?.locator_strategy || ''"
                  size="small"
                  style="width: 110px"
                  disabled
                >
                  <el-option
                    v-if="step.element?.locator_strategy"
                    :label="step.element.locator_strategy"
                    :value="step.element.locator_strategy"
                  />
                </el-select>
                <el-input
                  :model-value="step.element?.locator_value || ''"
                  size="small"
                  disabled
                />
              </div>
            </div>

            <div class="step-param step-backup-block">
              <label>{{ t('uiAutomation.testCase.backupSelectors') }}</label>
              <div class="backup-list">
                <div
                  v-for="(backup, bIdx) in (step.element?.backup_locators || [])"
                  :key="bIdx"
                  class="locator-editor backup-row"
                >
                  <el-select
                    :model-value="backup.strategy || ''"
                    size="small"
                    style="width: 110px"
                    disabled
                  >
                    <el-option
                      v-if="backup.strategy"
                      :label="backup.strategy"
                      :value="backup.strategy"
                    />
                  </el-select>
                  <el-input :model-value="backup.value || ''" size="small" disabled />
                </div>
                <el-button
                  v-if="!(step.element?.backup_locators || []).length"
                  type="primary"
                  size="small"
                  class="add-backup-btn"
                  disabled
                >
                  + {{ t('uiAutomation.testCase.addBackupSelector') }}
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="needsInputValue(step.action_type)" class="step-param">
            <label>{{ step.action_type === 'fill' ? t('uiAutomation.testCase.textValue') : t('uiAutomation.testCase.inputValue') }}</label>
            <el-input :model-value="step.input_value || ''" size="small" disabled />
          </div>

          <div v-if="needsWaitTime(step.action_type)" class="step-param">
            <label>{{ t('uiAutomation.testCase.waitTime') }}</label>
            <el-input-number
              :model-value="step.wait_time ?? 1000"
              :min="100"
              :max="30000"
              :step="100"
              size="small"
              disabled
            />
          </div>

          <div v-if="step.action_type === 'assert'" class="step-param">
            <label>{{ t('uiAutomation.testCase.assertType') }}</label>
            <el-select :model-value="step.assert_type || ''" size="small" style="width: 150px" disabled>
              <el-option
                v-for="opt in assertTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-input
              :model-value="step.assert_value || ''"
              size="small"
              style="flex: 1; margin-left: 10px; max-width: 240px"
              disabled
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUp, ArrowDown, Rank } from '@element-plus/icons-vue'

const props = defineProps({
  steps: {
    type: Array,
    default: () => []
  }
})

const { t } = useI18n()

/** 按索引记录展开态；用数组避免 object 键类型导致的误判 */
const stepExpanded = ref([])

const stepsIdentity = (steps) =>
  (steps || []).map((s, i) => String(s?.id ?? s?.step_number ?? `i${i}`)).join('|')

/**
 * 仅在步骤集合变化（换用例 / 增删步骤）时重置展开态。
 * 同一批步骤被父组件重新赋值（如 AI 回显轮询刷新）时保留展开，避免「展开全部」后立刻收起。
 */
watch(
  () => stepsIdentity(props.steps),
  (nextId, prevId) => {
    if (nextId === prevId) return
    stepExpanded.value = (props.steps || []).map(() => false)
  },
  { immediate: true }
)

const allStepsExpanded = computed(() => {
  const steps = props.steps || []
  return (
    steps.length > 0 &&
    stepExpanded.value.length === steps.length &&
    stepExpanded.value.every(Boolean)
  )
})

const toggleStep = (index) => {
  const next = stepExpanded.value.slice()
  next[index] = !next[index]
  stepExpanded.value = next
}

const toggleAllSteps = () => {
  const target = !allStepsExpanded.value
  stepExpanded.value = (props.steps || []).map(() => target)
}

const actionTypeOptions = computed(() => [
  { label: t('uiAutomation.testCase.actionClick'), value: 'click' },
  { label: t('uiAutomation.testCase.actionFill'), value: 'fill' },
  { label: t('uiAutomation.testCase.actionGetText'), value: 'getText' },
  { label: t('uiAutomation.testCase.actionWaitFor'), value: 'waitFor' },
  { label: t('uiAutomation.testCase.actionHover'), value: 'hover' },
  { label: t('uiAutomation.testCase.actionScroll'), value: 'scroll' },
  { label: t('uiAutomation.testCase.actionScreenshot'), value: 'screenshot' },
  { label: t('uiAutomation.testCase.actionAssert'), value: 'assert' },
  { label: t('uiAutomation.testCase.actionWait'), value: 'wait' },
  { label: t('uiAutomation.testCase.actionSwitchTab'), value: 'switchTab' },
  { label: t('uiAutomation.testCase.actionNavigateUrl'), value: 'navigateUrl' },
])

const assertTypeOptions = computed(() => [
  { label: t('uiAutomation.testCase.assertTextContains'), value: 'textContains' },
  { label: t('uiAutomation.testCase.assertTextEquals'), value: 'textEquals' },
  { label: t('uiAutomation.testCase.assertIsVisible'), value: 'isVisible' },
  { label: t('uiAutomation.testCase.assertExists'), value: 'exists' },
  { label: t('uiAutomation.testCase.assertHasAttribute'), value: 'hasAttribute' },
  { label: t('uiAutomation.testCase.assertUrlContains'), value: 'urlContains' },
])

const needsElement = (actionType) => !['wait', 'switchTab', 'screenshot', 'navigateUrl'].includes(actionType)
const needsInputValue = (actionType) => ['fill', 'switchTab', 'navigateUrl'].includes(actionType)
const needsWaitTime = (actionType) => ['wait', 'waitFor'].includes(actionType)

const elementSelectValue = (step) => step.element?.id ?? step.element_id ?? ''

const formatElementLabel = (step) => {
  const el = step.element
  if (!el) return ''
  const strategy = el.locator_strategy || ''
  const expr = el.locator_value || ''
  if (strategy && expr) return `${el.name} (${strategy}: ${expr})`
  if (expr) return `${el.name} (${expr})`
  return el.name || String(el.id || '')
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
</script>

<style scoped lang="scss">
.readonly-steps {
  margin-top: 0;

  .steps-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
  }

  .steps-toolbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    height: 22px;

    h4 {
      margin: 0;
      padding: 0;
      font-size: 14px;
      font-weight: 600;
      color: #303133;
      line-height: 22px;
      height: 22px;
      white-space: nowrap;
      display: inline-flex;
      align-items: center;
    }
  }

  .expand-all-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    margin: 0;
    padding: 0;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 10px;
    font-weight: 400;
    line-height: 1;
    height: 22px;
    color: #606266;
    white-space: nowrap;
    vertical-align: middle;

    .el-icon {
      font-size: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    &:hover {
      color: #409eff;
    }
  }

  .steps-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .step-item {
    border: 1px solid #e6e6e6;
    border-radius: 6px;
    margin-bottom: 10px;
    background: white;
    transition: all 0.3s;
  }

  .step-item:hover {
    border-color: #409eff;
  }

  .step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 15px;
    background: #fafafa;
    border-radius: 6px;
    gap: 8px;
    cursor: pointer;
  }

  .step-item.expanded .step-header {
    border-radius: 6px 6px 0 0;
  }

  .step-desc-row {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex: 1;
  }

  .drag-handle {
    color: #999;
    cursor: default;
    flex-shrink: 0;
  }

  .step-number {
    background: #409eff;
    color: white;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    flex-shrink: 0;
  }

  .step-desc-sizer {
    position: relative;
    display: inline-grid;
    align-items: center;
    max-width: 100%;
    min-width: 4em;
  }

  .step-desc-sizer > * {
    grid-area: 1 / 1;
  }

  .step-desc-mirror {
    visibility: hidden;
    white-space: pre;
    font-size: 14px;
    font-weight: 500;
    line-height: 24px;
    padding: 1px 11px;
    box-sizing: border-box;
    pointer-events: none;
    overflow: hidden;
  }

  .step-desc-input {
    width: 100%;
    min-width: 0;
  }

  .step-desc-input :deep(.el-input__wrapper) {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 0 0 1px #dcdfe6 inset;
    padding-left: 11px;
    padding-right: 11px;
    width: 100%;
  }

  .step-desc-input :deep(.el-input__inner) {
    font-size: 14px;
    font-weight: 500;
    color: #000 !important;
    -webkit-text-fill-color: #000;
    cursor: default;
    width: 100%;
  }

  .step-right {
    display: flex;
    align-items: center;
    gap: 5px;
    color: #909399;
    flex-shrink: 0;
  }

  .step-content {
    padding: 15px;
    border-top: 1px solid #e6e6e6;
  }

  .step-action-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }

  .pick-btn {
    --el-button-bg-color: #7c3aed;
    --el-button-border-color: #7c3aed;
    --el-button-text-color: #fff;
    --el-button-disabled-bg-color: #7c3aed;
    --el-button-disabled-border-color: #7c3aed;
    --el-button-disabled-text-color: #fff;
    opacity: 0.85;
  }

  .step-param {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    gap: 10px;

    &:last-child {
      margin-bottom: 0;
    }

    label {
      width: 120px;
      flex-shrink: 0;
      font-weight: 500;
      color: #333;
      line-height: 24px;
    }
  }

  .step-element-shot,
  .step-backup-block {
    align-items: flex-start;
  }

  .element-shot-box {
    width: 72px;
    height: 72px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    overflow: hidden;
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .element-shot-img {
    width: 72px;
    height: 72px;
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
    flex: 1;
    min-width: 0;
  }

  .locator-editor .el-input {
    flex: 1;
  }

  .backup-list {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .backup-row {
    width: 100%;
  }

  .add-backup-btn {
    align-self: flex-start;
    width: auto;
    --el-button-bg-color: #7c3aed;
    --el-button-border-color: #7c3aed;
    --el-button-text-color: #fff;
    --el-button-disabled-bg-color: #7c3aed;
    --el-button-disabled-border-color: #7c3aed;
    --el-button-disabled-text-color: #fff;
    opacity: 0.85;
  }

  /* 只读表单文字保持黑色，避免 disabled 发灰 */
  :deep(.el-input.is-disabled .el-input__inner),
  :deep(.el-select__wrapper.is-disabled .el-select__selected-item),
  :deep(.el-input-number.is-disabled .el-input__inner) {
    color: #000 !important;
    -webkit-text-fill-color: #000;
  }
}
</style>
