import type { WizardState, SceneInfo, InputSource, ProcessorConfig, OutputTarget, UploadedFileMeta, AiSuggestion, ExcelInputConfig, CsvInputConfig, DatabaseInputConfig, ExcelOutputConfig, CsvOutputConfig } from '../types/wizard'

type InputConfig = ExcelInputConfig | CsvInputConfig | DatabaseInputConfig
type OutputConfig = ExcelOutputConfig | CsvOutputConfig

export interface SnakeState {
  current_step: number
  scene: { name: string; description: string; version: string }
  inputs: Array<{
    name: string
    plugin: string
    table: string
    param_key: string
    file_id: string
    config: Record<string, unknown>
  }>
  processor: {
    plugin: string
    sql: string
    output_tables: string[]
  }
  output: {
    plugin: string
    config: Record<string, unknown>
  } | null
  uploaded_files: Record<string, unknown>
}

function getConfigField<T>(config: InputConfig | OutputConfig, field: string): T {
  return (config as unknown as Record<string, T>)[field]
}

export function buildInputConfig(config: InputConfig) {
  if (config.type === 'csv') {
    return {
      type: 'csv',
      delimiter: getConfigField<string>(config, 'delimiter'),
      encoding: getConfigField<string>(config, 'encoding'),
      has_header: getConfigField<boolean>(config, 'hasHeader'),
    }
  }
  if (config.type === 'database') {
    return {
      type: 'database',
      connection_id: getConfigField<string>(config, 'connectionId'),
      db_type: getConfigField<string>(config, 'dbType'),
      query_type: getConfigField<string>(config, 'queryType'),
      tables: getConfigField<string[]>(config, 'tables'),
      sql: getConfigField<string>(config, 'sql'),
    }
  }
  return {
    type: getConfigField<string>(config, 'type'),
    sheet: getConfigField<string>(config, 'sheet'),
  }
}

export function buildOutputConfig(config: OutputConfig) {
  const base = {
    source_table: getConfigField<string>(config, 'sourceTable'),
    output_dir: getConfigField<string>(config, 'outputDir'),
    filename: getConfigField<string>(config, 'filename'),
    columns: (getConfigField<Array<{ source: string; target: string }>>(config, 'columns') || []).map(
      (c) => ({ source: c.source, target: c.target }),
    ),
  }
  if (config.type === 'csv') {
    return {
      type: 'csv',
      ...base,
      delimiter: getConfigField<string>(config, 'delimiter'),
      encoding: getConfigField<string>(config, 'encoding'),
    }
  }
  return {
    type: getConfigField<string>(config, 'type'),
    template: getConfigField<string>(config, 'template'),
    sheet: getConfigField<string>(config, 'sheet'),
    ...base,
  }
}

export function stateToSnakeCase(state: WizardState): SnakeState {
  return {
    current_step: state.currentStep,
    scene: {
      name: state.scene.name,
      description: state.scene.description,
      version: state.scene.version,
    },
    inputs: state.inputs.map((inp) => ({
      name: inp.table,
      plugin: inp.plugin,
      table: inp.table,
      param_key: inp.paramKey,
      file_id: inp.fileId,
      config: buildInputConfig(inp.config),
    })),
    processor: {
      plugin: state.processor.plugin,
      sql: state.processor.sql,
      output_tables: [state.processor.outputTable],
    },
    output: state.output
      ? {
          plugin: state.output.plugin,
          config: buildOutputConfig(state.output.config),
        }
      : null,
    uploaded_files: {},
  }
}
