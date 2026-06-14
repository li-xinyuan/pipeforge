/**
 * Shared API request utilities.
 * Provides a common base for all composables to make HTTP requests
 * with consistent error handling.
 */

export interface ApiError {
  message: string
  code: string
}

export function useApi() {
  async function request<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: { headers?: Record<string, string> },
  ): Promise<{ data: T | null; error: ApiError | null }> {
    try {
      const opts: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      }
      if (body !== undefined) opts.body = JSON.stringify(body)
      const resp = await fetch(url, opts)
      const contentType = resp.headers.get('content-type') || ''

      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        return {
          data: null,
          error: {
            message: data?.error || data?.detail || `请求失败 (${resp.status})`,
            code: data?.code || 'API_ERROR',
          },
        }
      }

      if (contentType.includes('application/json')) {
        return { data: (await resp.json()) as T, error: null }
      }
      // For non-JSON responses (e.g., blobs)
      return { data: (await resp.blob()) as T, error: null }
    } catch {
      return {
        data: null,
        error: { message: 'Network error', code: 'NETWORK_ERROR' },
      }
    }
  }

  async function get<T>(url: string): Promise<{ data: T | null; error: ApiError | null }> {
    return request<T>('GET', url)
  }

  async function post<T>(url: string, body?: unknown): Promise<{ data: T | null; error: ApiError | null }> {
    return request<T>('POST', url, body)
  }

  async function put<T>(url: string, body?: unknown): Promise<{ data: T | null; error: ApiError | null }> {
    return request<T>('PUT', url, body)
  }

  async function del<T>(url: string): Promise<{ data: T | null; error: ApiError | null }> {
    return request<T>('DELETE', url)
  }

  return { request, get, post, put, del }
}
