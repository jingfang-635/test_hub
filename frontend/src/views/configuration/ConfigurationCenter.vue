<template>
  <div class="configuration-center">
    <div class="content-area">
      <router-view v-slot="{ Component, route }">
        <transition name="fade" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
// No script logic needed for now
</script>

<style scoped>
.configuration-center {
  height: 100%;
  width: 100%;
  max-height: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

.content-area {
  height: 100%;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  box-sizing: border-box;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
