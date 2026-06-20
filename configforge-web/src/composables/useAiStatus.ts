import { ref } from 'vue'
import { useApi, type AiSettings } from './useApi'

const aiConfigured = ref(false)
const aiProvider = ref('')
const aiModel = ref('')

export function useAiStatus() {
  const { getAiSettings } = useApi()

  async function checkStatus() {
    try {
      const data = await getAiSettings()
      if (data) {
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
