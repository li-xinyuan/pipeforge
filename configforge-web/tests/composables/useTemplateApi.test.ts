import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useTemplateApi } from '../../src/composables/useTemplateApi'

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

const rawTemplate = {
  id: 't1',
  name: '月度报表',
  description: '生成月度报表模板',
  category: 'report',
  tags: ['finance', 'monthly'],
  author: 'admin',
  version: '1.0',
  config_state: { scene: { name: '报表' } },
  requirements: [{ type: 'database', description: '需要数据库连接' }],
  usage_count: 10,
  is_official: true,
  created_at: '2026-01-01',
  updated_at: '2026-06-01',
}

describe('useTemplateApi', () => {
  let api: ReturnType<typeof useTemplateApi>

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    api = useTemplateApi()
  })

  describe('listTemplates', () => {
    it('returns mapped templates with items/total format', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [rawTemplate], total: 1 }), { status: 200 })
      )
      const result = await api.listTemplates()
      expect(result.items).toHaveLength(1)
      expect(result.items[0].id).toBe('t1')
      expect(result.items[0].name).toBe('月度报表')
      expect(result.items[0].configState).toEqual({ scene: { name: '报表' } })
      expect(result.items[0].usageCount).toBe(10)
      expect(result.items[0].isOfficial).toBe(true)
      expect(result.total).toBe(1)
    })

    it('handles array response format', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify([rawTemplate]), { status: 200 })
      )
      const result = await api.listTemplates()
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes category and search params', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 })
      )
      await api.listTemplates('report', '月度')
      const url = fetchSpy.mock.calls[0][0] as string
      expect(url).toContain('category=report')
      expect(url).toContain('search=%E6%9C%88%E5%BA%A6')
    })

    it('returns empty result on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'DB down' }), { status: 500 })
      )
      const result = await api.listTemplates()
      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
    })

    it('returns empty result on network error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Offline'))
      const result = await api.listTemplates()
      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
    })
  })

  describe('getTemplate', () => {
    it('returns mapped template on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawTemplate), { status: 200 })
      )
      const result = await api.getTemplate('t1')
      expect(result).not.toBeNull()
      expect(result!.id).toBe('t1')
      expect(result!.name).toBe('月度报表')
    })

    it('returns null on error', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.getTemplate('missing')
      expect(result).toBeNull()
    })
  })

  describe('createTemplate', () => {
    it('returns mapped template on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawTemplate), { status: 200 })
      )
      const result = await api.createTemplate({
        name: '月度报表',
        description: 'desc',
        category: 'report',
        tags: ['finance'],
        configState: { scene: { name: '报表' } },
        author: 'admin',
      })
      expect(result).not.toBeNull()
      expect(result!.name).toBe('月度报表')
    })

    it('converts configState to config_state in request body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawTemplate), { status: 200 })
      )
      await api.createTemplate({
        name: 'test',
        description: '',
        category: '',
        tags: [],
        configState: { key: 'val' },
        author: 'admin',
      })
      const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string)
      expect(body.config_state).toEqual({ key: 'val' })
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Invalid data' }), { status: 400 })
      )
      const result = await api.createTemplate({
        name: '', description: '', category: '', tags: [], configState: {}, author: '',
      })
      expect(result).toBeNull()
    })
  })

  describe('updateTemplate', () => {
    it('returns mapped template on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ ...rawTemplate, name: '更新报表' }), { status: 200 })
      )
      const result = await api.updateTemplate('t1', { name: '更新报表' })
      expect(result).not.toBeNull()
      expect(result!.name).toBe('更新报表')
    })

    it('converts configState to config_state in request body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawTemplate), { status: 200 })
      )
      await api.updateTemplate('t1', { configState: { new: 'state' } })
      const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string)
      expect(body.config_state).toEqual({ new: 'state' })
    })

    it('only includes defined fields in request body', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(rawTemplate), { status: 200 })
      )
      await api.updateTemplate('t1', { name: 'new-name' })
      const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string)
      expect(Object.keys(body)).toEqual(['name'])
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.updateTemplate('missing', { name: 'x' })
      expect(result).toBeNull()
    })
  })

  describe('deleteTemplate', () => {
    it('returns true on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('{}', { status: 200 })
      )
      const ok = await api.deleteTemplate('t1')
      expect(ok).toBe(true)
    })

    it('returns false on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const ok = await api.deleteTemplate('missing')
      expect(ok).toBe(false)
    })
  })

  describe('instantiateTemplate', () => {
    it('returns config_state on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ config_state: { scene: { name: '报表' } } }), { status: 200 })
      )
      const result = await api.instantiateTemplate('t1')
      expect(result).toEqual({ scene: { name: '报表' } })
    })

    it('returns null when config_state is missing', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      )
      const result = await api.instantiateTemplate('t1')
      expect(result).toBeNull()
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.instantiateTemplate('missing')
      expect(result).toBeNull()
    })
  })

  describe('checkCompatibility', () => {
    it('returns compatibility result on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({
          compatible: true,
          issues: [{ requirement: 'database', status: 'ok', suggestion: '已满足' }],
        }), { status: 200 })
      )
      const result = await api.checkCompatibility('t1')
      expect(result).not.toBeNull()
      expect(result!.compatible).toBe(true)
      expect(result!.issues).toHaveLength(1)
      expect(result!.issues[0].requirement).toBe('database')
    })

    it('handles empty issues array', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ compatible: true, issues: [] }), { status: 200 })
      )
      const result = await api.checkCompatibility('t1')
      expect(result!.issues).toEqual([])
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'fail' }), { status: 500 })
      )
      const result = await api.checkCompatibility('t1')
      expect(result).toBeNull()
    })
  })

  describe('exportTemplate', () => {
    it('returns blob on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(new Blob(['json-data']), {
          status: 200,
          headers: { 'Content-Type': 'application/octet-stream' },
        })
      )
      const result = await api.exportTemplate('t1')
      expect(result).toBeTruthy()
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Not found' }), { status: 404 })
      )
      const result = await api.exportTemplate('missing')
      expect(result).toBeNull()
    })
  })

  describe('importTemplate', () => {
    it('returns message and id on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ message: '导入成功', id: 'new-t1' }), { status: 200 })
      )
      const file = new File(['data'], 'template.json', { type: 'application/json' })
      const result = await api.importTemplate(file)
      expect(result).toEqual({ message: '导入成功', id: 'new-t1' })
    })

    it('sends FormData with file', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ message: 'ok', id: 'x' }), { status: 200 })
      )
      const file = new File(['data'], 'template.json')
      await api.importTemplate(file)
      const opts = fetchSpy.mock.calls[0][1] as RequestInit
      expect(opts.body).toBeInstanceOf(FormData)
    })

    it('returns null on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'Invalid file' }), { status: 400 })
      )
      const file = new File(['bad'], 'bad.json')
      const result = await api.importTemplate(file)
      expect(result).toBeNull()
    })
  })
})
