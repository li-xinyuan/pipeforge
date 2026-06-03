import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NInput, NTag, NButton, NSelect } from 'naive-ui'
import PythonProcessorContent from '../../src/components/step3/PythonProcessorContent.vue'
import type { ProcessorStep } from '../../src/types/wizard'

function createPythonProc(overrides: Partial<Extract<ProcessorStep, { plugin: 'python' }>> = {}): Extract<ProcessorStep, { plugin: 'python' }> {
  return {
    name: 'test python',
    plugin: 'python',
    script: 'def process(ctx):\n  pass',
    inputTables: [],
    outputTables: ['out'],
    ...overrides,
  } as Extract<ProcessorStep, { plugin: 'python' }>
}

describe('PythonProcessorContent', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders step name input', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.text()).toContain('步骤名称')
  })

  it('renders the Python script textarea', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    const textarea = wrapper.find('textarea')
    expect(textarea.exists()).toBe(true)
    expect(textarea.element.value).toBe('def process(ctx):\n  pass')
  })

  it('renders output table input', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.text()).toContain('输出表名')
  })

  it('renders quick template tags', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    const tags = wrapper.findAllComponents(NTag)
    expect(tags.length).toBeGreaterThanOrEqual(4) // clean, filter, aggregate, api
  })

  it('renders preview button', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.text()).toContain('预览结果')
  })

  it('shows script placeholder when empty', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc({ script: '' }), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    const textarea = wrapper.find('textarea')
    expect(textarea.element.placeholder).toContain('def process(ctx)')
  })

  it('emits update when textarea changes', async () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('def process(ctx):\n  return 42')
    expect(wrapper.emitted('update')).toBeTruthy()
  })
})
