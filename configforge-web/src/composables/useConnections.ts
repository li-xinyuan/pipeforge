import { ref } from 'vue'
import type { DbConnectionSummary } from '../types/wizard'
import { useConnectionApi } from './useConnectionApi'

export function useConnections() {
  const api = useConnectionApi()
  const connections = ref<DbConnectionSummary[]>([])
  const loading = ref(false)

  async function loadConnections(): Promise<DbConnectionSummary[]> {
    loading.value = true
    try {
      connections.value = await api.fetchConnections()
      return connections.value
    } finally {
      loading.value = false
    }
  }

  const connectionOptions = ref<Array<{ label: string; value: string }>>([])

  async function loadConnectionOptions(): Promise<void> {
    loading.value = true
    try {
      const list = await api.fetchConnections()
      connections.value = list
      connectionOptions.value = list.map(c => ({
        label: `${c.name} (${c.dbType})`,
        value: c.id,
      }))
    } catch {
      connectionOptions.value = []
    } finally {
      loading.value = false
    }
  }

  return {
    connections,
    connectionOptions,
    loading,
    loadConnections,
    loadConnectionOptions,
  }
}
