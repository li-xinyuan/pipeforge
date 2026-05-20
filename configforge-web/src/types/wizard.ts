export interface UploadedFileMeta {
  fileId: string
  originalName: string
  columns?: string[]
  sampleRows?: string[][]
}

export interface ConfirmedAnalysis {
  columnTypes: Record<string, string>
  tableName: string
  paramKeys: string[]
  timestamp: number
}

export interface AiSuggestion {
  content: string
  category: 'scene' | 'columns' | 'sql' | 'mapping' | 'diagnose'
  status: 'pending' | 'accepted' | 'rejected' | 'auto'
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

export type DbType = 'sqlite' | 'mysql' | 'postgresql'

export interface DatabaseInputConfig {
  type: 'database'
  connectionId: string
  queryType: 'table' | 'sql'
  tables: string[]    // max 1 element; multi-table → multiple InputSources or JOIN
  sql: string
}

export type DbConnection =
  | {
      id: string
      name: string
      dbType: 'sqlite'
      filePath: string
      createdAt: number
      updatedAt: number
    }
  | {
      id: string
      name: string
      dbType: 'mysql' | 'postgresql'
      host: string
      port: number
      database: string
      username: string
      password: string
      createdAt: number
      updatedAt: number
    }

export interface DbConnectionSummary {
  id: string
  name: string
  dbType: DbType
  // sqlite → filePath, mysql/postgresql → hostname/IP
  host: string
  port?: number
  database?: string
  username?: string
  passwordSet: boolean
  verified: boolean
  createdAt: number
  updatedAt: number
}

export interface InputSource {
  plugin: 'excel' | 'csv' | 'database'
  table: string
  paramKey: string
  fileId: string
  config: ExcelInputConfig | CsvInputConfig | DatabaseInputConfig
  confirmedAnalysis?: ConfirmedAnalysis
}

export interface ProcessorConfig {
  plugin: 'sql'
  sql: string
  outputTable: string
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

export interface SavedConfig {
  id: string
  sceneName: string
  description: string
  inputCount: number
  outputType: string
  version: string
  updatedAt: string
  inputs: Array<{ name: string; paramKey: string; plugin: string }>
}
