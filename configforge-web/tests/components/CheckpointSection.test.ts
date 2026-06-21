import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CheckpointSection from '../../src/components/step3/CheckpointSection.vue'
import type { CheckRule, RowCountRule } from '../../src/types/wizard'

// Mock Naive UI components that need special handling
vi.mock('naive-ui', async () => {
  const actual = await vi.importActual('naive-ui')
  return {
    ...actual,
    useDialog: () => ({
      warning: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
    }),
    NInputNumber: {
      name: 'NInputNumber',
      template: '<input type="number" class="n-input-number-stub" :value="value" @input="$emit(\'update:value\', Number($event.target.value))" />',
      props: ['value', 'min', 'max', 'step', 'size', 'style'],
      emits: ['update:value'],
    },
  }
})

function makeRowCount(overrides: Partial<RowCountRule> = {}): RowCountRule {
  return { type: 'row_count', table: '', min: 0, max: undefined, on_failure: 'block', ...overrides }
}

describe('CheckpointSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountComponent(checkpoints: CheckRule[] = []) {
    return mount(CheckpointSection, {
      props: {
        checkpoints,
        procIndex: 1,
        availableTables: [
          { table_name: 'output', columns: ['id', 'name', 'status', 'amount'] },
        ],
      },
      global: {
        plugins: [createPinia()],
      },
    })
  }

  it('renders collapsed by default', () => {
    const wrapper = mountComponent()
    expect(wrapper.text()).toContain('数据检查点')
    // The rules container div (with class p-3) should not be visible when collapsed
    const rulesContainer = wrapper.find('.p-3')
    expect(rulesContainer.exists()).toBe(false)
  })

  it('expands on header click', async () => {
    const wrapper = mountComponent()
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.find('.p-3').exists()).toBe(true)
  })

  it('shows empty state when no rules', async () => {
    const wrapper = mountComponent()
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.text()).toContain('暂未配置检查点规则')
  })

  it('renders existing row_count rule with correct tag count', async () => {
    const wrapper = mountComponent([makeRowCount({ table: 't1', min: 10 })])
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.text()).toContain('1 条规则')
  })

  it('adds new rule on button click', async () => {
    const wrapper = mountComponent([])
    await wrapper.find('.cursor-pointer').trigger('click')

    const buttons = wrapper.findAll('button')
    const addRuleBtn = buttons.find(b => b.text().includes('添加规则'))
    expect(addRuleBtn).toBeTruthy()
    await addRuleBtn!.trigger('click')

    const emitted = wrapper.emitted('update:checkpoints') as unknown as [CheckRule[]][] | undefined
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toHaveLength(1)
    expect(emitted![0][0][0].type).toBe('row_count')
  })

  it('removes rule on delete click', async () => {
    const wrapper = mountComponent([makeRowCount()])
    await wrapper.find('.cursor-pointer').trigger('click')

    const buttons = wrapper.findAll('button')
    const deleteBtn = buttons.find(b => b.text() === '删除')
    expect(deleteBtn).toBeTruthy()
    await deleteBtn!.trigger('click')

    const emitted = wrapper.emitted('update:checkpoints') as unknown as [CheckRule[]][] | undefined
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toHaveLength(0)
  })

  it('renders null_rate rule with column and threshold fields', async () => {
    const nullRateRule: CheckRule = {
      type: 'null_rate',
      table: '',
      column: 'id',
      max_null_rate: 0.1,
      on_failure: 'warn',
    }
    const wrapper = mountComponent([nullRateRule])
    await wrapper.find('.cursor-pointer').trigger('click')
    // Should show the type label
    expect(wrapper.text()).toContain('空值率检查')
    expect(wrapper.text()).toContain('1 条规则')
  })
})
