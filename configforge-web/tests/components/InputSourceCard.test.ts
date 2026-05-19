import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import InputSourceCard from '../../src/components/step2/InputSourceCard.vue'
import type { InputSource } from '../../src/types/wizard'

const makeInput = (overrides: Partial<InputSource> = {}): InputSource => ({
  plugin: 'excel',
  table: '',
  paramKey: '',
  fileId: '',
  config: { type: 'excel', sheet: 'Sheet1' },
  ...overrides,
})

const NButtonStub = {
  template: '<button :disabled="disabled"><slot /></button>',
  props: ['disabled', 'loading', 'size', 'type', 'text', 'dashed'],
  emits: ['click'],
}

const NInputStub = {
  template: '<input :value="modelValue" :disabled="disabled" />',
  props: ['modelValue', 'disabled', 'size', 'placeholder', 'status', 'id'],
  emits: ['update:value'],
}

const NTagStub = {
  template: '<span><slot /></span>',
  props: ['type', 'size', 'bordered', 'closable'],
}

const NCardStub = {
  template: '<div><slot name="header" /><slot /></div>',
  props: ['size', 'hoverable'],
}

const NUploadStub = {
  template: '<div><slot /></div>',
  props: ['customRequest', 'showFileList', 'accept'],
}

const NSelectStub = {
  template: '<select :disabled="disabled"><option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>',
  props: ['value', 'disabled', 'options', 'size'],
  emits: ['update:value'],
}

const NCheckboxStub = {
  template: '<input type="checkbox" :checked="checked" :disabled="disabled" />',
  props: ['checked', 'disabled'],
  emits: ['update:checked'],
}

const NSpinStub = {
  template: '<div class="n-spin-stub" />',
  props: ['size'],
}

const ColumnPreviewStub = {
  template: '<div />',
  props: ['columns', 'rows'],
}

describe('InputSourceCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountCard(input: InputSource = makeInput(), index = 0) {
    return mount(InputSourceCard, {
      props: { input, index },
      global: {
        stubs: {
          NButton: NButtonStub,
          NInput: NInputStub,
          NTag: NTagStub,
          NCard: NCardStub,
          NUpload: NUploadStub,
          NSelect: NSelectStub,
          NCheckbox: NCheckboxStub,
          NSpin: NSpinStub,
          ColumnPreview: ColumnPreviewStub,
        },
      },
    })
  }

  it('renders without crashing', () => {
    const wrapper = mountCard()
    expect(wrapper.exists()).toBe(true)
  })

  it('shows upload button when no fileId', () => {
    const wrapper = mountCard(makeInput({ fileId: '' }))
    expect(wrapper.text()).toContain('上传')
  })

  it('shows AI prompt when fileId is set and no confirmedAnalysis', () => {
    const wrapper = mountCard(makeInput({ fileId: 'file-1', confirmedAnalysis: undefined }))
    expect(wrapper.find('.input-card__ai-prompt').exists()).toBe(true)
  })

  it('shows AI prompt text', () => {
    const wrapper = mountCard(makeInput({ fileId: 'file-1' }))
    expect(wrapper.text()).toContain('AI 可分析')
    expect(wrapper.text()).toContain('立即分析')
  })

  it('hides AI prompt when confirmedAnalysis exists', () => {
    const wrapper = mountCard(makeInput({
      fileId: 'file-1',
      confirmedAnalysis: { columnTypes: { a: 'string' }, tableName: 't', paramKeys: [], timestamp: 1 },
    }))
    expect(wrapper.find('.input-card__ai-prompt').exists()).toBe(false)
  })

  it('hides AI prompt when no fileId', () => {
    const wrapper = mountCard(makeInput({ fileId: '' }))
    expect(wrapper.find('.input-card__ai-prompt').exists()).toBe(false)
  })
})
