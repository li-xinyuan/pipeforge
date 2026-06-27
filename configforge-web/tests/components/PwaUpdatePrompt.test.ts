import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PwaUpdatePrompt from '../../src/components/common/PwaUpdatePrompt.vue'
import { usePwa } from '../../src/composables/usePwa'

// usePwa is a module-level singleton with reactive refs.
// We can manipulate needRefresh directly via the composable.
const { needRefresh } = usePwa()

describe('PwaUpdatePrompt', () => {
  beforeEach(() => {
    needRefresh.value = false
  })

  it('does not render when needRefresh is false', async () => {
    const wrapper = mount(PwaUpdatePrompt, {
      global: { stubs: { NButton: { template: '<button><slot /></button>' } } },
    })
    await flushPromises()
    expect(wrapper.find('.pwa-prompt').exists()).toBe(false)
  })

  it('renders update prompt when needRefresh is true', async () => {
    needRefresh.value = true
    const wrapper = mount(PwaUpdatePrompt, {
      global: { stubs: { NButton: { template: '<button><slot /></button>' } } },
    })
    await flushPromises()
    expect(wrapper.find('.pwa-prompt').exists()).toBe(true)
    expect(wrapper.text()).toContain('发现新版本')
    expect(wrapper.text()).toContain('立即刷新')
    expect(wrapper.text()).toContain('稍后')
  })

  it('hides prompt when later button is clicked', async () => {
    needRefresh.value = true
    const wrapper = mount(PwaUpdatePrompt, {
      global: { stubs: { NButton: { template: '<button><slot /></button>' } } },
    })
    await flushPromises()
    expect(wrapper.find('.pwa-prompt').exists()).toBe(true)

    // Click the "Later" button (first button)
    const buttons = wrapper.findAll('button')
    await buttons[0].trigger('click')
    await flushPromises()

    expect(needRefresh.value).toBe(false)
  })
})
