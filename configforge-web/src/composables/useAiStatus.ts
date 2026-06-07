import { ref } from 'vue'

// 模块级单例，三态：null = 未检测，true = 已配置可用，false = 已检测不可用
const aiConfigured = ref<boolean | null>(null)
const checking = ref(false)

export function useAiStatus() {
  async function checkStatus() {
    if (checking.value) return
    checking.value = true
    try {
      const resp = await fetch('/api/ai/settings')
      if (resp.ok) {
        const data = await resp.json()
        aiConfigured.value = !!(data.enabled && data.api_key && data.api_key.length > 0)
      } else {
        aiConfigured.value = false
      }
    } catch {
      aiConfigured.value = false
    } finally {
      checking.value = false
    }
  }

  function markConfigured() {
    aiConfigured.value = true
  }

  return { aiConfigured, checking, checkStatus, markConfigured }
}
