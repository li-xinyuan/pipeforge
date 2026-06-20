import type { SavedConfig, WizardState } from '../types/wizard'
import { stateToSnakeCase } from '../utils/serialization'
import { useApi } from './useApi'

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
  const { loading, error, request } = useApi()

  async function listConfigs(page = 1, pageSize = 10, search = ''): Promise<ConfigListResult> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (search) params.set('search', search)
    const data = await request<{ items: Record<string, unknown>[]; total: number; page: number; page_size: number; total_pages: number } | Record<string, unknown>[]>(
      'GET', `/api/configs?${params}`,
    )
    if (!data) return { items: [], total: 0, page, pageSize, totalPages: 0 }
    const items = Array.isArray(data) ? data : (data.items || [])
    return {
      items: items.map(mapConfig),
      total: Array.isArray(data) ? items.length : (data.total ?? items.length),
      page: Array.isArray(data) ? page : (data.page ?? page),
      pageSize: Array.isArray(data) ? pageSize : (data.page_size ?? pageSize),
      totalPages: Array.isArray(data) ? 1 : (data.total_pages ?? 1),
    }
  }

  async function saveConfig(state: WizardState, configId?: string | null): Promise<string | null> {
    const body = { config_id: configId || null, state: stateToSnakeCase(state) }
    const data = await request<{ id: string }>('POST', '/api/configs', body)
    return data?.id ?? null
  }

  async function deleteConfig(id: string): Promise<boolean> {
    const result = await request<unknown>('DELETE', `/api/configs/${id}`)
    return result !== null
  }

  async function loadConfigState(id: string): Promise<Record<string, unknown> | null> {
    return request<Record<string, unknown>>('GET', `/api/configs/${id}`)
  }

  async function downloadConfigYaml(id: string): Promise<void> {
    const blob = await request<Blob>('GET', `/api/configs/${id}/yaml`)
    if (!blob || !(blob instanceof Blob)) return
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
  }

  async function executeConfig(id: string, files: Record<string, string>): Promise<Blob | null> {
    const result = await request<Blob>('POST', `/api/configs/${id}/execute`, { files })

    // request returns null when API responds with non-200
    if (result === null) {
      const execError: ExecuteError = { message: error.value?.message || '执行失败' }
      // Try to extract diagnosis from the error detail
      const errDetail = error.value?.detail as Record<string, unknown> | undefined
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

    return result instanceof Blob ? result : null
  }

  return { loading, error, listConfigs, saveConfig, deleteConfig, loadConfigState, downloadConfigYaml, executeConfig }
}

export function useConfigVersionApi() {
  const { loading, error, request } = useApi()

  async function listVersions(configId: string) {
    const data = await request<unknown[]>('GET', `/api/configs/${configId}/versions`)
    return data || []
  }

  async function getVersion(configId: string, version: number) {
    return request<Record<string, unknown>>('GET', `/api/configs/${configId}/versions/${version}`)
  }

  async function diffVersions(configId: string, v1: number, v2: number) {
    return request<Record<string, unknown>>('GET', `/api/configs/${configId}/diff?v1=${v1}&v2=${v2}`)
  }

  async function rollback(configId: string, version: number) {
    return request<Record<string, unknown>>('POST', `/api/configs/${configId}/versions/${version}/rollback`)
  }

  return { loading, error, listVersions, getVersion, diffVersions, rollback }
}
