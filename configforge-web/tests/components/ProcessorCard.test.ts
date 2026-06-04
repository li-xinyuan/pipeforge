import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NTag } from 'naive-ui'
import ProcessorCard from '../../src/components/step3/ProcessorCard.vue'
import type { ProcessorStep } from '../../src/types/wizard'

function createSqlProc(): ProcessorStep {
  return { name: 'SQL 查询', plugin: 'sql', sql: 'SELECT 1', inputTables: [], outputTables: ['r1'], checkpoints: [] }
}

function createPythonProc(): ProcessorStep {
  return { name: 'Python 脚本', plugin: 'python', script: 'def process(ctx): pass', inputTables: [], outputTables: ['out'], checkpoints: [] }
}

describe('ProcessorCard', () => {
  const baseOptions = {
    global: {
      plugins: [createPinia()],
      stubs: { CheckpointSection: { template: '<div class="checkpoint-stub" />', props: ['checkpoints', 'procIndex'] } },
    },
  }

  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders SQL processor with SQL tag', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    const tags = wrapper.findAllComponents(NTag)
    const typeTag = tags.find(t => t.text() === 'SQL' || t.text() === 'Python')
    expect(typeTag?.text()).toBe('SQL')
  })

  it('renders Python processor with Python tag', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createPythonProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    const tags = wrapper.findAllComponents(NTag)
    const typeTag = tags.find(t => t.text() === 'SQL' || t.text() === 'Python')
    expect(typeTag?.text()).toBe('Python')
  })

  it('renders delete button', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    expect(wrapper.text()).toContain('删除')
  })

  it('renders processor name in header', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    expect(wrapper.text()).toContain('SQL 查询')
  })

  it('shows default step label when name is empty', () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: { ...createSqlProc(), name: '' }, index: 2, availableTables: [] },
      ...baseOptions,
    })
    expect(wrapper.text()).toContain('步骤 3')
  })

  it('emits remove when delete button clicked', async () => {
    const wrapper = mount(ProcessorCard, {
      props: { proc: createSqlProc(), index: 0, availableTables: [] },
      ...baseOptions,
    })
    const deleteBtns = wrapper.findAll('button')
    const deleteBtn = deleteBtns.find(b => b.text() === '删除')
    await deleteBtn!.trigger('click')
    expect(wrapper.emitted('remove')).toBeTruthy()
  })
})
