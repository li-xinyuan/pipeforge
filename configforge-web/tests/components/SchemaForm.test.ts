import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import {
  registerWidget,
  registerAsyncOptionsLoader,
  clearWidgetRegistry,
} from '../../src/composables/widgetRegistry'

/**
 * SchemaForm 测试 — 限制①动态表单基础设施。
 *
 * 用 csv input schema 作为 PoC（最小：3 个字段 + type + file 跳过），
 * 验证 v-model 双向绑定、字段跳过、widget 渲染、异步选项、命名 widget 委托。
 *
 * 注意：Naive UI 组件无 `name` 属性，VTU 的 `global.stubs` 无法按名称匹配
 * `<script setup>` 中本地导入的组件。改用 `vi.mock('naive-ui', ...)` 在模块层
 * 替换为纯对象 stub（template 字符串，无需 vue 运行时），使 SchemaForm 导入时
 * 即获得 stub 组件。vi.mock 被提升到文件顶部，factory 内不能引用外部变量。
 */

vi.mock('naive-ui', () => ({
  NInput: {
    template: '<input type="text" data-test="n-input" :value="value" :disabled="disabled" :placeholder="placeholder" @input="$emit(\'update:value\', $event.target.value)" />',
    props: ['value', 'size', 'placeholder', 'disabled'],
    emits: ['update:value'],
  },
  NSelect: {
    template: '<select data-test="n-select" :value="value" :disabled="disabled" @change="$emit(\'update:value\', $event.target.value)"><option v-for="o in (options || [])" :key="o.value" :value="o.value">{{ o.label }}</option></select>',
    props: ['value', 'options', 'size', 'disabled', 'loading'],
    emits: ['update:value'],
  },
  NInputNumber: {
    template: '<input type="number" data-test="n-input-number" :value="value" :disabled="disabled" @input="$emit(\'update:value\', Number($event.target.value))" />',
    props: ['value', 'size', 'disabled'],
    emits: ['update:value'],
  },
  NCheckbox: {
    template: '<input type="checkbox" data-test="n-checkbox" :checked="checked" :disabled="disabled" @change="$emit(\'update:checked\', $event.target.checked)" />',
    props: ['checked', 'disabled'],
    emits: ['update:checked'],
  },
}))

// 在 mock 之后导入被测组件
import SchemaForm from '../../src/components/common/SchemaForm.vue'

/** csv input 插件的真实 schema 形态（pydantic v2 默认 alias 输出）。 */
const csvSchema = {
  properties: {
    type: { const: 'csv', default: 'csv', type: 'string' },
    delimiter: { default: ',', type: 'string' },
    encoding: { default: 'utf-8', type: 'string' },
    hasHeader: { default: true, type: 'boolean' },
    file: { default: null, type: ['string', 'null'] },
  },
}

function mountForm(modelValue: Record<string, unknown>, schema: Record<string, unknown>, opts: Record<string, unknown> = {}) {
  return mount(SchemaForm, {
    props: { modelValue, schema },
    ...opts,
  })
}

describe('SchemaForm', () => {
  beforeEach(() => {
    clearWidgetRegistry()
  })

  describe('字段跳过', () => {
    it('跳过 type (discriminator) 和 file (runtime 注入) 字段', () => {
      const wrapper = mountForm({ type: 'csv', delimiter: ',' }, csvSchema)
      const inputs = wrapper.findAll('[data-test="n-input"]')
      // delimiter + encoding = 2 个 NInput（type 和 file 被跳过）
      expect(inputs).toHaveLength(2)
    })
  })

  describe('v-model 双向绑定（csv PoC）', () => {
    it('渲染 modelValue 中的 delimiter 值', () => {
      const wrapper = mountForm({ delimiter: ';' }, csvSchema)
      const inputs = wrapper.findAll('[data-test="n-input"]')
      // 第一个 NInput 是 delimiter
      expect((inputs[0].element as HTMLInputElement).value).toBe(';')
    })

    it('更新 delimiter 时 emit update:modelValue', async () => {
      const wrapper = mountForm({ delimiter: ',', encoding: 'utf-8', hasHeader: true }, csvSchema)
      const input = wrapper.find('[data-test="n-input"]')
      await input.setValue('|')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![events!.length - 1][0]).toEqual({
        delimiter: '|',
        encoding: 'utf-8',
        hasHeader: true,
      })
    })

    it('更新 hasHeader (boolean checkbox) 时 emit update:modelValue', async () => {
      const wrapper = mountForm({ delimiter: ',', encoding: 'utf-8', hasHeader: true }, csvSchema)
      const checkbox = wrapper.find('[data-test="n-checkbox"]')
      // 手动切换 checked 状态并触发 change（stub 监听 @change）
      ;(checkbox.element as HTMLInputElement).checked = false
      await checkbox.trigger('change')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![events!.length - 1][0]).toMatchObject({ hasHeader: false })
    })

    it('未提供值时使用 schema.default', () => {
      const wrapper = mountForm({}, csvSchema)
      const inputs = wrapper.findAll('[data-test="n-input"]')
      // delimiter 默认 ','
      expect((inputs[0].element as HTMLInputElement).value).toBe(',')
      // hasHeader 默认 true → checkbox checked
      const checkbox = wrapper.find('[data-test="n-checkbox"]')
      expect((checkbox.element as HTMLInputElement).checked).toBe(true)
    })
  })

  describe('类型分发', () => {
    it('integer 字段渲染 NInputNumber', () => {
      const schema = {
        properties: { batchSize: { type: 'integer', default: 1000 } },
      }
      const wrapper = mountForm({ batchSize: 1000 }, schema)
      expect(wrapper.find('[data-test="n-input-number"]').exists()).toBe(true)
    })

    it('enum 字段渲染 NSelect', () => {
      const schema = {
        properties: {
          encoding: {
            type: 'string',
            enum: ['utf-8', 'gbk'],
            default: 'utf-8',
          },
        },
      }
      const wrapper = mountForm({ encoding: 'utf-8' }, schema)
      const select = wrapper.find('[data-test="n-select"]')
      expect(select.exists()).toBe(true)
      const options = select.findAll('option')
      expect(options).toHaveLength(2)
      expect(options[0].text()).toBe('utf-8')
    })
  })

  describe('异步选项（x-ui-options-from）', () => {
    it('挂载后调用注册的 loader 并渲染选项', async () => {
      const loader = vi.fn(async () => [
        { label: 'utf-8', value: 'utf-8' },
        { label: 'gbk', value: 'gbk' },
      ])
      registerAsyncOptionsLoader('encodings', loader)

      const schema = {
        properties: {
          encoding: {
            type: 'string',
            default: 'utf-8',
            'x-ui-options-from': 'encodings',
          },
        },
      }
      const wrapper = mountForm({ encoding: 'utf-8' }, schema)
      await flushPromises()

      expect(loader).toHaveBeenCalledOnce()
      const options = wrapper.find('[data-test="n-select"]').findAll('option')
      expect(options).toHaveLength(2)
      expect(options[0].text()).toBe('utf-8')
    })

    it('未注册 loader 时不报错且选项为空', async () => {
      const schema = {
        properties: {
          encoding: {
            type: 'string',
            'x-ui-options-from': 'unknown-loader',
          },
        },
      }
      const wrapper = mountForm({ encoding: 'utf-8' }, schema)
      await flushPromises()
      expect(wrapper.find('[data-test="n-select"]').exists()).toBe(true)
      expect(wrapper.findAll('option')).toHaveLength(0)
    })
  })

  describe('命名 widget（x-ui-widget）', () => {
    it('注册的命名 widget 替代通用控件渲染', async () => {
      const NamedWidget = {
        template: '<div data-test="named-widget">{{ modelValue }}</div>',
        props: ['modelValue'],
        emits: ['update:modelValue'],
      }
      registerWidget('my-widget', NamedWidget)

      const schema = {
        properties: {
          sql: {
            type: 'string',
            default: '',
            'x-ui-widget': 'my-widget',
          },
        },
      }
      const wrapper = mountForm({ sql: 'SELECT 1' }, schema)
      const named = wrapper.find('[data-test="named-widget"]')
      expect(named.exists()).toBe(true)
      expect(named.text()).toBe('SELECT 1')
    })

    it('命名 widget emit update:modelValue 时向上冒泡', async () => {
      const NamedWidget = {
        template: '<button data-test="named-widget" @click="$emit(\'update:modelValue\', \'NEW\')">set</button>',
        props: ['modelValue'],
        emits: ['update:modelValue'],
      }
      registerWidget('my-widget', NamedWidget)

      const schema = {
        properties: {
          sql: {
            type: 'string',
            'x-ui-widget': 'my-widget',
          },
        },
      }
      const wrapper = mountForm({ sql: 'old' }, schema)
      await wrapper.find('[data-test="named-widget"]').trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![events!.length - 1][0]).toMatchObject({ sql: 'NEW' })
    })

    it('widgetProps 向命名 widget 透传 per-instance props', () => {
      const NamedWidget = {
        template: '<div data-test="named-widget">{{ options.length }}-{{ disabled }}</div>',
        props: ['modelValue', 'options', 'disabled'],
        emits: ['update:modelValue'],
      }
      registerWidget('my-widget', NamedWidget)

      const schema = {
        properties: {
          sheet: {
            type: 'string',
            default: 'Sheet1',
            'x-ui-widget': 'my-widget',
          },
        },
      }
      const wrapper = mount(SchemaForm, {
        props: {
          modelValue: { sheet: 'Sheet1' },
          schema,
          widgetProps: {
            'my-widget': {
              options: [{ label: 'Sheet1', value: 'Sheet1' }, { label: 'Sheet2', value: 'Sheet2' }],
              disabled: true,
            },
          },
        },
      })
      const named = wrapper.find('[data-test="named-widget"]')
      expect(named.exists()).toBe(true)
      expect(named.text()).toBe('2-true')
    })

    it('widgetProps 未提供时不报错', () => {
      const NamedWidget = {
        template: '<div data-test="named-widget">{{ modelValue }}</div>',
        props: ['modelValue'],
        emits: ['update:modelValue'],
      }
      registerWidget('my-widget', NamedWidget)

      const schema = {
        properties: {
          sql: {
            type: 'string',
            'x-ui-widget': 'my-widget',
          },
        },
      }
      const wrapper = mountForm({ sql: 'SELECT 1' }, schema)
      expect(wrapper.find('[data-test="named-widget"]').exists()).toBe(true)
    })
  })

  describe('disabled 透传', () => {
    it('disabled prop 透传到 NInput', () => {
      const wrapper = mount(SchemaForm, {
        props: {
          modelValue: { delimiter: ',', encoding: 'utf-8', hasHeader: true },
          schema: csvSchema,
          disabled: true,
        },
      })
      const input = wrapper.find('[data-test="n-input"]')
      expect((input.element as HTMLInputElement).disabled).toBe(true)
    })
  })

  describe('skipFields（额外跳过字段）', () => {
    it('skipFields 中的字段被跳过', () => {
      const wrapper = mount(SchemaForm, {
        props: {
          modelValue: { delimiter: ',', encoding: 'utf-8', hasHeader: true, sourceTable: 't1' },
          schema: {
            properties: {
              delimiter: { type: 'string', default: ',' },
              encoding: { type: 'string', default: 'utf-8' },
              sourceTable: { type: 'string', default: '' },
            },
          },
          skipFields: ['sourceTable'],
        },
      })
      const inputs = wrapper.findAll('[data-test="n-input"]')
      // delimiter + encoding 渲染，sourceTable 被跳过
      expect(inputs).toHaveLength(2)
    })

    it('skipFields 与默认跳过字段（type/file）合并', () => {
      const wrapper = mount(SchemaForm, {
        props: {
          modelValue: { type: 'csv', delimiter: ',', file: null, columns: [] },
          schema: {
            properties: {
              type: { const: 'csv', default: 'csv', type: 'string' },
              delimiter: { type: 'string', default: ',' },
              file: { type: ['string', 'null'], default: null },
              columns: { type: 'array', default: [] },
            },
          },
          skipFields: ['columns'],
        },
      })
      // type/file 默认跳过，columns 额外跳过，只剩 delimiter
      expect(wrapper.findAll('[data-test="n-input"]')).toHaveLength(1)
    })
  })
})
