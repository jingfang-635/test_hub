<template>
  <div class="page-container task-detail">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">{{ $t('taskDetail.title') }}<span v-if="task.title" class="title-sub"> - {{ task.title }}</span></h2>
        <div class="task-info">
          <span class="task-id">{{ $t('taskDetail.taskId') }}: {{ taskId }}</span>
          <el-tag
            v-if="task.status"
            :type="getStatusTagType(task.status)"
            effect="light"
            size="small"
          >
            {{ getStatusText(task.status) }}
          </el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          v-if="testCases.length > 0"
          type="success"
          :loading="isExporting"
          @click="exportToExcel"
        >
          {{ isExporting ? $t('taskDetail.exporting') : $t('taskDetail.exportBtn') }}
        </el-button>
      </div>
    </div>

    <!-- 需求描述折叠卡片 -->
    <div v-if="task.requirement_text" class="requirement-description-card">
      <el-collapse>
        <el-collapse-item name="requirement">
          <template #title>
            <div class="collapse-title">
              <span class="title-text">{{ $t('taskDetail.requirementTitle') }}</span>
              <span class="title-hint">{{ $t('taskDetail.requirementHint') }}</span>
            </div>
          </template>
          <div class="requirement-content">
            <div class="requirement-text">
              {{ task.requirement_text }}
            </div>
            <div class="requirement-actions">
              <el-button size="small" @click="copyRequirementText">
                <el-icon><DocumentCopy /></el-icon>
                {{ $t('taskDetail.copyRequirement') }}
              </el-button>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <div v-if="isLoading" class="loading-state">
      <p>{{ $t('taskDetail.loading') }}</p>
    </div>

    <div v-else-if="!task.task_id" class="error-state">
      <h3>{{ $t('taskDetail.taskNotExist') }}</h3>
      <el-button type="primary" @click="$router.push('/ai-generation/generated-testcases')">
        {{ $t('taskDetail.backToList') }}
      </el-button>
    </div>

    <div v-else class="task-content">
      <div v-if="testCases.length > 0" class="card-container">
        <!-- 批量操作区域 -->
        <div class="batch-actions">
          <div class="selection-info">
            <el-checkbox :model-value="isAllSelected" @change="toggleSelectAll">
              {{ $t('taskDetail.selectAll') }}
            </el-checkbox>
            <span class="selected-count" v-if="selectedCases.length > 0">
              {{ $t('taskDetail.selectedCount', { count: selectedCases.length }) }}
            </span>
          </div>
          <div class="batch-buttons">
            <el-button type="success" :disabled="selectedCases.length === 0" @click="batchAdopt">
              {{ $t('taskDetail.batchAdopt', { count: selectedCases.length }) }}
            </el-button>
            <el-button type="danger" :disabled="selectedCases.length === 0" @click="batchDiscard">
              {{ $t('taskDetail.batchDiscard', { count: selectedCases.length }) }}
            </el-button>
          </div>
        </div>

        <!-- 测试用例列表 -->
        <div class="testcases-table">
          <el-table :data="paginatedTestCases">
            <el-table-column :label="$t('taskDetail.tableSelect')" width="55" align="center">
              <template #default="{ row }">
                <el-checkbox
                  :model-value="selectedCases.includes(row)"
                  @change="(val) => toggleCaseSelection(row, val)"
                />
              </template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tableCaseId')" min-width="140" show-overflow-tooltip>
              <template #default="{ row, $index }">
                <span class="case-id">{{ row.caseId || `TC${String($index + 1).padStart(3, '0')}` }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tableScenario')" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.scenario }}</template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tablePrecondition')" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ formatTextForList(row.precondition) }}</template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tableSteps')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">{{ formatTextForList(row.steps) }}</template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tableExpected')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">{{ formatTextForList(row.expected) }}</template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tablePriority')" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="getPriorityTagType(row.priority)" effect="light" size="small">
                  {{ row.priority || 'P2' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('taskDetail.tableActions')" width="265" fixed="right">
              <template #default="{ row, $index }">
                <div class="action-buttons">
                  <el-button size="small" class="view-btn" @click="viewCaseDetail(row, $index)">{{ $t('taskDetail.viewDetail') }}</el-button>
                  <el-button size="small" type="success" @click="adoptSingleCase(row, $index)">{{ $t('taskDetail.adopt') }}</el-button>
                  <el-button size="small" type="danger" @click="discardSingleCase(row, $index)">{{ $t('taskDetail.discard') }}</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="testCases.length"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="handleSizeChange"
          />
        </div>
      </div>

      <div v-else class="empty-state card-container">
        <h3>{{ $t('taskDetail.emptyTitle') }}</h3>
        <p>{{ $t('taskDetail.emptyHint') }}</p>
      </div>
    </div>

    <!-- 用例详情弹窗 -->
    <el-dialog
      v-model="showCaseDetail"
      :title="isEditing ? $t('taskDetail.modalEditTitle') : $t('taskDetail.modalViewTitle')"
      width="800px"
      class="case-detail-dialog"
      :close-on-click-modal="false"
      @close="closeCaseDetail"
    >
      <!-- 查看模式 -->
      <div v-if="!isEditing" class="modal-body">
        <div class="info-table">
          <div class="info-row">
            <div class="info-label">{{ $t('taskDetail.labelCaseId') }}</div>
            <div class="info-value">{{ selectedCase.caseId || `TC${String(selectedCaseIndex + 1).padStart(3, '0')}` }}</div>
          </div>
          <div class="info-row">
            <div class="info-label">{{ $t('taskDetail.labelScenario') }}</div>
            <div class="info-value" v-html="formatMarkdown(selectedCase.scenario)"></div>
          </div>
          <div class="info-row">
            <div class="info-label">{{ $t('taskDetail.labelPrecondition') }}</div>
            <div class="info-value" v-html="formatMarkdown(selectedCase.precondition || $t('taskDetail.labelNone'))"></div>
          </div>
          <div class="info-row">
            <div class="info-label">{{ $t('taskDetail.labelSteps') }}</div>
            <div class="info-value test-steps" v-html="formatMarkdown(selectedCase.steps)"></div>
          </div>
          <div class="info-row">
            <div class="info-label">{{ $t('taskDetail.labelExpected') }}</div>
            <div class="info-value" v-html="formatMarkdown(selectedCase.expected)"></div>
          </div>
          <div class="info-row">
            <div class="info-label">{{ $t('taskDetail.labelPriority') }}</div>
            <div class="info-value">
              <el-tag :type="getPriorityTagType(selectedCase.priority)" effect="light" size="small">
                {{ selectedCase.priority || 'P2' }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 编辑模式 -->
      <div v-else class="modal-body edit-mode">
        <div class="form-item">
          <label>{{ $t('taskDetail.labelCaseId') }}</label>
          <span class="readonly-field">{{ editForm.caseId || `TC${String(selectedCaseIndex + 1).padStart(3, '0')}` }}</span>
        </div>
        <div class="form-item">
          <label>{{ $t('taskDetail.labelScenario') }}</label>
          <el-input v-model="editForm.scenario" type="textarea" :rows="2" :placeholder="$t('taskDetail.placeholderScenario')" />
        </div>
        <div class="form-item">
          <label>{{ $t('taskDetail.labelPrecondition') }}</label>
          <el-input v-model="editForm.precondition" type="textarea" :rows="3" :placeholder="$t('taskDetail.placeholderPrecondition')" />
        </div>
        <div class="form-item">
          <label>{{ $t('taskDetail.labelSteps') }}</label>
          <el-input v-model="editForm.steps" type="textarea" :rows="6" :placeholder="$t('taskDetail.placeholderSteps')" />
        </div>
        <div class="form-item">
          <label>{{ $t('taskDetail.labelExpected') }}</label>
          <el-input v-model="editForm.expected" type="textarea" :rows="4" :placeholder="$t('taskDetail.placeholderExpected')" />
        </div>
        <div class="form-item">
          <label>{{ $t('taskDetail.labelPriority') }}</label>
          <el-select v-model="editForm.priority" :placeholder="$t('taskDetail.placeholderPriority')">
            <el-option label="P0" value="P0"></el-option>
            <el-option label="P1" value="P1"></el-option>
            <el-option label="P2" value="P2"></el-option>
            <el-option label="P3" value="P3"></el-option>
          </el-select>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <template #footer>
        <template v-if="!isEditing">
          <el-button type="primary" @click="startEdit">{{ $t('taskDetail.btnEdit') }}</el-button>
          <el-button @click="closeCaseDetail">{{ $t('taskDetail.btnClose') }}</el-button>
        </template>
        <template v-else>
          <el-button type="primary" :loading="isSaving" @click="saveEdit">
            {{ isSaving ? $t('taskDetail.btnSaveing') : $t('taskDetail.btnSave') }}
          </el-button>
          <el-button @click="cancelEdit" :disabled="isSaving">{{ $t('taskDetail.btnCancel') }}</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'

export default {
  name: 'TaskDetail',
  data() {
    return {
      taskId: '',
      task: {},
      testCases: [],
      selectedCases: [],
      isLoading: true,
      showCaseDetail: false,
      selectedCase: {},
      selectedCaseIndex: 0,
      currentPage: 1,
      pageSize: 10,
      isExporting: false,
      // 编辑相关状态
      isEditing: false,
      isSaving: false,
      editForm: {
        caseId: '',
        scenario: '',
        precondition: '',
        steps: '',
        expected: '',
        priority: 'P2'
      }
    }
  },

  computed: {
    isAllSelected() {
      return this.testCases.length > 0 && this.selectedCases.length === this.testCases.length
    },

    paginatedTestCases() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.testCases.slice(start, end)
    }
  },

  mounted() {
    this.taskId = this.$route.params.taskId
    this.loadTaskDetail()
  },

  methods: {
    // 复制需求描述文本
    async copyRequirementText() {
      try {
        await navigator.clipboard.writeText(this.task.requirement_text)
        ElMessage.success(this.$t('taskDetail.copySuccess'))
      } catch (error) {
        // 如果 navigator.clipboard 不可用，使用备用方法
        const textArea = document.createElement('textarea')
        textArea.value = this.task.requirement_text
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.select()
        try {
          document.execCommand('copy')
          ElMessage.success(this.$t('taskDetail.copySuccess'))
        } catch (err) {
          ElMessage.error(this.$t('taskDetail.copyFailed'))
        }
        document.body.removeChild(textArea)
      }
    },

    async loadTaskDetail() {
      try {
        // 获取任务基本信息
        const taskResponse = await api.get(`/requirement-analysis/testcase-generation/${this.taskId}/`)
        this.task = taskResponse.data

        // 解析最终测试用例
        if (this.task.final_test_cases) {
          this.testCases = this.parseTestCases(this.task.final_test_cases)
        }
      } catch (error) {
        console.error('Failed to load task details:', error)
        ElMessage.error(this.$t('taskDetail.loadFailed'))
      } finally {
        this.isLoading = false
      }
    },

    parseTestCases(content) {
      // 复用RequirementAnalysisView中的解析逻辑
      if (!content) return []

      // 去除markdown加粗标记，保留纯净文本
      let cleanContent = content.replace(/\*\*([^*]+)\*\*/g, '$1')

      const lines = cleanContent.split('\n').filter(line => line.trim())
      const testCases = []

      // 尝试解析表格格式
      let isTableFormat = false
      const tableData = []

      for (let line of lines) {
        const trimmedLine = line.trim()
        if (trimmedLine.includes('|') && !trimmedLine.includes('--------')) {
          // 保留空单元格位置，避免因删除空单元格导致列错位
          const cells = trimmedLine.replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim())
          if (cells.length > 1) {
            tableData.push(cells)
            isTableFormat = true
          }
        }
      }
      
      if (isTableFormat && tableData.length > 1) {
        // 表格格式解析
        const headers = tableData[0]
        for (let i = 1; i < tableData.length; i++) {
          const row = tableData[i]
          const testCase = {}

          // 清理<br>标签的辅助函数
          const cleanBrTags = (text) => {
            if (!text) return ''
            return text.replace(/<br\s*\/?>/gi, '\n')
          }

          headers.forEach((header, index) => {
            const value = cleanBrTags(row[index] || '')

            // 使用更精确的匹配逻辑，避免误判
            const cleanHeader = header.trim().toLowerCase()

            // 优先级匹配，避免误判
            if (cleanHeader === '优先级' || cleanHeader === 'priority' || cleanHeader === 'priority（优先级）' || cleanHeader === '优先级（priority）') {
              testCase.priority = value
            } else if (cleanHeader === '用例id' || cleanHeader === '用例编号' || cleanHeader === '测试用例编号' || cleanHeader === '编号' || cleanHeader === 'id' || cleanHeader.includes('用例id')) {
              testCase.caseId = value
            } else if (cleanHeader === '测试目标' || cleanHeader === '测试场景' || cleanHeader === '场景' || cleanHeader === '标题' || cleanHeader.includes('测试目标')) {
              testCase.scenario = value
            } else if (cleanHeader === '前置条件' || cleanHeader === '前置' || cleanHeader === '前提条件') {
              testCase.precondition = value
            } else if (cleanHeader === '测试步骤' || cleanHeader === '操作步骤' || cleanHeader === '步骤') {
              // 确保不要误匹配"预期结果"中包含的"步骤"字样
              if (!cleanHeader.includes('预期') && !cleanHeader.includes('结果')) {
                testCase.steps = value
              }
            } else if (cleanHeader === '预期结果' || cleanHeader === '预期' || cleanHeader === '结果' || cleanHeader.includes('预期结果')) {
              testCase.expected = value
            }
          })

          if (testCase.scenario || testCase.caseId) {
            // If steps field is empty, use scenario as default
            if (!testCase.steps && testCase.scenario) {
              testCase.steps = testCase.scenario
            }
            // 如果没有priority，设置默认值
            if (!testCase.priority) {
              testCase.priority = 'P2'
            }
            testCases.push(testCase)
          }
        }
      } else {
        // 结构化文本格式解析
        let currentTestCase = {}
        let caseNumber = 1
        
        for (const line of lines) {
          if (line.includes('测试用例') || line.includes('Test Case') || 
              line.match(/^(\d+\.|\*|\-|\d+、)/)) {
            
            if (Object.keys(currentTestCase).length > 0) {
              testCases.push(currentTestCase)
              caseNumber++
            }
            
            currentTestCase = {
              caseId: `TC${String(caseNumber).padStart(3, '0')}`,
              scenario: line.replace(/^(\d+\.|\*|\-|\d+、)\s*/, '').replace(/测试用例\d*[:：]?\s*/, '').replace(/Test Case\s*\d*[:：]?\s*/i, ''),
              precondition: '',
              steps: '',
              expected: '',
              priority: 'P2'
            }
          } else if (line.includes('前置条件') || line.includes('前提')) {
            currentTestCase.precondition = line.replace(/.*?[:：]\s*/, '')
          } else if (line.includes('测试步骤') || line.includes('操作步骤') || line.includes('步骤')) {
            currentTestCase.steps = line.replace(/.*?[:：]\s*/, '')
          } else if (line.includes('预期结果') || line.includes('Expected')) {
            currentTestCase.expected = line.replace(/.*?[:：]\s*/, '')
          } else if (line.includes('优先级')) {
            currentTestCase.priority = line.replace(/.*?[:：]\s*/, '')
          }
        }
        
        if (Object.keys(currentTestCase).length > 0) {
          testCases.push(currentTestCase)
        }
      }
      
      return testCases
    },

    getStatusText(status) {
      if (!status) return ''
      const statusKey = 'status' + status.charAt(0).toUpperCase() + status.slice(1)
      return this.$t('taskDetail.' + statusKey) || status
    },

    getStatusTagType(status) {
      const typeMap = {
        pending: 'info',
        generating: 'warning',
        reviewing: 'primary',
        completed: 'success',
        failed: 'danger'
      }
      return typeMap[status] || 'info'
    },

    getPriorityTagType(priority) {
      const priorityMap = {
        'P0': 'danger',
        'critical': 'danger',
        'P1': 'warning',
        'high': 'warning',
        'P2': 'primary',
        'medium': 'primary',
        'P3': 'info',
        'low': 'info'
      }
      return priorityMap[priority] || 'primary'
    },

    // 格式化列表中的文本，将<br>转换为换行
    formatTextForList(text) {
      if (!text) return ''
      // 将<br>、<br/>、<br />等标签替换为换行符
      return text.replace(/<br\s*\/?>/gi, '\n')
    },

    // 格式化文本，去除markdown标记并保留格式
    formatMarkdown(text) {
      if (!text) return ''

      // 先转义HTML标签，防止XSS
      let formatted = text.replace(/&/g, '&amp;')
                         .replace(/</g, '&lt;')
                         .replace(/>/g, '&gt;')

      // 去除markdown加粗标记 **text**，保留纯文本
      formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '$1')

      // 转换换行符为<br>
      formatted = formatted.replace(/\n/g, '<br>')

      return formatted
    },

    toggleSelectAll(val) {
      this.selectedCases = val ? [...this.testCases] : []
    },

    toggleCaseSelection(row, val) {
      if (val) {
        if (!this.selectedCases.includes(row)) {
          this.selectedCases.push(row)
        }
      } else {
        this.selectedCases = this.selectedCases.filter(item => item !== row)
      }
    },

    handleSizeChange() {
      this.currentPage = 1
    },

    async batchAdopt() {
      if (this.selectedCases.length === 0) {
        ElMessage.warning(this.$t('taskDetail.pleaseSelectFirst', { action: this.$t('taskDetail.adopt') }))
        return
      }

      try {
        await ElMessageBox.confirm(
          this.$t('taskDetail.confirmAdopt', { count: this.selectedCases.length }),
          this.$t('taskDetail.confirmAdoptTitle'),
          {
            confirmButtonText: this.$t('taskDetail.btnConfirm'),
            cancelButtonText: this.$t('taskDetail.btnCancelOperation'),
            type: 'success'
          }
        )
      } catch {
        return
      }

      try {
        const casesData = this.selectedCases.map((testCase, index) => ({
          title: testCase.scenario || `Test Case ${index + 1}`,
          description: testCase.scenario || '',
          preconditions: testCase.precondition || '',
          steps: testCase.steps || '',
          expected_result: testCase.expected || '',
          priority: this.mapPriority(testCase.priority),
          test_type: 'functional',
          status: 'draft'
        }))

        await api.post(`/requirement-analysis/testcase-generation/${this.taskId}/batch-adopt-selected/`, {
          test_cases: casesData
        })

        ElMessage.success(this.$t('taskDetail.adoptSuccess', { count: this.selectedCases.length }))
        this.selectedCases = []

        // Keep adopted cases in the list for multiple adoptions
        // this.testCases = this.testCases.filter(tc => !this.selectedCases.includes(tc))

      } catch (error) {
        console.error('Batch adopt failed:', error)
        ElMessage.error(this.$t('taskDetail.batchAdoptFailed') + ': ' + (error.response?.data?.message || error.message))
      }
    },

    async batchDiscard() {
      if (this.selectedCases.length === 0) {
        ElMessage.warning(this.$t('taskDetail.pleaseSelectFirst', { action: this.$t('taskDetail.discard') }))
        return
      }

      try {
        await ElMessageBox.confirm(
          this.$t('taskDetail.confirmDiscard', { count: this.selectedCases.length }),
          this.$t('taskDetail.confirmDiscardTitle'),
          {
            confirmButtonText: this.$t('taskDetail.btnConfirm'),
            cancelButtonText: this.$t('taskDetail.btnCancelOperation'),
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
      } catch {
        return
      }

      try {
        // 获取选中用例的全局索引（不是分页索引）
        const caseIndices = this.selectedCases.map(selectedCase => {
          // 在完整列表中查找索引
          const globalIndex = this.testCases.findIndex(tc =>
            tc.scenario === selectedCase.scenario &&
            tc.steps === selectedCase.steps &&
            tc.expected === selectedCase.expected
          )
          return globalIndex
        }).filter(index => index !== -1) // 过滤掉未找到的(-1)

        const response = await api.post(`/requirement-analysis/testcase-generation/${this.taskId}/discard-selected-cases/`, {
          case_indices: caseIndices
        })

        if (response.data.task_deleted) {
          ElMessage.success(this.$t('taskDetail.allDiscardedSuccess'))
          // 返回到AI生成用例记录列表
          this.$router.push('/generated-testcases')
        } else {
          ElMessage.success(this.$t('taskDetail.discardSuccess', { count: response.data.discarded_count }))

          // 重新解析更新后的测试用例
          if (response.data.updated_test_cases) {
            this.testCases = this.parseTestCases(response.data.updated_test_cases)
            this.selectedCases = []
            this.currentPage = 1 // 重置到第一页
          }
        }

      } catch (error) {
        console.error('Batch discard failed:', error)
        ElMessage.error(this.$t('taskDetail.batchDiscardFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    viewCaseDetail(testCase, index) {
      this.selectedCase = testCase
      this.selectedCaseIndex = index
      this.showCaseDetail = true
    },

    closeCaseDetail() {
      this.showCaseDetail = false
      this.selectedCase = {}
      this.isEditing = false
      this.editForm = {
        caseId: '',
        scenario: '',
        precondition: '',
        steps: '',
        expected: '',
        priority: 'P2'
      }
    },

    // 开始编辑
    startEdit() {
      this.isEditing = true

      this.editForm = {
        caseId: this.selectedCase.caseId || '',
        scenario: this.selectedCase.scenario || '',
        // 将<br>转换为换行符以便编辑
        precondition: this.convertBrToNewline(this.selectedCase.precondition || ''),
        steps: this.convertBrToNewline(this.selectedCase.steps || ''),
        expected: this.convertBrToNewline(this.selectedCase.expected || ''),
        // 直接使用原始优先级值，不转换
        priority: this.selectedCase.priority || 'P2'
      }
    },

    // 取消编辑
    cancelEdit() {
      this.isEditing = false
      this.editForm = {
        caseId: '',
        scenario: '',
        precondition: '',
        steps: '',
        expected: '',
        priority: 'P2'
      }
    },

    // 保存编辑
    async saveEdit() {
      // 简单验证
      if (!this.editForm.scenario?.trim()) {
        ElMessage.warning(this.$t('taskDetail.enterScenario'))
        return
      }

      this.isSaving = true

      try {
        // 将换行符转换回<br>
        const updatedCase = {
          ...this.selectedCase,
          scenario: this.editForm.scenario,
          precondition: this.convertNewlineToBr(this.editForm.precondition),
          steps: this.convertNewlineToBr(this.editForm.steps),
          expected: this.convertNewlineToBr(this.editForm.expected),
          priority: this.editForm.priority
        }

        // 更新本地数组中的数据
        const index = this.testCases.findIndex(tc => tc === this.selectedCase)
        if (index !== -1) {
          this.testCases[index] = updatedCase
          this.selectedCase = updatedCase
        }

        // 重新生成表格格式的测试用例字符串
        const updatedTestCases = this.generateTestCasesString()

        // 调用后端API保存（使用自定义action接口）
        await api.post(`/requirement-analysis/testcase-generation/${this.taskId}/update-test-cases/`, {
          final_test_cases: updatedTestCases
        })

        // 更新内存中的task数据
        this.task.final_test_cases = updatedTestCases

        ElMessage.success(this.$t('taskDetail.updateSuccess'))
        this.isEditing = false
      } catch (error) {
        console.error('Update failed:', error)
        ElMessage.error(this.$t('taskDetail.updateFailed') + ': ' + (error.response?.data?.error || error.message))
      } finally {
        this.isSaving = false
      }
    },

    // 将testCases数组重新生成为表格格式的字符串
    generateTestCasesString() {
      if (this.testCases.length === 0) return ''

      // 表头
      const headers = [
        this.$t('taskDetail.tableCaseId'),
        this.$t('taskDetail.tableScenario'),
        this.$t('taskDetail.tablePrecondition'),
        this.$t('taskDetail.tableSteps'),
        this.$t('taskDetail.tableExpected'),
        this.$t('taskDetail.tablePriority')
      ]
      let result = headers.join(' | ') + '\n'
      result += '|'.repeat(headers.length) + '\n'

      // 数据行
      this.testCases.forEach((testCase, index) => {
        const row = [
          testCase.caseId || `TC${String(index + 1).padStart(3, '0')}`,
          testCase.scenario || '',
          testCase.precondition || '',
          testCase.steps || '',
          testCase.expected || '',
          testCase.priority || 'P2'
        ]
        result += row.join(' | ') + '\n'
      })

      return result
    },

    // 将HTML的<br>标签转换为换行符
    convertBrToNewline(text) {
      if (!text) return ''
      return text.replace(/<br\s*\/?>/gi, '\n')
    },

    // 将换行符转换为HTML的<br>标签
    convertNewlineToBr(text) {
      if (!text) return ''
      return text.replace(/\n/g, '<br>')
    },

    async adoptSingleCase(testCase, index) {
      try {
        await ElMessageBox.confirm(
          this.$t('taskDetail.confirmAdoptSingle', { scenario: testCase.scenario }),
          this.$t('taskDetail.confirmAdoptTitle'),
          {
            confirmButtonText: this.$t('taskDetail.btnConfirm'),
            cancelButtonText: this.$t('taskDetail.btnCancelOperation'),
            type: 'success'
          }
        )
      } catch {
        return
      }

      try {
        const caseData = {
          title: testCase.scenario || `测试用例${index + 1}`,
          description: testCase.scenario || '',
          preconditions: testCase.precondition || '',
          steps: testCase.steps || '',
          expected_result: testCase.expected || '',
          priority: this.mapPriority(testCase.priority),
          test_type: 'functional',
          status: 'draft'
        }

        await api.post('/testcases/', caseData)
        ElMessage.success(this.$t('taskDetail.adoptSuccess', { count: 1 }))

        // 不再移除已采纳的用例，保留在列表中供多次采纳
        // this.testCases.splice(this.testCases.indexOf(testCase), 1)

      } catch (error) {
        console.error('Adopt case failed:', error)
        ElMessage.error(this.$t('taskDetail.adoptFailed') + ': ' + (error.response?.data?.message || error.message))
      }
    },

    async discardSingleCase(testCase, index) {
      try {
        await ElMessageBox.confirm(
          this.$t('taskDetail.confirmDiscardSingle', { scenario: testCase.scenario }),
          this.$t('taskDetail.confirmDiscardTitle'),
          {
            confirmButtonText: this.$t('taskDetail.btnConfirm'),
            cancelButtonText: this.$t('taskDetail.btnCancelOperation'),
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
      } catch {
        return
      }

      try {
        // 计算全局索引（当前页面起始位置 + 当前索引）
        const globalIndex = (this.currentPage - 1) * this.pageSize + index

        // 调用后端API弃用单个测试用例
        const response = await api.post(`/requirement-analysis/testcase-generation/${this.taskId}/discard-single-case/`, {
          case_index: globalIndex
        })

        if (response.data.task_deleted) {
          ElMessage.success(this.$t('taskDetail.allDiscardedSuccess'))
          // 返回到AI生成用例记录列表
          this.$router.push('/generated-testcases')
        } else {
          ElMessage.success(this.$t('taskDetail.caseDiscardedSuccess'))

          // 重新解析更新后的测试用例
          if (response.data.updated_test_cases) {
            this.testCases = this.parseTestCases(response.data.updated_test_cases)

            // 如果当前页没有数据了，回到上一页
            if (this.currentPage > 1 && this.paginatedTestCases.length === 0) {
              this.currentPage--
            }
          }
        }

      } catch (error) {
        console.error('Discard case failed:', error)
        ElMessage.error(this.$t('taskDetail.discardFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    mapPriority(priority) {
      const priorityMap = {
        '最高': 'P0', '紧急': 'P0', 'critical': 'P0', 'P0': 'P0',
        '高': 'P1', 'high': 'P1', 'P1': 'P1',
        '中': 'P2', 'medium': 'P2', 'P2': 'P2',
        '低': 'P3', 'low': 'P3', 'P3': 'P3'
      }
      return priorityMap[priority] || 'P2'
    },

    // 将英文优先级转换为本地化显示
    priorityToChinese(priority) {
      const priorityMap = {
        'critical': this.$t('generatedTestCases.priorityCritical'),
        'high': this.$t('generatedTestCases.priorityHigh'),
        'medium': this.$t('generatedTestCases.priorityMedium'),
        'low': this.$t('generatedTestCases.priorityLow')
      }
      return priorityMap[priority] || this.$t('generatedTestCases.priorityMedium')
    },

    // 导出到Excel
    exportToExcel() {
      if (this.testCases.length === 0) {
        ElMessage.warning(this.$t('taskDetail.noCasesToExport'))
        return
      }

      this.isExporting = true

      try {
        // 创建工作簿
        const workbook = XLSX.utils.book_new()

        // 准备数据
        const worksheetData = []

        // 添加表头（与用例库导出Excel模板保持一致）
        worksheetData.push([
          this.$t('testcase.excelNumber'),
          this.$t('testcase.excelTitle'),
          this.$t('testcase.excelPreconditions'),
          this.$t('testcase.excelSteps'),
          this.$t('testcase.excelExpectedResult'),
          this.$t('testcase.excelRemark'),
          this.$t('testcase.excelPriority'),
          this.$t('testcase.excelTestType'),
          this.$t('testcase.excelProject'),
          this.$t('testcase.excelVersions'),
          this.$t('testcase.l1'),
          this.$t('testcase.l2'),
          this.$t('testcase.l3')
        ])

        // 添加数据行（无对应数据时留空，保留字段名）
        this.testCases.forEach((testCase, index) => {
          worksheetData.push([
            testCase.caseId || `TC${String(index + 1).padStart(3, '0')}`,
            testCase.scenario || '',
            this.formatTextForList(testCase.precondition || ''),
            this.formatTextForList(testCase.steps || ''),
            this.formatTextForList(testCase.expected || ''),
            '', // 备注：无对应数据
            testCase.priority || 'P2',
            '', // 测试类型：无对应数据
            '', // 关联项目：无对应数据
            '', // 关联版本：无对应数据
            '', // L1：无对应数据
            '', // L2：无对应数据
            ''  // L3：无对应数据
          ])
        })

        // 创建工作表
        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)

        // 设置列宽（与用例库导出Excel模板保持一致）
        worksheet['!cols'] = [
          { wch: 12 }, { wch: 30 }, { wch: 30 }, { wch: 40 }, { wch: 30 }, { wch: 20 },
          { wch: 10 }, { wch: 15 }, { wch: 20 }, { wch: 25 }, { wch: 15 }, { wch: 15 }, { wch: 15 }
        ]

        // 为所有单元格添加自动换行样式
        const range = XLSX.utils.decode_range(worksheet['!ref'])
        for (let row = range.s.r; row <= range.e.r; row++) {
          for (let col = range.s.c; col <= range.e.c; col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
            if (!worksheet[cellAddress]) continue
            worksheet[cellAddress].s = {
              alignment: {
                wrapText: true,
                vertical: 'top'
              }
            }
          }
        }

        // 将工作表添加到工作簿
        XLSX.utils.book_append_sheet(workbook, worksheet, this.$t('taskDetail.excelSheetName'))

        // 生成文件名
        const dateStr = new Date().toISOString().slice(0, 10)
        const fileName = this.$t('taskDetail.excelFileName', { taskId: this.taskId, date: dateStr })

        // 导出文件
        XLSX.writeFile(workbook, fileName)

        ElMessage.success(this.$t('taskDetail.exportSuccess'))
      } catch (error) {
        console.error('Export Excel failed:', error)
        ElMessage.error(this.$t('taskDetail.exportFailed') + ': ' + (error.message || ''))
      } finally {
        this.isExporting = false
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.task-detail {
  // 标题副标题
  .title-sub {
    margin-left: 8px;
    font-size: 16px;
    font-weight: 500;
    color: var(--th-text-secondary);
  }

  .header-left {
    min-width: 0;
  }

  .task-info {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 8px;
    flex-wrap: wrap;

    .task-id {
      font-size: 14px;
      color: var(--th-text-secondary);
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }
}

/* 需求描述折叠卡片 */
.requirement-description-card {
  margin-bottom: 20px;
  background: var(--th-bg-elevated);
  border: 1px solid var(--th-border);
  border-radius: var(--th-radius-lg);
  box-shadow: var(--th-shadow-xs);
  overflow: hidden;

  .collapse-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 500;
    padding-left: 4px;
  }

  .title-text {
    color: var(--th-text-primary);
    font-weight: 600;
  }

  .title-hint {
    font-size: 13px;
    color: var(--th-text-secondary);
    font-weight: normal;
  }

  .requirement-content {
    padding: 4px 0 16px;
  }

  .requirement-text {
    background: var(--th-bg-muted);
    border-radius: var(--th-radius-sm);
    padding: 16px;
    line-height: 1.8;
    color: var(--th-text-regular);
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 400px;
    overflow-y: auto;
    border-left: 3px solid var(--th-color-primary);
  }

  .requirement-actions {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
  }

  :deep(.el-collapse) {
    border: none;
  }

  :deep(.el-collapse-item__header) {
    background: transparent;
    border-bottom: none;
    padding: 16px 20px;
    font-size: 15px;
  }

  :deep(.el-collapse-item__wrap) {
    border-bottom: none;
  }

  :deep(.el-collapse-item__content) {
    padding: 0 20px 16px;
  }

  // 隐藏默认箭头图标
  :deep(.el-collapse-item__header .el-icon),
  :deep(.el-collapse-item__header .el-collapse-item__arrow),
  :deep(.el-collapse-item__header .el-icon-arrow-right),
  :deep(.el-collapse-item__header .el-icon-arrow-left) {
    display: none !important;
  }
}

/* 批量操作区域 */
.batch-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;

  .selection-info {
    display: flex;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;

    .selected-count {
      color: var(--th-color-primary);
      font-weight: 500;
      font-size: 14px;
    }
  }

  .batch-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
}

/* 测试用例表格 */
.testcases-table {
  :deep(.el-table) {
    border-radius: var(--th-radius-md);
  }

  .case-id {
    font-family: var(--el-font-family);
    font-weight: 500;
    color: var(--th-text-primary);
  }

  /* 操作按钮：三个按钮保持在同一行 */
  .action-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }

  /* 查看详情按钮：浅紫色样式 */
  .view-btn {
    --el-button-bg-color: #f0edfd;
    --el-button-border-color: #ddd6fb;
    --el-button-text-color: var(--th-color-primary);
    --el-button-hover-bg-color: #e5e0fa;
    --el-button-hover-border-color: #c7bcf9;
    --el-button-hover-text-color: var(--th-color-primary);
    --el-button-active-bg-color: #ddd6fb;
    --el-button-active-border-color: #b3a1f0;
    --el-button-active-text-color: var(--th-color-primary);
  }
}

/* 分页 */
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 加载 / 错误 / 空状态 */
.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--th-text-secondary);

  h3 {
    color: var(--th-text-primary);
    margin-bottom: 10px;
  }
}

.error-state a {
  color: var(--th-color-primary);
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

/* 用例详情弹窗 */
.case-detail-dialog {
  :deep(.el-dialog__header) {
    border-bottom: 1px solid var(--th-border);
    padding-bottom: 16px;
    margin-right: 0;
  }

  :deep(.el-dialog__title) {
    font-weight: 600;
    color: var(--th-text-primary);
  }
}

/* 详情信息表格（参考项目与版本样式） */
.info-table {
  border: 1px solid var(--th-border);
  border-radius: var(--th-radius-md);
  overflow: hidden;

  .info-row {
    display: grid;
    grid-template-columns: 180px 1fr;
    border-bottom: 1px solid var(--th-border);

    &:last-child {
      border-bottom: none;
    }
  }

  .info-label {
    padding: 14px 20px;
    background: var(--th-bg-muted);
    color: var(--th-text-secondary);
    font-weight: 500;
    font-size: 14px;
    border-right: 1px solid var(--th-border);
  }

  .info-value {
    padding: 14px 20px;
    color: var(--th-text-primary);
    font-size: 14px;
    line-height: 1.8;
    min-width: 0;
    word-break: break-word;

    &.test-steps {
      white-space: pre-wrap;
    }
  }
}

.modal-body.edit-mode {
  .form-item {
    margin-bottom: 18px;

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      font-weight: 500;
      color: var(--th-text-primary);
    }
  }
}
</style>