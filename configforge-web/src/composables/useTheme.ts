import { ref } from 'vue'

const THEME_KEY = 'configforge-theme'
const isDark = ref(false)

function initTheme() {
  try {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'dark') {
      isDark.value = true
    } else if (stored === 'light') {
      isDark.value = false
    } else {
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
  } catch {
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyTheme()
}

function applyTheme() {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  try {
    localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
  } catch {
    // localStorage unavailable (private browsing, storage full) — silently ignore
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
}

export function useTheme() {
  return { isDark, initTheme, toggleTheme }
}
