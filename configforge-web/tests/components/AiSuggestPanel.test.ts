import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AiSuggestPanel from '../../src/components/common/AiSuggestPanel.vue'

// Mock DOMPurify to pass through content (simplifies testing)
vi.mock('dompurify', () => ({
  default: { sanitize: (str: string) => str },
  sanitize: (str: string) => str,
}))

const makeWrapper = (props = {}) =>
  mount(AiSuggestPanel, {
    props: { visible: true, content: '建议内容', ...props },
  })

describe('AiSuggestPanel', () => {
  it('renders when visible is true', () => {
    const wrapper = makeWrapper({ visible: true })
    expect(wrapper.find('div').exists()).toBe(true)
  })

  it('does not render when visible is false', () => {
    const wrapper = makeWrapper({ visible: false })
    expect(wrapper.find('div').exists()).toBe(false)
  })

  it('displays AI suggestion header', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('AI 建议')
  })

  it('renders content text', () => {
    const wrapper = makeWrapper({ content: '使用 SELECT * FROM table' })
    expect(wrapper.text()).toContain('使用 SELECT * FROM table')
  })

  it('emits accept when accept button is clicked', async () => {
    const wrapper = makeWrapper()
    const buttons = wrapper.findAll('button')
    const acceptBtn = buttons.find(b => b.text() === '采纳')
    await acceptBtn?.trigger('click')
    expect(wrapper.emitted('accept')).toHaveLength(1)
  })

  it('emits regenerate when regenerate button is clicked', async () => {
    const wrapper = makeWrapper()
    const buttons = wrapper.findAll('button')
    const regenBtn = buttons.find(b => b.text() === '重新生成')
    await regenBtn?.trigger('click')
    expect(wrapper.emitted('regenerate')).toHaveLength(1)
  })
})
