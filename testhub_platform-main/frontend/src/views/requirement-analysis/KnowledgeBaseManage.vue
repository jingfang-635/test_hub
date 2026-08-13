<template>
  <div class="knowledge-base-manage">
    <!-- 列表页 -->
    <template v-if="!selectedBase">
      <div class="page-header">
        <div class="header-left">
          <h1>{{ $t('knowledgeBase.title') }}</h1>
          <p>{{ $t('knowledgeBase.subtitle') }}</p>
        </div>
        <el-button type="primary" @click="openAddModal">
          <el-icon><Plus /></el-icon>
          {{ $t('knowledgeBase.addBase') }}
        </el-button>
      </div>

      <div class="filter-bar">
        <el-select
          v-model="projectFilter"
          :placeholder="$t('knowledgeBase.project')"
          clearable
          style="width: 240px"
          @change="loadBases"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
      </div>

      <div class="stats-row">
        <div class="stat-card stat-blue">
          <div class="stat-value">{{ bases.length }}</div>
          <div class="stat-label">{{ $t('knowledgeBase.totalCount') }}</div>
        </div>
        <div class="stat-card stat-orange">
          <div class="stat-value">{{ formatFileSize(totalSize) }}</div>
          <div class="stat-label">{{ $t('knowledgeBase.totalSize') }}</div>
        </div>
      </div>

      <el-card shadow="never" class="table-card" v-loading="loading">
        <el-table :data="bases" style="width: 100%" empty-text="-">
          <el-table-column type="index" :label="$t('knowledgeBase.index')" width="70" />
          <el-table-column prop="name" :label="$t('knowledgeBase.name')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="project_name" :label="$t('knowledgeBase.project')" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.project_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_by_name" :label="$t('knowledgeBase.creator')" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.created_by_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.createdAt')" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.actions')" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDocuments(row)">{{ $t('knowledgeBase.detail') }}</el-button>
              <el-button link type="primary" @click="editBase(row)">{{ $t('knowledgeBase.edit') }}</el-button>
              <el-button link type="danger" @click="removeBase(row)">{{ $t('knowledgeBase.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 知识库详情页 -->
    <template v-else>
      <div class="detail-page">
        <div class="detail-header">
          <el-button class="back-btn" link type="primary" @click="backToList">
            ← {{ $t('knowledgeBase.backToList') }}
          </el-button>
          <h1 class="detail-title">{{ selectedBase.name }}</h1>
          <el-tag
            :type="selectedBase.is_active ? 'success' : 'info'"
            size="small"
            effect="light"
            class="status-tag"
          >
            {{ selectedBase.is_active ? $t('knowledgeBase.enabled') : $t('knowledgeBase.disabled') }}
          </el-tag>
        </div>

        <!-- 基本信息 -->
        <el-card shadow="never" class="section-card info-card">
          <el-descriptions :column="3" border class="kb-descriptions">
            <el-descriptions-item :label="$t('knowledgeBase.project')">
              {{ selectedBase.project_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('knowledgeBase.chunkSize')">
              {{ selectedBase.chunk_size ?? 500 }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('knowledgeBase.chunkOverlap')">
              {{ selectedBase.chunk_overlap ?? 50 }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('knowledgeBase.vectorStatus')">
              <el-tag :type="vectorStatusTagType" size="small" effect="light">
                {{ vectorStatusLabel }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('knowledgeBase.totalSize')">
              {{ formatFileSize(detailTotalSize) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 文档列表 -->
        <el-card shadow="never" class="section-card" v-loading="docsLoading">
          <template #header>
            <div class="section-header">
              <span class="section-title">
                {{ $t('knowledgeBase.documentCount') }} ({{ documents.length }})
              </span>
              <el-upload
                multiple
                :auto-upload="false"
                :show-file-list="false"
                accept=".pdf,.doc,.docx,.txt,.md"
                :disabled="isUploading"
                :on-change="onUploadChange"
              >
                <el-button link type="primary" :loading="isUploading" class="upload-link">
                  +{{ $t('knowledgeBase.uploadDocument') }}
                </el-button>
              </el-upload>
            </div>
          </template>

          <el-table :data="documents" style="width: 100%" class="doc-table">
            <el-table-column type="index" :label="$t('knowledgeBase.index')" width="70" />
            <el-table-column prop="title" :label="$t('knowledgeBase.documentTitle')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="doc-title">{{ row.title }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('knowledgeBase.documentType')" width="140">
              <template #default="{ row }">
                {{ row.document_type_display || formatDocType(row.document_type) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('knowledgeBase.vectorStatus')" width="130">
              <template #default="{ row }">
                <el-tag :type="docVectorTagType(row)" size="small" effect="light">
                  {{ docVectorLabel(row) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('knowledgeBase.createdAt')" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('knowledgeBase.actions')" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="viewOriginal(row)">
                  {{ $t('knowledgeBase.viewOriginal') }}
                </el-button>
                <el-button link type="danger" @click="removeDocument(row)">
                  {{ $t('knowledgeBase.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 混合检索 -->
        <el-card shadow="never" class="section-card search-card">
          <div class="search-type-tabs">
            <button
              v-for="item in searchTypeOptions"
              :key="item.value"
              type="button"
              class="search-type-btn"
              :class="{ active: searchForm.searchType === item.value }"
              @click="searchForm.searchType = item.value"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="search-input-row">
            <el-input
              v-model="searchForm.query"
              clearable
              :placeholder="$t('knowledgeBase.searchPlaceholder')"
              class="search-input"
              @keyup.enter="runSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" class="search-btn" :loading="searchLoading" @click="runSearch">
              <el-icon><Search /></el-icon>
              {{ $t('knowledgeBase.search') }}
            </el-button>
          </div>

          <div class="search-params">
            <div class="param-item param-slider" v-if="searchForm.searchType !== 'keyword'">
              <label>{{ $t('knowledgeBase.similarityThreshold') }}</label>
              <div class="slider-row">
                <el-slider
                  v-model="searchForm.similarity"
                  :min="0"
                  :max="100"
                  :show-tooltip="true"
                  :format-tooltip="(v) => `${v}%`"
                />
                <span class="slider-value">{{ searchForm.similarity }}%</span>
              </div>
            </div>

            <div class="param-item param-recall">
              <label>{{ $t('knowledgeBase.recallCount') }}</label>
              <el-input-number
                v-model="searchForm.recallCount"
                :min="1"
                :max="50"
                controls-position="right"
                class="recall-input"
              />
            </div>

            <div class="param-item param-slider" v-if="searchForm.searchType === 'hybrid'">
              <label>
                {{ $t('knowledgeBase.vectorRatio') }}
                <el-tooltip :content="$t('knowledgeBase.vectorRatioTip')" placement="top">
                  <el-icon class="label-tip"><InfoFilled /></el-icon>
                </el-tooltip>
              </label>
              <div class="slider-row">
                <el-slider
                  v-model="searchForm.vectorRatio"
                  :min="0"
                  :max="100"
                  :show-tooltip="true"
                  :format-tooltip="(v) => `${v}%`"
                />
                <span class="slider-value">{{ searchForm.vectorRatio }}%</span>
              </div>
            </div>
          </div>

          <div v-if="searchResults.length" class="search-results">
            <div class="search-results-title">
              {{ $t('knowledgeBase.searchResults') }} ({{ searchResults.length }})
            </div>
            <div
              v-for="(item, idx) in searchResults"
              :key="`${item.id}-${idx}`"
              class="search-result-item"
            >
              <div class="result-meta">
                <span class="result-index">#{{ idx + 1 }}</span>
                <span class="result-title">{{ item.title }}</span>
                <el-tag v-if="item.score != null" size="small" type="info">
                  {{ (item.score * 100).toFixed(1) }}%
                </el-tag>
              </div>
              <div class="result-content">{{ item.content }}</div>
            </div>
          </div>
        </el-card>
      </div>
    </template>

    <!-- 新建/编辑知识库 -->
    <el-dialog
      v-model="showBaseModal"
      :title="isEditing ? $t('knowledgeBase.editBase') : $t('knowledgeBase.addBase')"
      width="560px"
      :close-on-click-modal="false"
      destroy-on-close
      class="kb-dialog"
      @closed="resetBaseForm"
    >
      <el-form ref="baseFormRef" :model="baseForm" :rules="baseRules" label-width="120px" label-position="right">
        <el-form-item :label="$t('knowledgeBase.name')" prop="name">
          <el-input v-model="baseForm.name" :placeholder="$t('knowledgeBase.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('knowledgeBase.project')" prop="project">
          <el-select v-model="baseForm.project" :placeholder="$t('knowledgeBase.projectPlaceholder')" style="width: 100%">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('knowledgeBase.description')">
          <el-input
            v-model="baseForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('knowledgeBase.descriptionPlaceholder')"
          />
        </el-form-item>

        <el-divider content-position="center">{{ $t('knowledgeBase.vectorConfig') }}</el-divider>

        <el-form-item>
          <template #label>
            <span>{{ $t('knowledgeBase.chunkSize') }}</span>
            <el-tooltip :content="$t('knowledgeBase.chunkSizeTip')" placement="top">
              <el-icon class="label-tip"><InfoFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number v-model="baseForm.chunk_size" :min="100" :max="4000" :step="50" style="width: 180px" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>{{ $t('knowledgeBase.chunkOverlap') }}</span>
            <el-tooltip :content="$t('knowledgeBase.chunkOverlapTip')" placement="top">
              <el-icon class="label-tip"><InfoFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number v-model="baseForm.chunk_overlap" :min="0" :max="1000" :step="10" style="width: 180px" />
        </el-form-item>
        <el-form-item :label="$t('knowledgeBase.enableVectorization')">
          <el-switch
            v-model="baseForm.enable_vectorization"
            inline-prompt
            :active-text="$t('knowledgeBase.yes')"
            :inactive-text="$t('knowledgeBase.no')"
          />
        </el-form-item>

        <el-form-item v-if="!isEditing" :label="$t('knowledgeBase.uploadDocument')">
          <el-upload
            drag
            multiple
            :auto-upload="false"
            :file-list="pendingFiles"
            accept=".pdf,.doc,.docx,.txt,.md"
            :on-change="onPendingFileChange"
            :on-remove="onPendingFileRemove"
            class="dialog-upload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">{{ $t('knowledgeBase.dragTip') }}</div>
            <template #tip>
              <div class="el-upload__tip">{{ $t('knowledgeBase.uploadHint') }}</div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item :label="$t('knowledgeBase.status')">
          <el-switch v-model="baseForm.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showBaseModal = false">{{ $t('knowledgeBase.cancel') }}</el-button>
        <el-button type="primary" :loading="isSaving" @click="saveBase">{{ $t('knowledgeBase.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 文本预览 -->
    <el-dialog
      v-model="showTextModal"
      :title="`${$t('knowledgeBase.extractPreview')} · ${previewDoc?.title || ''}`"
      width="780px"
    >
      <pre class="text-preview">{{ previewDoc?.extracted_text || '-' }}</pre>
      <template #footer>
        <el-button type="primary" @click="showTextModal = false">{{ $t('knowledgeBase.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import {
  getKnowledgeBases,
  getKnowledgeBaseDetail,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBaseDocuments,
  uploadKnowledgeDocument,
  deleteKnowledgeDocument,
  extractKnowledgeDocumentText
} from '@/api/requirement-analysis'
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, UploadFilled, InfoFilled, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.md']
const MAX_FILE_SIZE = 50 * 1024 * 1024

const defaultBaseForm = () => ({
  name: '',
  project: null,
  description: '',
  chunk_size: 500,
  chunk_overlap: 50,
  enable_vectorization: true,
  is_active: true
})

export default {
  name: 'KnowledgeBaseManage',
  components: { Plus, UploadFilled, InfoFilled, Search },
  setup() {
    const { t, locale } = useI18n()
    return { t, locale }
  },
  data() {
    return {
      loading: false,
      docsLoading: false,
      bases: [],
      projects: [],
      projectFilter: null,
      selectedBase: null,
      documents: [],
      showBaseModal: false,
      isEditing: false,
      isSaving: false,
      editingBaseId: null,
      baseForm: defaultBaseForm(),
      pendingFiles: [],
      isUploading: false,
      showTextModal: false,
      previewDoc: null,
      pendingUploadFiles: [],
      uploadConfirmTimer: null,
      searchLoading: false,
      searchResults: [],
      searchForm: {
        searchType: 'hybrid',
        query: '',
        similarity: 0,
        recallCount: 5,
        vectorRatio: 30
      }
    }
  },
  computed: {
    totalSize() {
      return this.bases.reduce((sum, item) => sum + (item.total_size || 0), 0)
    },
    detailTotalSize() {
      if (this.selectedBase?.total_size != null) return this.selectedBase.total_size
      return this.documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
    },
    vectorStatusKey() {
      if (!this.selectedBase) return 'pending'
      if (this.selectedBase.enable_vectorization === false) return 'disabled'
      if (!this.documents.length) return 'pending'
      if (this.documents.some((d) => d.status === 'processing')) return 'processing'
      if (this.documents.every((d) => d.is_vectorized)) return 'completed'
      if (this.documents.some((d) => d.status === 'failed')) return 'failed'
      return 'pending'
    },
    vectorStatusLabel() {
      const map = {
        completed: this.t('knowledgeBase.vectorCompleted'),
        processing: this.t('knowledgeBase.vectorProcessing'),
        failed: this.t('knowledgeBase.vectorFailed'),
        disabled: this.t('knowledgeBase.vectorDisabled'),
        pending: this.t('knowledgeBase.vectorPending')
      }
      return map[this.vectorStatusKey] || map.pending
    },
    vectorStatusTagType() {
      const map = {
        completed: 'success',
        processing: 'warning',
        failed: 'danger',
        disabled: 'info',
        pending: 'info'
      }
      return map[this.vectorStatusKey] || 'info'
    },
    searchTypeOptions() {
      return [
        { value: 'hybrid', label: this.t('knowledgeBase.searchHybrid') },
        { value: 'semantic', label: this.t('knowledgeBase.searchSemantic') },
        { value: 'keyword', label: this.t('knowledgeBase.searchKeyword') }
      ]
    },
    baseRules() {
      return {
        name: [{ required: true, message: this.t('knowledgeBase.nameRequired'), trigger: 'blur' }],
        project: [{ required: true, message: this.t('knowledgeBase.projectRequired'), trigger: 'change' }]
      }
    }
  },
  mounted() {
    this.fetchProjects()
    this.loadBases()
  },
  beforeUnmount() {
    if (this.uploadConfirmTimer) {
      clearTimeout(this.uploadConfirmTimer)
      this.uploadConfirmTimer = null
    }
  },
  methods: {
    async fetchProjects() {
      try {
        const response = await api.get('/projects/list/')
        this.projects = Array.isArray(response.data)
          ? response.data
          : (response.data?.results || [])
      } catch (error) {
        this.projects = []
      }
    },

    async loadBases() {
      this.loading = true
      try {
        const params = {}
        if (this.projectFilter) params.project = this.projectFilter
        const response = await getKnowledgeBases(params)
        if (response.data?.results && Array.isArray(response.data.results)) {
          this.bases = response.data.results
        } else if (Array.isArray(response.data)) {
          this.bases = response.data
        } else {
          this.bases = []
        }
      } catch (error) {
        this.bases = []
        if (error.response?.status === 401) {
          ElMessage.error(this.t('knowledgeBase.pleaseLogin'))
        } else {
          ElMessage.error(this.t('knowledgeBase.loadFailed'))
        }
      } finally {
        this.loading = false
      }
    },

    openAddModal() {
      this.isEditing = false
      this.editingBaseId = null
      this.baseForm = defaultBaseForm()
      this.pendingFiles = []
      this.showBaseModal = true
    },

    editBase(base) {
      this.isEditing = true
      this.editingBaseId = base.id
      this.baseForm = {
        name: base.name || '',
        project: base.project || null,
        description: base.description || '',
        chunk_size: base.chunk_size ?? 500,
        chunk_overlap: base.chunk_overlap ?? 50,
        enable_vectorization: base.enable_vectorization !== false,
        is_active: !!base.is_active
      }
      this.pendingFiles = []
      this.showBaseModal = true
    },

    resetBaseForm() {
      this.baseForm = defaultBaseForm()
      this.pendingFiles = []
      this.$refs.baseFormRef?.clearValidate?.()
    },

    onPendingFileChange(_file, fileList) {
      this.pendingFiles = fileList
    },

    onPendingFileRemove(_file, fileList) {
      this.pendingFiles = fileList
    },

    async saveBase() {
      const formRef = this.$refs.baseFormRef
      if (!formRef) return
      try {
        await formRef.validate()
      } catch (e) {
        return
      }

      this.isSaving = true
      try {
        const payload = {
          name: this.baseForm.name.trim(),
          project: this.baseForm.project,
          description: this.baseForm.description || '',
          chunk_size: this.baseForm.chunk_size,
          chunk_overlap: this.baseForm.chunk_overlap,
          enable_vectorization: this.baseForm.enable_vectorization,
          is_active: this.baseForm.is_active
        }

        let baseId = this.editingBaseId
        if (this.isEditing) {
          await updateKnowledgeBase(this.editingBaseId, payload)
          ElMessage.success(this.t('knowledgeBase.updateSuccess'))
        } else {
          const response = await createKnowledgeBase(payload)
          baseId = response.data?.id
          ElMessage.success(this.t('knowledgeBase.createSuccess'))

          const files = this.pendingFiles.map(f => f.raw).filter(Boolean)
          if (baseId && files.length) {
            await this.uploadFilesToBase(baseId, files)
          }
        }

        this.showBaseModal = false
        await this.loadBases()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || error.message || this.t('knowledgeBase.loadFailed'))
      } finally {
        this.isSaving = false
      }
    },

    async removeBase(base) {
      try {
        await ElMessageBox.confirm(
          this.t('knowledgeBase.deleteConfirm'),
          this.t('knowledgeBase.delete'),
          { type: 'warning' }
        )
        await deleteKnowledgeBase(base.id)
        ElMessage.success(this.t('knowledgeBase.deleteSuccess'))
        if (this.selectedBase?.id === base.id) {
          this.selectedBase = null
          this.documents = []
        }
        await this.loadBases()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error(error.response?.data?.detail || error.message || this.t('knowledgeBase.loadFailed'))
        }
      }
    },

    async openDocuments(base) {
      this.selectedBase = base
      this.searchResults = []
      this.searchForm = {
        searchType: 'hybrid',
        query: '',
        similarity: 0,
        recallCount: 5,
        vectorRatio: 30
      }
      await Promise.all([this.refreshSelectedBase(), this.loadDocuments()])
    },

    async refreshSelectedBase() {
      if (!this.selectedBase?.id) return
      try {
        const response = await getKnowledgeBaseDetail(this.selectedBase.id)
        if (response.data) {
          this.selectedBase = { ...this.selectedBase, ...response.data }
        }
      } catch (error) {
        // 保留列表中的基础信息即可
      }
    },

    backToList() {
      this.selectedBase = null
      this.documents = []
      this.searchResults = []
      this.loadBases()
    },

    async loadDocuments() {
      if (!this.selectedBase) return
      this.docsLoading = true
      try {
        const response = await getKnowledgeBaseDocuments(this.selectedBase.id)
        this.documents = Array.isArray(response.data) ? response.data : (response.data?.results || [])
      } catch (error) {
        this.documents = []
        ElMessage.error(this.t('knowledgeBase.loadFailed'))
      } finally {
        this.docsLoading = false
      }
    },

    docVectorLabel(row) {
      if (row.status === 'processing') return this.t('knowledgeBase.vectorProcessing')
      if (row.status === 'failed') return this.t('knowledgeBase.vectorFailed')
      if (row.is_vectorized) return this.t('knowledgeBase.vectorCompleted')
      return this.t('knowledgeBase.vectorPending')
    },

    docVectorTagType(row) {
      if (row.status === 'processing') return 'warning'
      if (row.status === 'failed') return 'danger'
      if (row.is_vectorized) return 'success'
      return 'info'
    },

    viewOriginal(doc) {
      if (doc.file_url) {
        window.open(doc.file_url, '_blank')
        return
      }
      this.viewText(doc)
    },

    runSearch() {
      const query = (this.searchForm.query || '').trim()
      if (!query) {
        ElMessage.warning(this.t('knowledgeBase.searchPlaceholder'))
        return
      }

      // 关键词检索：基于已提取文本做本地召回，便于验证知识库内容
      if (this.searchForm.searchType === 'keyword') {
        this.searchLoading = true
        try {
          const lower = query.toLowerCase()
          const matched = []
          for (const doc of this.documents) {
            const text = doc.extracted_text || ''
            if (!text.toLowerCase().includes(lower)) continue
            const idx = text.toLowerCase().indexOf(lower)
            const start = Math.max(0, idx - 60)
            const end = Math.min(text.length, idx + query.length + 140)
            matched.push({
              id: doc.id,
              title: doc.title,
              content: `${start > 0 ? '...' : ''}${text.slice(start, end)}${end < text.length ? '...' : ''}`,
              score: null
            })
            if (matched.length >= this.searchForm.recallCount) break
          }
          this.searchResults = matched
          if (!matched.length) {
            ElMessage.info(this.t('knowledgeBase.searchEmpty'))
          }
        } finally {
          this.searchLoading = false
        }
        return
      }

      this.searchResults = []
      ElMessage.info(this.t('knowledgeBase.searchComingSoon'))
    },

    onUploadChange(uploadFile) {
      if (!uploadFile?.raw || !this.selectedBase) return
      this.pendingUploadFiles.push(uploadFile.raw)
      if (this.uploadConfirmTimer) {
        clearTimeout(this.uploadConfirmTimer)
      }
      // 多文件拖拽时合并为一次确认
      this.uploadConfirmTimer = setTimeout(() => {
        this.confirmAndUploadPendingFiles()
      }, 150)
    },

    async confirmAndUploadPendingFiles() {
      const files = this.pendingUploadFiles.splice(0)
      this.uploadConfirmTimer = null
      if (!files.length || !this.selectedBase) return

      const validFiles = files.filter(file => this.validateFile(file))
      if (!validFiles.length) return

      const names = validFiles.map(f => f.name).join('、')
      const enableVector = this.selectedBase.enable_vectorization !== false
      try {
        await ElMessageBox.confirm(
          this.t('knowledgeBase.uploadConfirm', {
            count: validFiles.length,
            names,
            action: enableVector
              ? this.t('knowledgeBase.uploadConfirmVectorize')
              : this.t('knowledgeBase.uploadConfirmOnly')
          }),
          this.t('knowledgeBase.uploadConfirmTitle'),
          {
            type: 'info',
            confirmButtonText: this.t('knowledgeBase.confirm'),
            cancelButtonText: this.t('knowledgeBase.cancel')
          }
        )
      } catch (error) {
        return
      }

      await this.uploadFilesToBase(this.selectedBase.id, validFiles, {
        showSuccess: true,
        vectorizeHint: enableVector
      })
    },

    validateFile(file) {
      const name = (file.name || '').toLowerCase()
      const ok = ALLOWED_EXTENSIONS.some(ext => name.endsWith(ext))
      if (!ok) {
        ElMessage.warning(`${file.name}: ${this.t('knowledgeBase.invalidFileType')}`)
        return false
      }
      if (file.size > MAX_FILE_SIZE) {
        ElMessage.warning(`${file.name}: ${this.t('knowledgeBase.fileTooLarge')}`)
        return false
      }
      return true
    },

    async uploadFilesToBase(baseId, files, options = {}) {
      const { showSuccess = true, vectorizeHint = false } = options
      const validFiles = files.filter(file => this.validateFile(file))
      if (!validFiles.length) return 0

      this.isUploading = true
      let successCount = 0
      try {
        for (const file of validFiles) {
          const formData = new FormData()
          formData.append('knowledge_base', baseId)
          formData.append('title', file.name.replace(/\.[^.]+$/, ''))
          formData.append('file', file)
          try {
            await uploadKnowledgeDocument(formData)
            successCount += 1
          } catch (error) {
            const data = error.response?.data
            const detail = Array.isArray(data?.detail) ? data.detail[0] : data?.detail
            ElMessage.error(
              `${file.name}: ${data?.file?.[0] || detail || data?.error || this.t('knowledgeBase.uploadFailed')}`
            )
          }
        }
        if (successCount > 0 && showSuccess) {
          ElMessage.success(
            vectorizeHint
              ? this.t('knowledgeBase.uploadVectorizeSuccess')
              : this.t('knowledgeBase.uploadSuccess')
          )
          if (this.selectedBase?.id === baseId) {
            await Promise.all([this.loadDocuments(), this.refreshSelectedBase()])
          }
        }
      } finally {
        this.isUploading = false
      }
      return successCount
    },

    async removeDocument(doc) {
      try {
        await ElMessageBox.confirm(
          this.t('knowledgeBase.deleteDocConfirm'),
          this.t('knowledgeBase.delete'),
          { type: 'warning' }
        )
        await deleteKnowledgeDocument(doc.id)
        ElMessage.success(this.t('knowledgeBase.deleteDocSuccess'))
        await Promise.all([this.loadDocuments(), this.refreshSelectedBase()])
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error(error.response?.data?.detail || error.message || this.t('knowledgeBase.loadFailed'))
        }
      }
    },

    viewText(doc) {
      this.previewDoc = doc
      this.showTextModal = true
    },

    async reExtract(doc) {
      try {
        const response = await extractKnowledgeDocumentText(doc.id)
        ElMessage.success(this.t('knowledgeBase.extractSuccess'))
        doc.extracted_text = response.data?.extracted_text || ''
        doc.status = response.data?.status || doc.status
        await this.loadDocuments()
      } catch (error) {
        ElMessage.error(error.response?.data?.error || this.t('knowledgeBase.extractFailed'))
      }
    },

    formatDocType(type) {
      const map = {
        pdf: this.t('knowledgeBase.typePdf'),
        docx: this.t('knowledgeBase.typeDocx'),
        txt: this.t('knowledgeBase.typeTxt'),
        md: this.t('knowledgeBase.typeMd')
      }
      return map[type] || type
    },

    formatStatus(status) {
      const map = {
        uploaded: this.t('knowledgeBase.statusUploaded'),
        processing: this.t('knowledgeBase.statusProcessing'),
        ready: this.t('knowledgeBase.statusReady'),
        failed: this.t('knowledgeBase.statusFailed')
      }
      return map[status] || status
    },

    statusTagType(status) {
      const map = {
        ready: 'success',
        processing: 'warning',
        uploaded: 'info',
        failed: 'danger'
      }
      return map[status] || 'info'
    },

    formatFileSize(size) {
      if (!size && size !== 0) return '0 B'
      if (size < 1024) return `${size} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      return `${(size / (1024 * 1024)).toFixed(2)} MB`
    },

    formatDateTime(value) {
      if (!value) return '-'
      try {
        const d = new Date(value)
        if (Number.isNaN(d.getTime())) return value
        const pad = (n) => String(n).padStart(2, '0')
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
      } catch (e) {
        return value
      }
    }
  }
}
</script>

<style scoped>
.knowledge-base-manage {
  padding: 24px;
  min-height: 100%;
  background: #f5f7fa;
}

/* 去掉文字/链接按钮阴影（全局 primary 按钮阴影会作用到 link） */
.knowledge-base-manage :deep(.el-button.is-link),
.knowledge-base-manage :deep(.el-button.is-text) {
  box-shadow: none !important;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 16px;
}

.header-left h1 {
  margin: 0 0 8px;
  color: #303133;
  font-size: 22px;
  font-weight: 600;
  line-height: 1.3;
}

.header-left p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.filter-bar {
  margin-bottom: 16px;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  min-width: 180px;
  padding: 18px 24px;
  border-radius: 8px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-blue {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.stat-orange {
  background: linear-gradient(135deg, #e6a23c 0%, #f3d19e 100%);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 13px;
  opacity: 0.95;
}

.table-card {
  border-radius: 8px;
  margin-bottom: 16px;
}

.detail-page {
  max-width: 1200px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.back-btn {
  font-size: 14px;
  padding: 0;
}

.detail-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  line-height: 1.3;
}

.status-tag {
  vertical-align: middle;
}

.section-card {
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
}

.info-card :deep(.el-card__body) {
  padding: 0;
}

.info-card :deep(.el-descriptions) {
  border-radius: 8px;
  overflow: hidden;
}

.info-card :deep(.el-descriptions__body .el-descriptions__table) {
  border-radius: 8px;
}

.info-card :deep(.el-descriptions__body .el-descriptions__table.is-bordered .el-descriptions__cell) {
  border-color: #ebeef5;
}

.section-card :deep(.el-card__header) {
  padding: 14px 20px;
  border-bottom: 1px solid #ebeef5;
}

.section-card :deep(.el-card__body) {
  padding: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.upload-link {
  font-size: 14px;
  font-weight: 500;
}

.kb-descriptions :deep(.el-descriptions__label) {
  width: 120px;
  color: #606266;
  background: #fafafa;
}

.kb-descriptions :deep(.el-descriptions__content) {
  color: #303133;
  min-width: 140px;
}

.doc-title {
  color: #303133;
  font-weight: 500;
}

.doc-table :deep(.el-table__header th) {
  background: #fafafa;
  color: #606266;
  font-weight: 600;
}

.search-card :deep(.el-card__body) {
  padding: 20px 24px 24px;
}

.search-type-tabs {
  display: inline-flex;
  align-items: center;
  gap: 0;
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.search-type-btn {
  appearance: none;
  border: none;
  background: transparent;
  padding: 8px 18px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s ease;
  border-right: 1px solid #e4e7ed;
  line-height: 1.4;
}

.search-type-btn:last-child {
  border-right: none;
}

.search-type-btn:hover {
  color: var(--th-color-primary, #6c5ce7);
}

.search-type-btn.active {
  background: var(--th-color-primary, #6c5ce7);
  color: #fff;
}

.search-input-row {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 6px 0 0 6px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--th-color-primary, #6c5ce7) inset;
}

.search-btn {
  height: 32px;
  border-radius: 0 6px 6px 0;
  padding: 0 18px;
  margin-left: -1px;
}

.search-params {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 24px 32px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-item label {
  font-size: 13px;
  color: #606266;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.param-slider {
  flex: 1;
  min-width: 220px;
  max-width: 360px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-row :deep(.el-slider) {
  flex: 1;
}

.slider-value {
  min-width: 42px;
  text-align: right;
  color: #606266;
  font-size: 13px;
}

.param-recall {
  min-width: 120px;
}

.recall-input {
  width: 110px;
}

.search-results {
  margin-top: 20px;
  border-top: 1px solid #ebeef5;
  padding-top: 16px;
}

.search-results-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.search-result-item {
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 10px;
  background: #fafbfc;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.result-index {
  color: #909399;
  font-size: 12px;
}

.result-title {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}

.result-content {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.label-tip {
  margin-left: 2px;
  color: #909399;
  vertical-align: middle;
  cursor: help;
}

.dialog-upload {
  width: 100%;
}

.dialog-upload :deep(.el-upload) {
  width: 100%;
}

.dialog-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 28px 16px;
}

.text-preview {
  max-height: 420px;
  overflow: auto;
  background: #f7fafc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #303133;
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 768px) {
  .search-input-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .search-input :deep(.el-input__wrapper),
  .search-btn {
    border-radius: 6px;
    margin-left: 0;
  }

  .search-btn {
    width: 100%;
  }

  .param-slider {
    max-width: none;
  }
}
</style>
