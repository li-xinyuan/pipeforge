import { useApi, ApiError, handleApiError } from './useApi'

export interface NotificationConfig {
  id: string
  name: string
  type: 'webhook' | 'email'
  enabled: boolean
  webhook_url: string
  webhook_provider: 'dingtalk' | 'wecom' | 'feishu' | 'generic'
  webhook_headers: Record<string, string>
  email_to: string[]
  email_subject_template: string
  email_body_template: string
  trigger_on_success: boolean
  trigger_on_failure: boolean
  config_ids: string[] | null
}

export interface NotificationHistoryEntry {
  id: string
  config_id: string
  config_name: string
  execution_id: string
  pipeline_config_name: string
  status: string
  notify_success: boolean
  provider: string
  message: string
  triggered_at: string
}

export function useNotificationApi() {
  const { loading, error, requestOrThrow } = useApi()

  async function listConfigs(): Promise<NotificationConfig[]> {
    try {
      const data = await requestOrThrow<NotificationConfig[]>('GET', '/api/notifications/configs')
      return data || []
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    }
  }

  async function getConfig(id: string): Promise<NotificationConfig | null> {
    try {
      return await requestOrThrow<NotificationConfig>('GET', `/api/notifications/configs/${id}`)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function createConfig(body: Partial<NotificationConfig>): Promise<NotificationConfig | null> {
    try {
      return await requestOrThrow<NotificationConfig>('POST', '/api/notifications/configs', body)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function updateConfig(id: string, body: Partial<NotificationConfig>): Promise<NotificationConfig | null> {
    try {
      return await requestOrThrow<NotificationConfig>('PUT', `/api/notifications/configs/${id}`, body)
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function deleteConfig(id: string): Promise<boolean> {
    try {
      const result = await requestOrThrow<{ ok: boolean }>('DELETE', `/api/notifications/configs/${id}`)
      return result?.ok ?? false
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return false
    }
  }

  async function testConfig(id: string): Promise<{ ok: boolean; message: string; provider: string }> {
    try {
      const data = await requestOrThrow<{ ok: boolean; message: string; provider: string }>('POST', `/api/notifications/test/${id}`)
      return data || { ok: false, message: '请求失败', provider: '' }
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return { ok: false, message: '请求失败', provider: '' }
    }
  }

  async function getHistory(limit = 50): Promise<NotificationHistoryEntry[]> {
    try {
      const data = await requestOrThrow<NotificationHistoryEntry[]>('GET', `/api/notifications/history?limit=${limit}`)
      return data || []
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return []
    }
  }

  return { loading, error, listConfigs, getConfig, createConfig, updateConfig, deleteConfig, testConfig, getHistory }
}
