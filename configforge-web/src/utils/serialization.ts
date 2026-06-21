import type { WizardState, ExcelInputConfig, CsvInputConfig, DatabaseInputConfig, JsonInputConfig, XmlInputConfig, ParquetInputConfig, ApiInputConfig, ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig, CheckRule } from '../types/wizard'
import { camelToSnakeKey } from './transform'

type InputConfig = ExcelInputConfig | CsvInputConfig | DatabaseInputConfig | JsonInputConfig | XmlInputConfig | ParquetInputConfig | ApiInputConfig
type OutputConfig = ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig

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
  processors: Array<
    | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string; checkpoints: CheckRule[] }
    | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string; checkpoints: CheckRule[] }
  >
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
  if (config.type === 'json') {
    return {
      type: 'json',
      flatten_separator: getConfigField<string>(config, 'flattenSeparator'),
    }
  }
  if (config.type === 'xml') {
    return {
      type: 'xml',
      row_element: getConfigField<string>(config, 'rowElement'),
    }
  }
  if (config.type === 'parquet') {
    return {
      type: 'parquet',
    }
  }
  if (config.type === 'api') {
    return {
      type: 'api',
      url: getConfigField<string>(config, 'url'),
      method: getConfigField<string>(config, 'method'),
      headers: getConfigField<Record<string, string>>(config, 'headers'),
      params: getConfigField<Record<string, string>>(config, 'params'),
      data_path: getConfigField<string>(config, 'dataPath'),
      pagination: getConfigField<string>(config, 'pagination'),
      page_size: getConfigField<number>(config, 'pageSize'),
      max_pages: getConfigField<number>(config, 'maxPages'),
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
  if (config.type === 'database') {
    return {
      type: 'database',
      source_table: getConfigField<string>(config, 'sourceTable'),
      columns: (getConfigField<Array<{ source: string; target: string }>>(config, 'columns') || []).map(
        (c) => ({ source: c.source, target: c.target }),
      ),
      connection_id: getConfigField<string>(config, 'connectionId'),
      target_table: getConfigField<string>(config, 'targetTable'),
      write_mode: getConfigField<string>(config, 'writeMode'),
      create_table_if_not_exists: getConfigField<boolean>(config, 'createTableIfNotExists'),
      primary_key_columns: getConfigField<string[]>(config, 'primaryKeyColumns'),
      batch_size: getConfigField<number>(config, 'batchSize'),
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
    processors: state.processors.map((p) => {
      const snakeCheckpoints = (p.checkpoints || []).map((c: CheckRule) => {
        const result: Record<string, unknown> = {}
        for (const [key, value] of Object.entries(c)) {
          result[camelToSnakeKey(key)] = value
        }
        return result as unknown as CheckRule
      })
      if (p.plugin === 'python') {
        return {
          name: p.name, plugin: 'python' as const,
          input_tables: p.inputTables, output_tables: p.outputTables,
          script: p.script,
          checkpoints: snakeCheckpoints,
        }
      }
      return {
        name: p.name, plugin: 'sql' as const,
        input_tables: p.inputTables, output_tables: p.outputTables,
        sql: p.sql,
        checkpoints: snakeCheckpoints,
      }
    }),
    output: state.output
      ? {
          plugin: state.output.plugin,
          config: buildOutputConfig(state.output.config),
        }
      : null,
    uploaded_files: {},
  }
}
