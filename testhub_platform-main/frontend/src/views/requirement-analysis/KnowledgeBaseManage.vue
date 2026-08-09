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
          <el-table-column :label="$t('knowledgeBase.actions')" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDocuments(row)">{{ $t('knowledgeBase.upload') }}</el-button>
              <el-button link type="primary" @click="editBase(row)">{{ $t('knowledgeBase.edit') }}</el-button>
              <el-button link type="danger" @click="removeBase(row)">{{ $t('knowledgeBase.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 文档详情页 -->
    <template v-else>
      <div class="page-header">
        <div class="header-left">
          <el-button link type="primary" @click="backToList">← {{ $t('knowledgeBase.backToList') }}</el-button>
          <h1>{{ selectedBase.name }}</h1>
          <p>{{ $t('knowledgeBase.documents') }}</p>
        </div>
      </div>

      <el-card shadow="never" class="upload-card">
        <el-upload
          drag
          multiple
          :auto-upload="false"
          :show-file-list="false"
          accept=".pdf,.doc,.docx,.txt,.md"
          :disabled="isUploading"
          :on-change="onUploadChange"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            {{ isUploading ? $t('knowledgeBase.uploading') : $t('knowledgeBase.dragTip') }}
          </div>
          <template #tip>
            <div class="el-upload__tip">{{ $t('knowledgeBase.uploadHint') }}</div>
          </template>
        </el-upload>
      </el-card>

      <el-card shadow="never" class="table-card" v-loading="docsLoading">
        <el-table :data="documents" style="width: 100%">
          <el-table-column prop="title" :label="$t('knowledgeBase.documentTitle')" min-width="180">
            <template #default="{ row }">
              <div class="doc-title">{{ row.title }}</div>
              <div class="doc-filename">{{ row.file_name }}</div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.fileType')" width="100">
            <template #default="{ row }">{{ formatDocType(row.document_type) }}</template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.fileSize')" width="110">
            <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.status')" width="130">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ formatStatus(row.status) }}</el-tag>
              <div v-if="row.is_vectorized" class="doc-vectorized">
                {{ $t('knowledgeBase.vectorized', { count: row.chunk_count || 0 }) }}
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.uploadedAt')" width="180">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column :label="$t('knowledgeBase.actions')" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewText(row)">{{ $t('knowledgeBase.viewText') }}</el-button>
              <el-button link type="primary" @click="reExtract(row)">{{ $t('knowledgeBase.reExtract') }}</el-button>
              <el-button link type="danger" @click="removeDocument(row)">{{ $t('knowledgeBase.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
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
import { Plus, UploadFilled, InfoFilled } from '@element-plus/icons-vue'
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
  components: { Plus, UploadFilled, InfoFilled },
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
      uploadConfirmTimer: null
    }
  },
  computed: {
    totalSize() {
      return this.bases.reduce((sum, item) => sum + (item.total_size || 0), 0)
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
      await this.loadDocuments()
    },

    backToList() {
      this.selectedBase = null
      this.documents = []
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
            await this.loadDocuments()
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
        await this.loadDocuments()
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
        return new Date(value).toLocaleString(this.locale === 'zh-cn' ? 'zh-CN' : 'en-US')
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

.table-card,
.upload-card {
  border-radius: 8px;
  margin-bottom: 16px;
}

.doc-title {
  color: #303133;
  font-weight: 600;
}

.doc-filename {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.doc-vectorized {
  margin-top: 4px;
  color: #67c23a;
  font-size: 12px;
}

.label-tip {
  margin-left: 4px;
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
</style>
