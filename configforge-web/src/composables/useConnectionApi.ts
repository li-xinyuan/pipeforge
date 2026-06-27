import { ref, watch } from 'vue'
import type { DbConnectionSummary } from '../types/wizard'
import { useApi, ApiError, handleApiError } from './useApi'

export function useConnectionApi() {
  const { loading, error: apiError, requestOrThrow } = useApi()
  const connectionError = ref<string | null>(null)

  // Sync API error to connectionError
  watch(apiError, (err) => {
    connectionError.value = err?.message ?? null
  })

  async function fetchConnections(): Promise<DbConnectionSummary[]> {
    try {
      const result = await requestOrThrow<Record<string, unknown>[]>('GET', '/api/connections')
      // Backend returns db_type (snake_case); normalize to dbType for frontend
      return (result || []).map((c) => ({ ...c, dbType: c.dbType ?? c.db_type } as unknown as DbConnectionSummary))
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    }
  }

  async function createConnection(data: Record<string, unknown>): Promise<DbConnectionSummary | null> {
    try {
      const result = await requestOrThrow<Record<string, unknown>>('POST', '/api/connections', data)
      if (!result) return null
      return { ...result, dbType: result.dbType ?? result.db_type } as unknown as DbConnectionSummary
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function updateConnection(id: string, data: Record<string, unknown>): Promise<DbConnectionSummary | null> {
    try {
      const result = await requestOrThrow<Record<string, unknown>>('PUT', `/api/connections/${id}`, data)
      if (!result) return null
      return { ...result, dbType: result.dbType ?? result.db_type } as unknown as DbConnectionSummary
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function deleteConnection(id: string): Promise<boolean> {
    try {
      const result = await requestOrThrow<{ ok: boolean }>('DELETE', `/api/connections/${id}`)
      return result?.ok ?? false
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return false
    }
  }

  async function testConnection(id: string): Promise<{ ok: boolean; error?: string }> {
    try {
      const result = await requestOrThrow<{ ok: boolean; error?: string }>('POST', `/api/connections/${id}/test`)
      return result || { ok: false, error: 'Request failed' }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return { ok: false, error: 'Request failed' }
    }
  }

  async function fetchTables(id: string): Promise<string[]> {
    try {
      const result = await requestOrThrow<{ tables: string[] }>('GET', `/api/connections/${id}/tables`)
      return result?.tables || []
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    }
  }

  async function fetchColumns(id: string, table: string): Promise<{ name: string; type: string }[]> {
    try {
      const result = await requestOrThrow<{ columns: { name: string; type: string }[] }>(
        'GET', `/api/connections/${id}/tables/${encodeURIComponent(table)}/columns`
      )
      return result?.columns || []
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    }
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
