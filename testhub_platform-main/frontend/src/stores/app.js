import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import i18n from '@/locales'
import { getEnabledModuleSwitches } from '@/api/core'

function applyTheme(isDark) {
  const root = document.documentElement
  if (isDark) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export const useAppStore = defineStore('app', () => {
  const language = ref(localStorage.getItem('app-lang') || 'zh-cn')
  const isDark = ref(localStorage.getItem('app-theme') === 'dark')

  // 菜单开关：采用「默认启用 + 显式禁用」模型。
  // disabledKeys 中出现的 key（模块 key / 路由路径 / 首页入口 key）即为被禁用的项。
  const disabledKeys = ref([])
  const moduleLoaded = ref(false)
  const moduleLoading = ref(false)

  // 初始化主题
  applyTheme(isDark.value)

  const setLanguage = (lang) => {
    language.value = lang
    i18n.global.locale.value = lang
    localStorage.setItem('app-lang', lang)
    document.querySelector('html')?.setAttribute('lang', lang)
  }

  const setDark = (dark) => {
    isDark.value = dark
    localStorage.setItem('app-theme', dark ? 'dark' : 'light')
    applyTheme(dark)
  }

  const toggleDark = () => {
    setDark(!isDark.value)
  }

  // 指定 key（模块 key / 路由路径 / 首页入口 key）是否启用
  // 未加载完成前默认显示，避免菜单闪烁
  const isEnabled = (key) => {
    if (!moduleLoaded.value) return true
    return !disabledKeys.value.includes(key)
  }

  // 模块级开关（侧边栏模块分组 / 首页入口卡片）
  const isModuleEnabled = (key) => isEnabled(key)

  // 菜单项级开关（侧边栏单个菜单项）
  const isMenuEnabled = (key) => isEnabled(key)

  // 一组 key 中任意一个启用即视为启用（用于子菜单可见性判断）
  const isAnyEnabled = (keys) => {
    if (!moduleLoaded.value) return true
    return keys.some((key) => !disabledKeys.value.includes(key))
  }

  // 从后端加载被禁用的 key 列表（只加载一次，去重）
  const loadEnabledModules = async () => {
    if (moduleLoaded.value || moduleLoading.value) return
    moduleLoading.value = true
    try {
      const res = await getEnabledModuleSwitches()
      disabledKeys.value =
        Array.isArray(res?.disabled) && res.disabled.length ? res.disabled : []
    } catch (e) {
      // 加载失败时兜底：默认全部显示
      disabledKeys.value = []
    } finally {
      moduleLoaded.value = true
      moduleLoading.value = false
    }
  }

  // 强制刷新（配置页修改开关后调用，使菜单/首页实时生效）
  const refreshEnabledModules = async () => {
    moduleLoaded.value = false
    moduleLoading.value = false
    await loadEnabledModules()
  }

  watch(isDark, (val) => applyTheme(val))

  return {
    language, isDark,
    disabledKeys, moduleLoaded,
    setLanguage, setDark, toggleDark,
    isEnabled, isModuleEnabled, isMenuEnabled, isAnyEnabled,
    loadEnabledModules, refreshEnabledModules
  }
})
