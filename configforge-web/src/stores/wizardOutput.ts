import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OutputTarget, ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig } from '../types/wizard'

export const useWizardOutputStore = defineStore('wizardOutput', () => {
  const output = ref<OutputTarget | null>(null)

  function setOutput(o: OutputTarget) { output.value = o }

  function reset() {
    output.value = null
  }

  function loadOutput(outputData: Record<string, unknown> | null | undefined) {
    if (outputData) {
      const cfg = (outputData.config || {}) as Record<string, unknown>
      // Set defaults for output config fields
      cfg.sourceTable = cfg.sourceTable ?? ''
      cfg.targetTable = cfg.targetTable ?? ''
      cfg.writeMode = cfg.writeMode ?? 'append'
      cfg.createTableIfNotExists = cfg.createTableIfNotExists ?? true
      cfg.primaryKeyColumns = cfg.primaryKeyColumns ?? []
      cfg.batchSize = cfg.batchSize ?? 1000
      cfg.connectionId = cfg.connectionId ?? ''
      cfg.hasHeader = cfg.hasHeader ?? true
      output.value = {
        plugin: (outputData.plugin || 'excel') as 'excel' | 'csv' | 'database',
        config: cfg as unknown as ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig,
      }
    } else {
      output.value = null
    }
  }

  return { output, setOutput, reset, loadOutput }
}, {
  persist: { key: 'wizard_output_v1', storage: localStorage }
})
