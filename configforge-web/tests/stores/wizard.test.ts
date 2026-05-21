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

  it('addInput(\'database\') creates database input source', () => {
    const store = useWizardStore()
    store.addInput('database')
    expect(store.inputs).toHaveLength(1)
    const inp = store.inputs[0]
    expect(inp.plugin).toBe('database')
    expect(inp.config.type).toBe('database')
    expect(inp.config.connectionId).toBe('')
    expect(inp.config.queryType).toBe('table')
    expect(inp.config.tables).toEqual([])
    expect(inp.config.sql).toBe('')
  })

  it('loadFromConfigState deserializes database config', () => {
    const store = useWizardStore()
    store.loadFromConfigState({
      scene: { name: 'test' },
      inputs: [{
        plugin: 'database',
        table: 'users',
        param_key: 'db_param',
        config: {
          type: 'database',
          connection_id: 'conn-123',
          query_type: 'sql',
          tables: ['users'],
          sql: 'SELECT * FROM users',
        },
      }],
      processor: { plugin: 'sql', sql: 'SELECT 1', output_tables: ['out'] },
    })
    expect(store.inputs).toHaveLength(1)
    const inp = store.inputs[0]
    expect(inp.plugin).toBe('database')
    expect(inp.config.type).toBe('database')
    expect(inp.config.connectionId).toBe('conn-123')
    expect(inp.config.queryType).toBe('sql')
    expect(inp.config.tables).toEqual(['users'])
    expect(inp.config.sql).toBe('SELECT * FROM users')
  })

  it('loadFromConfigState handles database config with missing fields', () => {
    const store = useWizardStore()
    store.loadFromConfigState({
      scene: { name: 'test' },
      inputs: [{
        plugin: 'database',
        table: 't1',
        param_key: 'p1',
        config: { type: 'database' },
      }],
      processor: { plugin: 'sql', sql: '', output_tables: [] },
    })
    const inp = store.inputs[0]
    expect(inp.config.connectionId).toBe('')
    expect(inp.config.queryType).toBe('table')
    expect(inp.config.tables).toEqual([])
    expect(inp.config.sql).toBe('')
  })
})
