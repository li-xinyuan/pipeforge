import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

/**
 * SheetSelector 测试 — Excel 工作表选择命名 widget（限制①第二阶段迁移）。
 *
 * 双行为：
 * - options.length > 0：渲染 NSelect
 * - options.length === 0：渲染 NInput
 *
 * 注意：vi.mock 被提升到文件顶部，factory 内不能引用外部变量。
 */

vi.mock('naive-ui', () => ({
  NInput: {
    template: '<input type="text" data-test="n-input" :value="value" :disabled="disabled" :placeholder="placeholder" @input="$emit(\'update:value\', $event.target.value)" />',
    props: ['value', 'placeholder', 'disabled'],
    emits: ['update:value'],
  },
  NSelect: {
    template: '<select data-test="n-select" :value="value" :disabled="disabled" @change="$emit(\'update:value\', $event.target.value)"><option v-for="o in (options || [])" :key="o.value" :value="o.value">{{ o.label }}</option></select>',
    props: ['value', 'options', 'disabled'],
    emits: ['update:value'],
  },
}))

import SheetSelector from '../../src/components/common/SheetSelector.vue'

function mountSelector(props: Record<string, unknown>) {
  return mount(SheetSelector, { props })
}

describe('SheetSelector', () => {
  describe('渲染分发', () => {
    it('options.length > 0 时渲染 NSelect', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
        options: [
          { label: 'Sheet1', value: 'Sheet1' },
          { label: 'Sheet2', value: 'Sheet2' },
        ],
      })
      expect(wrapper.find('[data-test="n-select"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="n-input"]').exists()).toBe(false)
    })

    it('options 为空数组时渲染 NInput', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
        options: [],
      })
      expect(wrapper.find('[data-test="n-input"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="n-select"]').exists()).toBe(false)
    })

    it('options 未提供时回退到 NInput', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
      })
      expect(wrapper.find('[data-test="n-input"]').exists()).toBe(true)
      expect(wrapper.find('[data-test="n-select"]').exists()).toBe(false)
    })

    it('NSelect 渲染所有选项', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
        options: [
          { label: 'Sheet1', value: 'Sheet1' },
          { label: 'Sheet2', value: 'Sheet2' },
          { label: 'Data', value: 'Data' },
        ],
      })
      const options = wrapper.find('[data-test="n-select"]').findAll('option')
      expect(options).toHaveLength(3)
      expect(options[2].text()).toBe('Data')
    })
  })

  describe('v-model 双向绑定', () => {
    it('NInput 模式下输入时 emit update:modelValue', async () => {
      const wrapper = mountSelector({ modelValue: 'Sheet1', options: [] })
      const input = wrapper.find('[data-test="n-input"]')
      await input.setValue('MySheet')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![events!.length - 1][0]).toBe('MySheet')
    })

    it('NSelect 模式下选择时 emit update:modelValue', async () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
        options: [
          { label: 'Sheet1', value: 'Sheet1' },
          { label: 'Sheet2', value: 'Sheet2' },
        ],
      })
      const select = wrapper.find('[data-test="n-select"]')
      await select.setValue('Sheet2')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![events!.length - 1][0]).toBe('Sheet2')
    })
  })

  describe('disabled 透传', () => {
    it('NInput 模式下 disabled 透传', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
        options: [],
        disabled: true,
      })
      const input = wrapper.find('[data-test="n-input"]')
      expect((input.element as HTMLInputElement).disabled).toBe(true)
    })

    it('NSelect 模式下 disabled 透传', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet1',
        options: [{ label: 'Sheet1', value: 'Sheet1' }],
        disabled: true,
      })
      const select = wrapper.find('[data-test="n-select"]')
      expect((select.element as HTMLSelectElement).disabled).toBe(true)
    })
  })

  describe('初始值展示', () => {
    it('NInput 模式下展示 modelValue', () => {
      const wrapper = mountSelector({ modelValue: 'MySheet', options: [] })
      expect((wrapper.find('[data-test="n-input"]').element as HTMLInputElement).value).toBe('MySheet')
    })

    it('NSelect 模式下展示 modelValue', () => {
      const wrapper = mountSelector({
        modelValue: 'Sheet2',
        options: [
          { label: 'Sheet1', value: 'Sheet1' },
          { label: 'Sheet2', value: 'Sheet2' },
        ],
      })
      const select = wrapper.find('[data-test="n-select"]')
      expect((select.element as HTMLSelectElement).value).toBe('Sheet2')
    })
  })
})
