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

  async function executeSql(sql: string, tableMapping: Record<string, string>) {
    return post<{ columns: string[]; rows: string[][] }>('/api/preview/sql', { sql, table_mapping: tableMapping })
  }

  async function executePipeline(state: any): Promise<Blob | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch('/api/wizard/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '执行失败', code: data?.code || 'EXECUTE_ERROR' }
        return null
      }
      return await resp.blob()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  return { loading, error, initScene, fetchPreview, generateYaml, executeSql, executePipeline }
}

export function useAiApi() {
  const suggesting = ref(false)
  const aiError = ref<string | null>(null)

  async function askSuggestion(category: string, context: Record<string, any>): Promise<string | null> {
    suggesting.value = true
    aiError.value = null
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 120000)
    try {
      const resp = await fetch('/api/ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, context }),
        signal: controller.signal,
      })
      const data = await resp.json()
      if (resp.ok) return data.content
      aiError.value = data.detail || data.error || '未知错误'
    } catch (e) {
      aiError.value = e instanceof DOMException && e.name === 'AbortError'
        ? 'AI 请求超时，请重试'
        : '网络请求失败'
    } finally {
      clearTimeout(timer)
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
