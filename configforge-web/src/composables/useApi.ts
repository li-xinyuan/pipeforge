import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import router from '../router'

export class ApiError extends Error {
  code: string
  status: number
  data?: unknown
  constructor(message: string, code: string, status: number, data?: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.data = data
  }
}

/** Global error handler for ApiError */
export function handleApiError(error: ApiError): void {
  switch (error.status) {
    case 401:
      useAuthStore().clearAuth()
      router.push('/login')
      break
    case 403:
      window.alert('权限不足')
      break
    case 500:
      window.alert('服务器错误')
      break
    default:
      window.alert(error.message)
      break
  }
}

export function useApi() {
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  function extractErrorMessage(data: Record<string, unknown> | null, fallback: string): string {
    if (!data) return fallback
    return (data.error || data.detail || fallback) as string
  }

  function extractErrorCode(data: Record<string, unknown> | null, fallback: string): string {
    if (!data) return fallback
    return (data.code || fallback) as string
  }

  /** Build request headers with optional Authorization */
  function buildHeaders(isFormData: boolean): Record<string, string> {
    const headers: Record<string, string> = {}
    if (!isFormData) headers['Content-Type'] = 'application/json'
    const auth = useAuthStore()
    if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`
    return headers
  }

  /** Like request() but throws ApiError on failure instead of returning null */
  async function requestOrThrow<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: { signal?: AbortSignal },
  ): Promise<T> {
    loading.value = true
    error.value = null
    try {
      const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
      const opts: RequestInit = {
        method,
        headers: buildHeaders(isFormData),
        signal: options?.signal,
      }
      if (body !== undefined) opts.body = isFormData ? body : JSON.stringify(body)
      const resp = await fetch(url, opts)

      // Handle 401 — redirect to login
      if (resp.status === 401) {
        const auth = useAuthStore()
        if (auth.isAuthenticated) {
          auth.clearAuth()
          router.push('/login')
        }
        throw new ApiError('登录已过期，请重新登录', 'AUTH_FAILED', 401)
      }

      // Handle 403 — permission denied
      if (resp.status === 403) {
        throw new ApiError('权限不足', 'FORBIDDEN', 403)
      }

      const contentType = resp.headers.get('content-type') || ''

      // Explicitly binary content-type — return as blob
      if (contentType.includes('application/octet-stream') || contentType.includes('application/vnd.')) {
        if (!resp.ok) {
          throw new ApiError(`请求失败 (${resp.status})`, 'API_ERROR', resp.status)
        }
        return await resp.blob() as unknown as T
      }

      // Default: read body once as ArrayBuffer, then try JSON or fallback to Blob
      const buffer = await resp.arrayBuffer()

      let data: Record<string, unknown> | null = null
      try { data = JSON.parse(new TextDecoder().decode(buffer)) } catch { /* not JSON */ }

      if (!resp.ok) {
        throw new ApiError(
          extractErrorMessage(data, `请求失败 (${resp.status})`),
          extractErrorCode(data, 'API_ERROR'),
          resp.status,
          data,
        )
      }

      // If JSON parsing succeeded, return parsed data
      if (data !== null) return data as T

      // JSON parsing failed but response is ok — return as blob
      return new Blob([buffer]) as unknown as T
    } catch (e) {
      if (e instanceof ApiError) {
        error.value = e
        throw e
      }
      if (e instanceof DOMException && e.name === 'AbortError') {
        const apiErr = new ApiError('请求超时，请重试', 'TIMEOUT', 0)
        error.value = apiErr
        throw apiErr
      }
      if (e instanceof TypeError && e.message.includes('fetch')) {
        const apiErr = new ApiError('网络连接失败，请检查后端服务是否运行', 'NETWORK_ERROR', 0)
        error.value = apiErr
        throw apiErr
      }
      const msg = e instanceof Error ? e.message : '网络请求失败'
      const apiErr = new ApiError(msg, 'NETWORK_ERROR', 0)
      error.value = apiErr
      throw apiErr
    } finally {
      loading.value = false
    }
  }

  /** @deprecated Use requestOrThrow + try/catch instead */
  async function request<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: { signal?: AbortSignal },
  ): Promise<T | null> {
    try {
      return await requestOrThrow<T>(method, url, body, options)
    } catch {
      return null
    }
  }

  // ── Schedules API ──
  async function getSchedules() {
    return request<ScheduleItem[]>('GET', '/api/schedules')
  }

  async function getConfigs(params?: string) {
    const url = params ? `/api/configs?${params}` : '/api/configs'
    return request<{ items: ConfigItem[] }>('GET', url)
  }

  async function createSchedule(body: { config_id: string; cron_expression: string; description: string }) {
    return request<ScheduleItem>('POST', '/api/schedules', body)
  }

  async function updateSchedule(id: string, body: { cron_expression: string; description: string }) {
    return request<ScheduleItem>('PUT', `/api/schedules/${id}`, body)
  }

  async function toggleSchedule(id: string) {
    return request<unknown>('POST', `/api/schedules/${id}/toggle`)
  }

  async function deleteSchedule(id: string) {
    return request<unknown>('DELETE', `/api/schedules/${id}`)
  }

  // ── Executions API ──
  async function getExecutions(page: number, pageSize: number) {
    return request<{ items: ExecutionItem[]; total: number }>('GET', `/api/executions?page=${page}&page_size=${pageSize}`)
  }

  async function deleteExecution(id: string) {
    return request<unknown>('DELETE', `/api/executions/${id}`)
  }

  // ── Config Versions API ──
  async function getConfigVersions(configId: string) {
    return request<VersionMeta[]>('GET', `/api/configs/${configId}/versions`)
  }

  async function getConfigVersionDetail(configId: string, version: number) {
    return request<Record<string, unknown>>('GET', `/api/configs/${configId}/versions/${version}`)
  }

  async function getConfigDiff(configId: string, v1: number, v2: number) {
    return request<DiffResult>('GET', `/api/configs/${configId}/diff?v1=${v1}&v2=${v2}`)
  }

  async function rollbackConfig(configId: string, version: number) {
    return request<unknown>('POST', `/api/configs/${configId}/versions/${version}/rollback`)
  }

  // ── AI Settings API ──
  async function getAiSettings() {
    return request<AiSettings>('GET', '/api/ai/settings')
  }

  // ── File Upload API ──
  async function uploadFile(formData: FormData) {
    return request<{ file_id: string; original_name: string }>('POST', '/api/files/upload', formData)
  }

  // ── Wizard API Preview ──
  async function apiPreview(body: Record<string, unknown>) {
    return request<{ columns: string[]; rows: string[][] }>('POST', '/api/wizard/infer-api-input/api_preview', body)
  }

  async function apiTest(body: Record<string, unknown>) {
    return request<unknown>('POST', '/api/wizard/infer-api-input/api_test', body)
  }

  return {
    loading,
    error,
    request,
    requestOrThrow,
    getSchedules,
    getConfigs,
    createSchedule,
    updateSchedule,
    toggleSchedule,
    deleteSchedule,
    getExecutions,
    deleteExecution,
    getConfigVersions,
    getConfigVersionDetail,
    getConfigDiff,
    rollbackConfig,
    getAiSettings,
    uploadFile,
    apiPreview,
    apiTest,
  }
}

// ── Shared type definitions ──
export interface ScheduleItem {
  id: string
  config_id: string
  config_name: string
  cron_expression: string
  enabled: boolean
  description: string
  created_at: string
  last_run_at: string | null
  last_run_status: string | null
  next_run_time: string | null
}

export interface ConfigItem {
  id: string
  scene_name: string
  inputs?: Record<string, unknown>[]
  [key: string]: unknown
}

export interface ExecutionItem {
  id: string
  config_id: string
  config_version: number | null
  scene_name: string
  status: 'success' | 'failed'
  started_at: string
  finished_at: string
  duration_ms: number
  inputs_summary: Array<{ name: string; plugin: string }>
  processors_summary: Array<{ plugin: string; name: string }>
  output_type: string
  checks_summary: Array<{ type: string; passed: boolean; message: string }>
  error_message: string | null
  output_file_name: string | null
  diagnosis?: {
    cause: string
    suggestions: string[]
    severity: 'error' | 'warning'
    step?: number
  } | null
}

export interface VersionMeta {
  version: number
  scene_version: string
  change_summary: string
  created_at: string
  input_count: number
  processor_count: number
  output_type: string
}

export interface DiffResult {
  v1?: number
  v2?: number
  added?: Array<{ path: string; value: unknown }>
  removed?: Array<{ path: string; value: unknown }>
  modified?: Array<{ path: string; old: unknown; new: unknown }>
}

export interface AiSettings {
  enabled: boolean
  api_key?: string
  provider?: string
  model?: string
}
