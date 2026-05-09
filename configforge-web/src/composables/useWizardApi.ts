import { ref } from 'vue'

export function useWizardApi() {
  const loading = ref(false)
  const error = ref<{ message: string; code: string } | null>(null)

  async function post<T>(url: string, body: any): Promise<T | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await resp.json()
      if (!resp.ok) { error.value = { message: data.error, code: data.code }; return null }
      return data as T
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function initScene(fileIds: string[]) { return post<any>('/api/wizard/init-scene', { file_ids: fileIds }) }

  async function fetchPreview(fileId: string, sheet?: string) {
    return post<{ sheets: string[]; columns: string[]; rows: string[][] }>('/api/preview/file', { file_id: fileId, sheet })
  }

  async function generateYaml(state: any) {
    return post<{ yaml: string }>('/api/wizard/generate', { state })
  }

  return { loading, error, initScene, fetchPreview, generateYaml }
}

export function useAiApi() {
  const suggesting = ref(false)
  const aiError = ref<string | null>(null)

  async function askSuggestion(category: string, context: Record<string, any>): Promise<string | null> {
    suggesting.value = true
    aiError.value = null
    try {
      const resp = await fetch('/api/ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, context }),
      })
      const data = await resp.json()
      if (resp.ok) return data.content
      aiError.value = data.detail || data.error || '未知错误'
    } catch (e) {
      aiError.value = '网络请求失败'
    } finally {
      suggesting.value = false
    }
    return null
  }

  async function getAiSettings() {
    const resp = await fetch('/api/ai/settings')
    if (resp.ok) return await resp.json()
    return null
  }

  async function updateAiSettings(body: Record<string, any>) {
    const resp = await fetch('/api/ai/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return resp.ok
  }

  async function testAiConnection() {
    const resp = await fetch('/api/ai/test', { method: 'POST' })
    const data = await resp.json().catch(() => null)
    return { ok: resp.ok, data }
  }

  return { suggesting, aiError, askSuggestion, getAiSettings, updateAiSettings, testAiConnection }
}
