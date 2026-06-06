import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ColumnMapping from '../../src/components/step3/ColumnMapping.vue'
import type { ColumnMappingItem } from '../../src/types/wizard'

describe('ColumnMapping', () => {
  const makeWrapper = (columns: ColumnMappingItem[] = []) =>
    mount(ColumnMapping, {
      props: { columns },
      global: {
        stubs: {
          NInput: {
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', ($event.target as HTMLInputElement).value)" />',
            props: ['modelValue', 'size', 'placeholder'],
            emits: ['update:modelValue'],
          },
          NButton: {
            template: '<button @click="$emit(\'click\')"><slot /></button>',
            props: ['text', 'size', 'type'],
            emits: ['click'],
          },
        },
      },
    })

  it('renders table headers', () => {
    const wrapper = makeWrapper([])
    const headers = wrapper.findAll('th')
    expect(headers).toHaveLength(3)
    expect(headers[0].text()).toContain('源列')
    expect(headers[1].text()).toContain('目标列')
  })

  it('renders provided columns', () => {
    const cols: ColumnMappingItem[] = [
      { source: 'name', target: '姓名' },
      { source: 'dept', target: '部门' },
    ]
    const wrapper = makeWrapper(cols)
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
  })

  it('shows source as readonly text when filled', () => {
    const cols: ColumnMappingItem[] = [{ source: 'id', target: 'ID' }]
    const wrapper = makeWrapper(cols)
    const sourceCell = wrapper.findAll('td')[0]
    expect(sourceCell.find('span').exists()).toBe(true)
    expect(sourceCell.find('span').text()).toContain('id')
  })

  it('shows NInput for empty source', () => {
    const cols: ColumnMappingItem[] = [{ source: '', target: '备注' }]
    const wrapper = makeWrapper(cols)
    const sourceCell = wrapper.findAll('td')[0]
    // Empty source → NInput rendered (stubbed as input)
    expect(sourceCell.find('input').exists()).toBe(true)
  })

  it('emits remove when delete button clicked', async () => {
    const cols: ColumnMappingItem[] = [{ source: 'x', target: 'y' }]
    const wrapper = makeWrapper(cols)
    const delBtn = wrapper.findAll('button')[0]
    await delBtn.trigger('click')
    expect(wrapper.emitted('remove')).toBeTruthy()
    expect(wrapper.emitted('remove')![0]).toEqual([0])
  })

  it('renders empty tbody when no columns', () => {
    const wrapper = makeWrapper([])
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
  })
})
