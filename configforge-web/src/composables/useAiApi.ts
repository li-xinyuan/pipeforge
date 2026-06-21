import { ref, watch } from 'vue'
import { useApi, ApiError, handleApiError } from './useApi'

export function useAiApi() {
  const { loading: suggesting, error: apiError, requestOrThrow } = useApi()
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
      const data = await requestOrThrow<{ content: string }>('POST', '/api/ai/suggest', { category, context }, { signal: controller.signal })
      return data?.content ?? null
    } catch (e) {
      if (e instanceof ApiError) {
        aiError.value = e.message
        handleApiError(e)
      }
      return null
    } finally {
      clearTimeout(timer)
    }
  }

  async function getAiSettings() {
    try {
      return await requestOrThrow<Record<string, unknown>>('GET', '/api/ai/settings')
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function updateAiSettings(body: Record<string, unknown>) {
    try {
      await requestOrThrow<unknown>('PUT', '/api/ai/settings', body)
      return true
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return false
    }
  }

  async function testAiConnection() {
    try {
      const data = await requestOrThrow<{ ok?: boolean } & Record<string, unknown>>('POST', '/api/ai/test')
      return { ok: true, data }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return { ok: false, data: null }
    }
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
      return await requestOrThrow<{
        steps: Array<
          | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string }
          | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string }
        >
        explanation: string
        raw?: string
        parse_error?: boolean
      }>('POST', '/api/ai/orchestrate', { context }, { signal: controller.signal })
    } catch (e) {
      if (e instanceof ApiError) {
        aiError.value = e.message
        handleApiError(e)
      }
      return null
    } finally {
      clearTimeout(timer)
    }
  }

  return { suggesting, aiError, askSuggestion, askOrchestrate, getAiSettings, updateAiSettings, testAiConnection }
}
