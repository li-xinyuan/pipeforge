import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useNotificationApi } from '../../src/composables/useNotificationApi'

// Mock the auth store
vi.mock('../../src/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    token: 'test-token',
    isAuthenticated: true,
    clearAuth: vi.fn(),
  })),
}))

// Mock the router
vi.mock('../../src/router', () => ({
  default: { push: vi.fn() },
}))

const mockConfig = {
  id: 'nc1',
  name: '钉钉通知',
  type: 'webhook',
  enabled: true,
  webhook_url: 'https://oapi.dingtalk.com/robot/send?access_token=xxx',
  webhook_provider: 'dingtalk',
  webhook_headers: {},
  email_to: [],
  email_subject_template: '',
  email_body_template: '',
  trigger_on_success: true,
  trigger_on_failure: true,
  config_ids: null,
}

const mockHistoryEntry = {
  id: 'h1',
  config_id: 'nc1',
  config_name: '钉钉通知',
  execution_id: 'exec1',
  pipeline_config_name: '月度报表',
  status: 'success',
  notify_success: true,
  provider: 'dingtalk',
  message: '执行成功',
  triggered_at: '2026-06-01T10:00:00Z',
}

describe('useNotificationApi', () => {
  let api: ReturnType<typeof useNotificationApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    api = useNotificationApi()
  })

  describe('listConfigs', () => {
    it('returns configs on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([mockConfig]), { status: 200 })
      )
      const result = await api.listConfigs()
      expect(result).toHaveLength(1)
      expect(result[0].id).toBe('nc1')
      expect(result[0].name).toBe('钉钉通知')
      expect(result[0].type).toBe('webhook')
      expect(result[0].webhook_provider).toBe('dingtalk')
    })

    it('returns empty array on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Server error' }), { status: 500 })
      )
      const result = await api.listConfigs()
      expect(result).toEqual([])
    })

    it('returns empty array on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.listConfigs()
      expect(result).toEqual([])
    })
  })

  describe('getConfig', () => {
    it('returns config on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockConfig), { status: 200 })
      )
      const result = await api.getConfig('nc1')
      expect(result).not.toBeNull()
      expect(result!.id).toBe('nc1')
      expect(result!.webhook_url).toBe('https://oapi.dingtalk.com/robot/send?access_token=xxx')
    })

    it('returns null on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.getConfig('missing')
      expect(result).toBeNull()
    })
  })

  describe('createConfig', () => {
    it('returns created config on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockConfig), { status: 200 })
      )
      const result = await api.createConfig({
        name: '钉钉通知',
        type: 'webhook',
        webhook_url: 'https://oapi.dingtalk.com/robot/send?access_token=xxx',
        webhook_provider: 'dingtalk',
      })
      expect(result).not.toBeNull()
      expect(result!.name).toBe('钉钉通知')
    })

    it('sends POST request with body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockConfig), { status: 200 })
      )
      await api.createConfig({ name: '新通知', type: 'email' })
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('POST')
      const body = JSON.parse(opts.body as string)
      expect(body.name).toBe('新通知')
      expect(body.type).toBe('email')
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Invalid data' }), { status: 400 })
      )
      const result = await api.createConfig({ name: '' })
      expect(result).toBeNull()
    })
  })

  describe('updateConfig', () => {
    it('returns updated config on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ...mockConfig, enabled: false }), { status: 200 })
      )
      const result = await api.updateConfig('nc1', { enabled: false })
      expect(result).not.toBeNull()
      expect(result!.enabled).toBe(false)
    })

    it('sends PUT request to correct URL', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockConfig), { status: 200 })
      )
      await api.updateConfig('nc1', { name: '更新通知' })
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/notifications/configs/nc1')
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('PUT')
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.updateConfig('missing', { name: 'x' })
      expect(result).toBeNull()
    })
  })

  describe('deleteConfig', () => {
    it('returns true when deletion succeeds with ok=true', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
      const ok = await api.deleteConfig('nc1')
      expect(ok).toBe(true)
    })

    it('returns false when ok is not true', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: false }), { status: 200 })
      )
      const ok = await api.deleteConfig('nc1')
      expect(ok).toBe(false)
    })

    it('returns false on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const ok = await api.deleteConfig('missing')
      expect(ok).toBe(false)
    })

    it('sends DELETE request to correct URL', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
      await api.deleteConfig('nc1')
      const url = fetchSpy.mock.calls[0][0]
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(url).toBe('/api/notifications/configs/nc1')
      expect(opts.method).toBe('DELETE')
    })
  })

  describe('testConfig', () => {
    it('returns ok result on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true, message: '发送成功', provider: 'dingtalk' }), { status: 200 })
      )
      const result = await api.testConfig('nc1')
      expect(result.ok).toBe(true)
      expect(result.message).toBe('发送成功')
      expect(result.provider).toBe('dingtalk')
    })

    it('returns not ok on API error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Webhook 失败' }), { status: 500 })
      )
      const result = await api.testConfig('nc1')
      expect(result.ok).toBe(false)
      expect(result.message).toBe('请求失败')
    })

    it('returns not ok on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.testConfig('nc1')
      expect(result.ok).toBe(false)
    })

    it('sends POST request to correct URL', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true, message: 'ok', provider: 'dingtalk' }), { status: 200 })
      )
      await api.testConfig('nc1')
      const url = fetchSpy.mock.calls[0][0]
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(url).toBe('/api/notifications/test/nc1')
      expect(opts.method).toBe('POST')
    })
  })

  describe('getHistory', () => {
    it('returns history entries on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([mockHistoryEntry]), { status: 200 })
      )
      const result = await api.getHistory()
      expect(result).toHaveLength(1)
      expect(result[0].id).toBe('h1')
      expect(result[0].config_name).toBe('钉钉通知')
      expect(result[0].provider).toBe('dingtalk')
    })

    it('passes limit parameter in URL', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      )
      await api.getHistory(100)
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/notifications/history?limit=100')
    })

    it('uses default limit of 50', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 })
      )
      await api.getHistory()
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/notifications/history?limit=50')
    })

    it('returns empty array on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Server error' }), { status: 500 })
      )
      const result = await api.getHistory()
      expect(result).toEqual([])
    })

    it('returns empty array on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.getHistory()
      expect(result).toEqual([])
    })
  })
})
