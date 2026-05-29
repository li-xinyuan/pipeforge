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
  category: 'scene' | 'columns' | 'sql' | 'mapping' | 'diagnose' | 'chat' | 'orchestrate'
  status: 'pending' | 'accepted' | 'rejected' | 'auto'
  timestamp: number
}

export type OrchestrationStep =
  | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string }
  | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string }

export interface OrchestrationResult {
  steps: OrchestrationStep[]
  explanation: string
  raw?: string
  parse_error?: boolean
}

/** ChatMessage — single source of truth (used by AiChatPanel, ConfigWizardView, etc.) */
export interface ChatMessage {
  role: 'user' | 'ai'
  content: string
  code?: string
  orchestration?: OrchestrationResult
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

export type ProcessorStep =
  | { name: string; plugin: 'sql'; sql: string; inputTables: string[]; outputTables: string[] }
  | { name: string; plugin: 'python'; script: string; inputTables: string[]; outputTables: string[] }

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
  processors: ProcessorStep[]
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
