<template>
  <div class="module-switch-config">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('menu.moduleSwitchConfig') }}</h2>
        <p class="page-desc">控制各页面菜单在侧边栏及首页入口中的显示，关闭后对应菜单将不再显示。</p>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="将「功能模块」开关关闭会隐藏整个模块（含其下所有菜单）；单独关闭某个菜单项仅隐藏该菜单。"
      class="page-tip"
    />

    <el-card v-loading="loading" shadow="never" class="group-card">
      <div
        v-for="group in groups"
        :key="group.key"
        class="module-group"
      >
        <div class="group-header">
          <div class="group-title">
            <span class="group-name">{{ groupName(group) }}</span>
            <span class="group-key">{{ group.key }}</span>
            <el-tag v-if="group.moduleRec" size="small" type="info" effect="plain">模块开关</el-tag>
          </div>
          <el-switch
            v-model="group.moduleEnabled"
            :disabled="updatingKey === group.key"
            @change="handleModuleToggle(group)"
          />
        </div>

        <div class="group-body">
          <div
            v-for="item in group.itemList"
            :key="item.key"
            class="menu-row"
          >
            <div class="menu-name">
              <span>{{ itemName(item) }}</span>
              <span class="menu-key">{{ item.key }}</span>
            </div>
            <el-switch
              v-model="item.is_enabled"
              :disabled="updatingKey === item.key"
              @change="handleItemToggle(item)"
            />
          </div>
        </div>
      </div>

      <!-- 首页入口 -->
      <div class="module-group">
        <div class="group-header">
          <div class="group-title">
            <span class="group-name">首页入口</span>
            <span class="group-key">home</span>
          </div>
        </div>
        <div class="group-body">
          <div
            v-for="item in homeItems"
            :key="item.key"
            class="menu-row"
          >
            <div class="menu-name">
              <span>{{ itemName(item) }}</span>
              <span class="menu-key">{{ item.key }}</span>
            </div>
            <el-switch
              v-model="item.is_enabled"
              :disabled="updatingKey === item.key"
              @change="handleItemToggle(item)"
            />
          </div>
        </div>
      </div>

      <el-empty v-if="!groups.length && !homeItems.length" description="暂无菜单项" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import {
  getModuleSwitches,
  toggleModuleSwitch,
  toggleModuleSwitchByKey
} from '@/api/core'
import { MODULE_GROUPS, HOME_ENTRIES, menuItemsByModule } from '@/config/menuConfig'

const { t } = useI18n()
const appStore = useAppStore()

const loading = ref(false)
const updatingKey = ref(null)
const groups = ref([])
const homeItems = ref([])

// 菜单项显示名：优先 i18n，缺失时用中文兜底
const itemName = (item) => {
  if (item.nameKey) {
    const translated = t(item.nameKey)
    if (translated && translated !== item.nameKey) return translated
  }
  return item.name || item.nameKey || item.key
}

// 模块分组显示名
const groupName = (group) => {
  if (group.nameKey) {
    const translated = t(group.nameKey)
    if (translated && translated !== group.nameKey) return translated
  }
  return group.fallbackName || group.key
}

// 合并后端记录与前端注册表：未落库的菜单项默认启用
const buildView = (records) => {
  const map = new Map(records.map((r) => [r.key, r]))

  const gs = MODULE_GROUPS.map((g) => {
    const moduleRec = map.get(g.key)
    const itemList = menuItemsByModule(g.key).map((item) => {
      const rec = map.get(item.key)
      return {
        ...item,
        id: rec?.id || null,
        is_enabled: rec ? rec.is_enabled : true,
        location: rec?.location || item.location || 'sidebar'
      }
    })
    return {
      ...g,
      moduleRec,
      moduleEnabled: moduleRec ? moduleRec.is_enabled : true,
      itemList
    }
  })

  const homes = HOME_ENTRIES.map((item) => {
    const rec = map.get(item.key)
    return {
      ...item,
      id: rec?.id || null,
      is_enabled: rec ? rec.is_enabled : true,
      location: rec?.location || 'home'
    }
  })

  return { groups: gs, homeItems: homes }
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getModuleSwitches()
    const records = Array.isArray(res) ? res : res?.results || []
    const view = buildView(records)
    groups.value = view.groups
    homeItems.value = view.homeItems
  } catch (e) {
    ElMessage.error('加载菜单开关列表失败')
  } finally {
    loading.value = false
  }
}

// 执行切换：有 id 走记录切换，无 id 则按 key 自动创建（未落库的菜单项）
const doToggle = async (item, enabled, extra = {}) => {
  updatingKey.value = item.key
  try {
    if (item.id) {
      await toggleModuleSwitch(item.id, enabled)
    } else {
      await toggleModuleSwitchByKey(item.key, enabled, extra)
    }
    ElMessage.success(enabled ? '已启用' : '已停用')
    // 刷新已启用菜单，使侧边栏 / 首页实时生效
    await appStore.refreshEnabledModules()
    // 重新拉取列表，刷新 id / 状态
    await fetchList()
  } catch (e) {
    // 回退开关状态
    item.is_enabled = !enabled
    ElMessage.error('操作失败')
  } finally {
    updatingKey.value = null
  }
}

const handleItemToggle = async (item) => {
  await doToggle(item, item.is_enabled, {
    name: itemName(item),
    location: item.location
  })
}

const handleModuleToggle = async (group) => {
  const enabled = group.moduleEnabled
  updatingKey.value = group.key
  try {
    if (group.moduleRec?.id) {
      await toggleModuleSwitch(group.moduleRec.id, enabled)
    } else {
      await toggleModuleSwitchByKey(group.key, enabled, {
        name: groupName(group),
        location: 'all'
      })
    }
    ElMessage.success(enabled ? '模块已启用' : '模块已停用')
    await appStore.refreshEnabledModules()
    await fetchList()
  } catch (e) {
    group.moduleEnabled = !enabled
    ElMessage.error('操作失败')
  } finally {
    updatingKey.value = null
  }
}

onMounted(fetchList)
</script>

<style scoped>
.module-switch-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: var(--th-text-primary);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--th-text-secondary);
}

.page-tip {
  margin-bottom: 4px;
}

.group-card :deep(.el-card__body) {
  padding: 4px 20px 20px;
}

.module-group {
  padding: 16px 0;
  border-bottom: 1px solid var(--th-border);
}

.module-group:last-child {
  border-bottom: none;
  padding-bottom: 4px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--th-text-primary);
}

.group-key {
  font-size: 12px;
  color: var(--th-text-secondary);
  background: var(--th-bg-muted);
  padding: 1px 8px;
  border-radius: 10px;
}

.group-body {
  display: flex;
  flex-wrap: wrap;
  gap: 0 24px;
}

.menu-row {
  flex: 0 1 300px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
}

.menu-row:hover {
  background: var(--th-bg-hover);
}

.menu-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
  margin-right: 12px;
}

.menu-name span:first-child {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--th-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-key {
  font-size: 11.5px;
  color: var(--th-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
