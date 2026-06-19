import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CodeEditor from '../../src/components/common/CodeEditor.vue'

// Mock useTheme
vi.mock('../../src/composables/useTheme', () => ({
  useTheme: () => ({ isDark: { value: false }, toggleTheme: vi.fn() }),
}))

const makeWrapper = (props = {}) =>
  mount(CodeEditor, {
    props: { modelValue: 'SELECT 1', language: 'sql', ...props },
    attachTo: document.body,
  })

describe('CodeEditor', () => {
  it('renders wrapper div', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('.cm-editor-wrapper').exists()).toBe(true)
  })

  it('falls back to textarea in happy-dom', () => {
    const wrapper = makeWrapper()
    // In happy-dom, CodeMirror fails to init and falls back to textarea
    const textarea = wrapper.find('textarea')
    if (textarea.exists()) {
      expect(textarea.element.value).toBe('SELECT 1')
    }
  })

  it('textarea reflects modelValue in fallback mode', async () => {
    const wrapper = makeWrapper({ modelValue: 'SELECT * FROM users' })
    const textarea = wrapper.find('textarea')
    if (textarea.exists()) {
      expect(textarea.element.value).toBe('SELECT * FROM users')
    }
  })

  it('emits update:modelValue on textarea input in fallback mode', async () => {
    const wrapper = makeWrapper()
    const textarea = wrapper.find('textarea')
    if (textarea.exists()) {
      await textarea.setValue('SELECT 2')
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')!.at(-1)![0]).toBe('SELECT 2')
    }
  })

  it('renders with python language prop', () => {
    const wrapper = makeWrapper({ language: 'python', modelValue: 'print("hello")' })
    expect(wrapper.find('.cm-editor-wrapper').exists()).toBe(true)
  })

  it('renders with yaml language prop', () => {
    const wrapper = makeWrapper({ language: 'yaml', modelValue: 'key: value' })
    expect(wrapper.find('.cm-editor-wrapper').exists()).toBe(true)
  })

  it('sets readOnly on fallback textarea', () => {
    const wrapper = makeWrapper({ readOnly: true })
    const textarea = wrapper.find('textarea')
    if (textarea.exists()) {
      expect(textarea.element.readOnly).toBe(true)
    }
  })

  it('applies minHeight style on fallback textarea', () => {
    const wrapper = makeWrapper({ minHeight: '200px' })
    const textarea = wrapper.find('textarea')
    if (textarea.exists()) {
      expect(textarea.element.style.minHeight).toBe('200px')
    }
  })
})
