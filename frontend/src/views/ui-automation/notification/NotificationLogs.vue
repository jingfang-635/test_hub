<template>
  <div class="notification-logs-container">
    <div class="page-header">
      <h3 class="page-title">{{ $t('uiAutomation.notification.logs.title') }}</h3>
    </div>

    <!-- 筛选栏 -->
    <div class="card-container">
      <div class="filter-bar">
        <el-input
          v-model="searchForm.taskName"
          class="filter-item filter-item--search"
          :placeholder="$t('uiAutomation.notification.logs.searchTaskName')"
          clearable
          @input="handleSearchInput"
        >
          <template #prefix>
            <el-icon>
              <Search/>
            </el-icon>
          </template>
        </el-input>
        <el-date-picker
          v-model="searchForm.dateRange"
          class="filter-item filter-item--date"
          type="daterange"
          :range-separator="$t('uiAutomation.notification.logs.dateRangeTo')"
          :start-placeholder="$t('uiAutomation.notification.logs.startDate')"
          :end-placeholder="$t('uiAutomation.notification.logs.endDate')"
          value-format="YYYY-MM-DD"
          style="width: 240px; flex: none;"
          @change="handleSearch"
        />
        <el-select
          v-model="searchForm.status"
          class="filter-item filter-item--select"
          :placeholder="$t('uiAutomation.notification.logs.notificationStatus')"
          clearable
          @change="handleSearch"
        >
          <el-option :label="$t('uiAutomation.notification.logs.allStatus')" value=""/>
          <el-option :label="$t('uiAutomation.notification.logs.statusSuccess')" value="success"/>
          <el-option :label="$t('uiAutomation.notification.logs.statusFailed')" value="failed"/>
          <el-option :label="$t('uiAutomation.notification.logs.statusSending')" value="sending"/>
        </el-select>
        <el-button @click="handleReset">
          {{ $t('uiAutomation.common.reset') }}
        </el-button>
      </div>

      <!-- 通知列表 -->
      <div class="logs-table-container">
      <el-table
          :data="logsData"
          v-loading="loading"
          :element-loading-text="$t('uiAutomation.notification.logs.messages.loading')"
          stripe
          style="width: 100%"
      >
        <el-table-column
            prop="task_name"
            :label="$t('uiAutomation.notification.logs.taskName')"
            min-width="150"
        />
        <el-table-column
            prop="task_type_display"
            :label="$t('uiAutomation.notification.logs.taskType')"
            min-width="100"
        >
          <template #default="{ row }">
            <el-tag
                type="info"
                size="small"
            >
              {{ row.task_type_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
            prop="actual_notification_type_display"
            :label="$t('uiAutomation.notification.logs.notificationType')"
            min-width="120"
        >
          <template #default="{ row }">
            <el-tag
                :type="getNotificationTypeTagType(row.actual_notification_type_display)"
                size="small"
            >
              {{ row.actual_notification_type_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
            prop="created_at"
            :label="$t('uiAutomation.notification.logs.notificationTime')"
            min-width="180"
        >
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
            prop="status_display"
            :label="$t('uiAutomation.common.status')"
            min-width="100"
        >
          <template #default="{ row }">
            <el-tag
                :type="getStatusTagType(row.status_display)"
                size="small"
            >
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
            :label="$t('uiAutomation.common.operation')"
            fixed="right"
            width="120"
        >
          <template #default="{ row }">
            <el-button
                type="primary"
                round
                size="small"
                @click="viewDetail(row)"
            >
              {{ $t('uiAutomation.notification.logs.viewDetail') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
        />
      </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
        v-model="detailDialogVisible"
        class="notification-detail-dialog"
        :title="$t('uiAutomation.notification.logs.detailTitle')"
        width="600px"
        align-center
        :before-close="handleDetailDialogClose"
    >
      <el-form
          v-if="selectedLog"
          label-position="top"
          class="notification-detail-form"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('uiAutomation.notification.logs.taskName')">
              <span>{{ selectedLog.task_name }}</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('uiAutomation.notification.logs.taskType')">
              <span>{{ selectedLog.task_type_display }}</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('uiAutomation.notification.logs.notificationType')">
              <el-tag :type="getNotificationTypeTagType(selectedLog.actual_notification_type_display)">
                {{ selectedLog.actual_notification_type_display }}
              </el-tag>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('uiAutomation.common.status')">
              <el-tag :type="getStatusTagType(selectedLog.status_display)">
                {{ selectedLog.status_display }}
              </el-tag>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('uiAutomation.notification.logs.notificationTime')">
              <span>{{ formatDate(selectedLog.created_at) }}</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('uiAutomation.notification.logs.sentTime')">
              <span>{{ selectedLog.sent_at ? formatDate(selectedLog.sent_at) : '-' }}</span>
            </el-form-item>
          </el-col>
          <el-col :span="24" v-if="selectedLog.webhook_bot_info && (selectedLog.webhook_bot_info.bot_type || selectedLog.webhook_bot_info.type)">
            <el-form-item :label="$t('uiAutomation.notification.logs.webhookBot')">
              <div class="webhook-info">
                <el-tag
                    class="webhook-tag"
                    size="small"
                    type="info"
                >
                  {{ selectedLog.webhook_bot_info.name || selectedLog.webhook_bot_info.bot_name || $t('uiAutomation.notification.logs.defaultBotName') }}
                </el-tag>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="$t('uiAutomation.notification.logs.content')">
              <div class="notification-content">
                <div v-if="parsedNotificationContent" class="notification-content-parsed">
                  <template v-for="(item, index) in parsedNotificationContent" :key="index">
                    <div v-if="item.type === 'heading'" class="content-heading">
                      {{ item.value }}
                    </div>
                    <div v-else-if="item.type === 'field'" class="content-item">
                      <span class="content-label">{{ item.label }}:</span>
                      <span class="content-value">{{ item.value }}</span>
                    </div>
                    <div v-else class="content-item content-item--text">
                      <span class="content-value">{{ item.value }}</span>
                    </div>
                  </template>
                </div>
                <div v-else class="notification-content-raw">
                  <pre>{{ selectedLog.notification_content || '-' }}</pre>
                </div>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="24" v-if="selectedLog.error_message">
            <el-form-item :label="$t('uiAutomation.notification.logs.errorMessage')">
              <div class="error-message">
                <el-alert
                    :title="selectedLog.error_message"
                    type="error"
                    show-icon
                    :closable="false"
                />
              </div>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailDialogVisible = false">{{ $t('uiAutomation.common.close') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import {Search} from '@element-plus/icons-vue'
import {ref, reactive, onMounted, computed, onUnmounted} from 'vue'
import {ElMessage} from 'element-plus'
import { debounce } from 'lodash-es'
import { getNotificationLogs } from '@/api/ui_automation.js'
import { useI18n } from 'vue-i18n'

export default {
  name: 'NotificationLogs',
  components: {
    Search
  },
  setup() {
    const { t, locale } = useI18n()

    // 数据状态
    const loading = ref(false)
    const logsData = ref([])
    const detailDialogVisible = ref(false)
    const selectedLog = ref(null)

    // 搜索表单
    const searchForm = reactive({
      taskName: '',
      dateRange: [],
      status: ''
    })

    // 分页配置
    const pagination = reactive({
      currentPage: 1,
      pageSize: 10,
      total: 0
    })

    // 获取通知日志数据
    const fetchLogsData = async () => {
      loading.value = true
      try {
        const params = {
          page: pagination.currentPage,
          page_size: pagination.pageSize,
          ordering: '-created_at'
        }

        // 添加搜索条件
        if (searchForm.taskName) {
          params.search = searchForm.taskName
        }
        if (searchForm.dateRange && searchForm.dateRange.length === 2) {
          params.start_date = searchForm.dateRange[0]
          params.end_date = searchForm.dateRange[1]
        }
        if (searchForm.status) {
          params.status = searchForm.status
        }

        const response = await getNotificationLogs(params)
        logsData.value = response.data.results || []
        pagination.total = response.data.count || 0
      } catch (error) {
        console.error('Failed to fetch notification logs:', error)
        ElMessage.error(t('uiAutomation.notification.logs.messages.loadFailed'))
      } finally {
        loading.value = false
      }
    }

    // 处理搜索
    const handleSearch = () => {
      pagination.currentPage = 1
      fetchLogsData()
    }

    // 任务名称输入即时搜索（防抖 400ms）
    const handleSearchInput = debounce(() => {
      handleSearch()
    }, 400)

    // 重置搜索
    const handleReset = () => {
      searchForm.taskName = ''
      searchForm.dateRange = []
      searchForm.status = ''
      pagination.currentPage = 1
      fetchLogsData()
    }

    // 处理分页变化
    const handleSizeChange = (val) => {
      pagination.pageSize = val
      pagination.currentPage = 1
      fetchLogsData()
    }

    const handleCurrentChange = (val) => {
      pagination.currentPage = val
      fetchLogsData()
    }

    // 查看详情
    const viewDetail = (row) => {
      selectedLog.value = row
      detailDialogVisible.value = true
    }

    // 关闭详情弹窗
    const handleDetailDialogClose = (done) => {
      selectedLog.value = null
      done()
    }

    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString(locale.value === 'zh-cn' ? 'zh-CN' : 'en-US')
    }

    // 获取状态标签类型
    const getStatusTagType = (status) => {
      const typeMap = {
        // Chinese
        '发送成功': 'success',
        '发送失败': 'danger',
        '待发送': 'info',
        '发送中': 'warning',
        '已取消': 'info',
        // English
        'Success': 'success',
        'Failed': 'danger',
        'Pending': 'info',
        'Sending': 'warning',
        'Cancelled': 'info',
        // Lowercase
        'success': 'success',
        'failed': 'danger',
        'pending': 'info',
        'sending': 'warning',
        'cancelled': 'info'
      }
      return typeMap[status] || 'info'
    }

    // 获取通知类型标签类型
    const getNotificationTypeTagType = (typeDisplay) => {
      const typeMap = {
        // Chinese
        '邮箱通知': '',
        'Webhook机器人': 'primary',
        '两种都发送': 'warning',
        // English
        'Email': '',
        'Webhook Bot': 'primary',
        'Both': 'warning'
      }
      return typeMap[typeDisplay] || 'info'
    }

    // 将通知正文按行解析为可展示条目（保留全部内容，不丢弃任何行）
    const parseContentText = (text) => {
      if (!text) return []

      const result = []
      const lines = String(text).split('\n')

      lines.forEach((rawLine) => {
        const line = rawLine.replace(/\r$/, '').trim()
        if (!line) return

        // 去掉 markdown 加粗标记后再解析（模板中常见 **标签**: 值 写法）
        const plainLine = line.replace(/\*\*/g, '').trim()
        if (!plainLine) return

        // Markdown 标题行（整行加粗 或 # 标题）单独成行展示
        const headingMatch = line.match(/^\*\*(.+?)\*\*$/) || line.match(/^#{1,6}\s+(.+)$/)
        if (headingMatch) {
          result.push({
            type: 'heading',
            label: '',
            value: headingMatch[1].replace(/\*\*/g, '').trim()
          })
          return
        }

        // 键值对行：标签: 值（冒号需为半角或全角，且后面有内容）
        const kvMatch = plainLine.match(/^([^:：]{1,50})[:：]\s*(.+)$/)
        // 排除裸 URL（如 https://example.com）被误判为「标签: 值」
        const looksLikeUrl = kvMatch && kvMatch[2].trim().startsWith('//')
        if (kvMatch && !looksLikeUrl) {
          result.push({
            type: 'field',
            label: kvMatch[1].trim(),
            value: kvMatch[2].trim()
          })
          return
        }

        // 其余行原样保留（说明文字、列表项等）
        result.push({
          type: 'text',
          label: '',
          value: plainLine
        })
      })

      return result
    }

    // 提取 Webhook JSON 消息体中的正文文本
    const extractWebhookText = (jsonContent) => {
      // 飞书 interactive 卡片：标题 + 全部 elements
      if (jsonContent.msg_type === 'interactive' && jsonContent.card) {
        const elements = jsonContent.card.elements || []
        const bodyTexts = elements
            .map(el => (el && el.text && el.text.content) || '')
            .filter(Boolean)
        const body = bodyTexts.join('\n')

        const headerTitle = jsonContent.card.header?.title?.content || ''
        // 正文通常已包含标题，避免重复展示
        const needHeader = headerTitle && !body.includes(headerTitle)

        const parts = needHeader ? [headerTitle, ...bodyTexts] : bodyTexts
        if (parts.length) return parts.join('\n')
      }

      // 企业微信 / 钉钉 markdown 格式
      if (jsonContent.markdown) {
        if (jsonContent.markdown.text) return jsonContent.markdown.text
        if (jsonContent.markdown.content) return jsonContent.markdown.content
      }

      // 通用兜底：从常见字段中查找正文
      const fallbackCandidates = [
        jsonContent.content,
        jsonContent.text && jsonContent.text.content,
        jsonContent.text,
        jsonContent.body
      ]
      const found = fallbackCandidates.find(v => typeof v === 'string' && v.trim())
      return found || ''
    }

    // 解析通知内容为结构化数据
    const parsedNotificationContent = computed(() => {
      if (!selectedLog.value || !selectedLog.value.notification_content) {
        return null
      }

      const content = selectedLog.value.notification_content

      // 尝试解析JSON格式的通知内容(Webhook)
      try {
        const jsonContent = JSON.parse(content)
        const contentText = extractWebhookText(jsonContent)
        if (contentText) {
          const parsed = parseContentText(contentText)
          return parsed.length > 0 ? parsed : null
        }
      } catch {
        // JSON解析失败,继续尝试纯文本格式(邮件通知)
      }

      // 纯文本格式（邮件正文 / 兜底文案）
      const parsed = parseContentText(content)
      return parsed.length > 0 ? parsed : null
    })

    // 组件挂载时获取数据
    onMounted(() => {
      fetchLogsData()
    })

    return {
      loading,
      logsData,
      detailDialogVisible,
      selectedLog,
      searchForm,
      pagination,
      parsedNotificationContent,
      handleSearch,
      handleSearchInput,
      handleReset,
      handleSizeChange,
      handleCurrentChange,
      viewDetail,
      handleDetailDialogClose,
      formatDate,
      getStatusTagType,
      getNotificationTypeTagType
    }
  }
}
</script>

<style scoped>
.notification-logs-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  color: #303133;
  font-size: 20px;
  font-weight: 600;
}

.card-container {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-bar :deep(.filter-item--search) {
  width: 254px;
}

.filter-bar :deep(.filter-item--select) {
  width: 100px;
}

.filter-bar :deep(.filter-item--date) {
  width: 240px !important;
  max-width: 240px !important;
  flex: 0 0 240px !important;
  --el-date-editor-width: 240px;
  --el-date-editor-daterange-width: 240px;
}

.logs-table-container {
  margin-top: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.notification-detail-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.notification-content {
  width: 100%;
}

.notification-content-parsed {
  background: #ffffff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  box-sizing: border-box;
  width: 100%;
  overflow-wrap: anywhere;
}

/* 结构化内容行：键值对 / 小标题 / 普通文本 */
.content-item,
.content-heading,
.content-item--text {
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f5;
  font-size: 14px;
  line-height: 1.8;
}

.notification-content-parsed > :first-child {
  padding-top: 0;
}

.notification-content-parsed > :last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.content-item {
  display: flex;
  align-items: flex-start;
}

/* 小标题行（原 Markdown 加粗标题） */
.content-heading {
  font-weight: 600;
  color: #303133;
}

/* 普通文本行（非键值对，如说明文字、列表项） */
.content-item--text .content-value {
  color: #606266;
}

.content-label {
  font-weight: 600;
  color: #606266;
  min-width: 100px;
  flex-shrink: 0;
  margin-right: 16px;
  font-size: 14px;
  line-height: 1.8;
}

.content-value {
  color: #303133;
  flex: 1;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.8;
}

.notification-content-raw pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
}

.notification-content-raw pre::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.notification-content-raw pre::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.notification-content-raw pre::-webkit-scrollbar-thumb:hover {
  background: #a8abb2;
}

.webhook-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.webhook-tag {
  margin: 0;
}

.error-message {
  margin-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

<style>
/* 仅改弹窗本体高度；居中交给 align-center，勿改 overlay，否则蒙层易残留 */
.el-dialog.notification-detail-dialog {
  height: 700px;
  display: flex;
  flex-direction: column;
}

.el-dialog.notification-detail-dialog .el-dialog__header,
.el-dialog.notification-detail-dialog .el-dialog__footer {
  flex-shrink: 0;
}

.el-dialog.notification-detail-dialog .el-dialog__body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}
</style>
