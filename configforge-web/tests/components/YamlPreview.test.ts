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

// Stubs for Naive UI components used by YamlPreview
const stubs = {
  NCode: {
    template: '<pre><code>{{ code }}</code></pre>',
    props: ['code', 'language', 'wordWrap'],
  },
  NSkeleton: { template: '<div class="skeleton" />', props: ['text', 'repeat'] },
  NAlert: { template: '<div class="alert">{{ title }}</div>', props: ['type', 'title'] },
}

describe('YamlPreview', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useWizardStore().scene.name = 'test'
    vi.clearAllMocks()
  })

  it('renders NCode when yaml is loaded', async () => {
    mockGenerateYaml.mockResolvedValue({ yaml: 'scene:\n  name: test\ndescription: desc' })

    const { default: YamlPreview } = await import('../../src/components/step4/YamlPreview.vue')

    const wrapper = mount(YamlPreview, { global: { stubs } })

    // Wait for onMounted API call to resolve
    await new Promise(r => setTimeout(r, 100))
    await wrapper.vm.$nextTick()

    const code = wrapper.find('code')
    expect(code.exists()).toBe(true)
    expect(code.text()).toContain('scene:')
    expect(code.text()).toContain('name: test')
  })

  it('exposes loadYaml method', async () => {
    mockGenerateYaml.mockResolvedValue({ yaml: 'processors:\n  - name: step1' })

    const { default: YamlPreview } = await import('../../src/components/step4/YamlPreview.vue')

    const wrapper = mount(YamlPreview, { global: { stubs } })

    await new Promise(r => setTimeout(r, 100))
    await wrapper.vm.$nextTick()

    const vm = wrapper.vm as any
    expect(typeof vm.loadYaml).toBe('function')
    expect(wrapper.find('code').text()).toContain('processors:')
  })
})
