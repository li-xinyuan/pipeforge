import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useApi, ApiError, handleApiError } from '../../src/composables/useApi'
import { useAuthStore } from '../../src/stores/auth'

const mockClearAuth = vi.fn()
const mockAuthStore = {
  token: 'test-token',
  isAuthenticated: true,
  clearAuth: mockClearAuth,
}

// Mock the auth store
vi.mock('../../src/stores/auth', () => ({
  useAuthStore: vi.fn(() => mockAuthStore),
}))

// Mock the router
vi.mock('../../src/router', () => ({
  default: { push: vi.fn() },
}))

describe('ApiError', () => {
  it('stores code, status, and data', () => {
    const err = new ApiError('msg', 'CODE', 400, { foo: 'bar' })
    expect(err.message).toBe('msg')
    expect(err.code).toBe('CODE')
    expect(err.status).toBe(400)
    expect(err.data).toEqual({ foo: 'bar' })
  })

  it('is an instance of Error', () => {
    const err = new ApiError('msg', 'CODE', 500)
    expect(err).toBeInstanceOf(Error)
    expect(err).toBeInstanceOf(ApiError)
  })
})

describe('handleApiError', () => {
  beforeEach(() => {
    mockClearAuth.mockClear()
  })

  it('clears auth and redirects on 401', () => {
    const err = new ApiError('Unauthorized', 'AUTH_FAILED', 401)
    handleApiError(err)
    expect(mockClearAuth).toHaveBeenCalled()
  })

  it('alerts on 403', () => {
    const spy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const err = new ApiError('Forbidden', 'FORBIDDEN', 403)
    handleApiError(err)
    expect(spy).toHaveBeenCalledWith('权限不足')
    spy.mockRestore()
  })

  it('alerts on 500', () => {
    const spy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const err = new ApiError('Server Error', 'SERVER_ERROR', 500)
    handleApiError(err)
    expect(spy).toHaveBeenCalledWith('服务器错误')
    spy.mockRestore()
  })

  it('alerts with error message for other statuses', () => {
    const spy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const err = new ApiError('Custom error', 'CUSTOM', 422)
    handleApiError(err)
    expect(spy).toHaveBeenCalledWith('Custom error')
    spy.mockRestore()
  })
})

describe('useApi', () => {
  let api: ReturnType<typeof useApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    api = useApi()
  })

  describe('requestOrThrow', () => {
    it('returns parsed JSON on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ id: '1', name: 'test' }), { status: 200 })
      )
      const result = await api.requestOrThrow<{ id: string; name: string }>('GET', '/api/test')
      expect(result).toEqual({ id: '1', name: 'test' })
      expect(api.loading.value).toBe(false)
      expect(api.error.value).toBeNull()
    })

    it('sets Content-Type to application/json for non-FormData body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      await api.requestOrThrow('POST', '/api/test', { key: 'value' })
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect((opts.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    })

    it('does not set Content-Type for FormData body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      const formData = new FormData()
      formData.append('file', new Blob(['data']), 'test.txt')
      await api.requestOrThrow('POST', '/api/upload', formData)
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect((opts.headers as Record<string, string>)['Content-Type']).toBeUndefined()
    })

    it('sets Authorization header when token exists', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      await api.requestOrThrow('GET', '/api/test')
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect((opts.headers as Record<string, string>)['Authorization']).toBe('Bearer test-token')
    })

    it('throws ApiError with AUTH_FAILED on 401', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('', { status: 401 })
      )
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('登录已过期，请重新登录')
      expect(api.error.value?.code).toBe('AUTH_FAILED')
      expect(api.error.value?.status).toBe(401)
    })

    it('throws ApiError with FORBIDDEN on 403', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('', { status: 403 })
      )
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('权限不足')
      expect(api.error.value?.code).toBe('FORBIDDEN')
    })

    it('throws ApiError with server error message on non-ok response', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found', code: 'NOT_FOUND' }), { status: 404 })
      )
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('Not found')
      expect(api.error.value?.code).toBe('NOT_FOUND')
      expect(api.error.value?.status).toBe(404)
    })

    it('uses fallback message when response body has no error field', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 422 })
      )
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('请求失败 (422)')
    })

    it('returns blob for application/octet-stream content type', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(new Blob(['binary']), {
          status: 200,
          headers: { 'Content-Type': 'application/octet-stream' },
        })
      )
      const result = await api.requestOrThrow<Blob>('GET', '/api/download')
      expect(result).toBeTruthy()
    })

    it('handles abort signal (AbortError)', async () => {
      const abortErr = new DOMException('The operation was aborted', 'AbortError')
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(abortErr)
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('请求超时，请重试')
      expect(api.error.value?.code).toBe('TIMEOUT')
    })

    it('handles network error (fetch TypeError)', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('fetch failed'))
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('网络连接失败，请检查后端服务是否运行')
      expect(api.error.value?.code).toBe('NETWORK_ERROR')
    })

    it('handles generic error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Something broke'))
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow('Something broke')
      expect(api.error.value?.code).toBe('NETWORK_ERROR')
    })

    it('manages loading state', async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve(new Response('{}', { status: 200 })), 50))
      )
      const promise = api.requestOrThrow('GET', '/api/test')
      expect(api.loading.value).toBe(true)
      await promise
      expect(api.loading.value).toBe(false)
    })

    it('resets loading state even on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('fail'))
      await expect(api.requestOrThrow('GET', '/api/test')).rejects.toThrow()
      expect(api.loading.value).toBe(false)
    })
  })

  describe('request (deprecated)', () => {
    it('returns data on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
      const result = await api.request<{ ok: boolean }>('GET', '/api/test')
      expect(result).toEqual({ ok: true })
    })

    it('returns null on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'fail' }), { status: 500 })
      )
      const result = await api.request('GET', '/api/test')
      expect(result).toBeNull()
    })
  })

  describe('convenience methods', () => {
    it('getSchedules calls GET /api/schedules', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      )
      await api.getSchedules()
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(url).toBe('/api/schedules')
    })

    it('getConfigs calls GET /api/configs with optional params', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [] }), { status: 200 })
      )
      await api.getConfigs('page=1')
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(url).toBe('/api/configs?page=1')
    })

    it('createSchedule calls POST /api/schedules', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 's1' }), { status: 200 })
      )
      await api.createSchedule({ config_id: 'c1', cron_expression: '0 * * * *', description: 'test' })
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('POST')
    })

    it('updateSchedule calls PUT /api/schedules/:id', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 's1' }), { status: 200 })
      )
      await api.updateSchedule('s1', { cron_expression: '0 0 * * *', description: 'updated' })
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('PUT')
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/schedules/s1')
    })

    it('toggleSchedule calls POST /api/schedules/:id/toggle', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      await api.toggleSchedule('s1')
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/schedules/s1/toggle')
    })

    it('deleteSchedule calls DELETE /api/schedules/:id', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      await api.deleteSchedule('s1')
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('DELETE')
    })

    it('getExecutions calls GET /api/executions with pagination', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 })
      )
      await api.getExecutions(2, 20)
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(url).toBe('/api/executions?page=2&page_size=20')
    })

    it('getConfigVersions calls GET /api/configs/:id/versions', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      )
      await api.getConfigVersions('c1')
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(url).toBe('/api/configs/c1/versions')
    })

    it('getConfigDiff calls GET /api/configs/:id/diff with v1 and v2', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      )
      await api.getConfigDiff('c1', 1, 2)
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(url).toBe('/api/configs/c1/versions/diff?v1=1&v2=2')
    })

    it('rollbackConfig calls POST /api/configs/:id/versions/:v/rollback', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      await api.rollbackConfig('c1', 3)
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/configs/c1/versions/3/rollback')
    })

    it('uploadFile sends FormData via POST', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ file_id: 'f1', original_name: 'a.xlsx' }), { status: 200 })
      )
      const fd = new FormData()
      fd.append('file', new Blob(['data']), 'a.xlsx')
      await api.uploadFile(fd)
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('POST')
      expect(opts.body).toBe(fd)
    })
  })
})
