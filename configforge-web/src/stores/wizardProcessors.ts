import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ProcessorStep } from '../types/wizard'

export const useWizardProcessorsStore = defineStore('wizardProcessors', () => {
  const processors = ref<ProcessorStep[]>([])

  function addProcessor(plugin: 'sql' | 'python' = 'sql') {
    if (plugin === 'python') {
      processors.value.push({ name: '', plugin: 'python', script: '', inputTables: [], outputTables: [], checkpoints: [] })
    } else {
      processors.value.push({ name: '', plugin: 'sql', sql: '', inputTables: [], outputTables: [], checkpoints: [] })
    }
  }

  function removeProcessor(index: number) {
    processors.value.splice(index, 1)
  }

  function updateProcessor(index: number, proc: ProcessorStep) {
    processors.value[index] = proc
  }

  function setProcessors(newProcessors: ProcessorStep[]) {
    const valid = newProcessors.filter(p => p.plugin === 'sql' ? p.sql.trim() : p.script.trim())
    if (valid.length === 0) return
    for (let i = 0; i < valid.length; i++) {
      if (valid[i].outputTables.length === 0) {
        valid[i].outputTables = [`step_${i + 1}_output`]
      }
      if (!valid[i].name) {
        valid[i].name = `步骤 ${i + 1}`
      }
    }
    processors.value = valid
  }

  function reset() {
    processors.value = []
  }

  function loadProcessors(rawProcessors: Record<string, unknown>[]) {
    processors.value = rawProcessors.map((raw) => {
      const plugin = (raw.plugin || 'sql') as string
      const base = {
        name: (raw.name || '') as string,
        plugin,
        inputTables: (raw.inputTables || []) as string[],
        outputTables: (raw.outputTables || (raw.outputTable ? [raw.outputTable] : [])) as string[],
        // CheckRule fields use snake_case matching backend, no camelCase conversion needed
        checkpoints: ((raw.checkpoints || []) as Record<string, unknown>[]).map((c) => ({ ...c, on_failure: c.on_failure || 'block' })),
      }
      if (plugin === 'python') {
        return { ...base, script: ((raw.config as Record<string, unknown>)?.script || raw.script || '') as string } as ProcessorStep
      }
      return { ...base, sql: ((raw.config as Record<string, unknown>)?.sql || raw.sql || '') as string } as ProcessorStep
    })
  }

  return { processors, addProcessor, removeProcessor, updateProcessor, setProcessors, reset, loadProcessors }
}, {
  persist: { key: 'wizard_processors_v1', storage: localStorage }
})
