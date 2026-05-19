import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AiChatPanel from '../../src/components/wizard/AiChatPanel.vue'

describe('AiChatPanel', () => {
  it('renders the AI panel title', () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: true },
    })
    expect(wrapper.text()).toContain('AI 助手')
  })

  it('renders messages correctly', () => {
    const messages = [
      { role: 'ai' as const, content: 'Hello, I am AI' },
      { role: 'user' as const, content: 'Help me' },
    ]
    const wrapper = mount(AiChatPanel, {
      props: { messages, quickActions: [], visible: true },
    })
    expect(wrapper.text()).toContain('Hello, I am AI')
    expect(wrapper.text()).toContain('Help me')
  })

  it('renders quick action buttons', () => {
    const actions = ['AI 生成 SQL', '自动添加列映射']
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: actions, visible: true },
    })
    expect(wrapper.text()).toContain('AI 生成 SQL')
    expect(wrapper.text()).toContain('自动添加列映射')
  })

  it('emits send when typing and clicking send', async () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: true },
    })
    const input = wrapper.find('input')
    await input.setValue('Generate SQL')
    await wrapper.find('.ai-panel__send-btn').trigger('click')
    expect(wrapper.emitted('send')).toBeTruthy()
    expect(wrapper.emitted('send')![0]).toEqual(['Generate SQL'])
  })

  it('emits quickAction when a quick action is clicked', async () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: ['AI 生成 SQL'], visible: true },
    })
    await wrapper.find('.ai-panel__quick-action').trigger('click')
    expect(wrapper.emitted('quickAction')).toBeTruthy()
    expect(wrapper.emitted('quickAction')![0]).toEqual(['AI 生成 SQL'])
  })

  it('hides when visible is false', () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: false },
    })
    expect(wrapper.find('.ai-panel').exists()).toBe(false)
  })

  it('emits toggle when collapse button is clicked', async () => {
    const wrapper = mount(AiChatPanel, {
      props: { messages: [], quickActions: [], visible: true },
    })
    await wrapper.find('.ai-panel__collapse').trigger('click')
    expect(wrapper.emitted('toggle')).toBeTruthy()
  })
})
