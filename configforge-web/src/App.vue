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

const lightThemeOverrides = {
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

const darkThemeOverrides = {
  common: {
    primaryColor: '#14b8a6',
    primaryColorHover: '#2dd4bf',
    primaryColorPressed: '#0d9488',
    primaryColorSuppl: '#2dd4bf',
    borderRadius: '8px',
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    bodyColor: '#1c1917',
    cardColor: '#292524',
    modalColor: '#292524',
    popoverColor: '#292524',
    tableColor: '#292524',
    inputColor: 'rgba(41,37,36,0.5)',
    actionColor: '#292524',
    hoverColor: 'rgba(41,37,36,0.7)',
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
  Input: {
    colorFocus: 'rgba(41,37,36,0.7)',
    borderFocus: '1px solid #14b8a6',
    boxShadowFocus: '0 0 0 2px rgba(20,184,166,0.2)',
  },
  Steps: {
    stepHeaderFontSize: '13px',
    headerTextColorProcess: '#14b8a6',
    headerTextColorWait: '#78716c',
    headerTextColorFinish: '#a8a29e',
    indicatorColorProcess: '#14b8a6',
    indicatorBorderColorProcess: '#0d9488',
  },
  Tag: {
    borderRadius: '6px',
  },
  DataTable: {
    thColor: '#292524',
    tdColor: '#292524',
    tdColorHover: 'rgba(41,37,36,0.7)',
  },
}

const themeOverrides = computed(() => isDark.value ? darkThemeOverrides : lightThemeOverrides)
</script>

<style>
.app-shell {
  min-height: 100vh;
}
</style>
