import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useConfigApi } from '../../src/composables/useConfigApi'

describe('useConfigApi', () => {
  let api: ReturnType<typeof useConfigApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    api = useConfigApi()
  })

  describe('listConfigs', () => {
    it('returns mapped configs on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({
          items: [
            {
              id: 'c1', scene_name: '月度报表', description: 'desc',
              input_count: 2, output_type: 'excel', version: '1.0',
              updated_at: '2026-05-12', inputs: [{ name: 'in1', param_key: 'f1', plugin: 'excel' }],
            },
          ],
          total: 1, page: 1, page_size: 10, total_pages: 1,
        }), { status: 200 })
      )
      const result = await api.listConfigs()
      expect(result.items).toHaveLength(1)
      expect(result.items[0].id).toBe('c1')
      expect(result.items[0].sceneName).toBe('月度报表')
      expect(result.items[0].inputs).toHaveLength(1)
    })

    it('returns empty result on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'DB down' }), { status: 500 })
      )
      const result = await api.listConfigs()
      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
    })

    it('returns empty result on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.listConfigs()
      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
    })
  })

  describe('saveConfig', () => {
    const mockState = {
      currentStep: 5,
      scene: { name: '测试', description: 'desc', version: '1.0' },
      inputs: [{ plugin: 'excel', table: 't1', paramKey: 'f1', fileId: 'abc', config: { type: 'excel', sheet: 'Sheet1' } }],
      processors: [{ name: '', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['out1'] }],
      output: { plugin: 'excel', config: { type: 'excel', template: '', sheet: 'Sheet1', sourceTable: 'out1', outputDir: './output/', filename: 'out.xlsx', columns: [] } },
    }

    it('returns config id on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 'new-id-123' }), { status: 200 })
      )
      const id = await api.saveConfig(mockState)
      expect(id).toBe('new-id-123')
      expect(api.loading.value).toBe(false)
    })

    it('converts camelCase fields to snake_case in request body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 'x' }), { status: 200 })
      )
      await api.saveConfig(mockState)
      const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string)
      expect(body.state.scene.name).toBe('测试')
      expect(body.state.inputs[0].param_key).toBe('f1')
      expect(body.state.processors[0].output_tables).toEqual(['out1'])
      expect(body.state.output.config.source_table).toBe('out1')
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Disk full' }), { status: 500 })
      )
      const id = await api.saveConfig(mockState)
      expect(id).toBeNull()
    })
  })

  describe('deleteConfig', () => {
    it('returns true on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      const ok = await api.deleteConfig('c1')
      expect(ok).toBe(true)
    })

    it('returns false on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const ok = await api.deleteConfig('missing')
      expect(ok).toBe(false)
    })
  })

  describe('loadConfigState', () => {
    it('returns raw state on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ scene: { name: '已存场景' } }), { status: 200 })
      )
      const state = await api.loadConfigState('c1')
      expect(state).toEqual({ scene: { name: '已存场景' } })
    })

    it('returns null on 404', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const state = await api.loadConfigState('missing')
      expect(state).toBeNull()
    })
  })
})
