import { ref } from 'vue'
import type { AiSuggestion } from '../types/wizard'

export function useAiSuggest() {
  const suggesting = ref(false)
  const suggestion = ref<AiSuggestion | null>(null)
  const error = ref<string | null>(null)
  const aiConfigured = ref(false)

  async function askSuggestion(category: string, context: any) {
    suggesting.value = true; error.value = null
    try {
      const resp = await fetch('/api/ai/suggest', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, context }),
      })
      const data = await resp.json()
      if (!resp.ok) { error.value = data.error; return }
      suggestion.value = { content: data.content, category: data.category, status: 'pending', timestamp: Date.now() }
    } catch {
      error.value = 'AI 服务不可用'
    } finally { suggesting.value = false }
  }

  function accept() { if (suggestion.value) suggestion.value.status = 'accepted' }
  async function regenerate(feedback?: string) { if (suggestion.value) await askSuggestion(suggestion.value.category, { feedback }) }

  return { suggesting, suggestion, error, aiConfigured, askSuggestion, accept, regenerate }
}
