<template>
  <div class="execution-detail">
    <!-- 测试执行区域 -->
    <div v-if="testPlan.test_runs && testPlan.test_runs.length > 0">
      <div v-for="run in testPlan.test_runs" :key="run.id" class="test-run-card">
        <!-- 美化的运行头部 -->
        <div class="run-header">
          <div class="run-title-section">
            <el-button class="back-button" :icon="ArrowLeft" circle @click="$router.back()" />
            <h2 class="run-title">{{ testPlan.name }}</h2>
            <el-tag :type="getRunStatusType(run.progress)" size="large" class="run-status-tag">
              {{ getRunStatusText(run.progress) }}
            </el-tag>
          </div>

          <!-- 美化的统计卡片 -->
          <div class="stats-cards">
            <div class="stat-card total">
              <el-icon class="stat-icon"><Document /></el-icon>
              <div class="stat-content">
                <div class="stat-value">{{ run.progress.total }}</div>
                <div class="stat-label">{{ $t('execution.total') }}</div>
              </div>
            </div>
            <div class="stat-card passed">
              <el-icon class="stat-icon"><CircleCheck /></el-icon>
              <div class="stat-content">
                <div class="stat-value">{{ run.progress.passed }}</div>
                <div class="stat-label">{{ $t('execution.passed') }}</div>
              </div>
            </div>
            <div class="stat-card failed">
              <el-icon class="stat-icon"><CircleClose /></el-icon>
              <div class="stat-content">
                <div class="stat-value">{{ run.progress.failed }}</div>
                <div class="stat-label">{{ $t('execution.failed') }}</div>
              </div>
            </div>
            <div class="stat-card blocked">
              <el-icon class="stat-icon"><WarningFilled /></el-icon>
              <div class="stat-content">
                <div class="stat-value">{{ run.progress.blocked }}</div>
                <div class="stat-label">{{ $t('execution.blocked') }}</div>
              </div>
            </div>
            <div class="stat-card untested">
              <el-icon class="stat-icon"><QuestionFilled /></el-icon>
              <div class="stat-content">
                <div class="stat-value">{{ run.progress.untested }}</div>
                <div class="stat-label">{{ $t('execution.untested') }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 进度条 -->
        <div class="progress-section">
          <el-progress
            :percentage="run.progress.progress"
            :stroke-width="12"
            :color="getProgressColor(run.progress.progress)"
            :show-text="true">
            <template #default="{ percentage }">
              <span class="progress-text">{{ percentage }}%</span>
            </template>
          </el-progress>
        </div>

        <!-- 筛选栏：位于进度条与用例列表之间 -->
        <div class="filter-bar">
          <el-input
            v-model="filterCaseNumber"
            :placeholder="$t('testcase.caseNumber')"
            clearable
            size="small"
            class="filter-item"
          />
          <el-input
            v-model="filterCaseTitle"
            :placeholder="$t('testcase.caseTitle')"
            clearable
            size="small"
            class="filter-item"
          />
          <el-select
            v-model="filterPriority"
            :placeholder="$t('testcase.priority')"
            clearable
            size="small"
            class="filter-item filter-select"
          >
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
          <el-select
            v-model="filterStatus"
            :placeholder="$t('execution.executionStatus')"
            clearable
            size="small"
            class="filter-item filter-select"
          >
            <el-option :label="$t('execution.untested')" value="untested" />
            <el-option :label="$t('execution.passed')" value="passed" />
            <el-option :label="$t('execution.failed')" value="failed" />
            <el-option :label="$t('execution.blocked')" value="blocked" />
            <el-option :label="$t('execution.retest')" value="retest" />
            <el-option :label="$t('execution.na')" value="na" />
          </el-select>
          <el-button
            size="small"
            @click="resetFilters"
          >{{ $t('common.reset') }}</el-button>
        </div>

        <!-- 用例列表：左侧 L1/L2/L3 树 + 右侧列表/详情（与用例库一致） -->
        <RunCaseTree
          :cases="run.run_cases"
          :filter-case-number="filterCaseNumber"
          :filter-case-title="filterCaseTitle"
          :filter-priority="filterPriority"
          :filter-status="filterStatus"
          @changed="fetchTestPlan"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  Document, CircleCheck, CircleClose,
  WarningFilled, QuestionFilled, ArrowLeft
} from '@element-plus/icons-vue'
import axios from 'axios'
import RunCaseTree from './RunCaseTree.vue'

const { t } = useI18n()

const route = useRoute()
const testPlan = ref({})

// 筛选状态（筛选栏显示在进度条与用例列表之间）
const filterCaseNumber = ref('')
const filterCaseTitle = ref('')
const filterPriority = ref('')
const filterStatus = ref('')

const resetFilters = () => {
  filterCaseNumber.value = ''
  filterCaseTitle.value = ''
  filterPriority.value = ''
  filterStatus.value = ''
}

const fetchTestPlan = async () => {
  try {
    const planId = route.params.id
    const response = await axios.get(`/api/executions/plans/${planId}/`)
    testPlan.value = response.data
  } catch (error) {
    ElMessage.error(t('execution.fetchDetailFailed'))
  }
}

const getProgressColor = (percentage) => {
  if (percentage < 30) return '#f56c6c'
  if (percentage < 70) return '#e6a23c'
  return '#67c23a'
}

const getRunStatusType = (progress) => {
  if (progress.progress === 100) return 'success'
  if (progress.failed > 0) return 'danger'
  if (progress.blocked > 0) return 'warning'
  return 'info'
}

const getRunStatusText = (progress) => {
  if (progress.progress === 100) return t('execution.completed')
  if (progress.untested === progress.total) return t('execution.notStarted')
  return t('execution.inProgress')
}

onMounted(() => {
  fetchTestPlan()
})
</script>

<style scoped>
.execution-detail {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.back-button {
  background: transparent;
  border-color: transparent;
  color: #303133;
  flex-shrink: 0;
}

.back-button:hover,
.back-button:focus {
  background: #f5f7fa;
  border-color: transparent;
  color: #303133;
}

.back-button:active {
  background: #ebeef5;
  border-color: transparent;
  color: #303133;
}

.test-run-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.run-header {
  margin-bottom: 24px;
}

.run-title-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.run-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  line-height: 1;
  display: inline-flex;
  align-items: center;
}

.run-status-tag {
  font-weight: 600;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-card.total {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stat-card.passed {
  background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
  color: #155724;
}

.stat-card.failed {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  color: #721c24;
}

.stat-card.blocked {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  color: #856404;
}

.stat-card.untested {
  background: linear-gradient(135deg, #e0e7ff 0%, #cfd9ff 100%);
  color: #383d41;
}

.stat-icon {
  font-size: 32px;
  opacity: 0.9;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.9;
}

.progress-section {
  margin-bottom: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-shrink: 0;
  flex-wrap: wrap;

  .filter-item {
    width: 180px;
  }

  .filter-select {
    width: 140px;
  }

  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    border-radius: 20px;
    background: #fff;
  }
}

.progress-text {
  font-weight: 600;
  font-size: 14px;
}
</style>
