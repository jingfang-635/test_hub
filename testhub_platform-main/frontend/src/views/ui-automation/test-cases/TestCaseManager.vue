<template>
  <div class="test-case-manager">
    <div class="page-header">
      <h1 class="page-title">{{ t('uiAutomation.testCase.title') }}</h1>
      <div class="header-actions">
        <el-select v-model="projectId" :placeholder="t('uiAutomation.common.selectProject')" style="width: 200px; margin-right: 15px" @change="onProjectChange">
          <el-option :label="t('uiAutomation.common.allProjects')" value="all" />
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          {{ t('uiAutomation.testCase.newTestCase') }}
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧：测试用例列表（拾取投屏时自动收起） -->
      <div class="left-panel" :class="{ collapsed: leftPanelCollapsed }">
        <div v-if="leftPanelCollapsed" class="left-panel-collapsed">
          <el-button
            text
            class="left-expand-btn"
            :title="t('uiAutomation.testCase.expandCaseList')"
            @click="leftPanelCollapsed = false"
          >
            <el-icon :size="18"><DArrowRight /></el-icon>
          </el-button>
        </div>
        <template v-else>
          <div class="panel-header">
            <h3>{{ t('uiAutomation.testCase.testCaseList') }}</h3>
            <div class="panel-header-right">
              <el-input
                v-model="searchKeyword"
                :placeholder="t('uiAutomation.testCase.searchPlaceholder')"
                clearable
                size="small"
                style="width: 160px"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-button
                v-if="pickerVisible"
                text
                size="small"
                :title="t('uiAutomation.testCase.collapseCaseList')"
                @click="leftPanelCollapsed = true"
              >
                <el-icon><DArrowLeft /></el-icon>
              </el-button>
            </div>
          </div>

          <div class="test-case-list">
            <div
              v-for="testCase in filteredTestCases"
              :key="testCase.id"
              class="test-case-item"
              :class="{ active: selectedTestCase?.id === testCase.id }"
              @click="selectTestCase(testCase)"
            >
              <div class="case-header">
                <h4 class="case-name">{{ testCase.name }}</h4>
                <div class="case-actions">
                  <el-button size="small" text @click.stop="openRunDialog(testCase)">
                    <el-icon><CaretRight /></el-icon>
                  </el-button>
                  <el-button size="small" text @click.stop="editTestCase(testCase)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button size="small" text @click.stop="copyTestCase(testCase)">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                  <el-button size="small" text type="danger" @click.stop="deleteTestCase(testCase)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <p class="case-description">{{ testCase.description || t('uiAutomation.testCase.noDescription') }}</p>
              <div class="case-meta">
                <span class="step-count">{{ testCase.steps?.length || 0 }} {{ t('uiAutomation.testCase.stepsCount') }}</span>
                <span class="create-time">{{ formatTime(testCase.created_at || testCase.updated_at) }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 右侧：测试用例详情和步骤编辑 -->
      <div class="right-panel">
        <div v-if="selectedTestCase" class="test-case-detail">
          <div class="detail-header">
            <h3>{{ selectedTestCase.name }}</h3>
            <div class="detail-actions">
              <el-button
                size="small"
                type="primary"
                plain
                :loading="pickerStarting && !pickTargetStep"
                @click="openScreencast"
              >
                <el-icon><Monitor /></el-icon>
                {{ t('uiAutomation.testCase.screencast') }}
              </el-button>
              <el-button size="small" @click="addStep">
                <el-icon><Plus /></el-icon>
                {{ t('uiAutomation.testCase.addStep') }}
              </el-button>
              <el-button size="small" type="warning" @click="openRecordStepsDialog">
                <el-icon><VideoCamera /></el-icon>
                {{ t('uiAutomation.testCase.recordSteps') }}
              </el-button>
              <el-button size="small" type="primary" @click="saveTestCase">
                <el-icon><Check /></el-icon>
                {{ t('uiAutomation.testCase.saveTestCase') }}
              </el-button>
              <el-button size="small" type="success" @click="openRunDialog(selectedTestCase)" :loading="isRunning">
                <el-icon v-if="!isRunning"><CaretRight /></el-icon>
                {{ isRunning ? t('uiAutomation.testCase.running') : t('uiAutomation.testCase.runLabel') }}
              </el-button>
            </div>
          </div>

          <!-- 测试步骤编辑 -->
          <div class="steps-container">
            <div class="steps-header">
              <h4>{{ t('uiAutomation.testCase.testSteps') }}</h4>
              <el-button size="small" text @click="expandAllSteps">
                {{ allStepsExpanded ? t('uiAutomation.testCase.foldAll') : t('uiAutomation.testCase.expandAll') }}
              </el-button>
            </div>

            <div class="steps-scroll-container">
              <div class="steps-list">
                <draggable
                  v-model="currentSteps"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onStepsReorder"
                >
                  <template #item="{ element, index }">
                    <div class="step-item" :class="{ expanded: element.expanded }">
                      <div class="step-header" @click="onStepHeaderClick(element)">
                        <div class="step-desc-row">
                          <el-icon class="drag-handle" @click.stop><Rank /></el-icon>
                          <span class="step-number">{{ index + 1 }}</span>
                          <div class="step-desc-sizer">
                            <span class="step-desc-mirror">{{ element.description || t('uiAutomation.testCase.stepDescPlaceholder') }}</span>
                            <el-input
                              v-model="element.description"
                              :placeholder="t('uiAutomation.testCase.stepDescPlaceholder')"
                              size="small"
                              class="step-desc-input"
                              @click.stop
                            />
                          </div>
                        </div>
                        <div class="step-right" @click.stop>
                          <el-button
                            size="small"
                            text
                            @click="onStepHeaderClick(element)"
                          >
                            <el-icon>
                              <component :is="element.expanded ? 'ArrowUp' : 'ArrowDown'" />
                            </el-icon>
                          </el-button>
                          <el-button size="small" text type="danger" @click="removeStep(index)">
                            <el-icon><Delete /></el-icon>
                          </el-button>
                        </div>
                      </div>

                      <div v-if="element.expanded" class="step-content">
                        <!-- 操作栏 -->
                        <div class="step-action-row">
                          <el-select
                            v-model="element.action_type"
                            :placeholder="t('uiAutomation.testCase.selectAction')"
                            size="small"
                            style="width: 120px"
                            @change="onActionTypeChange(element)"
                          >
                            <el-option :label="t('uiAutomation.testCase.actionClick')" value="click" />
                            <el-option :label="t('uiAutomation.testCase.actionFill')" value="fill" />
                            <el-option :label="t('uiAutomation.testCase.actionGetText')" value="getText" />
                            <el-option :label="t('uiAutomation.testCase.actionWaitFor')" value="waitFor" />
                            <el-option :label="t('uiAutomation.testCase.actionHover')" value="hover" />
                            <el-option :label="t('uiAutomation.testCase.actionScroll')" value="scroll" />
                            <el-option :label="t('uiAutomation.testCase.actionScreenshot')" value="screenshot" />
                            <el-option :label="t('uiAutomation.testCase.actionAssert')" value="assert" />
                            <el-option :label="t('uiAutomation.testCase.actionWait')" value="wait" />
                            <el-option :label="t('uiAutomation.testCase.actionSwitchTab')" value="switchTab" />
                            <el-option :label="t('uiAutomation.testCase.actionNavigateUrl')" value="navigateUrl" />
                          </el-select>
                          <el-select
                            v-if="needsElement(element.action_type)"
                            v-model="element.page_filter"
                            :placeholder="t('uiAutomation.testCase.selectPage')"
                            size="small"
                            style="width: 150px"
                            filterable
                            @change="onPageFilterChange(element)"
                          >
                            <el-option
                              v-for="page in distinctPages"
                              :key="page"
                              :label="page"
                              :value="page"
                            />
                          </el-select>
                          <el-select
                            v-if="needsElement(element.action_type)"
                            v-model="element.element_id"
                            :placeholder="t('uiAutomation.testCase.selectElement')"
                            size="small"
                            style="width: 220px"
                            filterable
                            @change="onElementChange(element)"
                          >
                            <el-option
                              v-for="elem in getFilteredElements(element)"
                              :key="elem.id"
                              :label="formatElementOptionLabel(elem)"
                              :value="elem.id"
                            />
                          </el-select>
                          <el-button
                            v-if="needsElement(element.action_type)"
                            size="small"
                            type="primary"
                            plain
                            :loading="pickerStarting && pickTargetStep === element"
                            @click.stop="startPickElement(element)"
                          >
                            {{ t('uiAutomation.testCase.pickElement') }}
                          </el-button>
                        </div>

                        <!-- 控件截图 + 选择器 + 备用选择器 -->
                        <template v-if="needsElement(element.action_type) && (element.element_id || element.element_locator)">
                          <div class="step-param step-element-shot">
                            <label>{{ t('uiAutomation.testCase.elementScreenshot') }}</label>
                            <div class="element-shot-box">
                              <el-image
                                v-if="element.element_screenshot"
                                :src="resolveMediaUrl(element.element_screenshot)"
                                fit="contain"
                                :preview-src-list="[resolveMediaUrl(element.element_screenshot)]"
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
                              v-model="element.wait_timeout"
                              :min="1"
                              :max="60"
                              size="small"
                              @change="onStepWaitTimeoutChange(element)"
                            />
                          </div>

                          <div class="step-param step-locator-row">
                            <label>{{ t('uiAutomation.testCase.selector') }}</label>
                            <div class="locator-editor">
                              <el-select
                                v-model="element.element_locator_strategy"
                                size="small"
                                style="width: 110px"
                                filterable
                                allow-create
                                @change="onStepLocatorChange(element)"
                              >
                                <el-option
                                  v-for="s in locatorStrategies"
                                  :key="s.id"
                                  :label="s.name"
                                  :value="s.name"
                                />
                              </el-select>
                              <el-input
                                v-model="element.element_locator"
                                size="small"
                                :placeholder="t('uiAutomation.testCase.locatorExpressionPlaceholder')"
                                @change="onStepLocatorChange(element)"
                              />
                            </div>
                          </div>

                          <div class="step-param step-backup-block">
                            <label>{{ t('uiAutomation.testCase.backupSelectors') }}</label>
                            <div class="backup-list">
                              <div
                                v-for="(backup, bIdx) in (element.element_backup_locators || [])"
                                :key="bIdx"
                                class="locator-editor backup-row"
                              >
                                <el-select
                                  v-model="backup.strategy"
                                  size="small"
                                  style="width: 110px"
                                  filterable
                                  allow-create
                                  @change="onStepLocatorChange(element)"
                                >
                                  <el-option
                                    v-for="s in locatorStrategies"
                                    :key="s.id"
                                    :label="s.name"
                                    :value="s.name"
                                  />
                                </el-select>
                                <el-input
                                  v-model="backup.value"
                                  size="small"
                                  @change="onStepLocatorChange(element)"
                                />
                                <el-button
                                  size="small"
                                  text
                                  type="danger"
                                  @click="removeBackupLocator(element, bIdx)"
                                >
                                  <el-icon><Delete /></el-icon>
                                </el-button>
                              </div>
                              <el-button
                                type="primary"
                                size="small"
                                class="add-backup-btn"
                                @click="addBackupLocatorRow(element)"
                              >
                                + {{ t('uiAutomation.testCase.addBackupSelector') }}
                              </el-button>
                            </div>
                          </div>
                        </template>

                        <!-- 输入参数 -->
                        <div v-if="needsInputValue(element.action_type)" class="step-param">
                          <label>{{ element.action_type === 'fill' ? t('uiAutomation.testCase.textValue') : t('uiAutomation.testCase.inputValue') }}</label>
                          <div style="display: flex; gap: 5px; flex: 1">
                            <el-input
                              v-model="element.input_value"
                              :placeholder="element.action_type === 'switchTab' ? t('uiAutomation.testCase.switchTabPlaceholder') : (element.action_type === 'navigateUrl' ? t('uiAutomation.testCase.navigateUrlPlaceholder') : t('uiAutomation.testCase.inputPlaceholder'))"
                              size="small"
                            >
                              <template #append>
                                <el-button
                                  size="small"
                                  :icon="MagicStick"
                                  @click="openDataFactorySelector(element, 'input_value')"
                                  :title="t('uiAutomation.testCase.referenceDataFactory')"
                                  class="data-factory-btn"
                                />
                              </template>
                            </el-input>
                            <el-tooltip :content="t('uiAutomation.testCase.insertVariable')" placement="top" v-if="element.action_type !== 'switchTab'">
                              <el-button size="small" @click="openVariableHelper(element, 'input_value')" class="variable-helper-btn">
                                <el-icon><MagicStick /></el-icon>
                              </el-button>
                            </el-tooltip>
                          </div>
                        </div>

                        <!-- 等待时间 -->
                        <div v-if="needsWaitTime(element.action_type)" class="step-param">
                          <label>{{ t('uiAutomation.testCase.waitTime') }}</label>
                          <el-input-number
                            v-model="element.wait_time"
                            :min="100"
                            :max="30000"
                            :step="100"
                            size="small"
                          />
                        </div>

                        <!-- 断言参数 -->
                        <div v-if="element.action_type === 'assert'" class="step-param">
                          <label>{{ t('uiAutomation.testCase.assertType') }}</label>
                          <el-select v-model="element.assert_type" size="small" style="width: 150px">
                            <el-option :label="t('uiAutomation.testCase.assertTextContains')" value="textContains" />
                            <el-option :label="t('uiAutomation.testCase.assertTextEquals')" value="textEquals" />
                            <el-option :label="t('uiAutomation.testCase.assertIsVisible')" value="isVisible" />
                            <el-option :label="t('uiAutomation.testCase.assertExists')" value="exists" />
                            <el-option :label="t('uiAutomation.testCase.assertHasAttribute')" value="hasAttribute" />
                            <el-option :label="t('uiAutomation.testCase.assertUrlContains')" value="urlContains" />
                          </el-select>
                          <div style="display: flex; align-items: center; margin-left: 10px; width: 240px">
                            <el-input
                              v-model="element.assert_value"
                              :placeholder="t('uiAutomation.testCase.expectedValue')"
                              size="small"
                              style="flex: 1"
                            >
                              <template #append>
                                <el-button
                                  size="small"
                                  :icon="MagicStick"
                                  @click="openDataFactorySelector(element, 'assert_value')"
                                  :title="t('uiAutomation.testCase.referenceDataFactory')"
                                  class="data-factory-btn"
                                />
                              </template>
                            </el-input>
                            <el-tooltip :content="t('uiAutomation.testCase.insertVariable')" placement="top">
                              <el-button size="small" style="margin-left: 5px" @click="openVariableHelper(element, 'assert_value')" class="variable-helper-btn">
                                <el-icon><MagicStick /></el-icon>
                              </el-button>
                            </el-tooltip>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
                </draggable>
              </div>
            </div>
          </div>

        </div>

        <div v-else class="no-selection">
          <el-empty :description="t('uiAutomation.testCase.selectTestCase')" />
        </div>
      </div>

      <!-- 右侧：执行结果 -->
      <div v-if="executionResult" class="result-side-panel">
        <div class="result-side-header">
          <div class="result-side-title-row">
            <h3>{{ t('uiAutomation.testCase.executionResult') }}</h3>
            <el-tag
              v-if="executionResult.healed || executionPassedWithHeal"
              type="warning"
              size="small"
              effect="light"
            >
              {{ t('uiAutomation.testCase.healedViaAi') }}
            </el-tag>
            <el-tag
              v-else
              :type="executionResult.success ? 'success' : 'danger'"
              size="small"
              effect="light"
            >
              {{ executionResult.success ? t('uiAutomation.testCase.executionSuccess') : t('uiAutomation.testCase.executionFailed') }}
            </el-tag>
          </div>
          <div class="result-side-actions">
            <el-button type="warning" size="small" :loading="isRunning" @click="openRunDialog(selectedTestCase)">
              <el-icon v-if="!isRunning"><RefreshRight /></el-icon>
              {{ t('uiAutomation.testCase.rerun') }}
            </el-button>
            <el-button text size="small" class="result-close-btn" @click="closeExecutionResult">
              <el-icon :size="16"><Close /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="result-side-body">
          <div
            v-if="executionResult.healed || executionPassedWithHeal"
            class="result-heal-banner"
          >
            <div class="result-heal-title">{{ t('uiAutomation.testCase.healedViaAi') }}</div>
            <div
              v-for="(item, idx) in healedStepSummaries"
              :key="idx"
              class="result-heal-item"
            >
              <span class="result-heal-step">
                {{ t('uiAutomation.testCase.step') }} {{ item.step_number }}
              </span>
              <span class="result-heal-reason">
                {{ t('uiAutomation.testCase.aiFailureReason') }}：{{ item.healing_reason || '-' }}
              </span>
            </div>
          </div>

          <div class="result-side-section-title">{{ t('uiAutomation.testCase.executionLogs') }}</div>
          <div class="result-side-logs">
            <template v-if="parsedExecutionLogs.length > 0">
              <div
                v-for="(step, index) in parsedExecutionLogs"
                :key="index"
                class="result-log-card"
                :class="{
                  success: step.success !== false && !step.healed,
                  failed: step.success === false,
                  healed: !!step.healed
                }"
              >
                <span
                  class="result-log-step"
                  :class="{ failed: step.success === false, healed: !!step.healed }"
                >
                  {{ t('uiAutomation.testCase.step') }} {{ step.step_number ?? index + 1 }}
                </span>
                <el-tag v-if="step.healed" type="warning" size="small" effect="plain">
                  {{ t('uiAutomation.testCase.aiHealedStep') }}
                </el-tag>
                <span class="result-log-desc">{{ step.description || step.message || '' }}</span>
                <div v-if="step.healed && step.healing_reason" class="result-log-heal">
                  <div class="result-log-heal-label">{{ t('uiAutomation.testCase.aiFailureReason') }}</div>
                  <pre>{{ step.healing_reason }}</pre>
                  <div
                    v-if="step.healed_locator"
                    class="result-log-heal-locator"
                  >
                    {{ t('uiAutomation.testCase.aiTempLocator') }}：
                    {{ step.healed_locator.strategy }}={{ step.healed_locator.value }}
                  </div>
                </div>
                <div v-if="step.error" class="result-log-error">
                  <pre>{{ step.error }}</pre>
                </div>
              </div>
            </template>
            <el-empty v-else :description="t('uiAutomation.testCase.noLogs')" :image-size="64" />
          </div>

          <template v-if="executionResult.screenshots?.length">
            <div class="result-side-section-title">{{ t('uiAutomation.testCase.failedScreenshots') }}</div>
            <div class="result-side-screenshots">
              <div
                v-for="(screenshot, index) in executionResult.screenshots"
                :key="index"
                class="result-shot-item"
                @click="previewScreenshot(screenshot)"
              >
                <img :src="screenshot.url" :alt="`${t('uiAutomation.testCase.screenshot')} ${index + 1}`" />
              </div>
            </div>
          </template>

          <template v-if="executionResult.errors?.length">
            <div class="result-side-section-title">{{ t('uiAutomation.testCase.errorInfo') }}</div>
            <div class="result-side-errors">
              <div v-for="(error, index) in executionResult.errors" :key="index" class="result-error-card">
                <div class="result-error-msg">{{ error.message || error }}</div>
                <div v-if="error.step_number" class="result-error-step">
                  {{ t('uiAutomation.testCase.step') }} {{ error.step_number }}
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 右侧：元素拾取投屏 -->
      <div v-if="pickerVisible" class="picker-side-panel">
        <div class="picker-top-bar">
          <div class="picker-top-bar-left">
            <el-button
              v-if="inspectModeActive"
              type="danger"
              plain
              size="default"
              @click="exitInspectMode"
            >
              {{ t('uiAutomation.testCase.exitInspect') }}
            </el-button>
            <el-button
              v-else
              type="primary"
              plain
              size="default"
              @click="enterInspectMode"
            >
              {{ t('uiAutomation.testCase.enterInspect') }}
            </el-button>
            <el-tag v-if="inspectModeActive" size="small" type="warning" effect="plain">
              {{ t('uiAutomation.testCase.inspectModeOnly') }}
            </el-tag>
          </div>
          <el-button
            text
            size="small"
            class="picker-close-btn"
            :title="t('uiAutomation.testCase.closeScreencast')"
            @click="stopPickElement"
          >
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
        </div>
        <div class="picker-screen-dock">
          <div class="picker-url-row">
            <el-input
              v-model="pickerNavUrl"
              size="small"
              :placeholder="t('uiAutomation.testCase.pickUrlPlaceholder')"
              @keyup.enter="navigatePickerUrl"
            />
            <el-button size="small" :loading="pickerNavigating" @click="navigatePickerUrl">
              {{ t('uiAutomation.testCase.pickGo') }}
            </el-button>
          </div>
          <div
            class="picker-screen-wrap"
            :class="{ 'is-inspect': inspectModeActive }"
            tabindex="0"
            @wheel.prevent="onPickerWheel"
            @keydown="onPickerKeydown"
          >
            <div v-if="pickerStarting || (!pickerScreenshot && pickerSession)" class="picker-screen-loading">
              {{ t('uiAutomation.testCase.pickLoading') }}
            </div>
            <div v-if="pickerScreenshot" class="picker-screen-frame">
              <img
                ref="pickerImgRef"
                :src="pickerScreenshot"
                class="picker-screen-img"
                draggable="false"
                @click="onPickerScreenClick"
                @dblclick="onPickerScreenDblClick"
                @contextmenu.prevent="onPickerScreenContextMenu"
              />
              <div
                v-if="pickerHighlight && inspectModeActive"
                class="picker-highlight"
                :style="pickerHighlightStyle"
              />
            </div>
            <!-- 定位策略浮层 -->
            <div v-if="pickerInspect && inspectModeActive" class="picker-inspect-popup">
              <div class="picker-inspect-head">
                <div>
                  <div class="picker-inspect-tag">&lt;{{ pickerInspect.tag || 'element' }}&gt;</div>
                  <div class="picker-inspect-class">{{ pickerInspect.class_name || '' }}</div>
                </div>
                <el-button text size="small" @click="pickerInspect = null">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
              <el-button
                type="primary"
                class="picker-fill-all-btn"
                @click="fillAllLocators"
              >
                <el-icon><MagicStick /></el-icon>
                {{ t('uiAutomation.testCase.fillAllSmart') }}
              </el-button>
              <div class="picker-locator-list">
                <div
                  v-for="(loc, idx) in sortedPickerLocators"
                  :key="idx"
                  class="picker-locator-row"
                >
                  <div class="picker-locator-meta">
                    <span class="picker-locator-strategy">{{ locatorStrategyLabel(loc.strategy) }}</span>
                    <span class="picker-locator-value" :title="loc.value">{{ loc.value }}</span>
                  </div>
                  <div class="picker-locator-actions">
                    <el-tag
                      size="small"
                      :type="loc.unique ? 'success' : (loc.match_count === 0 ? 'warning' : 'info')"
                      effect="plain"
                    >
                      {{ loc.unique ? t('uiAutomation.testCase.uniqueMatch') : t('uiAutomation.testCase.matchCount', { n: loc.match_count }) }}
                    </el-tag>
                    <el-button text size="small" :title="t('uiAutomation.testCase.copyLocator')" @click="copyLocator(loc)">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                    <el-button text size="small" type="primary" :title="t('uiAutomation.testCase.fillOneLocator')" @click="fillOneLocator(loc)">
                      <el-icon><Download /></el-icon>
                    </el-button>
                  </div>
                </div>
              </div>
              <div class="picker-inspect-tip">{{ t('uiAutomation.testCase.fillAllTip') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建/编辑测试用例对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTestCase ? t('uiAutomation.testCase.editTestCase') : t('uiAutomation.testCase.createTestCase')"
      :close-on-click-modal="false"
      width="500px"
    >
      <el-form :model="testCaseForm" label-width="100px">
        <el-form-item :label="t('uiAutomation.testCase.caseName')" required>
          <el-input v-model="testCaseForm.name" :placeholder="t('uiAutomation.testCase.caseNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.caseDescription')">
          <el-input
            v-model="testCaseForm.description"
            type="textarea"
            :rows="3"
            :placeholder="t('uiAutomation.testCase.caseDescPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.priority')">
          <el-select v-model="testCaseForm.priority" style="width: 100%">
            <el-option :label="t('uiAutomation.testCase.priorityHigh')" value="high" />
            <el-option :label="t('uiAutomation.testCase.priorityMedium')" value="medium" />
            <el-option :label="t('uiAutomation.testCase.priorityLow')" value="low" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">{{ t('uiAutomation.common.cancel') }}</el-button>
          <el-button type="primary" @click="saveTestCaseForm">{{ t('uiAutomation.common.confirm') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 截图预览对话框 -->
    <el-dialog
      v-model="showScreenshotPreview"
      :title="t('uiAutomation.testCase.screenshotPreview')"
      width="80%"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
    >
      <div v-if="currentScreenshot" class="screenshot-preview">
        <div class="preview-info">
          <h4>{{ currentScreenshot.description }}</h4>
          <p v-if="currentScreenshot.step_number">{{ t('uiAutomation.testCase.failedStep') }}: {{ t('uiAutomation.testCase.step') }} {{ currentScreenshot.step_number }}</p>
          <p v-if="currentScreenshot.timestamp">{{ t('uiAutomation.testCase.screenshotTime') }}: {{ formatTime(currentScreenshot.timestamp) }}</p>
        </div>
        <div class="preview-image">
          <img :src="currentScreenshot.url" :alt="currentScreenshot.description" />
        </div>
      </div>
    </el-dialog>

    <!-- 变量助手对话框 -->
    <el-dialog
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      v-model="showVariableHelper"
      :title="t('uiAutomation.testCase.variableHelper')"
      :close-on-click-modal="false"
      width="900px"
    >
      <el-tabs tab-position="left" style="height: 450px">
        <el-tab-pane
          v-for="(category, index) in variableCategoriesComputed"
          :key="index"
          :label="category.label"
        >
          <div style="height: 450px; overflow-y: auto; padding: 10px;">
            <el-table :data="category.variables" style="width: 100%" @row-click="insertVariable" highlight-current-row>
              <el-table-column prop="name" :label="t('uiAutomation.testCase.functionName')" width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tag size="small">{{ row.name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="t('uiAutomation.testCase.description')" min-width="150" />
              <el-table-column prop="syntax" :label="t('uiAutomation.testCase.syntax')" min-width="200" show-overflow-tooltip />
              <el-table-column prop="example" :label="t('uiAutomation.testCase.example')" min-width="200" show-overflow-tooltip />
              <el-table-column :label="t('uiAutomation.testCase.operation')" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small">{{ t('uiAutomation.testCase.insert') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
    
    <DataFactorySelector
      v-model="showDataFactorySelector"
      @select="handleDataFactorySelect"
    />

    <!-- 录制步骤对话框 -->
    <el-dialog
      v-model="showRecordDialog"
      :title="t('uiAutomation.testCase.recordStepsTitle')"
      width="920px"
      :close-on-click-modal="false"
      @closed="onRecordDialogClosed"
    >
      <el-form label-width="100px" class="record-form">
        <el-form-item :label="t('uiAutomation.testCase.recordTargetUrl')" :required="!recordForm.autoLogin">
          <el-input
            v-model="recordForm.targetUrl"
            :placeholder="t('uiAutomation.testCase.recordTargetUrlPlaceholder')"
            :disabled="recordIsRecording"
            clearable
          />
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.recordBrowser')">
          <el-radio-group v-model="recordForm.browser" :disabled="recordIsRecording">
            <el-radio-button value="chromium">Chromium</el-radio-button>
            <el-radio-button value="firefox">Firefox</el-radio-button>
            <el-radio-button value="webkit">WebKit</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.recordAutoLogin')">
          <el-switch
            v-model="recordForm.autoLogin"
            :disabled="recordIsRecording"
          />
          <span class="record-auto-login-hint">
            {{ t('uiAutomation.testCase.recordAutoLoginNoCreds') }}
          </span>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.recordStatus')">
          <el-tag :type="recordStatusTagType">{{ recordStatusText }}</el-tag>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="recordStarting"
            :disabled="recordIsRecording || !recordEnvReady"
            @click="startRecordSteps"
          >
            {{ t('uiAutomation.testCase.recordStart') }}
          </el-button>
          <el-button
            type="danger"
            plain
            :loading="recordStopping"
            :disabled="!recordIsRecording"
            @click="stopRecordSteps"
          >
            {{ t('uiAutomation.testCase.recordStop') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="parsedRecordSteps.length" class="record-preview">
        <div class="record-preview-header">
          <span>{{ t('uiAutomation.testCase.recordPreview', { count: parsedRecordSteps.length }) }}</span>
          <el-radio-group v-model="recordImportMode" size="small">
            <el-radio-button value="append">{{ t('uiAutomation.testCase.recordAppend') }}</el-radio-button>
            <el-radio-button value="replace">{{ t('uiAutomation.testCase.recordReplace') }}</el-radio-button>
          </el-radio-group>
        </div>
        <el-table :data="parsedRecordSteps" size="small" max-height="320" stripe border>
          <el-table-column type="index" width="50" :label="t('uiAutomation.testCase.step')" />
          <el-table-column :label="t('uiAutomation.testCase.elementScreenshot')" width="72" align="center">
            <template #default="{ row }">
              <el-image
                v-if="row.element_screenshot"
                :src="resolveMediaUrl(row.element_screenshot)"
                fit="contain"
                class="record-preview-shot"
                :preview-src-list="[resolveMediaUrl(row.element_screenshot)]"
              />
              <span v-else class="record-preview-shot-empty">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" :label="t('uiAutomation.testCase.description')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="action_type" :label="t('uiAutomation.testCase.selectAction')" width="90">
            <template #default="{ row }">
              {{ getActionTypeText(row.action_type) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('uiAutomation.testCase.selector')" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.element_locator_strategy || row.element_locator">
                <el-tag v-if="row.element_locator_strategy" size="small" type="info" class="strategy-tag">
                  {{ row.element_locator_strategy }}
                </el-tag>
                {{ row.element_locator || '' }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('uiAutomation.testCase.backupSelectors')" width="90" align="center">
            <template #default="{ row }">
              {{ (row.element_backup_locators || []).length || 0 }}
            </template>
          </el-table-column>
          <el-table-column prop="input_value" :label="t('uiAutomation.testCase.inputValue')" min-width="100" show-overflow-tooltip />
        </el-table>
      </div>
      <div v-else-if="recordScriptContent" class="record-script-hint">
        {{ t('uiAutomation.testCase.recordScriptReady') }}
      </div>

      <template #footer>
        <el-button @click="showRecordDialog = false">{{ t('uiAutomation.common.cancel') }}</el-button>
        <el-button
          type="primary"
          :disabled="!parsedRecordSteps.length"
          @click="importRecordedSteps"
        >
          {{ t('uiAutomation.testCase.recordImport') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 运行配置对话框 -->
    <el-dialog
      v-model="showRunDialog"
      :title="t('uiAutomation.testCase.runConfig')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="runConfig" label-width="120px">
        <el-form-item :label="t('uiAutomation.testCase.testEngine')">
          <el-select v-model="runConfig.engine" :placeholder="t('uiAutomation.testCase.testEngine')" style="width: 100%">
            <el-option label="Playwright" value="playwright" />
            <el-option label="Selenium" value="selenium" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.browser')">
          <el-select v-model="runConfig.browser" :placeholder="t('uiAutomation.testCase.browser')" style="width: 100%">
            <el-option label="Chrome" value="chrome" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="Safari" value="safari" />
            <el-option label="Edge" value="edge" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.executionMode')">
          <el-radio-group v-model="runConfig.headless">
            <el-radio :label="false">{{ t('uiAutomation.testCase.headedMode') }}</el-radio>
            <el-radio :label="true">{{ t('uiAutomation.testCase.headlessMode') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.runTargetUrl')" :required="!runConfig.autoLogin">
          <el-input
            v-model="runConfig.targetUrl"
            :placeholder="t('uiAutomation.testCase.runTargetUrlPlaceholder')"
            clearable
          />
        </el-form-item>
        <el-form-item :label="t('uiAutomation.testCase.runAutoLogin')">
          <el-switch v-model="runConfig.autoLogin" />
          <span class="record-auto-login-hint">
            {{ t('uiAutomation.testCase.recordAutoLoginNoCreds') }}
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showRunDialog = false">{{ t('uiAutomation.common.cancel') }}</el-button>
          <el-button type="primary" :loading="isRunning" @click="confirmRunTestCase">
            {{ t('uiAutomation.testCase.runLabel') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onActivated, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, Edit, Delete, Check, CaretRight, ArrowUp, ArrowDown, Rank, MagicStick, VideoCamera, RefreshRight, Close, CopyDocument, Download, DArrowLeft, DArrowRight, Monitor
} from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import DataFactorySelector from '@/components/DataFactorySelector.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

import {
  loadUiAutomationProjects,
  getElements,
  createTestCase,
  updateTestCase,
  deleteTestCase as deleteTestCaseApi,
  getTestCases,
  runTestCase as runTestCaseApi,
  copyTestCase as copyTestCaseApi,
  getLocatorStrategies,
  checkCodegenEnv,
  startCodegenRecording,
  getCodegenStatus,
  stopCodegenRecording,
  getCodegenRecordedContent,
  parseCodegenToCaseSteps,
  getElementGroups,
  getElementGroupTree,
  getTestCaseDetail,
  updateElement,
  startElementPicker,
  inspectElementPicker,
  clickElementPicker,
  typeElementPicker,
  scrollElementPicker,
  navigateElementPicker,
  saveElementFromPicker,
  stopElementPicker
} from '@/api/ui_automation'
import { getVariableFunctions } from '@/api/data-factory'

// 响应式数据
const projects = ref([])
const projectId = ref('all')
const ALL_PROJECTS = 'all'
const isAllProjectsSelected = () => projectId.value === ALL_PROJECTS || projectId.value === ''
const getProjectQueryParams = () => (isAllProjectsSelected() ? {} : { project: projectId.value })
const ensureProjectSelected = () => {
  if (isAllProjectsSelected()) {
    ElMessage.warning(t('uiAutomation.common.selectSpecificProject'))
    return false
  }
  return true
}
const testCases = ref([])
const selectedTestCase = ref(null)
const currentSteps = ref([])
const availableElements = ref([])
const locatorStrategies = ref([])
const availablePageNames = ref([])
const searchKeyword = ref('')
const showCreateDialog = ref(false)
const editingTestCase = ref(null)
const executionResult = ref(null)

// ===== 元素拾取投屏 =====
const pickerVisible = ref(false)
const leftPanelCollapsed = ref(false)
const inspectModeActive = ref(false)
const pickerStarting = ref(false)
const pickerNavigating = ref(false)
const pickerSession = ref(null)
const pickerScreenshot = ref('')
const pickerNavUrl = ref('')
const pickTargetStep = ref(null)
const pickerInspect = ref(null)
const pickerHighlight = ref(null)
const pickerImgRef = ref(null)
const pickerInspecting = ref(false)
let pickerWs = null
const PICK_STRATEGY_PRIORITY = [
  'placeholder', 'label', 'test-id', 'ID', 'id', 'role', 'name', 'text', 'title', 'class', 'CSS', 'css', 'XPath', 'xpath'
]

const _strategyRank = (strategy) => {
  const i = PICK_STRATEGY_PRIORITY.indexOf(String(strategy || ''))
  return i < 0 ? 999 : i
}

/** 唯一匹配置顶，组内按语义策略优先 */
const sortLocatorsUniqueFirst = (locs) => {
  return [...(locs || [])].sort((a, b) => {
    const ua = a?.unique ? 1 : 0
    const ub = b?.unique ? 1 : 0
    if (ua !== ub) return ub - ua
    return _strategyRank(a?.strategy) - _strategyRank(b?.strategy)
  })
}

const sortedPickerLocators = computed(() => sortLocatorsUniqueFirst(pickerInspect.value?.locators))

const locatorStrategyLabel = (strategy) => {
  const s = String(strategy || '')
  const map = {
    label: t('uiAutomation.testCase.strategyLabel'),
    css: t('uiAutomation.testCase.strategyCssPath'),
    CSS: t('uiAutomation.testCase.strategyCssPath'),
    xpath: 'XPath',
    XPath: 'XPath',
    placeholder: 'placeholder',
    id: 'ID',
    ID: 'ID',
    'test-id': 'test-id',
    role: 'role',
    name: 'name',
    class: 'class',
    text: 'text',
    title: 'title'
  }
  return map[s] || s
}

const pickerHighlightStyle = computed(() => {
  const h = pickerHighlight.value
  const img = pickerImgRef.value
  if (!h || !img || !h.viewport) return { display: 'none' }
  const scaleX = img.clientWidth / (h.viewport.w || 1)
  const scaleY = img.clientHeight / (h.viewport.h || 1)
  return {
    left: `${h.rect.x * scaleX}px`,
    top: `${h.rect.y * scaleY}px`,
    width: `${h.rect.w * scaleX}px`,
    height: `${h.rect.h * scaleY}px`
  }
})

const disconnectPickerWs = () => {
  if (pickerWs) {
    try { pickerWs.close() } catch { /* ignore */ }
    pickerWs = null
  }
}

const connectPickerWs = (sessionId) => {
  disconnectPickerWs()
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws/ui-automation/element-picker/${sessionId}/`)
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'screenshot' && data.image) {
        pickerScreenshot.value = data.image
        pickerStarting.value = false
        if (data.page_url) pickerNavUrl.value = data.page_url
      }
    } catch { /* ignore */ }
  }
  pickerWs = ws
}

/** 右侧投屏是否已开（含启动中），此时禁止再调 start API */
const isScreencastOpen = () =>
  pickerVisible.value && !!(pickerSession.value || pickerScreenshot.value || pickerStarting.value)

/** 在已有投屏上进入检查元素（不重启浏览器） */
const activateInspectForStep = (step) => {
  pickTargetStep.value = step || null
  inspectModeActive.value = true
  pickerInspect.value = null
  pickerHighlight.value = null
  leftPanelCollapsed.value = true
  executionResult.value = null
}

const startPickerSession = async ({ step = null, inspect = false } = {}) => {
  // 投屏已开：只切目标步骤 / 检查模式，绝不重新 start
  if (isScreencastOpen()) {
    pickTargetStep.value = step
    if (inspect) activateInspectForStep(step)
    return
  }
  const pid = resolveRecordProjectId()
  if (!pid) {
    ElMessage.warning(t('uiAutomation.common.selectSpecificProject'))
    return
  }
  pickTargetStep.value = step
  pickerVisible.value = true
  leftPanelCollapsed.value = true
  inspectModeActive.value = inspect
  pickerStarting.value = true
  pickerInspect.value = null
  pickerHighlight.value = null
  pickerScreenshot.value = ''
  executionResult.value = null
  try {
    const res = await startElementPicker({ project_id: pid })
    const session = res.data?.session || res.session
    pickerSession.value = session
    pickerNavUrl.value = session?.page_url || session?.start_url || ''
    // HTTP 带回首帧，立刻出图，不依赖 WS 入组时序
    if (session?.image) {
      pickerScreenshot.value = session.image
    }
    if (session?.session_id) connectPickerWs(session.session_id)
    // 无首帧时保持 loading，等 WS 首包；最长再等 8s
    if (!pickerScreenshot.value) {
      const deadline = Date.now() + 8000
      while (!pickerScreenshot.value && Date.now() < deadline) {
        await new Promise(r => setTimeout(r, 200))
      }
    }
    if (pickerScreenshot.value) {
      ElMessage.success(
        inspect
          ? t('uiAutomation.testCase.messages.pickStarted')
          : t('uiAutomation.testCase.messages.screencastStarted')
      )
    } else {
      ElMessage.warning(t('uiAutomation.testCase.messages.screencastNoFrame'))
    }
  } catch (err) {
    pickerVisible.value = false
    leftPanelCollapsed.value = false
    inspectModeActive.value = false
    pickerSession.value = null
    ElMessage.error(err?.response?.data?.error || err?.message || t('uiAutomation.testCase.messages.pickStartFailed'))
  } finally {
    pickerStarting.value = false
  }
}

/** 用例级投屏：打开右侧投屏窗（可操作页面，不进入检查态） */
const openScreencast = () => startPickerSession({ inspect: false })

/** 步骤级拾取：已投屏则直接检查元素，否则先启动投屏再进入检查态 */
const startPickElement = (step) => {
  if (isScreencastOpen()) {
    activateInspectForStep(step)
    return
  }
  return startPickerSession({ step, inspect: true })
}

const exitInspectMode = () => {
  inspectModeActive.value = false
  pickerInspect.value = null
  pickerHighlight.value = null
}

const enterInspectMode = () => {
  inspectModeActive.value = true
}

const stopPickElement = async () => {
  disconnectPickerWs()
  pickerVisible.value = false
  leftPanelCollapsed.value = false
  inspectModeActive.value = false
  pickerScreenshot.value = ''
  pickerInspect.value = null
  pickerHighlight.value = null
  pickerSession.value = null
  pickTargetStep.value = null
  try {
    await stopElementPicker()
  } catch { /* ignore */ }
}

const navigatePickerUrl = async () => {
  const url = (pickerNavUrl.value || '').trim()
  if (!url) return
  pickerNavigating.value = true
  try {
    const res = await navigateElementPicker({ url })
    const data = res.data || res
    pickerNavUrl.value = data.page_url || url
    applyPickerImage(data)
    pickerInspect.value = null
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || err?.message || t('uiAutomation.testCase.messages.pickNavigateFailed'))
  } finally {
    pickerNavigating.value = false
  }
}

const applyPickerImage = (payload) => {
  const image = payload?.image || payload?.data?.image
  if (image) pickerScreenshot.value = image
  const pageUrl = payload?.page_url || payload?.data?.page_url
  if (pageUrl) pickerNavUrl.value = pageUrl
}

const onPickerWheel = async (e) => {
  if (!pickerSession.value) return
  try {
    const res = await scrollElementPicker({ delta_y: e.deltaY })
    applyPickerImage(res.data || res)
  } catch { /* ignore */ }
}

const _pickerClickPoint = (e) => {
  const img = e.currentTarget
  const rect = img.getBoundingClientRect()
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
    img_w: img.clientWidth,
    img_h: img.clientHeight
  }
}

const onPickerScreenClick = async (e) => {
  if (!pickerSession.value || pickerInspecting.value) return
  const point = _pickerClickPoint(e)
  if (inspectModeActive.value) {
    pickerInspecting.value = true
    try {
      const res = await inspectElementPicker(point)
      const result = res.data?.result || res.result
      if (!result || !(result.locators || []).length) {
        ElMessage.warning(t('uiAutomation.testCase.messages.pickNoElement'))
        return
      }
      pickerInspect.value = result
      if (result.rect && result.viewport) {
        pickerHighlight.value = { rect: result.rect, viewport: result.viewport }
      }
    } catch (err) {
      ElMessage.error(err?.response?.data?.error || err?.message || t('uiAutomation.testCase.messages.pickInspectFailed'))
    } finally {
      pickerInspecting.value = false
    }
    return
  }
  // 操作态：转发真实点击
  try {
    e.currentTarget?.closest?.('.picker-screen-wrap')?.focus?.()
    const res = await clickElementPicker({ ...point, button: 'left', click_count: 1 })
    applyPickerImage(res.data || res)
  } catch { /* ignore */ }
}

const onPickerScreenDblClick = async (e) => {
  if (inspectModeActive.value || !pickerSession.value) return
  try {
    const res = await clickElementPicker({ ..._pickerClickPoint(e), button: 'left', click_count: 2 })
    applyPickerImage(res.data || res)
  } catch { /* ignore */ }
}

const onPickerScreenContextMenu = async (e) => {
  if (inspectModeActive.value || !pickerSession.value) return
  try {
    const res = await clickElementPicker({ ..._pickerClickPoint(e), button: 'right', click_count: 1 })
    applyPickerImage(res.data || res)
  } catch { /* ignore */ }
}

const onPickerKeydown = async (e) => {
  if (inspectModeActive.value || !pickerSession.value) return
  // 避免输入框抢焦点时误传
  const tag = (e.target?.tagName || '').toLowerCase()
  if (tag === 'input' || tag === 'textarea') return
  e.preventDefault()
  try {
    let res
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      res = await typeElementPicker({ text: e.key })
    } else {
      const map = {
        Enter: 'Enter',
        Backspace: 'Backspace',
        Delete: 'Delete',
        Tab: 'Tab',
        Escape: 'Escape',
        ArrowLeft: 'ArrowLeft',
        ArrowRight: 'ArrowRight',
        ArrowUp: 'ArrowUp',
        ArrowDown: 'ArrowDown'
      }
      if (map[e.key]) {
        res = await typeElementPicker({ key: map[e.key] })
      }
    }
    if (res) applyPickerImage(res.data || res)
  } catch { /* ignore */ }
}

const copyLocator = async (loc) => {
  const text = `${loc.strategy}=${loc.value}`
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('uiAutomation.testCase.messages.locatorCopied'))
  } catch {
    ElMessage.warning(text)
  }
}

const applyPrimaryToStep = (step, strategy, value) => {
  step.element_locator_strategy = strategy
  step.element_locator = value
  if (!Array.isArray(step.element_backup_locators)) step.element_backup_locators = []
}

const fillOneLocator = async (loc) => {
  const step = pickTargetStep.value
  if (!step || !loc) return

  // 单条填入：仅追加备用，不改主选择器
  if (!Array.isArray(step.element_backup_locators)) {
    step.element_backup_locators = []
  }
  const key = `${loc.strategy}|${loc.value}`
  const sameAsPrimary =
    `${step.element_locator_strategy || ''}|${step.element_locator || ''}` === key
  const already = step.element_backup_locators.some(b => `${b.strategy}|${b.value}` === key)
  if (sameAsPrimary) {
    ElMessage.warning(t('uiAutomation.testCase.messages.locatorIsPrimary'))
    return
  }
  if (!already) {
    step.element_backup_locators.push({ strategy: loc.strategy, value: loc.value })
  }

  step.expanded = true
  await onStepLocatorChange(step)
  ElMessage.success(
    already
      ? t('uiAutomation.testCase.messages.locatorBackupExists')
      : t('uiAutomation.testCase.messages.locatorBackupAdded')
  )
}

const fillAllLocators = async () => {
  const step = pickTargetStep.value
  const locs = sortedPickerLocators.value
  if (!step || !locs.length) return
  const unique = locs.filter(l => l.unique)
  const pool = unique.length ? unique : locs
  let primary = null
  for (const name of PICK_STRATEGY_PRIORITY) {
    primary = pool.find(l => String(l.strategy) === name)
    if (primary) break
  }
  if (!primary) primary = pool[0]
  const backups = []
  const seen = new Set([`${primary.strategy}|${primary.value}`])
  for (const l of unique) {
    const key = `${l.strategy}|${l.value}`
    if (seen.has(key)) continue
    seen.add(key)
    backups.push({ strategy: l.strategy, value: l.value })
  }
  try {
    const res = await saveElementFromPicker({
      strategy: primary.strategy,
      value: primary.value,
      backup_locators: backups,
      tag: pickerInspect.value?.tag || ''
    })
    const payload = res.data || res
    const elem = payload.element
    if (!elem?.id) {
      ElMessage.error(t('uiAutomation.testCase.messages.pickSaveElementFailed'))
      return
    }
    // 刷新本地元素库缓存
    const idx = availableElements.value.findIndex(e => e.id === elem.id || e.id === Number(elem.id))
    if (idx >= 0) availableElements.value.splice(idx, 1, elem)
    else availableElements.value.unshift(elem)
    if (elem.page && !availablePageNames.value.includes(elem.page)) {
      availablePageNames.value = [...availablePageNames.value, elem.page]
    }

    step.element_id = elem.id
    step.page_filter = elem.page || payload.page || step.page_filter || ''
    applyPrimaryToStep(step, strategyNameOf(elem) || primary.strategy, elem.locator_value || primary.value)
    step.element_backup_locators = Array.isArray(elem.backup_locators)
      ? elem.backup_locators.map(b => ({ strategy: b.strategy || 'css', value: b.value || '' }))
      : backups
    hydrateStepElementFields(step, elem)
    if (!step.description) {
      step.description = buildFriendlyStepDescription(step.action_type, elem)
    }
    step.expanded = true
    ElMessage.success(t('uiAutomation.testCase.messages.locatorFilledAll', { n: 1 + backups.length }))
  } catch (err) {
    ElMessage.error(
      err?.response?.data?.error || err?.message || t('uiAutomation.testCase.messages.pickSaveElementFailed')
    )
  }
}

const allStepsExpanded = ref(false)
const showScreenshotPreview = ref(false)
const currentScreenshot = ref(null)
const isRunning = ref(false)
const showRunDialog = ref(false)
const pendingRunCase = ref(null)
const runConfig = reactive({
  engine: 'playwright',
  browser: 'chrome',
  headless: false,
  targetUrl: 'https://',
  autoLogin: true
})
const showVariableHelper = ref(false)
const currentEditingStep = ref(null)
const currentEditingField = ref('')
const showDataFactorySelector = ref(false)
const currentStepForDataFactory = ref(null)
const currentFieldForDataFactory = ref('')
const variableCategories = ref([])
const loading = ref(false)

// 录制步骤
const showRecordDialog = ref(false)
const recordForm = reactive({
  targetUrl: 'https://',
  browser: 'chromium',
  language: 'python',
  autoLogin: true
})
const recordSession = ref(null)
const recordScriptContent = ref('')
const recordStarting = ref(false)
const recordStopping = ref(false)
const recordParsing = ref(false)
const recordEnvReady = ref(true)
const parsedRecordSteps = ref([])
const recordImportMode = ref('append')
let recordPollTimer = null

const recordIsRecording = computed(() => ['starting', 'recording'].includes(recordSession.value?.status))

const recordStatusText = computed(() => {
  const status = recordSession.value?.status
  const map = {
    starting: t('uiAutomation.testCase.recordStatusStarting'),
    recording: t('uiAutomation.testCase.recordStatusRecording'),
    finished: t('uiAutomation.testCase.recordStatusFinished'),
    stopped: t('uiAutomation.testCase.recordStatusStopped'),
    failed: t('uiAutomation.testCase.recordStatusFailed')
  }
  return map[status] || t('uiAutomation.testCase.recordStatusIdle')
})

const recordStatusTagType = computed(() => {
  const status = recordSession.value?.status
  if (status === 'recording' || status === 'starting') return 'warning'
  if (status === 'finished') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
})



// 表单数据
const testCaseForm = reactive({
  name: '',
  description: '',
  priority: 'medium'
})

// 计算属性
const filteredTestCases = computed(() => {
  if (!searchKeyword.value) return testCases.value
  return testCases.value.filter(tc =>
    tc.name.includes(searchKeyword.value) ||
    tc.description?.includes(searchKeyword.value)
  )
})

// 获取所有可用页面（去重）：合并元素 page 字段与最新分组名
const distinctPages = computed(() => {
  const pages = new Set(availablePageNames.value.filter(Boolean))
  availableElements.value.forEach(elem => {
    if (elem.page) {
      pages.add(elem.page)
    } else {
      pages.add('未关联页面')
    }
  })
  return ['全部页面', ...Array.from(pages)]
})

// 根据页面筛选元素列表
const getFilteredElements = (step) => {
  const pageFilter = step.page_filter
  let list
  if (!pageFilter || pageFilter === '全部页面') {
    list = [...availableElements.value]
  } else if (pageFilter === '未关联页面') {
    list = availableElements.value.filter(elem => !elem.page)
  } else {
    // 兼容录制：步骤 page_filter=home，但元素 page 为空、仅 name 前缀为 home_
    list = availableElements.value.filter(elem => {
      if (elem.page === pageFilter) return true
      if (!elem.page && typeof elem.name === 'string' && elem.name.startsWith(`${pageFilter}_`)) return true
      return false
    })
    // 筛选结果为空时回退为全部，避免下拉「无数据」只显示裸 id
    if (list.length === 0) {
      list = [...availableElements.value]
    }
  }

  // 已选元素若不在列表中：从缓存补齐，或用步骤上的 element_name 合成选项
  if (step.element_id) {
    const selectedId = Number(step.element_id)
    let selected = list.find(e => e.id === selectedId || e.id === step.element_id)
    if (!selected) {
      selected = availableElements.value.find(e => e.id === selectedId || e.id === step.element_id)
    }
    if (!selected && (step.element_name || step.element_locator)) {
      selected = {
        id: selectedId || step.element_id,
        name: step.element_name || `元素#${step.element_id}`,
        locator_value: step.element_locator || '',
        locator_strategy: step.element_locator_strategy || '',
        page: step.page_filter || ''
      }
    }
    if (selected && !list.some(e => e.id === selected.id)) {
      list = [selected, ...list]
    }
  }
  return list
}

// 页面筛选变更处理
const onPageFilterChange = (step) => {
  const pageFilter = step.page_filter
  const currentElement = availableElements.value.find(e => e.id === step.element_id || e.id === Number(step.element_id))
  if (currentElement && pageFilter && pageFilter !== '全部页面') {
    let pageMatched = false
    if (pageFilter === '未关联页面') {
      pageMatched = !currentElement.page
    } else {
      pageMatched = currentElement.page === pageFilter
        || (!currentElement.page && typeof currentElement.name === 'string' && currentElement.name.startsWith(`${pageFilter}_`))
    }
    if (!pageMatched) {
      // 不强制清空：允许保留已选元素，避免只剩裸 id
    }
  }
}

// 解析执行日志
const parsedExecutionLogs = computed(() => {
  if (!executionResult.value || !executionResult.value.logs) return []
  try {
    const logs = typeof executionResult.value.logs === 'string'
      ? JSON.parse(executionResult.value.logs)
      : executionResult.value.logs
    return Array.isArray(logs) ? logs : [{ description: String(logs), success: executionResult.value.success, step_number: 1 }]
  } catch (e) {
    // 非 JSON 字符串日志直接展示
    return [{
      description: String(executionResult.value.logs),
      success: executionResult.value.success,
      step_number: 1
    }]
  }
})

const healedStepSummaries = computed(() => {
  const fromApi = executionResult.value?.ai_healing?.steps
  if (Array.isArray(fromApi) && fromApi.length > 0) {
    return fromApi
  }
  return parsedExecutionLogs.value
    .filter((s) => s && s.healed)
    .map((s) => ({
      step_number: s.step_number,
      description: s.description || '',
      healing_reason: s.healing_reason || '',
      healed_locator: s.healed_locator || null
    }))
})

const executionPassedWithHeal = computed(() => {
  if (executionResult.value?.healed) return true
  return !!(executionResult.value?.success && healedStepSummaries.value.length > 0)
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
    ElMessage.error('获取项目列表失败')
    console.error('获取项目列表失败:', error)
  }
}

const loadTestCases = async () => {
  if (!projectId.value) {
    testCases.value = []
    return
  }

  try {
    const response = await getTestCases(getProjectQueryParams())
    testCases.value = response.data.results || response.data
  } catch (error) {
    console.error('获取测试用例失败:', error)
  }
}

const loadElements = async () => {
  if (!projectId.value) {
    availableElements.value = []
    return
  }

  try {
    // 下拉需要完整列表；后端默认分页 20，且旧配置可能忽略 page_size，这里翻页拉全
    const baseParams = {
      ...getProjectQueryParams(),
      page_size: 1000
    }
    const all = []
    let page = 1
    let next = true
    while (next) {
      const response = await getElements({ ...baseParams, page })
      const payload = response.data
      const batch = payload?.results || (Array.isArray(payload) ? payload : [])
      all.push(...batch)
      next = Boolean(payload?.next)
      page += 1
      // 防护：异常 next 时避免死循环
      if (page > 50) break
    }
    availableElements.value = all
    syncStepPageFiltersFromElements()
    hydrateAllStepsFromElements(currentSteps)
    hydrateAllStepsFromElements(parsedRecordSteps)
  } catch (error) {
    console.error('获取元素列表失败:', error)
  }
}

const loadLocatorStrategies = async () => {
  try {
    const response = await getLocatorStrategies()
    const payload = response.data
    locatorStrategies.value = payload?.results || (Array.isArray(payload) ? payload : [])
  } catch (error) {
    console.error('获取定位策略失败:', error)
  }
}

const strategyNameOf = (elem) => {
  if (!elem) return ''
  if (typeof elem.locator_strategy === 'string') return elem.locator_strategy
  return elem.locator_strategy?.name || elem.element_locator_strategy || ''
}

const formatElementOptionLabel = (elem) => {
  const strategy = strategyNameOf(elem)
  const expr = elem.locator_value || elem.element_locator || ''
  if (strategy && expr) return `${elem.name} (${strategy}: ${expr})`
  if (expr) return `${elem.name} (${expr})`
  return elem.name || String(elem.id)
}

const resolveMediaUrl = (url) => {
  if (!url) return ''
  if (String(url).startsWith('data:')) return url
  // 绝对地址只取 path，走前端 /media 代理，避免 127.0.0.1 vs localhost 丢图
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

const hydrateStepElementFields = (step, elem) => {
  if (!elem || !step) return
  step.element_name = elem.name || step.element_name || ''
  step.element_locator = elem.locator_value || step.element_locator || ''
  step.element_locator_strategy = strategyNameOf(elem) || step.element_locator_strategy || ''
  // 元素库为准：录制写入的备用/截图在元素上，步骤需回填
  if (Array.isArray(elem.backup_locators)) {
    step.element_backup_locators = elem.backup_locators.map(b => ({
      strategy: b.strategy || 'css',
      value: b.value || ''
    }))
  } else if (!Array.isArray(step.element_backup_locators)) {
    step.element_backup_locators = []
  }
  const shot = elem.screenshot_url || elem.screenshot || elem.element_screenshot || ''
  if (shot) {
    step.element_screenshot = resolveMediaUrl(shot) || shot
  } else if (!step.element_screenshot) {
    step.element_screenshot = ''
  }
  step.wait_timeout = elem.wait_timeout ?? 5
}

/** 用 availableElements 回填步骤上的截图/策略/备用选择器 */
const hydrateAllStepsFromElements = (stepsRef = currentSteps) => {
  const list = stepsRef?.value || stepsRef || []
  if (!list.length || !availableElements.value.length) return
  list.forEach(step => {
    if (!step.element_id) return
    const elem = availableElements.value.find(
      e => e.id === step.element_id || e.id === Number(step.element_id)
    )
    if (elem) hydrateStepElementFields(step, elem)
  })
}

const onStepLocatorChange = async (step) => {
  if (!step?.element_id) return
  const strategyName = step.element_locator_strategy || 'css'
  const strategy = locatorStrategies.value.find(
    s => s.name === strategyName || String(s.id) === String(strategyName)
  )
  // 策略可重复；同一策略下同一表达式不可重复
  const seen = new Set()
  const backups = []
  for (const b of (step.element_backup_locators || [])) {
    if (!b.strategy || !b.value) continue
    const key = `${String(b.strategy).toLowerCase()}|${b.value}`
    if (seen.has(key)) continue
    seen.add(key)
    backups.push({ strategy: b.strategy, value: b.value })
  }
  step.element_backup_locators = backups
  const payload = {
    locator_value: step.element_locator || '',
    backup_locators: backups
  }
  if (strategy?.id) {
    payload.locator_strategy_id = strategy.id
  }
  try {
    await updateElement(step.element_id, payload)
    const cached = availableElements.value.find(e => e.id === step.element_id || e.id === Number(step.element_id))
    if (cached) {
      cached.locator_value = payload.locator_value
      cached.backup_locators = payload.backup_locators
      if (strategy) {
        cached.locator_strategy = strategy
        cached.locator_strategy_id = strategy.id
      }
    }
  } catch (error) {
    console.error('更新元素定位器失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || t('uiAutomation.testCase.messages.updateLocatorFailed'))
  }
}

const onStepWaitTimeoutChange = async (step) => {
  if (!step?.element_id) return
  const wait_timeout = Number(step.wait_timeout) || 5
  step.wait_timeout = wait_timeout
  try {
    await updateElement(step.element_id, { wait_timeout })
    const cached = availableElements.value.find(e => e.id === step.element_id || e.id === Number(step.element_id))
    if (cached) cached.wait_timeout = wait_timeout
  } catch (error) {
    console.error('更新元素等待超时失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || t('uiAutomation.testCase.messages.updateLocatorFailed'))
  }
}

const addBackupLocatorRow = (step) => {
  if (!Array.isArray(step.element_backup_locators)) {
    step.element_backup_locators = []
  }
  step.element_backup_locators.push({ strategy: 'css', value: '' })
}

const removeBackupLocator = (step, index) => {
  if (!Array.isArray(step.element_backup_locators)) return
  step.element_backup_locators.splice(index, 1)
  onStepLocatorChange(step)
}

/** 用元素当前所属页面刷新步骤中的页面显示，跟随分组改名 */
const syncStepPageFiltersFromElements = () => {
  if (!currentSteps.value.length) return
  currentSteps.value.forEach(step => {
    if (!step.element_id) return
    const el = availableElements.value.find(
      e => e.id === step.element_id || e.id === Number(step.element_id)
    )
    if (!el) return
    const latestPage = el.page || el.group?.name || ''
    if (latestPage && step.page_filter !== latestPage) {
      step.page_filter = latestPage
    }
  })
}

const collectGroupNames = (groups, acc = []) => {
  ;(groups || []).forEach(g => {
    if (g?.name) acc.push(g.name)
    if (g?.children?.length) collectGroupNames(g.children, acc)
  })
  return acc
}

const loadPageNames = async () => {
  if (!projectId.value) {
    availablePageNames.value = []
    return
  }
  try {
    const [listRes, treeRes] = await Promise.all([
      getElementGroups({ ...getProjectQueryParams(), page_size: 1000 }),
      getElementGroupTree(getProjectQueryParams()).catch(() => null)
    ])
    const flat = listRes.data?.results || listRes.data || []
    const tree = treeRes?.data || []
    const names = new Set([
      ...flat.map(g => g.name).filter(Boolean),
      ...collectGroupNames(tree)
    ])
    availablePageNames.value = Array.from(names)
  } catch (error) {
    console.error('获取页面分组失败:', error)
    availablePageNames.value = []
  }
}

const refreshSelectedTestCaseSteps = async () => {
  if (!selectedTestCase.value?.id) return
  try {
    const response = await getTestCaseDetail(selectedTestCase.value.id)
    const latest = response.data
    if (!latest) return
    selectedTestCase.value = latest
    if (latest.steps?.length) {
      // 保留展开状态
      const expandedMap = new Map(currentSteps.value.map(s => [s.id, s.expanded]))
      currentSteps.value = latest.steps.map(step => {
        const mapped = {
          ...step,
          page_filter: step.page_filter || '',
          element_id: step.element ?? '',
          element_locator_strategy: step.element_locator_strategy || '',
          element_backup_locators: Array.isArray(step.element_backup_locators)
            ? step.element_backup_locators.map(b => ({ strategy: b.strategy || 'css', value: b.value || '' }))
            : [],
          element_screenshot: step.element_screenshot || '',
          expanded: expandedMap.get(step.id) || false
        }
        const elem = availableElements.value.find(e => e.id === mapped.element_id || e.id === Number(mapped.element_id))
        if (elem) hydrateStepElementFields(mapped, elem)
        return mapped
      })
      syncStepPageFiltersFromElements()
    }
  } catch (error) {
    console.error('刷新用例步骤失败:', error)
  }
}

const onProjectChange = async () => {
  selectedTestCase.value = null
  currentSteps.value = []
  executionResult.value = null

  await Promise.all([
    loadTestCases(),
    loadElements(),
    loadPageNames(),
    loadLocatorStrategies()
  ])
}

const selectTestCase = (testCase) => {
  // 如果点击的是同一个用例，不做任何处理
  if (selectedTestCase.value && selectedTestCase.value.id === testCase.id) {
    return
  }

  selectedTestCase.value = testCase
  // 确保步骤数据格式正确，添加前端需要的字段
  if (testCase.steps && testCase.steps.length > 0) {
    currentSteps.value = testCase.steps.map(step => {
      const mapped = {
        ...step,
        page_filter: step.page_filter || '',
        element_id: step.element ?? '',
        element_locator_strategy: step.element_locator_strategy || '',
        element_backup_locators: Array.isArray(step.element_backup_locators)
          ? step.element_backup_locators.map(b => ({ strategy: b.strategy || 'css', value: b.value || '' }))
          : [],
        element_screenshot: step.element_screenshot || '',
        expanded: false
      }
      const elem = availableElements.value.find(e => e.id === mapped.element_id || e.id === Number(mapped.element_id))
      if (elem) hydrateStepElementFields(mapped, elem)
      return mapped
    })
    syncStepPageFiltersFromElements()
  } else {
    currentSteps.value = []
  }
  // 只有在切换到不同用例时才清空执行结果
  executionResult.value = null
}

const addStep = () => {
  const newStep = {
    id: Date.now(),
    action_type: 'click',
    page_filter: '',
    element_id: '',
    input_value: '',
    wait_time: 1000,
    assert_type: 'textContains',
    assert_value: '',
    description: '',
    expanded: false
  }
  currentSteps.value.push(newStep)
}

const clearRecordPoll = () => {
  if (recordPollTimer) {
    clearInterval(recordPollTimer)
    recordPollTimer = null
  }
}

const applyRecordSession = (nextSession) => {
  recordSession.value = nextSession || null
  if (nextSession?.content) {
    recordScriptContent.value = nextSession.content
  }
  if (['finished', 'stopped', 'failed'].includes(nextSession?.status)) {
    clearRecordPoll()
    if (nextSession.status === 'finished') {
      ElMessage.success(t('uiAutomation.testCase.messages.recordFinished'))
      if (recordScriptContent.value.trim() && !parsedRecordSteps.value.length) {
        parseRecordedSteps()
      }
    } else if (nextSession.status === 'failed' && nextSession.error) {
      ElMessage.error(nextSession.error)
    }
  }
}

const pollRecordStatus = async () => {
  try {
    const res = await getCodegenStatus({ include_content: 1 })
    const data = res.data || res
    applyRecordSession(data.session)
  } catch (error) {
    console.error(error)
  }
}

const startRecordPolling = () => {
  clearRecordPoll()
  recordPollTimer = setInterval(pollRecordStatus, 2000)
}

// project 可能是数字主键，也可能是 { id }；不能写 project?.id || projectId（会把 1 当成无 id 落到 'all'）
const resolveCaseProjectId = (tc) => tc?.project?.id ?? tc?.project_id ?? tc?.project ?? null

const resolveRecordProjectId = () => {
  if (!isAllProjectsSelected()) {
    return projectId.value
  }
  return resolveCaseProjectId(selectedTestCase.value)
}

const openRecordStepsDialog = async () => {
  if (!selectedTestCase.value) {
    ElMessage.warning(t('uiAutomation.testCase.selectTestCase'))
    return
  }
  const pid = resolveRecordProjectId()
  if (!pid) {
    ElMessage.warning(t('uiAutomation.common.selectSpecificProject'))
    return
  }

  showRecordDialog.value = true
  parsedRecordSteps.value = []
  recordScriptContent.value = ''
  recordSession.value = null
  recordImportMode.value = 'append'

  try {
    const res = await checkCodegenEnv()
    const env = res.data || res
    recordEnvReady.value = Boolean(env?.can_start)
    if (!recordEnvReady.value) {
      ElMessage.warning(t('uiAutomation.testCase.messages.recordEnvNotReady'))
    }
  } catch (error) {
    recordEnvReady.value = false
    console.error(error)
    ElMessage.warning(t('uiAutomation.testCase.messages.recordEnvCheckFailed'))
  }

  // 复用登录态默认开：目标 URL 留空，由后端取项目环境地址
  recordForm.autoLogin = true
  recordForm.targetUrl = ''
}

const isBlankTargetUrl = (url) => {
  const v = (url || '').trim()
  return !v || v === 'https://' || v === 'http://'
}

const startRecordSteps = async () => {
  const url = (recordForm.targetUrl || '').trim()
  if (isBlankTargetUrl(url) && !recordForm.autoLogin) {
    ElMessage.warning(t('uiAutomation.testCase.messages.recordEmptyUrl'))
    return
  }
  recordStarting.value = true
  parsedRecordSteps.value = []
  try {
    const res = await startCodegenRecording({
      url: isBlankTargetUrl(url) ? '' : url,
      browser: recordForm.browser,
      language: recordForm.language,
      project_id: resolveRecordProjectId(),
      script_name: `case_${selectedTestCase.value?.id || 'tmp'}_record`,
      auto_login: recordForm.autoLogin
    })
    const data = res.data || res
    applyRecordSession(data.session)
    ElMessage.success(data.message || t('uiAutomation.testCase.messages.recordStarted'))
    startRecordPolling()
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.testCase.messages.recordStartFailed')
    ElMessage.error(msg)
  } finally {
    recordStarting.value = false
  }
}

const stopRecordSteps = async () => {
  recordStopping.value = true
  clearRecordPoll()
  try {
    const res = await stopCodegenRecording()
    const data = res.data || res
    applyRecordSession(data.session)
    if (data.session?.content) {
      recordScriptContent.value = data.session.content
    } else if (data.session?.script_name) {
      try {
        const fileRes = await getCodegenRecordedContent(data.session.script_name)
        const fileData = fileRes.data || fileRes
        if (fileData.content) {
          recordScriptContent.value = fileData.content
        }
      } catch (e) {
        console.error(e)
      }
    }
    ElMessage.success(data.message || t('uiAutomation.testCase.messages.recordStopped'))
    if (recordScriptContent.value.trim()) {
      await parseRecordedSteps()
    }
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.testCase.messages.recordStopFailed')
    ElMessage.error(msg)
    if (recordIsRecording.value) {
      startRecordPolling()
    }
  } finally {
    recordStopping.value = false
  }
}

const parseRecordedSteps = async () => {
  if (!recordScriptContent.value.trim()) {
    ElMessage.warning(t('uiAutomation.testCase.messages.recordEmptyScript'))
    return
  }
  recordParsing.value = true
  try {
    const scriptName = recordSession.value?.script_name
      || `case_${selectedTestCase.value?.id || 'tmp'}_record.py`
    const res = await parseCodegenToCaseSteps({
      content: recordScriptContent.value,
      project_id: resolveRecordProjectId(),
      language: recordForm.language,
      create_elements: true,
      recorded_name: scriptName,
      script_name: scriptName
    })
    const data = res.data || res
    parsedRecordSteps.value = (data.steps || []).map(step => ({
      ...step,
      element_backup_locators: Array.isArray(step.element_backup_locators)
        ? step.element_backup_locators.map(b => ({ strategy: b.strategy || 'css', value: b.value || '' }))
        : [],
      element_screenshot: step.element_screenshot || '',
      element_locator_strategy: step.element_locator_strategy || ''
    }))
    if (!parsedRecordSteps.value.length) {
      ElMessage.warning(t('uiAutomation.testCase.messages.recordNoSteps'))
    } else {
      const used = data.captures_used || 0
      ElMessage.success(
        data.message || t('uiAutomation.testCase.messages.recordParsed', { count: parsedRecordSteps.value.length })
        + (used ? `（采集 ${used} 个控件）` : '')
      )
      // 刷新元素列表，回填截图/备用选择器
      await loadElements()
      hydrateAllStepsFromElements(parsedRecordSteps)
    }
  } catch (error) {
    const msg = error.response?.data?.error || error.message || t('uiAutomation.testCase.messages.recordParseFailed')
    ElMessage.error(msg)
  } finally {
    recordParsing.value = false
  }
}

const importRecordedSteps = () => {
  if (!parsedRecordSteps.value.length) return

  const mapped = parsedRecordSteps.value.map((step, index) => {
    const row = {
      id: Date.now() + index,
      action_type: step.action_type || 'click',
      page_filter: step.page_filter || '',
      element_id: step.element_id || '',
      element_name: step.element_name || '',
      element_locator: step.element_locator || '',
      element_locator_strategy: step.element_locator_strategy || '',
      element_backup_locators: Array.isArray(step.element_backup_locators)
        ? step.element_backup_locators.map(b => ({ strategy: b.strategy || 'css', value: b.value || '' }))
        : [],
      element_screenshot: step.element_screenshot || '',
      input_value: step.input_value || '',
      wait_time: step.wait_time || 1000,
      assert_type: step.assert_type || 'textContains',
      assert_value: step.assert_value || '',
      description: step.description || '',
      expanded: false
    }
    const elem = availableElements.value.find(
      e => e.id === row.element_id || e.id === Number(row.element_id)
    )
    if (elem) hydrateStepElementFields(row, elem)
    return row
  })

  if (recordImportMode.value === 'replace') {
    currentSteps.value = mapped
  } else {
    currentSteps.value = [...currentSteps.value, ...mapped]
  }

  showRecordDialog.value = false
  ElMessage.success(t('uiAutomation.testCase.messages.recordImported', { count: mapped.length }))
}

const onRecordDialogClosed = () => {
  clearRecordPoll()
  // 录制进行中不强制 stop，用户可到 Playwright 录制页继续；此处仅停轮询
}

const removeStep = (index) => {
  currentSteps.value.splice(index, 1)
}

const onStepsReorder = () => {
  // 步骤重新排序后的处理
  console.log('步骤已重新排序')
}

const onActionTypeChange = (step) => {
  // 根据操作类型重置相关参数
  if (step.action_type !== 'fill') {
    step.input_value = ''
  }
  if (step.action_type !== 'wait') {
    step.wait_time = 1000
  }
  if (step.action_type !== 'assert') {
    step.assert_type = 'textContains'
    step.assert_value = ''
  }
}

const stripRecordedPrefix = (name) => {
  if (!name) return ''
  return String(name).replace(/^(?:recorded?_)+/i, '').replace(/_/g, ' ').trim()
}

const buildFriendlyStepDescription = (actionType, element) => {
  const label = stripRecordedPrefix(element?.name) || '元素'
  const typeMap = {
    INPUT: '输入框',
    BUTTON: '按钮',
    LINK: '链接',
    DROPDOWN: '下拉框',
    CHECKBOX: '复选框',
    RADIO: '单选框',
    TEXT: '文本'
  }
  const kind = typeMap[element?.element_type] || '元素'
  // 名称已含类型后缀时不再重复拼接
  const display = label.endsWith(kind) ? label.slice(0, -kind.length) || label : label
  if (actionType === 'click') return `点击「${display}」${kind}`
  if (actionType === 'fill') return `在「${display}」${kind}中输入`
  if (actionType === 'assert') return `断言「${display}」${kind}`
  if (actionType === 'hover') return `悬停「${display}」${kind}`
  if (actionType === 'getText') return `获取「${display}」${kind}文本`
  if (actionType === 'waitFor') return `等待「${display}」${kind}`
  return `${getActionTypeText(actionType)}「${display}」${kind}`
}

const onElementChange = (step) => {
  const element = availableElements.value.find(e => e.id === step.element_id || e.id === Number(step.element_id))
  if (element) {
    hydrateStepElementFields(step, element)
    if (!step.description) {
      step.description = buildFriendlyStepDescription(step.action_type, element)
    }
  }
}

const onStepHeaderClick = (step) => {
  step.expanded = !step.expanded
  if (step.expanded && step.element_id) {
    const elem = availableElements.value.find(
      e => e.id === step.element_id || e.id === Number(step.element_id)
    )
    if (elem) hydrateStepElementFields(step, elem)
  }
}

const needsInputValue = (actionType) => {
  return ['fill', 'switchTab', 'navigateUrl'].includes(actionType)
}

const needsWaitTime = (actionType) => {
  return ['wait', 'waitFor'].includes(actionType)
}

const needsElement = (actionType) => {
  return !['wait', 'switchTab', 'screenshot', 'navigateUrl'].includes(actionType)
}

const expandAllSteps = () => {
  allStepsExpanded.value = !allStepsExpanded.value
  currentSteps.value.forEach(step => {
    step.expanded = allStepsExpanded.value
  })
}

const saveTestCase = async () => {
  if (!selectedTestCase.value) return

  try {
    const project = resolveCaseProjectId(selectedTestCase.value)
    if (!project || project === ALL_PROJECTS) {
      ElMessage.warning(t('uiAutomation.common.selectSpecificProject'))
      return
    }
    const updateData = {
      name: selectedTestCase.value.name,
      description: selectedTestCase.value.description || '',
      priority: selectedTestCase.value.priority,
      status: selectedTestCase.value.status,
      project,
      steps: currentSteps.value
    }

    await updateTestCase(selectedTestCase.value.id, updateData)
    ElMessage.success(t('uiAutomation.testCase.save.success'))

    // 更新本地数据
    const merged = { ...selectedTestCase.value, ...updateData, steps: currentSteps.value }
    const index = testCases.value.findIndex(tc => tc.id === selectedTestCase.value.id)
    if (index !== -1) {
      testCases.value[index] = merged
    }
    selectedTestCase.value = merged
  } catch (error) {
      console.error('保存测试用例失败:', error)
      ElMessage.error(t('uiAutomation.testCase.save.failed'))
    }
}

const openRunDialog = (testCase) => {
  if (!testCase) {
    ElMessage.warning(t('uiAutomation.testCase.selectTestCase'))
    return
  }
  pendingRunCase.value = testCase
  runConfig.autoLogin = true
  // 复用登录态开启时目标 URL 留空，由后端取项目环境地址
  runConfig.targetUrl = ''
  showRunDialog.value = true
}

const confirmRunTestCase = async () => {
  const testCase = pendingRunCase.value
  if (!testCase) return
  if (isBlankTargetUrl(runConfig.targetUrl) && !runConfig.autoLogin) {
    ElMessage.warning(t('uiAutomation.testCase.messages.runEmptyUrl'))
    return
  }
  showRunDialog.value = false
  await runTestCase(testCase)
}

const runTestCase = async (testCase) => {
  isRunning.value = true
  try {
    const modeText = runConfig.headless ? t('uiAutomation.testCase.runMode.headless') : t('uiAutomation.testCase.runMode.headed')
    ElMessage.info(t('uiAutomation.testCase.run.start', { engine: runConfig.engine.toUpperCase(), browser: runConfig.browser.toUpperCase(), mode: modeText }))

    const targetUrl = isBlankTargetUrl(runConfig.targetUrl) ? '' : runConfig.targetUrl.trim()
    const response = await runTestCaseApi(testCase.id, {
      project_id: resolveCaseProjectId(testCase) || (isAllProjectsSelected() ? null : projectId.value),
      engine: runConfig.engine,
      browser: runConfig.browser,
      headless: runConfig.headless,
      target_url: targetUrl,
      auto_login: runConfig.autoLogin
    })

    executionResult.value = response.data

    if (response.data.success) {
      if (response.data.healed) {
        ElMessage.success(t('uiAutomation.testCase.healedViaAi'))
      } else {
        ElMessage.success(t('uiAutomation.testCase.run.success'))
      }
    } else {
      ElMessage.error(t('uiAutomation.testCase.run.failed'))
    }
  } catch (error) {
    console.error('执行测试用例失败:', error)

    // 即使出错也要设置执行结果,显示错误信息
    const errorMessage = error.response?.data?.message || error.message || '执行失败'
    const errorLogs = error.response?.data?.logs || `测试用例执行出错\n\n错误信息: ${errorMessage}`

    // 格式化错误信息为统一的对象格式
    const errors = error.response?.data?.errors || [{
      message: errorMessage,
      details: error.stack || '',
      step_number: null,
      action_type: '',
      element: '',
      description: ''
    }]

    executionResult.value = {
      success: false,
      logs: errorLogs,
      screenshots: error.response?.data?.screenshots || [],
      execution_time: 0,
      errors: errors
    }

    ElMessage.error(t('uiAutomation.testCase.run.failedWithMessage', { message: errorMessage }))
  } finally {
    isRunning.value = false
  }
}

const closeExecutionResult = () => {
  executionResult.value = null
}

const editTestCase = (testCase) => {
  editingTestCase.value = testCase
  testCaseForm.name = testCase.name
  testCaseForm.description = testCase.description || ''
  testCaseForm.priority = testCase.priority || 'medium'
  showCreateDialog.value = true
}

const deleteTestCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.testCase.delete.confirm', { name: testCase.name }),
      t('uiAutomation.testCase.delete.title'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'warning'
      }
    )

    await deleteTestCaseApi(testCase.id)
    ElMessage.success(t('uiAutomation.testCase.delete.success'))

    // 从列表中移除
    const index = testCases.value.findIndex(tc => tc.id === testCase.id)
    if (index !== -1) {
      testCases.value.splice(index, 1)
    }

    // 如果删除的是当前选中的用例，清空选择
    if (selectedTestCase.value?.id === testCase.id) {
      selectedTestCase.value = null
      currentSteps.value = []
      executionResult.value = null
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除测试用例失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const copyTestCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      t('uiAutomation.testCase.copy.confirm', { name: testCase.name }),
      t('uiAutomation.testCase.copy.title'),
      {
        confirmButtonText: t('uiAutomation.common.confirm'),
        cancelButtonText: t('uiAutomation.common.cancel'),
        type: 'info'
      }
    )

    const response = await copyTestCaseApi(testCase.id)
    ElMessage.success(t('uiAutomation.testCase.copy.success'))

    // 找到原用例的位置
    const index = testCases.value.findIndex(tc => tc.id === testCase.id)
    if (index !== -1) {
      // 在原用例下方插入新用例
      testCases.value.splice(index + 1, 0, response.data)
    } else {
      // 如果找不到，就添加到末尾
      testCases.value.push(response.data)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('复制测试用例失败:', error)
      ElMessage.error('复制失败')
    }
  }
}

// 加载变量函数
const loadVariableFunctions = async () => {
  try {
    loading.value = true
    console.log('开始加载变量函数...')
    const apiResponse = await getVariableFunctions()
    console.log('变量函数响应:', apiResponse)
    console.log('变量函数响应.data:', apiResponse.data)
    
    // 检查不同可能的数据结构
    let functionsData = []
    if (apiResponse && apiResponse.data) {
      if (Array.isArray(apiResponse.data)) {
        // 后端返回的是数组，直接使用
        functionsData = apiResponse.data
      } else if (apiResponse.data.functions) {
        // 如果data中有functions字段，使用它
        functionsData = apiResponse.data.functions
      } else if (typeof apiResponse.data === 'object') {
        // 如果data是对象但没有functions字段，假设整个对象就是按分类组织的函数
        functionsData = apiResponse.data
      }
    }
    
    console.log('处理后的函数数据:', functionsData)
    
    // 处理函数数据，按分类组织
    const grouped = {}
    
    if (Array.isArray(functionsData)) {
      // 如果是数组格式
      functionsData.forEach(func => {
        const category = func.category || '未分类'
        if (!grouped[category]) {
          grouped[category] = []
        }
        grouped[category].push({
          name: func.name,
          syntax: func.syntax,
          desc: func.description || func.desc || '',
          example: func.example
        })
      })
    } else if (typeof functionsData === 'object') {
      // 如果是按分类组织的对象格式
      for (const [category, funcs] of Object.entries(functionsData)) {
        if (Array.isArray(funcs)) {
          grouped[category] = funcs.map(func => ({
            name: func.name,
            syntax: func.syntax,
            desc: func.description || func.desc || '',
            example: func.example
          }))
        }
      }
    }
    
    console.log('按分类组织后的函数:', grouped)
    
    // 定义固定的分类顺序
    const categoryOrder = ['随机数', '测试数据', '字符串', '编码转换', '加密', '时间日期', 'Crontab', '未分类']
    
    // 按固定顺序构建分类列表
    const orderedCategories = []
    categoryOrder.forEach(category => {
      if (grouped[category]) {
        orderedCategories.push({
          label: category,
          variables: grouped[category]
        })
        delete grouped[category]
      }
    })
    
    // 添加剩余的分类
    for (const [category, funcs] of Object.entries(grouped)) {
      orderedCategories.push({
        label: category,
        variables: funcs
      })
    }
    
    console.log('最终的分类列表:', orderedCategories)
    variableCategories.value = orderedCategories
  } catch (error) {
    console.error('加载变量函数失败:', error)
    ElMessage.error('加载变量函数失败，使用本地数据')
    useLocalVariableCategories()
  } finally {
    loading.value = false
  }
}

// 使用本地变量分类数据作为 fallback
const useLocalVariableCategories = () => {
  variableCategories.value = [
    {
      label: t('uiAutomation.testCase.variableCategory.randomNumber'),
      variables: [
        { name: 'random_int', syntax: '${random_int(min, max, count)}', desc: t('uiAutomation.testCase.variable.randomInt.desc'), example: '${random_int(100, 999, 1)}' },
        { name: 'random_float', syntax: '${random_float(min, max, precision, count)}', desc: t('uiAutomation.testCase.variable.randomFloat.desc'), example: '${random_float(0, 1, 2, 1)}' }
      ]
    },
    {
      label: t('uiAutomation.testCase.variableCategory.randomString'),
      variables: [
        { name: 'random_string', syntax: '${random_string(length, char_type, count)}', desc: t('uiAutomation.testCase.variable.randomString.desc'), example: '${random_string(8, "all", 1)}' }
      ]
    }
  ]
}

// 计算属性提供变量分类数据
const variableCategoriesComputed = computed(() => {
  return variableCategories.value.length > 0 ? variableCategories.value : [
    {
      label: t('uiAutomation.testCase.variableCategory.randomNumber'),
      variables: []
    }
  ]
})

const openVariableHelper = (step, field) => {
  console.log('TestCaseManager openVariableHelper 被调用, step:', step, 'field:', field)
  console.log('variableCategories.value:', variableCategories.value)
  console.log('variableCategories.value.length:', variableCategories.value.length)
  currentEditingStep.value = step
  currentEditingField.value = field
  showVariableHelper.value = true
  console.log('showVariableHelper.value:', showVariableHelper.value)
}

const openDataFactorySelector = (step, field) => {
  currentStepForDataFactory.value = step
  currentFieldForDataFactory.value = field
  showDataFactorySelector.value = true
}

const handleDataFactorySelect = (record) => {
  const step = currentStepForDataFactory.value
  const field = currentFieldForDataFactory.value
  
  if (record && record.output_data && step && field) {
    let valueToSet = ''
    
    if (typeof record.output_data === 'string') {
      valueToSet = record.output_data
    } else if (record.output_data.result) {
      valueToSet = record.output_data.result
    } else if (record.output_data.output_data) {
      valueToSet = record.output_data.output_data
    } else {
      valueToSet = JSON.stringify(record.output_data)
    }
    
    step[field] = valueToSet
    ElMessage.success(t('uiAutomation.testCase.messages.dataFactorySelected', { toolName: record.tool_name }))
  }
  
  showDataFactorySelector.value = false
}

const insertVariable = (variable) => {
  if (currentEditingStep.value && currentEditingField.value) {
    const example = variable.example
    const currentValue = currentEditingStep.value[currentEditingField.value] || ''
    
    // 简单起见，这里直接追加到末尾，或者如果为空则替换
    if (!currentValue) {
      currentEditingStep.value[currentEditingField.value] = example
    } else {
      currentEditingStep.value[currentEditingField.value] = currentValue + example
    }
    
    ElMessage.success(t('uiAutomation.testCase.messages.variableInserted', { name: variable.name }))
    showVariableHelper.value = false
  }
}

const saveTestCaseForm = async () => {
  if (!testCaseForm.name.trim()) {
    ElMessage.warning(t('uiAutomation.testCase.form.nameRequired'))
    return
  }

  if (!editingTestCase.value && !ensureProjectSelected()) {
    return
  }

  try {
    const data = {
      name: testCaseForm.name,
      description: testCaseForm.description,
      priority: testCaseForm.priority,
      project: editingTestCase.value
        ? (resolveCaseProjectId(editingTestCase.value) || projectId.value)
        : projectId.value,
      steps: []
    }
    if (!data.project || data.project === ALL_PROJECTS) {
      ElMessage.warning(t('uiAutomation.common.selectSpecificProject'))
      return
    }

    if (editingTestCase.value) {
      // 编辑现有用例
      await updateTestCase(editingTestCase.value.id, data)
      ElMessage.success(t('uiAutomation.testCase.update.success'))

      // 更新本地数据
      const index = testCases.value.findIndex(tc => tc.id === editingTestCase.value.id)
      if (index !== -1) {
        testCases.value[index] = { ...testCases.value[index], ...data }
      }
    } else {
      // 创建新用例
      const response = await createTestCase(data)
      ElMessage.success(t('uiAutomation.testCase.create.success'))
      testCases.value.push(response.data)
    }

    showCreateDialog.value = false
    editingTestCase.value = null
    resetForm()
  } catch (error) {
    console.error('保存测试用例失败:', error)
    ElMessage.error(t('uiAutomation.testCase.save.failed'))
  }
}

const resetForm = () => {
  testCaseForm.name = ''
  testCaseForm.description = ''
  testCaseForm.priority = 'medium'
}

// 辅助方法
const getStatusTag = (status) => {
  const tagMap = {
    'draft': 'info',
    'ready': 'success',
    'running': 'warning',
    'passed': 'success',
    'failed': 'danger'
  }
  return tagMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'draft': t('uiAutomation.testCase.status.draft'),
    'ready': t('uiAutomation.testCase.status.ready'),
    'running': t('uiAutomation.testCase.status.running'),
    'passed': t('uiAutomation.testCase.status.passed'),
    'failed': t('uiAutomation.testCase.status.failed')
  }
  return textMap[status] || t('uiAutomation.testCase.status.unknown')
}

const getActionTypeText = (actionType) => {
  const textMap = {
    'click': t('uiAutomation.testCase.actionType.click'),
    'fill': t('uiAutomation.testCase.actionType.fill'),
    'getText': t('uiAutomation.testCase.actionType.getText'),
    'waitFor': t('uiAutomation.testCase.actionType.waitFor'),
    'hover': t('uiAutomation.testCase.actionType.hover'),
    'scroll': t('uiAutomation.testCase.actionType.scroll'),
    'screenshot': t('uiAutomation.testCase.actionType.screenshot'),
    'assert': t('uiAutomation.testCase.actionType.assert'),
    'wait': t('uiAutomation.testCase.actionType.wait'),
    'navigateUrl': t('uiAutomation.testCase.actionType.navigateUrl')
  }
  return textMap[actionType] || actionType
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString()
}

// 图片处理方法
const previewScreenshot = (screenshot) => {
  currentScreenshot.value = screenshot
  showScreenshotPreview.value = true
}

// 组件挂载
onMounted(async () => {
  console.log('TestCaseManager onMounted 开始执行...')
  await loadProjects()
  console.log('loadProjects 完成，准备加载变量函数...')
  await loadVariableFunctions()
  console.log('loadVariableFunctions 完成')

  projectId.value = ALL_PROJECTS
  await onProjectChange()
})

// 从元素管理改名返回后，刷新分组名/元素 page/步骤 page_filter
onActivated(async () => {
  if (!projectId.value) return
  await Promise.all([
    loadElements(),
    loadPageNames(),
    refreshSelectedTestCaseSteps()
  ])
})

onBeforeUnmount(() => {
  clearRecordPoll()
  stopPickElement()
})

const openCreateDialog = () => {
  if (!ensureProjectSelected()) return
  showCreateDialog.value = true
}
</script>

<style scoped>
.test-case-manager {
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
  width: 350px;
  border-right: 1px solid #e6e6e6;
  background: white;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.left-panel.collapsed {
  width: 44px;
  min-width: 44px;
}

.left-panel-collapsed {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12px;
}

.left-expand-btn {
  padding: 8px 4px !important;
  color: #606266;
}

.left-expand-btn:hover {
  color: #409eff;
}

.panel-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.panel-header {
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
}

.test-case-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.test-case-item {
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  margin-bottom: 10px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s;
}

.test-case-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.test-case-item.active {
  border-color: #409eff;
  background-color: #f0f8ff;
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}

.case-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-description {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.4;
  width: 100%;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  word-break: break-word;
}

.case-actions {
  display: flex;
  flex-shrink: 0;
  margin-left: auto;
  justify-content: flex-end;
  gap: 0.2ch;
}

.case-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.case-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #888;
}

.step-count {
  color: #409eff;
  font-weight: 500;
}

.create-time {
  margin-left: auto;
  text-align: right;
  white-space: nowrap;
}

.right-panel {
  flex: 1;
  background: white;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.result-side-panel {
  width: 340px;
  flex-shrink: 0;
  border-left: 1px solid #e6e6e6;
  background: #f7f8fa;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.picker-side-panel {
  width: 840px;
  flex-shrink: 0;
  border-left: 1px solid #e6e6e6;
  background: #f7f8fa;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.picker-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.picker-top-bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.picker-close-btn {
  padding: 4px !important;
  color: #909399;
  flex-shrink: 0;
}

.picker-close-btn:hover {
  color: #f56c6c;
}

.picker-screen-dock {
  margin-top: 0;
  display: flex;
  flex-direction: column;
  max-height: 72%;
  min-height: 280px;
  flex-shrink: 0;
  border-bottom: 1px solid #ebeef5;
  border-top: none;
  background: #fff;
}

.picker-side-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.picker-side-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.picker-side-title-row h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.picker-url-row {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.picker-screen-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #f5f7fa;
  cursor: default;
  outline: none;
}

.picker-screen-wrap.is-inspect {
  cursor: crosshair;
}

.picker-screen-wrap:not(.is-inspect) {
  cursor: pointer;
}

.picker-screen-loading {
  color: #909399;
  padding: 24px;
  text-align: center;
}

.picker-screen-frame {
  position: relative;
  display: block;
  width: 100%;
  line-height: 0;
}

.picker-screen-img {
  display: block;
  width: 100%;
  height: auto;
  user-select: none;
  vertical-align: top;
}

.picker-highlight {
  position: absolute;
  border: 2px solid #409eff;
  background: rgba(64, 158, 255, 0.15);
  pointer-events: none;
  box-sizing: border-box;
}

.picker-inspect-popup {
  position: absolute;
  right: 10px;
  top: 10px;
  width: 320px;
  max-height: calc(100% - 20px);
  overflow: auto;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  padding: 12px;
  z-index: 5;
}

.picker-inspect-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.picker-inspect-tag {
  color: #409eff;
  font-weight: 600;
  font-size: 14px;
}

.picker-inspect-class {
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
  word-break: break-all;
}

.picker-fill-all-btn {
  width: 100%;
  margin-bottom: 10px;
}

.picker-locator-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.picker-locator-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}

.picker-locator-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.picker-locator-strategy {
  font-size: 12px;
  color: #606266;
  font-weight: 600;
}

.picker-locator-value {
  font-size: 12px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-locator-actions {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
}

.picker-inspect-tip {
  margin-top: 10px;
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}

.result-side-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.result-side-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.result-side-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.result-side-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.result-close-btn {
  padding: 4px !important;
  color: #909399;
}

.result-side-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 16px 20px;
}

.result-side-section-title {
  font-size: 13px;
  color: #909399;
  margin: 4px 0 10px;
}

.result-side-logs {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  padding-left: 10px;
}

.result-side-logs::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: #c4b5fd;
  border-radius: 1px;
}

.result-log-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  border-left: 3px solid #67c23a;
  padding: 10px 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px;
}

.result-log-card.failed {
  border-left-color: #f56c6c;
}

.result-log-card.healed {
  border-left-color: #e6a23c;
  background: #fdf6ec;
}

.result-heal-banner {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid #f5dab1;
  background: #fdf6ec;
}

.result-heal-title {
  font-size: 13px;
  font-weight: 600;
  color: #b88230;
  margin-bottom: 8px;
}

.result-heal-item {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
  margin-top: 6px;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
}

.result-heal-step {
  flex-shrink: 0;
  font-weight: 600;
  color: #e6a23c;
}

.result-heal-reason {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.result-log-step {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #67c23a;
  background: #f0f9eb;
  padding: 2px 8px;
  border-radius: 4px;
  line-height: 1.5;
}

.result-log-step.failed {
  color: #f56c6c;
  background: #fef0f0;
}

.result-log-step.healed {
  color: #e6a23c;
  background: #fdf6ec;
}

.result-log-desc {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
  word-break: break-word;
}

.result-log-heal {
  width: 100%;
  margin-top: 4px;
  background: #fff7e6;
  border: 1px solid #f5dab1;
  border-radius: 4px;
  padding: 6px 8px;
}

.result-log-heal-label {
  font-size: 12px;
  font-weight: 600;
  color: #b88230;
  margin-bottom: 4px;
}

.result-log-heal pre {
  margin: 0;
  font-size: 12px;
  color: #8a6d3b;
  white-space: pre-wrap;
  word-break: break-word;
}

.result-log-heal-locator {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  word-break: break-all;
}

.result-log-error {
  width: 100%;
  margin-top: 4px;
  background: #fef0f0;
  border-radius: 4px;
  padding: 6px 8px;
}

.result-log-error pre {
  margin: 0;
  font-size: 12px;
  color: #f56c6c;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, Monaco, monospace;
}

.result-side-screenshots {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.result-shot-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  background: #fff;
}

.result-shot-item img {
  display: block;
  width: 100%;
  height: auto;
}

.result-side-errors {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-error-card {
  background: #fff;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  padding: 10px 12px;
}

.result-error-msg {
  font-size: 13px;
  color: #f56c6c;
  word-break: break-word;
}

.result-error-step {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.test-case-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: hidden;
  height: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e6e6e6;
}

.detail-header h3 {
  margin: 0;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.record-preview {
  margin-top: 12px;
}

.record-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 600;
}

.record-preview-shot {
  width: 40px;
  height: 40px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.record-preview-shot-empty {
  color: #c0c4cc;
}

.strategy-tag {
  margin-right: 6px;
}

.record-script-hint {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}

.record-auto-login-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 13px;
}

.steps-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin-bottom: 20px;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  background: #fafafa;
  overflow: hidden;
}

.steps-container.has-steps {
  max-height: 50%;
}

.steps-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.steps-header h4 {
  margin: 0;
}

.steps-list {
  padding: 10px;
  padding-bottom: 20px;
}

.steps-scroll-container {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  padding: 10px;
  padding-right: 5px;
}

.steps-scroll-container::-webkit-scrollbar {
  width: 6px;
}

.steps-scroll-container::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 3px;
}

.steps-scroll-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.steps-scroll-container::-webkit-scrollbar-thumb:hover {
  background: #999;
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
  padding-left: 11px;
  padding-right: 11px;
  width: 100%;
}

.step-desc-input :deep(.el-input__inner) {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  width: 100%;
}

.step-action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.step-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drag-handle {
  cursor: move;
  color: #999;
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
}

.step-right {
  display: flex;
  gap: 5px;
}

.step-content {
  padding: 15px;
  border-top: 1px solid #e6e6e6;
}

.step-param {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
}

.step-param label {
  width: 120px;
  flex-shrink: 0;
  font-weight: 500;
  color: #333;
  line-height: 24px;
}

.step-element-shot,
.step-backup-block {
  align-items: flex-start;
}

.step-element-shot .element-shot-box {
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
  --el-button-hover-bg-color: #6d28d9;
  --el-button-hover-border-color: #6d28d9;
  --el-button-hover-text-color: #fff;
  --el-button-active-bg-color: #5b21b6;
  --el-button-active-border-color: #5b21b6;
}

/* 截图预览对话框样式 */
.screenshot-preview {
  display: flex;
  flex-direction: column;
}

.preview-info {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
}

.preview-info h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.preview-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #666;
}

.preview-image {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
  max-height: 70vh;
  overflow: auto;
}

.preview-image img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.data-factory-btn {
  background-color: #409eff !important;
  border-color: #409eff !important;
  color: white !important;
}

.data-factory-btn:hover {
  background-color: #66b1ff !important;
  border-color: #66b1ff !important;
}

.variable-helper-btn {
  background-color: #67c23a;
  border-color: #67c23a;
  color: white;
}

.variable-helper-btn:hover {
  background-color: #5daf34;
  border-color: #5daf34;
}
</style>