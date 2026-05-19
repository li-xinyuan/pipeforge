import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SceneInfo, InputSource, ProcessorConfig, OutputTarget, UploadedFileMeta, AiSuggestion } from '../types/wizard'

export const useWizardStore = defineStore('wizard', () => {
  const currentStep = ref(1)
  const scene = ref<SceneInfo>({ name: '', description: '', version: '1.0' })
  const inputs = ref<InputSource[]>([])
  const processor = ref<ProcessorConfig>({ plugin: 'sql', sql: '', outputTable: '' })
  const output = ref<OutputTarget>({ plugin: 'excel', config: { type: 'excel', template: '', sheet: 'Sheet1', outputDir: './output/', sourceTable: '', filename: 'output.xlsx', columns: [] } })
  const configId = ref<string | null>(null)
  const uploadedFiles = ref<Record<string, UploadedFileMeta>>({})
  const aiSuggestions = ref<Record<string, AiSuggestion>>({})

  const canProceed = computed(() => {
    if (currentStep.value === 1) return scene.value.name.trim().length > 0
    if (currentStep.value === 2) return inputs.value.length > 0
    if (currentStep.value === 3) return processor.value.sql.trim().length > 0 && processor.value.outputTable.trim().length > 0
    if (currentStep.value === 4) return (output.value.config as any)?.sourceTable && (output.value.config as any)?.columns?.length > 0
    return true
  })

  const stepValidation = computed(() => {
    const msgs: string[] = []
    if (currentStep.value === 1 && !scene.value.name.trim()) msgs.push('场景名称不能为空')
    if (currentStep.value === 2 && inputs.value.length === 0) msgs.push('至少需要 1 个输入源')
    if (currentStep.value === 3 && !processor.value.sql.trim()) msgs.push('SQL 不能为空')
    if (currentStep.value === 3 && !processor.value.outputTable.trim()) msgs.push('输出表名不能为空')
    if (currentStep.value === 4 && !(output.value.config as any)?.sourceTable) msgs.push('请选择数据源表')
    if (currentStep.value === 4 && (output.value.config as any)?.columns?.length === 0) msgs.push('尚未配置列映射')
    return msgs
  })

  function nextStep() { if (canProceed.value && currentStep.value < 5) currentStep.value++ }
  function prevStep() { if (currentStep.value > 1) currentStep.value-- }
  function goToStep(n: number) { if (n >= 1 && n <= currentStep.value && n <= 5) currentStep.value = n }
  function addInput(plugin: 'excel' | 'csv' = 'excel') {
    const config = plugin === 'csv'
      ? { type: 'csv' as const, delimiter: ',', encoding: 'utf-8', hasHeader: true }
      : { type: 'excel' as const, sheet: '' }

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
  function setProcessor(p: ProcessorConfig) { processor.value = p }
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
    processor.value = { plugin: 'sql', sql: '', outputTable: '' }
    output.value = { plugin: 'excel', config: { type: 'excel', template: '', sheet: 'Sheet1', outputDir: './output/', sourceTable: '', filename: 'output.xlsx', columns: [] } }
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
      }
      return {
        plugin: inp.plugin || 'excel',
        table: inp.table || inp.name || '',
        paramKey: inp.param_key || '',
        fileId: '',
        config: cfg,
      }
    })

    processor.value = {
      plugin: stateDict.processor?.plugin || 'sql',
      sql: stateDict.processor?.sql || '',
      outputTable: (stateDict.processor?.output_tables || [])[0] || '',
    }

    if (stateDict.output) {
      const cfg = { ...stateDict.output.config }
      if (cfg.source_table) { cfg.sourceTable = cfg.source_table; delete cfg.source_table }
      if (cfg.output_dir) { cfg.outputDir = cfg.output_dir; delete cfg.output_dir }
      output.value = {
        plugin: stateDict.output.plugin || 'excel',
        config: cfg,
      }
    } else {
      output.value = { plugin: 'excel', config: { type: 'excel', template: '', sheet: 'Sheet1', outputDir: './output/', sourceTable: '', filename: 'output.xlsx', columns: [] } }
    }

    currentStep.value = 5
  }

  return {
    currentStep, scene, inputs, processor, output, uploadedFiles, aiSuggestions, configId,
    canProceed, stepValidation,
    nextStep, prevStep, goToStep,
    addInput, removeInput, updateInput,
    setProcessor, setOutput,
    addFileRef, removeFileRef,
    setSuggestion, acceptSuggestion, rejectSuggestion,
    setConfigId, loadFromConfigState, resetAll
  }
}, {
  persist: { key: 'wizard_state_v1', storage: localStorage }
})
