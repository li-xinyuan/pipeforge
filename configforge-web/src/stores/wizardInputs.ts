import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { InputSource, UploadedFileMeta } from '../types/wizard'

export const useWizardInputsStore = defineStore('wizardInputs', () => {
  const inputs = ref<InputSource[]>([])
  const uploadedFiles = ref<Record<string, UploadedFileMeta>>({})

  function addInput(plugin: InputSource['plugin'] = 'excel') {
    let config: InputSource['config']
    if (plugin === 'csv') {
      config = { type: 'csv' as const, delimiter: ',', encoding: 'utf-8', hasHeader: true }
    } else if (plugin === 'database') {
      config = { type: 'database' as const, connectionId: '', queryType: 'table' as const, tables: [], sql: '' }
    } else if (plugin === 'json') {
      config = { type: 'json' as const, flattenSeparator: '.' }
    } else if (plugin === 'xml') {
      config = { type: 'xml' as const, rowElement: '' }
    } else if (plugin === 'parquet') {
      config = { type: 'parquet' as const }
    } else if (plugin === 'api') {
      config = { type: 'api' as const, url: '', method: 'GET', headers: {}, params: {}, dataPath: '', pagination: 'none', pageSize: 100, maxPages: 10 }
    } else {
      config = { type: 'excel' as const, sheet: '' }
    }

    inputs.value.push({
      plugin,
      table: '',
      paramKey: '',
      fileId: '',
      config,
    } as InputSource)
  }

  function removeInput(index: number) { inputs.value.splice(index, 1) }
  function updateInput(index: number, input: InputSource) { inputs.value[index] = input }
  function addFileRef(fileId: string, meta: UploadedFileMeta) { uploadedFiles.value[fileId] = meta }
  function removeFileRef(fileId: string) { delete uploadedFiles.value[fileId] }

  function reset() {
    inputs.value = []
    uploadedFiles.value = {}
  }

  function loadInputs(rawInputs: Record<string, unknown>[]) {
    inputs.value = rawInputs.map((inp) => {
      const cfg = (inp.config || {}) as Record<string, unknown>
      // Set defaults for database config fields
      if (inp.plugin === 'database' || cfg.type === 'database') {
        cfg.connectionId = cfg.connectionId ?? ''
        cfg.dbType = cfg.dbType ?? ''
        cfg.queryType = cfg.queryType ?? 'table'
        cfg.tables = cfg.tables ?? []
        cfg.sql = cfg.sql ?? ''
      }
      // Set defaults for json config fields
      if (inp.plugin === 'json' || cfg.type === 'json') {
        cfg.flattenSeparator = cfg.flattenSeparator ?? '.'
      }
      // Set defaults for xml config fields
      if (inp.plugin === 'xml' || cfg.type === 'xml') {
        cfg.rowElement = cfg.rowElement ?? ''
      }
      // Set defaults for api config fields
      if (inp.plugin === 'api' || cfg.type === 'api') {
        cfg.url = cfg.url ?? ''
        cfg.method = cfg.method ?? 'GET'
        cfg.headers = cfg.headers ?? {}
        cfg.params = cfg.params ?? {}
        cfg.dataPath = cfg.dataPath ?? ''
        cfg.pagination = cfg.pagination ?? 'none'
        cfg.pageSize = cfg.pageSize ?? 100
        cfg.maxPages = cfg.maxPages ?? 10
      }
      return {
        plugin: (inp.plugin || 'excel') as InputSource['plugin'],
        table: (inp.table || inp.name || '') as string,
        paramKey: (inp.paramKey || '') as string,
        fileId: '',
        config: cfg as unknown as InputSource['config'],
      }
    })
  }

  return { inputs, uploadedFiles, addInput, removeInput, updateInput, addFileRef, removeFileRef, reset, loadInputs }
}, {
  persist: { key: 'wizard_inputs_v1', storage: localStorage }
})
