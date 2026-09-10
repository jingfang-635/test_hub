<template>
  <div class="skills-config" v-loading="loading">
    <div class="section-header">
      <div class="section-title">
        <h2>{{ $t('configuration.skills.listTitle') }}</h2>
        <span class="count-badge">{{ skills.length }}</span>
      </div>
      <div class="section-actions">
        <input
          ref="mdInputRef"
          type="file"
          accept=".md,.markdown,.txt,text/markdown,text/plain"
          class="hidden-file-input"
          @change="onMdSelected"
        >
        <button class="import-btn" type="button" :disabled="importing" @click="triggerImport">
          {{ importing ? $t('configuration.skills.importing') : $t('configuration.skills.importMd') }}
        </button>
        <button class="add-btn" type="button" @click="openAddModal">
          {{ $t('configuration.skills.addSkill') }}
        </button>
      </div>
    </div>

    <div v-if="skills.length" class="skills-grid">
      <div v-for="skill in skills" :key="skill.id" class="skill-card">
        <div class="card-header">
          <h3 class="skill-name" :title="skill.name">{{ skill.name }}</h3>
          <div class="badges">
            <span v-if="skill.is_enabled" class="badge badge-enabled">{{ $t('configuration.common.enabled') }}</span>
            <span v-else class="badge badge-disabled">{{ $t('configuration.common.disabled') }}</span>
            <span v-if="skill.is_builtin" class="badge badge-builtin">{{ $t('configuration.skills.builtin') }}</span>
          </div>
        </div>

        <p class="skill-desc">{{ skill.description || $t('configuration.skills.noDescription') }}</p>

        <div v-if="skill.tags && skill.tags.length" class="tag-list">
          <span v-for="tag in skill.tags" :key="tag" class="tag-pill">{{ tag }}</span>
        </div>

        <div class="created-at">
          <span>{{ $t('configuration.common.createdAt') }}: {{ formatDateTime(skill.created_at) }}</span>
        </div>

        <div class="card-footer">
          <el-switch
            :model-value="skill.is_enabled"
            :loading="skill.toggling"
            @change="(val) => onToggle(skill, val)"
          />
          <div class="footer-actions">
            <button class="action-btn" type="button" @click="openEditModal(skill)">
              {{ $t('configuration.common.edit') }}
            </button>
            <button class="action-btn" type="button" :disabled="skill.exporting" @click="onExport(skill)">
              {{ $t('configuration.skills.export') }}
            </button>
            <button
              class="action-btn danger"
              type="button"
              @click="onDelete(skill)"
            >
              {{ $t('configuration.common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="empty-state">
      <h3>{{ $t('configuration.skills.emptyTitle') }}</h3>
      <p>{{ $t('configuration.skills.emptyDescription') }}</p>
      <button class="add-btn" type="button" @click="openAddModal">
        {{ $t('configuration.skills.addSkill') }}
      </button>
    </div>

    <el-dialog
      v-model="showModal"
      :title="isEditing ? $t('configuration.skills.editSkill') : $t('configuration.skills.addSkill')"
      width="640px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item :label="$t('configuration.skills.name')" prop="name">
          <el-input
            v-model="form.name"
            :disabled="isEditing && form.is_builtin"
            :placeholder="$t('configuration.skills.namePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('configuration.skills.description')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('configuration.skills.descriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('configuration.skills.tags')" prop="tagsText">
          <el-input
            v-model="form.tagsText"
            :placeholder="$t('configuration.skills.tagsPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('configuration.skills.content')" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            :placeholder="$t('configuration.skills.contentPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('configuration.skills.enabled')">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModal = false">{{ $t('configuration.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="saveSkill">
          {{ $t('configuration.common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createSkill,
  deleteSkill,
  exportSkill,
  getSkills,
  importSkillMd,
  toggleSkill,
  updateSkill
} from '@/api/core'

const { t } = useI18n()

const loading = ref(false)
const importing = ref(false)
const saving = ref(false)
const skills = ref([])
const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const mdInputRef = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  description: '',
  tagsText: '',
  content: '',
  is_enabled: true,
  is_builtin: false,
  files: {}
})

const rules = computed(() => ({
  name: [
    { required: true, message: t('configuration.skills.nameRequired'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && /\s/.test(value)) {
          callback(new Error(t('configuration.skills.nameNoSpace')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}))

const unwrapList = (res) => {
  const data = res?.data ?? res
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.data)) return data.data
  return []
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  const locale = t('configuration.common.locale') || 'zh-CN'
  return date.toLocaleString(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadSkills = async () => {
  loading.value = true
  try {
    const res = await getSkills({ ordering: '-created_at' })
    skills.value = unwrapList(res).map((item) => ({
      ...item,
      toggling: false,
      exporting: false
    }))
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.skills.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.name = ''
  form.description = ''
  form.tagsText = ''
  form.content = ''
  form.is_enabled = true
  form.is_builtin = false
  form.files = {}
  isEditing.value = false
  editingId.value = null
}

const openAddModal = () => {
  resetForm()
  showModal.value = true
}

const openEditModal = (skill) => {
  isEditing.value = true
  editingId.value = skill.id
  form.name = skill.name
  form.description = skill.description || ''
  form.tagsText = (skill.tags || []).join(', ')
  form.content = skill.content || ''
  form.is_enabled = !!skill.is_enabled
  form.is_builtin = !!skill.is_builtin
  form.files = skill.files || {}
  showModal.value = true
}

const parseTags = (text) =>
  String(text || '')
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean)

const saveSkill = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  const payload = {
    name: form.name.trim(),
    description: form.description,
    tags: parseTags(form.tagsText),
    content: form.content,
    files: form.files || {},
    is_enabled: form.is_enabled
  }

  saving.value = true
  try {
    if (isEditing.value) {
      await updateSkill(editingId.value, payload)
      ElMessage.success(t('configuration.skills.messages.updateSuccess'))
    } else {
      await createSkill(payload)
      ElMessage.success(t('configuration.skills.messages.createSuccess'))
    }
    showModal.value = false
    await loadSkills()
  } catch (error) {
    const detail =
      error?.response?.data?.name?.[0] ||
      error?.response?.data?.detail ||
      t('configuration.skills.messages.saveFailed')
    ElMessage.error(detail)
  } finally {
    saving.value = false
  }
}

const onToggle = async (skill, value) => {
  const prev = skill.is_enabled
  skill.is_enabled = value
  skill.toggling = true
  try {
    const res = await toggleSkill(skill.id, value)
    const data = res?.data ?? res
    Object.assign(skill, data, { toggling: false, exporting: false })
  } catch (error) {
    skill.is_enabled = prev
    ElMessage.error(error?.response?.data?.detail || t('configuration.skills.messages.toggleFailed'))
  } finally {
    skill.toggling = false
  }
}

const onDelete = async (skill) => {
  try {
    await ElMessageBox.confirm(
      skill.is_builtin
        ? t('configuration.skills.messages.deleteBuiltinConfirm', { name: skill.name })
        : t('configuration.skills.messages.deleteConfirm', { name: skill.name }),
      t('configuration.skills.messages.deleteTitle'),
      { type: 'warning', confirmButtonText: t('configuration.common.delete'), cancelButtonText: t('configuration.common.cancel') }
    )
    await deleteSkill(skill.id)
    ElMessage.success(t('configuration.skills.messages.deleteSuccess'))
    await loadSkills()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error?.response?.data?.detail || t('configuration.skills.messages.deleteFailed'))
  }
}

const onExport = async (skill) => {
  skill.exporting = true
  try {
    const res = await exportSkill(skill.id)
    const blob = res?.data instanceof Blob
      ? res.data
      : new Blob([res?.data ?? res], { type: 'text/markdown;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${skill.name}.md`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success(t('configuration.skills.messages.exportSuccess'))
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.skills.messages.exportFailed'))
  } finally {
    skill.exporting = false
  }
}

const triggerImport = () => {
  mdInputRef.value?.click()
}

const onMdSelected = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  importing.value = true
  try {
    const res = await importSkillMd(file)
    const data = res?.data ?? res
    ElMessage.success(
      data?.created
        ? t('configuration.skills.messages.importCreated')
        : t('configuration.skills.messages.importUpdated')
    )
    await loadSkills()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('configuration.skills.messages.importFailed'))
  } finally {
    importing.value = false
  }
}

onMounted(loadSkills)
</script>

<style scoped>
.skills-config {
  padding: 20px 24px 32px;
  max-width: 1480px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--th-text-primary, #1f2937);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: var(--th-color-primary, #6c5ce7);
  font-size: 13px;
  font-weight: 600;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hidden-file-input {
  display: none;
}

.import-btn,
.add-btn,
.action-btn {
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.import-btn {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
}

.import-btn:hover:not(:disabled) {
  border-color: var(--th-color-primary, #6c5ce7);
  color: var(--th-color-primary, #6c5ce7);
}

.add-btn {
  background: var(--th-color-primary, #6c5ce7);
  border: 1px solid var(--th-color-primary, #6c5ce7);
  color: #fff;
}

.add-btn:hover {
  filter: brightness(1.05);
}

.import-btn:disabled,
.add-btn:disabled,
.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.skill-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  min-height: 250px;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.skill-card:hover {
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.skill-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  line-height: 1.4;
  word-break: break-word;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.badge-enabled {
  background: #ecfdf5;
  color: #059669;
}

.badge-disabled {
  background: #f3f4f6;
  color: #6b7280;
}

.badge-builtin {
  background: #fff7ed;
  color: #ea580c;
}

.skill-desc {
  margin: 0 0 12px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 62px;
  flex: 1;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.tag-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
}

.created-at {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 14px;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: auto;
  padding-top: 4px;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
  padding: 6px 12px;
}

.action-btn:hover:not(:disabled) {
  border-color: #9ca3af;
}

.action-btn.danger {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fff;
}

.action-btn.danger:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #f87171;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  background: #fff;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #111827;
}

.empty-state p {
  margin: 0 0 20px;
  color: #6b7280;
}

@media (max-width: 1280px) {
  .skills-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .skills-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .skills-grid {
    grid-template-columns: 1fr;
  }
}

:global(.is-dark) .skill-card,
:global(.is-dark) .import-btn,
:global(.is-dark) .action-btn,
:global(.is-dark) .empty-state {
  background: var(--th-bg-elevated, #1f2430);
  border-color: var(--th-border-color, #2f3645);
  color: var(--th-text-primary, #e8ecf4);
}

:global(.is-dark) .skill-name,
:global(.is-dark) .section-title h2,
:global(.is-dark) .empty-state h3 {
  color: var(--th-text-primary, #e8ecf4);
}

:global(.is-dark) .skill-desc,
:global(.is-dark) .created-at,
:global(.is-dark) .empty-state p {
  color: var(--th-text-secondary, #9aa3b2);
}

:global(.is-dark) .tag-pill {
  background: #2a3140;
  color: #9aa3b2;
}

:global(.is-dark) .count-badge {
  background: rgba(108, 92, 231, 0.2);
}
</style>
