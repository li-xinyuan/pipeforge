import './style.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'
import { setupErrorReporting, reportError } from './utils/errorReport'
import { usePwa } from './composables/usePwa'
import i18n from './i18n'

const app = createApp(App)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
app.use(router)
app.use(i18n)

// Setup frontend error reporting (global handlers)
setupErrorReporting()

// Register PWA service worker (only in production build)
if (import.meta.env.PROD) {
  const { initPwa } = usePwa()
  initPwa()
}

// Global error handler — prevents unhandled errors from crashing the UI
app.config.errorHandler = (err, _instance, info) => {
  // eslint-disable-next-line no-console
  console.error('[ConfigForge] Unhandled error:', err, info)
  reportError(err instanceof Error ? err : String(err), { info })
}

app.mount('#app')
