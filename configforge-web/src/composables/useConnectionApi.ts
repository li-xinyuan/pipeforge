import { ref, watch } from 'vue'
import type { DbConnectionSummary } from '../types/wizard'
import { useApi } from './useApi'

export function useConnectionApi() {
  const { loading, error: apiError, request } = useApi()
  const connectionError = ref<string | null>(null)

  // Sync API error to connectionError
  watch(apiError, (err) => {
    connectionError.value = err?.message ?? null
  })

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
    const result = await request<{ ok: boolean; error?: string }>('POST', `/api/connections/${id}/test`)
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
    connecting: loading,
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
