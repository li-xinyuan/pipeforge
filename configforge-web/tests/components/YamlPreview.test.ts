import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useWizardStore } from '../../src/stores/wizard'

// Single mock with controllable return value
const mockGenerateYaml = vi.fn()

vi.mock('../../src/composables/useWizardApi', () => ({
  useWizardApi: () => ({
    generateYaml: mockGenerateYaml,
  }),
}))

// Mock useMessage to avoid requiring <n-message-provider>
vi.mock('naive-ui', async () => {
  const actual = await vi.importActual('naive-ui')
  return {
    ...actual,
    useMessage: () => ({
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    }),
  }
})

// Stubs for Naive UI components used by YamlPreview
const stubs = {
  NButton: {
    template: '<button :disabled="disabled" :type="type"><slot /></button>',
    props: ['size', 'type', 'disabled'],
    emits: ['click'],
  },
  CodeEditor: {
    template: '<div class="code-editor-stub"><pre>{{ modelValue }}</pre></div>',
    props: ['modelValue', 'language', 'readOnly', 'minHeight', 'placeholder'],
    emits: ['update:modelValue'],
  },
}

describe('YamlPreview', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useWizardStore().scene.name = 'test'
    vi.clearAllMocks()
  })

  it('renders YAML content when loaded', async () => {
    mockGenerateYaml.mockResolvedValue({ yaml: 'scene:\n  name: test\ndescription: desc' })

    const { default: YamlPreview } = await import('../../src/components/step4/YamlPreview.vue')

    const wrapper = mount(YamlPreview, { global: { stubs } })

    // Wait for onMounted API call to resolve
    await new Promise(r => setTimeout(r, 100))
    await wrapper.vm.$nextTick()

    const editor = wrapper.find('.code-editor-stub')
    expect(editor.exists()).toBe(true)
    expect(editor.text()).toContain('scene:')
    expect(editor.text()).toContain('name: test')
  })

  it('exposes loadYaml method', async () => {
    mockGenerateYaml.mockResolvedValue({ yaml: 'processors:\n  - name: step1' })

    const { default: YamlPreview } = await import('../../src/components/step4/YamlPreview.vue')

    const wrapper = mount(YamlPreview, { global: { stubs } })

    await new Promise(r => setTimeout(r, 100))
    await wrapper.vm.$nextTick()

    const vm = wrapper.vm as any
    expect(typeof vm.loadYaml).toBe('function')
    const editor = wrapper.find('.code-editor-stub')
    expect(editor.text()).toContain('processors:')
  })
})
