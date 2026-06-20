import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useKeyboard } from '../../src/composables/useKeyboard'

function mountWithKeyboard(handlers: Record<string, (e: KeyboardEvent) => void>) {
  const Wrapper = defineComponent({
    setup() {
      useKeyboard(handlers)
      return () => h('div', { class: 'wrapper' })
    },
  })
  return mount(Wrapper)
}

function createKeyboardEvent(props: Partial<KeyboardEventInit> & { key: string }) {
  const event = new KeyboardEvent('keydown', {
    key: props.key,
    ctrlKey: props.ctrlKey ?? false,
    metaKey: props.metaKey ?? false,
    shiftKey: props.shiftKey ?? false,
    bubbles: true,
    cancelable: true,
  })
  vi.spyOn(event, 'preventDefault')
  return event
}

describe('useKeyboard', () => {
  let handlers: Record<string, (e: KeyboardEvent) => void>

  beforeEach(() => {
    handlers = {
      'Ctrl+s': vi.fn(),
      'Ctrl+Enter': vi.fn(),
      'Escape': vi.fn(),
    }
  })

  it('registers a keydown listener on mount', () => {
    const addSpy = vi.spyOn(document, 'addEventListener')
    mountWithKeyboard(handlers)
    expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
    addSpy.mockRestore()
  })

  it('removes the keydown listener on unmount', () => {
    const removeSpy = vi.spyOn(document, 'removeEventListener')
    const wrapper = mountWithKeyboard(handlers)
    wrapper.unmount()
    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
    removeSpy.mockRestore()
  })

  it('triggers Ctrl+S handler', () => {
    mountWithKeyboard(handlers)
    const event = createKeyboardEvent({ key: 's', ctrlKey: true })
    document.dispatchEvent(event)
    expect(handlers['Ctrl+s']).toHaveBeenCalledWith(event)
    expect(event.preventDefault).toHaveBeenCalled()
  })

  it('triggers Ctrl+Enter handler', () => {
    mountWithKeyboard(handlers)
    const event = createKeyboardEvent({ key: 'Enter', ctrlKey: true })
    document.dispatchEvent(event)
    expect(handlers['Ctrl+Enter']).toHaveBeenCalledWith(event)
    expect(event.preventDefault).toHaveBeenCalled()
  })

  it('triggers Escape handler', () => {
    mountWithKeyboard(handlers)
    const event = createKeyboardEvent({ key: 'Escape' })
    document.dispatchEvent(event)
    expect(handlers['Escape']).toHaveBeenCalledWith(event)
    expect(event.preventDefault).toHaveBeenCalled()
  })

  it('does not trigger handler for unregistered key', () => {
    mountWithKeyboard(handlers)
    const event = createKeyboardEvent({ key: 'a' })
    document.dispatchEvent(event)
    expect(handlers['Ctrl+s']).not.toHaveBeenCalled()
    expect(handlers['Escape']).not.toHaveBeenCalled()
  })

  it('supports metaKey (Cmd) as Ctrl modifier', () => {
    mountWithKeyboard(handlers)
    const event = createKeyboardEvent({ key: 's', metaKey: true })
    document.dispatchEvent(event)
    expect(handlers['Ctrl+s']).toHaveBeenCalledWith(event)
  })

  it('supports Shift modifier in key combination', () => {
    const shiftHandlers = {
      'Ctrl+Shift+p': vi.fn(),
    }
    mountWithKeyboard(shiftHandlers)
    const event = createKeyboardEvent({ key: 'p', ctrlKey: true, shiftKey: true })
    document.dispatchEvent(event)
    expect(shiftHandlers['Ctrl+Shift+p']).toHaveBeenCalledWith(event)
  })

  it('calls preventDefault only when handler is found', () => {
    mountWithKeyboard(handlers)
    const event = createKeyboardEvent({ key: 'x' }) // no handler for 'x'
    document.dispatchEvent(event)
    expect(event.preventDefault).not.toHaveBeenCalled()
  })
})
