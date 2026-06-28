import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { InputSource, UploadedFileMeta } from '../types/wizard'
import { usePluginSchema } from '../composables/usePluginSchema'

/**
 * deriveDefaultsFromSchema — 从 JSON schema 的 properties.default 派生配置默认值。
 *
 * 限制①动态表单基础设施：消除前端硬编码默认值，单一数据源来自后端 schema。
 *
 * 规则：
 * - 包含 `type` 字段（鉴别联合 discriminator，config 必须携带）
 * - 跳过 `file` 字段（pipeforge 运行时注入，前端不收集）
 * - 其他字段读取 `default` 值；无 default 时跳过（由 SchemaForm 运行时回退）
 */
function deriveDefaultsFromSchema(schema: Record<string, unknown> | undefined): Record<string, unknown> | null {
  if (!schema || typeof schema !== 'object') return null
  const properties = (schema as { properties?: Record<string, { default?: unknown }> }).properties
  if (!properties) return null
  const result: Record<string, unknown> = {}
  for (const [key, prop] of Object.entries(properties)) {
    if (key === 'file') continue // 运行时注入字段，前端不收集
    if (prop && 'default' in prop) {
      result[key] = prop.default
    }
  }
  return Object.keys(result).length > 0 ? result : null
}

/** api 插件无后端 schema（configforge 专属预览插件），保留硬编码默认值。 */
function apiInputDefaults(): Record<string, unknown> {
  return { type: 'api', url: '', method: 'GET', headers: {}, params: {}, dataPath: '', pagination: 'none', pageSize: 100, maxPages: 10 }
}

export const useWizardInputsStore = defineStore('wizardInputs', () => {
  const inputs = ref<InputSource[]>([])
  const uploadedFiles = ref<Record<string, UploadedFileMeta>>({})

  function addInput(plugin: InputSource['plugin'] = 'excel') {
    let config: Record<string, unknown>

    if (plugin === 'api') {
      // api 插件无后端 schema，使用专属默认值
      config = apiInputDefaults()
    } else {
      // 优先从后端 schema 派生默认值（限制①：单一数据源）
      const { getSchema } = usePluginSchema()
      const schema = getSchema(plugin, 'input')
      const derived = deriveDefaultsFromSchema(schema)
      if (derived) {
        config = derived
      } else {
        // schema 未加载时的回退（Day 13-16 迁移完成后可移除）
        config = hardcodedInputDefaults(plugin)
      }
    }

    inputs.value.push({
      plugin,
      table: '',
      paramKey: '',
      fileId: '',
      config,
    } as unknown as InputSource)
  }

  /** 硬编码回退默认值（schema 未加载时使用，Day 13-16 后移除）。 */
  function hardcodedInputDefaults(plugin: string): Record<string, unknown> {
    if (plugin === 'csv') return { type: 'csv', delimiter: ',', encoding: 'utf-8', hasHeader: true }
    if (plugin === 'database') return { type: 'database', connectionId: '', queryType: 'table', tables: [], sql: '' }
    if (plugin === 'json') return { type: 'json', flattenSeparator: '.' }
    if (plugin === 'xml') return { type: 'xml', rowElement: '' }
    if (plugin === 'parquet') return { type: 'parquet' }
    return { type: 'excel', sheet: '' }
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
        fileId: (inp.fileId || inp.file_id || '') as string,
        config: cfg as unknown as InputSource['config'],
      }
    })
  }

  return { inputs, uploadedFiles, addInput, removeInput, updateInput, addFileRef, removeFileRef, reset, loadInputs }
}, {
  persist: { key: 'wizard_inputs_v1', storage: localStorage }
})
