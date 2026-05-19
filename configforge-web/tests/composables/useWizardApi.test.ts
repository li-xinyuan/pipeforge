import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useWizardApi, useAiApi } from '../../src/composables/useWizardApi'

describe('useWizardApi', () => {
  let api: ReturnType<typeof useWizardApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    api = useWizardApi()
  })

  describe('initScene', () => {
    it('returns scene data on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ scene: { name: '新场景', version: '1.0' } }), { status: 200 })
      )
      const result = await api.initScene(['f1', 'f2'])
      expect(result).toEqual({ scene: { name: '新场景', version: '1.0' } })
    })

    it('sets error on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Invalid file', code: 'INVALID' }), { status: 400 })
      )
      const result = await api.initScene([])
      expect(result).toBeNull()
      expect(api.error.value).toEqual({ message: 'Invalid file', code: 'INVALID' })
    })
  })

  describe('generateYaml', () => {
    it('returns yaml string', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ yaml: 'scene:\n  name: test' }), { status: 200 })
      )
      const result = await api.generateYaml({ scene: { name: 'test' } })
      expect(result).toEqual({ yaml: 'scene:\n  name: test' })
    })
  })

  describe('executeSql', () => {
    it('returns columns and rows', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ columns: ['a', 'b'], rows: [['1', '2']] }), { status: 200 })
      )
      const result = await api.executeSql('SELECT * FROM t', { t: 'f1' })
      expect(result).toEqual({ columns: ['a', 'b'], rows: [['1', '2']] })
    })
  })

  describe('executePipeline', () => {
    it('returns blob on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(new Blob(['fake-xlsx']), { status: 200, headers: { 'Content-Type': 'application/octet-stream' } })
      )
      const result = await api.executePipeline({})
      expect(result).toBeInstanceOf(Blob)
      expect(api.loading.value).toBe(false)
    })

    it('sets error on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'SQL syntax error', code: 'SQL_ERROR' }), { status: 400 })
      )
      const result = await api.executePipeline({})
      expect(result).toBeNull()
      expect(api.error.value?.message).toBe('SQL syntax error')
    })
  })

  describe('network error handling', () => {
    it('handles fetch rejection', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network down'))
      const result = await api.initScene([])
      expect(result).toBeNull()
      expect(api.error.value).toEqual({ message: 'Network error', code: 'NETWORK_ERROR' })
    })
  })
})

describe('useAiApi', () => {
  let ai: ReturnType<typeof useAiApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    ai = useAiApi()
  })

  describe('askSuggestion', () => {
    it('returns content on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ content: 'SELECT * FROM t', category: 'sql' }), { status: 200 })
      )
      const content = await ai.askSuggestion('sql', { description: 'all records' })
      expect(content).toBe('SELECT * FROM t')
      expect(ai.suggesting.value).toBe(false)
    })

    it('sets error on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'AI 响应超时' }), { status: 503 })
      )
      const content = await ai.askSuggestion('sql', {})
      expect(content).toBeNull()
      expect(ai.aiError.value).toBe('AI 响应超时')
    })

    it('sets suggesting flag during request', async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() =>
        new Promise(resolve => setTimeout(() => resolve(new Response('{}')), 50))
      )
      const promise = ai.askSuggestion('sql', {})
      expect(ai.suggesting.value).toBe(true)
      await promise
    })
  })

  describe('getAiSettings', () => {
    it('returns settings on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ enabled: true, provider: 'openai', api_key: 'sk-***' }), { status: 200 })
      )
      const settings = await ai.getAiSettings()
      expect(settings).toEqual({ enabled: true, provider: 'openai', api_key: 'sk-***' })
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 500 })
      )
      const settings = await ai.getAiSettings()
      expect(settings).toBeNull()
    })
  })

  describe('testAiConnection', () => {
    it('returns ok with latency data', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true, latency_ms: 350 }), { status: 200 })
      )
      const result = await ai.testAiConnection()
      expect(result.ok).toBe(true)
      expect(result.data?.latency_ms).toBe(350)
    })
  })
})
