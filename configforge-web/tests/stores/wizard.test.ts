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
    expect(store.canProceed(1)).toBe(false)
  })

  it('canProceed is true when scene name is set', () => {
    const store = useWizardStore()
    store.scene.name = '测试场景'
    expect(store.canProceed(1)).toBe(true)
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

  it('starts with empty processors array', () => {
    const store = useWizardStore()
    expect(store.processors).toHaveLength(0)
  })

  it('addProcessor adds a new processor', () => {
    const store = useWizardStore()
    store.addProcessor()
    expect(store.processors).toHaveLength(1)
  })

  it('removeProcessor removes by index', () => {
    const store = useWizardStore()
    store.addProcessor()
    store.addProcessor()
    expect(store.processors).toHaveLength(2)
    store.removeProcessor(1)
    expect(store.processors).toHaveLength(1)
  })

  it('removeProcessor can remove last processor', () => {
    const store = useWizardStore()
    store.addProcessor()
    expect(store.processors).toHaveLength(1)
    store.removeProcessor(0)
    expect(store.processors).toHaveLength(0)
  })

  it('updateProcessor updates processor at index', () => {
    const store = useWizardStore()
    store.addProcessor()
    store.updateProcessor(0, { name: 'step1', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['t1'] })
    expect(store.processors[0].sql).toBe('SELECT 1')
    expect(store.processors[0].outputTables).toEqual(['t1'])
  })

  it('loadFromConfigState upgrades old single processor format', () => {
    const store = useWizardStore()
    store.loadFromConfigState({
      scene: { name: 'test' },
      inputs: [],
      processor: { plugin: 'sql', sql: 'SELECT 1', outputTable: 'result' },
      output: null,
    })
    expect(store.processors).toHaveLength(1)
    expect(store.processors[0].sql).toBe('SELECT 1')
  })

  it('loadFromConfigState upgrades old single processor format with output_tables', () => {
    const store = useWizardStore()
    store.loadFromConfigState({
      scene: { name: 'test' },
      inputs: [],
      processor: { plugin: 'sql', sql: 'SELECT 1', output_tables: ['result'] },
      output: null,
    })
    expect(store.processors).toHaveLength(1)
    expect(store.processors[0].sql).toBe('SELECT 1')
    expect(store.processors[0].outputTables).toEqual(['result'])
  })

  it('loadFromConfigState loads processors array format', () => {
    const store = useWizardStore()
    store.loadFromConfigState({
      scene: { name: 'test' },
      inputs: [],
      processors: [
        { name: 'step1', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['t1'] },
        { name: 'step2', plugin: 'sql', sql: 'SELECT 2', inputTables: ['t1'], outputTables: ['t2'] },
      ],
      output: null,
    })
    expect(store.processors).toHaveLength(2)
    expect(store.processors[0].sql).toBe('SELECT 1')
    expect(store.processors[1].sql).toBe('SELECT 2')
    expect(store.processors[1].inputTables).toEqual(['t1'])
  })

  it('canProceed requires all processors to have sql and outputTables', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: '', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['t1'] },
      { name: '', plugin: 'sql', sql: '', inputTables: [], outputTables: ['t2'] },
    ]
    expect(store.canProceed(3)).toBe(false)
  })

  it('canProceed is true when all processors have sql and outputTables at step 3', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: '', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['t1'] },
      { name: '', plugin: 'sql', sql: 'SELECT 2', inputTables: ['t1'], outputTables: ['t2'] },
    ]
    expect(store.canProceed(3)).toBe(true)
  })

  it('stepValidation reports errors for empty processors array', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = []
    expect(store.stepValidation(3)).toContain('至少需要 1 个处理步骤')
  })

  it('stepValidation reports per-step errors', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: '', plugin: 'sql', sql: '', inputTables: [], outputTables: [] },
      { name: '', plugin: 'sql', sql: 'SELECT 2', inputTables: [], outputTables: [] },
    ]
    const msgs = store.stepValidation(3)
    expect(msgs).toContain('步骤 1: 代码不能为空')
    expect(msgs).toContain('步骤 1: 输出表名不能为空')
    expect(msgs).toContain('步骤 2: 输出表名不能为空')
  })

  it('getWizardState returns processors field', () => {
    const store = useWizardStore()
    store.processors = [
      { name: 'p1', plugin: 'sql', sql: 'SELECT 1', inputTables: ['a'], outputTables: ['b'] },
    ]
    const state = store.getWizardState()
    expect(state.processors).toHaveLength(1)
    expect(state.processors[0].sql).toBe('SELECT 1')
  })

  // Python processor tests
  it('addProcessor(\'python\') creates a Python processor', () => {
    const store = useWizardStore()
    store.addProcessor('python')
    expect(store.processors).toHaveLength(1)
    expect(store.processors[0].plugin).toBe('python')
    expect(store.processors[0].script).toBe('')
    expect(store.processors[0].outputTables).toEqual([])
  })

  it('updateProcessor updates Python processor script', () => {
    const store = useWizardStore()
    store.addProcessor('python')
    store.updateProcessor(0, { name: 'py_step', plugin: 'python', script: 'def process(ctx): pass', inputTables: ['t1'], outputTables: ['out'] } as any)
    expect(store.processors[0].script).toBe('def process(ctx): pass')
    expect(store.processors[0].name).toBe('py_step')
  })

  it('canProceed requires Python script to be non-empty', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: 'p1', plugin: 'python', script: '', inputTables: [], outputTables: ['out'] },
    ]
    expect(store.canProceed(3)).toBe(false)
  })

  it('canProceed is true when Python script and outputTables are set', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: 'p1', plugin: 'python', script: 'def process(ctx): pass', inputTables: ['t1'], outputTables: ['out'] },
    ]
    expect(store.canProceed(3)).toBe(true)
  })

  it('stepValidation reports Python script empty error', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: '', plugin: 'python', script: '', inputTables: [], outputTables: [] },
    ]
    const msgs = store.stepValidation(3)
    expect(msgs).toContain('步骤 1: 代码不能为空')
  })

  it('stepValidation reports Python output table empty error', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: '', plugin: 'python', script: 'def process(ctx): pass', inputTables: [], outputTables: [] },
    ]
    const msgs = store.stepValidation(3)
    expect(msgs).toContain('步骤 1: 输出表名不能为空')
  })

  it('loadFromConfigState handles Python processor format', () => {
    const store = useWizardStore()
    store.loadFromConfigState({
      scene: { name: 'test' },
      inputs: [],
      processors: [
        { name: 'py1', plugin: 'python', script: 'def process(ctx):\n  pass', input_tables: ['a'], output_tables: ['b'] },
      ],
      output: null,
    })
    expect(store.processors).toHaveLength(1)
    expect(store.processors[0].plugin).toBe('python')
    expect(store.processors[0].script).toBe('def process(ctx):\n  pass')
    expect(store.processors[0].outputTables).toEqual(['b'])
  })

  it('getWizardState includes Python processor script', () => {
    const store = useWizardStore()
    store.processors = [
      { name: 'p1', plugin: 'python', script: 'def process(ctx): return 1', inputTables: ['a'], outputTables: ['b'] },
    ]
    const state = store.getWizardState()
    expect(state.processors).toHaveLength(1)
    expect(state.processors[0].script).toBe('def process(ctx): return 1')
  })

  it('can handle mixed SQL and Python processors', () => {
    const store = useWizardStore()
    store.currentStep = 3
    store.processors = [
      { name: 'sql_step', plugin: 'sql', sql: 'SELECT 1', inputTables: ['t1'], outputTables: ['r1'] },
      { name: 'py_step', plugin: 'python', script: 'def process(ctx): pass', inputTables: ['r1'], outputTables: ['r2'] },
    ]
    expect(store.canProceed(3)).toBe(true)
    expect(store.stepValidation(3)).toEqual([])
    const state = store.getWizardState()
    expect(state.processors[0].sql).toBe('SELECT 1')
    expect(state.processors[1].script).toBe('def process(ctx): pass')
  })
})
