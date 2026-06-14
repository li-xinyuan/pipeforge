import { ref } from 'vue'
import type { DbConnectionSummary, WizardState } from '../types/wizard'
import { stateToSnakeCase } from '../utils/serialization'

export function useWizardApi() {
  const loading = ref(false)
  const error = ref<{ message: string; code: string } | null>(null)

  async function post<T>(url: string, body: unknown): Promise<T | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      let data: Record<string, unknown> | null = null
      try { data = await resp.json() } catch { /* ignore parse error */ }
      if (!resp.ok) {
        if (data) {
          error.value = { message: (data.error || data.detail || `请求失败 (${resp.status})`) as string, code: (data.code || 'API_ERROR') as string }
        } else {
          error.value = { message: `服务器错误 (${resp.status})`, code: 'SERVER_ERROR' }
        }
        return null
      }
      return data as T
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function initScene(fileIds: string[]) { return post<Record<string, unknown>>('/api/wizard/init-scene', { file_ids: fileIds }) }

  async function fetchPreview(fileId: string, sheet?: string) {
    return post<{ sheets: string[]; columns: string[]; rows: string[][] }>('/api/preview/file', { file_id: fileId, sheet })
  }

  async function generateYaml(state: WizardState) {
    return post<{ yaml: string }>('/api/wizard/generate', { state: stateToSnakeCase(state) })
  }

  async function executeSql(sql: string, tableMapping: Record<string, string>) {
    return post<{
      columns: string[]
      rows: string[][]
      total_source_rows: number
      sample_rows_loaded: number
      is_sampled: boolean
    }>('/api/preview/sql', { sql, table_mapping: tableMapping })
  }

  async function dryRun(state: WizardState) {
    return post<{
      tables: { table_name: string; columns: string[]; rows: string[][]; total_rows: number }[]
      inputs: Record<string, unknown>
      processors: Record<string, unknown>[]
    }>('/api/wizard/dry-run', { state: stateToSnakeCase(state) })
  }

  async function executePipeline(state: WizardState): Promise<Blob | { status: string; message: string; exec_id: string } | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch('/api/wizard/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: stateToSnakeCase(state) }),
      })
      if (!resp.ok) {
        let data: Record<string, unknown> | null = null
        try { data = await resp.json() } catch { /* ignore parse error */ }
        error.value = { message: (data?.error || data?.detail || `请求失败 (${resp.status})`) as string, code: (data?.code || 'EXECUTE_ERROR') as string }
        return null
      }
      const contentType = resp.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        return await resp.json()
      }
      return await resp.blob()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  return { loading, error, initScene, fetchPreview, generateYaml, executeSql, dryRun, executePipeline }
}

export function useAiApi() {
  const suggesting = ref(false)
  const aiError = ref<string | null>(null)

  async function askSuggestion(category: string, context: Record<string, unknown>): Promise<string | null> {
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

  async function updateAiSettings(body: Record<string, unknown>) {
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

  async function askOrchestrate(context: Record<string, unknown>): Promise<{
    steps: Array<
      | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string }
      | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string }
    >
    explanation: string
    raw?: string
    parse_error?: boolean
  } | null> {
    suggesting.value = true
    aiError.value = null
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 120000)
    try {
      const resp = await fetch('/api/ai/orchestrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context }),
        signal: controller.signal,
      })
      const data = await resp.json()
      if (resp.ok) return data
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

  return { suggesting, aiError, askSuggestion, askOrchestrate, getAiSettings, updateAiSettings, testAiConnection }
}

export function useConnectionApi() {
  const connecting = ref(false)
  const connectionError = ref<string | null>(null)

  async function request<T>(method: string, url: string, body?: unknown): Promise<T | null> {
    try {
      const opts: RequestInit = {
        method,
        headers: { 'Content-Type': 'application/json' },
      }
      if (body) opts.body = JSON.stringify(body)
      const res = await fetch(url, opts)
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }))
        connectionError.value = err.error || err.detail || 'Request failed'
        return null
      }
      return await res.json()
    } catch (e: unknown) {
      connectionError.value = e instanceof Error ? e.message : 'Network error'
      return null
    }
  }

  async function fetchConnections(): Promise<DbConnectionSummary[]> {
    const result = await request<DbConnectionSummary[]>('GET', '/api/connections')
    return result || []
  }

  async function createConnection(data: Record<string, unknown>): Promise<DbConnectionSummary | null> {
    return request<DbConnectionSummary>('POST', '/api/connections', data)
  }

  async function updateConnection(id: string, data: Record<string, unknown>): Promise<DbConnectionSummary | null> {
    return request<DbConnectionSummary>('PUT', `/api/connections/${id}`, data)
  }

  async function deleteConnection(id: string): Promise<boolean> {
    const result = await request<{ ok: boolean }>('DELETE', `/api/connections/${id}`)
    return result?.ok ?? false
  }

  async function testConnection(id: string): Promise<{ ok: boolean; error?: string }> {
    connecting.value = true
    const result = await request<{ ok: boolean; error?: string }>('POST', `/api/connections/${id}/test`)
    connecting.value = false
    return result || { ok: false, error: 'Request failed' }
  }

  async function fetchTables(id: string): Promise<string[]> {
    const result = await request<{ tables: string[] }>('GET', `/api/connections/${id}/tables`)
    return result?.tables || []
  }

  async function fetchColumns(id: string, table: string): Promise<{ name: string; type: string }[]> {
    const result = await request<{ columns: { name: string; type: string }[] }>(
      'GET', `/api/connections/${id}/tables/${encodeURIComponent(table)}/columns`
    )
    return result?.columns || []
  }

  return {
    connecting,
    connectionError,
    fetchConnections,
    createConnection,
    updateConnection,
    deleteConnection,
    testConnection,
    fetchTables,
    fetchColumns,
  }
}
