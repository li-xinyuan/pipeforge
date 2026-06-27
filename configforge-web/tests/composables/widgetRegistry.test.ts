import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import {
  registerWidget,
  getWidget,
  registerAsyncOptionsLoader,
  getAsyncOptionsLoader,
  clearWidgetRegistry,
} from '../../src/composables/widgetRegistry'

describe('widgetRegistry', () => {
  beforeEach(() => {
    clearWidgetRegistry()
  })

  describe('registerWidget / getWidget', () => {
    it('registers and retrieves a named widget', () => {
      const FakeWidget = defineComponent({ name: 'FakeWidget', template: '<div />' })
      registerWidget('code-editor', FakeWidget)
      expect(getWidget('code-editor')).toBe(FakeWidget)
    })

    it('returns undefined for unregistered widget', () => {
      expect(getWidget('nonexistent')).toBeUndefined()
    })

    it('overwrites when re-registering the same name', () => {
      const WidgetA = defineComponent({ name: 'WidgetA', template: '<div />' })
      const WidgetB = defineComponent({ name: 'WidgetB', template: '<span />' })
      registerWidget('w', WidgetA)
      registerWidget('w', WidgetB)
      expect(getWidget('w')).toBe(WidgetB)
    })
  })

  describe('registerAsyncOptionsLoader / getAsyncOptionsLoader', () => {
    it('registers and retrieves an async options loader', async () => {
      const loader = async () => [
        { label: 'Sheet1', value: 'Sheet1' },
        { label: 'Sheet2', value: 'Sheet2' },
      ]
      registerAsyncOptionsLoader('preview-sheets', loader)
      expect(getAsyncOptionsLoader('preview-sheets')).toBe(loader)

      const options = await loader()
      expect(options).toHaveLength(2)
      expect(options[0]).toEqual({ label: 'Sheet1', value: 'Sheet1' })
    })

    it('returns undefined for unregistered loader', () => {
      expect(getAsyncOptionsLoader('nonexistent')).toBeUndefined()
    })
  })

  describe('clearWidgetRegistry', () => {
    it('clears both widgets and async loaders', () => {
      const Widget = defineComponent({ name: 'W', template: '<div />' })
      registerWidget('w', Widget)
      registerAsyncOptionsLoader('loader', async () => [])

      clearWidgetRegistry()

      expect(getWidget('w')).toBeUndefined()
      expect(getAsyncOptionsLoader('loader')).toBeUndefined()
    })
  })
})
