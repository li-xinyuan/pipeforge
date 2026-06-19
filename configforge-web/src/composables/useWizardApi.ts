import type { WizardState } from '../types/wizard'
import { stateToSnakeCase } from '../utils/serialization'
import { useApi } from './useApi'

export function useWizardApi() {
  const { loading, error, request } = useApi()

  async function initScene(fileIds: string[]) {
    return request<Record<string, unknown>>('POST', '/api/wizard/init-scene', { file_ids: fileIds })
  }

  async function fetchPreview(fileId: string, sheet?: string) {
    return request<{ sheets: string[]; columns: string[]; rows: string[][] }>('POST', '/api/preview/file', { file_id: fileId, sheet })
  }

  async function generateYaml(state: WizardState) {
    return request<{ yaml: string }>('POST', '/api/wizard/generate', { state: stateToSnakeCase(state) })
  }

  async function executeSql(sql: string, tableMapping: Record<string, string>) {
    return request<{
      columns: string[]
      rows: string[][]
      total_source_rows: number
      sample_rows_loaded: number
      is_sampled: boolean
    }>('POST', '/api/preview/sql', { sql, table_mapping: tableMapping })
  }

  async function dryRun(state: WizardState) {
    return request<{
      tables: { table_name: string; columns: string[]; rows: string[][]; total_rows: number }[]
      inputs: Record<string, unknown>
      processors: Record<string, unknown>[]
    }>('POST', '/api/wizard/dry-run', { state: stateToSnakeCase(state) })
  }

  async function executePipeline(state: WizardState): Promise<Blob | { status: string; message: string; exec_id: string } | null> {
    return request<Blob | { status: string; message: string; exec_id: string }>('POST', '/api/wizard/execute', { state: stateToSnakeCase(state) })
  }

  return { loading, error, initScene, fetchPreview, generateYaml, executeSql, dryRun, executePipeline }
}

// Re-export for backward compatibility
export { useAiApi } from './useAiApi'
export { useConnectionApi } from './useConnectionApi'
