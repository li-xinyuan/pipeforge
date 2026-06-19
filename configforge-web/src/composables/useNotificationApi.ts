import { useApi } from './useApi'

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
  const { loading, error, request } = useApi()

  async function listConfigs(): Promise<NotificationConfig[]> {
    const data = await request<NotificationConfig[]>('GET', '/api/notifications/configs')
    return data || []
  }

  async function getConfig(id: string): Promise<NotificationConfig | null> {
    return request<NotificationConfig>('GET', `/api/notifications/configs/${id}`)
  }

  async function createConfig(body: Partial<NotificationConfig>): Promise<NotificationConfig | null> {
    return request<NotificationConfig>('POST', '/api/notifications/configs', body)
  }

  async function updateConfig(id: string, body: Partial<NotificationConfig>): Promise<NotificationConfig | null> {
    return request<NotificationConfig>('PUT', `/api/notifications/configs/${id}`, body)
  }

  async function deleteConfig(id: string): Promise<boolean> {
    const result = await request<{ ok: boolean }>('DELETE', `/api/notifications/configs/${id}`)
    return result?.ok ?? false
  }

  async function testConfig(id: string): Promise<{ ok: boolean; message: string; provider: string }> {
    const data = await request<{ ok: boolean; message: string; provider: string }>('POST', `/api/notifications/test/${id}`)
    return data || { ok: false, message: '请求失败', provider: '' }
  }

  async function getHistory(limit = 50): Promise<NotificationHistoryEntry[]> {
    const data = await request<NotificationHistoryEntry[]>('GET', `/api/notifications/history?limit=${limit}`)
    return data || []
  }

  return { loading, error, listConfigs, getConfig, createConfig, updateConfig, deleteConfig, testConfig, getHistory }
}
