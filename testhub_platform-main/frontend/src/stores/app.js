import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import i18n from '@/locales'

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

  watch(isDark, (val) => applyTheme(val))

  return { language, isDark, setLanguage, setDark, toggleDark }
})
