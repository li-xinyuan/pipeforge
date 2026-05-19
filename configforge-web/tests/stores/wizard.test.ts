import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWizardStore } from '../../src/stores/wizard'

describe('useWizardStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts at step 1', () => {
    const store = useWizardStore()
    expect(store.currentStep).toBe(1)
  })

  it('canProceed is false when scene name is empty', () => {
    const store = useWizardStore()
    store.scene.name = ''
    expect(store.canProceed).toBe(false)
  })

  it('canProceed is true when scene name is set', () => {
    const store = useWizardStore()
    store.scene.name = '测试场景'
    expect(store.canProceed).toBe(true)
  })

  it('nextStep advances step', () => {
    const store = useWizardStore()
    store.scene.name = '测试'
    store.nextStep()
    expect(store.currentStep).toBe(2)
  })

  it('goToStep navigates to completed step', () => {
    const store = useWizardStore()
    store.scene.name = '测试'
    store.nextStep() // 1->2
    store.nextStep() // 2->3
    store.goToStep(1)
    expect(store.currentStep).toBe(1)
  })

  it('addInput adds to inputs array', () => {
    const store = useWizardStore()
    store.addInput()
    expect(store.inputs).toHaveLength(1)
  })

  it('removeInput removes by index', () => {
    const store = useWizardStore()
    store.addInput()
    store.removeInput(0)
    expect(store.inputs).toHaveLength(0)
  })
})
