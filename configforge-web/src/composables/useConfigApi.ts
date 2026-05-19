import { ref } from 'vue'
import type { SavedConfig } from '../types/wizard'

function mapConfig(raw: any): SavedConfig {
  return {
    id: raw.id,
    sceneName: raw.scene_name,
    description: raw.description || '',
    inputCount: raw.input_count,
    outputType: raw.output_type,
    version: raw.version,
    updatedAt: raw.updated_at,
    inputs: (raw.inputs || []).map((i: any) => ({
      name: i.name,
      paramKey: i.param_key,
      plugin: i.plugin,
    })),
  }
}

export function useConfigApi() {
  const loading = ref(false)
  const error = ref<{ message: string; code: string } | null>(null)

  async function post<T>(url: string, body: any): Promise<T | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await resp.json()
      if (!resp.ok) { error.value = { message: data.error || data.detail, code: data.code }; return null }
      return data as T
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function listConfigs(): Promise<SavedConfig[]> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch('/api/configs')
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '加载失败', code: data?.code || 'LOAD_ERROR' }
        return []
      }
      const data = await resp.json()
      return (data || []).map(mapConfig)
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return []
    } finally { loading.value = false }
  }

  async function saveConfig(state: any, configId?: string | null): Promise<string | null> {
    const body = {
      config_id: configId || null,
      state: {
        current_step: state.currentStep,
        scene: { name: state.scene.name, description: state.scene.description, version: state.scene.version },
        inputs: state.inputs.map((inp: any) => ({
          name: inp.table,
          plugin: inp.plugin,
          table: inp.table,
          param_key: inp.paramKey,
          file_id: inp.fileId,
          config: inp.config,
        })),
        processor: {
          plugin: state.processor.plugin,
          sql: state.processor.sql,
          output_tables: [state.processor.outputTable],
        },
        output: state.output ? {
          plugin: state.output.plugin,
          config: (() => {
            const cfg = { ...state.output.config }
            if (cfg.sourceTable) { cfg.source_table = cfg.sourceTable; delete cfg.sourceTable }
            if (cfg.outputDir) { cfg.output_dir = cfg.outputDir; delete cfg.outputDir }
            if (cfg.hasHeader !== undefined) { cfg.has_header = cfg.hasHeader; delete cfg.hasHeader }
            return cfg
          })(),
        } : null,
        uploaded_files: {},
      },
    }
    const data = await post<{ id: string }>('/api/configs', body)
    return data?.id ?? null
  }

  async function deleteConfig(id: string): Promise<boolean> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${id}`, { method: 'DELETE' })
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '删除失败', code: data?.code || 'DELETE_ERROR' }
        return false
      }
      return true
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return false
    } finally { loading.value = false }
  }

  async function loadConfigState(id: string): Promise<any | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${id}`)
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '加载失败', code: data?.code || 'LOAD_ERROR' }
        return null
      }
      return await resp.json()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  async function downloadConfigYaml(id: string): Promise<void> {
    try {
      const resp = await fetch(`/api/configs/${id}/yaml`)
      if (!resp.ok) return
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      try {
        const a = document.createElement('a')
        a.href = url
        a.download = `pipeline_${id}.yaml`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } finally {
        URL.revokeObjectURL(url)
      }
    } catch { /* 下载失败静默忽略 */ }
  }

  async function executeConfig(id: string, files: Record<string, string>): Promise<Blob | null> {
    loading.value = true; error.value = null
    try {
      const resp = await fetch(`/api/configs/${id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files }),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => null)
        error.value = { message: data?.error || data?.detail || '执行失败', code: data?.code || 'EXECUTE_ERROR' }
        return null
      }
      return await resp.blob()
    } catch {
      error.value = { message: 'Network error', code: 'NETWORK_ERROR' }
      return null
    } finally { loading.value = false }
  }

  return { loading, error, listConfigs, saveConfig, deleteConfig, loadConfigState, downloadConfigYaml, executeConfig }
}
