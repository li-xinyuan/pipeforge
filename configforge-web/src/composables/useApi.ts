import { ref } from 'vue'

export interface ApiError {
  message: string
  code: string
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

  async function request<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: { signal?: AbortSignal },
  ): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      const opts: RequestInit = {
        method,
        headers: { 'Content-Type': 'application/json' },
        signal: options?.signal,
      }
      if (body !== undefined) opts.body = JSON.stringify(body)
      const resp = await fetch(url, opts)
      const contentType = resp.headers.get('content-type') || ''

      // Explicitly binary content-type — return as blob
      if (contentType.includes('application/octet-stream') || contentType.includes('application/vnd.')) {
        if (!resp.ok) {
          error.value = { message: `请求失败 (${resp.status})`, code: 'API_ERROR' }
          return null
        }
        return await resp.blob() as unknown as T
      }

      // Default: read body once as ArrayBuffer, then try JSON or fallback to Blob
      const buffer = await resp.arrayBuffer()

      let data: Record<string, unknown> | null = null
      try { data = JSON.parse(new TextDecoder().decode(buffer)) } catch { /* not JSON */ }

      if (!resp.ok) {
        error.value = {
          message: extractErrorMessage(data, `请求失败 (${resp.status})`),
          code: extractErrorCode(data, 'API_ERROR'),
        }
        return null
      }

      // If JSON parsing succeeded, return parsed data
      if (data !== null) return data as T

      // JSON parsing failed but response is ok — return as blob
      return new Blob([buffer]) as unknown as T
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        error.value = { message: '请求超时，请重试', code: 'TIMEOUT' }
      } else if (e instanceof TypeError && e.message.includes('fetch')) {
        error.value = { message: '网络连接失败，请检查后端服务是否运行', code: 'NETWORK_ERROR' }
      } else {
        const msg = e instanceof Error ? e.message : '网络请求失败'
        error.value = { message: msg, code: 'NETWORK_ERROR' }
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { loading, error, request }
}
