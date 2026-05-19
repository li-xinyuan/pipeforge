<template>
  <NConfigProvider :theme="naiveTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NModalProvider>
        <NDialogProvider>
          <div class="app-shell">
            <router-view />
          </div>
        </NDialogProvider>
      </NModalProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  NConfigProvider,
  NMessageProvider,
  NModalProvider,
  NDialogProvider,
  darkTheme,
} from 'naive-ui'
import { useTheme } from './composables/useTheme'
import 'highlight.js/lib/languages/yaml'

const { isDark, initTheme } = useTheme()
initTheme()

const naiveTheme = computed(() => isDark.value ? darkTheme : undefined)

const themeOverrides = {
  common: {
    primaryColor: '#0d9488',
    primaryColorHover: '#14b8a6',
    primaryColorPressed: '#0f766e',
    primaryColorSuppl: '#14b8a6',
    borderRadius: '8px',
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  Button: {
    borderRadiusMedium: '8px',
    colorPrimary: '#0d9488',
    colorPrimaryHover: '#14b8a6',
    colorPrimaryPressed: '#0f766e',
  },
  Card: {
    borderRadius: '14px',
  },
  Steps: {
    stepHeaderFontSize: '13px',
    headerTextColorProcess: '#0d9488',
    headerTextColorWait: '#94a3b8',
    headerTextColorFinish: '#64748b',
    indicatorColorProcess: '#0d9488',
    indicatorBorderColorProcess: '#0f766e',
  },
  Tag: {
    borderRadius: '6px',
  },
}
</script>

<style>
.app-shell {
  min-height: 100vh;
}
</style>
