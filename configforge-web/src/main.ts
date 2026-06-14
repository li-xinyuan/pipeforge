import './style.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
app.use(router)

// Global error handler — prevents unhandled errors from crashing the UI
app.config.errorHandler = (err, _instance, info) => {
  console.error('[ConfigForge] Unhandled error:', err, info)
}

app.mount('#app')
