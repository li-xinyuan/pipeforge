import type { WizardState } from '../types/wizard'
import { stateToSnakeCase } from '../utils/serialization'
import { useApi, ApiError, handleApiError } from './useApi'

export function useWizardApi() {
  const { loading, error, requestOrThrow } = useApi()

  async function initScene(fileIds: string[]) {
    try {
      return await requestOrThrow<Record<string, unknown>>('POST', '/api/wizard/init-scene', { file_ids: fileIds })
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function fetchPreview(fileId: string, sheet?: string) {
    try {
      return await requestOrThrow<{ sheets: string[]; columns: string[]; rows: string[][] }>('POST', '/api/preview/file', { file_id: fileId, sheet })
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function generateYaml(state: WizardState) {
    try {
      return await requestOrThrow<{ yaml: string }>('POST', '/api/wizard/generate', { state: stateToSnakeCase(state) })
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function executeSql(sql: string, tableMapping: Record<string, string>) {
    try {
      return await requestOrThrow<{
        columns: string[]
        rows: string[][]
        total_source_rows: number
        sample_rows_loaded: number
        is_sampled: boolean
      }>('POST', '/api/preview/sql', { sql, table_mapping: tableMapping })
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function dryRun(state: WizardState) {
    try {
      return await requestOrThrow<{
        tables: { table_name: string; columns: string[]; rows: string[][]; total_rows: number }[]
        inputs: Record<string, unknown>
        processors: Record<string, unknown>[]
      }>('POST', '/api/wizard/dry-run', { state: stateToSnakeCase(state) })
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  async function executePipeline(state: WizardState): Promise<Blob | { status: string; message: string; exec_id: string } | null> {
    try {
      return await requestOrThrow<Blob | { status: string; message: string; exec_id: string }>('POST', '/api/wizard/execute', { state: stateToSnakeCase(state) })
    } catch (e) {
      if (e instanceof ApiError) handleApiError(e)
      return null
    }
  }

  return { loading, error, initScene, fetchPreview, generateYaml, executeSql, dryRun, executePipeline }
}

// Re-export for backward compatibility
export { useAiApi } from './useAiApi'
export { useConnectionApi } from './useConnectionApi'
