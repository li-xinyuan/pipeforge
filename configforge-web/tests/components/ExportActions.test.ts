import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const mockMessage = {
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}

const mockDialog = {
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}

vi.mock('naive-ui', () => ({
  NButton: {
    template: '<button @click="$emit(\'click\')"><slot /></button>',
    props: ['size', 'type', 'loading'],
    emits: ['click'],
  },
  useMessage: () => mockMessage,
  useDialog: () => mockDialog,
}))

vi.mock('../../src/composables/useWizardApi', () => ({
  useWizardApi: () => ({
    executePipeline: vi.fn(),
  }),
}))

describe('ExportActions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders four action buttons', async () => {
    const { default: ExportActions } = await import('../../src/components/step4/ExportActions.vue')
    const wrapper = mount(ExportActions, { global: { stubs: {} } })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(4)
    expect(buttons[0].text()).toBe('复制')
    expect(buttons[1].text()).toBe('下载 YAML')
    expect(buttons[2].text()).toBe('下载结果文件')
    expect(buttons[3].text()).toBe('保存配置')
  })

  it('copy button writes clipboard from yaml prop', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })

    const { default: ExportActions } = await import('../../src/components/step4/ExportActions.vue')
    const wrapper = mount(ExportActions, {
      props: { yaml: 'scene:\n  name: test' },
      global: { stubs: {} },
    })
    await wrapper.findAll('button')[0].trigger('click')

    expect(writeText).toHaveBeenCalledWith('scene:\n  name: test')
  })

  it('download YAML creates a blob from yaml prop and triggers download', async () => {
    const clickSpy = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreateElement(tag)
      if (tag === 'a') {
        Object.defineProperty(el, 'click', { value: clickSpy })
        let _href = ''
        Object.defineProperty(el, 'href', { get: () => _href, set: (v) => { _href = v } })
      }
      return el
    })

    const { default: ExportActions } = await import('../../src/components/step4/ExportActions.vue')
    const wrapper = mount(ExportActions, {
      props: { yaml: 'pipeline content' },
      global: { stubs: {} },
    })
    await wrapper.findAll('button')[1].trigger('click')

    expect(clickSpy).toHaveBeenCalled()
    vi.restoreAllMocks()
  })
})
