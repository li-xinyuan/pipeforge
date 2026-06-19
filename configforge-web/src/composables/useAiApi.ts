import { ref, watch } from 'vue'
import { useApi } from './useApi'

export function useAiApi() {
  const { loading: suggesting, error: apiError, request } = useApi()
  const aiError = ref<string | null>(null)

  // Sync API error to aiError
  watch(apiError, (err) => {
    if (err) aiError.value = err.message
  })

  async function askSuggestion(category: string, context: Record<string, unknown>): Promise<string | null> {
    aiError.value = null
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 120000)
    try {
      const data = await request<{ content: string }>('POST', '/api/ai/suggest', { category, context }, { signal: controller.signal })
      return data?.content ?? null
    } finally {
      clearTimeout(timer)
    }
  }

  async function getAiSettings() {
    return request<Record<string, unknown>>('GET', '/api/ai/settings')
  }

  async function updateAiSettings(body: Record<string, unknown>) {
    const result = await request<unknown>('PUT', '/api/ai/settings', body)
    return result !== null
  }

  async function testAiConnection() {
    const data = await request<{ ok?: boolean } & Record<string, unknown>>('POST', '/api/ai/test')
    return { ok: data !== null, data }
  }

  async function askOrchestrate(context: Record<string, unknown>): Promise<{
    steps: Array<
      | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string }
      | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string }
    >
    explanation: string
    raw?: string
    parse_error?: boolean
  } | null> {
    aiError.value = null
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 120000)
    try {
      return await request<{
        steps: Array<
          | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string }
          | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string }
        >
        explanation: string
        raw?: string
        parse_error?: boolean
      }>('POST', '/api/ai/orchestrate', { context }, { signal: controller.signal })
    } finally {
      clearTimeout(timer)
    }
  }

  return { suggesting, aiError, askSuggestion, askOrchestrate, getAiSettings, updateAiSettings, testAiConnection }
}
