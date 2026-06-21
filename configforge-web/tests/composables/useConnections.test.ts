import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useConnections } from '../../src/composables/useConnections'

const fetchConnections = vi.fn()

vi.mock('../../src/composables/useConnectionApi', () => ({
  useConnectionApi: () => ({ fetchConnections }),
}))

describe('useConnections', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('returns reactive refs with default values', () => {
    const { connections, connectionOptions, loading } = useConnections()
    expect(connections.value).toEqual([])
    expect(connectionOptions.value).toEqual([])
    expect(loading.value).toBe(false)
  })

  describe('loadConnections', () => {
    it('loads connections and returns them', async () => {
      const mockData = [
        { id: '1', name: 'prod-db', dbType: 'postgresql' },
        { id: '2', name: 'analytics', dbType: 'mysql' },
      ]
      fetchConnections.mockResolvedValueOnce(mockData)
      const { connections, loading, loadConnections } = useConnections()
      const result = await loadConnections()
      expect(connections.value).toEqual(mockData)
      expect(result).toEqual(mockData)
      expect(loading.value).toBe(false)
    })

    it('sets loading to true during fetch and false after', async () => {
      let resolve!: (v: unknown[]) => void
      fetchConnections.mockReturnValueOnce(new Promise(r => { resolve = r }))
      const { loading, loadConnections } = useConnections()
      const promise = loadConnections()
      expect(loading.value).toBe(true)
      resolve([])
      await promise
      expect(loading.value).toBe(false)
    })

    it('sets loading to false even on error', async () => {
      fetchConnections.mockRejectedValueOnce(new Error('fail'))
      const { loading, loadConnections } = useConnections()
      await expect(loadConnections()).rejects.toThrow('fail')
      expect(loading.value).toBe(false)
    })
  })

  describe('loadConnectionOptions', () => {
    it('maps connections to label/value options', async () => {
      const mockData = [
        { id: '1', name: 'prod-db', dbType: 'postgresql' },
        { id: '2', name: 'analytics', dbType: 'mysql' },
      ]
      fetchConnections.mockResolvedValueOnce(mockData)
      const { connectionOptions, loadConnectionOptions } = useConnections()
      await loadConnectionOptions()
      expect(connectionOptions.value).toEqual([
        { label: 'prod-db (postgresql)', value: '1' },
        { label: 'analytics (mysql)', value: '2' },
      ])
    })

    it('also populates connections ref', async () => {
      const mockData = [
        { id: '1', name: 'prod-db', dbType: 'postgresql' },
      ]
      fetchConnections.mockResolvedValueOnce(mockData)
      const { connections, loadConnectionOptions } = useConnections()
      await loadConnectionOptions()
      expect(connections.value).toEqual(mockData)
    })

    it('sets loading to true during fetch and false after', async () => {
      let resolve!: (v: unknown[]) => void
      fetchConnections.mockReturnValueOnce(new Promise(r => { resolve = r }))
      const { loading, loadConnectionOptions } = useConnections()
      const promise = loadConnectionOptions()
      expect(loading.value).toBe(true)
      resolve([])
      await promise
      expect(loading.value).toBe(false)
    })

    it('clears connectionOptions on error', async () => {
      fetchConnections.mockRejectedValueOnce(new Error('fail'))
      const { connectionOptions, loading, loadConnectionOptions } = useConnections()
      await loadConnectionOptions()
      expect(connectionOptions.value).toEqual([])
      expect(loading.value).toBe(false)
    })
  })
})
