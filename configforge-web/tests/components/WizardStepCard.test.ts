import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WizardStepCard from '../../src/components/wizard/WizardStepCard.vue'

describe('WizardStepCard', () => {
  it('renders title and description', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: '场景信息', description: '填写基本信息', icon: '🎨', status: 'active' },
    })
    expect(wrapper.text()).toContain('场景信息')
    expect(wrapper.text()).toContain('填写基本信息')
    expect(wrapper.text()).toContain('🎨')
  })

  it('renders slot content', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'active' },
      slots: { default: '<p class="slot-content">Hello world</p>' },
    })
    expect(wrapper.find('.slot-content').exists()).toBe(true)
  })

  it('applies active border class when status is active', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'active' },
    })
    expect(wrapper.find('.wizard-step-card').classes()).toContain('wizard-step-card--active')
  })

  it('applies locked opacity when status is locked', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'locked' },
    })
    expect(wrapper.find('.wizard-step-card').classes()).toContain('wizard-step-card--locked')
  })

  it('shows status badge text', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'completed', badge: '✓ 已完成' },
    })
    expect(wrapper.text()).toContain('✓ 已完成')
  })

  it('renders footer slot', () => {
    const wrapper = mount(WizardStepCard, {
      props: { title: 'Test', description: 'Desc', icon: '📂', status: 'active' },
      slots: { footer: '<button class="footer-btn">下一步</button>' },
    })
    expect(wrapper.find('.footer-btn').exists()).toBe(true)
  })
})
