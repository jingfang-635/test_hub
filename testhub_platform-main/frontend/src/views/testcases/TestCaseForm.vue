<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('testcase.create') }}</h1>
    </div>

    <div class="card-container">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item :label="$t('testcase.caseTitle')" prop="title">
          <el-input v-model="form.title" :placeholder="$t('testcase.caseTitlePlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('testcase.preconditions')" prop="preconditions">
          <el-input
            v-model="form.preconditions"
            type="textarea"
            :rows="3"
            :placeholder="$t('testcase.preconditionsPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('testcase.steps')" prop="steps">
          <el-input
            v-model="form.steps"
            type="textarea"
            :rows="6"
            maxlength="1000"
            show-word-limit
            :placeholder="$t('testcase.stepsPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('testcase.expectedResult')" prop="expected_result">
          <el-input
            v-model="form.expected_result"
            type="textarea"
            :rows="3"
            :placeholder="$t('testcase.expectedResultPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('testcase.caseRemark')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            :placeholder="$t('testcase.caseRemarkPlaceholder')"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item :label="$t('testcase.project')" prop="project_id">
              <el-select
                v-model="form.project_id"
                :placeholder="$t('testcase.selectProject')"
                clearable
                filterable
                @change="onProjectChange"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('testcase.priority')" prop="priority">
              <el-select v-model="form.priority" :placeholder="$t('testcase.selectPriority')">
                <el-option :label="$t('testcase.p0')" value="P0" />
                <el-option :label="$t('testcase.p1')" value="P1" />
                <el-option :label="$t('testcase.p2')" value="P2" />
                <el-option :label="$t('testcase.p3')" value="P3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('testcase.testType')" prop="test_type">
              <el-select v-model="form.test_type" :placeholder="$t('testcase.selectTestType')">
                <el-option :label="$t('testcase.functional')" value="functional" />
                <el-option :label="$t('testcase.integration')" value="integration" />
                <el-option :label="$t('testcase.api')" value="api" />
                <el-option :label="$t('testcase.ui')" value="ui" />
                <el-option :label="$t('testcase.performance')" value="performance" />
                <el-option :label="$t('testcase.security')" value="security" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('testcase.caseType')" prop="case_type">
              <el-select
                v-model="form.case_type"
                :placeholder="$t('testcase.selectCaseType')"
                multiple
                clearable
              >
                <el-option :label="$t('testcase.caseTypeManual')" value="manual" />
                <el-option :label="$t('testcase.caseTypeUi')" value="ui" />
                <el-option :label="$t('testcase.caseTypeApi')" value="api" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item :label="$t('testcase.relatedVersions')" prop="version_ids">
              <el-select
                v-model="form.version_ids"
                :placeholder="$t('testcase.selectVersions')"
                multiple
                clearable
                filterable
                @change="onVersionChange"
              >
                <el-option
                  v-for="version in projectVersions"
                  :key="version.id"
                  :label="version.name + (version.is_baseline ? ' (' + $t('testcase.baseline') + ')' : '')"
                  :value="version.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item :label="$t('testcase.l1')" prop="l1">
              <el-input v-model="form.l1" :placeholder="$t('testcase.l1Placeholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('testcase.l2')" prop="l2">
              <el-input v-model="form.l2" :placeholder="$t('testcase.l2Placeholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('testcase.l3')" prop="l3">
              <el-input v-model="form.l3" :placeholder="$t('testcase.l3Placeholder')" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">
            {{ $t('testcase.createCase') }}
          </el-button>
          <el-button @click="$router.back()">{{ $t('common.cancel') }}</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const { t } = useI18n()
const router = useRouter()
const formRef = ref()
const submitting = ref(false)
const projects = ref([])
const projectVersions = ref([])

const form = reactive({
  title: '',
  description: '',
  project_id: null,
  priority: 'P2',
  test_type: 'functional',
  preconditions: '',
  case_type: ['manual'],
  steps: '',
  expected_result: '',
  l1: '',
  l2: '',
  l3: '',
  version_ids: []
})

const rules = {
  title: [
    { required: true, message: computed(() => t('testcase.titleRequired')), trigger: 'blur' },
    { min: 5, max: 500, message: computed(() => t('testcase.titleLength')), trigger: 'blur' }
  ],
  steps: [
    { required: true, message: computed(() => t('testcase.stepsRequired')), trigger: 'blur' },
    { max: 1000, message: computed(() => t('testcase.stepsMaxLength')), trigger: 'blur' }
  ],
  expected_result: [
    { required: true, message: computed(() => t('testcase.expectedResultRequired')), trigger: 'blur' }
  ],
  project_id: [
    { required: true, message: computed(() => t('testcase.projectRequired')), trigger: 'change' }
  ],
  priority: [
    { required: true, message: computed(() => t('testcase.priorityRequired')), trigger: 'change' }
  ],
  test_type: [
    { required: true, message: computed(() => t('testcase.testTypeRequired')), trigger: 'change' }
  ],
  case_type: [
    { required: true, type: 'array', min: 1, message: computed(() => t('testcase.caseTypeRequired')), trigger: 'change' }
  ],
  version_ids: [
    { required: true, type: 'array', message: computed(() => t('testcase.versionsRequired')), trigger: 'change' }
  ],
  l1: [
    {
      validator: (rule, value, callback) => {
        if (!value || !value.trim()) {
          callback(new Error(t('testcase.l1Required')))
          return
        }
        const project = projects.value.find(p => p.id === form.project_id)
        if (project && value.trim() !== project.name) {
          callback(new Error(t('testcase.l1MustMatchProject', { projectName: project.name })))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ],
  l2: [
    { required: true, message: computed(() => t('testcase.l2Required')), trigger: 'blur' }
  ],
  l3: [
    { required: true, message: computed(() => t('testcase.l3Required')), trigger: 'blur' }
  ]
}

const fetchProjects = async () => {
  // 与「项目与版本」一致：仅显示关联了 AI用例生成 的项目
  try {
    const response = await api.get('/projects/list/', {
      params: { project_type: 'ai_generation' }
    })
    projects.value = response.data.results || []
  } catch (error) {
    ElMessage.error(t('testcase.fetchProjectsFailed'))
  }
}

const fetchProjectVersions = async (projectId) => {
  if (!projectId) {
    projectVersions.value = []
    return
  }

  try {
    const response = await api.get(`/versions/projects/${projectId}/versions/`)
    projectVersions.value = response.data || []
  } catch (error) {
    console.error(t('testcase.fetchVersionsFailed'), error)
    ElMessage.error(t('testcase.fetchVersionsFailed'))
    projectVersions.value = []
  }
}

const onProjectChange = (projectId) => {
  form.version_ids = []
  fetchProjectVersions(projectId)
  // 选择项目后自动填充 L1 为项目名
  const project = projects.value.find(p => p.id === projectId)
  form.l1 = project ? project.name : ''
  // 项目变化后重新校验 L1（依赖项目名）
  formRef.value && formRef.value.validateField('l1')
}

const onVersionChange = () => {
  // Version change handling logic if needed
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        await api.post('/testcases/', form)
        ElMessage.success(t('testcase.createSuccess'))
        router.push('/ai-generation/testcases')
      } catch (error) {
        // 后端校验错误（如用例标题重复、L1 与项目名不一致）优先展示具体信息
        const errData = error.response?.data
        let msg = t('testcase.createFailed')
        if (errData) {
          if (typeof errData.detail === 'string') {
            msg = errData.detail
          } else {
            // 遍历所有字段错误，取第一条
            for (const key in errData) {
              const v = errData[key]
              if (Array.isArray(v) && v.length) {
                msg = v[0]
                break
              }
            }
          }
        }
        ElMessage.error(msg)
        console.error('Submit error:', error)
      } finally {
        submitting.value = false
      }
    }
  })
}

onMounted(() => {
  fetchProjects()
})
</script>
