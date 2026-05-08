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
