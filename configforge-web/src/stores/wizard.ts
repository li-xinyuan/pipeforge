import { defineStore } from 'pinia'
import { reactive, ref, computed } from 'vue'
import type { SceneInfo, InputSource, ProcessorStep, OutputTarget, UploadedFileMeta, AiSuggestion, WizardState } from '../types/wizard'

export const useWizardStore = defineStore('wizard', () => {
  const currentStep = ref(1)
  const scene = ref<SceneInfo>({ name: '', description: '', version: '1.0' })
  const inputs = ref<InputSource[]>([])
  const processors = ref<ProcessorStep[]>([])
  const output = ref<OutputTarget | null>(null)
  const configId = ref<string | null>(null)
  const uploadedFiles = ref<Record<string, UploadedFileMeta>>({})
  const aiSuggestions = ref<Record<string, AiSuggestion>>({})

  // AI 生成的执行计划（待办列表）
  const plan = ref<Record<number, { total: number; items: string[] }>>({})

  function setPlan(p: Record<number, { total: number; items: string[] }>) {
    plan.value = p
  }

  // UI 层临时标记，不持久化，刷新后消失
  const aiPrefilledFields = reactive<Record<string, boolean>>({})

  function markAiPrefilled(fieldPath: string) {
    aiPrefilledFields[fieldPath] = true
  }

  function markUserEdited(fieldPath: string) {
    delete aiPrefilledFields[fieldPath]
  }

  function isAiPrefilled(fieldPath: string): boolean {
    return fieldPath in aiPrefilledFields
  }

  const canProceed = computed(() => {
    if (currentStep.value === 1) return scene.value.name.trim().length > 0
    if (currentStep.value === 2) return inputs.value.length > 0
    if (currentStep.value === 3) {
      return processors.value.length > 0
        && processors.value.every(p => {
          const hasCode = p.plugin === 'sql' ? p.sql.trim().length > 0 : p.script.trim().length > 0
          return hasCode && p.outputTables.length > 0
        })
    }
    if (currentStep.value === 4) return output.value.config?.sourceTable && output.value.config?.columns?.length > 0
    return true
  })

  const stepValidation = computed(() => {
    const msgs: string[] = []
    if (currentStep.value === 1 && !scene.value.name.trim()) msgs.push('场景名称不能为空')
    if (currentStep.value === 2 && inputs.value.length === 0) msgs.push('至少需要 1 个输入源')
    if (currentStep.value === 3) {
      if (processors.value.length === 0) msgs.push('至少需要 1 个处理步骤')
      processors.value.forEach((p, i) => {
        const codeEmpty = p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()
        if (codeEmpty) msgs.push(`步骤 ${i + 1}: 代码不能为空`)
        if (p.outputTables.length === 0) msgs.push(`步骤 ${i + 1}: 输出表名不能为空`)
      })
    }
    if (currentStep.value === 4 && !output.value.config?.sourceTable) msgs.push('请选择数据源表')
    if (currentStep.value === 4 && output.value.config?.columns?.length === 0) msgs.push('尚未配置列映射')
    return msgs
  })

  function nextStep() { if (canProceed.value && currentStep.value < 5) currentStep.value++ }
  function prevStep() { if (currentStep.value > 1) currentStep.value-- }
  function goToStep(n: number) { if (n >= 1 && n <= currentStep.value && n <= 5) currentStep.value = n }

  /** Go back to previous step and only clear the current step's data */
  function goBackToStep(fromStep: number) {
    const targetStep = fromStep - 1
    if (targetStep < 1 || targetStep > 5) return

    // Only clear the step being left, NOT downstream steps
    if (fromStep === 2) {
      inputs.value = []
      uploadedFiles.value = {}
    } else if (fromStep === 3) {
      processors.value = []
      output.value = null
    } else if (fromStep === 4) {
      output.value = null
    }
    // fromStep === 5: nothing to clear

    currentStep.value = targetStep
  }
  function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
    let config: { type: 'excel'; sheet: string } | { type: 'csv'; delimiter: string; encoding: string; hasHeader: boolean } | { type: 'database'; connectionId: string; queryType: 'table'; tables: string[]; sql: string }
    if (plugin === 'csv') {
      config = { type: 'csv' as const, delimiter: ',', encoding: 'utf-8', hasHeader: true }
    } else if (plugin === 'database') {
      config = { type: 'database' as const, connectionId: '', queryType: 'table' as const, tables: [], sql: '' }
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

  function setOutput(o: OutputTarget) { output.value = o }
  function addFileRef(fileId: string, meta: UploadedFileMeta) { uploadedFiles.value[fileId] = meta }
  function removeFileRef(fileId: string) { delete uploadedFiles.value[fileId] }
  function setSuggestion(category: string, s: AiSuggestion) { aiSuggestions.value[category] = s }
  function acceptSuggestion(category: string) { if (aiSuggestions.value[category]) aiSuggestions.value[category].status = 'accepted' }
  function rejectSuggestion(category: string) { if (aiSuggestions.value[category]) aiSuggestions.value[category].status = 'rejected' }
  function setConfigId(id: string | null) { configId.value = id }

  function resetAll() {
    currentStep.value = 1
    scene.value = { name: '', description: '', version: '1.0' }
    inputs.value = []
    processors.value = []
    output.value = null
    configId.value = null
    uploadedFiles.value = {}
    aiSuggestions.value = {}
  }

  function loadFromConfigState(stateDict: any) {
    scene.value = {
      name: stateDict.scene?.name || '',
      description: stateDict.scene?.description || '',
      version: stateDict.scene?.version || '1.0',
    }

    inputs.value = (stateDict.inputs || []).map((inp: any) => {
      const cfg = inp.config || {}
      if (cfg.type === 'csv' && cfg.has_header !== undefined) {
        cfg.hasHeader = cfg.has_header
        delete cfg.has_header
      } else if (cfg.type === 'database') {
        cfg.connectionId = cfg.connection_id || ''
        cfg.queryType = cfg.query_type || 'table'
        cfg.tables = cfg.tables || []
        cfg.sql = cfg.sql || ''
        delete cfg.connection_id
        delete cfg.query_type
      }
      return {
        plugin: inp.plugin || 'excel',
        table: inp.table || inp.name || '',
        paramKey: inp.param_key || '',
        fileId: '',
        config: cfg,
      }
    })

    // If stateDict has "processor" (singular, old format), wrap as [processor]
    const rawProcessors = stateDict.processors || (stateDict.processor ? [stateDict.processor] : [])
    processors.value = rawProcessors.map((raw: any) => {
      const plugin = raw.plugin || 'sql'
      const base = {
        name: raw.name || '',
        plugin,
        inputTables: raw.input_tables || raw.inputTables || [],
        outputTables: raw.output_tables || raw.outputTables || (raw.outputTable ? [raw.outputTable] : []),
        // CheckRule fields use snake_case matching backend, no camelCase conversion needed
        checkpoints: (raw.checkpoints || []).map((c: any) => ({ ...c, on_failure: c.on_failure || 'block' })),
      }
      if (plugin === 'python') {
        return { ...base, script: raw.config?.script || raw.script || '' } as ProcessorStep
      }
      return { ...base, sql: raw.config?.sql || raw.sql || '' } as ProcessorStep
    })

    if (stateDict.output) {
      const cfg = { ...stateDict.output.config }
      if (cfg.source_table) { cfg.sourceTable = cfg.source_table; delete cfg.source_table }
      if (cfg.output_dir) { cfg.outputDir = cfg.output_dir; delete cfg.output_dir }
      output.value = {
        plugin: stateDict.output.plugin || 'excel',
        config: cfg,
      }
    } else {
      output.value = null
    }

    currentStep.value = 5
  }

  function getWizardState(): WizardState {
    return {
      currentStep: currentStep.value,
      scene: scene.value,
      inputs: inputs.value,
      processors: processors.value.map(p => ({
        ...p,
        checkpoints: p.checkpoints || [],
      })),
      output: output.value,
      uploadedFiles: uploadedFiles.value,
      aiSuggestions: aiSuggestions.value,
    }
  }

  return {
    currentStep, scene, inputs, processors, output, uploadedFiles, aiSuggestions, configId,
    canProceed, stepValidation,
    nextStep, prevStep, goToStep, goBackToStep,
    addInput, removeInput, updateInput,
    addProcessor, removeProcessor, updateProcessor, setProcessors, setOutput,
    addFileRef, removeFileRef,
    setSuggestion, acceptSuggestion, rejectSuggestion,
    setConfigId, loadFromConfigState, resetAll, getWizardState,
    aiPrefilledFields, markAiPrefilled, markUserEdited, isAiPrefilled,
    plan, setPlan
  }
}, {
  persist: { key: 'wizard_state_v2', storage: localStorage }
})
