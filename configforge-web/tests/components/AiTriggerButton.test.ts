import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AiTriggerButton from '../../src/components/common/AiTriggerButton.vue'

// Mock useTheme
vi.mock('../../src/composables/useTheme', () => ({
  useTheme: () => ({ isDark: { value: false }, toggleTheme: vi.fn() }),
}))

const makeWrapper = (props = {}) =>
  mount(AiTriggerButton, {
    props: { label: 'AI 分析', ...props },
  })

describe('AiTriggerButton', () => {
  it('renders label text', () => {
    const wrapper = makeWrapper({ label: 'AI 分析此文件' })
    expect(wrapper.text()).toContain('AI 分析此文件')
  })

  it('renders sparkles icon', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('✨')
  })

  it('shows loading text when loading', () => {
    const wrapper = makeWrapper({ loading: true })
    expect(wrapper.text()).toContain('AI 思考中...')
    expect(wrapper.text()).not.toContain('AI 分析')
  })

  it('adds loading style when loading', () => {
    const wrapper = makeWrapper({ loading: true })
    const btn = wrapper.find('button')
    expect(btn.element.disabled).toBe(true)
    expect(btn.attributes('style')).toContain('opacity')
  })

  it('is disabled when disabled prop is true', () => {
    const wrapper = makeWrapper({ disabled: true })
    expect(wrapper.find('button').element.disabled).toBe(true)
  })

  it('is disabled when loading', () => {
    const wrapper = makeWrapper({ loading: true })
    expect(wrapper.find('button').element.disabled).toBe(true)
  })

  it('emits click event when clicked', async () => {
    const wrapper = makeWrapper()
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('does not emit click when disabled', async () => {
    const wrapper = makeWrapper({ disabled: true })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('click')).toBeUndefined()
  })

  it('uses ai-btn class', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('button').classes()).toContain('ai-btn')
  })

  it('shows sparkles icon when loading', () => {
    const wrapper = makeWrapper({ loading: true })
    expect(wrapper.text()).toContain('✨')
  })
})
