export interface UploadedFileMeta {
  fileId: string
  originalName: string
}

export interface AiSuggestion {
  content: string
  category: 'scene' | 'columns' | 'sql' | 'mapping' | 'diagnose'
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

export interface CsvInputConfig {
  type: 'csv'
  delimiter: string
  encoding: string
  hasHeader: boolean
}

export interface InputSource {
  name: string
  plugin: 'excel' | 'csv'
  table: string
  paramKey: string
  fileId: string
  config: ExcelInputConfig | CsvInputConfig
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

export interface CsvOutputConfig {
  type: 'csv'
  sourceTable: string
  outputDir: string
  filename: string
  delimiter: string
  encoding: string
  columns: ColumnMappingItem[]
}

export interface OutputTarget {
  plugin: 'excel' | 'csv'
  config: ExcelOutputConfig | CsvOutputConfig
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
