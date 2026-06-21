import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useConnectionApi } from '../../src/composables/useConnectionApi'

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

const rawConnection = {
  id: 'conn1',
  name: '生产数据库',
  db_type: 'mysql',
  host: '10.0.0.1',
  port: 3306,
  database: 'production',
  username: 'root',
  password_set: true,
  verified: true,
  created_at: 1700000000,
  updated_at: 1700000000,
}

describe('useConnectionApi', () => {
  let api: ReturnType<typeof useConnectionApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    api = useConnectionApi()
  })

  describe('fetchConnections', () => {
    it('returns connections on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([rawConnection]), { status: 200 })
      )
      const result = await api.fetchConnections()
      expect(result).toHaveLength(1)
      expect(result[0].id).toBe('conn1')
      expect(result[0].name).toBe('生产数据库')
    })

    it('returns empty array on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'DB error' }), { status: 500 })
      )
      const result = await api.fetchConnections()
      expect(result).toEqual([])
    })

    it('returns empty array on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.fetchConnections()
      expect(result).toEqual([])
    })
  })

  describe('createConnection', () => {
    it('returns created connection on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawConnection), { status: 200 })
      )
      const result = await api.createConnection({ name: '生产数据库', db_type: 'mysql', host: '10.0.0.1' })
      expect(result).not.toBeNull()
      expect(result!.name).toBe('生产数据库')
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Duplicate name' }), { status: 409 })
      )
      const result = await api.createConnection({ name: '重复' })
      expect(result).toBeNull()
    })
  })

  describe('updateConnection', () => {
    it('returns updated connection on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ...rawConnection, name: '更新数据库' }), { status: 200 })
      )
      const result = await api.updateConnection('conn1', { name: '更新数据库' })
      expect(result).not.toBeNull()
      expect(result!.name).toBe('更新数据库')
    })

    it('sends PUT request to correct URL', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawConnection), { status: 200 })
      )
      await api.updateConnection('conn1', { host: '10.0.0.2' })
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/connections/conn1')
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.method).toBe('PUT')
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.updateConnection('missing', { name: 'x' })
      expect(result).toBeNull()
    })
  })

  describe('deleteConnection', () => {
    it('returns true when deletion succeeds with ok=true', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
      const ok = await api.deleteConnection('conn1')
      expect(ok).toBe(true)
    })

    it('returns false when ok is not true', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: false }), { status: 200 })
      )
      const ok = await api.deleteConnection('conn1')
      expect(ok).toBe(false)
    })

    it('returns false on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const ok = await api.deleteConnection('missing')
      expect(ok).toBe(false)
    })
  })

  describe('testConnection', () => {
    it('returns ok result on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
      const result = await api.testConnection('conn1')
      expect(result.ok).toBe(true)
    })

    it('returns error message on failure response', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: false, error: 'Connection refused' }), { status: 200 })
      )
      const result = await api.testConnection('conn1')
      expect(result.ok).toBe(false)
      expect(result.error).toBe('Connection refused')
    })

    it('returns not ok on API error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Server error' }), { status: 500 })
      )
      const result = await api.testConnection('conn1')
      expect(result.ok).toBe(false)
    })

    it('returns not ok on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.testConnection('conn1')
      expect(result.ok).toBe(false)
    })
  })

  describe('fetchTables', () => {
    it('returns table names on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ tables: ['users', 'orders', 'products'] }), { status: 200 })
      )
      const result = await api.fetchTables('conn1')
      expect(result).toEqual(['users', 'orders', 'products'])
    })

    it('returns empty array on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.fetchTables('missing')
      expect(result).toEqual([])
    })

    it('calls correct URL with connection id', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ tables: [] }), { status: 200 })
      )
      await api.fetchTables('conn1')
      const url = fetchSpy.mock.calls[0][0]
      expect(url).toBe('/api/connections/conn1/tables')
    })
  })

  describe('fetchColumns', () => {
    it('returns columns on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({
          columns: [
            { name: 'id', type: 'INTEGER' },
            { name: 'name', type: 'VARCHAR' },
          ],
        }), { status: 200 })
      )
      const result = await api.fetchColumns('conn1', 'users')
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('id')
      expect(result[0].type).toBe('INTEGER')
    })

    it('encodes table name in URL', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ columns: [] }), { status: 200 })
      )
      await api.fetchColumns('conn1', 'my table')
      const url = fetchSpy.mock.calls[0][0] as string
      expect(url).toContain('/api/connections/conn1/tables/my%20table/columns')
    })

    it('returns empty array on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.fetchColumns('conn1', 'missing')
      expect(result).toEqual([])
    })
  })

  describe('connectionError sync', () => {
    it('syncs error message from apiError', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: '连接超时' }), { status: 500 })
      )
      await api.fetchConnections()
      expect(api.connectionError.value).toBe('连接超时')
    })
  })
})
