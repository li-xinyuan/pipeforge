import { ref } from 'vue'

const aiConfigured = ref(false)

export function useAiStatus() {
  async function checkStatus() {
    try {
      const resp = await fetch('/api/ai/settings')
      if (resp.ok) {
        const data = await resp.json()
        aiConfigured.value = !!(data.enabled && data.api_key && data.api_key.length > 0)
      }
    } catch {
      aiConfigured.value = false
    }
  }

  function markConfigured() {
    aiConfigured.value = true
  }

  return { aiConfigured, checkStatus, markConfigured }
}
