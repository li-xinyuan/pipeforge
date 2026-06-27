import { createI18n } from 'vue-i18n'
import zhCN from '../locales/zh-CN.json'
import enUS from '../locales/en-US.json'

export type AppLocale = 'zh-CN' | 'en-US'

export const AVAILABLE_LOCALES: { value: AppLocale; label: string }[] = [
  { value: 'zh-CN', label: '中文' },
  { value: 'en-US', label: 'English' },
]

const STORAGE_KEY = 'configforge_locale'

/** Safely read from localStorage (may be unavailable in some test/private-mode contexts). */
function readStorage(key: string): string | null {
  try {
    if (typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function') {
      return localStorage.getItem(key)
    }
  } catch {
    // Ignore storage errors (e.g., private mode, sandboxed iframe)
  }
  return null
}

/** Read persisted locale from localStorage, fall back to browser language, then zh-CN. */
function detectInitialLocale(): AppLocale {
  const saved = readStorage(STORAGE_KEY)
  if (saved === 'zh-CN' || saved === 'en-US') return saved
  const navLang = (typeof navigator !== 'undefined' ? navigator.language : '') || ''
  if (navLang.startsWith('en')) return 'en-US'
  return 'zh-CN'
}

const initialLocale = detectInitialLocale()

const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export function setLocale(locale: AppLocale): void {
  i18n.global.locale.value = locale
  try {
    if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
      localStorage.setItem(STORAGE_KEY, locale)
    }
  } catch {
    // Ignore storage errors (e.g., private mode)
  }
  // Update <html lang> attribute for accessibility
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale === 'en-US' ? 'en' : 'zh-CN'
  }
}

// Sync <html lang> on initial load
if (typeof document !== 'undefined') {
  document.documentElement.lang = initialLocale === 'en-US' ? 'en' : 'zh-CN'
}

export default i18n
