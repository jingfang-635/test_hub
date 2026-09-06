<template>
  <el-config-provider :locale="elementLocale">
    <div id="app">
      <router-view />
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ElConfigProvider } from 'element-plus'
import { useAppStore } from '@/stores/app'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

const appStore = useAppStore()

const elementLocale = computed(() => {
  return appStore.language === 'zh-cn' ? zhCn : en
})

onMounted(() => {
  // initAuth 已在 main.js 完成，这里不再重复调用
  document.documentElement.classList.toggle('dark', appStore.isDark)
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

#app {
  font-family: 'Plus Jakarta Sans', 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Noto Sans SC', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
  width: 100vw;
  background: var(--th-bg-page);
  color: var(--th-text-primary);
}
</style>
