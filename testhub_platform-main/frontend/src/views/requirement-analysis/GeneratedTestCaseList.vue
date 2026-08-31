<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('generatedTestCases.title') }}</h1>
    </div>

    <div class="card-container">
      <el-table
        :data="tasks"
        v-loading="isLoading"
        style="width: 100%"
        border
        row-key="task_id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column :label="$t('generatedTestCases.serialNumber')" width="70" align="center">
          <template #default="{ $index }">
            {{ getSerialNumber($index) }}
          </template>
        </el-table-column>
        <el-table-column prop="task_id" :label="$t('generatedTestCases.taskId')" min-width="180" show-overflow-tooltip />
        <el-table-column :label="$t('generatedTestCases.requirement')" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="requirement-name">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('generatedTestCases.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('generatedTestCases.caseCount')" width="100" align="center">
          <template #default="{ row }">
            {{ getTestCaseCount(row) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('generatedTestCases.generationTime')" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('generatedTestCases.actions')" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewTaskDetail(row)">
              {{ $t('generatedTestCases.viewDetail') }}
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              type="success"
              @click="batchAdoptTask(row)"
            >
              {{ $t('generatedTestCases.batchAdopt') }}
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              type="danger"
              @click="batchDiscardTask(row)"
            >
              {{ $t('generatedTestCases.batchDiscard') }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-hint">
            <p class="empty-title">{{ $t('generatedTestCases.noTasks') }}</p>
            <p>
              {{ $t('generatedTestCases.emptyHint') }}
              <router-link to="/ai-generation/requirement-analysis">{{ $t('generatedTestCases.aiGeneration') }}</router-link>
              {{ $t('generatedTestCases.createTask') }}
            </p>
          </div>
        </template>
      </el-table>

      <div v-if="pagination.total > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="pagination.pageSizeOptions"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </div>

    <!-- 测试用例详情弹窗 -->
    <div v-if="selectedTestCaseDetail" class="testcase-detail-modal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ selectedTestCaseDetail.title }}</h3>
          <button class="close-btn" @click="closeTestCaseDetail">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.caseNumber') }}</label>
            <span>{{ selectedTestCaseDetail.case_id }}</span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.relatedRequirement') }}</label>
            <span>{{ selectedTestCaseDetail.requirement_name }} ({{ selectedTestCaseDetail.requirement_id_display }})</span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.priority') }}</label>
            <span class="priority-tag" :class="selectedTestCaseDetail.priority.toLowerCase()">
              {{ selectedTestCaseDetail.priority_display }}
            </span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.status') }}</label>
            <span class="status-tag" :class="selectedTestCaseDetail.status">
              {{ selectedTestCaseDetail.status_display }}
            </span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.preconditions') }}</label>
            <p>{{ selectedTestCaseDetail.precondition }}</p>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.testSteps') }}</label>
            <p class="test-steps" v-html="selectedTestCaseDetail.test_steps"></p>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.expectedResult') }}</label>
            <p v-html="selectedTestCaseDetail.expected_result"></p>
          </div>
          <div class="detail-item" v-if="selectedTestCaseDetail.review_comments">
            <label>{{ $t('generatedTestCases.reviewComments') }}</label>
            <p>{{ selectedTestCaseDetail.review_comments }}</p>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.generatedAI') }}</label>
            <span>{{ selectedTestCaseDetail.generated_by_ai }}</span>
          </div>
          <div class="detail-item" v-if="selectedTestCaseDetail.reviewed_by_ai">
            <label>{{ $t('generatedTestCases.reviewedAI') }}</label>
            <span>{{ selectedTestCaseDetail.reviewed_by_ai }}</span>
          </div>
          <div class="detail-item">
            <label>{{ $t('generatedTestCases.generatedTime') }}</label>
            <span>{{ formatDateTime(selectedTestCaseDetail.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 采纳用例编辑弹框 -->
    <div v-if="showAdoptModal" class="testcase-detail-modal">
      <div class="modal-content large-modal" @click.stop>
        <div class="modal-header">
          <h3>{{ $t('generatedTestCases.adoptModalTitle') }}</h3>
          <button class="close-btn" @click="closeAdoptModal">×</button>
        </div>
        <div class="modal-body">
          <form class="adopt-form">
            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.caseTitle') }}</label>
                <input v-model="adoptForm.title" type="text" :placeholder="$t('generatedTestCases.caseTitlePlaceholder')" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.caseDescription') }}</label>
                <textarea v-model="adoptForm.description" rows="3" :placeholder="$t('generatedTestCases.caseDescriptionPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.belongsToProject') }} <span class="required">*</span></label>
                <select v-model="adoptForm.project_id" @change="onAdoptProjectChange">
                  <option value="">{{ $t('generatedTestCases.selectProject') }}</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ $t('generatedTestCases.relatedVersion') }} <span class="required">*</span></label>
                <select v-model="adoptForm.version_id">
                  <option value="">{{ $t('generatedTestCases.selectVersion') }}</option>
                  <option v-for="version in availableVersions" :key="version.id" :value="version.id">
                    {{ version.name }}{{ version.is_baseline ? $t('generatedTestCases.baseline') : '' }}
                  </option>
                </select>
                <small class="form-hint">
                  {{ adoptForm.project_id ?
                      $t('generatedTestCases.showingProjectVersions', { project: getProjectName(adoptForm.project_id) }) :
                      $t('generatedTestCases.showingAllVersions') }}
                </small>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.priority') }}</label>
                <select v-model="adoptForm.priority">
                  <option value="P0">P0</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ $t('generatedTestCases.testType') }}</label>
                <select v-model="adoptForm.test_type">
                  <option value="functional">{{ $t('generatedTestCases.testTypeFunctional') }}</option>
                  <option value="integration">{{ $t('generatedTestCases.testTypeIntegration') }}</option>
                  <option value="api">{{ $t('generatedTestCases.testTypeAPI') }}</option>
                  <option value="ui">{{ $t('generatedTestCases.testTypeUI') }}</option>
                  <option value="performance">{{ $t('generatedTestCases.testTypePerformance') }}</option>
                  <option value="security">{{ $t('generatedTestCases.testTypeSecurity') }}</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.status') }}</label>
                <select v-model="adoptForm.status">
                  <option value="draft">{{ $t('generatedTestCases.statusDraft') }}</option>
                  <option value="active">{{ $t('generatedTestCases.statusActive') }}</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.preconditions') }}</label>
                <textarea v-model="adoptForm.preconditions" rows="3" :placeholder="$t('generatedTestCases.preconditionsPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.operationSteps') }}</label>
                <textarea v-model="adoptForm.steps" rows="6" :placeholder="$t('generatedTestCases.operationStepsPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('generatedTestCases.expectedResult') }}</label>
                <textarea v-model="adoptForm.expected_result" rows="3" :placeholder="$t('generatedTestCases.expectedResultPlaceholder')"></textarea>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="confirm-btn" @click="confirmAdopt" :disabled="isAdopting">
                {{ isAdopting ? $t('generatedTestCases.adopting') : $t('generatedTestCases.confirmAdopt') }}
              </button>
              <button type="button" class="cancel-btn" @click="closeAdoptModal">{{ $t('generatedTestCases.cancel') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'GeneratedTestCaseList',
  data() {
    return {
      isLoading: false,
      tasks: [], // 改为任务列表
      selectedTaskDetail: null,
      selectedTestCaseDetail: null,
      showAdoptModal: false,
      isAdopting: false,
      projects: [],
      projectVersions: [],
      allVersions: [], // 存储所有版本列表
      adoptForm: {
        title: '',
        description: '',
        project_id: null,
        priority: 'P2',
        test_type: 'functional',
        status: 'draft',
        preconditions: '',
        steps: '',
        expected_result: '',
        version_id: null // 改为单选
      },
      currentAdoptingTask: null,
      // 选择相关数据
      selectedTasks: [], // 已选中的任务ID列表
      isDeleting: false, // 是否正在删除
      // 分页相关数据
      pagination: {
        currentPage: 1,
        pageSize: 10,
        total: 0,
        pageSizeOptions: [10, 20, 50]
      }
    }
  },

  computed: {
    // 可用版本列表 - 根据是否选择项目来决定显示哪些版本
    availableVersions() {
      if (this.adoptForm.project_id) {
        return this.projectVersions
      } else {
        return this.allVersions
      }
    }
  },
  
  mounted() {
    this.loadTasks()
    this.fetchProjects()
    this.fetchAllVersions()
  },
  
  methods: {
    async loadTasks() {
      this.isLoading = true
      try {
        let url = '/requirement-analysis/testcase-generation/'
        const params = new URLSearchParams()
        
        params.append('page', String(this.pagination.currentPage))
        params.append('page_size', String(this.pagination.pageSize))
        
        if (params.toString()) {
          url += '?' + params.toString()
        }
        
        const response = await api.get(url)
        
        if (response.data.results) {
          this.tasks = response.data.results
          this.pagination.total = response.data.count || 0
        } else {
          this.tasks = response.data || []
          this.pagination.total = this.tasks.length
        }
        
      } catch (error) {
        console.error(this.$t('generatedTestCases.loadTasksFailed'), error)
        this.tasks = []
        this.pagination.total = 0
      } finally {
        this.isLoading = false
        this.selectedTasks = []
      }
    },

    getSerialNumber(index) {
      return (this.pagination.currentPage - 1) * this.pagination.pageSize + index + 1
    },

    handleSelectionChange(selection) {
      this.selectedTasks = selection.map(task => task.task_id)
    },

    // 批量删除任务
    async batchDeleteTasks() {
      if (this.selectedTasks.length === 0) {
        ElMessage.warning(this.$t('generatedTestCases.selectTasksFirst'))
        return
      }

      if (!confirm(this.$t('generatedTestCases.batchDeleteConfirm', { count: this.selectedTasks.length }))) {
        return
      }

      this.isDeleting = true
      let successCount = 0
      let failCount = 0

      try {
        // 逐个删除选中的任务
        for (const taskId of this.selectedTasks) {
          try {
            await api.delete(`/requirement-analysis/testcase-generation/${taskId}/`)
            successCount++
          } catch (error) {
            console.error(`删除任务 ${taskId} 失败:`, error)
            failCount++
          }
        }

        // 显示删除结果
        if (successCount > 0) {
          ElMessage.success(this.$t('generatedTestCases.deleteSuccess', { success: successCount, failed: failCount }))
        } else {
          ElMessage.error(this.$t('generatedTestCases.deleteFailed'))
        }

        // 清空选择并重新加载列表
        this.selectedTasks = []
        this.loadTasks()

      } catch (error) {
        console.error(this.$t('generatedTestCases.batchDeleteFailed'), error)
        ElMessage.error(this.$t('generatedTestCases.batchDeleteFailed') + ': ' + (error.message || this.$t('generatedTestCases.unknownError')))
      } finally {
        this.isDeleting = false
      }
    },

    getStatusText(status) {
      const statusMap = {
        'pending': this.$t('generatedTestCases.statusPending'),
        'generating': this.$t('generatedTestCases.statusGenerating'),
        'reviewing': this.$t('generatedTestCases.statusReviewing'),
        'revising': this.$t('generatedTestCases.statusRevising'),
        'completed': this.$t('generatedTestCases.statusCompleted'),
        'failed': this.$t('generatedTestCases.statusFailed')
      }
      return statusMap[status] || status
    },

    getStatusTagType(status) {
      const typeMap = {
        pending: 'info',
        generating: 'warning',
        reviewing: '',
        revising: 'warning',
        completed: 'success',
        failed: 'danger'
      }
      return typeMap[status] || 'info'
    },

    // 获取测试用例条数
    getTestCaseCount(task) {
      if (!task.final_test_cases) {
        return 0
      }

      // 解析测试用例内容，计算条数
      const content = task.final_test_cases
      const lines = content.split('\n').filter(line => line.trim())

      // 尝试表格格式
      let tableRows = 0
      let isFirstRow = true
      let isTableFormat = false

      for (let line of lines) {
        if (line.includes('|') && !line.includes('--------')) {
          const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell)
          if (cells.length > 1) {
            // 检查第一行是否是表头
            if (isFirstRow) {
              isFirstRow = false
              // 如果第一行包含表头标识，标记为表格格式
              if (line.includes('测试用例编号') || line.includes('ID') || line.includes('用例ID') ||
                  line.includes('场景') || line.includes('步骤')) {
                isTableFormat = true
                continue  // 跳过表头行
              }
            }

            tableRows++
            if (tableRows >= 1) {
              isTableFormat = true
            }
          }
        }
      }

      if (isTableFormat && tableRows > 0) {
        return tableRows
      }

      // 尝试结构化文本格式
      let caseCount = 0
      for (const line of lines) {
        if (line.includes('测试用例') || line.includes('Test Case') || line.match(/^(\d+\.|测试场景)/)) {
          caseCount++
        }
      }

      return caseCount || 0
    },

    viewTaskDetail(task) {
      if (['pending', 'generating', 'reviewing', 'revising'].includes(task.status)) {
        ElMessage.info(this.$t('generatedTestCases.generatingWait'))
        return
      }
      
      if (task.status === 'completed') {
        // 在新标签页打开任务详情
        const url = this.$router.resolve({
          name: 'TaskDetail',
          params: { taskId: task.task_id }
        }).href
        window.open(url, '_blank')
      }
    },

    async batchAdoptTask(task) {
      if (!confirm(this.$t('generatedTestCases.adoptConfirm', { title: task.title }))) {
        return
      }

      try {
        // 调用后端API批量采纳该任务的所有测试用例
        // await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch-adopt/`)
        await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch_adopt/`)
        ElMessage.success(this.$t('generatedTestCases.adoptSuccess'))
        this.loadTasks()
      } catch (error) {
        console.error(this.$t('generatedTestCases.adoptFailed'), error)
        ElMessage.error(this.$t('generatedTestCases.adoptFailed') + ': ' + (error.response?.data?.message || error.message))
      }
    },

    async batchDiscardTask(task) {
      if (!confirm(this.$t('generatedTestCases.discardConfirm', { title: task.title }))) {
        return
      }

      try {
        // 调用后端API批量删除该任务的所有测试用例
        // await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch-discard/`)
        await api.post(`/requirement-analysis/testcase-generation/${task.task_id}/batch_discard/`)
        ElMessage.success(this.$t('generatedTestCases.discardSuccess'))
        this.loadTasks()
      } catch (error) {
        console.error(this.$t('generatedTestCases.discardFailed'), error)
        ElMessage.error(this.$t('generatedTestCases.discardFailed') + ': ' + (error.response?.data?.message || error.message))
      }
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    // 获取项目列表
    async fetchProjects() {
      try {
        const response = await api.get('/projects/list/')
        this.projects = response.data.results || []
      } catch (error) {
        console.error(this.$t('generatedTestCases.fetchProjectsFailed'), error)
      }
    },

    // 获取所有版本列表
    async fetchAllVersions() {
      try {
        const response = await api.get('/versions/')
        this.allVersions = response.data.results || response.data || []
      } catch (error) {
        console.error(this.$t('generatedTestCases.fetchVersionsFailed'), error)
        this.allVersions = []
      }
    },

    // 获取项目版本列表
    async fetchProjectVersions(projectId) {
      if (!projectId) {
        this.projectVersions = []
        return
      }

      try {
        const response = await api.get(`/versions/projects/${projectId}/versions/`)
        this.projectVersions = response.data || []
      } catch (error) {
        console.error(this.$t('generatedTestCases.fetchProjectVersionsFailed'), error)
        this.projectVersions = []
      }
    },

    // 采纳测试用例
    async adoptTestCase(testCase) {
      this.currentAdoptingTask = testCase
      
      // 预填充表单数据
      this.adoptForm = {
        title: testCase.title,
        description: testCase.title, // 用标题作为描述的默认值
        project_id: null,
        priority: 'P2',
        test_type: 'functional',
        status: 'draft',
        preconditions: testCase.precondition || '',
        steps: testCase.test_steps || '',
        expected_result: testCase.expected_result || '',
        version_id: null // 改为单选
      }
      
      this.showAdoptModal = true
    },

    // 项目改变时的处理
    async onAdoptProjectChange() {
      if (this.adoptForm.project_id) {
        // 选择了项目，加载该项目的版本
        await this.fetchProjectVersions(this.adoptForm.project_id)
        
        // 检查当前选择的版本是否属于新项目，如果不属于则清空
        if (this.adoptForm.version_id) {
          const versionExists = this.projectVersions.some(v => v.id === this.adoptForm.version_id)
          if (!versionExists) {
            this.adoptForm.version_id = null
          }
        }
      } else {
        // 清空项目选择时，清空项目版本列表
        // 此时版本下拉会自动切换到显示所有版本（通过computed属性）
        this.projectVersions = []
        // 保持当前版本选择，因为可以从所有版本中选择
      }
    },

    // 确认采纳
    async confirmAdopt() {
      // 必填项验证
      if (!this.adoptForm.project_id) {
        alert(this.$t('generatedTestCases.selectProjectRequired'))
        return
      }

      if (!this.adoptForm.version_id) {
        alert(this.$t('generatedTestCases.selectVersionRequired'))
        return
      }

      if (!this.adoptForm.title.trim()) {
        alert(this.$t('generatedTestCases.enterCaseTitle'))
        return
      }

      if (!this.adoptForm.expected_result.trim()) {
        alert(this.$t('generatedTestCases.enterExpectedResult'))
        return
      }
      
      this.isAdopting = true
      
      try {
        // 准备提交的数据，将单选版本转换为数组格式（如果API需要）
        const submitData = {
          title: this.adoptForm.title,
          description: this.adoptForm.description,
          project_id: this.adoptForm.project_id,
          priority: this.adoptForm.priority || 'P2',
          test_type: this.adoptForm.test_type,
          status: this.adoptForm.status,
          preconditions: this.adoptForm.preconditions,
          steps: this.adoptForm.steps,
          expected_result: this.adoptForm.expected_result,
          version_ids: this.adoptForm.version_id ? [this.adoptForm.version_id] : []
        }
        
        // 确保优先级有默认值
        if (!submitData.priority) {
          submitData.priority = 'P2'
        }
        
        // 调用API创建测试用例
        await api.post('/testcases/', submitData)
        
        // 将AI生成的用例状态更新为"已采纳"
        try {
          await api.patch(`/requirement-analysis/test-cases/${this.currentAdoptingTask.id}/`, {
            status: 'adopted'
          })
        } catch (updateError) {
          console.warn(this.$t('generatedTestCases.updateStatusFailed'), updateError)
          // 即使状态更新失败，用例已成功导入，仍然提示成功
        }

        alert(this.$t('generatedTestCases.adoptModalSuccess'))
        this.closeAdoptModal()
        this.loadTestCases() // 重新加载列表

      } catch (error) {
        console.error(this.$t('generatedTestCases.adoptCaseFailed'), error)
        alert(this.$t('generatedTestCases.adoptCaseFailedRetry'))
      } finally{
        this.isAdopting = false
      }
    },

    // 弃用测试用例
    async discardTestCase(testCase) {
      if (!confirm(this.$t('generatedTestCases.discardCaseConfirm', { title: testCase.title }))) {
        return
      }

      try {
        // 将状态更新为"已弃用"
        await api.patch(`/requirement-analysis/test-cases/${testCase.id}/`, {
          status: 'discarded'
        })
        alert(this.$t('generatedTestCases.caseDiscarded'))
        this.loadTestCases() // 重新加载列表，已弃用的用例会被过滤掉
      } catch (error) {
        console.error(this.$t('generatedTestCases.discardCaseFailed'), error)
        alert(this.$t('generatedTestCases.discardCaseFailedRetry'))
      }
    },

    // 关闭采纳弹框
    closeAdoptModal() {
      this.showAdoptModal = false
      this.currentAdoptingTask = null
      this.projectVersions = []
    },

    // 关闭测试用例详情弹窗
    closeTestCaseDetail() {
      this.selectedTestCaseDetail = null
    },

    // 加载测试用例列表（别名，与loadTasks一致）
    loadTestCases() {
      this.loadTasks()
    },

    // 分页相关方法
    onPageSizeChange() {
      this.pagination.currentPage = 1
      this.loadTasks()
    },

    handlePageChange() {
      this.loadTasks()
    },

    // 获取项目名称的辅助方法
    getProjectName(projectId) {
      const project = this.projects.find(p => p.id === projectId)
      return project ? project.name : ''
    }
  }
}
</script>

<style scoped>
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.requirement-name {
  font-weight: 500;
  color: var(--th-text-primary);
}

.empty-hint {
  padding: 24px 12px;
  color: var(--th-text-secondary);
  line-height: 1.6;
}

.empty-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--th-text-primary);
}

.empty-hint a {
  color: var(--th-color-primary);
  text-decoration: none;
}

.empty-hint a:hover {
  text-decoration: underline;
}

/* 弹窗 */
.testcase-detail-modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--th-bg-elevated);
  border-radius: var(--th-radius-lg);
  border: 1px solid var(--th-border);
  box-shadow: var(--th-shadow-lg);
  padding: 0;
  max-width: 800px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.large-modal {
  max-width: 900px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--th-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--th-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.4rem;
  cursor: pointer;
  color: var(--th-text-secondary);
  line-height: 1;
}

.close-btn:hover {
  color: var(--th-text-primary);
}

.modal-body {
  padding: 24px;
}

.detail-item {
  margin-bottom: 18px;
}

.detail-item label {
  font-weight: 600;
  color: var(--th-text-primary);
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
}

.detail-item span,
.detail-item p {
  color: var(--th-text-regular);
  line-height: 1.6;
  margin: 0;
}

.test-steps {
  white-space: pre-line;
  line-height: 1.6;
  background: var(--th-bg-muted);
  padding: 14px;
  border-radius: var(--th-radius-sm);
  border-left: 3px solid var(--th-color-primary);
}

.priority-tag,
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.priority-tag.p0,
.priority-tag.critical {
  background: #fef2f2;
  color: #dc2626;
}

.priority-tag.p1,
.priority-tag.high {
  background: #fff7ed;
  color: #ea580c;
}

.priority-tag.p2,
.priority-tag.medium {
  background: #eff6ff;
  color: #2563eb;
}

.priority-tag.p3,
.priority-tag.low {
  background: #f0fdf4;
  color: #16a34a;
}

.status-tag.pending {
  background: #f3f4f6;
  color: #6b7280;
}

.status-tag.generating,
.status-tag.reviewing {
  background: #fff7ed;
  color: #ea580c;
}

.status-tag.completed {
  background: #f0fdf4;
  color: #16a34a;
}

.status-tag.failed {
  background: #fef2f2;
  color: #dc2626;
}

.adopt-form {
  max-width: 100%;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  color: var(--th-text-primary);
  margin-bottom: 6px;
  font-size: 13px;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 8px 12px;
  border: 1px solid var(--th-border);
  border-radius: var(--th-radius-sm);
  font-size: 14px;
  background: var(--th-bg-elevated);
  color: var(--th-text-regular);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--th-color-primary);
  box-shadow: 0 0 0 2px var(--th-color-primary-soft);
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.form-hint {
  color: var(--th-text-secondary);
  font-size: 12px;
  margin-top: 4px;
}

.required {
  color: #ef4444;
  font-weight: 600;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--th-border);
}

.confirm-btn {
  background: var(--th-accent-green);
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: var(--th-radius-sm);
  cursor: pointer;
  font-size: 14px;
}

.confirm-btn:hover:not(:disabled) {
  filter: brightness(0.95);
}

.confirm-btn:disabled {
  background: #c4c9d4;
  cursor: not-allowed;
}

.cancel-btn {
  background: #eef1f7;
  color: var(--th-text-regular);
  border: none;
  padding: 10px 20px;
  border-radius: var(--th-radius-sm);
  cursor: pointer;
  font-size: 14px;
}

.cancel-btn:hover {
  background: #e4e8f0;
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
    gap: 12px;
  }

  .large-modal {
    max-width: 95%;
  }

  .pagination-container {
    justify-content: center;
  }
}
</style>