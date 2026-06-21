import type { Template } from '../types/wizard'
import { snakeToCamel } from '../utils/transform'
import { useApi, ApiError, handleApiError } from './useApi'

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
  const { loading, error, requestOrThrow } = useApi()

  async function listTemplates(category?: string, search?: string): Promise<{ items: Template[]; total: number }> {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (search) params.set('search', search)
    const qs = params.toString()
    const url = `/api/templates${qs ? '?' + qs : ''}`
    try {
      const data = await requestOrThrow<{ items: Record<string, unknown>[]; total: number } | Record<string, unknown>[]>('GET', url)
      if (Array.isArray(data)) {
        return { items: data.map(mapTemplate), total: data.length }
      }
      const items = (data.items || []) as Record<string, unknown>[]
      return { items: items.map(mapTemplate), total: data.total ?? items.length }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return { items: [], total: 0 }
    }
  }

  async function getTemplate(id: string): Promise<Template | null> {
    try {
      const data = await requestOrThrow<Record<string, unknown>>('GET', `/api/templates/${id}`)
      return mapTemplate(data)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
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
    try {
      const result = await requestOrThrow<Record<string, unknown>>('POST', '/api/templates', body)
      return mapTemplate(result)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function updateTemplate(id: string, data: Partial<Template>): Promise<Template | null> {
    const body: Record<string, unknown> = {}
    if (data.name !== undefined) body.name = data.name
    if (data.description !== undefined) body.description = data.description
    if (data.category !== undefined) body.category = data.category
    if (data.tags !== undefined) body.tags = data.tags
    if (data.configState !== undefined) body.config_state = data.configState
    if (data.author !== undefined) body.author = data.author
    try {
      const result = await requestOrThrow<Record<string, unknown>>('PUT', `/api/templates/${id}`, body)
      return mapTemplate(result)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function deleteTemplate(id: string): Promise<boolean> {
    try {
      await requestOrThrow<unknown>('DELETE', `/api/templates/${id}`)
      return true
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return false
    }
  }

  async function instantiateTemplate(id: string): Promise<Record<string, unknown> | null> {
    try {
      const data = await requestOrThrow<{ config_state: Record<string, unknown> }>('POST', `/api/templates/${id}/instantiate`)
      return data.config_state ?? null
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function checkCompatibility(id: string): Promise<{
    compatible: boolean
    issues: Array<{ requirement: string; status: string; suggestion: string }>
  } | null> {
    try {
      const data = await requestOrThrow<Record<string, unknown>>('POST', `/api/templates/${id}/check-compatibility`)
      return {
        compatible: data.compatible as boolean,
        issues: ((data.issues || []) as Record<string, unknown>[]).map((i) => ({
          requirement: (i.requirement || '') as string,
          status: (i.status || '') as string,
          suggestion: (i.suggestion || '') as string,
        })),
      }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function exportTemplate(id: string): Promise<Blob | null> {
    try {
      const data = await requestOrThrow<Blob>('GET', `/api/templates/${id}/export`)
      return data
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function importTemplate(file: File): Promise<{ message: string; id: string } | null> {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const data = await requestOrThrow<Record<string, unknown>>('POST', '/api/templates/import', formData)
      return { message: (data.message || '') as string, id: (data.id || '') as string }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
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
    exportTemplate,
    importTemplate,
  }
}
