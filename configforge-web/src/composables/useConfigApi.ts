import { ref } from 'vue'
import type { SavedConfig, WizardState } from '../types/wizard'
import { stateToSnakeCase } from '../utils/serialization'

function mapConfig(raw: Record<string, unknown>): SavedConfig {
  return {
    id: raw.id as string,
    sceneName: raw.scene_name as string,
    description: (raw.description || '') as string,
    inputCount: raw.input_count as number,
    outputType: raw.output_type as string,
    version: raw.version as string,
    updatedAt: raw.updated_at as string,
    inputs: ((raw.inputs || []) as Record<string, unknown>[]).map((i) => ({
      name: i.name as string,
      paramKey: i.param_key as string,
      plugin: i.plugin as string,
    })),
  }
}

export interface ConfigListResult {
  items: SavedConfig[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export function useConfigApi() {
  const loading = ref(false)
  const error = ref<{ message: string; code: string } | null>(null)

  async function post<T>(url: string, body: unknown): Promise<T | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      if (!resp.ok) { error.value = { message: data.error || data.detail, code: data.code }; return null }
      return data as T
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function listConfigs(page = 1, pageSize = 10, search = ''): Promise<ConfigListResult> {
    loading.value = true; error.value = null
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
      if (search) params.set('search', search)
      const resp = await fetch(`/api/configs?${params}`)
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '加载失败', code: data?.code || 'LOAD_ERROR' }
        return { items: [], total: 0, page, pageSize, totalPages: 0 }
      }
      const data = await resp.json()
      const items = Array.isArray(data) ? data : (data.items || [])
      return {
        items: items.map(mapConfig),
        total: data.total ?? items.length,
        page: data.page ?? page,
        pageSize: data.page_size ?? pageSize,
        totalPages: data.total_pages ?? 1,
      }
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return { items: [], total: 0, page, pageSize, totalPages: 0 }
    } finally { loading.value = false }
  }

  async function saveConfig(state: WizardState, configId?: string | null): Promise<string | null> {
    const body = {
      config_id: configId || null,
      state: stateToSnakeCase(state),
    }
    const data = await post<{ id: string }>('/api/configs', body)
    return data?.id ?? null
  }

  async function deleteConfig(id: string): Promise<boolean> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${id}`, { method: 'DELETE' })
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '删除失败', code: data?.code || 'DELETE_ERROR' }
        return false
      }
      return true
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return false
    } finally { loading.value = false }
  }

  async function loadConfigState(id: string): Promise<Record<string, unknown> | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${id}`)
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '加载失败', code: data?.code || 'LOAD_ERROR' }
        return null
      }
      return await resp.json()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function downloadConfigYaml(id: string): Promise<void> {
    try {
      const resp = await fetch(`/api/configs/${id}/yaml`)
      if (!resp.ok) return
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      try {
        const a = document.createElement('a')
        a.href = url
        a.download = `pipeline_${id}.yaml`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } finally {
        URL.revokeObjectURL(url)
      }
    } catch { /* 下载失败静默忽略 */ }
  }

  async function executeConfig(id: string, files: Record<string, string>): Promise<Blob | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files }),
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

  return { loading, error, listConfigs, saveConfig, deleteConfig, loadConfigState, downloadConfigYaml, executeConfig }
}

export function useConfigVersionApi() {
  const loading = ref(false)
  const error = ref<{ message: string; code: string } | null>(null)

  async function listVersions(configId: string) {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${configId}/versions`)
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '加载版本列表失败', code: data?.code || 'VERSIONS_ERROR' }
        return []
      }
      return await resp.json()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return []
    } finally { loading.value = false }
  }

  async function getVersion(configId: string, version: number) {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${configId}/versions/${version}`)
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '加载版本失败', code: data?.code || 'VERSION_ERROR' }
        return null
      }
      return await resp.json()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function diffVersions(configId: string, v1: number, v2: number) {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${configId}/diff?v1=${v1}&v2=${v2}`)
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '版本对比失败', code: data?.code || 'DIFF_ERROR' }
        return null
      }
      return await resp.json()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function rollback(configId: string, version: number) {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${configId}/versions/${version}/rollback`, { method: 'POST' })
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '回滚失败', code: data?.code || 'ROLLBACK_ERROR' }
        return null
      }
      return await resp.json()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  return { loading, error, listVersions, getVersion, diffVersions, rollback }
}
