import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WizardProgress from '../../src/components/wizard/WizardProgress.vue'

const steps = [
  { label: '场景', status: 'completed' as const },
  { label: '数据源', status: 'active' as const },
  { label: '处理', status: 'locked' as const },
  { label: '输出', status: 'locked' as const },
  { label: '导出', status: 'locked' as const },
]

describe('WizardProgress', () => {
  it('renders all 5 steps', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const items = wrapper.findAll('[data-step]')
    expect(items).toHaveLength(5)
  })

  it('shows step numbers', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('2')
  })

  it('renders connector lines between steps', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const connectors = wrapper.findAll('.wizard-progress__connector')
    expect(connectors).toHaveLength(4)
  })

  it('emits stepClick with correct index when a completed step is clicked', async () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    await wrapper.find('[data-step="1"]').trigger('click')
    expect(wrapper.emitted('stepClick')).toBeTruthy()
    expect(wrapper.emitted('stepClick')![0]).toEqual([1])
  })

  it('does not emit stepClick when a locked step is clicked', async () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    await wrapper.find('[data-step="3"]').trigger('click')
    expect(wrapper.emitted('stepClick')).toBeFalsy()
  })

  it('applies active class to the active step', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const active = wrapper.find('[data-step="2"]')
    expect(active.classes()).toContain('wizard-progress__step--active')
  })

  it('applies completed class to the completed step', () => {
    const wrapper = mount(WizardProgress, { props: { steps } })
    const completed = wrapper.find('[data-step="1"]')
    expect(completed.classes()).toContain('wizard-progress__step--completed')
  })
})
