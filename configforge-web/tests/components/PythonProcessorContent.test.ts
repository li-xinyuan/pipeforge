import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NTag } from 'naive-ui'
import type { ProcessorStep } from '../../src/types/wizard'

/**
 * PythonProcessorContent 测试 — 限制①第三阶段迁移后更新。
 *
 * 迁移后 script 字段由 SchemaForm + code-editor 命名 widget 渲染，
 * 依赖 usePluginSchema 返回 python processor 的 schema。此处 mock
 * usePluginSchema 提供 script 字段 + x-ui-widget: 'code-editor' hint，
 * 使 SchemaForm 渲染 CodeEditorWidget → CodeEditor。
 *
 * vi.mock 被提升到文件顶部，factory 内不能引用外部变量。
 */
vi.mock('../../src/composables/usePluginSchema', () => ({
  usePluginSchema: () => ({
    getSchema: (plugin: string, type: string) => {
      if (plugin === 'python' && type === 'processor') {
        return {
          properties: {
            type: { const: 'python', default: 'python', type: 'string' },
            script: { type: 'string', default: '', 'x-ui-widget': 'code-editor' },
          },
        }
      }
      return undefined
    },
    load: vi.fn().mockResolvedValue([]),
    getSchemaAsync: vi.fn(),
    clearCache: vi.fn(),
  }),
}))

import PythonProcessorContent from '../../src/components/step3/PythonProcessorContent.vue'

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

  it('renders the Python script editor', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    // CodeEditor renders either CodeMirror or fallback textarea
    const editor = wrapper.findComponent({ name: 'CodeEditor' })
    expect(editor.exists()).toBe(true)
    expect(editor.props('modelValue')).toBe('def process(ctx):\n  pass')
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

  it('passes placeholder to CodeEditor when script is empty', () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc({ script: '' }), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    const editor = wrapper.findComponent({ name: 'CodeEditor' })
    expect(editor.props('placeholder')).toContain('def process(ctx)')
  })

  it('emits update when script changes via CodeEditor', async () => {
    const wrapper = mount(PythonProcessorContent, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      global: { plugins: [createPinia()] },
    })
    const editor = wrapper.findComponent({ name: 'CodeEditor' })
    editor.vm.$emit('update:modelValue', 'def process(ctx):\n  return 42')
    expect(wrapper.emitted('update')).toBeTruthy()
  })
})
