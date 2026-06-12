import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NTag } from 'naive-ui'
import ProcessorCard from '../../src/components/step3/ProcessorCard.vue'
import type { ProcessorStep } from '../../src/types/wizard'

// Mock fetch to prevent happy-dom from making real network requests
vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
  ok: true,
  json: () => Promise.resolve({}),
})))

// Mock composables used by SqlProcessorContent
vi.mock('../../src/composables/useWizardApi', () => ({
  useWizardApi: () => ({
    dryRun: vi.fn(() => Promise.resolve(null)),
    error: { value: null },
  }),
  useAiApi: () => ({
    suggesting: { value: false },
    aiError: { value: null },
    askSuggestion: vi.fn(),
    getAiSettings: vi.fn(() => Promise.resolve({ enabled: false, api_key: '' })),
  }),
}))

function createSqlProc(): ProcessorStep {
  return { name: 'SQL 查询', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['r1'], checkpoints: [] }
}

function createPythonProc(): ProcessorStep {
  return { name: 'Python 脚本', plugin: 'python', script: 'def process(ctx): pass', inputTables: [], outputTables: ['out'], checkpoints: [] }
}

describe('ProcessorCard', () => {
  const baseOptions = {
    global: {
      plugins: [createPinia()],
      stubs: {
        CheckpointSection: { template: '<div class="checkpoint-stub" />', props: ['checkpoints', 'procIndex'] },
        NPopconfirm: {
          template: '<div class="n-popconfirm-stub"><slot name="trigger" /><slot /></div>',
          emits: ['positive-click'],
        },
        SqlProcessorContent: {
          template: '<div class="sql-processor-stub" />',
          props: ['proc', 'index', 'availableTables', 'pulseSql'],
        },
        PythonProcessorContent: {
          template: '<div class="python-processor-stub" />',
          props: ['proc', 'index', 'availableTables'],
        },
      },
    },
  }

  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders SQL processor with SQL tag', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    const tags = wrapper.findAllComponents(NTag)
    const typeTag = tags.find(t => t.text() === 'SQL' || t.text() === 'Python')
    expect(typeTag?.text()).toBe('SQL')
  })

  it('renders Python processor with Python tag', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    const tags = wrapper.findAllComponents(NTag)
    const typeTag = tags.find(t => t.text() === 'SQL' || t.text() === 'Python')
    expect(typeTag?.text()).toBe('Python')
  })

  it('renders delete button', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    expect(wrapper.text()).toContain('删除')
  })

  it('renders processor name in header', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    expect(wrapper.text()).toContain('SQL 查询')
  })

  it('shows default step label when name is empty', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: { ...createSqlProc(), name: '' }, index: 2, availableTables: [] },
      ...baseOptions,
    })
    expect(wrapper.text()).toContain('步骤 3')
  })

  it('emits remove when delete is confirmed via NPopconfirm', async () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    // The NPopconfirm is stubbed but naive-ui registers it internally as 'Popconfirm'
    // Try both names
    let popconfirm = wrapper.findComponent({ name: 'NPopconfirm' })
    if (!popconfirm.exists()) {
      popconfirm = wrapper.findComponent({ name: 'Popconfirm' })
    }
    // If still not found by name, find by the stub's class
    if (!popconfirm.exists()) {
      const stubEl = wrapper.find('.n-popconfirm-stub')
      if (stubEl.exists()) {
        popconfirm = wrapper.findComponent(stubEl)
      }
    }
    expect(popconfirm.exists()).toBe(true)
    await popconfirm.vm.$emit('positive-click')
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('remove')).toBeTruthy()
  })
})
