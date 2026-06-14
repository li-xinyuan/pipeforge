import { ref } from 'vue'

const aiConfigured = ref(false)
const aiProvider = ref('')
const aiModel = ref('')

export function useAiStatus() {
  async function checkStatus() {
    try {
      const resp = await fetch('/api/ai/settings')
      if (resp.ok) {
        const data = await resp.json()
        aiConfigured.value = !!(data.enabled && data.api_key && data.api_key.length > 0)
        if (aiConfigured.value) {
          aiProvider.value = data.provider || ''
          aiModel.value = data.model || ''
        }
      }
    } catch {
      aiConfigured.value = false
    }
  }

  function markConfigured() {
    aiConfigured.value = true
  }

  return { aiConfigured, aiProvider, aiModel, checkStatus, markConfigured }
}
