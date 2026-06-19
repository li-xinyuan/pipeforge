import type { Template } from '../types/wizard'
import { snakeToCamel } from '../utils/transform'
import { useApi } from './useApi'

function mapTemplate(raw: Record<string, unknown>): Template {
  const camel = snakeToCamel(raw) as Record<string, unknown>
  return {
    id: camel.id as string,
    name: camel.name as string,
    description: (camel.description || '') as string,
    category: (camel.category || '') as string,
    tags: (camel.tags || []) as string[],
    author: (camel.author || '') as string,
    version: (camel.version || '1.0') as string,
    configState: (camel.configState || {}) as Record<string, unknown>,
    requirements: (camel.requirements || []) as Template['requirements'],
    usageCount: (camel.usageCount || 0) as number,
    isOfficial: (camel.isOfficial || false) as boolean,
    createdAt: (camel.createdAt || '') as string,
    updatedAt: (camel.updatedAt || '') as string,
  }
}

export function useTemplateApi() {
  const { loading, error, request } = useApi()

  async function listTemplates(category?: string, search?: string): Promise<{ items: Template[]; total: number }> {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (search) params.set('search', search)
    const qs = params.toString()
    const url = `/api/templates${qs ? '?' + qs : ''}`
    const data = await request<{ items: Record<string, unknown>[]; total: number } | Record<string, unknown>[]>(url.includes('?') ? 'GET' : 'GET', url)
    if (!data) return { items: [], total: 0 }
    if (Array.isArray(data)) {
      return { items: data.map(mapTemplate), total: data.length }
    }
    const items = (data.items || []) as Record<string, unknown>[]
    return { items: items.map(mapTemplate), total: data.total ?? items.length }
  }

  async function getTemplate(id: string): Promise<Template | null> {
    const data = await request<Record<string, unknown>>('GET', `/api/templates/${id}`)
    if (!data) return null
    return mapTemplate(data)
  }

  async function createTemplate(data: {
    name: string
    description: string
    category: string
    tags: string[]
    configState: Record<string, unknown>
    author: string
  }): Promise<Template | null> {
    const body = {
      name: data.name,
      description: data.description,
      category: data.category,
      tags: data.tags,
      config_state: data.configState,
      author: data.author,
    }
    const result = await request<Record<string, unknown>>('POST', '/api/templates', body)
    if (!result) return null
    return mapTemplate(result)
  }

  async function updateTemplate(id: string, data: Partial<Template>): Promise<Template | null> {
    const body: Record<string, unknown> = {}
    if (data.name !== undefined) body.name = data.name
    if (data.description !== undefined) body.description = data.description
    if (data.category !== undefined) body.category = data.category
    if (data.tags !== undefined) body.tags = data.tags
    if (data.configState !== undefined) body.config_state = data.configState
    if (data.author !== undefined) body.author = data.author
    const result = await request<Record<string, unknown>>('PUT', `/api/templates/${id}`, body)
    if (!result) return null
    return mapTemplate(result)
  }

  async function deleteTemplate(id: string): Promise<boolean> {
    const result = await request<unknown>('DELETE', `/api/templates/${id}`)
    return result !== null
  }

  async function instantiateTemplate(id: string): Promise<Record<string, unknown> | null> {
    const data = await request<{ config_state: Record<string, unknown> }>('POST', `/api/templates/${id}/instantiate`)
    if (!data) return null
    return data.config_state ?? null
  }

  async function checkCompatibility(id: string): Promise<{
    compatible: boolean
    issues: Array<{ requirement: string; status: string; suggestion: string }>
  } | null> {
    const data = await request<Record<string, unknown>>('POST', `/api/templates/${id}/check-compatibility`)
    if (!data) return null
    return {
      compatible: data.compatible as boolean,
      issues: ((data.issues || []) as Record<string, unknown>[]).map((i) => ({
        requirement: (i.requirement || '') as string,
        status: (i.status || '') as string,
        suggestion: (i.suggestion || '') as string,
      })),
    }
  }

  return {
    loading,
    error,
    listTemplates,
    getTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    instantiateTemplate,
    checkCompatibility,
  }
}
