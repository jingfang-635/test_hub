<template>
  <div class="admin-embed-container">
    <iframe
      :src="adminUrl"
      class="admin-iframe"
      frameborder="0"
      allowfullscreen
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // Admin 路径，如 '/admin/core/performancestatistics/'
  path: {
    type: String,
    required: true
  }
})

const adminUrl = computed(() => {
  // 通过 Vite 代理使用同源 URL，避免 iframe 跨域问题
  // Vite 已将 /admin/ 和 /static/ 代理到后端 8000
  return props.path
})
</script>

<style scoped>
.admin-embed-container {
  width: 100%;
  height: 100%; /* 自适应父容器，避免硬算高度导致外层多余滚动条 */
  overflow: hidden;
}

.admin-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 4px;
  background: #fff;
}
</style>
