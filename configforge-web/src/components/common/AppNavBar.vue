<template>
  <nav class="app-nav-bar">
    <div class="app-nav-bar__left">
      <router-link to="/" class="app-nav-bar__brand">
        <span class="app-nav-bar__logo">⚡</span>
        <span class="app-nav-bar__name">ConfigForge</span>
      </router-link>
      <span v-if="badge" class="app-nav-bar__badge">{{ badge }}</span>
    </div>
    <div class="app-nav-bar__right">
      <router-link to="/" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'home' }" :aria-current="currentRoute === 'home' ? 'page' : undefined">我的配置</router-link>
      <router-link to="/history" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'history' }" :aria-current="currentRoute === 'history' ? 'page' : undefined">执行历史</router-link>
      <router-link to="/schedules" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'schedules' }" :aria-current="currentRoute === 'schedules' ? 'page' : undefined">定时任务</router-link>
      <router-link to="/settings" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'settings' }" :aria-current="currentRoute === 'settings' ? 'page' : undefined">AI 设置</router-link>
      <button class="app-nav-bar__theme-btn" @click="toggleTheme" :title="isDark ? '切换亮色模式' : '切换暗色模式'">
        {{ isDark ? '☀' : '☾' }}
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

defineProps<{
  currentRoute: 'home' | 'wizard' | 'settings' | 'history' | 'schedules' | 'guide'
  badge?: string
}>()

const isDark = ref(false)

onMounted(() => {
  isDark.value = document.documentElement.getAttribute('data-theme') === 'dark'
})

function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
}
</script>

<style scoped>
.app-nav-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--color-surface-glass);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--color-border-light);
  transition: background var(--transition-normal);
}
.app-nav-bar__left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.app-nav-bar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--color-text);
}
.app-nav-bar__logo {
  font-size: 20px;
}
.app-nav-bar__name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}
.app-nav-bar__badge {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
  border: 1px solid var(--color-primary-border);
}
.app-nav-bar__right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.app-nav-bar__link {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
  padding: 4px 0;
}
.app-nav-bar__link:hover {
  color: var(--color-primary);
}
.app-nav-bar__link--active {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}
.app-nav-bar__theme-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  color: var(--color-text);
}
.app-nav-bar__theme-btn:hover {
  border-color: var(--color-primary-lighter);
  background: var(--color-primary-bg);
}

/* Mobile */
@media (max-width: 767px) {
  .app-nav-bar {
    padding: 0 12px;
  }
  .app-nav-bar__name {
    display: none;
  }
  .app-nav-bar__link {
    font-size: var(--font-size-xs);
  }
}
</style>
