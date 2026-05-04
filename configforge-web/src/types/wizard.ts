export interface UploadedFileMeta {
  fileId: string
  originalName: string
}

export interface AiSuggestion {
  content: string
  category: 'scene' | 'columns' | 'sql' | 'mapping'
  status: 'pending' | 'accepted' | 'rejected'
  timestamp: number
}

export interface SceneInfo {
  name: string
  description: string
  version: string
}

export interface ExcelInputConfig {
  type: 'excel'
  sheet: string
}

export interface InputSource {
  name: string
  plugin: 'excel'
  table: string
  paramKey: string
  fileId: string
  config: ExcelInputConfig
}

export interface ProcessorConfig {
  plugin: 'sql'
  sql: string
  outputTables: string[]
}

export interface ColumnMappingItem {
  source: string
  target: string
}

export interface ExcelOutputConfig {
  type: 'excel'
  template: string
  sheet: string
  outputDir: string
  sourceTable: string
  filename: string
  columns: ColumnMappingItem[]
}

export interface OutputTarget {
  plugin: 'excel'
  config: ExcelOutputConfig
}

export interface WizardState {
  currentStep: number
  scene: SceneInfo
  inputs: InputSource[]
  processor: ProcessorConfig
  output: OutputTarget | null
  uploadedFiles: Record<string, UploadedFileMeta>
  aiSuggestions: Record<string, AiSuggestion>
}
