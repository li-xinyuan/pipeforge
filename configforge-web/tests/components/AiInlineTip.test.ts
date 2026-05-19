import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AiInlineTip from '../../src/components/wizard/AiInlineTip.vue'

describe('AiInlineTip', () => {
  it('renders the message text', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'AI has analyzed your data' },
    })
    expect(wrapper.text()).toContain('AI has analyzed your data')
  })

  it('shows the lightning emoji by default', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test' },
    })
    expect(wrapper.text()).toContain('⚡')
  })

  it('renders action button when actionLabel and showAction are provided', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test', showAction: true, actionLabel: 'Apply' },
    })
    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.find('button').text()).toBe('Apply →')
  })

  it('does not render action button when showAction is false', () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test', showAction: false },
    })
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('emits action event when button is clicked', async () => {
    const wrapper = mount(AiInlineTip, {
      props: { message: 'Test', showAction: true, actionLabel: 'Apply' },
    })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
  })
})
