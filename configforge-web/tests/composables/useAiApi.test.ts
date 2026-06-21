import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAiApi } from '../../src/composables/useAiApi'

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

describe('useAiApi', () => {
  let api: ReturnType<typeof useAiApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    api = useAiApi()
  })

  describe('askSuggestion', () => {
    it('returns content on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ content: 'SELECT * FROM users' }), { status: 200 })
      )
      const result = await api.askSuggestion('sql', { description: 'all users' })
      expect(result).toBe('SELECT * FROM users')
      expect(api.suggesting.value).toBe(false)
    })

    it('returns null when content is missing', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      )
      const result = await api.askSuggestion('sql', {})
      expect(result).toBeNull()
    })

    it('sets aiError on API error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'AI 服务不可用' }), { status: 503 })
      )
      const result = await api.askSuggestion('sql', {})
      expect(result).toBeNull()
      expect(api.aiError.value).toBe('AI 服务不可用')
    })

    it('sets aiError on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network down'))
      const result = await api.askSuggestion('sql', {})
      expect(result).toBeNull()
      expect(api.aiError.value).toBeTruthy()
    })

    it('manages suggesting flag during request', async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve(new Response('{}')), 50))
      )
      const promise = api.askSuggestion('sql', {})
      expect(api.suggesting.value).toBe(true)
      await promise
      expect(api.suggesting.value).toBe(false)
    })

    it('sends category and context in request body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ content: 'result' }), { status: 200 })
      )
      await api.askSuggestion('python', { code: 'print(1)' })
      const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string)
      expect(body.category).toBe('python')
      expect(body.context).toEqual({ code: 'print(1)' })
    })
  })

  describe('getAiSettings', () => {
    it('returns settings on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ enabled: true, provider: 'openai', model: 'gpt-4' }), { status: 200 })
      )
      const settings = await api.getAiSettings()
      expect(settings).toEqual({ enabled: true, provider: 'openai', model: 'gpt-4' })
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Server error' }), { status: 500 })
      )
      const settings = await api.getAiSettings()
      expect(settings).toBeNull()
    })
  })

  describe('updateAiSettings', () => {
    it('returns true on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      const ok = await api.updateAiSettings({ enabled: true, api_key: 'sk-xxx' })
      expect(ok).toBe(true)
    })

    it('sends PUT request with body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      await api.updateAiSettings({ enabled: false })
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('PUT')
      const body = JSON.parse(opts.body as string)
      expect(body.enabled).toBe(false)
    })

    it('returns false on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Invalid key' }), { status: 400 })
      )
      const ok = await api.updateAiSettings({ api_key: 'bad' })
      expect(ok).toBe(false)
    })
  })

  describe('testAiConnection', () => {
    it('returns ok with data on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true, latency_ms: 200 }), { status: 200 })
      )
      const result = await api.testAiConnection()
      expect(result.ok).toBe(true)
      expect(result.data?.latency_ms).toBe(200)
    })

    it('returns not ok on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Connection refused' }), { status: 500 })
      )
      const result = await api.testAiConnection()
      expect(result.ok).toBe(false)
      expect(result.data).toBeNull()
    })

    it('returns not ok on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.testAiConnection()
      expect(result.ok).toBe(false)
      expect(result.data).toBeNull()
    })
  })

  describe('askOrchestrate', () => {
    const orchestrateResponse = {
      steps: [
        { name: 'step1', plugin: 'sql' as const, input_tables: ['t1'], output_tables: ['t2'], sql: 'SELECT * FROM t1' },
      ],
      explanation: '简单查询',
    }

    it('returns orchestration result on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(orchestrateResponse), { status: 200 })
      )
      const result = await api.askOrchestrate({ description: 'query t1' })
      expect(result).not.toBeNull()
      expect(result!.steps).toHaveLength(1)
      expect(result!.steps[0].plugin).toBe('sql')
      expect(result!.explanation).toBe('简单查询')
    })

    it('returns result with parse_error flag', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ...orchestrateResponse, parse_error: true, raw: 'bad json' }), { status: 200 })
      )
      const result = await api.askOrchestrate({ description: 'test' })
      expect(result!.parse_error).toBe(true)
      expect(result!.raw).toBe('bad json')
    })

    it('sets aiError on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'AI 超时' }), { status: 504 })
      )
      const result = await api.askOrchestrate({})
      expect(result).toBeNull()
      expect(api.aiError.value).toBe('AI 超时')
    })

    it('returns null on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.askOrchestrate({})
      expect(result).toBeNull()
    })
  })
})
