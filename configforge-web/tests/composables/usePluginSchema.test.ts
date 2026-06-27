import { describe, it, expect, beforeEach, vi } from 'vitest'
import { usePluginSchema } from '../../src/composables/usePluginSchema'

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

const csvInputSchema = {
  name: 'csv',
  type: 'input',
  label: 'CSV',
  config_schema: {
    type: 'object',
    properties: {
      type: { type: 'string', const: 'csv' },
      delimiter: { type: 'string', default: ',' },
      encoding: { type: 'string', default: 'utf-8' },
      hasHeader: { type: 'boolean', default: true },
      file: { type: 'string' },
    },
  },
}

const excelInputSchema = {
  name: 'excel',
  type: 'input',
  label: 'Excel',
  config_schema: { type: 'object', properties: { type: { type: 'string', const: 'excel' }, sheet: { type: 'string' } } },
}

describe('usePluginSchema', () => {
  let api: ReturnType<typeof usePluginSchema>

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    api = usePluginSchema()
    api.clearCache()
  })

  describe('load', () => {
    it('loads plugin manifest from API', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([csvInputSchema, excelInputSchema]), { status: 200 }),
      )
      const result = await api.load()
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('csv')
    })

    it('caches result — second load does not call fetch', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([csvInputSchema]), { status: 200 }),
      )
      await api.load()
      await api.load()
      expect(fetchSpy).toHaveBeenCalledTimes(1)
    })

    it('force=true bypasses cache', async () => {
      const fetchSpy = vi
        .spyOn(globalThis, 'fetch')
        .mockResolvedValue(new Response(JSON.stringify([csvInputSchema]), { status: 200 }))
      await api.load()
      await api.load(true)
      expect(fetchSpy).toHaveBeenCalledTimes(2)
    })

    it('returns empty array on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'server error' }), { status: 500 }),
      )
      const result = await api.load()
      expect(result).toEqual([])
    })
  })

  describe('getSchema', () => {
    it('returns schema for a loaded plugin', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([csvInputSchema, excelInputSchema]), { status: 200 }),
      )
      await api.load()
      const schema = api.getSchema('csv', 'input')
      expect(schema).toBeDefined()
      expect(schema?.properties).toHaveProperty('delimiter')
    })

    it('returns undefined before load', () => {
      expect(api.getSchema('csv', 'input')).toBeUndefined()
    })

    it('returns undefined for unknown plugin', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([csvInputSchema]), { status: 200 }),
      )
      await api.load()
      expect(api.getSchema('nonexistent', 'input')).toBeUndefined()
    })
  })

  describe('getSchemaAsync', () => {
    it('auto-loads then returns schema', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([csvInputSchema]), { status: 200 }),
      )
      const schema = await api.getSchemaAsync('csv', 'input')
      expect(schema).toBeDefined()
      expect(schema?.properties).toHaveProperty('hasHeader')
    })
  })

  describe('clearCache', () => {
    it('clears cache so next load refetches', async () => {
      const fetchSpy = vi
        .spyOn(globalThis, 'fetch')
        .mockResolvedValue(new Response(JSON.stringify([csvInputSchema]), { status: 200 }))
      await api.load()
      api.clearCache()
      expect(api.getSchema('csv', 'input')).toBeUndefined()
      await api.load()
      expect(fetchSpy).toHaveBeenCalledTimes(2)
    })
  })
})
