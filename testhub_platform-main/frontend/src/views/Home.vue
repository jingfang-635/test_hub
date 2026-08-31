<template>
  <div class="home-container">
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>

    <div class="content-wrapper">
      <div class="header-actions">
        <div class="th-utility-bar">
          <el-dropdown @command="handleLanguageChange" trigger="click">
            <button type="button" class="th-utility-btn">
              <svg class="lang-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18M12 3c2.5 2.8 3.8 5.7 3.8 9S14.5 18.2 12 21c-2.5-2.8-3.8-5.7-3.8-9S9.5 5.8 12 3z" />
              </svg>
              <span>{{ currentLanguage === 'zh-cn' ? 'ZH' : 'EN' }}</span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="zh-cn" :disabled="currentLanguage === 'zh-cn'">
                  {{ $t('home.language.zhCN') }}
                </el-dropdown-item>
                <el-dropdown-item command="en" :disabled="currentLanguage === 'en'">
                  {{ $t('home.language.en') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <button
            type="button"
            class="th-utility-btn"
            :title="appStore.isDark ? '切换浅色模式' : '切换深色模式'"
            @click="appStore.toggleDark()"
          >
            <el-icon>
              <Moon v-if="!appStore.isDark" />
              <Sunny v-else />
            </el-icon>
          </button>

          <el-dropdown @command="handleCommand" trigger="click">
            <button type="button" class="th-utility-btn">
              <el-icon><UserFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  {{ userStore.user?.username || $t('home.user') }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">{{ $t('home.logout') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <header class="hero">
        <h1 class="main-title">{{ $t('home.title') }}</h1>
        <p class="subtitle">{{ $t('home.subtitle') }}</p>
      </header>

      <div class="cards-container">
        <div
          v-for="card in moduleCards"
          :key="card.key"
          class="nav-card"
          role="button"
          tabindex="0"
          @click="handleNavigate(card.key)"
          @keyup.enter="handleNavigate(card.key)"
        >
          <div class="card-icon" :class="card.iconClass">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
          <h3>{{ card.title }}</h3>
          <p>{{ card.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MagicStick, Link, Monitor, DataLine, Cpu, Setting, ChatDotRound,
  UserFilled, Cellphone, Moon, Sunny
} from '@element-plus/icons-vue'

const router = useRouter()
const { t } = useI18n()
const userStore = useUserStore()
const appStore = useAppStore()

const currentLanguage = computed(() => appStore.language)

onMounted(() => {
  appStore.loadEnabledModules()
})

const moduleCards = computed(() => [
  {
    key: 'ai',
    moduleKey: 'ai-generation',
    title: t('home.aiCaseGeneration'),
    desc: t('home.aiCaseGenerationDesc'),
    icon: MagicStick,
    iconClass: 'ai-icon'
  },
  {
    key: 'api',
    moduleKey: 'api-testing',
    title: t('home.apiTesting'),
    desc: t('home.apiTestingDesc'),
    icon: Link,
    iconClass: 'api-icon'
  },
  {
    key: 'ui',
    moduleKey: 'ui-automation',
    title: t('home.uiAutomation'),
    desc: t('home.uiAutomationDesc'),
    icon: Monitor,
    iconClass: 'ui-icon'
  },
  {
    key: 'app',
    moduleKey: 'app-automation',
    title: 'APP自动化测试',
    desc: '基于Airtest的Android APP自动化测试',
    icon: Cellphone,
    iconClass: 'app-icon'
  },
  {
    key: 'data',
    moduleKey: 'data-factory',
    title: t('home.dataFactory'),
    desc: t('home.dataFactoryDesc'),
    icon: DataLine,
    iconClass: 'data-icon'
  },
  {
    key: 'ai-intelligent',
    moduleKey: 'ai-intelligent-mode',
    title: t('home.aiIntelligentMode'),
    desc: t('home.aiIntelligentModeDesc'),
    icon: Cpu,
    iconClass: 'ai-intelligent-icon'
  },
  {
    key: 'assistant',
    moduleKey: 'assistant',
    title: t('home.aiEvaluator'),
    desc: t('home.aiEvaluatorDesc'),
    icon: ChatDotRound,
    iconClass: 'assistant-icon'
  },
  {
    key: 'config',
    moduleKey: 'configuration',
    title: t('home.configCenter'),
    desc: t('home.configCenterDesc'),
    icon: Setting,
    iconClass: 'config-icon'
  }
].filter(card => appStore.isModuleEnabled(card.moduleKey)))

const handleLanguageChange = (lang) => {
  appStore.setLanguage(lang)
}

const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  }
}

const handleLogout = () => {
  ElMessageBox.confirm(t('home.logoutConfirm'), t('common.tips'), {
    confirmButtonText: t('common.confirm'),
    cancelButtonText: t('common.cancel'),
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
    ElMessage.success(t('home.logoutSuccess'))
  }).catch(() => {})
}

const handleNavigate = (type) => {
  const routes = {
    'ai': '/ai-generation/requirement-analysis',
    'api': '/api-testing/dashboard',
    'ui': '/ui-automation/dashboard',
    'app': '/app-automation/dashboard',
    'ai-intelligent': '/ai-intelligent-mode/testing',
    'assistant': '/ai-generation/assistant',
    'config': '/configuration/ai-model',
    'data': '/data-factory'
  }

  if (routes[type]) {
    const routeData = router.resolve({ path: routes[type] })
    window.open(routeData.href, '_blank')
  }
}
</script>

<style scoped lang="scss">
.home-container {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 48px 24px;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(125, 211, 252, 0.35), transparent 55%),
    radial-gradient(900px 500px at 95% 0%, rgba(196, 181, 253, 0.32), transparent 50%),
    radial-gradient(800px 500px at 80% 100%, rgba(167, 243, 208, 0.28), transparent 55%),
    radial-gradient(700px 400px at 0% 90%, rgba(253, 186, 116, 0.18), transparent 50%),
    var(--th-bg-page);
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
  opacity: 0.55;
  animation: float 12s ease-in-out infinite;
}

.orb-1 {
  width: 320px;
  height: 320px;
  left: -80px;
  top: 20%;
  background: rgba(125, 211, 252, 0.45);
}

.orb-2 {
  width: 280px;
  height: 280px;
  right: -60px;
  top: 10%;
  background: rgba(196, 181, 253, 0.4);
  animation-delay: -4s;
}

.orb-3 {
  width: 260px;
  height: 260px;
  right: 15%;
  bottom: -40px;
  background: rgba(167, 243, 208, 0.35);
  animation-delay: -7s;
}

@keyframes float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-18px) scale(1.04); }
}

.content-wrapper {
  text-align: center;
  max-width: 1120px;
  width: 100%;
  position: relative;
  z-index: 1;
}

.header-actions {
  position: absolute;
  top: 0;
  right: 0;

  .lang-icon {
    width: 16px;
    height: 16px;
  }
}

.hero {
  margin-bottom: 48px;
  animation: fadeUp 0.55s ease-out;
}

.main-title {
  font-size: clamp(2rem, 4vw, 3.25rem);
  color: var(--th-text-primary);
  margin: 0 0 12px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.subtitle {
  font-size: clamp(1rem, 1.6vw, 1.25rem);
  color: var(--th-text-secondary);
  margin: 0;
  font-weight: 500;
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
  animation: fadeUp 0.7s ease-out 0.08s both;
}

.nav-card {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: var(--th-radius-lg);
  padding: 28px 18px 24px;
  cursor: pointer;
  transition: transform var(--th-transition), box-shadow var(--th-transition), background var(--th-transition), border-color var(--th-transition);
  box-shadow: var(--th-shadow-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  backdrop-filter: blur(10px);
  min-height: 196px;

  &:hover {
    transform: translateY(-8px);
    box-shadow: var(--th-shadow-md);
    background: var(--th-bg-elevated);
    border-color: var(--th-color-primary-soft);
  }

  &:focus-visible {
    outline: 2px solid var(--th-color-primary);
    outline-offset: 2px;
  }

  h3 {
    font-size: 1.05rem;
    color: var(--th-text-primary);
    margin: 16px 0 8px;
    font-weight: 700;
  }

  p {
    color: var(--th-text-secondary);
    line-height: 1.55;
    margin: 0;
    font-size: 0.86rem;
  }
}

html.dark .nav-card {
  background: rgba(23, 27, 38, 0.82);
  border-color: var(--th-border);
}

.card-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  transition: transform var(--th-transition);

  &.ai-icon {
    background: rgba(255, 138, 101, 0.14);
    color: var(--th-accent-peach);
  }

  &.api-icon {
    background: rgba(66, 165, 245, 0.14);
    color: var(--th-accent-blue);
  }

  &.ui-icon {
    background: rgba(255, 183, 77, 0.16);
    color: var(--th-accent-amber);
  }

  &.app-icon {
    background: rgba(240, 98, 146, 0.14);
    color: var(--th-accent-pink);
  }

  &.data-icon {
    background: rgba(102, 187, 106, 0.14);
    color: var(--th-accent-green);
  }

  &.ai-intelligent-icon {
    background: rgba(255, 152, 0, 0.14);
    color: var(--th-accent-orange);
  }

  &.assistant-icon {
    background: rgba(255, 152, 0, 0.12);
    color: #fb8c00;
  }

  &.config-icon {
    background: rgba(38, 166, 154, 0.14);
    color: var(--th-accent-teal);
  }
}

.nav-card:hover .card-icon {
  transform: scale(1.08);
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media screen and (max-width: 1100px) {
  .cards-container {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media screen and (max-width: 800px) {
  .home-container {
    padding: 88px 16px 40px;
    align-items: flex-start;
  }

  .header-actions {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 5;
  }

  .cards-container {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .nav-card {
    min-height: 170px;
    padding: 22px 14px;
  }
}

@media screen and (max-width: 480px) {
  .cards-container {
    grid-template-columns: 1fr;
  }

  .hero {
    margin-bottom: 28px;
  }
}
</style>
