<template>
  <div class="notification-configs-container">
    <!-- 页面说明 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon class="title-icon">
          <Setting/>
        </el-icon>
        {{ $t('uiAutomation.notification.configs.pageTitle') }}
      </h1>
    </div>

    <!-- Tab切换 -->
    <div class="content-wrapper">
      <el-tabs v-model="activeTab" class="notification-tabs">

        <!-- 邮箱配置Tab -->
        <el-tab-pane :label="$t('uiAutomation.notification.configs.emailTab')" name="email">
          <div class="tab-content">
            <div class="config-section">
              <el-form
                  ref="emailFormRef"
                  :model="emailConfig"
                  label-position="top"
                  class="config-form"
              >
                <el-row :gutter="20">
                  <!-- 第一行：SMTP服务器、启用 -->
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.smtpHost')">
                      <el-select
                          v-model="emailConfig.smtp_host"
                          filterable
                          allow-create
                          default-first-option
                          :reserve-keyword="false"
                          :placeholder="$t('uiAutomation.notification.configs.smtpHostPlaceholder')"
                          style="width: 100%"
                          @change="onSmtpHostChange"
                      >
                        <el-option
                            v-for="provider in smtpHostOptions"
                            :key="provider.value"
                            :label="provider.label"
                            :value="provider.value"
                        >
                          <span>{{ provider.label }}</span>
                          <span style="float: right; margin-left: 16px; color: #a8abb2; font-size: 12px">{{ provider.value }}</span>
                        </el-option>
                      </el-select>
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.smtpHostHint') }}
                      </div>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.enable')">
                      <el-switch v-model="emailConfig.is_active"/>
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.emailActiveHint') }}
                      </div>
                    </el-form-item>
                  </el-col>

                  <!-- 第二行：加密方式、SMTP端口 -->
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.secureMode')">
                      <el-radio-group v-model="emailConfig.use_ssl" @change="onSecureModeChange">
                        <el-radio :value="true">{{ $t('uiAutomation.notification.configs.useSsl') }}</el-radio>
                        <el-radio :value="false">{{ $t('uiAutomation.notification.configs.useTls') }}</el-radio>
                      </el-radio-group>
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.secureModeHint') }}
                      </div>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.smtpPort')">
                      <el-input-number
                          v-model="emailConfig.smtp_port"
                          :min="1"
                          :max="65535"
                          controls-position="right"
                      />
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.smtpPortHint') }}
                      </div>
                    </el-form-item>
                  </el-col>

                  <!-- 第三行：发件人邮箱、授权码 -->
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.senderEmail')">
                      <el-input
                          v-model="emailConfig.sender_email"
                          :placeholder="$t('uiAutomation.notification.configs.senderEmailPlaceholder')"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.authCode')">
                      <el-input
                          v-model="emailConfig.smtp_password"
                          type="password"
                          show-password
                          :placeholder="emailConfig.has_password
                            ? $t('uiAutomation.notification.configs.authCodeKeepPlaceholder')
                            : $t('uiAutomation.notification.configs.authCodePlaceholder')"
                      />
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.authCodeHint') }}
                      </div>
                    </el-form-item>
                  </el-col>

                  <!-- 第四行：通知收件人 -->
                  <el-col :span="24">
                    <el-form-item :label="$t('uiAutomation.notification.configs.recipientEmails')">
                      <el-select
                          v-model="emailConfig.recipient_emails"
                          multiple
                          filterable
                          allow-create
                          default-first-option
                          :reserve-keyword="false"
                          :placeholder="$t('uiAutomation.notification.configs.recipientEmailsPlaceholder')"
                      >
                        <el-option
                            v-for="email in emailConfig.recipient_emails"
                            :key="email"
                            :label="email"
                            :value="email"
                        />
                      </el-select>
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.recipientEmailsHint') }}
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>

                <div class="form-actions">
                  <el-button :loading="testingEmail" @click="handleTestEmail">
                    {{ $t('uiAutomation.notification.configs.testConnection') }}
                  </el-button>
                  <el-button type="primary" :loading="savingEmail" @click="saveEmailConfigHandler">
                    {{ $t('uiAutomation.notification.configs.saveEmailConfig') }}
                  </el-button>
                </div>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <!-- 飞书机器人Tab -->
        <el-tab-pane :label="$t('uiAutomation.notification.configs.feishuBot')" name="feishu">
          <div class="tab-content">
            <div class="config-section">
              <el-form
                  ref="feishuFormRef"
                  :model="webhookBots.feishu"
                  label-position="top"
                  class="config-form"
              >
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.botName')">
                      <el-input
                          v-model="webhookBots.feishu.name"
                          :placeholder="$t('uiAutomation.notification.configs.feishuBotNamePlaceholder')"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item :label="$t('uiAutomation.notification.configs.enable')">
                      <el-switch v-model="webhookBots.feishu.enabled"/>
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item :label="$t('uiAutomation.notification.configs.webhookUrl')">
                      <el-input
                          v-model="webhookBots.feishu.webhook_url"
                          :placeholder="$t('uiAutomation.notification.configs.webhookPlaceholder')"
                      />
                      <div class="form-item-hint">
                        {{ $t('uiAutomation.notification.configs.feishuUrlHint') }}
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>

                <div class="form-actions">
                  <el-button :loading="testingFeishu" @click="handleTestFeishu">
                    {{ $t('uiAutomation.notification.configs.testSend') }}
                  </el-button>
                  <el-button type="primary" @click="saveWebhookBot('feishu')">
                    {{ $t('uiAutomation.notification.configs.saveFeishuConfig') }}
                  </el-button>
                </div>
              </el-form>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script>
import {Setting} from '@element-plus/icons-vue'
import {ref, reactive, computed, onMounted} from 'vue'
import {ElMessage} from 'element-plus'
import {
  getEmailConfig,
  saveEmailConfig,
  testEmailConfig,
  getUnifiedNotificationConfigs,
  createUnifiedNotificationConfig,
  updateUnifiedNotificationConfig,
  testNotificationWebhook
} from '@/api/core.js'
import { useI18n } from 'vue-i18n'

export default {
  name: 'NotificationConfigs',
  components: {
    Setting
  },
  setup() {
    const { t } = useI18n()

    // 数据状态
    const emailFormRef = ref(null)
    const feishuFormRef = ref(null)
    const activeTab = ref('email')
    const savingEmail = ref(false)
    const testingEmail = ref(false)
    const testingFeishu = ref(false)

    // 邮箱配置
    const emailConfig = reactive({
      name: '默认邮箱配置',
      smtp_host: '',
      smtp_port: 465,
      sender_email: '',
      smtp_password: '',
      use_ssl: true,
      use_tls: false,
      recipient_emails: [],
      is_active: true,
      has_password: false
    })

    // Webhook机器人配置（仅飞书）
    // 不再区分业务类型：配置后 UI自动化 / 接口测试 / APP自动化 全模块生效
    const webhookBots = reactive({
      feishu: {
        name: '',
        webhook_url: '',
        enabled: true,
        enable_ui_automation: true,
        enable_api_testing: true
      }
    })

    // 常见邮箱服务商预设：选择后自动带入 SMTP 端口与加密方式
    // 用户也可直接输入自定义域名（allow-create）
    const smtpHostOptions = computed(() => {
      const k = 'uiAutomation.notification.configs.smtpProviders'
      return [
        { label: t(`${k}.qq`), value: 'smtp.qq.com', port: 465, use_ssl: true },
        { label: t(`${k}.qqExmail`), value: 'smtp.exmail.qq.com', port: 465, use_ssl: true },
        { label: t(`${k}.netease163`), value: 'smtp.163.com', port: 465, use_ssl: true },
        { label: t(`${k}.netease126`), value: 'smtp.126.com', port: 465, use_ssl: true },
        { label: t(`${k}.neteaseQiye`), value: 'smtp.qiye.163.com', port: 465, use_ssl: true },
        { label: t(`${k}.aliyun`), value: 'smtp.aliyun.com', port: 465, use_ssl: true },
        { label: t(`${k}.feishu`), value: 'smtp.feishu.cn', port: 465, use_ssl: true },
        { label: t(`${k}.gmail`), value: 'smtp.gmail.com', port: 465, use_ssl: true },
        { label: t(`${k}.outlook`), value: 'smtp.office365.com', port: 587, use_ssl: false },
        { label: t(`${k}.sina`), value: 'smtp.sina.com', port: 465, use_ssl: true }
      ]
    })

    // 选择服务商后自动填充端口与加密方式；自定义域名则不改动
    const onSmtpHostChange = (host) => {
      const preset = smtpHostOptions.value.find(item => item.value === host)
      if (!preset) return
      emailConfig.smtp_port = preset.port
      emailConfig.use_ssl = preset.use_ssl
      emailConfig.use_tls = !preset.use_ssl
    }

    // SSL / TLS 互斥，切换时同步端口默认值
    const onSecureModeChange = (useSsl) => {
      emailConfig.use_ssl = useSsl
      emailConfig.use_tls = !useSsl
      if (useSsl && emailConfig.smtp_port === 587) {
        emailConfig.smtp_port = 465
      } else if (!useSsl && emailConfig.smtp_port === 465) {
        emailConfig.smtp_port = 587
      }
    }

    // 获取邮箱配置
    const fetchEmailConfig = async () => {
      try {
        const response = await getEmailConfig()
        const data = response.data || {}
        emailConfig.name = data.name || '默认邮箱配置'
        emailConfig.smtp_host = data.smtp_host || ''
        emailConfig.smtp_port = data.smtp_port || 465
        emailConfig.sender_email = data.sender_email || ''
        emailConfig.use_ssl = data.use_ssl !== false
        emailConfig.use_tls = data.use_tls === true
        emailConfig.recipient_emails = data.recipient_emails || []
        emailConfig.is_active = data.is_active !== false
        emailConfig.has_password = data.has_password === true
        // 授权码不回显：留空表示「保持原值」
        emailConfig.smtp_password = ''
      } catch (error) {
        console.error(t('uiAutomation.notification.configs.messages.emailGetFailed'), error)
      }
    }

    // 保存邮箱配置
    const saveEmailConfigHandler = async () => {
      if (!emailConfig.smtp_host || !emailConfig.sender_email) {
        ElMessage.warning(t('uiAutomation.notification.configs.messages.emailRequired'))
        return
      }

      savingEmail.value = true
      try {
        const payload = {
          name: emailConfig.name || '默认邮箱配置',
          smtp_host: emailConfig.smtp_host,
          smtp_port: emailConfig.smtp_port,
          sender_email: emailConfig.sender_email,
          use_ssl: emailConfig.use_ssl,
          use_tls: !emailConfig.use_ssl,
          recipient_emails: emailConfig.recipient_emails,
          is_active: emailConfig.is_active
        }
        // 留空表示不修改已保存的授权码
        if (emailConfig.smtp_password) {
          payload.smtp_password = emailConfig.smtp_password
        }

        const response = await saveEmailConfig(payload)
        emailConfig.has_password = response.data?.has_password === true
        emailConfig.smtp_password = ''
        ElMessage.success(t('uiAutomation.notification.configs.messages.emailSaveSuccess'))
      } catch (error) {
        console.error('保存邮箱配置失败:', error)
        ElMessage.error(t('uiAutomation.notification.configs.messages.emailSaveFailed') + ': ' + (error.response?.data?.detail || error.message))
      } finally {
        savingEmail.value = false
      }
    }

    // 测试邮箱配置
    const handleTestEmail = async () => {
      testingEmail.value = true
      try {
        const response = await testEmailConfig({})
        ElMessage.success(response.data?.detail || t('uiAutomation.notification.configs.messages.emailTestSuccess'))
      } catch (error) {
        console.error('测试邮箱配置失败:', error)
        ElMessage.error(error.response?.data?.detail || t('uiAutomation.notification.configs.messages.emailTestFailed'))
      } finally {
        testingEmail.value = false
      }
    }

    // 测试飞书机器人 Webhook：发送一条测试消息
    const handleTestFeishu = async () => {
      const { webhook_url, name } = webhookBots.feishu
      if (!webhook_url) {
        ElMessage.warning(t('uiAutomation.notification.configs.messages.webhookRequired'))
        return
      }
      testingFeishu.value = true
      try {
        const response = await testNotificationWebhook({
          webhook_url,
          bot_name: name || ''
        })
        ElMessage.success(response.data?.detail || t('uiAutomation.notification.configs.messages.webhookTestSuccess'))
      } catch (error) {
        console.error('测试飞书机器人失败:', error)
        ElMessage.error(error.response?.data?.detail || t('uiAutomation.notification.configs.messages.webhookTestFailed'))
      } finally {
        testingFeishu.value = false
      }
    }

    // 获取config_type映射
    const getConfigType = (botType) => {
      const configTypeMap = {
        'feishu': 'webhook_feishu'
      }
      return configTypeMap[botType]
    }

    // 获取机器人显示名称
    const getBotDisplayName = (botType) => {
      const displayNameMap = {
        'feishu': t('uiAutomation.notification.configs.platforms.feishu')
      }
      return displayNameMap[botType] || botType
    }

    // 保存Webhook机器人配置
    const saveWebhookBot = async (botType) => {
      const formRef = feishuFormRef.value
      if (!formRef) return

      try {
        const configType = getConfigType(botType)
        const botDisplayName = getBotDisplayName(botType)

        // 检查是否已存在对应类型的机器人配置
        let webhookConfigId = null
        try {
          const response = await getUnifiedNotificationConfigs({ config_type: configType })
          if (response.data.results && response.data.results.length > 0) {
            webhookConfigId = response.data.results[0].id
          }
        } catch (error) {
          console.log(t('uiAutomation.notification.configs.messages.noExistingConfig'))
        }

        const botConfig = webhookBots[botType]
        // 全模块生效：不再按业务类型过滤，统一置为启用
        const botData = {
          name: botConfig.name || `${botType}机器人`,
          webhook_url: botConfig.webhook_url,
          enabled: botConfig.enabled,
          enable_ui_automation: true,
          enable_api_testing: true
        }

        let requestData
        if (webhookConfigId) {
          // 更新现有配置 - 保留已有的其它字段
          const configResponse = await getUnifiedNotificationConfigs({ config_type: configType })
          const existingConfig = configResponse.data.results[0]
          const updatedWebhookBots = existingConfig.webhook_bots || {}
          updatedWebhookBots[botType] = botData

          requestData = {
            name: existingConfig.name || `${botDisplayName}${t('uiAutomation.notification.configs.title')}`,
            config_type: configType,
            webhook_bots: updatedWebhookBots,
            is_active: true
          }

          await updateUnifiedNotificationConfig(webhookConfigId, requestData)
          ElMessage.success(t('uiAutomation.notification.configs.messages.feishuUpdateSuccess'))
        } else {
          // 创建新配置
          requestData = {
            name: `${botDisplayName}${t('uiAutomation.notification.configs.title')}`,
            config_type: configType,
            webhook_bots: {
              [botType]: botData
            },
            is_active: true
          }

          await createUnifiedNotificationConfig(requestData)
          ElMessage.success(t('uiAutomation.notification.configs.messages.feishuCreateSuccess'))
        }

        // 重新加载数据以确保状态同步
        fetchWebhookConfig(botType)
      } catch (error) {
        console.error('保存Webhook机器人配置失败:', error)
        ElMessage.error(t('uiAutomation.notification.configs.messages.feishuSaveFailed') + ': ' + (error.response?.data?.detail || error.message))
      }
    }

    // 获取Webhook机器人配置
    const fetchWebhookConfig = async (botType) => {
      try {
        const configType = getConfigType(botType)
        const response = await getUnifiedNotificationConfigs({ config_type: configType })
        if (response.data.results && response.data.results.length > 0) {
          const config = response.data.results[0]

          if (config.webhook_bots && config.webhook_bots[botType]) {
            const bot = config.webhook_bots[botType]
            webhookBots[botType].name = bot.name || ''
            webhookBots[botType].webhook_url = bot.webhook_url || ''
            webhookBots[botType].enabled = bot.enabled !== false
            // 全模块生效，业务类型字段仅作占位
            webhookBots[botType].enable_ui_automation = true
            webhookBots[botType].enable_api_testing = true
          }
        }
      } catch (error) {
        console.error(t('uiAutomation.notification.configs.messages.getConfigFailed'), error)
      }
    }

    // 组件挂载时获取数据
    onMounted(async () => {
      try {
        await Promise.all([
          fetchEmailConfig(),
          fetchWebhookConfig('feishu')
        ])
      } catch (error) {
        console.error('NotificationConfigs 组件初始化失败:', error)
      }
    })

    return {
      emailFormRef,
      feishuFormRef,
      activeTab,
      savingEmail,
      testingEmail,
      testingFeishu,
      emailConfig,
      webhookBots,
      smtpHostOptions,
      onSmtpHostChange,
      onSecureModeChange,
      saveEmailConfigHandler,
      handleTestEmail,
      handleTestFeishu,
      fetchEmailConfig,
      saveWebhookBot,
      fetchWebhookConfig
    }
  }
}
</script>

<style scoped>
.notification-configs-container {
  padding: 20px;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--th-text-primary);
  letter-spacing: -0.02em;
  display: flex;
  align-items: center;
}

.title-icon {
  display: none;
}

.content-wrapper {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.notification-tabs :deep(.el-tabs__nav-wrap) {
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.notification-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.notification-tabs :deep(.el-tabs__nav-scroll) {
  padding: 0;
  width: 100%;
}

.notification-tabs :deep(.el-tabs__nav) {
  display: flex;
  width: 100%;
  float: none;
  background: #f8f9fa;
}

.notification-tabs :deep(.el-tabs__item) {
  flex: 1;
  width: 50%;
  max-width: 50%;
  padding: 16px 24px !important;
  font-size: 15px;
  font-weight: 500;
  color: #6c757d;
  border: none;
  text-align: center;
  justify-content: center;
}

.notification-tabs :deep(.el-tabs__item:hover) {
  color: #667eea;
  background: rgba(102, 126, 234, 0.08);
}

.notification-tabs :deep(.el-tabs__item.is-active) {
  color: #667eea;
  background: white;
  border-bottom: 2px solid #667eea;
}

.notification-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.notification-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.tab-content {
  padding: 24px;
}

.config-section {
  padding: 20px 0;
}

.config-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.form-item-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  line-height: 1.5;
}

.form-actions {
  margin-top: 20px;
  padding-top: 20px;
  text-align: right;
}

/* 收件人下拉支持输入新邮箱 */
.config-form :deep(.el-select) {
  width: 100%;
}

/* 让提示语始终换行显示在输入控件下方（内容区默认是 flex，会导致提示语横向排在窄控件右边） */
.config-form :deep(.el-form-item__content) {
  flex-wrap: wrap;
}

.config-form .form-item-hint {
  flex: 0 0 100%;
  width: 100%;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .notification-configs-container {
    padding: 16px;
  }

  .page-header {
    margin-bottom: 16px;
  }

  .page-title {
    font-size: 20px;
  }

  .notification-tabs :deep(.el-tabs__item) {
    padding: 12px 16px !important;
    font-size: 14px;
  }

  .tab-content {
    padding: 16px;
  }
}
</style>
