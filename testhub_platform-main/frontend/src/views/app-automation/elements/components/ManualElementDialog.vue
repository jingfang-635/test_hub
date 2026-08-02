<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑元素' : '新增元素'"
    :width="activeTab === 'capture' ? '47vw' : '700px'"
    :top="activeTab === 'capture' ? '4vh' : undefined"
    @close="handleClose"
  >
    <el-tabs v-model="activeTab" class="dialog-tabs">
      <el-tab-pane label="手动创建" name="manual">
        <el-form :model="formData" ref="formRef" label-width="120px" :rules="rules">
          <el-form-item label="元素名称" prop="name" required>
            <el-input v-model="formData.name" placeholder="如：登录按钮" />
          </el-form-item>

          <el-form-item label="所属项目">
            <el-select v-model="formData.project" placeholder="请选择项目" clearable filterable style="width: 100%">
              <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="元素类型" prop="element_type" required>
            <el-radio-group v-model="formData.element_type" @change="handleTypeChange">
              <el-radio value="image">图片元素</el-radio>
              <el-radio value="pos">坐标元素</el-radio>
              <el-radio value="region">区域元素</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="标签">
            <el-select
              v-model="formData.tags"
              multiple
              filterable
              allow-create
              placeholder="输入标签后回车"
              style="width: 100%"
            >
              <el-option label="登录" value="登录" />
            </el-select>
            <div style="color: #909399; font-size: 12px; margin-top: 5px;">
              💡 提示：输入标签回车创建
            </div>
          </el-form-item>
          
          <!-- 图片类型配置 -->
          <template v-if="formData.element_type === 'image'">
            <el-divider content-position="left">图片配置</el-divider>
            
            <el-form-item label="图片分类" required>
              <div style="display: flex; gap: 10px;">
                <el-select 
                  v-model="formData.config.image_category"
                  placeholder="选择分类"
                  filterable
                  style="flex: 1;"
                >
                  <el-option 
                    v-for="cat in imageCategories" 
                    :key="cat" 
                    :label="cat" 
                    :value="cat"
                  >
                    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                      <span>{{ cat }}</span>
                      <el-button
                        v-if="cat !== 'common'"
                        type="danger"
                        size="small"
                        link
                        :icon="Delete"
                        @click.stop="handleDeleteCategory(cat)"
                        title="删除分类"
                        style="padding: 0; margin-left: 8px;"
                      />
                    </div>
                  </el-option>
                </el-select>
                <el-button 
                  type="primary" 
                  :icon="Plus" 
                  @click="showCreateCategoryDialog"
                  title="创建新分类"
                />
              </div>
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                💡 提示：图片将保存到 Template/&lt;分类&gt;/ 目录下
              </div>
            </el-form-item>
            
            <el-form-item label="元素图片">
              <!-- 编辑模式：显示当前图片和更换选项 -->
              <div v-if="isEdit && formData.config.image_path" class="current-image-section">
                <div style="color: #606266; font-size: 14px; margin-bottom: 10px; font-weight: 500;">
                  📷 当前图片
                </div>
                
                <!-- 图片预览 -->
                <div class="image-preview-box">
                  <el-image 
                    :key="imageRefreshKey"
                    :src="currentImageUrl" 
                    style="max-width: 200px; max-height: 150px; border-radius: 4px;"
                    fit="contain"
                    :preview-src-list="[currentImageUrl]"
                  >
                    <template #error>
                      <div class="image-error">
                        <el-icon :size="50"><Picture /></el-icon>
                        <div>加载失败</div>
                      </div>
                    </template>
                  </el-image>
                </div>
                
                <!-- 图片信息 -->
                <div class="image-info-box">
                  <div class="info-item">
                    <el-icon><Folder /></el-icon>
                    <span>{{ formData.config.image_path }}</span>
                  </div>
                </div>
                
                <!-- 操作按钮 -->
                <el-space style="margin-top: 10px">
                  <el-button 
                    v-if="!showUpload" 
                    type="primary" 
                    size="small"
                    :icon="Upload"
                    @click="handleChangeImage"
                  >
                    更换图片
                  </el-button>
                  <el-button 
                    v-if="showUpload"
                    size="small"
                    @click="cancelUpload"
                  >
                    取消更换
                  </el-button>
                </el-space>
                
                <!-- 隐藏的 upload 组件 -->
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :on-change="handleImageChange"
                  :limit="1"
                  :show-file-list="false"
                  accept="image/png,image/jpg,image/jpeg"
                  style="display: none;"
                />
                
                <!-- 新图片预览区域 -->
                <div v-if="showUpload && imagePreview" style="margin-top: 15px">
                  <div style="color: #67C23A; font-size: 14px; margin-bottom: 10px; font-weight: 500;">
                    <el-icon><SuccessFilled /></el-icon> 新图片
                  </div>
                  
                  <div class="image-preview-box" style="border-color: #67C23A;">
                    <el-image 
                      :src="imagePreview" 
                      style="max-width: 200px; max-height: 150px; border-radius: 4px;"
                      fit="contain"
                      :preview-src-list="[imagePreview]"
                    />
                  </div>
                  
                  <div class="image-info-box">
                    <div class="info-item">
                      <el-icon><Document /></el-icon>
                      <span>{{ imageFile?.name || '新选择的图片' }}</span>
                    </div>
                  </div>
                  
                  <div style="color: #67C23A; font-size: 12px; margin-top: 8px;">
                    💡 保存后将替换当前图片
                  </div>
                </div>
              </div>
              
              <!-- 新建模式：直接显示上传 -->
              <div v-else>
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :on-change="handleImageChange"
                  :on-exceed="handleExceed"
                  :limit="1"
                  accept="image/png,image/jpg,image/jpeg"
                  list-type="picture"
                >
                  <el-button type="primary" size="small" :icon="Upload">
                    选择图片
                  </el-button>
                  <template #tip>
                    <div style="color: #909399; font-size: 12px;">
                      支持 PNG、JPG 格式
                    </div>
                  </template>
                </el-upload>
                
                <div v-if="imagePreview" style="margin-top: 10px">
                  <el-image :src="imagePreview" style="max-width: 200px" fit="contain" />
                </div>
              </div>
            </el-form-item>
            
            <el-form-item label="匹配阈值">
              <el-slider
                v-model="formData.config.image_threshold"
                :min="0.5"
                :max="1.0"
                :step="0.05"
                show-input
                :format-tooltip="val => val.toFixed(2)"
              />
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                💡 提示：阈值越高匹配越严格（推荐 0.7-0.8），越低越宽松但可能误匹配
              </div>
            </el-form-item>
            
            <el-form-item label="颜色模式">
              <el-switch
                v-model="formData.config.rgb"
                active-text="RGB彩色"
                inactive-text="灰度"
              />
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                💡 提示：RGB彩色适用于彩色界面，灰度适用于单色或对颜色不敏感的场景
              </div>
            </el-form-item>
          </template>
          
          <!-- 坐标类型配置 -->
          <template v-if="formData.element_type === 'pos'">
            <el-divider content-position="left">坐标配置</el-divider>
            
            <el-form-item label="X坐标" required>
              <el-input-number v-model="formData.config.x" :min="0" placeholder="横坐标" style="width: 100%" />
            </el-form-item>
            
            <el-form-item label="Y坐标" required>
              <el-input-number v-model="formData.config.y" :min="0" placeholder="纵坐标" style="width: 100%" />
            </el-form-item>
          </template>
          
          <!-- 区域类型配置 -->
          <template v-if="formData.element_type === 'region'">
            <el-divider content-position="left">区域配置</el-divider>
            
            <el-form-item label="左上角坐标" required>
              <el-space>
                <el-input-number v-model="formData.config.x1" placeholder="X1" style="width: 150px" />
                <el-input-number v-model="formData.config.y1" placeholder="Y1" style="width: 150px" />
              </el-space>
            </el-form-item>
            
            <el-form-item label="右下角坐标" required>
              <el-space>
                <el-input-number v-model="formData.config.x2" placeholder="X2" style="width: 150px" />
                <el-input-number v-model="formData.config.y2" placeholder="Y2" style="width: 150px" />
              </el-space>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="从设备创建" name="capture">
        <div class="capture-container">
          <!-- 左侧：截图画布 -->
          <div class="capture-left">
            <div
              v-if="displayImage"
              ref="imageWrapper"
              class="image-wrapper"
              @mousedown="handleMouseDown"
              @mousemove="handleMouseMove"
              @mouseup="handleMouseUp"
              @mouseleave="handleMouseUp"
            >
              <img
                ref="imageRef"
                :src="displayImage"
                @load="handleImageLoad"
                class="capture-image"
              />
              <!-- 选区框 -->
              <div
                v-if="selection && formData.element_type === 'region'"
                class="selection-box"
                :style="selectionStyle"
                @mousedown.stop="handleSelectionMouseDown"
              >
                <button class="selection-close" @click.stop="clearSelection">×</button>
                <div class="selection-info">{{ selectionInfo }}</div>
                <!-- 8个调整手柄 -->
                <span
                  v-for="handle in resizeHandles"
                  :key="handle"
                  class="resize-handle"
                  :class="`resize-handle-${handle}`"
                  @mousedown.stop="handleResizeStart(handle, $event)"
                ></span>
              </div>
              <!-- 坐标标记 -->
              <div
                v-if="posMarker && formData.element_type === 'pos'"
                class="pos-marker"
                :style="posMarkerStyle"
              >
                <span class="pos-marker-label">{{ posValue }}</span>
              </div>
            </div>
            <div v-else class="empty-state">
              <el-empty :description="emptyStateDescription" />
            </div>
          </div>

          <!-- 右侧：配置表单 -->
          <div class="capture-right">
            <el-form :model="formData" ref="captureFormRef" label-width="110px" size="small">
              <!-- 设备选择和截图 -->
              <el-form-item label="选择设备">
                <el-select v-model="selectedDevice" placeholder="选择设备" style="width: 100%" :loading="devicesLoading">
                  <el-option 
                    v-for="device in devices" 
                    :key="device.id" 
                    :label="device.device_id" 
                    :value="device.id" 
                  />
                </el-select>
              </el-form-item>

              <el-form-item>
                <el-button type="primary" :loading="capturing" :disabled="!selectedDevice" @click="captureScreen">
                  从设备截图
                </el-button>
              </el-form-item>

              <!-- Region和Pos值（根据元素类型显示） -->
              <el-form-item label="Region 值" v-if="formData.element_type === 'region'">
                <el-input v-model="regionValue" readonly placeholder="在截图上拖拽框选区域" />
              </el-form-item>

              <el-form-item label="Pos 值" v-if="formData.element_type === 'pos'">
                <el-input v-model="posValue" readonly placeholder="在截图上单击选择坐标" />
              </el-form-item>

              <el-divider content-position="left">元素信息</el-divider>

              <!-- 元素名称 -->
              <el-form-item label="元素名称" required>
                <el-input v-model="formData.name" placeholder="如：登录按钮" />
              </el-form-item>

              <!-- 所属项目 -->
              <el-form-item label="所属项目">
                <el-select v-model="formData.project" placeholder="请选择项目" clearable filterable style="width: 100%">
                  <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>

              <!-- 元素类型 -->
              <el-form-item label="元素类型" required>
                <el-radio-group v-model="formData.element_type" @change="handleTypeChange">
                  <el-radio value="image">图片元素</el-radio>
                  <el-radio value="pos">坐标元素</el-radio>
                  <el-radio value="region">区域元素</el-radio>
                </el-radio-group>
              </el-form-item>

              <!-- 标签 -->
              <el-form-item label="标签">
                <el-select v-model="formData.tags" multiple filterable allow-create placeholder="输入标签后回车" style="width: 100%">
                  <el-option label="登录" value="登录" />
                </el-select>
                <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                  💡 提示：输入标签回车创建
                </div>
              </el-form-item>

              <!-- 图片类型特有配置 -->
              <template v-if="formData.element_type === 'image'">
                <el-divider content-position="left">图片配置</el-divider>

                <!-- 图片分类 -->
                <el-form-item label="图片分类" required>
                  <div style="display: flex; gap: 10px;">
                    <el-select
                      v-model="formData.config.image_category"
                      placeholder="选择分类"
                      filterable
                      style="flex: 1;"
                    >
                      <el-option 
                        v-for="cat in imageCategories" 
                        :key="cat" 
                        :label="cat" 
                        :value="cat"
                      >
                        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                          <span>{{ cat }}</span>
                          <el-button
                            v-if="cat !== 'common'"
                            type="danger"
                            size="small"
                            link
                            :icon="Delete"
                            @click.stop="handleDeleteCategory(cat)"
                            title="删除分类"
                            style="padding: 0; margin-left: 8px;"
                          />
                        </div>
                      </el-option>
                    </el-select>
                    <el-button 
                      type="primary" 
                      :icon="Plus" 
                      @click="showCreateCategoryDialog"
                      title="创建新分类"
                    />
                  </div>
                  <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                    💡 提示：图片将保存到 Template/&lt;分类&gt;/ 目录下
                  </div>
                </el-form-item>

                <el-form-item label="模板文件名" required>
                  <el-input v-model="templateFileName" :placeholder="templateFilePlaceholder" />
                  <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                    💡 提示：建议使用有意义的英文文件名
                  </div>
                </el-form-item>

                <!-- 当前保存路径 -->
                <el-form-item label="保存路径">
                  <el-input :value="imageSavePath" readonly>
                    <template #prepend>
                      <el-icon><FolderOpened /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <el-form-item label="匹配阈值">
                  <el-slider v-model="formData.config.image_threshold" :min="0.5" :max="1.0" :step="0.05" show-input />
                  <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                    💡 提示：值越高匹配越严格，默认 0.7
                  </div>
                </el-form-item>

                <el-form-item label="颜色模式">
                  <el-switch
                    v-model="formData.config.rgb"
                    active-text="RGB彩色"
                    inactive-text="灰度"
                  />
                  <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                    💡 提示：RGB彩色适用于彩色界面，灰度适用于单色或对颜色不敏感的场景
                  </div>
                </el-form-item>
              </template>
            </el-form>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting" :disabled="!canSubmit">
        保存
      </el-button>
    </template>
  </el-dialog>
  
  <!-- 创建图片分类对话框 -->
  <el-dialog
    v-model="createCategoryVisible"
    title="创建图片分类"
    width="400px"
  >
    <el-form>
      <el-form-item label="分类名称">
        <el-input 
          v-model="newCategoryName" 
          placeholder="如：button, icon, menu"
          @keyup.enter="handleCreateCategory"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 5px;">
          💡 只能包含字母、数字、下划线和中划线
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createCategoryVisible = false">取消</el-button>
      <el-button type="primary" @click="handleCreateCategory" :loading="creatingCategory">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Upload, Document, Folder, SuccessFilled, Picture, FolderOpened } from '@element-plus/icons-vue'
import {
  uploadAppElementImage,
  createAppElement,
  updateAppElement,
  getAppImageCategories,
  createAppImageCategory,
  deleteAppImageCategory,
  getDeviceList,
  captureDeviceScreenshot
} from '@/api/app-automation'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editData: {
    type: Object,
    default: null
  },
  projectList: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEdit = computed(() => !!props.editData)

// Tab state
const activeTab = ref('manual')

// Manual form refs
const formRef = ref(null)
const uploadRef = ref(null)
const imageRefreshKey = ref(0)
const currentImageUrl = computed(() => {
  if (props.editData?.id && props.editData?.config?.image_path) {
    return `/api/app-automation/elements/${props.editData.id}/preview/?t=${imageRefreshKey.value}`
  }
  return ''
})

// Capture form refs
const captureFormRef = ref(null)
const imageRef = ref(null)
const imageWrapper = ref(null)

// Shared state
const submitting = ref(false)
const imageFile = ref(null)
const imagePreview = ref('')
const showUpload = ref(false)
const imageCategories = ref([])
const createCategoryVisible = ref(false)
const newCategoryName = ref('')
const creatingCategory = ref(false)

// Capture tab state
const devices = ref([])
const devicesLoading = ref(false)
const selectedDevice = ref(null)
const capturing = ref(false)
const capturedImage = ref('')

// Screenshot selection
const selection = ref(null)
const selecting = ref(false)
const startPoint = ref(null)
const action = ref(null)
const resizeHandle = ref(null)
const moveOffset = ref(null)
const imageSize = ref({ width: 0, height: 0 })
const posMarker = ref(null)

const resizeHandles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

// Template file name
const templateFileName = ref('')

const formData = reactive({
  name: '',
  element_type: 'image',
  project: null,
  tags: [],
  config: {
    image_category: 'common',
    image_threshold: 0.7,
    rgb: false,
    x: 0,
    y: 0,
    x1: 0,
    y1: 0,
    x2: 0,
    y2: 0,
    image_path: '',
    file_hash: ''
  }
})

const rules = {
  name: [
    { required: true, message: '请输入元素名称', trigger: 'blur' }
  ],
  element_type: [
    { required: true, message: '请选择元素类型', trigger: 'change' }
  ]
}

// === Capture tab computed properties ===

const displayImage = computed(() => {
  if (capturedImage.value) return capturedImage.value
  if (isEdit.value && formData.element_type === 'image' && formData.config.image_path) {
    return currentImageUrl.value
  }
  return ''
})

const emptyStateDescription = computed(() => {
  if (isEdit.value && formData.element_type === 'image') {
    return '无法加载当前图片，请重新截图'
  }
  return '请先从设备截图'
})

const regionValue = computed(() => {
  if (formData.config.x1 && formData.config.y1 && formData.config.x2 && formData.config.y2) {
    return `${formData.config.x1},${formData.config.y1},${formData.config.x2},${formData.config.y2}`
  }
  return ''
})

const posValue = computed(() => {
  if (formData.config.x && formData.config.y) {
    return `${formData.config.x},${formData.config.y}`
  }
  return ''
})

const selectionStyle = computed(() => {
  if (!selection.value) return {}
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  const x2 = Math.max(selection.value.x1, selection.value.x2)
  const y2 = Math.max(selection.value.y1, selection.value.y2)
  return {
    left: `${x1}px`,
    top: `${y1}px`,
    width: `${x2 - x1}px`,
    height: `${y2 - y1}px`
  }
})

const selectionInfo = computed(() => {
  if (!selection.value) return ''
  const width = Math.abs(selection.value.x2 - selection.value.x1)
  const height = Math.abs(selection.value.y2 - selection.value.y1)
  return `${Math.round(width)} × ${Math.round(height)}`
})

const posMarkerStyle = computed(() => {
  if (!posMarker.value) return {}
  return {
    left: `${posMarker.value.x}px`,
    top: `${posMarker.value.y}px`
  }
})

const imageSavePath = computed(() => {
  const imageCategory = formData.config.image_category || 'common'
  const filename = templateFileName.value || 'template.png'
  return `Template/${imageCategory}/${filename}`
})

const templateFilePlaceholder = computed(() => {
  if (isEdit.value && formData.config.image_path) {
    const parts = formData.config.image_path.split('/')
    const existingName = parts[parts.length - 1] || 'template.png'
    return `如：${existingName}（留空则保留原图片）`
  }
  return '如：login_btn.png'
})

const canSubmit = computed(() => {
  if (!formData.name) return false
  if (activeTab.value === 'capture') {
    if (formData.element_type === 'image') {
      if (!formData.config.image_category) return false
      if (capturedImage.value) {
        return templateFileName.value && formData.config.image_category
      }
      return !!formData.config.image_path
    } else if (formData.element_type === 'pos') {
      return formData.config.x && formData.config.y
    } else if (formData.element_type === 'region') {
      return formData.config.x1 && formData.config.y1 && formData.config.x2 && formData.config.y2
    }
  } else {
    if (formData.element_type === 'image') {
      if (isEdit.value) {
        if (imageFile.value) return formData.config.image_category
        return !!formData.config.image_path
      }
      return !!imageFile.value && formData.config.image_category
    } else if (formData.element_type === 'pos') {
      return formData.config.x && formData.config.y
    } else if (formData.element_type === 'region') {
      return formData.config.x1 && formData.config.y1 && formData.config.x2 && formData.config.y2
    }
  }
  return false
})

// === Type change handler ===

const handleTypeChange = () => {
  formData.config = {
    image_category: formData.config.image_category || 'common',
    image_threshold: 0.7,
    rgb: false,
    x: 0,
    y: 0,
    x1: 0,
    y1: 0,
    x2: 0,
    y2: 0,
    image_path: isEdit.value ? (formData.config.image_path || '') : '',
    file_hash: isEdit.value ? (formData.config.file_hash || '') : ''
  }
  imageFile.value = null
  imagePreview.value = ''
  capturedImage.value = ''
  selection.value = null
  posMarker.value = null
}

// === Manual tab image handlers ===

const handleImageChange = (file) => {
  if (!file || !file.raw) return
  
  imageFile.value = file.raw
  
  const reader = new FileReader()
  reader.onload = (e) => {
    if (e.target && typeof e.target.result === 'string') {
      imagePreview.value = e.target.result
    }
  }
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  
  reader.readAsDataURL(file.raw)
}

const handleExceed = () => {
  ElMessage.warning('最多只能上传 1 个图片文件')
}

const handleChangeImage = async () => {
  imagePreview.value = ''
  imageFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  
  showUpload.value = true
  
  await nextTick()
  
  if (uploadRef.value) {
    const uploadElement = uploadRef.value.$el
    const inputElement = uploadElement.querySelector('input[type="file"]')
    if (inputElement) {
      inputElement.value = ''
      inputElement.click()
    }
  }
}

const cancelUpload = () => {
  showUpload.value = false
  imagePreview.value = ''
  imageFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// === Capture tab device & screenshot ===

const loadDevices = async () => {
  devicesLoading.value = true
  try {
    const { data } = await getDeviceList()
    devices.value = data.results || []
  } catch (error) {
    console.error('加载设备列表失败:', error)
    ElMessage.error('加载设备列表失败')
  } finally {
    devicesLoading.value = false
  }
}

const captureScreen = async () => {
  if (!selectedDevice.value) {
    ElMessage.warning('请先选择设备')
    return
  }

  capturing.value = true
  try {
    const { data } = await captureDeviceScreenshot(selectedDevice.value)
    
    if (data.success && data.data) {
      capturedImage.value = data.data.content || data.content || ''
      if (!capturedImage.value) {
        throw new Error('截图数据为空')
      }
      ElMessage.success('截图成功')
    } else {
      ElMessage.error(data.message || '截图失败')
    }
  } catch (error) {
    console.error('截图失败:', error)
    ElMessage.error('截图失败')
  } finally {
    capturing.value = false
  }
}

// === Capture tab image interaction ===

const handleImageLoad = () => {
  if (imageRef.value) {
    imageSize.value = {
      width: imageRef.value.naturalWidth || imageRef.value.width,
      height: imageRef.value.naturalHeight || imageRef.value.height
    }
    
    if (isEdit.value && displayImage.value === currentImageUrl.value) {
      if (formData.element_type === 'region' && formData.config.x1 && formData.config.y1 && formData.config.x2 && formData.config.y2) {
        const scaleX = imageRef.value.clientWidth / imageSize.value.width
        const scaleY = imageRef.value.clientHeight / imageSize.value.height
        selection.value = {
          x1: formData.config.x1 * scaleX,
          y1: formData.config.y1 * scaleY,
          x2: formData.config.x2 * scaleX,
          y2: formData.config.y2 * scaleY
        }
      } else if (formData.element_type === 'pos' && formData.config.x && formData.config.y) {
        const scaleX = imageRef.value.clientWidth / imageSize.value.width
        const scaleY = imageRef.value.clientHeight / imageSize.value.height
        posMarker.value = {
          x: formData.config.x * scaleX,
          y: formData.config.y * scaleY
        }
      }
    }
  }
}

const getImageRect = () => {
  if (!imageWrapper.value || !imageRef.value) return null
  return imageWrapper.value.getBoundingClientRect()
}

const getSelectionInNatural = () => {
  if (!selection.value || !imageRef.value) return null
  const scaleX = imageSize.value.width / imageRef.value.clientWidth
  const scaleY = imageSize.value.height / imageRef.value.clientHeight
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  const x2 = Math.max(selection.value.x1, selection.value.x2)
  const y2 = Math.max(selection.value.y1, selection.value.y2)
  return {
    x1: Math.round(x1 * scaleX),
    y1: Math.round(y1 * scaleY),
    x2: Math.round(x2 * scaleX),
    y2: Math.round(y2 * scaleY)
  }
}

const updateSelectionValues = () => {
  const natural = getSelectionInNatural()
  if (natural) {
    formData.config.x1 = natural.x1
    formData.config.y1 = natural.y1
    formData.config.x2 = natural.x2
    formData.config.y2 = natural.y2
  }
}

const handleMouseDown = (e) => {
  if (!displayImage.value || !imageWrapper.value) return
  const rect = getImageRect()
  if (!rect) return
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))
  
  if (formData.element_type === 'pos') {
    // Single click to set position
    const scaleX = imageSize.value.width / (imageRef.value?.clientWidth || 1)
    const scaleY = imageSize.value.height / (imageRef.value?.clientHeight || 1)
    formData.config.x = Math.round(x * scaleX)
    formData.config.y = Math.round(y * scaleY)
    posMarker.value = { x, y }
    selection.value = null
    return
  }
  
  if (formData.element_type === 'region') {
    selecting.value = true
    startPoint.value = { x, y }
    action.value = 'create'
    selection.value = { x1: x, y1: y, x2: x, y2: y }
    posMarker.value = null
    e.preventDefault()
  }
}

const handleMouseMove = (e) => {
  if (!selecting.value || !selection.value) return
  if (!imageWrapper.value) return
  const rect = getImageRect()
  if (!rect) return
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))
  
  if (action.value === 'create' && startPoint.value) {
    selection.value = { x1: startPoint.value.x, y1: startPoint.value.y, x2: x, y2: y }
  } else if (action.value === 'move' && moveOffset.value) {
    const width = Math.abs(selection.value.x2 - selection.value.x1)
    const height = Math.abs(selection.value.y2 - selection.value.y1)
    const left = Math.max(0, Math.min(x - moveOffset.value.x, rect.width - width))
    const top = Math.max(0, Math.min(y - moveOffset.value.y, rect.height - height))
    selection.value = { x1: left, y1: top, x2: left + width, y2: top + height }
  } else if (action.value === 'resize' && resizeHandle.value) {
    selection.value = resizeSelection(selection.value, resizeHandle.value, x, y, rect)
  }
  e.preventDefault()
}

const handleMouseUp = () => {
  if (selecting.value) {
    if (action.value === 'create' && selection.value) {
      const width = Math.abs(selection.value.x2 - selection.value.x1)
      const height = Math.abs(selection.value.y2 - selection.value.y1)
      if (width < 5 && height < 5) {
        selection.value = null
      } else {
        updateSelectionValues()
      }
    } else if (action.value === 'move' || action.value === 'resize') {
      updateSelectionValues()
    }
    selecting.value = false
    startPoint.value = null
    action.value = null
    resizeHandle.value = null
    moveOffset.value = null
  }
}

const handleSelectionMouseDown = (e) => {
  if (!imageWrapper.value) return
  const rect = getImageRect()
  if (!rect || !selection.value) return
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  selecting.value = true
  action.value = 'move'
  moveOffset.value = { x: x - x1, y: y - y1 }
  e.preventDefault()
}

const handleResizeStart = (handle, e) => {
  if (!imageWrapper.value) return
  selecting.value = true
  action.value = 'resize'
  resizeHandle.value = handle
  e.preventDefault()
}

const resizeSelection = (sel, handle, x, y, rect) => {
  let { x1, y1, x2, y2 } = sel
  const clampX = Math.max(0, Math.min(x, rect.width))
  const clampY = Math.max(0, Math.min(y, rect.height))
  if (handle.includes('n')) y1 = clampY
  if (handle.includes('s')) y2 = clampY
  if (handle.includes('w')) x1 = clampX
  if (handle.includes('e')) x2 = clampX
  return { x1, y1, x2, y2 }
}

const clearSelection = () => {
  selection.value = null
  action.value = null
  resizeHandle.value = null
  moveOffset.value = null
  formData.config.x1 = 0
  formData.config.y1 = 0
  formData.config.x2 = 0
  formData.config.y2 = 0
}

// === Submit ===

const handleSubmit = async () => {
  try {
    if (activeTab.value === 'manual' && formRef.value) {
      await formRef.value.validate()
    }
    
    if (!formData.name) {
      ElMessage.warning('请输入元素名称')
      return
    }

    submitting.value = true
    
    if (activeTab.value === 'capture') {
      await handleCaptureSubmit()
    } else {
      await handleManualSubmit()
    }
  } catch (error) {
    console.error('提交失败:', error)
    if (error !== 'validation failed') {
      ElMessage.error('操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleCaptureSubmit = async () => {
  try {
    if (formData.element_type === 'image') {
      if (capturedImage.value) {
        if (!templateFileName.value) {
          ElMessage.warning('请输入模板文件名')
          submitting.value = false
          return
        }
        if (!formData.config.image_category) {
          ElMessage.warning('请选择图片分类')
          submitting.value = false
          return
        }
        
        // Upload captured image
        let imageBlob
        if (selection.value && imageRef.value && formData.element_type === 'region') {
          const img = imageRef.value
          const sel = selection.value
          const scaleX = imageSize.value.width / img.clientWidth
          const scaleY = imageSize.value.height / img.clientHeight
          
          const x1 = Math.min(sel.x1, sel.x2)
          const y1 = Math.min(sel.y1, sel.y2)
          const x2 = Math.max(sel.x1, sel.x2)
          const y2 = Math.max(sel.y1, sel.y2)
          const width = x2 - x1
          const height = y2 - y1
          
          const cropX = Math.round(x1 * scaleX)
          const cropY = Math.round(y1 * scaleY)
          const cropWidth = Math.round(width * scaleX)
          const cropHeight = Math.round(height * scaleY)

          const canvas = document.createElement('canvas')
          canvas.width = cropWidth
          canvas.height = cropHeight
          const ctx = canvas.getContext('2d')

          if (ctx) {
            ctx.drawImage(img, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight)
            imageBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
          }
        } else {
          const base64Data = capturedImage.value.split(',')[1]
          imageBlob = base64ToBlob(base64Data, 'image/png')
        }

        if (!imageBlob) {
          ElMessage.error('图片处理失败')
          submitting.value = false
          return
        }

        const file = new File([imageBlob], templateFileName.value, { type: 'image/png' })
        
        try {
          const { data: uploadData } = await uploadAppElementImage(
            file,
            formData.config.image_category || 'common',
            props.editData?.id || null
          )
          
          if (uploadData.success) {
            formData.config.image_path = uploadData.data.image_path
            formData.config.file_hash = uploadData.data.file_hash
          } else {
            let errorMessage = uploadData.message || '上传图片失败'
            if (uploadData.detail) {
              errorMessage += `\n\n${uploadData.detail}`
            }
            if (uploadData.suggestion) {
              errorMessage += `\n\n💡 建议：${uploadData.suggestion}`
            }
            ElMessage.error({
              message: errorMessage,
              duration: 8000,
              showClose: true
            })
            submitting.value = false
            return
          }
        } catch (uploadError) {
          console.error('图片上传异常:', uploadError)
          let errorMessage = '图片上传失败'
          if (uploadError.response?.data) {
            const data = uploadError.response.data
            errorMessage = data.message || data.detail || errorMessage
          } else if (uploadError.message) {
            errorMessage += `: ${uploadError.message}`
          }
          ElMessage.error({
            message: errorMessage,
            duration: 5000,
            showClose: true
          })
          submitting.value = false
          return
        }
      } else if (!formData.config.image_path) {
        if (isEdit.value) {
          ElMessage.warning('请截图或选择要保留的图片')
        } else {
          ElMessage.warning('请先截图')
        }
        submitting.value = false
        return
      }
    } else if (formData.element_type === 'pos') {
      if (!formData.config.x || !formData.config.y) {
        ElMessage.warning('请设置坐标')
        submitting.value = false
        return
      }
    } else if (formData.element_type === 'region') {
      if (!formData.config.x1 || !formData.config.y1 || !formData.config.x2 || !formData.config.y2) {
        ElMessage.warning('请框选区域')
        submitting.value = false
        return
      }
    }

    const submitData = {
      name: formData.name,
      element_type: formData.element_type,
      project: formData.project || null,
      tags: formData.tags,
      config: {
        ...formData.config
      }
    }

    if (isEdit.value) {
      await updateAppElement(props.editData.id, submitData)
      ElMessage.success('更新成功')
    } else {
      await createAppElement(submitData)
      ElMessage.success('创建成功')
    }
    emit('success')
    handleClose()
  } catch (error) {
    console.error('提交失败:', error)
    let errorMessage = '操作失败'
    if (error.response?.data) {
      const data = error.response.data
      if (data.message) {
        errorMessage = data.message
      } else if (data.detail) {
        errorMessage = data.detail
      } else if (data.config) {
        const configErrors = data.config
        if (Array.isArray(configErrors)) {
          errorMessage = `配置错误: ${configErrors.join(', ')}`
        } else if (typeof configErrors === 'object') {
          errorMessage = `配置错误: ${JSON.stringify(configErrors)}`
        }
      }
      errorMessage += ` (状态码: ${error.response.status})`
    } else if (error.message) {
      errorMessage = `错误: ${error.message}`
    }
    ElMessage.error({
      message: errorMessage,
      duration: 5000,
      showClose: true
    })
  }
}

const handleManualSubmit = async () => {
  try {
    if (formData.element_type === 'image') {
      if (!isEdit.value && !imageFile.value) {
        ElMessage.warning('请选择图片文件')
        submitting.value = false
        return
      }
      
      if (imageFile.value) {
        const { data: uploadData } = await uploadAppElementImage(
          imageFile.value,
          formData.config.image_category || 'common',
          props.editData?.id || null
        )
        
        if (uploadData.success) {
          formData.config.image_path = uploadData.data.image_path
          formData.config.file_hash = uploadData.data.file_hash
        } else {
          let errorMessage = uploadData.message || '上传图片失败'
          if (uploadData.detail) {
            errorMessage += `\n\n${uploadData.detail}`
          }
          if (uploadData.suggestion) {
            errorMessage += `\n\n💡 建议：${uploadData.suggestion}`
          }
          ElMessage.error({
            message: errorMessage,
            duration: 8000,
            showClose: true
          })
          submitting.value = false
          return
        }
      }
    }
    
    const submitData = {
      name: formData.name,
      element_type: formData.element_type,
      project: formData.project || null,
      tags: formData.tags,
      config: {}
    }
    
    if (formData.element_type === 'image') {
      submitData.config = {
        image_category: formData.config.image_category || 'common',
        image_threshold: formData.config.image_threshold,
        rgb: formData.config.rgb,
        image_path: formData.config.image_path || '',
        file_hash: formData.config.file_hash || ''
      }
    } else if (formData.element_type === 'pos') {
      submitData.config = {
        x: formData.config.x,
        y: formData.config.y
      }
    } else if (formData.element_type === 'region') {
      submitData.config = {
        x1: formData.config.x1,
        y1: formData.config.y1,
        x2: formData.config.x2,
        y2: formData.config.y2
      }
    }
    
    if (isEdit.value) {
      await updateAppElement(props.editData.id, submitData)
      ElMessage.success('更新成功')
    } else {
      await createAppElement(submitData)
      ElMessage.success('创建成功')
    }
    emit('success')
    handleClose()
  } catch (error) {
    console.error('提交失败:', error)
    let errorMessage = '操作失败'
    if (error.response?.data) {
      const data = error.response.data
      if (data.message) {
        errorMessage = data.message
      } else if (data.detail) {
        errorMessage = data.detail
      } else if (data.config) {
        const configErrors = data.config
        if (Array.isArray(configErrors)) {
          errorMessage = `配置错误: ${configErrors.join(', ')}`
        } else if (typeof configErrors === 'object') {
          errorMessage = `配置错误: ${JSON.stringify(configErrors)}`
        }
      }
      errorMessage += ` (状态码: ${error.response.status})`
    } else if (error.message) {
      errorMessage = `错误: ${error.message}`
    }
    ElMessage.error({
      message: errorMessage,
      duration: 5000,
      showClose: true
    })
  }
}

const base64ToBlob = (base64, type = 'image/png') => {
  const byteCharacters = atob(base64)
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }
  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type })
}

// === Close / Reset ===

const handleClose = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  
  activeTab.value = 'manual'
  imageFile.value = null
  imagePreview.value = ''
  showUpload.value = false
  capturedImage.value = ''
  selection.value = null
  posMarker.value = null
  templateFileName.value = ''
  
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  
  Object.assign(formData, {
    name: '',
    element_type: 'image',
    project: null,
    tags: [],
    config: {
      image_category: 'common',
      image_threshold: 0.7,
      rgb: false,
      x: 0,
      y: 0,
      x1: 0,
      y1: 0,
      x2: 0,
      y2: 0,
      image_path: '',
      file_hash: ''
    }
  })
  
  emit('update:modelValue', false)
}

// === Watchers ===

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    activeTab.value = 'manual'
    if (props.editData) {
      if (props.editData.config) {
        formData.config.image_path = props.editData.config.image_path || ''
        formData.config.file_hash = props.editData.config.file_hash || ''
      }
      imageRefreshKey.value = Date.now()
      
      // Extract template file name from image path for edit mode
      if (props.editData.config?.image_path) {
        const parts = props.editData.config.image_path.split('/')
        templateFileName.value = parts[parts.length - 1] || ''
      } else {
        templateFileName.value = ''
      }
    }
    loadDevices()
  }
})

watch(() => props.editData, (data) => {
  if (data) {
    formData.name = data.name || ''
    formData.element_type = data.element_type || 'image'
    formData.project = data.project || null
    formData.tags = data.tags ? [...data.tags] : []
    
    if (data.config) {
      formData.config = {
        image_category: data.config.image_category || 'common',
        image_threshold: data.config.image_threshold || 0.7,
        rgb: data.config.rgb !== undefined ? data.config.rgb : false,
        x: data.config.x || 0,
        y: data.config.y || 0,
        x1: data.config.x1 || 0,
        y1: data.config.y1 || 0,
        x2: data.config.x2 || 0,
        y2: data.config.y2 || 0,
        image_path: data.config.image_path || '',
        file_hash: data.config.file_hash || ''
      }
    }
    
    imagePreview.value = ''
    imageFile.value = null
    showUpload.value = false
    capturedImage.value = ''
    selection.value = null
    posMarker.value = null
    templateFileName.value = ''
    
    if (data.config?.image_path) {
      const parts = data.config.image_path.split('/')
      templateFileName.value = parts[parts.length - 1] || ''
    }
    
    imageRefreshKey.value = Date.now()
  }
}, { immediate: true })

// === Image categories ===

const loadImageCategories = async () => {
  try {
    const { data } = await getAppImageCategories()
    if (data.success && Array.isArray(data.data)) {
      imageCategories.value = data.data.map(cat => cat.name || cat)
    }
  } catch (error) {
    console.error('加载图片分类失败:', error)
    imageCategories.value = ['common']
  }
}

const showCreateCategoryDialog = () => {
  newCategoryName.value = ''
  createCategoryVisible.value = true
}

const handleCreateCategory = async () => {
  if (!newCategoryName.value.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  
  try {
    creatingCategory.value = true
    const { data } = await createAppImageCategory(newCategoryName.value.trim())
    
    if (data.success) {
      ElMessage.success('创建成功')
      await loadImageCategories()
      formData.config.image_category = data.data.name
      createCategoryVisible.value = false
    } else {
      ElMessage.error(data.message || '创建失败')
    }
  } catch (error) {
    console.error('创建分类失败:', error)
    ElMessage.error('创建失败')
  } finally {
    creatingCategory.value = false
  }
}

const handleDeleteCategory = async (categoryName) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除分类 "${categoryName}" 吗？只能删除空目录。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    const { data } = await deleteAppImageCategory(categoryName)
    
    if (data.success) {
      ElMessage.success('删除成功')
      await loadImageCategories()
      if (formData.config.image_category === categoryName) {
        formData.config.image_category = 'common'
      }
    } else {
      ElMessage.error(data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除分类失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadImageCategories()
})
</script>

<style scoped>
.dialog-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 20px;
  }
  :deep(.el-tabs__nav-wrap) {
    justify-content: center;
  }
  :deep(.el-tabs__nav-scroll) {
    display: flex;
    justify-content: center;
  }
  :deep(.el-tabs__nav) {
    float: none;
    display: flex;
    justify-content: center;
  }
}

.current-image-section {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

.image-preview-box {
  display: inline-block;
  padding: 10px;
  background: white;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  color: #909399;
  font-size: 12px;
}

.image-info-box {
  margin-top: 10px;
  font-size: 12px;
  color: #606266;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 0;
}

.info-item .el-icon {
  color: #909399;
}

.capture-container {
  display: flex;
  gap: 20px;
  height: calc(100vh - 200px);
  justify-content: flex-end;
}

.capture-left {
  flex: 0 0 auto;
  width: 42%;
  min-width: 0;
  max-width: 42%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-wrapper {
  position: relative;
  cursor: crosshair;
  display: inline-block;
  max-width: 100%;
  max-height: 100%;
}

.capture-image {
  max-width: 100%;
  max-height: calc(100vh - 220px);
  display: block;
  user-select: none;
  object-fit: contain;
}

.selection-box {
  position: absolute;
  border: 2px solid #409eff;
  background: rgba(64, 158, 255, 0.1);
  cursor: move;
  pointer-events: auto;
}

.selection-info {
  position: absolute;
  top: -25px;
  left: 0;
  background: #409eff;
  color: white;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
}

.selection-close {
  position: absolute;
  top: -10px;
  right: -10px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f56c6c;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  pointer-events: auto;
  z-index: 10;
}

.selection-close:hover {
  background: #f78989;
}

.resize-handle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #409eff;
  border: 1px solid white;
  border-radius: 50%;
  pointer-events: auto;
  z-index: 5;
}

.resize-handle-nw { top: -5px; left: -5px; cursor: nwse-resize; }
.resize-handle-n { top: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
.resize-handle-ne { top: -5px; right: -5px; cursor: nesw-resize; }
.resize-handle-e { top: 50%; right: -5px; transform: translateY(-50%); cursor: ew-resize; }
.resize-handle-se { bottom: -5px; right: -5px; cursor: nwse-resize; }
.resize-handle-s { bottom: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
.resize-handle-sw { bottom: -5px; left: -5px; cursor: nesw-resize; }
.resize-handle-w { top: 50%; left: -5px; transform: translateY(-50%); cursor: ew-resize; }

.pos-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  z-index: 5;
}

.pos-marker::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  border: 2px solid #f56c6c;
  border-radius: 50%;
  background: rgba(245, 108, 108, 0.2);
}

.pos-marker-label {
  position: absolute;
  top: -22px;
  left: 50%;
  transform: translateX(-50%);
  background: #f56c6c;
  color: white;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  white-space: nowrap;
}

.capture-right {
  flex: 0 0 auto;
  width: 400px;
  overflow-y: auto;
  padding-right: 0;
}

.empty-state {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
