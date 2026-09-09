<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('testcase.detail') }}</h1>
      <div>
        <el-button @click="$router.back()">{{ $t('common.back') }}</el-button>
        <el-button type="primary" @click="editTestCase">{{ $t('common.edit') }}</el-button>
      </div>
    </div>

    <div class="card-container" v-if="testcase">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="$t('testcase.tabBasic')" name="basic">
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="$t('testcase.caseTitle')" :span="2">{{ testcase.title }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.priority')">
              <el-tag :class="`priority-tag ${testcase.priority}`">{{ getPriorityText(testcase.priority) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.testType')">{{ getTypeText(testcase.test_type) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.caseType')">{{ getCaseTypeText(testcase.case_type) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.project')">{{ testcase.project?.name || $t('testcase.noProject') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.relatedVersions')" :span="2">
              <div v-if="testcase.versions && testcase.versions.length > 0" class="version-tags">
                <el-tag
                  v-for="version in testcase.versions"
                  :key="version.id"
                  size="small"
                  :type="version.is_baseline ? 'warning' : 'info'"
                  class="version-tag"
                >
                  {{ version.name }}
                </el-tag>
              </div>
              <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.author')">{{ testcase.author?.username }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.createdAt')" :span="2">{{ formatDate(testcase.created_at) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l1')">{{ testcase.l1 || $t('testcase.none') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l2')">{{ testcase.l2 || $t('testcase.none') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.l3')" :span="2">{{ testcase.l3 || $t('testcase.none') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.caseDescription')" :span="2">{{ testcase.description || $t('testcase.noDescription') }}</el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.preconditions')" :span="2">
              <div v-html="testcase.preconditions || $t('testcase.none')"></div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.steps')" :span="2">
              <div class="steps-content" v-html="testcase.steps || $t('testcase.none')"></div>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('testcase.expectedResult')" :span="2">
              <div v-html="testcase.expected_result || $t('testcase.none')"></div>
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane :label="$t('testcase.tabUi')" name="ui">
          <div class="tab-actions">
            <el-button type="primary" @click="editTestCase">{{ $t('testcase.goEdit') }}</el-button>
            <el-button @click="handleAiGenerateSteps('ui')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
          </div>
          <el-empty :description="$t('testcase.tabEmpty')" />
        </el-tab-pane>
        <el-tab-pane :label="$t('testcase.tabApi')" name="api">
          <div class="tab-actions">
            <el-button type="primary" @click="editTestCase">{{ $t('testcase.goEdit') }}</el-button>
            <el-button @click="handleAiGenerateSteps('api')">{{ $t('testcase.aiGenerateSteps') }}</el-button>
          </div>
          <el-empty :description="$t('testcase.tabEmpty')" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const testcase = ref(null)
const activeTab = ref('basic')

const fetchTestCase = async () => {
  try {
    const response = await api.get(`/testcases/${route.params.id}/`)
    testcase.value = response.data
  } catch (error) {
    ElMessage.error(t('testcase.fetchDetailFailed'))
  }
}

const editTestCase = () => {
  router.push(`/ai-generation/testcases/${route.params.id}/edit`)
}

const handleAiGenerateSteps = () => {
  ElMessage.info(t('testcase.aiGenerateStepsTodo'))
}

const getPriorityText = (priority) => {
  const textMap = {
    P0: t('testcase.p0'),
    P1: t('testcase.p1'),
    P2: t('testcase.p2'),
    P3: t('testcase.p3')
  }
  return textMap[priority] || priority
}

const getTypeText = (type) => {
  const textMap = {
    functional: t('testcase.functional'),
    integration: t('testcase.integration'),
    api: t('testcase.api'),
    ui: t('testcase.ui'),
    performance: t('testcase.performance'),
    security: t('testcase.security')
  }
  return textMap[type] || '-'
}

const getCaseTypeText = (caseType) => {
  const textMap = {
    manual: t('testcase.caseTypeManual'),
    ui: t('testcase.caseTypeUi'),
    api: t('testcase.caseTypeApi')
  }
  const values = Array.isArray(caseType)
    ? caseType
    : (typeof caseType === 'string' && caseType.trim()
      ? caseType.split(/[,，、;；]/).map(v => v.trim()).filter(Boolean)
      : [])
  if (!values.length) return '-'
  return values.map(v => textMap[v] || v).join('、')
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchTestCase()
})
</script>

<style lang="scss" scoped>
.priority-tag {
  &.P0 { color: #f56c6c; font-weight: bold; }
  &.P1 { color: #f56c6c; }
  &.P2 { color: #e6a23c; }
  &.P3 { color: #67c23a; }
  /* 兼容旧值（迁移前的数据） */
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.critical { color: #f56c6c; font-weight: bold; }
}

.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  
  .version-tag {
    margin: 0;
  }
}

.no-version {
  color: #909399;
  font-size: 14px;
  font-style: italic;
}

.steps-content {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #303133;
  font-family: inherit;
}

.tab-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 8px 0;

  .el-button--primary {
    box-shadow: none;
  }
}
</style>