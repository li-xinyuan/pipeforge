import type { SavedConfig, WizardState } from '../types/wizard'
import { stateToSnakeCase } from '../utils/serialization'
import { useApi, ApiError, handleApiError } from './useApi'

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

export interface ExecuteError {
  message: string
  diagnosis?: {
    cause: string
    suggestions: string[]
    severity: 'error' | 'warning'
    step?: number
  } | null
}

export function useConfigApi() {
  const { loading, error, requestOrThrow } = useApi()

  async function listConfigs(page = 1, pageSize = 10, search = ''): Promise<ConfigListResult> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (search) params.set('search', search)
    try {
      const data = await requestOrThrow<{ configs?: Record<string, unknown>[]; items?: Record<string, unknown>[]; total: number; page: number; page_size: number; total_pages?: number } | Record<string, unknown>[]>(
        'GET', `/api/configs?${params}`,
      )
      const items = Array.isArray(data) ? data : (data.configs || data.items || [])
      return {
        items: items.map(mapConfig),
        total: Array.isArray(data) ? items.length : (data.total ?? items.length),
        page: Array.isArray(data) ? page : (data.page ?? page),
        pageSize: Array.isArray(data) ? pageSize : (data.page_size ?? pageSize),
        totalPages: Array.isArray(data) ? 1 : (data.total_pages ?? 1),
      }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return { items: [], total: 0, page, pageSize, totalPages: 0 }
    }
  }

  async function saveConfig(state: WizardState, configId?: string | null): Promise<string | null> {
    const body = { config_id: configId || null, state: stateToSnakeCase(state) }
    try {
      const data = await requestOrThrow<{ id: string }>('POST', '/api/configs', body)
      return data.id
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function deleteConfig(id: string): Promise<boolean> {
    try {
      await requestOrThrow<unknown>('DELETE', `/api/configs/${id}`)
      return true
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return false
    }
  }

  async function loadConfigState(id: string): Promise<Record<string, unknown> | null> {
    try {
      return await requestOrThrow<Record<string, unknown>>('GET', `/api/configs/${id}`)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function downloadConfigYaml(id: string): Promise<void> {
    try {
      const blob = await requestOrThrow<Blob>('GET', `/api/configs/${id}/yaml`)
      if (!(blob instanceof Blob)) return
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
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
    }
  }

  async function exportConfig(id: string, format: 'yaml' | 'json' = 'yaml'): Promise<void> {
    try {
      const blob = await requestOrThrow<Blob>('GET', `/api/configs/${id}/export?format=${format}`)
      if (!(blob instanceof Blob)) return
      const url = URL.createObjectURL(blob)
      try {
        const a = document.createElement('a')
        a.href = url
        a.download = `config_${id}.${format}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } finally {
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
    }
  }

  async function importConfig(file: File): Promise<{ id: string; sceneName: string } | null> {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const data = await requestOrThrow<{ id: string; scene_name: string }>('POST', '/api/configs/import', formData)
      return { id: data.id, sceneName: data.scene_name }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function executeConfig(id: string, files: Record<string, string>): Promise<Blob | null> {
    try {
      const result = await requestOrThrow<Blob>('POST', `/api/configs/${id}/execute`, { files })
      return result instanceof Blob ? result : null
    } catch (e) {
      if (e instanceof ApiError) {
        const execError: ExecuteError = { message: e.message }
        // Try to extract diagnosis from the error detail
        const errDetail = (e as ApiError & { detail?: unknown }).detail as Record<string, unknown> | undefined
        if (errDetail && typeof errDetail === 'object' && 'diagnosis' in errDetail) {
          const d = errDetail.diagnosis as Record<string, unknown>
          if (d.cause && d.severity) {
            execError.diagnosis = {
              cause: d.cause as string,
              suggestions: (d.suggestions as string[]) || [],
              severity: d.severity as 'error' | 'warning',
              step: d.step as number | undefined,
            }
          }
        }
        throw execError
      }
      throw e
    }
  }

  return { loading, error, listConfigs, saveConfig, deleteConfig, loadConfigState, downloadConfigYaml, exportConfig, importConfig, executeConfig }
}

export function useConfigVersionApi() {
  const { loading, error, requestOrThrow } = useApi()

  async function listVersions(configId: string) {
    try {
      const data = await requestOrThrow<unknown[]>('GET', `/api/configs/${configId}/versions`)
      return data || []
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    }
  }

  async function getVersion(configId: string, version: number) {
    try {
      return await requestOrThrow<Record<string, unknown>>('GET', `/api/configs/${configId}/versions/${version}`)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function diffVersions(configId: string, v1: number, v2: number) {
    try {
      return await requestOrThrow<Record<string, unknown>>('GET', `/api/configs/${configId}/versions/diff?v1=${v1}&v2=${v2}`)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function rollback(configId: string, version: number) {
    try {
      return await requestOrThrow<Record<string, unknown>>('POST', `/api/configs/${configId}/versions/${version}/rollback`)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  return { loading, error, listVersions, getVersion, diffVersions, rollback }
}
