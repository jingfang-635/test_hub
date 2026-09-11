<template>
  <div class="automation-testing">
    <div class="header">
      <h3>{{ $t('apiTesting.automation.title') }}</h3>
      <el-button type="primary" @click="openCreateSuiteDialog">
        <el-icon><Plus /></el-icon>
        {{ $t('apiTesting.automation.createSuite') }}
      </el-button>
    </div>

    <div class="content-layout">
      <!-- 左侧项目选择和测试套件列表 -->
      <div class="sidebar">
        <div class="project-selector">
          <el-select
            v-model="selectedProject"
            :placeholder="$t('apiTesting.common.selectProject')"
            @change="onProjectChange"
            style="width: 100%;"
          >
            <el-option :label="$t('apiTesting.common.allProjects')" value="all" />
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </div>
        
        <div class="suite-list">
          <div class="list-header">
            <span>{{ $t('apiTesting.automation.testSuites') }}</span>
            <el-button size="small" text @click="loadTestSuites">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          
          <el-scrollbar height="400px">
            <div
              v-for="suite in testSuites"
              :key="suite.id"
              class="suite-item"
              :class="{ active: selectedSuite?.id === suite.id }"
              @click="selectSuite(suite)"
            >
              <div class="suite-info">
                <div class="suite-name">{{ suite.name }}</div>
                <div class="suite-meta">
                  <template v-if="isAllProjectsSelected() && suite.project_name">
                    {{ suite.project_name }} ·
                  </template>
                  {{ $t('apiTesting.automation.requestCount', { n: suite.suite_requests?.length || 0 }) }}
                </div>
              </div>
              <el-dropdown @command="handleSuiteAction" trigger="click">
                <el-button size="small" text>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'run', suite }">{{ $t('apiTesting.automation.run') }}</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'edit', suite }">{{ $t('apiTesting.common.edit') }}</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'duplicate', suite }">{{ $t('apiTesting.common.copy') }}</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', suite }" divided>{{ $t('apiTesting.common.delete') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </el-scrollbar>
        </div>
      </div>

      <!-- 右侧测试套件详情 -->
      <div class="main-content">
        <div v-if="!selectedSuite" class="empty-state">
          <el-empty :description="$t('apiTesting.automation.selectSuiteHint')" />
        </div>
        
        <div v-else class="suite-detail">
          <!-- 套件信息 -->
          <div class="suite-header">
            <div class="suite-title">
              <h4>{{ selectedSuite.name }}</h4>
              <div class="suite-actions">
                <el-button type="success" @click="runTestSuite(selectedSuite)" :loading="running">
                  <el-icon><VideoPlay /></el-icon>
                  {{ $t('apiTesting.automation.runTest') }}
                </el-button>
                <el-button @click="editSuite(selectedSuite)">
                  <el-icon><Edit /></el-icon>
                  {{ $t('apiTesting.common.edit') }}
                </el-button>
              </div>
            </div>
            <div class="suite-description">
              {{ selectedSuite.description || $t('apiTesting.automation.noDescription') }}
            </div>
            <div class="suite-meta">
              <el-tag size="small">{{ getEnvironmentName(selectedSuite.environment) }}</el-tag>
            </div>
          </div>

          <!-- 请求列表 -->
          <div class="requests-section">
            <div class="section-header">
              <h5>{{ $t('apiTesting.automation.testRequests') }}</h5>
              <el-button size="small" @click="showAddRequest">
                <el-icon><Plus /></el-icon>
                {{ $t('apiTesting.automation.addRequest') }}
              </el-button>
            </div>
            
            <el-table :data="selectedSuite.suite_requests" style="width: 100%">
              <el-table-column type="index" width="50" />
              <el-table-column prop="request.name" :label="$t('apiTesting.automation.requestName')" min-width="160" />
              <el-table-column prop="request.method" :label="$t('apiTesting.automation.method')" width="80">
                <template #default="scope">
                  <el-tag :type="getMethodType(scope.row.request.method)" size="small">
                    {{ scope.row.request.method }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="request.url" label="URL" min-width="220" show-overflow-tooltip />
              <el-table-column prop="enabled" :label="$t('apiTesting.automation.enabled')" width="80">
                <template #default="scope">
                  <el-switch
                    v-model="scope.row.enabled"
                    @change="updateRequestEnabled(scope.row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.skipCondition')" min-width="160" show-overflow-tooltip>
                <template #default="scope">
                  <span class="skip-condition-text">{{ scope.row.skip_condition || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.variableExtraction')" width="100">
                <template #default="scope">
                  {{ getExtractorCount(scope.row) }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.assertions')" width="80">
                <template #default="scope">
                  {{ scope.row.assertions?.length || 0 }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.common.operation')" width="220" align="center" fixed="right">
                <template #default="scope">
                  <el-button
                    class="request-op-btn"
                    link
                    type="primary"
                    size="small"
                    :disabled="scope.$index === 0 || movingRequestOrder"
                    :title="$t('apiTesting.automation.moveUp')"
                    @click="moveRequest(scope.$index, 'up')"
                  >
                    <el-icon><Top /></el-icon>
                  </el-button>
                  <el-button
                    class="request-op-btn"
                    link
                    type="primary"
                    size="small"
                    :disabled="scope.$index === selectedSuite.suite_requests.length - 1 || movingRequestOrder"
                    :title="$t('apiTesting.automation.moveDown')"
                    @click="moveRequest(scope.$index, 'down')"
                  >
                    <el-icon><Bottom /></el-icon>
                  </el-button>
                  <el-button
                    class="request-op-btn"
                    link
                    type="primary"
                    @click="openRequestConfig(scope.row)"
                    size="small"
                  >
                    {{ $t('apiTesting.automation.configure') }}
                  </el-button>
                  <el-button link type="danger" @click="removeRequest(scope.row)" size="small">
                    {{ $t('apiTesting.automation.remove') }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 执行历史 -->
          <div class="executions-section">
            <div class="section-header">
              <h5>{{ $t('apiTesting.automation.executionHistory') }}</h5>
              <el-button size="small" @click="loadExecutions">
                <el-icon><Refresh /></el-icon>
                {{ $t('apiTesting.automation.refresh') }}
              </el-button>
            </div>

            <el-table :data="executions" v-loading="executionsLoading" style="width: 100%">
              <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="100">
                <template #default="scope">
                  <el-tag :type="getStatusType(scope.row.status)">
                    {{ getStatusText(scope.row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="total_requests" :label="$t('apiTesting.automation.totalRequests')" min-width="100" />
              <el-table-column prop="passed_requests" :label="$t('apiTesting.automation.passedCount')" min-width="100">
                <template #default="scope">
                  <span style="color: #67c23a">{{ scope.row.passed_requests }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="failed_requests" :label="$t('apiTesting.automation.failedCount')" min-width="100">
                <template #default="scope">
                  <span style="color: #f56c6c">{{ scope.row.failed_requests }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.averageTime')" min-width="120">
                <template #default="scope">
                  {{ getAverageExecutionTime(scope.row) }}
                </template>
              </el-table-column>
              <el-table-column prop="executed_by.username" :label="$t('apiTesting.automation.executor')" min-width="120" />
              <el-table-column prop="created_at" :label="$t('apiTesting.automation.executionTime')" min-width="160">
                <template #default="scope">
                  {{ formatDate(scope.row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.common.operation')" width="120">
                <template #default="scope">
                  <el-button link type="primary" @click="viewExecutionDetail(scope.row)" size="small">
                    {{ $t('apiTesting.automation.viewDetails') }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑测试套件对话框 -->
    <el-dialog
      v-model="showCreateSuiteDialog"
      :title="editingSuite ? $t('apiTesting.automation.editSuite') : $t('apiTesting.automation.createSuite')"
      width="600px"
      :close-on-click-modal="false"
      @close="resetSuiteForm"
    >
      <el-form
        ref="suiteFormRef"
        :model="suiteForm"
        :rules="suiteRules"
        label-width="100px"
      >
        <el-form-item :label="$t('apiTesting.automation.suiteName')" prop="name">
          <el-input v-model="suiteForm.name" :placeholder="$t('apiTesting.automation.inputSuiteName')" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.suiteDescription')" prop="description">
          <el-input
            v-model="suiteForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('apiTesting.automation.inputSuiteDescription')"
          />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.belongProject')" prop="project">
          <el-select v-model="suiteForm.project" :placeholder="$t('apiTesting.automation.selectProject')">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.executionEnvironment')" prop="environment">
          <el-select v-model="suiteForm.environment" :placeholder="$t('apiTesting.automation.selectEnvironment')" clearable>
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateSuiteDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitSuiteForm" :loading="submittingSuite">
          {{ editingSuite ? $t('apiTesting.common.update') : $t('apiTesting.common.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加请求对话框 -->
    <el-dialog
      v-model="showAddRequestDialog"
      :title="$t('apiTesting.automation.addRequestToSuite')"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="add-request-content">
        <div class="request-selector">
          <el-tree
            ref="requestTreeRef"
            :data="requestTree"
            :props="requestTreeProps"
            show-checkbox
            node-key="id"
            :check-on-click-node="false"
            @check="onRequestCheck"
          >
            <template #default="{ node, data }">
              <div class="request-tree-node">
                <el-icon v-if="data.type === 'collection'">
                  <Folder />
                </el-icon>
                <el-icon v-else>
                  <Document />
                </el-icon>
                <span>{{ data.name }}</span>
                <span v-if="data.type === 'request'" class="method-tag" :class="data.method?.toLowerCase()">
                  {{ data.method }}
                </span>
              </div>
            </template>
          </el-tree>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showAddRequestDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="addSelectedRequests" :loading="addingRequests">
          {{ $t('apiTesting.automation.addSelectedRequests') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行结果对话框 -->
    <el-dialog
      v-model="showExecutionDialog"
      :title="$t('apiTesting.automation.testExecutionResult')"
      width="80%"
      :top="'5vh'"
    >
      <div v-if="currentExecution" class="execution-detail">
        <div class="execution-summary">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.totalRequests')" :value="currentExecution.total_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.passedCount')" :value="currentExecution.passed_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.failedCount')" :value="currentExecution.failed_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.passRate')" :value="getPassRate(currentExecution)" suffix="%" />
            </el-col>
          </el-row>
        </div>

        <div class="execution-results">
          <h4>{{ $t('apiTesting.automation.detailedResults') }}</h4>
          <el-table :data="formatExecutionResults(currentExecution.results)">
            <el-table-column prop="name" :label="$t('apiTesting.automation.requestName')" min-width="200" />
            <el-table-column prop="method" :label="$t('apiTesting.automation.method')" width="80">
              <template #default="scope">
                <el-tag :type="getMethodType(scope.row.method)" size="small">
                  {{ scope.row.method }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('apiTesting.automation.result')" width="100">
              <template #default="scope">
                <el-tag v-if="scope.row.skipped" type="info" size="small">
                  {{ $t('apiTesting.automation.status.skipped') }}
                </el-tag>
                <el-tag v-else :type="scope.row.passed ? 'success' : 'danger'" size="small">
                  {{ scope.row.passed ? $t('apiTesting.automation.status.passed') : $t('apiTesting.automation.status.failed') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status_code" :label="$t('apiTesting.automation.statusCode')" width="100" />
            <el-table-column prop="response_time" :label="$t('apiTesting.automation.responseTime')" width="120">
              <template #default="scope">
                {{ scope.row.response_time?.toFixed(0) }}ms
              </template>
            </el-table-column>
            <el-table-column prop="error" :label="$t('apiTesting.automation.errorMessage')" min-width="200" show-overflow-tooltip />
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button
          v-if="currentExecution?.report_url"
          type="primary"
          @click="openAllureReport(currentExecution.report_url)"
        >
          {{ $t('apiTesting.automation.viewAllureReport') }}
        </el-button>
        <el-button @click="showExecutionDialog = false">{{ $t('apiTesting.common.close') }}</el-button>
      </template>
    </el-dialog>

    <!-- 请求配置对话框 -->
    <el-dialog
      v-model="showRequestConfigDialog"
      :title="$t('apiTesting.automation.requestConfig')"
      width="920px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-tabs v-model="requestConfigTab">
        <el-tab-pane :label="$t('apiTesting.automation.skipCondition')" name="skip">
          <el-form label-position="top">
            <el-form-item :label="$t('apiTesting.automation.skipCondition')">
              <el-input
                v-model="requestConfigForm.skip_condition"
                type="textarea"
                :rows="5"
                :placeholder="$t('apiTesting.automation.skipConditionPlaceholder')"
              />
            </el-form-item>
            <el-alert
              type="info"
              :closable="false"
              show-icon
              class="skip-help-alert"
            >
              <template #title>
                <div class="skip-help">
                  <p>{{ $t('apiTesting.automation.skipConditionHelp') }}</p>
                  <ul>
                    <li><code>variables.get("env") == "dev"</code></li>
                    <li><code>variables.get("skip_flag") == True</code></li>
                    <li><code>variables.get("count", 0) &gt; 10</code></li>
                  </ul>
                </div>
              </template>
            </el-alert>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="$t('apiTesting.automation.variableExtraction')" name="extractors">
          <div class="config-list-header">
            <span>{{ $t('apiTesting.automation.variableExtraction') }}</span>
            <div class="config-list-actions">
              <el-button
                size="small"
                type="success"
                :loading="syncingExtractors"
                @click="syncExtractorsFromInterface"
              >
                {{ $t('apiTesting.automation.syncInterfaceData') }}
              </el-button>
              <el-button size="small" type="primary" @click="addConfigExtractor">
                <el-icon><Plus /></el-icon>
                {{ $t('apiTesting.automation.add') }}
              </el-button>
            </div>
          </div>

          <div
            v-for="(extractor, index) in requestConfigForm.extractors"
            :key="'ext-' + index"
            class="extractor-config-item"
          >
            <div class="extractor-config-row">
              <el-input
                v-model="extractor.variable"
                size="small"
                class="extractor-field-variable"
                :placeholder="$t('apiTesting.interface.extractorVariablePlaceholder')"
              />
              <el-select v-model="extractor.source" size="small" class="extractor-field-source">
                <el-option :label="$t('apiTesting.interface.extractorSources.body')" value="body" />
                <el-option :label="$t('apiTesting.interface.extractorSources.headers')" value="headers" />
              </el-select>
              <el-select v-model="extractor.type" size="small" class="extractor-field-type">
                <el-option :label="$t('apiTesting.interface.extractorTypes.jsonpath')" value="jsonpath" />
                <el-option :label="$t('apiTesting.interface.extractorTypes.regex')" value="regex" />
              </el-select>
              <div class="extractor-field-expression">
                <el-input
                  v-model="extractor.expression"
                  size="small"
                  :placeholder="extractor.type === 'regex'
                    ? $t('apiTesting.interface.extractorRegexPlaceholder')
                    : $t('apiTesting.interface.extractorJsonPathPlaceholder')"
                />
                <div class="extractor-expression-hint">
                  {{ extractor.type === 'regex'
                    ? $t('apiTesting.automation.extractorRegexHint')
                    : $t('apiTesting.automation.extractorJsonPathHint') }}
                </div>
              </div>
              <el-input
                v-model="extractor.default_value"
                size="small"
                class="extractor-field-default"
                :placeholder="$t('apiTesting.interface.extractorDefaultValue')"
              />
              <el-button
                type="danger"
                circle
                size="small"
                @click="requestConfigForm.extractors.splice(index, 1)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>

          <el-empty
            v-if="!requestConfigForm.extractors.length"
            :description="$t('apiTesting.automation.noSuiteExtractors')"
            :image-size="60"
          />

          <div class="extractor-help">
            <div class="extractor-help-header" @click="extractorHelpExpanded = !extractorHelpExpanded">
              <span>{{ $t('apiTesting.interface.extractorHelpTitle') }}</span>
              <el-icon class="extractor-help-arrow" :class="{ expanded: extractorHelpExpanded }">
                <ArrowRight />
              </el-icon>
            </div>
            <div v-show="extractorHelpExpanded" class="extractor-help-body">
              <p>{{ $t('apiTesting.automation.suiteExtractorHelp') }}</p>
              <ul>
                <li>{{ $t('apiTesting.automation.suiteExtractorHelpSync') }}</li>
                <li>{{ $t('apiTesting.automation.suiteExtractorHelpAdd') }}</li>
                <li>{{ $t('apiTesting.automation.suiteExtractorHelpScope') }}</li>
              </ul>
              <p>{{ $t('apiTesting.interface.extractorHelpJsonPathDesc') }}</p>
              <ul>
                <li><code>$.data.token</code></li>
                <li><code>$.items[0].id</code></li>
                <li><code>$.users[*].name</code></li>
              </ul>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="$t('apiTesting.automation.assertionConfig')" name="assertions">
          <div class="config-list-header">
            <div class="config-list-actions">
              <el-button
                size="small"
                type="success"
                :loading="syncingAssertions"
                @click="syncAssertionsFromInterface"
              >
                {{ $t('apiTesting.automation.syncInterfaceData') }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                link
                :disabled="!requestConfigForm.assertions.length"
                @click="clearConfigAssertions"
              >
                {{ $t('apiTesting.automation.clearAssertions') }}
              </el-button>
            </div>
          </div>

          <div
            v-for="(assertion, index) in requestConfigForm.assertions"
            :key="'ast-' + index"
            class="assertion-config-item"
          >
            <div class="assertion-config-top">
              <el-input
                v-model="assertion.name"
                size="small"
                class="assertion-field-name"
                :placeholder="$t('apiTesting.interface.assertionName')"
              />
              <el-select
                v-model="assertion.type"
                size="small"
                class="assertion-field-type"
                @change="onConfigAssertionTypeChange(assertion)"
              >
                <el-option :label="$t('apiTesting.interface.assertionTypes.statusCode')" value="status_code" />
                <el-option :label="$t('apiTesting.interface.assertionTypes.responseTime')" value="response_time" />
                <el-option :label="$t('apiTesting.interface.assertionTypes.contains')" value="contains" />
                <el-option :label="$t('apiTesting.interface.assertionTypes.jsonPath')" value="json_path" />
                <el-option :label="$t('apiTesting.interface.assertionTypes.header')" value="header" />
                <el-option :label="$t('apiTesting.interface.assertionTypes.equals')" value="equals" />
              </el-select>
              <el-input
                v-if="assertion.type === 'json_path'"
                v-model="assertion.json_path"
                size="small"
                class="assertion-field-extra"
                :placeholder="$t('apiTesting.interface.jsonPathExample')"
              />
              <el-input
                v-else-if="assertion.type === 'header'"
                v-model="assertion.header_name"
                size="small"
                class="assertion-field-extra"
                :placeholder="$t('apiTesting.interface.headerNameLabel')"
              />
              <el-input
                v-model="assertion.expected"
                size="small"
                class="assertion-field-expected"
                :placeholder="getAssertionExpectedPlaceholder(assertion.type)"
              />
              <el-button
                type="danger"
                circle
                size="small"
                class="assertion-delete-btn"
                @click="requestConfigForm.assertions.splice(index, 1)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>

          <el-empty
            v-if="!requestConfigForm.assertions.length"
            :description="$t('apiTesting.automation.noSuiteAssertions')"
            :image-size="60"
          />

          <el-button class="add-assertion-btn" type="primary" @click="addConfigAssertion">
            <el-icon><Plus /></el-icon>
            {{ $t('apiTesting.automation.addAssertion') }}
          </el-button>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="showRequestConfigDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" :loading="savingRequestConfig" @click="saveRequestConfig">
          {{ $t('apiTesting.common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Plus, Refresh, MoreFilled, VideoPlay, Edit,
  Folder, Document, Delete, ArrowRight, Top, Bottom
} from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()

const projects = ref([])
const ALL_PROJECTS = 'all'
const selectedProject = ref(ALL_PROJECTS)
const isAllProjectsSelected = () => selectedProject.value === ALL_PROJECTS || selectedProject.value === ''
/** 列表查询参数：全部项目不传 project */
const getProjectQueryParams = () => (
  isAllProjectsSelected() ? {} : { project: selectedProject.value }
)
const testSuites = ref([])
const selectedSuite = ref(null)
const executions = ref([])
const environments = ref([])
const requestTree = ref([])
const running = ref(false)
const executionsLoading = ref(false)
const showCreateSuiteDialog = ref(false)
const showAddRequestDialog = ref(false)
const showExecutionDialog = ref(false)
const showRequestConfigDialog = ref(false)
const editingSuite = ref(null)
const submittingSuite = ref(false)
const addingRequests = ref(false)
const movingRequestOrder = ref(false)
const savingRequestConfig = ref(false)
const syncingExtractors = ref(false)
const syncingAssertions = ref(false)
const extractorHelpExpanded = ref(false)
const currentExecution = ref(null)
const currentConfigRequest = ref(null)
const requestConfigTab = ref('skip')
const suiteFormRef = ref()
const requestTreeRef = ref()

const requestConfigForm = reactive({
  skip_condition: '',
  extractors: [],
  assertions: []
})

const suiteForm = reactive({
  name: '',
  description: '',
  project: null,
  environment: null
})

const suiteRules = computed(() => ({
  name: [{ required: true, message: t('apiTesting.automation.inputSuiteName'), trigger: 'blur' }],
  project: [{ required: true, message: t('apiTesting.automation.selectProject'), trigger: 'change' }]
}))

const requestTreeProps = {
  children: 'children',
  label: 'name'
}

const getMethodType = (method) => {
  const typeMap = {
    'GET': 'success',
    'POST': 'primary',
    'PUT': 'warning', 
    'DELETE': 'danger',
    'PATCH': 'info'
  }
  return typeMap[method] || 'info'
}

const getStatusType = (status) => {
  const typeMap = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusKey = {
    'PENDING': 'pending',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled'
  }[status]
  return statusKey ? t(`apiTesting.automation.status.${statusKey}`) : status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const getExecutionTime = (execution) => {
  if (!execution.start_time || !execution.end_time) return '-'
  const start = dayjs(execution.start_time)
  const end = dayjs(execution.end_time)
  return `${end.diff(start, 'second')}s`
}

const getAverageExecutionTime = (execution) => {
  if (!execution.results || !Array.isArray(execution.results) || execution.results.length === 0) {
    return '-'
  }
  
  // 计算所有请求的平均响应时间
  const totalResponseTime = execution.results.reduce((sum, result) => sum + (result.response_time || 0), 0)
  const averageTime = totalResponseTime / execution.results.length
  
  if (averageTime < 1000) {
    return `${Math.round(averageTime)}ms`
  } else {
    return `${(averageTime / 1000).toFixed(1)}s`
  }
}

const getPassRate = (execution) => {
  if (execution.total_requests === 0) return 0
  return ((execution.passed_requests / execution.total_requests) * 100).toFixed(1)
}

const getEnvironmentName = (environmentId) => {
  if (!environmentId) return t('apiTesting.automation.noEnvironment')
  const env = environments.value.find(e => e.id == environmentId)
  return env ? env.name : t('apiTesting.automation.noEnvironment')
}

const loadProjects = async () => {
  try {
    // 与「项目与版本」一致：仅展示已勾选 API测试 的主项目
    const response = await api.get('/projects/', {
      params: {
        project_type: 'api_testing',
        page_size: 100
      }
    })
    const hubs = response.data.results || response.data || []
    if (!hubs.length) {
      projects.value = []
      selectedProject.value = null
      selectedSuite.value = null
      testSuites.value = []
      ElMessage.warning('暂无关联 API测试 的项目，请先在「项目与版本」中创建并勾选 API测试')
      return
    }

    const mapped = []
    for (const hub of hubs) {
      try {
        const res = await api.post('/api-testing/projects/ensure/', {
          hub_project_id: hub.id
        })
        const apiProject = res.data
        if (apiProject?.id && apiProject.project_type !== 'WEBSOCKET') {
          mapped.push({
            ...apiProject,
            name: hub.name || apiProject.name,
            hub_project_id: hub.id
          })
        }
      } catch (error) {
        console.error('关联 API 项目失败:', hub.id, error)
      }
    }

    projects.value = mapped

    if (mapped.length > 0) {
      // 默认「全部项目」；若已选具体项目且仍有效则保留
      const stillValid = selectedProject.value === ALL_PROJECTS
        || mapped.some(p => p.id === selectedProject.value)
      if (!stillValid) {
        selectedProject.value = ALL_PROJECTS
      }
      await onProjectChange()
    } else {
      selectedProject.value = null
      selectedSuite.value = null
      testSuites.value = []
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadProjects'))
  }
}

const loadTestSuites = async () => {
  if (!selectedProject.value) return

  try {
    const response = await api.get('/api-testing/test-suites/', {
      params: getProjectQueryParams()
    })
    testSuites.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadTestSuites'))
  }
}

const loadEnvironments = async () => {
  try {
    // 获取全局环境 + 当前项目环境
    const response = await api.get('/api-testing/environments/', {
      // 不传递project参数，让后端返回所有可访问的环境（全局+当前项目）
    })
    const allEnvironments = response.data.results || response.data

    if (isAllProjectsSelected()) {
      environments.value = allEnvironments
    } else {
      // 过滤当前项目相关或全局环境
      environments.value = allEnvironments.filter(env =>
        env.scope === 'GLOBAL' ||
        (env.scope === 'LOCAL' && env.project == selectedProject.value)
      )
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadEnvironments'))
  }
}

const loadRequestTree = async () => {
  // 全部项目模式下，按当前套件所属项目加载接口树
  let projectId = selectedProject.value
  if (isAllProjectsSelected()) {
    projectId = selectedSuite.value?.project
  }
  if (projectId == null || projectId === '' || projectId === 'undefined' || projectId === 'null' || projectId === ALL_PROJECTS) {
    requestTree.value = []
    return
  }

  try {
    // 加载集合
    const collectionsRes = await api.get('/api-testing/collections/', {
      params: { project: projectId }
    })
    const collections = collectionsRes.data.results || collectionsRes.data

    // 加载请求
    const requestsRes = await api.get('/api-testing/requests/', {
      params: { project: projectId }
    })
    const requests = requestsRes.data.results || requestsRes.data

    // 构建树形结构
    requestTree.value = buildRequestTree(collections, requests)
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadRequestTree'))
  }
}

const buildRequestTree = (collections, requests) => {
  const map = {}
  const roots = []
  
  // 创建集合节点
  collections.forEach(collection => {
    map[collection.id] = {
      ...collection,
      type: 'collection',
      children: []
    }
  })
  
  // 构建集合层级关系
  collections.forEach(collection => {
    if (collection.parent && map[collection.parent]) {
      map[collection.parent].children.push(map[collection.id])
    } else {
      roots.push(map[collection.id])
    }
  })
  
  // 添加请求到对应集合
  requests.forEach(request => {
    if (map[request.collection]) {
      map[request.collection].children.push({
        ...request,
        type: 'request',
        id: `request_${request.id}`
      })
    }
  })
  
  return roots
}

const loadExecutions = async () => {
  if (!selectedSuite.value) return

  executionsLoading.value = true
  try {
    const response = await api.get('/api-testing/test-executions/', {
      params: { test_suite: selectedSuite.value.id }
    })
    executions.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadExecutionHistory'))
  } finally {
    executionsLoading.value = false
  }
}

const onProjectChange = async () => {
  if (!selectedProject.value) {
    selectedSuite.value = null
    testSuites.value = []
    return
  }

  selectedSuite.value = null
  await Promise.all([
    loadTestSuites(),
    loadEnvironments()
  ])
}

const selectSuite = (suite) => {
  selectedSuite.value = suite
  loadExecutions()
}

const handleSuiteAction = async ({ action, suite }) => {
  switch (action) {
    case 'run':
      await runTestSuite(suite)
      break
    case 'edit':
      editSuite(suite)
      break
    case 'duplicate':
      await duplicateSuite(suite)
      break
    case 'delete':
      await deleteSuite(suite)
      break
  }
}

const runTestSuite = async (suite) => {
  running.value = true
  try {
    const response = await api.post(`/api-testing/test-suites/${suite.id}/execute/`)
    currentExecution.value = response.data
    showExecutionDialog.value = true
    await loadExecutions()
    ElMessage.success(t('apiTesting.messages.success.suiteExecuted'))
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.executeSuite'))
  } finally {
    running.value = false
  }
}

const editSuite = (suite) => {
  editingSuite.value = suite
  suiteForm.name = suite.name
  suiteForm.description = suite.description
  suiteForm.project = suite.project
  // 修复：environment字段直接是ID，不需要?.id
  suiteForm.environment = suite.environment || null
  showCreateSuiteDialog.value = true
}

const duplicateSuite = async (suite) => {
  try {
    const newSuite = {
      name: `${suite.name}（副本）`,
      description: suite.description,
      project: suite.project,
      environment: suite.environment || null
    }
    await api.post('/api-testing/test-suites/', newSuite)
    ElMessage.success(t('apiTesting.messages.success.copy'))
    await loadTestSuites()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.copyFailed'))
  }
}

const deleteSuite = async (suite) => {
  try {
    await ElMessageBox.confirm(
      t('apiTesting.automation.confirmDeleteSuite', { name: suite.name }),
      t('apiTesting.messages.confirm.deleteTitle'),
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/api-testing/test-suites/${suite.id}/`)
    ElMessage.success(t('apiTesting.messages.success.delete'))

    if (selectedSuite.value?.id === suite.id) {
      selectedSuite.value = null
    }
    await loadTestSuites()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.deleteFailed'))
    }
  }
}

const submitSuiteForm = async () => {
  if (!suiteFormRef.value) return

  const valid = await suiteFormRef.value.validate().catch(() => false)
  if (!valid) return

  submittingSuite.value = true
  try {
    const payload = {
      name: suiteForm.name,
      description: suiteForm.description,
      project: suiteForm.project,
      environment: suiteForm.environment || null
    }
    const editingId = editingSuite.value?.id

    if (editingId) {
      await api.put(`/api-testing/test-suites/${editingId}/`, payload)
      ElMessage.success(t('apiTesting.messages.success.save'))
    } else {
      await api.post('/api-testing/test-suites/', payload)
      ElMessage.success(t('apiTesting.messages.success.create'))
    }

    showCreateSuiteDialog.value = false
    await loadTestSuites()

    // 保存后同步刷新当前选中套件，确保环境变更立即生效
    if (editingId && selectedSuite.value?.id === editingId) {
      const updated = testSuites.value.find(s => s.id === editingId)
      if (updated) {
        selectedSuite.value = { ...updated }
      } else {
        await reloadCurrentSuite()
      }
    }
  } catch (error) {
    ElMessage.error(editingSuite.value ? t('apiTesting.messages.error.updateFailed') : t('apiTesting.messages.error.createFailed'))
  } finally {
    submittingSuite.value = false
  }
}

const resetSuiteForm = () => {
  editingSuite.value = null
  Object.assign(suiteForm, {
    name: '',
    description: '',
    // 全部项目模式下不预填，需用户手动选择
    project: isAllProjectsSelected() ? null : selectedProject.value,
    environment: null
  })
  suiteFormRef.value?.resetFields()
}

const openCreateSuiteDialog = () => {
  resetSuiteForm()
  showCreateSuiteDialog.value = true
}

const showAddRequest = async () => {
  await loadRequestTree()
  showAddRequestDialog.value = true
  
  // 等待对话框显示完成后再设置勾选状态
  nextTick(() => {
    setTimeout(() => {
      if (requestTreeRef.value && selectedSuite.value) {
        // 获取当前已关联的请求ID
        const existingRequestIds = selectedSuite.value.suite_requests?.map(sr => 
          `request_${sr.request.id}`
        ) || []
        
        // 设置已关联接口为已勾选状态
        requestTreeRef.value.setCheckedKeys(existingRequestIds, false)
        console.log('设置已关联接口ID:', existingRequestIds)
      }
    }, 200)
  })
}

const onRequestCheck = () => {
  // 请求选择变化处理
}

const addSelectedRequests = async () => {
  const checkedNodes = requestTreeRef.value.getCheckedNodes()
  const requestIds = checkedNodes
    .filter(node => node.type === 'request')
    .map(node => node.id.replace('request_', ''))

  if (requestIds.length === 0) {
    ElMessage.warning(t('apiTesting.messages.warning.selectAtLeastOneRequest'))
    return
  }

  addingRequests.value = true
  try {
    // 这里需要调用添加请求到套件的API
    await api.post(`/api-testing/test-suites/${selectedSuite.value.id}/add-requests/`, {
      request_ids: requestIds
    })

    ElMessage.success(t('apiTesting.messages.success.addSuccess'))
    showAddRequestDialog.value = false
    // 重新加载当前测试套件详情
    await reloadCurrentSuite()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.addFailed'))
  } finally {
    addingRequests.value = false
  }
}

const updateRequestEnabled = async (suiteRequest) => {
  try {
    await api.put(`/api-testing/test-suite-requests/${suiteRequest.id}/`, {
      enabled: suiteRequest.enabled
    })
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed'))
    suiteRequest.enabled = !suiteRequest.enabled
  }
}

const getExtractorCount = (suiteRequest) => {
  // 仅统计套件级变量提取（对当前套件生效）
  return suiteRequest?.extractors?.length || 0
}

const openRequestConfig = (suiteRequest) => {
  currentConfigRequest.value = suiteRequest
  requestConfigTab.value = 'skip'
  extractorHelpExpanded.value = false
  requestConfigForm.skip_condition = suiteRequest.skip_condition || ''
  // 只加载套件自身配置，不自动带入接口提取器（需点「同步接口数据」）
  requestConfigForm.extractors = JSON.parse(JSON.stringify(suiteRequest.extractors || []))
  requestConfigForm.assertions = JSON.parse(JSON.stringify(suiteRequest.assertions || []))
  showRequestConfigDialog.value = true
}

const addConfigExtractor = () => {
  requestConfigForm.extractors.push({
    variable: '',
    source: 'body',
    type: 'jsonpath',
    expression: '',
    default_value: ''
  })
}

const syncExtractorsFromInterface = async () => {
  const requestId = currentConfigRequest.value?.request?.id
  if (!requestId) {
    ElMessage.warning(t('apiTesting.automation.syncInterfaceMissing'))
    return
  }

  syncingExtractors.value = true
  try {
    const { data } = await api.get(`/api-testing/requests/${requestId}/`)
    const interfaceExtractors = Array.isArray(data.extractors) ? data.extractors : []
    requestConfigForm.extractors = JSON.parse(JSON.stringify(interfaceExtractors)).map((item) => ({
      variable: item.variable || '',
      source: item.source || 'body',
      type: item.type || 'jsonpath',
      expression: item.expression || '',
      default_value: item.default_value || ''
    }))
    ElMessage.success(t('apiTesting.automation.syncSuccess'))
  } catch (error) {
    console.error('同步接口变量提取失败:', error)
    ElMessage.error(t('apiTesting.automation.syncFailed'))
  } finally {
    syncingExtractors.value = false
  }
}

const normalizeAssertion = (item = {}, index = 0) => {
  const type = item.type || 'status_code'
  let expected = item.expected
  if (expected === undefined || expected === null) {
    expected = item.expected_value !== undefined ? item.expected_value : item.value
  }
  if (type === 'status_code' && (expected === undefined || expected === null || expected === '')) {
    expected = 200
  }
  return {
    name: item.name || `${t('apiTesting.interface.assertion')}${index + 1}`,
    type,
    expected: expected ?? '',
    json_path: item.json_path || '',
    header_name: item.header_name || '',
    expected_value: item.expected_value || expected || ''
  }
}

const addConfigAssertion = () => {
  requestConfigForm.assertions.push(normalizeAssertion({
    type: 'status_code',
    expected: 200
  }, requestConfigForm.assertions.length))
}

const onConfigAssertionTypeChange = (assertion) => {
  if (!assertion) return
  if (assertion.type === 'status_code') {
    assertion.expected = 200
  } else if (assertion.type === 'response_time') {
    assertion.expected = 1000
  } else {
    assertion.expected = ''
  }
  assertion.json_path = ''
  assertion.header_name = ''
  assertion.expected_value = ''
}

const getAssertionExpectedPlaceholder = (type) => {
  if (type === 'status_code') return t('apiTesting.interface.expectedStatusCode')
  if (type === 'response_time') return t('apiTesting.interface.maxResponseTime')
  if (type === 'contains') return t('apiTesting.interface.expectedContains')
  if (type === 'equals') return t('apiTesting.interface.expectedMatch')
  return t('apiTesting.interface.expectedValue')
}

const clearConfigAssertions = () => {
  requestConfigForm.assertions = []
}

const syncAssertionsFromInterface = async () => {
  const requestId = currentConfigRequest.value?.request?.id
  if (!requestId) {
    ElMessage.warning(t('apiTesting.automation.syncInterfaceMissing'))
    return
  }

  syncingAssertions.value = true
  try {
    const { data } = await api.get(`/api-testing/requests/${requestId}/`)
    const interfaceAssertions = Array.isArray(data.assertions) ? data.assertions : []
    requestConfigForm.assertions = interfaceAssertions.map((item, index) => normalizeAssertion(item, index))
    ElMessage.success(t('apiTesting.automation.syncSuccess'))
  } catch (error) {
    console.error('同步接口断言失败:', error)
    ElMessage.error(t('apiTesting.automation.syncFailed'))
  } finally {
    syncingAssertions.value = false
  }
}

const saveRequestConfig = async () => {
  if (!currentConfigRequest.value?.id) return
  savingRequestConfig.value = true
  try {
    const assertions = (requestConfigForm.assertions || []).map((item, index) => {
      const normalized = normalizeAssertion(item, index)
      if (normalized.type === 'header') {
        normalized.expected_value = normalized.expected
      }
      // status_code / response_time 期望值为数字
      if (['status_code', 'response_time'].includes(normalized.type)) {
        const num = Number(normalized.expected)
        if (!Number.isNaN(num)) normalized.expected = num
      }
      return normalized
    })

    await api.patch(`/api-testing/test-suite-requests/${currentConfigRequest.value.id}/`, {
      skip_condition: requestConfigForm.skip_condition || '',
      extractors: requestConfigForm.extractors || [],
      assertions
    })
    ElMessage.success(t('apiTesting.messages.success.save') || '保存成功')
    showRequestConfigDialog.value = false
    await reloadCurrentSuite()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed') || '保存失败')
  } finally {
    savingRequestConfig.value = false
  }
}

const removeRequest = async (suiteRequest) => {
  try {
    await ElMessageBox.confirm(t('apiTesting.automation.confirmRemoveRequest'), t('apiTesting.common.tip') || '提示', {
      confirmButtonText: t('apiTesting.common.confirm'),
      cancelButtonText: t('apiTesting.common.cancel'),
      type: 'warning'
    })

    await api.delete(`/api-testing/test-suite-requests/${suiteRequest.id}/`)
    ElMessage.success(t('apiTesting.messages.success.removeSuccess'))
    // 重新加载当前测试套件详情
    await reloadCurrentSuite()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.removeFailed'))
    }
  }
}

const moveRequest = async (index, direction) => {
  if (!selectedSuite.value?.suite_requests || movingRequestOrder.value) return

  const requests = selectedSuite.value.suite_requests
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  if (targetIndex < 0 || targetIndex >= requests.length) return

  const previousOrders = requests.map(item => ({ id: item.id, order: item.order }))
  const reordered = [...requests]
  const temp = reordered[index]
  reordered[index] = reordered[targetIndex]
  reordered[targetIndex] = temp
  reordered.forEach((item, i) => {
    item.order = i
  })
  selectedSuite.value.suite_requests = reordered

  movingRequestOrder.value = true
  try {
    await api.post(`/api-testing/test-suites/${selectedSuite.value.id}/update-request-order/`, {
      request_orders: reordered.map((item, i) => ({ id: item.id, order: i }))
    })

    const suiteIndex = testSuites.value.findIndex(suite => suite.id === selectedSuite.value.id)
    if (suiteIndex !== -1) {
      testSuites.value[suiteIndex] = {
        ...testSuites.value[suiteIndex],
        suite_requests: [...reordered]
      }
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed'))
    // 失败时按原顺序回滚，避免界面与后端不一致
    const restored = [...reordered]
    previousOrders.forEach(({ id, order }) => {
      const item = restored.find(r => r.id === id)
      if (item) item.order = order
    })
    restored.sort((a, b) => a.order - b.order)
    selectedSuite.value.suite_requests = restored
  } finally {
    movingRequestOrder.value = false
  }
}

const reloadCurrentSuite = async () => {
  if (!selectedSuite.value) return

  try {
    // 重新加载当前测试套件的详细信息
    const response = await api.get(`/api-testing/test-suites/${selectedSuite.value.id}/`)
    const updatedSuite = response.data

    // 强制重新设置响应式数据
    selectedSuite.value = { ...updatedSuite }

    // 同时更新测试套件列表中对应的套件
    const index = testSuites.value.findIndex(suite => suite.id === updatedSuite.id)
    if (index !== -1) {
      testSuites.value[index] = { ...updatedSuite }
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.refreshSuiteFailed'))
  }
}

const viewExecutionDetail = (execution) => {
  currentExecution.value = execution
  showExecutionDialog.value = true
}

const openAllureReport = (reportUrl) => {
  if (!reportUrl) return
  const url = reportUrl.startsWith('http') ? reportUrl : `${window.location.origin}${reportUrl}`
  window.open(url, '_blank')
}

const formatExecutionResults = (results) => {
  if (!results || !Array.isArray(results)) return []
  return results
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.automation-testing {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.content-layout {
  display: flex;
  flex: 1;
  gap: 20px;
  overflow: hidden;
}

.sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.project-selector {
  background: white;
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.suite-list {
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 500;
}

.suite-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #f5f7fa;
  cursor: pointer;
  transition: background-color 0.3s;
}

.suite-item:hover {
  background: #f5f7fa;
}

.suite-item.active {
  background: #e1f3d8;
  border-color: #67c23a;
}

.suite-info {
  flex: 1;
}

.suite-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.suite-meta {
  font-size: 12px;
  color: #909399;
}

.main-content {
  flex: 1;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.suite-detail {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.suite-header {
  margin-bottom: 30px;
}

.suite-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.suite-title h4 {
  margin: 0;
  color: #303133;
}

.suite-actions {
  display: flex;
  gap: 10px;
}

.suite-description {
  color: #606266;
  margin-bottom: 10px;
}

.suite-meta {
  display: flex;
  gap: 15px;
  align-items: center;
}

.meta-text {
  font-size: 12px;
  color: #909399;
}

.requests-section,
.executions-section {
  margin-bottom: 30px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h5 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.request-op-btn,
.request-op-btn:hover,
.request-op-btn:focus,
.request-op-btn:active {
  box-shadow: none !important;
}

.add-request-content {
  max-height: 400px;
  overflow-y: auto;
}

.request-tree-node {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
}

.method-tag {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 2px;
  color: white;
  font-weight: bold;
  margin-left: auto;
}

.method-tag.get { background: #67c23a; }
.method-tag.post { background: #409eff; }
.method-tag.put { background: #e6a23c; }
.method-tag.delete { background: #f56c6c; }
.method-tag.patch { background: #909399; }

.execution-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.execution-summary {
  margin-bottom: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 6px;
}

.execution-results h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

.skip-condition-text {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: #606266;
}

.skip-help-alert {
  margin-top: 4px;
}

.skip-help p {
  margin: 0 0 6px;
}

.skip-help ul {
  margin: 0;
  padding-left: 18px;
}

.skip-help code {
  background: #f4f4f5;
  padding: 1px 6px;
  border-radius: 4px;
  color: #c45656;
  font-family: Consolas, Monaco, monospace;
}

.config-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: 600;
  color: #303133;
}

.config-list-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.config-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.config-row:last-child {
  margin-bottom: 0;
}

.config-row .el-input {
  flex: 1;
}

.extractor-config-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}

.extractor-config-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.extractor-field-variable {
  width: 140px;
  flex-shrink: 0;
}

.extractor-field-source {
  width: 110px;
  flex-shrink: 0;
}

.extractor-field-type {
  width: 120px;
  flex-shrink: 0;
}

.extractor-field-expression {
  flex: 1;
  min-width: 160px;
}

.extractor-expression-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.extractor-field-default {
  width: 120px;
  flex-shrink: 0;
}

.extractor-help {
  margin-top: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.extractor-help-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  cursor: pointer;
  color: #606266;
  font-size: 13px;
  user-select: none;
}

.extractor-help-header:hover {
  background: #f5f7fa;
}

.extractor-help-arrow {
  width: 20px;
  height: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease;
  color: #909399;
}

.extractor-help-arrow.expanded {
  transform: rotate(90deg);
}

.extractor-help-body {
  padding: 0 12px 12px;
  border-top: 1px solid #ebeef5;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
}

.extractor-help-body p {
  margin: 10px 0 4px;
}

.extractor-help-body ul {
  margin: 0;
  padding-left: 18px;
}

.extractor-help-body code {
  background: #f4f4f5;
  padding: 1px 6px;
  border-radius: 4px;
  color: #c45656;
  font-family: Consolas, Monaco, monospace;
}

.assertion-config-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
  background: #fff;
}

.assertion-config-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.assertion-field-name {
  width: 140px;
  flex-shrink: 0;
}

.assertion-field-type {
  width: 150px;
  flex-shrink: 0;
}

.assertion-field-extra {
  flex: 1;
  min-width: 140px;
}

.assertion-field-expected {
  flex: 1;
  min-width: 120px;
}

.assertion-delete-btn {
  flex-shrink: 0;
  margin-left: auto;
}

.add-assertion-btn {
  width: 100%;
  margin-top: 4px;
}
</style>