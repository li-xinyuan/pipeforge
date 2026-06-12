import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { InputSource } from '../../src/types/wizard'
import DatabaseForm from '../../src/components/step2/DatabaseForm.vue'

const mockFetchConnections = vi.fn()
const mockTestConnection = vi.fn()
const mockFetchTables = vi.fn()
const mockFetchColumns = vi.fn()

vi.mock('../../src/composables/useWizardApi', () => ({
  useConnectionApi: () => ({
    fetchConnections: mockFetchConnections,
    testConnection: mockTestConnection,
    fetchTables: mockFetchTables,
    connecting: { value: false },
    connectionError: { value: null },
    createConnection: vi.fn(),
    updateConnection: vi.fn(),
    deleteConnection: vi.fn(),
    fetchColumns: mockFetchColumns,
  }),
}))

const makeInput = (overrides: Partial<InputSource> = {}): InputSource => ({
  plugin: 'database',
  table: '',
  paramKey: '',
  fileId: '',
  config: { type: 'database', connectionId: '', queryType: 'table', tables: [], sql: '' },
  ...overrides,
})

const NSelectStub = {
  template: '<select :value="value"><option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>',
  props: ['value', 'options', 'placeholder', 'disabled', 'size'],
  emits: ['update:value'],
}

const NButtonStub = {
  template: '<button :disabled="disabled || loading"><slot /></button>',
  props: ['disabled', 'loading', 'size', 'type', 'text'],
  emits: ['click'],
}

const NRadioGroupStub = {
  template: '<div><slot /></div>',
  props: ['value'],
  emits: ['update:value'],
}

const NRadioStub = {
  template: '<label><input type="radio" :value="value" /><slot /></label>',
  props: ['value'],
}

const NInputStub = {
  template: '<input :value="modelValue" />',
  props: ['modelValue', 'type', 'placeholder', 'rows', 'size'],
  emits: ['update:value'],
}

const RouterLinkStub = {
  template: '<a><slot /></a>',
  props: ['to'],
}

const NTagStub = {
  template: '<span><slot /></span>',
  props: ['size', 'bordered', 'type'],
}

const NSpinStub = {
  template: '<div class="n-spin-stub" />',
  props: ['size'],
}

describe('DatabaseForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchConnections.mockResolvedValue([])
    mockFetchTables.mockResolvedValue([])
    mockFetchColumns.mockResolvedValue([])
  })

  function mountForm(input: InputSource = makeInput(), index = 0) {
    return mount(DatabaseForm, {
      props: { input, index },
      global: {
        stubs: {
          NSelect: NSelectStub,
          NButton: NButtonStub,
          NRadioGroup: NRadioGroupStub,
          NRadio: NRadioStub,
          NInput: NInputStub,
          RouterLink: RouterLinkStub,
          NTag: NTagStub,
          NSpin: NSpinStub,
        },
      },
    })
  }

  it('renders without crashing', () => {
    const wrapper = mountForm()
    expect(wrapper.exists()).toBe(true)
  })

  it('shows connection selector placeholder', () => {
    const wrapper = mountForm()
    expect(wrapper.text()).toContain('数据库连接')
  })

  it('shows link to settings page', () => {
    const wrapper = mountForm()
    expect(wrapper.text()).toContain('设置页')
  })

  it('does not show test/load buttons when no connection selected', () => {
    const wrapper = mountForm(makeInput({ config: { type: 'database', connectionId: '', queryType: 'table', tables: [], sql: '' } }))
    expect(wrapper.text()).not.toContain('测试连通')
    expect(wrapper.text()).not.toContain('加载表列表')
  })

  it('shows test button when connection selected', async () => {
    mockFetchConnections.mockResolvedValue([{ id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' }])
    const wrapper = mountForm(makeInput({ config: { type: 'database', connectionId: 'c1', queryType: 'table', tables: [], sql: '' } }))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('测试连通')
  })

  it('shows query type radio group when connection selected', async () => {
    mockFetchConnections.mockResolvedValue([{ id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' }])
    const wrapper = mountForm(makeInput({ config: { type: 'database', connectionId: 'c1', queryType: 'table', tables: [], sql: '' } }))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('选择表')
    expect(wrapper.text()).toContain('自定义 SQL')
  })

  it('shows table selector when query type is table', async () => {
    mockFetchConnections.mockResolvedValue([{ id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' }])
    const wrapper = mountForm(makeInput({ config: { type: 'database', connectionId: 'c1', queryType: 'table', tables: [], sql: '' } }))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('选择表')
  })

  it('shows SQL editor when query type is sql', async () => {
    mockFetchConnections.mockResolvedValue([{ id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' }])
    const wrapper = mountForm(makeInput({ config: { type: 'database', connectionId: 'c1', queryType: 'sql', tables: [], sql: 'SELECT 1' } }))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('SQL 查询')
  })

  it('emits update when connection is selected', async () => {
    mockFetchConnections.mockResolvedValue([{ id: 'c1', name: 'TestDB', dbType: 'sqlite', host: '/tmp/test.db', passwordSet: false, verified: true, createdAt: '', updatedAt: '' }])
    const wrapper = mountForm()
    await wrapper.vm.$nextTick()
    // NSelect stubbing by name doesn't work with naive-ui — the real component
    // has name "Select" internally. Find by component name and emit directly.
    const select = wrapper.findComponent({ name: 'Select' })
    expect(select.exists()).toBe(true)
    await select.vm.$emit('update:value', 'c1')
    await wrapper.vm.$nextTick()
    // Wait for async onConnectionSelected to complete (autoLoadTables)
    await new Promise(r => setTimeout(r, 50))
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update')).toBeTruthy()
  })
})
