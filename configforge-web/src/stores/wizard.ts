import { defineStore, storeToRefs } from 'pinia'
import { ref } from 'vue'
import type { AiSuggestion, WizardState } from '../types/wizard'
import { snakeToCamel } from '../utils/transform'
import { useWizardSceneStore } from './wizardScene'
import { useWizardInputsStore } from './wizardInputs'
import { useWizardProcessorsStore } from './wizardProcessors'
import { useWizardOutputStore } from './wizardOutput'

export const useWizardStore = defineStore('wizard', () => {
  // Sub-stores
  const sceneStore = useWizardSceneStore()
  const inputsStore = useWizardInputsStore()
  const processorsStore = useWizardProcessorsStore()
  const outputStore = useWizardOutputStore()

  // Re-expose sub-store state as refs for unified API
  const { scene } = storeToRefs(sceneStore)
  const { inputs, uploadedFiles } = storeToRefs(inputsStore)
  const { processors } = storeToRefs(processorsStore)
  const { output } = storeToRefs(outputStore)

  // Main store's own state
  const currentStep = ref(1)
  const configId = ref<string | null>(null)
  const aiSuggestions = ref<Record<string, AiSuggestion>>({})

  // Dry-run 预览结果
  const dryRunResults = ref<{ table_name: string; columns: string[]; rows: string[][]; total_rows: number }[] | null>(null)

  // Pending autofixes to apply when navigating to wizard
  const pendingAutofixes = ref<{ step: number; field: string; old: string; new: string; reason: string }[]>([])

  function setDryRunResults(results: { table_name: string; columns: string[]; rows: string[][]; total_rows: number }[] | null) {
    dryRunResults.value = results
  }

  /**
   * Apply autofix results to the wizard store.
   * Maps AI-returned field names to store paths using FIELD_STORE_MAP.
   */
  function applyAutofixes(fixes: { step: number; field: string; old: string; new: string; reason: string }[]) {
    let applied = 0
    for (const fix of fixes) {
      const field = fix.field.toLowerCase()
      if (field === 'sql' && fix.step === 3) {
        // Apply to the first SQL processor
        const proc = processors.value.find(p => p.plugin === 'sql')
        if (proc && proc.sql.includes(fix.old)) {
          proc.sql = proc.sql.replace(fix.old, fix.new)
          applied++
        } else if (proc) {
          proc.sql = fix.new
          applied++
        }
      } else if (field === 'script' && fix.step === 3) {
        const proc = processors.value.find(p => p.plugin === 'python')
        if (proc && proc.script.includes(fix.old)) {
          proc.script = proc.script.replace(fix.old, fix.new)
          applied++
        } else if (proc) {
          proc.script = fix.new
          applied++
        }
      } else if (field === 'path' && fix.step === 2) {
        const inp = inputs.value[0]
        if (inp && inp.config.type === 'excel' && inp.config.path !== undefined) {
          inp.config.path = fix.new
          applied++
        }
      } else if (field === 'table' && fix.step === 2) {
        const inp = inputs.value[0]
        if (inp) {
          inp.table = fix.new
          applied++
        }
      }
      // Unsupported fields are skipped; user will be prompted to manually fix
    }
    return applied
  }

  function canProceed(n: number): boolean {
    if (n === 1) return scene.value.name.trim().length > 0
    if (n === 2) return inputs.value.length > 0 && inputs.value.every(inp => {
      const hasFile = inp.plugin === 'database' || !!inp.fileId
      return hasFile && inp.table.trim().length > 0
    })
    if (n === 3) {
      return processors.value.length > 0
        && processors.value.every(p => {
          const hasCode = p.plugin === 'sql' ? p.sql.trim().length > 0 : p.script.trim().length > 0
          return hasCode && p.outputTables.length > 0
        })
    }
    if (n === 4) return !!output.value && !!output.value.config?.sourceTable && (output.value.config?.columns?.length ?? 0) > 0
    return true
  }

  function stepValidation(n: number): string[] {
    const msgs: string[] = []
    if (n === 1 && !scene.value.name.trim()) msgs.push('请输入场景名称')
    if (n === 2) {
      if (inputs.value.length === 0) msgs.push('至少需要添加 1 个输入源')
      if (inputs.value.some(inp => inp.plugin !== 'database' && !inp.fileId)) msgs.push('请为所有输入源上传文件')
      if (inputs.value.some(inp => !inp.table.trim())) msgs.push('请为所有输入源填写表名')
    }
    if (n === 3) {
      if (processors.value.length === 0) msgs.push('至少需要 1 个处理步骤')
      processors.value.forEach((p, i) => {
        const codeEmpty = p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()
        if (codeEmpty) msgs.push(`步骤 ${i + 1}: 代码不能为空`)
        if (p.outputTables.length === 0) msgs.push(`步骤 ${i + 1}: 输出表名不能为空`)
      })
    }
    if (n === 4) {
      if (!output.value) msgs.push('请选择输出格式')
      else {
        if (!output.value.config?.sourceTable) msgs.push('请选择数据源表')
        if ((output.value.config?.columns?.length ?? 0) === 0) msgs.push('请先配置列映射')
      }
    }
    return msgs
  }

  function goBackToStep(fromStep: number) {
    const targetStep = fromStep - 1
    if (targetStep < 1 || targetStep > 5) return
    if (fromStep === 2) { inputsStore.reset() }
    else if (fromStep === 3) { processorsStore.reset(); outputStore.reset() }
    else if (fromStep === 4) { outputStore.reset() }
    currentStep.value = targetStep
  }

  function nextStep() { if (canProceed(currentStep.value) && currentStep.value < 5) currentStep.value++ }
  function prevStep() { if (currentStep.value > 1) currentStep.value-- }
  function goToStep(n: number) { if (n >= 1 && n <= currentStep.value && n <= 5) currentStep.value = n }

  // Delegate to sub-stores
  function addInput(plugin: Parameters<typeof inputsStore.addInput>[0] = 'excel') { inputsStore.addInput(plugin) }
  function removeInput(index: number) { inputsStore.removeInput(index) }
  function updateInput(index: number, input: Parameters<typeof inputsStore.updateInput>[1]) { inputsStore.updateInput(index, input) }
  function addProcessor(plugin: 'sql' | 'python' = 'sql') { processorsStore.addProcessor(plugin) }
  function removeProcessor(index: number) { processorsStore.removeProcessor(index) }
  function updateProcessor(index: number, proc: Parameters<typeof processorsStore.updateProcessor>[1]) { processorsStore.updateProcessor(index, proc) }
  function setProcessors(newProcessors: Parameters<typeof processorsStore.setProcessors>[0]) { processorsStore.setProcessors(newProcessors) }
  function setOutput(o: Parameters<typeof outputStore.setOutput>[0]) { outputStore.setOutput(o) }
  function addFileRef(fileId: string, meta: Parameters<typeof inputsStore.addFileRef>[1]) { inputsStore.addFileRef(fileId, meta) }
  function removeFileRef(fileId: string) { inputsStore.removeFileRef(fileId) }

  function setSuggestion(category: string, s: AiSuggestion) { aiSuggestions.value[category] = s }
  function acceptSuggestion(category: string) { if (aiSuggestions.value[category]) aiSuggestions.value[category].status = 'accepted' }
  function rejectSuggestion(category: string) { if (aiSuggestions.value[category]) aiSuggestions.value[category].status = 'rejected' }
  function setConfigId(id: string | null) { configId.value = id }

  function resetAll() {
    currentStep.value = 1
    sceneStore.reset()
    inputsStore.reset()
    processorsStore.reset()
    outputStore.reset()
    configId.value = null
    aiSuggestions.value = {}
    dryRunResults.value = null
  }

  function loadFromConfigState(stateDict: Record<string, unknown>, startFromBeginning = false) {
    // Use snakeToCamel to normalize backend snake_case keys to frontend camelCase
    const normalized = snakeToCamel(stateDict) as Record<string, unknown>

    // Distribute data to sub-stores
    const sceneData = (normalized.scene || {}) as Record<string, unknown>
    sceneStore.loadScene({
      name: sceneData.name as string | undefined,
      description: sceneData.description as string | undefined,
      version: sceneData.version as string | undefined,
    })

    inputsStore.loadInputs((normalized.inputs || []) as Record<string, unknown>[])

    processorsStore.loadProcessors((normalized.processors || []) as Record<string, unknown>[])

    outputStore.loadOutput(normalized.output as Record<string, unknown> | null | undefined)

    currentStep.value = startFromBeginning ? 1 : 5
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
    // Sub-store state (re-exposed for unified API)
    scene, inputs, processors, output, uploadedFiles,
    // Main store state
    currentStep, configId, aiSuggestions, dryRunResults, pendingAutofixes,
    // Validation & navigation
    canProceed, stepValidation,
    nextStep, prevStep, goToStep, goBackToStep,
    // Sub-store method delegates
    addInput, removeInput, updateInput,
    addProcessor, removeProcessor, updateProcessor, setProcessors, setOutput,
    addFileRef, removeFileRef,
    // Main store methods
    setSuggestion, acceptSuggestion, rejectSuggestion,
    setConfigId, loadFromConfigState, resetAll, getWizardState,
    setDryRunResults, applyAutofixes
  }
}, {
  persist: { key: 'wizard_core_v1', storage: localStorage, paths: ['currentStep', 'configId', 'aiSuggestions', 'dryRunResults', 'pendingAutofixes'] }
})
